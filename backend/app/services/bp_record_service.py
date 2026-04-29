from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bp_record import BpRecord
from app.schemas.bp_record import BpRecordCreate, BpRecordUpdate


class BpRecordNotFoundError(Exception):
    pass


def create(db: Session, user_id: int, data: BpRecordCreate) -> BpRecord:
    rec = BpRecord(user_id=user_id, **data.model_dump())
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def get(db: Session, user_id: int, rec_id: int) -> BpRecord:
    rec = db.get(BpRecord, rec_id)
    if rec is None or rec.user_id != user_id:
        raise BpRecordNotFoundError(f"record {rec_id} not found")
    return rec


def update(db: Session, user_id: int, rec_id: int, data: BpRecordUpdate) -> BpRecord:
    rec = get(db, user_id, rec_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rec, field, value)
    db.commit()
    db.refresh(rec)
    return rec


def delete(db: Session, user_id: int, rec_id: int) -> None:
    rec = get(db, user_id, rec_id)
    db.delete(rec)
    db.commit()


def list_records(
    db: Session,
    user_id: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[int, list[BpRecord]]:
    q = db.query(BpRecord).filter(BpRecord.user_id == user_id)
    if start is not None:
        q = q.filter(BpRecord.measured_at >= start)
    if end is not None:
        q = q.filter(BpRecord.measured_at <= end)
    total = q.count()
    items = (
        q.order_by(BpRecord.measured_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return total, items


def stats(db: Session, user_id: int, days: int = 30) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(BpRecord).filter(
        BpRecord.user_id == user_id,
        BpRecord.measured_at >= cutoff,
    )
    items = q.all()
    result = {"count": len(items), "window_days": days}
    if not items:
        return result
    sys_vals = [r.systolic for r in items]
    dia_vals = [r.diastolic for r in items]
    hr_vals = [r.heart_rate for r in items if r.heart_rate is not None]
    result.update(
        systolic_avg=round(sum(sys_vals) / len(sys_vals), 1),
        systolic_max=max(sys_vals),
        systolic_min=min(sys_vals),
        diastolic_avg=round(sum(dia_vals) / len(dia_vals), 1),
        diastolic_max=max(dia_vals),
        diastolic_min=min(dia_vals),
        heart_rate_avg=round(sum(hr_vals) / len(hr_vals), 1) if hr_vals else None,
    )
    return result


def _moving_average(values: list[float], window: int) -> list[float]:
    out: list[float] = []
    for i in range(len(values)):
        lo = max(0, i - window + 1)
        chunk = values[lo : i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def forecast(db: Session, user_id: int, days: int = 7) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    items = (
        db.query(BpRecord)
        .filter(BpRecord.user_id == user_id, BpRecord.measured_at >= cutoff)
        .order_by(BpRecord.measured_at.asc())
        .all()
    )
    if len(items) < 3:
        return {
            "window": days,
            "points": [],
            "trend": "unknown",
            "message": "数据不足，至少需要 3 条记录才能给出趋势提示",
        }

    by_day: dict[str, list[BpRecord]] = {}
    for r in items:
        key = r.measured_at.date().isoformat()
        by_day.setdefault(key, []).append(r)
    daily_sys: list[tuple[str, float]] = []
    daily_dia: list[tuple[str, float]] = []
    for key in sorted(by_day.keys()):
        rs = by_day[key]
        daily_sys.append((key, sum(r.systolic for r in rs) / len(rs)))
        daily_dia.append((key, sum(r.diastolic for r in rs) / len(rs)))

    window = min(7, len(daily_sys))
    sys_ma = _moving_average([v for _, v in daily_sys], window)
    dia_ma = _moving_average([v for _, v in daily_dia], window)

    points = [
        {"date": daily_sys[i][0], "systolic": round(sys_ma[i], 1), "diastolic": round(dia_ma[i], 1)}
        for i in range(len(daily_sys))
    ]

    recent = sys_ma[-min(7, len(sys_ma)) :]
    prev = sys_ma[: -len(recent)] or [sys_ma[0]]
    recent_avg = sum(recent) / len(recent)
    prev_avg = sum(prev) / len(prev)
    delta = recent_avg - prev_avg
    pct = (delta / prev_avg * 100) if prev_avg else 0.0

    if pct > 3:
        trend = "up"
        msg = f"近 {len(recent)} 天收缩压均值较前期上升 {pct:.1f}%，建议关注饮食与情绪"
    elif pct < -3:
        trend = "down"
        msg = f"近 {len(recent)} 天收缩压均值较前期下降 {abs(pct):.1f}%，继续保持"
    else:
        trend = "stable"
        msg = f"近 {len(recent)} 天收缩压均值波动 {pct:+.1f}%，整体平稳"

    return {"window": days, "points": points, "trend": trend, "message": msg}
