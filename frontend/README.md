# WhatSub Frontend

Vue 3 + Vite SPA입니다. 이 폴더에서 바로 npm 명령을 실행합니다.

```bash
cd ~/Desktop/Coding/WhatSub/frontend
npm i
npm run dev
```

## 구조

```text
frontend/
  public/img/
  src/
    api/         # fetch/CSRF 공통 처리
    components/  # 재사용 컴포넌트
    router/      # Vue Router
    stores/      # Pinia
    views/       # 페이지 화면
    App.vue
    main.js
    styles.css
```

Django는 화면을 렌더링하지 않고 `/api/...` JSON API와 OAuth 콜백만 담당합니다.

협업 규칙상 `npm audit fix`는 실행하지 않습니다.
