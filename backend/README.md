# HealthAgent 后端（P1 阶段）

个人健康管理智能体 — FastAPI 后端骨架与用户体系。

## 目录

```
backend/
├── app/
│   ├── api/v1/       # auth, users 路由
│   ├── core/         # 配置、安全、日志
│   ├── db/           # SQLAlchemy session 与 Base
│   ├── models/       # ORM 模型
│   ├── schemas/      # Pydantic 校验
│   ├── services/     # 业务逻辑
│   └── main.py       # FastAPI 入口
├── tests/            # pytest
├── pyproject.toml
├── Dockerfile
└── .env.example
```

## 本地开发（SQLite）

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -e ".[dev]"
cp .env.example .env                              # 或手动复制
uvicorn app.main:app --reload
```

启动后访问 `http://127.0.0.1:8000/docs` 查看 Swagger UI。

## Docker（Postgres）

项目根目录：
```bash
docker compose up -d --build
```

## 测试

```bash
cd backend
python -m pytest -q --cov=app --cov-report=term-missing
```

当前：**27 通过，覆盖率 96%**。详见 [`docs/P1_测试报告.md`](../docs/P1_测试报告.md)。

## E2E 冒烟（P2）

`backend/tests/smoke_p2.py` 针对 live uvicorn 进程跑「注册 → me → 改资料 → refresh → 改密码 → 新旧密码登录」：

```bash
# 终端 A
cd backend
DATABASE_URL="sqlite:///./healthagent_smoke.db" JWT_SECRET="smoke-secret" \
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 终端 B
cd backend
python tests/smoke_p2.py
```

详见 [`docs/P2_测试报告.md`](../docs/P2_测试报告.md)。

## 已实现接口（P1）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/healthz` | 健康检查 |
| POST | `/api/v1/auth/register` | 注册 |
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/auth/refresh` | 刷新 token |
| GET | `/api/v1/users/me` | 当前用户 |
| PATCH | `/api/v1/users/me` | 修改资料 |
| POST | `/api/v1/users/me/password` | 修改密码 |

## 注意

- `passlib 1.7.4` 与 `bcrypt 4.1+` 不兼容，`bcrypt` 锁定 `4.0.1`。
- JWT 密钥必须通过 `.env` 的 `JWT_SECRET` 覆盖。
