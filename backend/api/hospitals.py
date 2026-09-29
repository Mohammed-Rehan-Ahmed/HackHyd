from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database.db import get_db
from models.hospital import Hospital, Specialist
import json

router = APIRouter()

class BedUpdate(BaseModel):
    available_beds: Optional[int] = None
    available_icu_beds: Optional[int] = None

@router.get("/")
def list_hospitals(type: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Hospital).filter(Hospital.is_active == True)
    if type:
        q = q.filter(Hospital.type == type)
    return [{"id": h.id, "name": h.name, "type": h.type, "district": h.district,
             "available_beds": h.available_beds, "available_icu_beds": h.available_icu_beds,
             "specialties": json.loads(h.specialties or "[]"),
             "emergency_number": h.emergency_number} for h in q.all()]

@router.get("/{hospital_id}")
def get_hospital(hospital_id: str, db: Session = Depends(get_db)):
    h = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hospital not found")
    specialists = db.query(Specialist).filter(Specialist.hospital_id == hospital_id).all()
    return {
        "id": h.id, "name": h.name, "type": h.type, "district": h.district,
        "total_beds": h.total_beds, "available_beds": h.available_beds,
        "icu_beds": h.icu_beds, "available_icu_beds": h.available_icu_beds,
        "specialties": json.loads(h.specialties or "[]"),
        "contact_number": h.contact_number, "emergency_number": h.emergency_number,
        "specialists": [{"id": s.id, "name": s.name, "specialty": s.specialty,
                         "is_available": s.is_available} for s in specialists],
    }

@router.patch("/{hospital_id}/beds")
def update_beds(hospital_id: str, body: BedUpdate, db: Session = Depends(get_db)):
    h = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hospital not found")
    if body.available_beds is not None:
        h.available_beds = body.available_beds
    if body.available_icu_beds is not None:
        h.available_icu_beds = body.available_icu_beds
    db.commit()
    return {"message": "Beds updated", "available_beds": h.available_beds, "available_icu_beds": h.available_icu_beds}

@router.get("/{hospital_id}/availability")
def check_availability(hospital_id: str, db: Session = Depends(get_db)):
    h = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hospital not found")
    specialists = db.query(Specialist).filter(
        Specialist.hospital_id == hospital_id, Specialist.is_available == True).all()
    return {
        "hospital_id": hospital_id,
        "available_beds": h.available_beds,
        "available_icu_beds": h.available_icu_beds,
        "available_specialists": [{"name": s.name, "specialty": s.specialty} for s in specialists],
    }
