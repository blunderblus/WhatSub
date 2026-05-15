from django.http import JsonResponse

from allauth.socialaccount.models import SocialToken

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from email.header import decode_header, make_header

# Create your views here.

def test_view(request):
    return JsonResponse({
        'message' : 'hello'
    })


def gmail_test(request):

    print(request.user)

    token = SocialToken.objects.filter(
        account__user=request.user
    ).first()

    print(token)

    if token is None:
        return JsonResponse({
            'error': 'token not found'
        })

    return JsonResponse({
        'token': token.token
    })

def gmail_messages(request):

    social_token = SocialToken.objects.filter(
        account__user=request.user
    ).first()

    credentials = Credentials(
        token=social_token.token
    )

    service = build(
        'gmail',
        'v1',
        credentials=credentials
    )

    results = service.users().messages().list(
        userId='me',
        maxResults=10
    ).execute()

    messages = results.get('messages', [])

    return JsonResponse({
        'messages': messages
    })


KEYWORDS = [
    'Netflix',
    'Amazon Prime',
    'YouTube',
    'Spotify',
    'OpenAI',
    'ChatGPT',
    'Apple',
    'iTunes',
    'Monthly',
    'Weekly',
    'Disney+',
    'Tving',
    '티빙',
    'Wavve',
    'Apple TV+',
    'Coupang Play',
    '배민',
    '쿠팡',
    '결제',
    '청구서',
    '카드',
    '구독',
    '멤버십',
    'Premium',
]



def gmail_detail(request):

    social_token = SocialToken.objects.filter(
        account__user=request.user
    ).first()

    if social_token is None:
        return JsonResponse({
            'error': 'social token not found'
        })

    credentials = Credentials(
        token=social_token.token
    )

    service = build(
        'gmail',
        'v1',
        credentials=credentials
    )

    results = service.users().messages().list(
        userId='me',
        q='newer_than:1m',
        maxResults=100
    ).execute()

    messages = results.get('messages', [])

    email_data = []

    for message in messages:

        msg = service.users().messages().get(
            userId='me',
            id=message['id']
        ).execute()

        headers = msg['payload'].get('headers', [])

        subject = ''
        sender = ''
        date = ''

        for header in headers:

            # 제목
            if header['name'] == 'Subject':

                raw_subject = header['value']

                try:
                    subject = str(
                        make_header(
                            decode_header(raw_subject)
                        )
                    )

                except:
                    subject = raw_subject

            # 발신자
            elif header['name'] == 'From':

                try:
                    sender = str(
                        make_header(
                            decode_header(header['value'])
                        )
                    )

                except:
                    sender = header['value']

            # 날짜
            elif header['name'] == 'Date':
                date = header['value']

        combined_text = f'{subject} {sender}'

        if any(
            keyword.lower() in combined_text.lower()
            for keyword in KEYWORDS
        ):

            email_data.append({
                'subject': subject,
                'sender': sender,
                'date': date,
            })

    return JsonResponse({
        'emails': email_data
    }, json_dumps_params={
        'ensure_ascii': False
    })

