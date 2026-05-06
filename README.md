# HealthAgent — 个人健康管理智能体

本科生毕业设计项目。面向普通家庭的个人血压管理工具，核心功能：**拍照识别血压计读数 → 看趋势变化 → AI 健康问诊（RAG，回答有据可查）**。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.11, FastAPI, SQLAlchemy 2, SQLite/PostgreSQL, sqlite-vec, JWT, OpenCV |
| 前端 | React 18, TypeScript 5 (strict), Vite 5, Ant Design 5, ECharts 6, Zustand 5 |
| AI/ML | DashScope (Qwen-VL, Qwen-Plus, text-embedding-v3), HOG+SVM 本地分类器 |
| OCR | 百度云 OCR + VLM 双通路, CLAHE 预处理, X坐标聚类字段抽取 |

## 项目结构

```
HealthAgent/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/             # REST API 路由
│   │   │   ├── auth.py         # 注册/登录/刷新Token
│   │   │   ├── users.py        # 用户信息/修改密码
│   │   │   ├── ocr.py          # 拍照上传OCR识别
│   │   │   ├── bp_records.py   # 血压记录CRUD/统计/预测
│   │   │   ├── chat.py         # 对话/SSE流式问诊
│   │   │   ├── deps.py         # JWT认证依赖
│   │   │   └── router.py       # /api/v1 路由汇总
│   │   ├── core/               # 配置(config.py) + 安全(security.py)
│   │   ├── db/session.py       # SQLAlchemy 引擎 + get_db()
│   │   ├── models/             # ORM: User, BpRecord, Conversation, ChatMessage
│   │   ├── schemas/            # Pydantic v2 请求/响应模型
│   │   ├── services/
│   │   │   ├── ocr_service.py  # OCR主流程：分类→路由→识别→抽字段→VLM兜底
│   │   │   ├── ocr/            # 子模块：预处理/百度OCR/VLM/字段抽取/分类器
│   │   │   ├── rag/            # RAG子模块：LLM/分片/向量库/检索/入库/Prompt/问答
│   │   │   ├── bp_record_service.py
│   │   │   ├── user_service.py
│   │   │   └── chat_store.py
│   │   ├── cli/kb.py           # 知识库管理: ingest / stats
│   │   └── main.py             # FastAPI 入口, create_app()
│   ├── data/kb/                # 12篇医学知识库Markdown文档
│   ├── storage/                # 运行时存储(向量库/图片)
│   ├── tests/                  # pytest 86个用例, 82%覆盖率
│   ├── tools/rag_eval.py       # RAG自动评测脚本
│   ├── pyproject.toml
│   └── .env                    # 密钥/配置
├── frontend/                   # React + Vite 前端
│   ├── src/
│   │   ├── pages/              # Login, Register, Me, BpDashboard, BpRecordForm, BpRecordList, Chat
│   │   ├── components/         # AppLayout(侧边栏布局), RequireAuth(鉴权守卫), ErrorBoundary
│   │   ├── api/                # Axios客户端 + 各模块API封装
│   │   ├── store/auth.ts       # Zustand认证状态
│   │   ├── types/api.ts        # TypeScript类型
│   │   └── utils/error.ts      # 错误提取
│   ├── src/__tests__/          # vitest 15个用例
│   ├── vite.config.ts          # 代理 /api → :8000
│   └── package.json
├── datasets/                   # 测试数据集
│   ├── bp_images/              # 10张LCD血压计照片 + labels.json
│   └── bp_clean/               # 10张标准字体血压界面图片 + labels.json
├── scripts/                    # 工具脚本
│   ├── generate_bp_images.py   # 生成合成LCD血压计图片
│   ├── generate_clean_bp.py    # 生成标准字体血压界面图片
│   ├── train_lcd_classifier.py # 训练HOG+SVM LCD分类器
│   ├── gen_fig_ocr_compare.py  # 绘制OCR对比图
│   └── gen_fig_perf.py         # 绘制性能基准图
├── docs/                       # 论文 + 设计文档 + 测试报告
│   ├── thesis.tex              # 毕业论文LaTeX源码
│   ├── thesis.pdf              # 毕业论文PDF
│   └── *.md                    # 各阶段设计文档和测试报告
├── pic/                        # 论文插图PNG（图1-3）
├── format/                     # 毕业论文格式模板（PDF扫描件）
├── revision/                   # 导师返稿修改建议
├── docker-compose.yml          # PostgreSQL + Backend
└── CLAUDE.md                  # Claude Code 开发约定
```

## 快速启动

### 1. 环境变量 (`backend/.env`)

必填：
```env
JWT_SECRET=xxx
DASHSCOPE_API_KEY=xxx          # 通义千问API（RAG问答 + VLM兜底均依赖）
BAIDU_OCR_AK=xxx               # 百度云OCR（标准字体路径）
BAIDU_OCR_SK=xxx
```

可选（有默认值）：
```env
DATABASE_URL=sqlite:///./healthagent.db   # 默认SQLite，生产换成PostgreSQL
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:5173
DASHSCOPE_VL_MODEL=qwen-vl-plus
DASHSCOPE_CHAT_MODEL=qwen-plus
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v3
RAG_TOP_K=5
```

### 2. 后端

```bash
cd backend
pip install -e .
python -m app.cli.kb ingest data/kb    # 首次运行：构建向量知识库（约10s）
python -m app.cli.kb stats             # 验证：应输出 docs: 12, chunks: 64
uvicorn app.main:app --reload --port 8000
```

API 文档：`http://localhost:8000/docs`

### 3. 前端

```bash
cd frontend
npm install
npm run dev         # http://localhost:5173, /api 代理到 :8000
```

### 4. 测试

```bash
# 后端 86 用例, 82% 覆盖率
cd backend && python -m pytest --cov=app --cov-report=term-missing

# 前端 15 用例 + 类型检查
cd frontend && npm run test -- --run && npx tsc --noEmit
```

### 5. Docker

```bash
docker compose up    # PostgreSQL + Backend
```

## 核心架构

### OCR 双通路流水线

```
上传血压计照片
  → 本地 HOG+SVM 分类器（<1ms，判断是否LCD七段数码管屏幕）
    ├─ LCD 屏幕 → 直接调用 Qwen-VL 端到端识别（跳过传统OCR）
    └─ 标准字体 → 百度云 accurate OCR → X坐标聚类字段抽取
                   → VLM兜底（仅字段缺失/校验失败时触发）
```

在10张LCD+10张标准字体图片（60个标注字段）上端到端准确率100%。传统OCR方案在LCD场景下准确率均<20%（PaddleOCR 16.7-20.0%, 百度云 3.3-16.7%）。

### RAG 健康问诊

```
用户提问
  → text-embedding-v3 生成1024维查询向量
  → sqlite-vec L2距离检索 Top-5 知识库片段
  → Prompt 组装：6条安全行为边界 + Top-5引用片段 + 用户近14天血压概况 + 最近6轮对话
  → Qwen-Plus SSE流式输出（打字机效果）
```

安全约束（Prompt层面6条红线）：强制引用标注、禁止剂量建议、禁止确定性诊断、诚实边界、强制免责声明、角色定位。自动评测脚本在10道问题上三项安全指标均达100%。

### 数据管理

- **用户隔离**：服务层双重校验，越权访问统一返回404（不用403防信息泄露）
- **趋势判定**：自适应窗口（min(7, N)）+ 简单滑动平均，Δ±3%阈值，数据不足3天直接告知
- **看板**：双Y轴ECharts折线图 + 四色统计卡片 + 趋势Tag

## API 概要

所有接口前缀 `/api/v1/`，除注册/登录/刷新外均需 `Authorization: Bearer <access_token>`。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册（返回用户+双Token） |
| POST | `/auth/login` | 登录 |
| POST | `/auth/refresh` | 刷新Token |
| GET/PATCH | `/users/me` | 查看/修改个人信息 |
| POST | `/users/me/password` | 修改密码 |
| POST | `/ocr/bp` | 上传血压计照片做OCR（multipart/form-data） |
| POST | `/bp-records` | 创建血压记录 |
| GET | `/bp-records` | 分页查询（支持日期范围筛选） |
| GET | `/bp-records/stats?days=30` | 统计聚合（COUNT/AVG/MAX/MIN） |
| GET | `/bp-records/forecast?days=7` | 趋势预测 |
| GET/PATCH/DELETE | `/bp-records/{id}` | 查看/修改/删除单条记录 |
| POST/GET | `/chat/conversations` | 创建/列出对话 |
| DELETE | `/chat/conversations/{id}` | 删除对话 |
| GET | `/chat/conversations/{id}/messages` | 获取对话消息列表 |
| POST | `/chat/conversations/{id}/ask` | SSE流式问诊 |

## 论文

- LaTeX 源码：[docs/thesis.tex](docs/thesis.tex)（约900行，XeLaTeX编译）
- 编译命令：`cd docs && xelatex thesis.tex`（两遍）
- 图片资源：[pic/](pic/)（pic1.png 架构图, pic2.png OCR对比, pic3.png 性能基准）
- 格式模板：[format/](format/)（华中科技大学本科毕设格式示例）
- 返稿建议：[revision/](revision/)（导师修改建议存放处）
- 数据集：[datasets/](datasets/)（LCD+标准字体各10张，含标注）
- 脚本：[scripts/](scripts/)（数据集生成、模型训练、论文配图绘制）
