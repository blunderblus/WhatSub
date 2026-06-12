# WhatSub Setup Guide

이 문서는 Git Bash 기준 실행 방법입니다.

## 1. 프로젝트로 이동

```bash
cd ~/Desktop/Coding/WhatSub
```

## 2. Python 가상환경

```bash
py -m venv venv
source venv/Scripts/activate
```

## 3. 백엔드 패키지 설치

```bash
pip install -r backend/requirements.txt
```

## 4. `.env` 만들기

프로젝트 루트에 `.env` 파일을 만들고 값을 채웁니다.

```env
DEBUG=True
SECRET_KEY='your-django-secret-key'
FRONTEND_URL='http://127.0.0.1:5173'
TMDB_API_KEY=''
WATCHMODE_API_KEY=''
AI_API_KEY=''
RAPID_API_KEY=''
GOOGLE_CLIENT_ID=''
GOOGLE_CLIENT_SECRET=''
```

## 5. 데이터베이스 준비

```bash
py backend/manage.py makemigrations
py backend/manage.py migrate
py backend/manage.py loaddata subscriptions/fixtures/platform_seed.json
```

## 6. 백엔드 실행

```bash
py backend/manage.py runserver
```

백엔드는 API 서버입니다.

```text
http://127.0.0.1:8000/api/
```

## 7. 프론트엔드 설치 및 실행

Vue 앱은 `frontend` 폴더에 바로 있습니다.

```bash
cd ~/Desktop/Coding/WhatSub/frontend
npm i
npm run dev
```

브라우저 접속 주소:

```text
http://127.0.0.1:5173
```

주의: 협업 규칙상 `npm audit fix`와 `npm audit fix --force`는 실행하지 않습니다.

## 8. 점검 명령

```bash
cd ~/Desktop/Coding/WhatSub
py backend/manage.py check
```

```bash
cd ~/Desktop/Coding/WhatSub/frontend
npm run build
```

## 프론트엔드 구조

```text
frontend/
  public/img/       # Vite 정적 이미지
  src/
    api/            # 공통 API 요청 함수
    components/     # 재사용 컴포넌트
    router/         # Vue Router 설정
    stores/         # Pinia stores
    views/          # 라우터에 연결되는 화면
    App.vue
    main.js
    styles.css
  index.html
  package.json
  vite.config.js
```

역할 분리:

```text
Vue: 화면, 라우팅, 상태 관리, 정적 프론트 이미지
Django: /api/... JSON API, DB, OAuth 콜백, media 파일
```
