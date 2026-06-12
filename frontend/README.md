# WhatSub Frontend

Django 템플릿 기반 UI와 향후 Vue SPA가 분리된 프론트엔드 영역입니다.

## 구조

```
frontend/
├── templates/     # Django가 렌더링하는 HTML (전환기)
│   ├── index.html
│   ├── accounts/  # 로그인, 온보딩, 프로필
│   └── contents/  # 콘텐츠 탐색 (일부 Vue CDN 사용)
├── static/        # 이미지, 파비콘 등 정적 자산
└── vue/           # 향후 Vite + Vue 3 SPA (미구현)
```

## 현재 상태

- **운영 중**: `templates/` + `static/` — Django `runserver`가 직접 서빙
- **예정**: `vue/` — API 전용 백엔드와 분리된 SPA로 점진 이전

## 개발 시 참고

- Django 템플릿 경로: `backend/whatsub/settings.py` → `frontend/templates`
- 정적 파일 경로: `frontend/static` (`{% static 'img/...' %}`)
- 콘텐츠 목록·상세(`movie_list.html`, `movie_detail.html`)는 Vue 3 CDN을 사용합니다. SPA 이전 시 `vue/`로 로직을 옮기면 됩니다.
