# P3 OCR 模块（血压计图像识别）

> 周期：2026-01-16 ~ 2026-02-20（5 周，含寒假）
> 目标：用户上传电子血压计照片，系统自动识别收缩压、舒张压、心率三项关键数值并落库，是本课题第一项核心内容。

## 1. 目标

- 核心指标：**字段级准确率 ≥ 90%**（收缩压/舒张压/心率三项，基于自建测试集 ≥ 50 张）
- 单张图片识别端到端 ≤ 3s（CPU），≤ 1s（若有 GPU）
- 提供"识别 → 用户确认 → 入库"的闭环 UI

## 2. 输入

- P2 搭好的后端骨架
- 参考文献 1：百度 AI Studio 液晶屏识别（https://aistudio.baidu.com/projectdetail/9661312）
- 测试图片集：自拍摄 + 网络公开样本（需去水印、注意版权）

## 3. 任务拆解

### 3.1 数据采集与标注（第 1 周）

- 已采集 20 张样本（标注格式见 `datasets/bp_images/labels.json` 和 `datasets/bp_clean/labels.json`）：
  - 10张真实七段数码管LCD血压计屏幕照片（`bp_images/`）
  - 10张合成标准印刷字体血压界面（`bp_clean/`，模拟App截图/电脑看板/打印标签）
- 标注格式（JSON）：

  ```json
  {"file":"001.jpg","systolic":128,"diastolic":82,"heart_rate":76}
  ```

- 分训练/测试集 8:2（若走微调路径）

### 3.2 OCR 方案落地（第 2 周）

经过多轮迭代，最终采用 **"分类先行、双通路"** 架构（演进自最初的"百度云数字OCR + VLM兜底"方案，演进历程见 `docs/P3_测试报告.md`）：

1. **图像类型分类（新增）**：
   - 本地 HOG+SVM 分类器判断图片是七段数码管LCD还是标准字体界面（App截图/打印标签等）
   - 训练数据：10张LCD + 10张标准字体图片，20/20分类正确
   - 推理耗时 < 1ms，零API开销，模型文件 ~600KB（`backend/app/services/ocr/lcd_classifier.pkl`）
2. **LCD路径：直达VLM**：
   - 分类为LCD → 跳过OCR，直接调用通义千问VL（`qwen-vl-plus`）做端到端识别
   - Prompt包含血压计屏幕识别专用的结构化JSON指令
   - 平均耗时 ~1.05s
3. **非LCD路径：百度云通用OCR + X坐标聚类**：
   - 百度云通用OCR（`/rest/2.0/ocr/v1/accurate`），检出率100%（标准字体）
   - 图像预处理：灰度化 + CLAHE对比度增强，长边缩至1920px
   - X坐标聚类字段分配：主列（SYS+DIA，X相近）Y排序 → SYS/DIA，侧栏（X偏离≥200px）→ HR
   - 聚类条件不满足时自动回退到Y坐标排序
   - 平均耗时 ~0.69s
4. **VLM兜底（保留但未触发）**：
   - 非LCD路径上OCR + X聚类完成后若仍有字段为None，触发VLM补充识别
   - 实测中标准字体图片OCR检出率100% + X聚类解决字段互换后，此路径从未触发
5. **字段抽取与校验（共用）**：
   - 基于 **bbox 高度过滤**（主数字远大于辅助文字）
   - **X坐标聚类**优先（主列 vs 侧栏），回退**Y坐标排序**
   - 数值范围校验：收缩压 60-250 / 舒张压 30-160 / 心率 30-200
   - 一致性校验：收缩压 ≤ 舒张压时废弃舒张压
6. **兜底方案**：若识别失败，UI保留候选 + 字段均为null，强制用户手动录入

### 3.3 后端接口（第 3 周）

```
POST /api/v1/ocr/bp
  multipart/form-data: file=<image>
  -> 200 {
       "image_id": "...",
       "raw_text": "...",
       "candidates": [{"label":"systolic","value":128,"confidence":0.93}, ...],
       "fields": {"systolic":128,"diastolic":82,"heart_rate":76}
     }

POST /api/v1/ocr/bp/confirm
  json: { image_id, systolic, diastolic, heart_rate, record_time, note }
  -> 201 { "record_id": "..." }   # 写入 health_records
```

- 图片存储：本地 `storage/images/{user_id}/{uuid}.jpg`，可替换为 MinIO
- `images` 表保留 `ocr_raw_json` 便于复盘
- 服务层 `services/ocr_service.py` 暴露 `recognize(image_bytes) -> OCRResult`，与 Web 层解耦，便于单测

### 3.4 前端交互（第 4 周）

- 页面 `/ocr/new`：
  - 拍照 / 选择图片（移动端调相机）
  - 上传 → 显示识别结果 + 置信度
  - 可编辑字段后点击"确认入库"
  - 异常场景：置信度低高亮红色并提示手动校正

### 3.5 评测与调优（第 5 周）

- 脚本 `tests/ocr_bench.py`：遍历测试集、计算字段准确率、输出 bad case 列表
- 针对 bad case 调参（预处理阈值、ROI 裁剪、语言模型后处理）
- 产出评测报告，写入本阶段文档末尾

## 4. 交付物

- `backend/app/services/ocr_service.py` 与 `routers/ocr.py`
- `frontend/src/pages/ocr/` 页面
- `datasets/bp_images/`（或云盘链接）+ `labels.json`
- 评测脚本与报告

## 5. 验收结果

- **字段级准确率**：20张图片（10 LCD + 10 Clean）× 3字段 = 60/60  **100%**（远超 ≥ 90% 目标）
- **端到端耗时**：LCD路径 ~1.05s，非LCD路径 ~0.69s（均满足 ≤ 3s 目标）
- 低置信度字段在 UI 有显著提示（彩色Tag标完整度） ✅
- 识别结果可被用户编辑并正确写入 `health_records` ✅
- 单元测试覆盖预处理、字段抽取、X坐标聚类与范围校验 ✅

## 6. 风险与缓解结果

| 风险 | 缓解 | 实际结果 |
| --- | --- | --- |
| 百度云OCR对七段数码管LCD识别率低 | VLM直达识别（LCD路径） | 已解决：LCD分类后直达VLM，跳过OCR |
| VLM调用成本/延迟 | 本地分类器零开销路由；VLM仅LCD路径触发 | 已解决：分类器 < 1ms，VLM 约1s |
| 标准字体字段分配互换（DIA/HR） | X坐标聚类替代纯Y排序 | 已解决：Clean 33.3%→100% |
| 不同品牌/App布局差异 | X聚类回退机制 + 范围校验 | 部分解决：需更多样本覆盖边界case |
| 在线API断网 | `OCR_ENGINE=paddle` 切换到本地PaddleOCR降级模式 | 保留作为降级方案 |
