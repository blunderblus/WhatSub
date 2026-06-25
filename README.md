# WhatSub - 구독 관리/콘텐츠 추천 서비스

SSAFY 관통 프로젝트 제출 기준에 맞춰 작성한 README입니다.  
WhatSub는 OTT 구독을 자동 감지하고, 콘텐츠 취향 데이터를 바탕으로 사용자 맞춤 플랫폼을 추천하는 웹 서비스입니다.

## 1. 팀원 정보 및 역할 분담

| 이름 | 역할 | 주요 담당 |
| --- | --- | --- |
| 허선율 | Backend/AI | UI 디자인 디렉션, 백엔드 로직, LLM 파이프라인, 온보딩 |
| 유성현 | Frontend/UX | 프론트엔드 전반, UX 개선, 커뮤니티 CRUD |

## 2. 서비스 개요

- Gmail 결제 메일과 영수증 이미지를 분석해 구독 서비스를 자동 등록
- 영화/시리즈 검색 후 플랫폼별 시청 가능 여부(구독/대여/구매) 조회
- 플랫폼 벤치마크(Value Score)와 개인화 추천(Personal Score) 제공
- 커뮤니티 게시글/댓글 CRUD, 반응(좋아요/싫어요), 신고 기능 제공

## 3. 기술 스택

- Backend: Django 5.2, Django REST Framework, django-allauth
- Frontend: Vue 3, Vite, Pinia, Vue Router
- DB: SQLite(기본), PostgreSQL(`DATABASE_URL` 설정 시)
- External API: TMDB, Watchmode, RapidAPI, Google OAuth/Gmail API
- AI: OpenAI 호환 Chat API + Gemini Vision API(영수증 분석)

## 4. 시스템 아키텍처

```text
[Vue 3 Frontend]
        |
        v
[Django REST API]
  | accounts / contents / subscriptions / community / detector
  |
  +--> [DB: User, Subscription, Content, Benchmark Snapshot ...]
  +--> [TMDB / Watchmode / RapidAPI]
  +--> [Google OAuth + Gmail API]
  +--> [LLM API (취향/벤치마크/영수증 분석)]
```

## 5. 주요 기능 설명 (요구사항 대응)

### 5.1 인증/회원 기능
- 회원가입, 로그인, 로그아웃, 회원 탈퇴 API 제공
- `Custom User` 기반 프로필 정보(닉네임, 이미지, bio) 관리
- Google OAuth 로그인 + 온보딩 플로우 연결

### 5.2 구독 관리
- 수동 구독 등록/삭제, 갱신 예정 알림 피드 조회
- Gmail 스캔 결과를 일괄 저장하는 온보딩 API 제공
- 영수증 이미지 업로드 시 반복결제 항목 자동 추출

### 5.3 콘텐츠 탐색
- 영화/TV 리스트/상세/검색 API 제공
- 작품별 스트리밍 플랫폼 가용성 조회
- 사용자 반응(좋아요/싫어요) 기반 선호 데이터 축적

### 5.4 플랫폼 벤치마크
- 플랫폼별 5축 점수 계산
  - availability(보유량)
  - exclusivity(독점성)
  - quality(품질)
  - price(가격경쟁력)
  - accessibility(접근성)
- 정규화 후 Value Score 산출 및 리더보드 제공

### 5.5 커뮤니티
- 게시판/게시글/댓글 CRUD
- 게시글/댓글 반응 및 신고 기능
- 작성자 권한 기반 수정/삭제 처리

## 6. 금융(구독) 추천 알고리즘 기술 설명

본 프로젝트의 핵심 추천은 `Personal Score`입니다.

1) 사용자 취향 벡터 생성
- 좋아요/싫어요 반응에서 장르 가중치 계산
- 온보딩 설문/대화에서 장르 선호도 및 소비 습관 반영
- 필요 시 LLM으로 취향 가중치 보정(일일 호출 제한 적용)

2) 플랫폼별 개인 적합도 계산
- `Genre Benefit`: 선호 장르 * 플랫폼 장르 보유량
- `Exclusivity Affinity`: 사용자가 좋아한 작품의 독점작 매칭 정도
- 두 축을 독립 정규화 후 평균하여 `Personal Score` 계산

3) 추천 결과 생성
- 점수 순 정렬된 플랫폼 목록 제공
- 추천 사유(장르 적합, 독점작 매칭, 가격 경쟁력) 자동 생성
- 기존 구독 월 지출 및 최소 요금제 가격을 함께 제시

## 7. 생성형 AI 활용 내용

### 7.1 Gmail 구독 추출
- Gmail 메일 본문에서 플랫폼/요금/결제주기/갱신일 JSON 추출
- 캐싱/예외처리로 실패 시 안전하게 폴백 처리

### 7.2 영수증 이미지 분석
- Gemini Vision 기반 OCR+의미 추출로 정기결제 항목 인식
- 단건/다건 이미지 처리 및 페이로드 크기 제한 대응

### 7.3 추천/벤치마크 고도화
- 독점작 트렌딩 가중치, 요금제 효용 판단에 LLM 활용
- 프롬프트 해시 기반 캐시 키를 이용해 재계산 최소화

## 8. ERD 요약

- `accounts.User`: 사용자 기본 정보
- `accounts.UserPreferenceProfile`: 취향 프로필/설문 결과
- `subscriptions.Platform`, `SubscriptionPlan`, `UserSubscription`: 플랫폼/요금제/개인 구독
- `contents.ContentReaction`, `PlatformBenchmarkSnapshot`: 반응 데이터/플랫폼 점수 스냅샷
- `community.CommunityPost`, `CommunityComment`: 커뮤니티 게시글/댓글

> 상세 ERD 이미지는 `docs` 폴더 또는 발표 자료에 첨부해 제출 권장.

## 9. 실행 방법

### 9.1 Backend
```bash
cd backend
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 9.2 Frontend
```bash
cd frontend
npm install
npm run dev
```

### 9.3 필수 환경변수(.env)
```env
DEBUG=True
SECRET_KEY=your-secret-key
FRONTEND_URL=http://127.0.0.1:5173
BACKEND_URL=http://127.0.0.1:8000
DATABASE_URL=
TMDB_API_KEY=
WATCHMODE_API_KEY=
RAPID_API_KEY=
AI_API_KEY=
AI_API_BASE=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

## 10. 비기능 요구사항 반영

- 환경변수 분리: 민감정보를 `.env`로 분리
- 오류 처리: 외부 API 실패/한도 초과/인증 오류 메시지 처리
- 문서화: README에 아키텍처, 알고리즘, AI 활용 내용 명시
- Git 관리: 불필요 파일 제외 및 모듈별 구조 분리

## 11. 프로젝트 후기 및 느낀 점

- 외부 API와 AI를 동시에 연동할 때 장애 포인트가 많아, 캐시/폴백 설계가 중요함을 확인
- 추천 정확도는 단일 규칙보다 사용자 반응 + 온보딩 + LLM 보정의 결합이 더 효과적이었음
- 실제 서비스 수준에서는 데이터 신뢰도(갱신 주기, 중복 제거, 실패 복구)가 기능 자체만큼 중요함

## 12. 참고 자료

- [Django 공식 문서](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Vue 공식 문서](https://vuejs.org/)
- [TMDB API](https://developer.themoviedb.org/docs)
- [YouTube Data API](https://developers.google.com/youtube/v3/getting-started?hl=ko)
- [Google Gmail API](https://developers.google.com/gmail/api)
