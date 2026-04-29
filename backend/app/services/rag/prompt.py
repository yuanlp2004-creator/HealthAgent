from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.services.rag.retriever import RetrievedCitation
from app.services import bp_record_service


SYSTEM_PROMPT = """你是一个负责任的个人健康助手，面向使用本应用的具体用户。请严格遵守：
1. **只根据下方提供的知识库片段作答**；若资料不足，坦诚告知"资料不足，建议咨询医生"，不要编造。
2. 在回答中涉及事实性陈述时，必须以 [1]、[2] 等标注引用，编号对应"知识库片段"列表中的序号。
3. **不得给出具体的药物剂量、加药/减药/停药建议**。涉及用药调整一律回复"需由医生评估"。
4. 不得给出确定性诊断。描述可能性时使用"提示"、"可能"、"建议就医排查"等措辞。
5. 结合"用户近 14 天血压概况"给出个性化解读，但不得臆测未提供的数据。
6. 末尾始终包含一行免责声明："以上内容仅供参考，不构成医疗诊断。"
"""


@dataclass
class UserHealthContext:
    """Digest of the user's recent bp data, injected into the prompt."""

    count: int
    window_days: int
    systolic_avg: Optional[float] = None
    systolic_max: Optional[int] = None
    systolic_min: Optional[int] = None
    diastolic_avg: Optional[float] = None
    heart_rate_avg: Optional[float] = None
    out_of_range_count: int = 0  # how many readings exceeded 140/90

    def render(self) -> str:
        if self.count == 0:
            return f"用户近 {self.window_days} 天内没有血压记录。"
        lines = [
            f"- 记录条数：{self.count}",
            f"- 收缩压均值：{self.systolic_avg} mmHg（范围 {self.systolic_min}–{self.systolic_max}）",
            f"- 舒张压均值：{self.diastolic_avg} mmHg",
        ]
        if self.heart_rate_avg is not None:
            lines.append(f"- 心率均值：{self.heart_rate_avg} bpm")
        lines.append(
            f"- 其中 {self.out_of_range_count} 条读数达到或超过 140/90 mmHg"
        )
        return "\n".join(lines)


def build_user_context(db: Session, user_id: int, *, days: int = 14) -> UserHealthContext:
    stats = bp_record_service.stats(db, user_id, days=days)

    # count out-of-range manually
    from app.models.bp_record import BpRecord

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    oor = (
        db.query(BpRecord)
        .filter(
            BpRecord.user_id == user_id,
            BpRecord.measured_at >= cutoff,
            ((BpRecord.systolic >= 140) | (BpRecord.diastolic >= 90)),
        )
        .count()
    )
    return UserHealthContext(
        count=stats["count"],
        window_days=stats["window_days"],
        systolic_avg=stats.get("systolic_avg"),
        systolic_max=stats.get("systolic_max"),
        systolic_min=stats.get("systolic_min"),
        diastolic_avg=stats.get("diastolic_avg"),
        heart_rate_avg=stats.get("heart_rate_avg"),
        out_of_range_count=oor,
    )


def render_citations(citations: list[RetrievedCitation]) -> str:
    if not citations:
        return "（检索未命中知识库任何片段。）"
    blocks: list[str] = []
    for c in citations:
        header = f"[{c.idx}] {c.title}"
        if c.heading_path:
            header += f" · {c.heading_path}"
        if c.source:
            header += f"（来源：{c.source}）"
        blocks.append(f"{header}\n{c.text}")
    return "\n\n".join(blocks)


def build_user_message(
    question: str,
    citations: list[RetrievedCitation],
    context: Optional[UserHealthContext],
) -> str:
    parts: list[str] = []
    if context is not None:
        parts.append(f"【用户近 {context.window_days} 天血压概况】\n{context.render()}")
    parts.append(f"【知识库片段】\n{render_citations(citations)}")
    parts.append(f"【用户问题】\n{question}")
    return "\n\n".join(parts)
