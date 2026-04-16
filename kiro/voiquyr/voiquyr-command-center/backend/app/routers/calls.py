from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db, Call, User
from app.core.auth import get_current_user

router = APIRouter()


class CallResponse(BaseModel):
    id: int
    call_id: str
    from_number: str
    to_number: str
    status: str
    duration: int
    cost: float
    started_at: datetime
    ended_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[CallResponse])
async def list_calls(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Call).filter(Call.user_id == current_user.id).order_by(Call.started_at.desc()).limit(100).all()


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    call = db.query(Call).filter(
        Call.call_id == call_id, Call.user_id == current_user.id
    ).first()
    if not call:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Call not found")
    return call
