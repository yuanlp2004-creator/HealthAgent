from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.bp_record import (
    BpRecordCreate,
    BpRecordForecast,
    BpRecordListOut,
    BpRecordOut,
    BpRecordStats,
    BpRecordUpdate,
)
from app.services import bp_record_service
from app.services.bp_record_service import BpRecordNotFoundError

router = APIRouter(prefix="/bp-records", tags=["bp-records"])


@router.post("", response_model=BpRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: BpRecordCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = bp_record_service.create(db, current.id, payload)
    return BpRecordOut.model_validate(rec)


@router.get("", response_model=BpRecordListOut)
def list_records(
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total, items = bp_record_service.list_records(
        db, current.id, start=start, end=end, page=page, size=size
    )
    return BpRecordListOut(
        total=total,
        page=page,
        size=size,
        items=[BpRecordOut.model_validate(r) for r in items],
    )


@router.get("/stats", response_model=BpRecordStats)
def get_stats(
    days: int = Query(default=30, ge=1, le=365),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BpRecordStats(**bp_record_service.stats(db, current.id, days=days))


@router.get("/forecast", response_model=BpRecordForecast)
def get_forecast(
    days: int = Query(default=7, ge=1, le=30),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BpRecordForecast(**bp_record_service.forecast(db, current.id, days=days))


@router.get("/{rec_id}", response_model=BpRecordOut)
def get_record(
    rec_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rec = bp_record_service.get(db, current.id, rec_id)
    except BpRecordNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return BpRecordOut.model_validate(rec)


@router.patch("/{rec_id}", response_model=BpRecordOut)
def update_record(
    rec_id: int,
    payload: BpRecordUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rec = bp_record_service.update(db, current.id, rec_id, payload)
    except BpRecordNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return BpRecordOut.model_validate(rec)


@router.delete("/{rec_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    rec_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        bp_record_service.delete(db, current.id, rec_id)
    except BpRecordNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return None
