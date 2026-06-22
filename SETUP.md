# WhatSub Setup Guide

새로운 환경에서 `git clone`을 받은 뒤 WhatSub 프로젝트를 실행하기 위한 설치/생성/로드 지침입니다.

아래 명령어는 Git Bash 기준입니다.

## 1. 프로젝트 받기

```bash
git clone <repository-url>
cd WhatSub
```

이미 받은 프로젝트라면 프로젝트 루트로 이동합니다.

```bash
cd /path/to/WhatSub
```

## 2. Python 가상환경 만들기

Python 3.12 기준으로 가상환경을 만듭니다.

```bash
python -m venv venv
source venv/Scripts/activate
```

## 3. 패키지 설치

```bash
pip install -r backend/requirements.txt
```

## 4. `.env` 파일 만들기

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
DEBUG=True
SECRET_KEY=''
TMDB_API_KEY=''
WATCHMODE_API_KEY=''
AI_API_KEY=''
RAPID_API_KEY=''
GOOGLE_CLIENT_ID=''
GOOGLE_CLIENT_SECRET=''
```

주의: `.env`는 커밋하지 않습니다.

Google 로그인 테스트 전에 `backend/whatsub/urls.py`에서 위 라우팅이 활성화되어 있는지 확인합니다.

## 6. 데이터베이스 생성

SQLite DB는 clone 시 없을 수 있으므로 마이그레이션을 실행합니다.

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

기본 플랫폼/요금제 데이터를 불러옵니다.

```bash
python manage.py loaddata subscriptions/fixtures/platform_seed.json
```

## 7. 서버 실행

```bash
cd backend
python manage.py runserver
```

브라우저에서 접속합니다.

```text
http://127.0.0.1:8000/
```

현재 주요 경로는 다음과 같습니다.

```text
/contents/movies/
/contents/shows/
/contents/search/
/accounts/profile/
/subscriptions/platforms/
/detector/gmail_detail/
```

## 8. 실행 전 체크

```bash
cd backend
python manage.py check
```

문제가 없으면 서버를 실행합니다.

## 9. 새 환경에서 꼭 확인할 것

- `venv`는 clone 후 새로 생성합니다.
- `.env`는 직접 만들어야 합니다.
- `db.sqlite3`가 없다면 `python manage.py migrate`를 실행합니다.
- 플랫폼/요금제 기본 데이터가 필요하므로 `python manage.py loaddata subscriptions/fixtures/platform_seed.json`를 실행합니다.
- API 키 이름은 코드와 맞춰야 합니다.
- `.env`는 커밋하지 않습니다.
