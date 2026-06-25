"""Personal Score: genre benefit + exclusivity affinity (axes normalized independently)."""
import json
import logging
from collections import defaultdict

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

from accounts.models import UserPreferenceProfile, UserPreferenceChatSession, UserTasteAnalysis
from subscriptions.models import Platform

from .benchmark_constants import GENRE_NAMES, platform_icon
from .benchmark_scoring import normalize_scores
from .llm_judgment import get_llm_judgment, is_configured
from .taste_titles import fallback_taste_titles, resolve_taste_titles_from_llm, taste_titles_prompt_block
from .title_display import get_title_display_map, title_payload_from_map
from .models import (
    ContentReaction,
    LLMJudgmentCache,
    PlatformBenchmarkSnapshot,
    PlatformGenreStats,
    StreamingCache,
    TitleGenres,
    TitleMeta,
)

logger = logging.getLogger(__name__)

PERSONAL_SCORE_CACHE_TTL = 60 * 60 * 6

LIKE_WEIGHT = 1.0
DISLIKE_WEIGHT = -0.5
DAILY_TASTE_LLM_LIMIT = 5

TASTE_LLM_SCHEMA = (
    '{"genre_weights": {"<genre_id>": float 0.0-1.0}, '
    '"summary": string, "top_genre_ids": [int], '
    '"taste_title_habit": string, "taste_title_genre": string}'
)

ONBOARDING_PARSE_SCHEMA = (
    '{"monthly_spend_cap": int|null, "preferred_genre_ids": [int], '
    '"consumption_habits": {"binge": bool, "family": bool, "late_night": bool, '
    '"documentary_heavy": bool}, '
    '"platform_criteria": [string], "genre_weights": {"<genre_id>": float}, '
    '"taste_summary": string, "taste_title_habit": string, "taste_title_genre": string}'
)


def _content_media_type(content):
    ct = (content.content_type or '').lower()
    if ct in ('tv', 'show', 'series'):
        return 'tv'
    return 'movie'


def _normalize_genre_weights(raw_weights):
    if not raw_weights:
        return {}
    cleaned = {}
    for gid, w in raw_weights.items():
        try:
            key = int(gid)
            val = max(0.0, float(w))
        except (TypeError, ValueError):
            continue
        if val > 0:
            cleaned[key] = val
    if not cleaned:
        return {}
    lo, hi = min(cleaned.values()), max(cleaned.values())
    if hi == lo:
        return {k: 1.0 for k in cleaned}
    return {k: round((v - lo) / (hi - lo), 4) for k, v in cleaned.items()}


def compute_reaction_genre_weights(user):
    weights = defaultdict(float)
    likes = 0
    dislikes = 0

    reactions = ContentReaction.objects.filter(user=user).select_related('content')
    for reaction in reactions:
        content = reaction.content
        media_type = _content_media_type(content)
        genre_rows = TitleGenres.objects.filter(
            tmdb_id=content.tmdb_id, media_type=media_type,
        ).values_list('genre_id', flat=True)
        if not genre_rows:
            continue
        if reaction.reaction == ContentReaction.Reaction.LIKE:
            likes += 1
            delta = LIKE_WEIGHT
        else:
            dislikes += 1
            delta = DISLIKE_WEIGHT
        for genre_id in genre_rows:
            weights[genre_id] += delta

    positive = {k: v for k, v in weights.items() if v > 0}
    return _normalize_genre_weights(positive), likes, dislikes


def _merge_weight_maps(*maps):
    merged = defaultdict(float)
    for m in maps:
        for gid, w in (m or {}).items():
            try:
                merged[int(gid)] += float(w)
            except (TypeError, ValueError):
                continue
    return _normalize_genre_weights(dict(merged))


def _preference_genre_weights(user):
    profile = UserPreferenceProfile.objects.filter(user=user).first()
    if not profile:
        return {}
    explicit = {}
    for gid in profile.preferred_genre_ids or []:
        try:
            explicit[int(gid)] = 1.0
        except (TypeError, ValueError):
            continue
    explicit = _normalize_genre_weights(explicit)
    parsed = _normalize_genre_weights(profile.genre_weights or {})
    return _merge_weight_maps(explicit, parsed)


def _save_profile_taste_titles(user, habit, genre):
    profile, _ = UserPreferenceProfile.objects.get_or_create(user=user)
    profile.taste_title_habit = habit or ''
    profile.taste_title_genre = genre or ''
    profile.save(update_fields=['taste_title_habit', 'taste_title_genre', 'updated_at'])


def resolve_taste_titles(user):
    today = timezone.localdate()
    analysis = (
        UserTasteAnalysis.objects
        .filter(user=user, analysis_date=today)
        .order_by('-created_at')
        .first()
    )
    if analysis and (analysis.taste_title_habit or analysis.taste_title_genre):
        return {
            'habit': analysis.taste_title_habit,
            'genre': analysis.taste_title_genre,
        }

    pref = UserPreferenceProfile.objects.filter(user=user).first()
    if pref and (pref.taste_title_habit or pref.taste_title_genre):
        return {
            'habit': pref.taste_title_habit,
            'genre': pref.taste_title_genre,
        }
    return {'habit': '', 'genre': ''}


def taste_llm_runs_today(user, today=None):
    today = today or timezone.localdate()
    return UserTasteAnalysis.objects.filter(user=user, analysis_date=today).count()


def can_run_daily_taste_llm(user, today=None):
    return taste_llm_runs_today(user, today) < DAILY_TASTE_LLM_LIMIT


def _taste_meta(user, likes, dislikes, today=None):
    today = today or timezone.localdate()
    runs = taste_llm_runs_today(user, today)
    remaining = max(0, DAILY_TASTE_LLM_LIMIT - runs)
    return {
        'likes': likes,
        'dislikes': dislikes,
        'llm_ran_today': runs > 0,
        'llm_runs_today': runs,
        'llm_runs_remaining': remaining,
        'llm_limit': DAILY_TASTE_LLM_LIMIT,
        'llm_available_today': remaining > 0 and is_configured(),
    }


def run_daily_taste_llm(user, reaction_weights, likes, dislikes, today=None):
    today = today or timezone.localdate()
    if not can_run_daily_taste_llm(user, today):
        existing = (
            UserTasteAnalysis.objects
            .filter(user=user, analysis_date=today)
            .order_by('-created_at')
            .first()
        )
        if existing:
            return existing.genre_weights, existing.llm_summary
        return None, ''

    if not is_configured():
        return None, ''

    pref = UserPreferenceProfile.objects.filter(user=user).first()
    pref_payload = {}
    if pref:
        pref_payload = {
            'monthly_spend_cap': pref.monthly_spend_cap,
            'preferred_genre_ids': pref.preferred_genre_ids,
            'consumption_habits': pref.consumption_habits,
            'platform_criteria': pref.platform_criteria,
            'genre_weights': pref.genre_weights,
            'taste_summary': pref.taste_summary,
        }

    prompt = (
        f'User taste signals for KR OTT personalization.\n'
        f'Likes: {likes}, Dislikes: {dislikes}\n'
        f'Reaction-derived genre weights (TMDB genre id -> weight):\n'
        f'{json.dumps(reaction_weights, ensure_ascii=False)}\n'
        f'Onboarding preference profile:\n'
        f'{json.dumps(pref_payload, ensure_ascii=False)}\n'
        f'Merge into final genre_weights (0.0-1.0 per TMDB genre id). '
        f'Disliked genres should have low/zero weight. '
        f'Provide a one-sentence Korean summary of taste.\n\n'
        f'{taste_titles_prompt_block()}'
    )
    cache_key = f'user_taste:{user.id}:{today.isoformat()}'
    result = get_llm_judgment(
        cache_key, prompt, today,
        LLMJudgmentCache.JudgmentType.USER_TASTE,
        target_id=str(user.id),
        schema_hint=TASTE_LLM_SCHEMA,
    )
    if not result:
        return None, ''

    genre_weights = _normalize_genre_weights(result.get('genre_weights') or {})
    summary = (result.get('summary') or '').strip()
    habit, genre = resolve_taste_titles_from_llm(
        result,
        consumption_habits=(pref.consumption_habits if pref else {}),
        platform_criteria=(pref.platform_criteria if pref else []),
        genre_weights=genre_weights,
    )

    UserTasteAnalysis.objects.create(
        user=user,
        analysis_date=today,
        genre_weights=genre_weights,
        llm_summary=summary,
        taste_title_habit=habit,
        taste_title_genre=genre,
        reaction_like_count=likes,
        reaction_dislike_count=dislikes,
    )
    _save_profile_taste_titles(user, habit, genre)
    return genre_weights, summary


def resolve_user_genre_weights(user, use_llm=True):
    reaction_weights, likes, dislikes = compute_reaction_genre_weights(user)
    pref_weights = _preference_genre_weights(user)
    base = _merge_weight_maps(reaction_weights, pref_weights)

    today = timezone.localdate()
    analysis = (
        UserTasteAnalysis.objects
        .filter(user=user, analysis_date=today)
        .order_by('-created_at')
        .first()
    )
    if analysis:
        merged = _merge_weight_maps(base, analysis.genre_weights)
        return merged, analysis.llm_summary, _taste_meta(user, likes, dislikes, today)

    if use_llm and can_run_daily_taste_llm(user, today):
        llm_weights, summary = run_daily_taste_llm(
            user, reaction_weights, likes, dislikes, today,
        )
        if llm_weights:
            return _merge_weight_maps(base, llm_weights), summary, _taste_meta(user, likes, dislikes, today)

    return base, '', _taste_meta(user, likes, dislikes, today)


def compute_genre_benefit_raw(user_weights, snapshot_date):
    raw = defaultdict(float)
    rows = PlatformGenreStats.objects.filter(snapshot_date=snapshot_date)
    for row in rows:
        w = user_weights.get(row.genre_id, 0.0)
        if w <= 0:
            continue
        raw[row.platform_id] += w * row.title_count
    return dict(raw)


def _user_liked_title_keys(user):
    keys = set()
    for reaction in ContentReaction.objects.filter(
        user=user, reaction=ContentReaction.Reaction.LIKE,
    ).select_related('content'):
        keys.add((reaction.content.tmdb_id, _content_media_type(reaction.content)))
    return keys


def _exclusive_title_keys():
    return set(
        StreamingCache.objects
        .filter(available=True)
        .values('tmdb_id', 'media_type')
        .annotate(n=Count('platform', distinct=True))
        .filter(n=1)
        .values_list('tmdb_id', 'media_type')
    )


def _platform_available_keys(platform_id):
    return set(
        StreamingCache.objects
        .filter(platform_id=platform_id, available=True)
        .values_list('tmdb_id', 'media_type')
    )


def _exclusive_titles_by_platform():
    exclusive_keys = _exclusive_title_keys()
    by_platform = defaultdict(set)
    for row in StreamingCache.objects.filter(available=True).values('platform_id', 'tmdb_id', 'media_type'):
        key = (row['tmdb_id'], row['media_type'])
        if key in exclusive_keys:
            by_platform[row['platform_id']].add(key)
    return by_platform


def _liked_titles_on_platform(user, platform_id, display_map, limit=12):
    available = _platform_available_keys(platform_id)
    if not available:
        return []

    titles = []
    reactions = ContentReaction.objects.filter(
        user=user, reaction=ContentReaction.Reaction.LIKE,
    ).select_related('content')
    for reaction in reactions:
        content = reaction.content
        media_type = _content_media_type(content)
        key = (content.tmdb_id, media_type)
        if key not in available:
            continue
        titles.append(title_payload_from_map(
            content.tmdb_id, media_type, display_map, is_exclusive=False,
        ))

    titles.sort(key=lambda t: (t.get('popularity') or 0, t.get('vote_average') or 0), reverse=True)
    return titles[:limit]


def _exclusive_highlights(platform_id, display_map, limit=8):
    exclusive_keys = _exclusive_titles_by_platform().get(platform_id, set())
    if not exclusive_keys:
        return []

    items = [
        title_payload_from_map(tmdb_id, media_type, display_map, is_exclusive=True)
        for tmdb_id, media_type in exclusive_keys
    ]
    items.sort(key=lambda t: (t.get('popularity') or 0, t.get('vote_average') or 0), reverse=True)
    return items[:limit]


def _collect_display_keys(user, platform_ids, liked, by_platform_exclusive):
    keys = set()
    for pid in platform_ids:
        keys |= (_platform_available_keys(pid) & liked)
        keys |= by_platform_exclusive.get(pid, set())
    return keys


def compute_exclusivity_affinity_raw(user, user_weights):
    liked = _user_liked_title_keys(user)
    by_platform = _exclusive_titles_by_platform()
    raw = defaultdict(float)

    for platform_id, exclusive_keys in by_platform.items():
        matched = liked & exclusive_keys
        score = float(len(matched))
        for tmdb_id, media_type in matched:
            for genre_id in TitleGenres.objects.filter(
                tmdb_id=tmdb_id, media_type=media_type,
            ).values_list('genre_id', flat=True):
                score += user_weights.get(genre_id, 0.0) * 0.5
        raw[platform_id] = score
    return dict(raw)


def _top_genre_matches(user_weights, platform_id, snapshot_date, limit=3):
    rows = PlatformGenreStats.objects.filter(
        platform_id=platform_id, snapshot_date=snapshot_date,
    ).order_by('-title_count')
    scored = []
    for row in rows:
        w = user_weights.get(row.genre_id, 0.0)
        if w <= 0:
            continue
        scored.append({
            'genre_id': row.genre_id,
            'genre_name': GENRE_NAMES.get(row.genre_id, f'Genre {row.genre_id}'),
            'user_weight': round(w, 3),
            'title_count': row.title_count,
            'match_score': round(w * row.title_count, 2),
        })
    scored.sort(key=lambda x: -x['match_score'])
    return scored[:limit]


def _build_platform_reasons(
    platform_name, genre_benefit_norm, exclusivity_norm,
    top_genres, exclusive_liked_count, benchmark_snap,
):
    reasons = []
    if top_genres:
        top = top_genres[0]
        reasons.append(
            f'{top["genre_name"]} 장르 선호도가 높고, {platform_name}에 해당 장르 작품이 '
            f'{top["title_count"]}편 있습니다.'
        )
    if exclusive_liked_count > 0:
        reasons.append(
            f'좋아요한 작품 중 {exclusive_liked_count}편이 {platform_name} 독점작입니다.'
        )
    if benchmark_snap and benchmark_snap.price_score and benchmark_snap.price_score >= 0.6:
        reasons.append(f'{platform_name}은(는) 가격 경쟁력 벤치마크 점수가 높습니다.')
    if genre_benefit_norm >= 0.7:
        reasons.insert(0, f'장르 편익 점수 {genre_benefit_norm:.2f} — 콘텐츠 구성이 취향과 잘 맞습니다.')
    if exclusivity_norm >= 0.5 and exclusive_liked_count == 0:
        reasons.append(f'{platform_name} 독점작 라인업이 취향 장르와 겹칩니다.')
    if not reasons:
        reasons.append(f'{platform_name}의 장르 구성이 취향 프로필과 부분적으로 맞습니다.')
    return reasons[:4]


def _plan_monthly_price(plan):
    price = plan.price or 0
    if plan.billing_period == 'annual':
        return round(price / 12)
    if plan.billing_period == 'weekly':
        return round(price * 52 / 12)
    return price


def _user_existing_monthly_total(user):
    from subscriptions.models import UserSubscription

    total = 0
    for sub in UserSubscription.objects.filter(user=user, is_active=True):
        amount = sub.payment_amount or 0
        if sub.billing_cycle == 'annual':
            total += round(amount / 12)
        elif sub.billing_cycle == 'weekly':
            total += round(amount * 52 / 12)
        else:
            total += amount
    return total


def _min_monthly_plan_by_platform(platform_ids):
    from subscriptions.models import SubscriptionPlan

    result = {}
    for plan in SubscriptionPlan.objects.filter(platform_id__in=platform_ids):
        monthly = _plan_monthly_price(plan)
        pid = plan.platform_id
        if pid not in result or monthly < result[pid]:
            result[pid] = monthly
    return result


def _latest_benchmark_date():
    return (
        PlatformBenchmarkSnapshot.objects
        .order_by('-snapshot_date')
        .values_list('snapshot_date', flat=True)
        .first()
    )


def _personal_score_cache_version(user_id):
    return cache.get(f'personal_score_v:{user_id}', 0)


def invalidate_personal_score_cache(user_id):
    version = _personal_score_cache_version(user_id) + 1
    cache.set(f'personal_score_v:{user_id}', version, None)


def _personal_score_cache_key(user_id, snapshot_date):
    version = _personal_score_cache_version(user_id)
    return f'personal_score:{user_id}:{version}:{snapshot_date}'


def compute_personal_score(user, snapshot_date=None, use_llm=False, skip_cache=False):
    snapshot_date = snapshot_date or _latest_benchmark_date()
    if not snapshot_date:
        return None

    cache_key = _personal_score_cache_key(user.id, snapshot_date.isoformat())
    if not skip_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    user_weights, taste_summary, taste_meta = resolve_user_genre_weights(user, use_llm=use_llm)
    pref = UserPreferenceProfile.objects.filter(user=user).first()
    monthly_spend_cap = pref.monthly_spend_cap if pref else None
    existing_monthly_total = _user_existing_monthly_total(user)

    if not user_weights:
        result = {
            'snapshot_date': snapshot_date.isoformat(),
            'taste_summary': taste_summary,
            'taste_titles': resolve_taste_titles(user),
            'taste_meta': taste_meta,
            'genre_weights': {},
            'platforms': [],
            'monthly_spend_cap': monthly_spend_cap,
            'existing_monthly_total': existing_monthly_total,
            'detail': '좋아요/싫어요 또는 취향 설정이 필요합니다.',
        }
        if not skip_cache:
            cache.set(cache_key, result, PERSONAL_SCORE_CACHE_TTL)
        return result

    genre_raw = compute_genre_benefit_raw(user_weights, snapshot_date)
    exclusivity_raw = compute_exclusivity_affinity_raw(user, user_weights)

    platform_ids = set(genre_raw) | set(exclusivity_raw)
    if not platform_ids:
        platform_ids = set(
            PlatformGenreStats.objects
            .filter(snapshot_date=snapshot_date)
            .values_list('platform_id', flat=True)
            .distinct()
        )

    genre_norm = normalize_scores({pid: genre_raw.get(pid, 0) for pid in platform_ids})
    exclusivity_norm = normalize_scores({pid: exclusivity_raw.get(pid, 0) for pid in platform_ids})

    liked = _user_liked_title_keys(user)
    by_platform_exclusive = _exclusive_titles_by_platform()
    benchmark_map = {
        s.platform_id: s
        for s in PlatformBenchmarkSnapshot.objects.filter(snapshot_date=snapshot_date)
    }
    display_keys = _collect_display_keys(user, platform_ids, liked, by_platform_exclusive)
    display_map = get_title_display_map(display_keys, max_tmdb_fetches=50)
    min_plan_prices = _min_monthly_plan_by_platform(platform_ids)

    platforms_out = []
    for pid in platform_ids:
        platform = Platform.objects.filter(pk=pid).first()
        if not platform:
            continue
        gb = round(genre_norm.get(pid, 0.0), 4)
        ea = round(exclusivity_norm.get(pid, 0.0), 4)
        personal = round((gb + ea) / 2, 4)
        exclusive_liked = len(liked & by_platform_exclusive.get(pid, set()))
        top_genres = _top_genre_matches(user_weights, pid, snapshot_date)
        reasons = _build_platform_reasons(
            platform.name, gb, ea, top_genres, exclusive_liked, benchmark_map.get(pid),
        )
        snap = benchmark_map.get(pid)
        platforms_out.append({
            'platform_id': pid,
            'name': platform.name,
            'icon_url': platform_icon(platform.name),
            'personal_score': personal,
            'genre_benefit_score': gb,
            'exclusivity_affinity_score': ea,
            'exclusive_liked_count': exclusive_liked,
            'top_genres': top_genres,
            'reasons': reasons,
            'benchmark_value_score': snap.value_score if snap else None,
            'min_monthly_plan': min_plan_prices.get(pid),
            'liked_titles': _liked_titles_on_platform(user, pid, display_map),
            'exclusive_highlights': _exclusive_highlights(pid, display_map),
        })

    platforms_out.sort(key=lambda x: -x['personal_score'])

    result = {
        'snapshot_date': snapshot_date.isoformat(),
        'taste_summary': taste_summary,
        'taste_titles': resolve_taste_titles(user),
        'taste_meta': taste_meta,
        'genre_weights': {
            str(k): v for k, v in sorted(user_weights.items(), key=lambda x: -x[1])[:15]
        },
        'monthly_spend_cap': monthly_spend_cap,
        'existing_monthly_total': existing_monthly_total,
        'platforms': platforms_out,
    }
    if not skip_cache:
        cache.set(cache_key, result, PERSONAL_SCORE_CACHE_TTL)
    return result


def parse_onboarding_chat(user, structured_answers, chat_messages=None):
    payload = {
        'structured_answers': structured_answers,
        'chat_messages': chat_messages or [],
    }
    prompt = (
        'Parse this KR OTT onboarding preference input into structured taste data.\n'
        f'Input JSON:\n{json.dumps(payload, ensure_ascii=False)}\n'
        'Map free-text vibes to TMDB genre ids where possible '
        '(28 Action, 18 Drama, 10749 Romance, 16 Animation, 35 Comedy, 27 Horror, '
        '99 Documentary, 878 Sci-Fi, 10751 Family, etc.).\n\n'
        f'{taste_titles_prompt_block()}'
    )
    cache_key = f'onboarding_parse:{user.id}:{hash(json.dumps(payload, sort_keys=True))}'
    result = get_llm_judgment(
        cache_key, prompt, timezone.localdate(),
        LLMJudgmentCache.JudgmentType.ONBOARDING_PARSE,
        target_id=str(user.id),
        schema_hint=ONBOARDING_PARSE_SCHEMA,
    )

    profile, _ = UserPreferenceProfile.objects.get_or_create(user=user)
    if result:
        cap = result.get('monthly_spend_cap')
        if cap is not None:
            try:
                profile.monthly_spend_cap = int(cap)
            except (TypeError, ValueError):
                pass
        profile.preferred_genre_ids = (
            result.get('preferred_genre_ids')
            or structured_answers.get('preferred_genre_ids') or []
        )
        profile.consumption_habits = (
            result.get('consumption_habits')
            or structured_answers.get('consumption_habits') or {}
        )
        profile.platform_criteria = (
            result.get('platform_criteria')
            or structured_answers.get('platform_criteria') or []
        )
        profile.genre_weights = _normalize_genre_weights(result.get('genre_weights') or {})
        profile.taste_summary = result.get('taste_summary') or ''
        habit, genre = resolve_taste_titles_from_llm(
            result,
            consumption_habits=profile.consumption_habits,
            platform_criteria=profile.platform_criteria,
            genre_weights=profile.genre_weights,
        )
        profile.taste_title_habit = habit
        profile.taste_title_genre = genre
    else:
        profile.preferred_genre_ids = structured_answers.get('preferred_genre_ids') or []
        profile.consumption_habits = structured_answers.get('consumption_habits') or {}
        profile.platform_criteria = structured_answers.get('platform_criteria') or []
        cap = structured_answers.get('monthly_spend_cap')
        if cap is not None:
            profile.monthly_spend_cap = int(cap)
        habit, genre = fallback_taste_titles(
            consumption_habits=profile.consumption_habits,
            platform_criteria=profile.platform_criteria,
            genre_weights=_preference_genre_weights(user),
        )
        profile.taste_title_habit = habit
        profile.taste_title_genre = genre

    profile.onboarding_chat_completed = True
    profile.save()

    UserTasteAnalysis.objects.filter(
        user=user, analysis_date=timezone.localdate(),
    ).delete()

    if chat_messages:
        session = UserPreferenceChatSession.objects.create(user=user, messages=chat_messages)
        session.completed_at = timezone.now()
        session.save(update_fields=['completed_at'])

    return profile
