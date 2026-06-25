"""Demo activity seed: users, community, platform reviews, content reactions."""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import UserPreferenceProfile
from community.models import (
    CommunityComment,
    CommunityPost,
    CommunityPostReaction,
    CommunityCommentReaction,
    Reaction,
)
from contents.models import (
    Content,
    ContentReaction,
    PlatformUserReview,
    PlatformUserReviewComment,
    PlatformUserReviewReaction,
    TitleMeta,
)
from subscriptions.models import Platform, SubscriptionPlan, UserSubscription

User = get_user_model()

DEMO_PASSWORD = 'demo1234'
DEMO_AVATARS = [f'/img/avatars/avatar-3d-{index:02d}.png' for index in range(1, 10)]
DEMO_USER_SPECS = [
    ('demo_netflix_fan', '넷플릭스덕', 'netflix@demo.local'),
    ('demo_tving_lover', '티빙러버', 'tving@demo.local'),
    ('demo_movie_buff', '영화매니아', 'movie@demo.local'),
    ('demo_family', '가족시청', 'family@demo.local'),
    ('demo_deal_hunter', '가성비러', 'deal@demo.local'),
    ('demo_cinephile', '시네필', 'cine@demo.local'),
    ('demo_drama_queen', '드라마퀸', 'drama@demo.local'),
    ('demo_anime_kid', '애니덕후', 'anime@demo.local'),
]

OTT_PLATFORM_NAMES = [
    'Netflix', 'Disney+', 'Apple TV+', 'TVING', 'Wavve',
    'Watcha', 'Coupang Play', 'Amazon Prime Video',
]

NOTICE_POSTS = [
    (
        'WhatSub 베타 오픈 안내',
        'WhatSub 베타 서비스가 시작되었습니다. OTT 벤치마크, 맞춤 추천, 구독 관리 기능을 '
        '자유롭게 이용해 보시고 커뮤니티에 의견 남겨 주세요. 불편 사항은 OTT 게시판에 적어 주시면 '
        '빠르게 개선하겠습니다.',
    ),
    (
        '6월 벤치마크 스냅샷 업데이트',
        'Netflix·Disney+·TVING 등 주요 8개 플랫폼의 최신 벤치마크 스냅샷을 반영했습니다. '
        '「나에게 맞는 OTT」 탭에서 취향 기반 순위도 함께 확인해 보세요.',
    ),
]

OTT_POSTS = [
    ('Netflix', None, '넷플릭스 광고형 요금제, 3개월 써본 솔직 후기',
     '광고형으로 내렸더니 월 5,500원 절약됩니다. 다만 영화 시작 전 15초 광고는 '
     '아직 적응 중이에요. 드라마 정주행 위주면 충분히 만족합니다.'),
    ('Netflix', None, '넷플릭스 5월 신작 중에 이건 꼭 보세요',
     '「폭군의 셰프」랑 「살인자ㅇ난강」 둘 다 속도감 좋아요. '
     '주말에 밀어둔 목록 비우기 좋았습니다.'),
    ('Disney+', None, '디즈니+ 마블 정주행 로드맵 공유합니다',
     'MCU Phase 4부터 다시 보는 중인데 IMAX 버전 있는 타이틀 위주로 골라봤어요. '
     '아이랑 주말에 보기 좋은 타이틀도 많아서 가족 구독 유지 중입니다.'),
    ('TVING', None, '티빙 T4U vs 넷플릭스, 예능만 본다면?',
     '예능·예능 클립 소비만 보면 티빙이 훨씬 낫더라고요. '
     '특히 신규 예능 업데이트 속도는 티빙 압승입니다.'),
    ('Wavve', None, 'wavve 스포츠+드라마 패키지 가성비',
     'KBL·K리그 보는 분들 wavve 스포츠 패키지 진짜 괜찮아요. '
     '드라마까지 같이 보면 월 구독료 대비 만족도 높습니다.'),
    ('Watcha', None, '왓챠 독립·예술 영화 추천 5편',
     '메인스트림 OTT에 없는 작품들 많아요. 이번 주말에 '
     '「Perfect Days」 다시 봤는데 여전히 좋네요.'),
    ('Coupang Play', None, '쿠팡 와우 + 쿠팡플레이 번들 후기',
     '배송 자주 쓰면 사실상 OTT 공짜에 가깝습니다. '
     '스포츠 중계 품질은 TVING·SPOTV랑 비교해봐야 할 듯.'),
    ('Amazon Prime Video', None, '프라임 비디오 오리지널, 한국에서도 볼만한가?',
     '「Reacher」 시즌3 보고 왔습니다. 액션물 좋아하시면 프라임만 따로 '
     '빼서 보는 것도 나쁘지 않아요. 다만 UI는 솔직히 좀 아쉽…'),
    ('Apple TV+', None, '애플TV+ 3개월 무료 끝나고 유지할지 고민',
     '「Severance」 시즌2 기다리는 중이라 유지는 할 것 같아요. '
     '작품 수는 적지만 퀄리티는 확실합니다.'),
    ('Netflix', None, '넷플릭스 동시접속 4명, 가족 계정 나누기 팁',
     '프로필 5개 + PIN 걸어두면 아이 프로필 관리 편해요. '
     '청소년 등급 제한도 꼭 켜두세요.'),
    ('TVING', None, '티빙 라이브 vs wavve 라이브, 지상파 뭐가 나아요?',
     'SBS·KBS 라이브 딜레이는 둘 다 비슷한데 티빙 앱이 조금 더 안정적이었어요.'),
    ('Disney+', None, '디즈니+ 연간권 vs 월간, 계산해 봤습니다',
     '연 99,000원대면 2개월치 정도 이득. '
     '마블·스타워즈 팬이면 연간이 낫습니다.'),
    ('Wavve', None, 'wavve에서 「눈물의 여왕」 재방송 타이밍',
     '재방송·VOD 편성표 보고 들어왔는데 아직도 인기 있네요. '
     '드라마 몰아보기는 wavve가 편했습니다.'),
    ('Watcha', None, '왓챠피디아 평점 믿어도 될까요?',
     '마이너 영화 고를 때는 오히려 왓챠 평점이 도움 됩니다. '
     '다만 표본 적은 작품은 그냥 참고만 하세요.'),
    ('Netflix', 'other', 'OTT 3개 넘으면 번들 없이 관리하는 방법',
     '플랫폼마다 결제일 다르면 캘린더에 다 넣어두세요. '
     'WhatSub 구독 캘린더 쓰니까 갱신일 놓칠 일이 줄었어요.'),
    ('Amazon Prime Video', None, '프라임 + 넷플릭스 병행 중인데 역할 분담',
     '넷플릭스는 드라마·예능, 프라임은 영화·미드 위주로 보고 있습니다.'),
    ('TVING', None, '티빙 「놀뭐」 클립만 봐도 월 요금 값 하는지',
     '출퇴근길에 클립만 봐도 30분은 금방 갑니다. 유튜브 대신 티빙 켜는 날이 많아요.'),
    ('Coupang Play', None, '쿠팡플레이 EPL 중계 화질 후기',
     '4K TV에서 봤을 때 꽤 선명했어요. '
     '와우 멤버십이면 추가 비용 없이 보는 게 최대 장점.'),
]

FREE_POSTS = [
    ('이번 주말 영화 추천해 주세요 (스릴러)', '넷플·왓챠·티빙 중 어디에 스릴러 많은지 궁금합니다. '
     '최근에 「비밀의 숲」 재시청했는데 이런 분위기 좋아요.'),
    ('「시맨틱 에러」 보신 분 계신가요?', 'BL 입문작으로 봤는데 생각보다 감성적이에요. '
     '비슷한 힐링 드라마 추천 부탁드립니다.'),
    ('OTT 동시구독 몇 개까지가 적당하다고 생각하세요?', '저는 3개인데 2개로 줄이고 싶어요. '
     '다들 가성비 조합 공유해 주세요.'),
    ('배우 송강ho 신작 어디서 보나요?', '플랫폼별 편성표 찾기가 너무 힘들어서 여기서 물어봅니다.'),
    ('다큐 좋아하는데 넷플 vs 디즈니+', '자연·과학 다큐 위주로 보면 어디가 라인업 더 좋을까요?'),
    ('아이랑 주말에 볼 가족 영화', '만 7세 아이 기준으로 무서운 장면 없는 거 추천해 주세요.'),
    ('사운드바 샀는데 OTT 영화 추천', 'Atmos 지원 타이틀 위주로 보고 싶어요. 액션 말고 SF도 OK.'),
    ('주말에 「더 글로리」 정주행 끝', '복수극 또 보고 싶은데 비슷한 작품 있을까요?'),
    ('애니는 넷플 vs 왓챠?', '신작 속도·더빙/자막 품질 비교 경험 공유 부탁드려요.'),
    ('WhatSub 벤치마크 점수 어떻게 해석하나요?', '가격 점수랑 독점성 점수 같이 높으면 무조건 추천인가요?'),
]

COMMENT_SAMPLES = [
    '저도 같은 생각이에요.',
    '정보 감사합니다! 바로 확인해 볼게요.',
    '이 조합 괜찮네요. 저는 티빙+넷플 병행 중입니다.',
    '광고형은 저도 2주 만에 적응됐어요.',
    '연간권 계산표 공유 가능할까요?',
    '왓챠는 마이너 영화 찾을 때 진짜 좋더라고요.',
    '쿠팡 와우 쓰면 쿠팡플레이는 거의 필수인 듯…',
    '프라임 UI는 저도 불편…',
    '가족 프로필 PIN 설정 꿀팁이네요.',
    '벤치마크 탭에서 플랫폼별 비교해 보니까 한눈에 보여서 좋았어요.',
    '저는 2개만 유지하려고 WhatSub 계산기 씁니다.',
    '다음 달 신작 편성표 나오면 또 공유해 주세요!',
]

REVIEW_SAMPLES = [
    ('Netflix', 5, '드라마·영화 라인업이 가장 탄탄합니다. UI도 익숙하고 가족 프로필 관리 편해요.'),
    ('Netflix', 4, '가격은 올랐지만 여전히 1티어 OTT. 광고형 도입 이후 가성비는 더 좋아졌어요.'),
    ('Disney+', 4, '마블·픽사·스타워즈 팬이면 필수. 한국 드라마 편성은 조금 아쉽습니다.'),
    ('Disney+', 5, '아이랑 보기 좋은 콘텐츠가 많아서 가족 구독 유지 중입니다.'),
    ('TVING', 5, '국내 예능·드라마는 티빙이 최고예요. 라이브 채널도 자주 씁니다.'),
    ('TVING', 4, '클립·예능 소비만 해도 월 요금 값 합니다. 해외작은 다소 부족.'),
    ('Wavve', 4, '지상파·종편·스포츠까지 한 번에. 드라마 재방송 보기 좋아요.'),
    ('Watcha', 4, '마이너·독립 영화 찾기 최고. 메인 OTT 보조용으로 추천합니다.'),
    ('Coupang Play', 4, '와우 멤버십이면 사실상 공짜에 가깝습니다. EPL 보는 분께 추천.'),
    ('Amazon Prime Video', 3, '작품은 괜찮은데 앱 UX가 아쉬워요. 프라임 혜택으로 끼워 넣기엔 OK.'),
    ('Apple TV+', 4, '작품 수는 적지만 퀄리티 일정. 오리지널만 보면 만족합니다.'),
    ('Apple TV+', 5, '「Severance」「Pachinko」급 작품들 때문에 유지 중입니다.'),
]

REVIEW_COMMENTS = [
    '공감합니다. 저도 같은 이유로 유지해요.',
    '저는 해외작 비중이 아쉬워서 이번 달 해지 예정이에요.',
    '와우 번들이면 쿠팡플레이는 진짜 가성비 최고…',
    '벤치마크 점수랑 비슷하게 느껴지네요.',
]


def _days_ago(days, hours=0):
    return timezone.now() - timedelta(days=days, hours=hours)


def _platform_map():
    return {p.name: p for p in Platform.objects.filter(name__in=OTT_PLATFORM_NAMES)}


class Command(BaseCommand):
    help = 'Seed demo users and activity (community, reviews, reactions) for presentations.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo_* users and recreate all demo activity.',
        )
        parser.add_argument(
            '--update-avatars',
            action='store_true',
            help='Assign default avatar presets to demo_* users only.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['update_avatars']:
            self._ensure_users()
            self.stdout.write(self.style.SUCCESS('Updated demo user avatars.'))
            return

        if options['reset']:
            deleted, _ = User.objects.filter(username__startswith='demo_').delete()
            self.stdout.write(f'Removed demo users ({deleted} related rows).')

        if User.objects.filter(username='demo_netflix_fan').exists() and not options['reset']:
            self.stdout.write(self.style.WARNING('Demo data already exists. Use --reset to recreate.'))
            return

        if not Platform.objects.exists():
            self.stdout.write(self.style.ERROR('Load subscriptions catalog first (load_seed_data.sh).'))
            return

        users = self._ensure_users()
        admin = User.objects.filter(username='admin', is_staff=True).first()
        platforms = _platform_map()

        posts = self._seed_community(users, platforms, admin)
        self._seed_community_engagement(users, posts)
        reviews = self._seed_platform_reviews(users, platforms)
        self._seed_review_engagement(users, reviews)
        content_count = self._seed_content_reactions(users)
        sub_count = self._seed_subscriptions(users, platforms)
        pref_count = self._seed_preference_profiles(users)

        self.stdout.write(self.style.SUCCESS(
            f'Demo seed complete: {len(users)} users, {len(posts)} posts, '
            f'{len(reviews)} platform reviews, {content_count} content reactions, '
            f'{sub_count} subscriptions, {pref_count} taste profiles. '
            f'Demo password: {DEMO_PASSWORD}',
        ))

    def _ensure_users(self):
        users = {}
        for idx, (username, nickname, email) in enumerate(DEMO_USER_SPECS):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'nickname': nickname, 'email': email, 'is_active': True},
            )
            if not created and user.nickname != nickname:
                user.nickname = nickname
            user.profile_image = DEMO_AVATARS[idx % len(DEMO_AVATARS)]
            user.set_password(DEMO_PASSWORD)
            user.save()
            users[username] = user
        return users

    def _seed_community(self, users, platforms, admin):
        posts = []
        author_cycle = list(users.values())

        for idx, (title, content) in enumerate(NOTICE_POSTS):
            author = admin or author_cycle[0]
            post = CommunityPost.objects.create(
                board=CommunityPost.Board.NOTICE,
                title=title,
                content=content,
                author=author,
                view_count=320 + idx * 45,
            )
            CommunityPost.objects.filter(pk=post.pk).update(created_at=_days_ago(14 - idx, 2))
            posts.append(post)

        for idx, (platform_name, flair_tag, title, content) in enumerate(OTT_POSTS):
            author = author_cycle[idx % len(author_cycle)]
            platform = platforms.get(platform_name)
            post = CommunityPost.objects.create(
                board=CommunityPost.Board.OTT,
                title=title,
                content=content,
                author=author,
                platform=platform,
                flair_tag=flair_tag or '',
                view_count=random.randint(28, 280),
            )
            CommunityPost.objects.filter(pk=post.pk).update(
                created_at=_days_ago(random.randint(0, 12), random.randint(0, 10)),
            )
            posts.append(post)

        for idx, (title, content) in enumerate(FREE_POSTS):
            author = author_cycle[(idx + 2) % len(author_cycle)]
            post = CommunityPost.objects.create(
                board=CommunityPost.Board.FREE,
                title=title,
                content=content,
                author=author,
                view_count=random.randint(15, 120),
            )
            CommunityPost.objects.filter(pk=post.pk).update(
                created_at=_days_ago(random.randint(0, 10), random.randint(0, 8)),
            )
            posts.append(post)

        return posts

    def _seed_community_engagement(self, users, posts):
        user_list = list(users.values())
        comment_count = 0
        for post in posts:
            if post.board == CommunityPost.Board.NOTICE:
                continue
            n_comments = random.randint(1, 4)
            for c_idx in range(n_comments):
                author = user_list[(post.pk + c_idx) % len(user_list)]
                if author.pk == post.author_id:
                    author = user_list[(c_idx + 1) % len(user_list)]
                comment = CommunityComment.objects.create(
                    post=post,
                    author=author,
                    content=random.choice(COMMENT_SAMPLES),
                )
                CommunityComment.objects.filter(pk=comment.pk).update(
                    created_at=post.created_at + timedelta(hours=2 + c_idx),
                )
                comment_count += 1
                if random.random() < 0.5:
                    reactor = user_list[(post.pk + c_idx + 2) % len(user_list)]
                    if reactor.pk != comment.author_id:
                        CommunityCommentReaction.objects.get_or_create(
                            comment=comment,
                            user=reactor,
                            defaults={'reaction': Reaction.LIKE},
                        )

            reactors = random.sample(user_list, k=min(random.randint(2, 5), len(user_list)))
            for reactor in reactors:
                if reactor.pk == post.author_id:
                    continue
                CommunityPostReaction.objects.get_or_create(
                    post=post,
                    user=reactor,
                    defaults={'reaction': Reaction.LIKE if random.random() > 0.15 else Reaction.DISLIKE},
                )

        return comment_count

    def _seed_platform_reviews(self, users, platforms):
        reviews = []
        user_list = list(users.values())
        for idx, (platform_name, score, body) in enumerate(REVIEW_SAMPLES):
            platform = platforms.get(platform_name)
            if not platform:
                continue
            author = user_list[idx % len(user_list)]
            review, _ = PlatformUserReview.objects.update_or_create(
                platform=platform,
                user=author,
                defaults={'score': score, 'body': body},
            )
            PlatformUserReview.objects.filter(pk=review.pk).update(
                created_at=_days_ago(random.randint(1, 20)),
            )
            reviews.append(review)
        return reviews

    def _seed_review_engagement(self, users, reviews):
        user_list = list(users.values())
        for review in reviews:
            for c_idx in range(random.randint(0, 2)):
                author = user_list[(review.pk + c_idx) % len(user_list)]
                if author.pk == review.user_id:
                    continue
                comment = PlatformUserReviewComment.objects.create(
                    review=review,
                    author=author,
                    content=random.choice(REVIEW_COMMENTS),
                )
                PlatformUserReviewComment.objects.filter(pk=comment.pk).update(
                    created_at=review.created_at + timedelta(hours=1 + c_idx),
                )
            for reactor in random.sample(user_list, k=min(3, len(user_list))):
                if reactor.pk == review.user_id:
                    continue
                PlatformUserReviewReaction.objects.get_or_create(
                    review=review,
                    user=reactor,
                    defaults={'reaction': PlatformUserReviewReaction.Reaction.LIKE},
                )

    def _seed_content_reactions(self, users):
        titles = list(
            TitleMeta.objects.exclude(title='').order_by('-vote_average', '-popularity')[:20],
        )
        if len(titles) < 5:
            titles = list(TitleMeta.objects.order_by('-vote_average')[:20])
        if not titles:
            self.stdout.write(self.style.WARNING('No TitleMeta rows — skip content reactions.'))
            return 0

        user_list = list(users.values())
        count = 0
        for idx, meta in enumerate(titles[:18]):
            title = meta.title or f'TMDB #{meta.tmdb_id}'
            content, _ = Content.objects.get_or_create(
                tmdb_id=meta.tmdb_id,
                defaults={
                    'title': title,
                    'korean_title': title,
                    'content_type': meta.media_type,
                    'rating': meta.vote_average,
                    'poster_url': meta.poster_url or '',
                },
            )
            for user in random.sample(user_list, k=min(random.randint(2, 4), len(user_list))):
                reaction = ContentReaction.Reaction.LIKE if random.random() > 0.2 else ContentReaction.Reaction.DISLIKE
                _, created = ContentReaction.objects.get_or_create(
                    content=content,
                    user=user,
                    defaults={'reaction': reaction},
                )
                if created:
                    count += 1
        return count

    def _seed_subscriptions(self, users, platforms):
        specs = [
            ('demo_netflix_fan', 'Netflix'),
            ('demo_tving_lover', 'TVING'),
            ('demo_movie_buff', 'Watcha'),
            ('demo_family', 'Disney+'),
            ('demo_deal_hunter', 'Coupang Play'),
            ('demo_cinephile', 'Apple TV+'),
        ]
        today = timezone.localdate()
        count = 0
        for username, platform_name in specs:
            user = users.get(username)
            platform = platforms.get(platform_name)
            if not user or not platform:
                continue
            plan = SubscriptionPlan.objects.filter(platform=platform).order_by('price').first()
            plan_name = plan.plan_name if plan else f'{platform_name} 기본'
            amount = plan.price if plan else 9900
            UserSubscription.objects.update_or_create(
                user=user,
                platform=platform,
                defaults={
                    'plan': plan,
                    'plan_name': plan_name,
                    'payment_amount': amount,
                    'billing_cycle': 'monthly',
                    'payment_method': 'card',
                    'start_date': today - timedelta(days=90),
                    'renewal_date': today + timedelta(days=random.randint(3, 25)),
                    'auto_renew': True,
                    'is_active': True,
                },
            )
            count += 1
        return count

    def _seed_preference_profiles(self, users):
        specs = [
            ('demo_netflix_fan', [18, 10749, 35], {'28': 0.9, '18': 0.7, '35': 0.5}),
            ('demo_tving_lover', [10751, 35, 99], {'35': 0.85, '10751': 0.8}),
            ('demo_cinephile', [18, 99, 36], {'18': 0.95, '99': 0.8, '36': 0.6}),
            ('demo_anime_kid', [16, 878, 28], {'16': 1.0, '878': 0.7}),
        ]
        count = 0
        for username, genre_ids, genre_weights in specs:
            user = users.get(username)
            if not user:
                continue
            UserPreferenceProfile.objects.update_or_create(
                user=user,
                defaults={
                    'monthly_spend_cap': random.choice([30000, 45000, 55000]),
                    'preferred_genre_ids': genre_ids,
                    'consumption_habits': {'binge': True, 'family': username == 'demo_family'},
                    'platform_criteria': ['price', 'exclusives'],
                    'genre_weights': genre_weights,
                    'taste_summary': f'{user.nickname}님의 시연용 취향 프로필입니다.',
                    'onboarding_chat_completed': True,
                },
            )
            count += 1
        return count

    def _seed_preference_profiles(self, users):
        specs = [
            ('demo_netflix_fan', [18, 10749, 35], {'28': 0.9, '18': 0.7, '35': 0.5}),
            ('demo_tving_lover', [10751, 35, 99], {'35': 0.85, '10751': 0.8}),
            ('demo_cinephile', [18, 99, 36], {'18': 0.95, '99': 0.8, '36': 0.6}),
            ('demo_anime_kid', [16, 878, 28], {'16': 1.0, '878': 0.7}),
        ]
        count = 0
        for username, genre_ids, genre_weights in specs:
            user = users.get(username)
            if not user:
                continue
            UserPreferenceProfile.objects.update_or_create(
                user=user,
                defaults={
                    'monthly_spend_cap': random.choice([30000, 45000, 55000]),
                    'preferred_genre_ids': genre_ids,
                    'consumption_habits': {'binge': True, 'family': username == 'demo_family'},
                    'platform_criteria': ['price', 'exclusives'],
                    'genre_weights': genre_weights,
                    'taste_summary': f'{user.nickname}님의 시연용 취향 프로필입니다.',
                    'onboarding_chat_completed': True,
                },
            )
            count += 1
        return count
