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

- 采集 ≥ 50 张样本，覆盖：正拍/斜拍、强光/弱光、不同品牌型号、七段数码管与 LCD 点阵
- 标注格式（JSON）：

  ```json
  {"file":"001.jpg","systolic":128,"diastolic":82,"heart_rate":76}
  ```

- 分训练/测试集 8:2（若走微调路径）

### 3.2 OCR 方案落地（第 2 周）

采用 **"百度云数字 OCR（主） + 通义千问 VL（兜底/复检）"双通路** 方案（替代原 PaddleOCR 本地方案，原因见 `docs/P3_测试报告.md` 的实测对比）：

1. **图像预处理**：
   - 灰度化 + CLAHE 对比度增强
   - 长边缩放到 1600-1920 像素，提升小字识别率
   - 可选：Canny 边缘 + 最大四边形检测做透视矫正
2. **主通路：百度云 OCR（`/rest/2.0/ocr/v1/numbers`）**
   - 延迟低（≤ 1s / 张，CPU 无需本地模型），有 bbox、字段抽取可基于 `location` + `height`
3. **兜底通路：通义千问 VL（`qwen-vl-plus`）**
   - 当百度云识别结果缺字段 / 高低压不合常理 / 置信度低时触发
   - Prompt 示例（JSON 结构化输出）：
     ```
     这是一张电子血压计的照片。请只返回 JSON，不要解释：
     {"systolic":<int|null>,"diastolic":<int|null>,"heart_rate":<int|null>}
     无法识别的字段填 null。
     ```
   - 解析模型输出 JSON → 填充字段，视为最终结果
4. **字段抽取（共用）**：
   - 基于 **bbox 高度过滤**（主数字远大于历史记录）
   - **Y 坐标排序**与**数值大小规则**识别收缩压（60-250）/ 舒张压（30-160）/ 心率（30-200）
   - 正则 + 数值范围双重校验；异常（sys ≤ dia）则废弃 diastolic 保留 systolic
5. **兜底方案**：若两路都识别失败，UI 保留候选 + 字段均为 null，强制用户手动录入

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

## 5. 验收标准

- 字段级准确率 ≥ 90%（测试集）
- 低置信度字段在 UI 有显著提示
- 识别结果可被用户编辑并正确写入 `health_records`
- 单元测试覆盖预处理、字段抽取与范围校验

## 6. 风险

| 风险 | 缓解 |
| --- | --- |
| 百度云数字 OCR 对部分机型（OMRON/低对比度 LCD）识别率低 | 通义千问 VL 兜底复检；前端强制用户校正 |
| 通义千问 VL 调用成本/延迟 | 仅在百度云失败时触发；缓存命中的识别结果 |
| 样本量不足 | 允许使用网络公开图片 + 数据增强（旋转、亮度、噪声） |
| 不同品牌布局差异 | 字段抽取采用"数值范围 + bbox 高度过滤 + Y 坐标"启发式 |
| 在线 API 断网 | `OCR_ENGINE=paddle` 切换到本地 PaddleOCR 降级模式 |
