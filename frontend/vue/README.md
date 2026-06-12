# Vue SPA (예정)

WhatSub 프론트엔드를 Django 템플릿에서 Vue 3 + Vite SPA로 이전할 때 이 디렉터리를 사용합니다.

## 이전 대상

| 현재 (Django 템플릿) | 향후 (Vue) |
|---------------------|------------|
| `../templates/contents/movie_list.html` | 콘텐츠 목록 컴포넌트 |
| `../templates/contents/movie_detail.html` | 콘텐츠 상세 컴포넌트 |
| `../templates/accounts/*.html` | 인증·온보딩·대시보드 |
| `../templates/index.html` | 랜딩 페이지 |

## 스캐폴딩 (나중에 실행)

```bash
cd frontend/vue
npm create vite@latest . -- --template vue
npm install
npm run dev
```

백엔드 API는 `http://127.0.0.1:8000` (Django)를 사용하고, 개발 시 CORS 설정이 필요할 수 있습니다.
