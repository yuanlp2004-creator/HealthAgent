# HealthAgent · 个人健康管理智能体

> 本科毕业设计项目：面向家庭的个人健康管理系统，集成 **血压计拍照 OCR、健康数据管理与趋势预测、基于 RAG 的大模型健康问诊**。

- 后端：Python 3.11 + FastAPI + SQLAlchemy 2 + SQLite + sqlite-vec
- 前端：React 18 + Vite 5 + TypeScript 5 + Ant Design 5 + ECharts
- 算法：百度云 OCR（主路径）+ 通义千问 qwen-vl-plus（VLM 兜底）、text-embedding-v3 + qwen-plus（RAG 问诊）
- 预测：线性回归 + ARIMA（简化版）双模型对比

---

## 1. 功能概览

| 模块 | 能力 |
| --- | --- |
| 用户体系 | 用户名/邮箱注册、JWT 登录、Access(15min) + Refresh(7day) 双 Token、/users/me 资料维护、改密 |
| OCR 录入 | 上传血压计照片 → 百度 OCR 精排 → 自动抽取收缩压/舒张压/心率 → VLM 兜底 → 候选字段预填表单 |
| 健康数据 | 手动/OCR 两种来源统一入库、分页列表、编辑、删除、软删与用户隔离 |
| 数据看板 | 7/30/90 天趋势折线、统计卡片（均值/极值/达标率）、线性 + ARIMA 简化预测 |
| RAG 问诊 | 本地医学知识库（sqlite-vec）+ 用户近 14 天血压上下文注入 + SSE 流式问答 + 引用可追溯 |
| 安全合规 | Prompt 强制引用、免责声明、禁用具体剂量/确定性诊断，响应全链路跨用户 404 隔离 |

## 2. 架构

```
┌────────────────── Browser ──────────────────┐
│  React + AntD  (Vite dev / build)           │
│   └ /api/v1/*  ─ vite proxy ─► FastAPI      │
└─────────────────────────────────────────────┘
                    │
┌────────── FastAPI :8000 ──────────┐
│  auth / users / bp-records / ocr  │
│  chat (SSE)                       │
│    │                              │
│    ├─► OCR: 百度云 / qwen-vl-plus │
│    ├─► RAG: sqlite-vec + qwen-plus│
│    └─► DB: SQLite (可切 Postgres) │
└───────────────────────────────────┘
```

## 3. 快速启动

### 3.1 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # Linux/macOS

pip install -e .

# 复制并填入 DashScope / 百度 OCR Key
cp .env.example .env
# 编辑 .env，至少填入 DASHSCOPE_API_KEY（RAG 与 VLM 兜底均依赖）

# 首次运行：构建医学知识库（约 10s，消耗少量 embedding 额度）
python -m app.cli.kb ingest data/kb
python -m app.cli.kb stats     # 应看到 docs: 12, chunks: 64

# 启动
uvicorn app.main:app --reload --port 8000
```

### 3.2 前端

```bash
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173
```

`vite.config.ts` 已配置 `/api` → `http://127.0.0.1:8000` 代理，无需额外 CORS 配置。

### 3.3 一键注册测试账号

访问 http://localhost:5173/register，填入任意用户名/邮箱（至少 8 位密码），注册后自动跳转首页。

## 4. 测试

```bash
# 后端：86 用例 + 覆盖率
cd backend
python -m pytest --cov=app --cov-report=term-missing

# 前端：15 用例
cd frontend
npm run test -- --run
npx tsc --noEmit
```

期望输出：**86 passed / 覆盖率 82%**（后端）、**15 passed / 0 type error**（前端）。

## 5. 目录结构

```
HealthAgent/
├─ backend/
│  ├─ app/
│  │  ├─ api/v1/         # auth / users / bp_records / ocr / chat 路由
│  │  ├─ core/           # 配置、JWT、日志
│  │  ├─ db/             # Session 与 Base
│  │  ├─ models/         # SQLAlchemy 模型
│  │  ├─ schemas/        # Pydantic v2 Schema
│  │  ├─ services/
│  │  │  ├─ ocr/         # 百度 OCR 客户端 + qwen-vl 兜底 + 字段抽取
│  │  │  ├─ rag/         # chunker/vector_store/retriever/prompt/chat_service
│  │  │  ├─ ocr_service.py
│  │  │  ├─ bp_record_service.py
│  │  │  ├─ chat_store.py
│  │  │  └─ user_service.py
│  │  └─ cli/            # kb ingest/stats 命令行
│  ├─ data/kb/           # 12 篇占位医学 MD（非权威，待替换）
│  ├─ storage/           # 运行时：图片、kb.sqlite
│  ├─ tests/             # 86 个 pytest（含 e2e 全链路）
│  └─ tools/rag_eval.py  # RAG 规则式自动评测
├─ frontend/
│  └─ src/
│     ├─ pages/          # Login/Register/Bp*/Chat/Me
│     ├─ components/     # AppLayout/PageHeader/EmptyState/ErrorBoundary/...
│     ├─ api/            # axios client + 各模块 API
│     ├─ store/          # zustand auth store
│     ├─ types/          # TS 类型
│     └─ theme.ts        # AntD 主题与路由元数据
└─ docs/                 # 规划文档 00-07 + P1-P6 测试报告 + 评测产物
```

## 6. 阶段性成果

| 阶段 | 交付 | 测试报告 |
| --- | --- | --- |
| P1 | 环境搭建 / 用户体系 | [P1](docs/P1_测试报告.md) |
| P2 | 登录/注册/鉴权前端 | [P2](docs/P2_测试报告.md) |
| P3 | OCR 主路径 + VLM 兜底 | [P3](docs/P3_测试报告.md) |
| P4 | 血压 CRUD + 看板 + 预测 | [P4](docs/P4_测试报告.md) |
| P5 | RAG 知识库 + qwen-plus SSE 问诊 | [P5](docs/P5_测试报告.md) |
| P6 | 前端设计系统统一 + 侧栏导航 + UX 打磨 | [P6](docs/P6_测试报告.md) |
| P7 | 整体验收（覆盖率/e2e/手工走查/文档） | [整体验收](docs/整体验收报告.md) |

## 7. 已知限制

1. **语料非权威**：12 篇知识库为自编占位，答辩前请替换为 WHO / 国家卫健委 / 中国高血压防治指南等权威材料后 `python -m app.cli.kb ingest data/kb` 增量替换
2. **DashScope 额度**：qwen-plus 与 text-embedding-v3 均按 token 计费（毕设免费额度内），请保管 `.env` 不要提交到仓库
3. **移动端未适配**：仅桌面 Chrome/Edge 样式最佳；移动浏览器可能出现侧栏遮挡
4. **部署未完成**：P7 的部署/论文/答辩按计划后置；当前仅本地 `uvicorn + npm run dev` 模式

## 8. 致谢

- 百度云 OCR · 阿里云 DashScope （通义千问系列）
- Ant Design / ECharts / sqlite-vec 开源社区
