from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db, SIPTrunk, User
from app.core.auth import get_current_user

router = APIRouter()


class SIPTrunkCreate(BaseModel):
    name: str
    uri: str
    username: Optional[str] = None
    password: Optional[str] = None
    region: str = "EU-Frankfurt"


class SIPTrunkResponse(BaseModel):
    id: int
    name: str
    uri: str
    username: Optional[str]
    region: str
    status: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[SIPTrunkResponse])
async def list_sip_trunks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(SIPTrunk).filter(SIPTrunk.user_id == current_user.id).all()


@router.post("/", response_model=SIPTrunkResponse, status_code=status.HTTP_201_CREATED)
async def create_sip_trunk(
    payload: SIPTrunkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trunk = SIPTrunk(
        user_id=current_user.id,
        name=payload.name,
        uri=payload.uri,
        username=payload.username,
        password=payload.password,
        region=payload.region,
    )
    db.add(trunk)
    db.commit()
    db.refresh(trunk)
    return trunk


@router.delete("/{trunk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sip_trunk(
    trunk_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trunk = db.query(SIPTrunk).filter(
        SIPTrunk.id == trunk_id, SIPTrunk.user_id == current_user.id
    ).first()
    if not trunk:
        raise HTTPException(status_code=404, detail="SIP trunk not found")
    db.delete(trunk)
    db.commit()
