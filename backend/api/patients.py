from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from models.patient import Patient, PatientJourneyLog
import json

router = APIRouter()

@router.get("/")
def list_patients(db: Session = Depends(get_db)):
    patients = db.query(Patient).filter(Patient.is_active == True).all()
    return [{"id": p.id, "name": p.name, "age": p.age, "village": p.village, "registered_at": p.registered_at} for p in patients]

@router.get("/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "id": p.id, "name": p.name, "age": p.age, "gender": p.gender,
        "village": p.village, "district": p.district,
        "symptoms": json.loads(p.symptoms),
        "vitals": {
            "temperature": p.temperature,
            "bp_systolic": p.blood_pressure_systolic,
            "bp_diastolic": p.blood_pressure_diastolic,
            "pulse_rate": p.pulse_rate,
            "spo2": p.spo2,
        },
        "registered_at": p.registered_at,
    }

@router.get("/{patient_id}/journey")
def get_patient_journey(patient_id: str, db: Session = Depends(get_db)):
    logs = db.query(PatientJourneyLog).filter(PatientJourneyLog.patient_id == patient_id).order_by(PatientJourneyLog.logged_at).all()
    return [{"status": l.status, "location": l.location, "notes": l.notes, "logged_at": l.logged_at} for l in logs]
