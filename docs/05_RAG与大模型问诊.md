# P5 RAG 与大模型问诊

> 周期：2026-03-21 ~ 2026-04-20（4.5 周）
> 目标：构建医学知识库与 RAG 问答链路，结合用户健康数据给出个性化、可溯源的医疗建议，覆盖课题第三项内容。

## 1. 目标

- 智能体能基于用户历史健康数据与医学知识库，回答"我最近血压偏高怎么办？"之类问题
- 回答附带引用（文档名 + 片段），避免纯幻觉
- 首 token 延迟 ≤ 3s，支持流式输出

## 2. 输入

- 健康数据（P4）
- 医学知识库原始语料：权威来源（如 WHO、卫健委慢病管理指南、医学教科书节选），**注意版权**，论文中注明来源
- 在线 LLM API：通义千问（主 provider，`qwen-plus` / `qwen-max` 文本问诊，`qwen-vl-plus` 作为 OCR 复检通道）；DeepSeek（备用 fallback）

## 3. 任务拆解

### 3.1 知识库建设（第 1 周）

- 收集 20~50 篇高血压/心率/慢病管理相关文档（PDF/HTML/MD）
- 统一转为 Markdown，清洗页眉页脚、图片注释
- 元数据：`title`, `source`, `url`, `published_at`, `tags`

### 3.2 分片与向量化（第 1 周尾）

- 分片策略：按标题层级 + 500 字窗口 + 50 字重叠
- Embedding：调用在线 API（`text-embedding-v3` 或 `bge-m3`），批量入库
- 向量库：Chroma（Docker 启动），collection 名 `medical_kb`
- 提供 CLI：`python -m app.cli.kb ingest <path>`，支持增量

### 3.3 检索器（第 2 周）

- 基础：向量 Top-K=5
- 进阶（参考文献 2，时间允许则做）：
  - Hybrid Search（BM25 + Vector，RRF 融合）
  - Reranker（调用在线 rerank API）
  - Query 重写（把对话历史改写为独立检索 query）
- 输出 `Context` 对象：`[{text, source, score}]`

### 3.4 对话编排（第 2 周后半）

- 使用 LangChain 或手写简单 orchestrator（推荐手写以控复杂度）
- Prompt 模板：

  ```
  你是个人健康助手。请根据下列资料与用户健康数据作答：
  - 必须在回答末尾以 [1][2] 标注引用
  - 不给出确定性诊断，提醒用户在必要时就医
  - 如资料不足，坦诚告知，不编造

  【用户近 14 天血压均值】...
  【知识库片段】...
  【用户问题】...
  ```

- 注入用户上下文：最近 14 天血压/心率均值与极值、异常次数
- 流式：FastAPI `StreamingResponse` + SSE，前端增量渲染

### 3.5 会话与存档（第 3 周前半）

- `conversations` / `messages` 表的 CRUD
- 每条 assistant 消息保存 `citations_json`（引用片段 id 与原文）
- 接口：

  ```
  POST /api/v1/chat/conversations
  GET  /api/v1/chat/conversations
  POST /api/v1/chat/conversations/{id}/ask   # SSE
  GET  /api/v1/chat/conversations/{id}/messages
  ```

### 3.6 前端问诊页（第 3 周后半）

- 左侧会话列表，右侧对话区
- 消息气泡：用户普通样式；助手样式带"引用"小角标，点击展开原文
- 底部输入框支持快捷问题（"解读我最新一次测量"）
- 显著显示"AI 建议仅供参考，不构成诊断"声明

### 3.7 评测与调优（第 4 周）

- 构造 20~30 条典型问题（涵盖数据解读、生活建议、异常处置）
- 评估维度：**相关性、事实性、引用正确率、拒答合理性**
- 人工打分 + 记录 bad case → 调整 prompt / 分片 / Top-K

## 4. 交付物

- 知识库原始语料与向量库
- `backend/app/services/rag/`（ingest、retriever、chat）
- 前端问诊页面 + 流式渲染
- 问答评测报告（CSV + Markdown 结论）

## 5. 验收标准

- 20+ 条典型问题中，引用正确率 ≥ 80%，事实性错误 ≤ 10%
- 流式首 token ≤ 3s（国内 provider 正常网络）
- 每条 assistant 回复均可展开引用原文
- 断网或 API 故障时有优雅降级提示

## 6. 风险

| 风险 | 缓解 |
| --- | --- |
| 语料版权 | 仅用公开许可语料，论文注明来源 |
| 大模型幻觉 | 严格 prompt、强制引用、低温度（0.3） |
| API 费用 | 开发阶段启用磁盘缓存 (`diskcache`) 对相同 query 复用 |
| Provider 限流 | 支持多 provider 切换（统一 `LLMClient` 抽象） |
| 医疗合规 | 所有回答含免责声明；禁止输出具体药物剂量推荐 |
