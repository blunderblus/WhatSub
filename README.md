# WhatSub?

> **구독을 추적하고, 스트리밍을 비교하고, 내 취향에 맞는 플랫폼을 찾아드립니다.**

WhatSub?는 구독 관리와 스트리밍 콘텐츠 탐색을 하나로 통합한 플랫폼입니다. Gmail 연동으로 구독을 자동 감지하고, 내가 좋아하는 작품 취향을 기반으로 어떤 스트리밍 서비스가 가장 나에게 맞는지 알려줍니다.

---

## ✨ Key Features

### 📬 Gmail 기반 구독 자동 감지
Gmail을 연동하면 결제 메일을 분석해 구독 중인 서비스를 자동으로 탐지합니다. 넷플릭스부터 쿠팡 WOW, 배민클럽까지 — 직접 입력 없이 초기 구독 프로필이 구성됩니다.

### 🔍 스트리밍 콘텐츠 탐색
영화나 TV 시리즈를 검색하면 국내외 스트리밍 플랫폼 중 어디서 볼 수 있는지, 구독/대여/구매 여부와 만료일까지 한번에 확인할 수 있습니다.

### 🏆 플랫폼 벤치마크 & 리더보드
플랫폼별 Value Score를 산출해 객관적인 순위를 제공합니다.

```
Value Score =
  콘텐츠 수량 (40%)  ← 카탈로그 규모
+ 콘텐츠 품질 (30%)  ← 고평점 작품 비율
+ 가격 경쟁력 (20%)  ← 월정액 대비 효용
+ 접근성    (10%)  ← 동시접속, 화질, 다운로드
```

### 🎯 Personal Score
내가 좋아요를 누른 작품들의 장르 분포를 분석해, 플랫폼별 개인화 점수를 계산합니다.

> 예: 로맨틱 코미디를 주로 좋아한다면 → 해당 장르 보유작이 많은 플랫폼의 Personal Score가 높아집니다.

---

## 🛠 Tech Stack

| Category | Stack |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Database | PostgreSQL |
| Auth | Google OAuth 2.0 (django-allauth) |
| Content API | TMDB |
| Streaming Availability | Watchmode API |
| Gmail Integration | Google Gmail API |
| Docs | drf-yasg (Swagger) |

---

## 📡 API Strategy

| 역할 | 도구 |
|---|---|
| 콘텐츠 메타데이터 | TMDB (무료, 무제한) |
| 플랫폼 가용 여부 | Watchmode API (KR 지원, 캐싱) |
| 벤치마크 통계 | StreamingCache 집계 |
| 가격/접근성 데이터 | DB 관리 (수동) |

**Watchmode KR 리전 커버 서비스:**
Netflix, Prime Video, Disney+, Apple TV+, TVING, Watcha, Wavve,
Crunchyroll Premium, MUBI, Curiosity Stream, GuideDoc, Zee5

---

## 🗂 Project Structure

```

## 주요 기능

### 구독 관리
- **Google 로그인** — django-allauth 기반 OAuth 인증
- **Gmail 자동 감지** — 받은편지함에서 구독·결제 관련 메일을 키워드 필터링 후 LLM으로 플랫폼·요금·갱신일 추출
- **수동 등록** — 온보딩 중 직접 구독 정보 입력
- **구독 대시보드** — 월간 지출 합계, 갱신 일정, 플랫폼별 구독 목록 확인

### 콘텐츠 탐색
- **TMDB 연동** — 영화·드라마 검색, 메타데이터(포스터, 평점, 장르) 조회
- **시청 가능 플랫폼 조회** — Watchmode·RapidAPI를 통해 구독/대여/구매/무료 시청처 확인 (24시간 DB 캐시)

### 플랫폼·요금제 정보
- Netflix, Disney+, TVING, Wavve, Coupang Play 등 주요 서비스의 **요금제·번들·애드온 패스** 데이터 제공
- 쿠팡 플레이(일반/와우), 배민클럽 번들 등 복잡한 요금 구조를 관계형 모델로 표현

---

## 프로젝트 구조

백엔드(Django)와 프론트엔드(템플릿·정적 자산·향후 Vue)를 분리한 모노레포입니다.

```
10-pjt/
├── backend/           # Django API·비즈니스 로직
│   ├── accounts/      # 회원가입, 로그인, 온보딩, 프로필
│   ├── contents/      # TMDB 콘텐츠 검색·상세, 시청 가능 플랫폼
│   ├── detector/      # Gmail API 연동, 구독 메일 감지·LLM 추출
│   ├── subscriptions/ # 플랫폼·요금제·사용자 구독 모델
│   ├── notifications/ # 알림 (예정)
│   ├── whatsub/       # Django 프로젝트 설정
│   ├── manage.py
│   └── requirements.txt
├── frontend/          # UI (Django 템플릿 → Vue SPA 이전 예정)
│   ├── templates/     # HTML 템플릿
│   ├── static/        # 이미지·파비콘
│   ├── public/        # Vue 정적 파일
│   └── src/           # Vue 3 SPA 소스
├── .env               # 환경 변수 (프로젝트 루트)
├── SETUP.md           # 상세 설치 가이드
└── PROJECT_CONTEXT.md # 기능·아키텍처 상세 문서
```

---

## Gmail 구독 감지 파이프라인

```
Gmail 받은편지함 접근
  → 메일 메타데이터 수집 (최근 1개월, 최대 100건)
    → 키워드 기반 필터링 (Netflix, 구독, 결제, Premium 등)
      → LLM 배치 추출 (플랫폼, 요금, 결제 주기, 갱신일)
        → UserSubscription 생성 (사용자 확인 후 저장)
```

**키워드 예시:** Netflix, Disney+, TVING, Spotify, ChatGPT, 결제, 구독, Premium, 멤버십 등

**LLM 출력 스키마:**
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

## 시작하기

> 자세한 설치 절차는 [SETUP.md](./SETUP.md)를 참고하세요.

### 1. 저장소 클론 및 가상환경

```bash
git clone <repository-url>
cd 10-pjt
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
pip install -r backend/requirements.txt
```

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
DEBUG=True
SECRET_KEY='your-django-secret-key'
TMDB_API_KEY=''
WATCHMODE_API_KEY=''
AI_API_KEY=''
RAPID_API_KEY=''
GOOGLE_CLIENT_ID=''
GOOGLE_CLIENT_SECRET=''
```

> `.env` 파일은 Git에 커밋하지 마세요.

**Google OAuth 설정:** [Google Cloud Console](https://console.cloud.google.com/)에서 OAuth 클라이언트 ID를 발급하고, Gmail API(`gmail.readonly`)를 활성화합니다. 리디렉션 URI에 `http://127.0.0.1:8000/accounts/google/login/callback/`을 등록합니다.

### 3. 데이터베이스 초기화

```bash
cd backend
python manage.py migrate
python manage.py loaddata subscriptions/fixtures/platform_seed.json
```

### 4. 서버 실행

```bash
cd backend
python manage.py check
python manage.py runserver
```

브라우저에서 [http://127.0.0.1:8000/](http://127.0.0.1:8000/) 접속

---

## 주요 URL

| 경로 | 설명 |
|------|------|
| `/` | 메인 페이지 |
| `/accounts/login/` | 로그인 |
| `/accounts/signup/` | 회원가입 |
| `/accounts/onboarding/` | 온보딩 (Gmail 스캔 / 수동 추가 선택) |
| `/accounts/onboarding/gmail/` | Gmail 구독 스캔 |
| `/accounts/profile/` | 구독 대시보드 |
| `/contents/movies/` | 영화 목록 |
| `/contents/shows/` | 드라마 목록 |
| `/contents/search/` | 콘텐츠 검색 |
| `/subscriptions/platforms/` | 플랫폼·요금제 목록 |
| `/detector/gmail_detail/` | Gmail 구독 메일 필터링 API (JSON) |

---

## API 키 안내

| 변수 | 용도 |
|------|------|
| `TMDB_API_KEY` | 영화·드라마 메타데이터, Watch Provider |
| `WATCHMODE_API_KEY` | 한국 지역 실시간 시청 가능 플랫폼 (월 2,500건 무료) |
| `RAPID_API_KEY` | Streaming Availability API (보조 소스) |
| `AI_API_KEY` | Gmail 구독 정보 LLM 추출 |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth 및 Gmail API |

Watchmode는 무료 티어 한도를 위해 **작품별 24시간 DB 캐시**를 사용합니다.

---

## 데이터 모델 개요

- **Platform** — Netflix, TVING 등 구독 서비스
- **SubscriptionPlan** — 요금제 (가격, 화질, 동시 시청 수, 번들 여부)
- **BundleContent** — 번들에 포함된 서비스 (예: 배민클럽 → YouTube Premium)
- **AddOnPass / AddOnPassPricing** — 애드온 패스 및 멤버십 등급별 가격
- **UserSubscription** — 사용자별 실제 구독 내역
- **Content / ContentPlatform** — TMDB 콘텐츠 및 플랫폼별 시청 정보

---

## 개발 참고

- 상세 기능 명세·로드맵: [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)
- 설치·실행 체크리스트: [SETUP.md](./SETUP.md)
- Django Admin: `/admin/` (슈퍼유저 생성 후 이용)

---

## 라이선스

이 프로젝트는 SSAFY(삼성청년 SW·AI 아카데미) 교육 과정의 팀 프로젝트입니다.
