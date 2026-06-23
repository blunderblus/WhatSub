# WhatSub? — Project Context

## Overview

WhatSub? is a subscription management platform that helps users track their recurring subscriptions, discover streaming content, and maximize the value they get from their services.

Unlike traditional subscription trackers, WhatSub? combines:

- Subscription management
- Streaming content discovery
- Personalized platform recommendations
- Promotion and bundle optimization

into a single ecosystem.

---

## Current MVP Goals

1. Google Login
2. Gmail Inbox Access
3. Automatic Subscription Detection
4. UserSubscription Generation
5. TMDB-based Content Search
6. Streaming Platform Availability Lookup
7. Personalized Subscription Dashboard

The primary objective is to automate subscription discovery and management with minimal manual input from the user.

---

## Core Features

### 1. Gmail-Based Subscription Detection

During onboarding, users connect their Gmail account. The system scans the inbox to identify subscription-related payment records and automatically builds an initial subscription profile.

**Target services include (but are not limited to):**
- Netflix, Disney+, Tving, Wavve, Watcha
- YouTube Premium, Spotify
- ChatGPT Plus
- Coupang WOW, Baemin Club
- Apple Services, Google One

#### Pipeline

```
Gmail Inbox Access
  → Email Metadata Collection
    → Rule-Based Filtering
      → Deduplication
        → LLM-Based Extraction
          → UserSubscription Generation
```

#### Rule-Based Filtering

Before invoking the LLM, potential subscription emails are identified using:

**Keywords:**
payment, purchase, membership, premium, subscription, renewal, invoice, receipt,
결제, 구매, 구독, 멤버십, 정기결제

**Known Service Names:**
Netflix, Disney, Spotify, Apple, Google, OpenAI, Coupang, Baemin, Tving, Wavve

**Payment Processors:**
NHN KCP, KG Inicis, Toss Payments, KakaoPay, Naver Pay

#### Gmail Search Filters (to be evaluated)
- `category:purchases`
- `newer_than:1m`
- `has:attachment`

#### Deduplication Criteria
- Same sender
- Same platform
- Similar subject line
- Similar payment amount
- Close timestamps

#### LLM Extraction Output Schema

```json
{
  "platform": "Netflix",
  "plan_name": "Standard",
  "payment_amount": 13500,
  "billing_cycle": "monthly",
  "renewal_date": "2026-06-15"
}
```

---

### 2. Streaming Content Discovery

Similar to JustWatch and Letterboxd, but focused on subscription optimization rather than social interaction.

**Features:**
- Movie and TV show search
- Platform availability lookup (subscription / rent / buy / free)
- Personalized content recommendations

---

### 3. User Preferences

Users can like movies and TV shows to build a preference profile.

**Tracked dimensions:**
- Genre preference
- Runtime preference
- Language preference
- Platform preference

---

### 4. Platform Benchmark & Leaderboard (Killer Feature)

#### Value Score Formula (5 Axes)

```
Value Score =
  Availability Score    (quantitative)
+ Exclusivity Score      (quantitative + LLM-adjusted)
+ Overall Quality Score  (quantitative, asymmetric)
+ Price Score            (quantitative + LLM-judged)
+ Accessibility Score    (DB-managed, static)
```

> Weighting between axes is TBD pending UX testing. Each axis is normalized (0.0–1.0) independently before combination.

#### Axis Definitions

| Axis | Question | Source |
|---|---|---|
| Availability | How many titles are available on the platform? | StreamingCache aggregation |
| Exclusivity | How many exclusive titles, and how trending/notable are they? | StreamingCache + TMDB metadata + LLM trending weight |
| Overall Quality | Does the platform have many high-quality titles? (bad titles must NOT drag down the score) | TMDB metadata, threshold-based, asymmetric |
| Price | How many promos/bundles exist, and how many plans are genuinely beneficial to viewers? | SubscriptionPlan/AddOnPass/BundleContent + LLM judgment |
| Accessibility | Streaming quality, simultaneous streams, downloads, devices | DB-managed static table (unchanged from prior design) |

---

#### Availability Score

Computed from `StreamingCache` (see API Strategy section — built organically from per-title Watchmode lookups, cold-start warmed via TMDB popular titles).

```python
SELECT platform, COUNT(DISTINCT tmdb_id) AS total_titles
FROM streaming_cache
WHERE available = True
GROUP BY platform
```

```python
availability_score = normalize(total_titles_per_platform)
```

---

#### Exclusivity Score

A title is "exclusive" if it is observed on exactly one platform within `StreamingCache`. Raw exclusive count alone is insufficient — exclusivity should be weighted by how notable/trending the exclusive titles are.

```python
SELECT sc.tmdb_id, sc.platform, t.vote_average, t.popularity
FROM streaming_cache sc
JOIN title_meta t ON sc.tmdb_id = t.tmdb_id
WHERE sc.tmdb_id IN (
    SELECT tmdb_id FROM streaming_cache
    WHERE available = True
    GROUP BY tmdb_id
    HAVING COUNT(DISTINCT platform) = 1
)
```

```python
exclusivity_score = (
    normalize(exclusive_title_count) * 0.4
    + normalize(avg_popularity_of_exclusives) * 0.6
)
```

**LLM-adjusted trending weight:** TMDB `popularity`/`vote_average` don't fully capture cultural buzz (e.g., recent word-of-mouth, awards). An LLM call (batched per platform, cached, `temperature=0`) assigns a `trending_weight` (0.0–1.0) per exclusive title without re-judging the underlying rating/popularity numbers themselves.

```python
exclusivity_score = sum(
    title.popularity_normalized * title.trending_weight
    for title in exclusive_titles
)
```

> Caveat: "exclusive" here means "exclusive within our observed cache," not verified global exclusivity. Treat as low-confidence until cache coverage grows; expose a `confidence_level` field alongside the score.

---

#### Overall Quality Score (Asymmetric)

**Requirement:** A platform with many great titles AND many bad titles must not be penalized for the bad ones. Simple averaging (`AVG(vote_average)`) violates this, since poor titles drag the mean down.

**Solution:** Count high-quality titles only — poor titles simply don't contribute, they never subtract.

```python
QUALITY_THRESHOLD = 7.0
MIN_VOTE_COUNT = 500  # filter out noisy low-vote-count titles

SELECT platform, COUNT(*) AS quality_title_count
FROM streaming_cache sc
JOIN title_meta t ON sc.tmdb_id = t.tmdb_id
WHERE sc.available = True
  AND t.vote_average >= 7.0
  AND t.vote_count >= 500
GROUP BY platform
```

```python
quality_score = normalize(quality_title_count)
```

> Use absolute count, not ratio (quality_count / total_count) — ratio would unfairly favor small, low-volume platforms. Quantity is already captured separately by Availability Score.

> Future refinement (not implemented yet): genre-specific quality thresholds (documentaries skew lower on vote_average than blockbusters). If pursued, generate thresholds via a one-time LLM proposal and hardcode the result — do not re-judge per batch run, to avoid score drift between snapshots.

---

#### Price Score

Two components:
1. **Bundle/promo count** — purely quantitative
2. **"Genuinely beneficial" plan count** — requires contextual judgment (e.g., Coupang WOW bundles streaming with free shipping; TVING affiliate pricing requires a specific card/carrier) — delegated to LLM

```python
bundle_count = SubscriptionPlan.objects.filter(
    platform=platform, is_bundle=True
).count()
```

LLM judgment (batched per platform, cached, `temperature=0`, structured output only):

```
Given this platform's plans and bundle/affiliate offers (price, specs, eligibility conditions),
judge whether each plan is "genuinely beneficial" to an average consumer.
Consider: price-to-spec ratio, feasibility of eligibility conditions
(e.g. requiring a specific card/carrier), relative competitiveness vs. other platforms.
Return strict JSON: [{plan_id, is_beneficial: bool, reason: string}]
```

```python
price_score = (
    normalize(bundle_count) * 0.3
    + normalize(beneficial_plan_count) * 0.7
)
```

---

#### Accessibility Score

Unchanged — derived from the static `SubscriptionPlan` fields (`max_streams`, `max_quality`, `has_download`, device count). Manually maintained; see **Platform Data Model**.

---

#### LLM Judgment Layer — Design Principles

LLM is used only where contextual/qualitative judgment is required — not as a substitute for computable metrics. Applies the same caching discipline as the BL project's news-sentiment pipeline (content-hash idempotent cache, `temperature=0`, structured output, point-in-time cutoffs where relevant).

```python
def get_llm_judgment(cache_key, prompt, schema):
    cached = db.get(f"llm_judgment:{cache_key}")
    if cached:
        return cached
    response = gemini_api.call(prompt=prompt, temperature=0, response_schema=schema)
    db.set(f"llm_judgment:{cache_key}", response, ttl=None)  # persists until next batch snapshot
    return response
```

New model:

```python
LLMJudgmentCache(
    id,
    cache_key,       # unique, e.g. f"{platform}_{snapshot_date}_exclusivity"
    judgment_type,   # "exclusivity_weight" | "price_beneficial"
    target_id,       # tmdb_id or plan_id
    result_json,     # structured LLM output, stored as-is
    snapshot_date,
)
```

**Estimated cost:** 8 platforms × 2 judgment types × weekly batch ≈ 16 calls/week (lists batched per platform, not per title/plan). Negligible on Gemini Flash-Lite.

---

#### Genre Distribution (for Pie Charts & Personal Score)

Genre aggregation uses **TMDB genre IDs** as the canonical taxonomy (e.g. Action=28, Romance=10749, Animation=16) so that genre stats are standardized across platforms and reusable for both benchmark pie charts and Personal Score.

```python
SELECT sc.platform, tg.genre_id, COUNT(*) AS title_count
FROM streaming_cache sc
JOIN title_genres tg ON sc.tmdb_id = tg.tmdb_id
WHERE sc.available = True
GROUP BY sc.platform, tg.genre_id
```

Stored in `PlatformGenreStats` (see below). Genre name lookup uses TMDB's static genre list (`/genre/movie/list`, `/genre/tv/list`) cached locally — no need to re-fetch per request.

---

#### Pipeline Overview

```
[Cold start — one-time/low-frequency]
  TMDB /discover popular titles
    → warm StreamingCache + title_meta

[Continuous — on every user search]
  Watchmode lookup → StreamingCache (tmdb_id, platform, available, checked_at)
  TMDB title metadata → title_meta (vote_average, vote_count, popularity)
  TMDB genre mapping → title_genres (tmdb_id, genre_id)

[Weekly batch — management command]
  Aggregate StreamingCache + title_meta + title_genres
    → Availability Score
    → Exclusivity Score (+ LLM trending weight)
    → Quality Score (asymmetric, threshold-based)
    → PlatformGenreStats (for pie charts + Personal Score)
  Aggregate SubscriptionPlan + BundleContent
    → Price Score (+ LLM beneficial-plan judgment)
  Accessibility Score from static SubscriptionPlan fields
  → Write PlatformBenchmarkSnapshot

[User request]
  → Serve directly from PlatformBenchmarkSnapshot (no live API calls)
```

#### New Models

```python
# Reusable TMDB metadata cache (separate from StreamingCache, which tracks availability)
TitleMeta(
    tmdb_id,
    vote_average,
    vote_count,
    popularity,
    media_type,  # "movie" | "tv"
)

# Genre membership per title (TMDB genre IDs as canonical taxonomy)
TitleGenres(
    tmdb_id,
    genre_id,    # TMDB genre id (e.g. 28=Action, 10749=Romance)
)

# Aggregated genre distribution per platform (drives pie charts + Personal Score)
PlatformGenreStats(
    id,
    platform_id,
    genre_id,
    title_count,
    snapshot_date,
)

# Final benchmark snapshot served to users
PlatformBenchmarkSnapshot(
    id,
    platform_id,
    snapshot_date,
    availability_score,
    exclusivity_score,
    quality_score,
    price_score,
    accessibility_score,
    confidence_level,  # low/medium/high based on cache coverage — shown to user for transparency
    value_score,       # combined score, weighting TBD
)

LLMJudgmentCache(
    id,
    cache_key,
    judgment_type,   # "exclusivity_weight" | "price_beneficial"
    target_id,
    result_json,
    snapshot_date,
)
```

---

### 5. Personal Score (Killer Feature)

Computes how well each platform aligns with an individual user's taste, combining quantitative genre distribution, exclusivity signals, and qualitative "vibe" data (from likes/dislikes and, optionally, free-form preference input — see **Onboarding Preference Chat** below).

#### Inputs

| Signal | Source |
|---|---|
| Genre preference weights | Derived from liked/disliked titles, mapped via TMDB genre IDs |
| Platform genre distribution | `PlatformGenreStats` (see Benchmark section) |
| Exclusivity affinity | Does the user's liked-title genre profile overlap with a platform's exclusive titles? |
| Qualitative preference (optional) | Free-text taste description captured via onboarding chat, interpreted by LLM into genre/style weights |

#### Calculation Logic

```python
# Step 1: Derive user genre weights from liked/disliked titles (TMDB genre IDs)
user_weights = {
    28:    0.3,   # Action
    10749: 0.6,   # Romance
    16:    0.1,   # Animation
}
# Disliked titles can subtract weight or be excluded — exact handling TBD

# Step 2: Fetch platform genre stats (from PlatformGenreStats, same data as benchmark pie charts)
platform_genre_stats = {
    "Netflix": {28: 800,  10749: 1200, 16: 300},
    "Disney+": {28: 1500, 10749: 200,  16: 900},
}

# Step 3: Compute weighted personal score per platform
for platform, genres in platform_genre_stats.items():
    score = sum(user_weights.get(genre_id, 0) * count for genre_id, count in genres.items())
```

Example output:
> "You watch mostly Romance — Netflix has 1,200 Romance titles vs Disney+'s 200. Netflix fits you better."

#### Onboarding Preference Chat (Planned — Not Yet Implemented)

During onboarding, users can optionally have a free-form conversation with an LLM to surface:
- Favorite/recently watched titles
- Preferred platforms
- Preferred genres or "vibes" that are hard to capture via structured like/dislike alone

The LLM parses this conversation into structured genre/style weights (same schema as `user_weights` above) to seed or refine the Personal Score before the user has accumulated enough likes/dislikes for a reliable signal. This is an optional, skippable step — not a hard onboarding requirement.

> Implementation status: design only. No data model, prompt, or pipeline has been built yet.

---

## API Strategy

### TMDB (Primary — Free, Unlimited)

- Content metadata: titles, ratings, posters, genres
- Platform availability via Watch Providers
- Benchmark data via `/discover` endpoint with filters
- Already integrated

### Watchmode (Secondary — 2,500 free requests/month)

- Real-time per-title streaming availability for KR region
- Rental/purchase price data for individual titles
- Caching is mandatory to stay within free tier limits

#### Confirmed KR Region Coverage

Watchmode indexes the following services in South Korea:

**Subscription:**
Netflix, Prime Video, Disney+, Apple TV+, Crunchyroll Premium,
Curiosity Stream, GuideDoc, MUBI, TVING, Watcha, Wavve, Zee5

**Purchase & Rental:**
Plex

> TVING, Watcha, and Wavve are confirmed covered — JustWatch/Kinolights crawling is not required for availability checks.

#### Two-Step Deep Link Strategy

Watchmode provides title-level deep links but not episode-level links.
The recommended approach:

```
Step 1 — Availability check (Watchmode)
  → Confirm title is available on platform X
  → Receive title-level web_url from Watchmode

Step 2 — Episode-level link construction
  → Global services: construct URL from known patterns
  → Korean services: construct URL from known patterns or crawl episode listing
```

Known URL patterns:

```python
EPISODE_URL_PATTERNS = {
    # Global
    "Netflix":   "https://www.netflix.com/watch/{content_id}",
    "Disney+":   "https://www.disneyplus.com/video/{content_id}",
    "Apple TV+": "https://tv.apple.com/movie/{slug}",
    "Prime Video": "https://www.primevideo.com/detail/{content_id}",
    # Korean
    "TVING":  "https://www.tving.com/vod/player/{content_id}",
    "Wavve":  "https://www.wavve.com/player/movie/{content_id}",
    "Watcha": "https://watcha.com/contents/{content_id}",
}
```

Episode-level IDs must be resolved via platform-specific crawling or TMDB external_ids mapping where available.

#### Caching Strategy

```python
# Cache per-title streaming availability for 24 hours
def get_streaming_sources(tmdb_id):
    cached = db.get(f"streaming:{tmdb_id}")
    if cached:
        return cached  # No API call

    data = watchmode_api.get_sources(tmdb_id, region="KR")
    db.set(f"streaming:{tmdb_id}", data, ttl=86400)
    return data
```

With 50 DAU, real unique title lookups per day ≈ 30–50.
Estimated monthly API calls: ~900–1,500 (within 2,500 free tier).

### Benchmark Data Refresh (Batch Job — Weekly)

See **Pipeline Overview** under Platform Benchmark & Leaderboard for the full weekly batch flow (Availability, Exclusivity, Quality, Price, Genre Distribution).

---

## TMDB Integration

TMDB is the primary content metadata provider.

**Current usage:**
- Movie and TV metadata
- Posters, backdrops, ratings
- Watch Providers (streaming availability)

**Known Limitation:**

TMDB Watch Provider data for Korean domestic services is incomplete or outdated.

Affected services: TVING, Wavve, Watcha

**Mitigation:**
Watchmode (KR region) covers TVING, Watcha, and Wavve directly.
Use Watchmode as the source of truth for per-title availability on Korean services.
TMDB Watch Providers are used only for benchmark batch stats (content quantity/quality scoring), where minor gaps are acceptable.

---

## Platform Data Model

Flat dictionaries cannot represent the complexity of real-world streaming plans (e.g., Coupang Play's regular vs. Wow member pricing, add-on passes with tiered pricing). A relational model is required.

### Schema

```python
# Core platform entity
Platform(
    id,
    name,           # "Netflix", "Coupang Play", ...
    logo_url,
    website_url,
    country,        # "KR", "GLOBAL"
)

# One platform has multiple plans (basic / standard / premium / 일반 / 와우 / ...)
SubscriptionPlan(
    id,
    platform_id,          # FK → Platform
    plan_name,            # "일반", "와우", "Basic", "Standard", "Premium"
    price,                # int (KRW), 0 = free
    billing_period,       # "monthly" | "annual" | "weekly"
    max_streams,          # int
    max_quality,          # "SD" | "HD" | "FHD" | "4K"
    has_download,         # bool
    has_ads,              # bool
    requires_membership,  # FK → SubscriptionPlan (nullable)
                          # e.g. Coupang Play 와우 requires Coupang WOW plan
    is_bundle,            # bool
)

# Services included in a bundle plan (1:N)
BundleContent(
    id,
    plan_id,              # FK → SubscriptionPlan
    included_platform_id, # FK → Platform
    # e.g. Baemin Club plan → includes YouTube Premium
)

# Add-on passes offered by a platform
AddOnPass(
    id,
    platform_id,  # FK → Platform
    pass_name,    # "스포츠 패스", "J PLUS 패스", "Paramount+ 패스", ...
)

# Price of each add-on pass varies by base membership tier
AddOnPassPricing(
    id,
    pass_id,         # FK → AddOnPass
    base_plan_id,    # FK → SubscriptionPlan (nullable = non-member price)
    price,           # int (KRW)
    billing_period,  # "monthly" | "annual"
)
```

### Example: Coupang Play

```
Platform: Coupang Play

SubscriptionPlan:
  일반   price=0,    billing=monthly, max_quality=FHD, max_streams=1, has_ads=True
  와우   price=7890, billing=monthly, max_quality=4K,  max_streams=2, has_ads=False
         requires_membership → Coupang WOW (SubscriptionPlan of Coupang platform)

AddOnPass: 스포츠 패스
  AddOnPassPricing: base_plan=일반 → 16,600원
  AddOnPassPricing: base_plan=와우  →  9,900원

AddOnPass: J PLUS 패스
  AddOnPassPricing: base_plan=일반 → 6,900원
  AddOnPassPricing: base_plan=와우  → 5,500원

AddOnPass: Paramount+ 패스
  AddOnPassPricing: base_plan=일반 → 4,900원
  AddOnPassPricing: base_plan=와우  → 3,300원
```

### Example: Baemin Club (Bundle)

```
Platform: Baemin

SubscriptionPlan:
  배민클럽  price=3990, billing=monthly, is_bundle=True

BundleContent:
  plan=배민클럽 → included_platform=YouTube Premium
```

---

## Bundle Subscription Handling

Many subscriptions bundle multiple services under a single payment.

**Examples:**
- Baemin Club + YouTube Premium
- SKT Universe + YouTube Premium
- TVING + Wavve Bundle
- Coupang WOW + Coupang Play

These are modeled via `SubscriptionPlan.is_bundle = True` and `BundleContent` mapping.
This allows bundle, individual, and mixed subscription portfolios to coexist without data conflicts.

---

## Promotion and Discount Sources

*(Reserved — document approved sources here)*

**Target categories:**
- Carrier promotions (SKT, KT, LG U+)
- OTT bundle packages
- Credit/debit card benefits
- Membership discounts (Naver Plus, Kakao, etc.)

---

## Tech Stack

- **Backend:** Django + Django REST Framework
- **Database:** PostgreSQL (psycopg2)
- **Authentication:** Google OAuth via django-allauth
- **External APIs:** TMDB, Watchmode, Gmail API, Gemini API (LLM judgment + extraction)
- **Environment:** python-dotenv, django-environ
- **Documentation:** drf-yasg (Swagger)

---

## Known Constraints

- Watchmode free tier: 2,500 requests/month — DB caching per title (TTL 24h) is required
- TMDB Watch Provider data for TVING/Wavve/Watcha is incomplete — use Watchmode for per-title availability
- Watchmode does not provide episode-level deep links — URL pattern construction or crawling required for episode linking
- Platform pricing and plan data (SubscriptionPlan, AddOnPass) must be maintained manually — no public API exists
- No public API exists for streaming platform subscription pricing
- LLM judgment calls (exclusivity trending weight, price beneficial-plan judgment) must be cached per snapshot (content-hash or cache_key based) and run at `temperature=0` to avoid score drift between batch runs
- Exclusivity Score is only as reliable as StreamingCache coverage — expose `confidence_level` to avoid overstating low-data platforms