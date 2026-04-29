# HealthAgent 前端（P2 阶段）

个人健康管理智能体 — React + Vite + TypeScript + Ant Design 前端骨架。

## 目录

```
frontend/
├── src/
│   ├── api/             # axios 实例 + 接口封装
│   ├── components/      # RequireAuth 等通用组件
│   ├── pages/           # Login / Register / Me
│   ├── store/           # zustand auth store
│   ├── types/           # 后端接口 TS 类型
│   ├── utils/           # 错误提取等
│   ├── __tests__/       # vitest 单测
│   └── main.tsx
├── vite.config.ts       # 含 /api → 127.0.0.1:8000 代理
└── package.json
```

## 本地开发

```bash
cd frontend
npm install
npm run dev      # http://127.0.0.1:5173
```

另启后端（见 `backend/README.md`），Vite dev server 会把 `/api/*` 代理到 `127.0.0.1:8000`。

## 测试

```bash
npm test         # vitest，15/15 通过
```

## 生产构建

```bash
npm run build    # tsc --noEmit && vite build → dist/
npm run preview
```

## 已实现页面（P2）

| 路由 | 说明 |
| --- | --- |
| `/login` | 登录 |
| `/register` | 注册 |
| `/me` | 个人中心（查看/修改资料、修改密码、退出） |

未登录访问 `/me` 会重定向到 `/login?redirect=...`，登录成功后回跳。

## 注意

- 依赖 P1 后端所有接口，启动前端前请先起 backend。
- Token 持久化在 `localStorage`（`ha.access` / `ha.refresh`），401 时自动用 refresh 换 access 并重放一次。
- AntD 当前全量引入，bundle 约 gzip 280 KB，P6 阶段将按需引入。
