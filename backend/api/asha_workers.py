from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from models.asha_worker import ASHAWorker

router = APIRouter()

@router.get("/")
def list_workers(db: Session = Depends(get_db)):
    workers = db.query(ASHAWorker).filter(ASHAWorker.is_active == True).all()
    return [{"id": w.id, "name": w.name, "village": w.village, "district": w.district,
             "phc_id": w.phc_id, "total_referrals": w.total_referrals} for w in workers]

@router.get("/{worker_id}")
def get_worker(worker_id: str, db: Session = Depends(get_db)):
    w = db.query(ASHAWorker).filter(ASHAWorker.id == worker_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="ASHA worker not found")
    return w
