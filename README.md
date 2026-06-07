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
WhatSub/
├── accounts/        # Google OAuth, 유저 관리
├── subscriptions/   # 구독 감지, UserSubscription
├── platforms/       # 플랫폼·요금제 데이터, 벤치마크
├── contents/        # TMDB 연동, 스트리밍 가용 조회
└── config/          # Django settings, urls
```

---

## 🚀 Getting Started

### Requirements
- Python 3.11+
- PostgreSQL
- API Keys: TMDB, Watchmode, Google OAuth, Gmail API

### Installation

```bash
git clone https://github.com/blunderblus/WhatSub.git
cd WhatSub
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

### Environment Setup

`.env` 파일을 생성하고 아래 값을 채워주세요:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

DB_NAME=whatsub
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

TMDB_API_KEY=your-tmdb-api-key
WATCHMODE_API_KEY=your-watchmode-api-key

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### Run

```bash
python manage.py migrate
python manage.py loaddata platforms/fixtures/platform_seed.json
python manage.py runserver
```

API 문서: `http://localhost:8000/swagger/`

---

## 📊 Platform Data Model

요금제 구조가 복잡한 서비스(예: 쿠팡플레이의 일반/와우, 티빙의 제휴 요금)를 모두 수용하는 릴레이셔널 모델을 사용합니다.

```
Platform
  └── SubscriptionPlan (베이직 / 스탠다드 / 프리미엄 / 와우 ...)
        └── requires_membership (FK, nullable)  # 와우 → 쿠팡WOW 필요
  └── AddOnPass (스포츠 패스, J PLUS 패스 ...)
        └── AddOnPassPricing (일반가 / 와우가)
  └── BundleContent (번들에 포함된 서비스 목록)
```

---

## 🗺 Roadmap

- [x] 프로젝트 설계 및 데이터 모델 확정
- [x] 플랫폼 요금제 시드 데이터 (Netflix, Disney+, TVING, Wavve, Watcha, Coupang Play, Apple TV+, Laftel, SPOTV)
- [x] Google OAuth 로그인
- [x] Gmail 구독 감지 파이프라인
- [x] TMDB 콘텐츠 검색
- [x] Watchmode 스트리밍 가용 조회 + 캐싱
- [x] 플랫폼 벤치마크 & 리더보드
- [ ] Personal Score
- [x] 구독 대시보드

---

## 📄 License

MIT
