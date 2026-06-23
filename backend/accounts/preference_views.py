"""Onboarding preference chat API."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserPreferenceProfile
from contents.personal_scoring import parse_onboarding_chat

PREFERENCE_QUESTIONS = [
    {
        'id': 'monthly_spend_cap',
        'type': 'number',
        'label': '월 OTT 구독 예산 상한',
        'description': '매달 스트리밍·OTT에 쓰고 싶은 최대 금액(원)을 알려주세요.',
        'placeholder': '예: 30000',
        'required': False,
    },
    {
        'id': 'preferred_genre_ids',
        'type': 'genre_multi',
        'label': '선호하는 장르',
        'description': '자주 보는 장르를 골라주세요. (복수 선택)',
        'required': False,
    },
    {
        'id': 'consumption_habits',
        'type': 'habits',
        'label': '구독 소비 습관',
        'description': '해당되는 항목을 선택해주세요.',
        'options': [
            {'key': 'binge', 'label': '주말/휴일에 몰아보기'},
            {'key': 'family', 'label': '가족과 함께 시청'},
            {'key': 'late_night', 'label': '밤늦게 혼자 시청'},
            {'key': 'documentary_heavy', 'label': '다큐·교양 위주'},
        ],
        'required': False,
    },
    {
        'id': 'platform_criteria',
        'type': 'criteria_multi',
        'label': '플랫폼 선택 기준',
        'description': '구독할 때 중요하게 보는 기준을 골라주세요.',
        'options': [
            {'key': 'price', 'label': '가격·가성비'},
            {'key': 'exclusives', 'label': '독점작·오리지널'},
            {'key': 'quality', 'label': '화질·사운드'},
            {'key': 'kids', 'label': '키즈·가족 콘텐츠'},
            {'key': 'kcontent', 'label': '한국 콘텐츠'},
            {'key': 'global', 'label': '해외 드라마·영화'},
        ],
        'required': False,
    },
    {
        'id': 'free_text',
        'type': 'textarea',
        'label': '추가로 알려주고 싶은 취향',
        'description': '최근 재밌게 본 작품, 분위기, 피하고 싶은 장르 등 자유롭게 적어주세요.',
        'placeholder': '예: SF랑 스릴러 좋아하고, 로코는 별로예요.',
        'required': False,
    },
]

GENRE_OPTIONS = [
    {'id': 28, 'name': 'Action'}, {'id': 18, 'name': 'Drama'}, {'id': 10749, 'name': 'Romance'},
    {'id': 35, 'name': 'Comedy'}, {'id': 16, 'name': 'Animation'}, {'id': 27, 'name': 'Horror'},
    {'id': 878, 'name': 'Sci-Fi'}, {'id': 99, 'name': 'Documentary'}, {'id': 10751, 'name': 'Family'},
    {'id': 9648, 'name': 'Mystery'}, {'id': 53, 'name': 'Thriller'}, {'id': 10765, 'name': 'Sci-Fi & Fantasy'},
]


def _profile_payload(profile):
    if not profile:
        return None
    return {
        'monthly_spend_cap': profile.monthly_spend_cap,
        'preferred_genre_ids': profile.preferred_genre_ids,
        'consumption_habits': profile.consumption_habits,
        'platform_criteria': profile.platform_criteria,
        'genre_weights': profile.genre_weights,
        'taste_summary': profile.taste_summary,
        'onboarding_chat_completed': profile.onboarding_chat_completed,
        'updated_at': profile.updated_at.isoformat() if profile.updated_at else None,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def preference_questions(request):
    return Response({
        'questions': PREFERENCE_QUESTIONS,
        'genre_options': GENRE_OPTIONS,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def preference_profile(request):
    profile = UserPreferenceProfile.objects.filter(user=request.user).first()
    return Response({'profile': _profile_payload(profile)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preference_complete(request):
    """
    Submit structured onboarding answers (+ optional chat transcript).
    Body: { structured_answers: {...}, chat_messages: [{role, content}] }
    """
    structured = request.data.get('structured_answers') or request.data
    chat_messages = request.data.get('chat_messages') or []

    if not structured and not chat_messages:
        return Response({'detail': '취향 정보가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

    profile = parse_onboarding_chat(request.user, structured, chat_messages)
    return Response({'profile': _profile_payload(profile)})
