from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from database.db import get_db
from models.referral import Referral
from models.patient import Patient, PatientJourneyLog
from models.hospital import Specialist
import json

router = APIRouter()

@router.get("/")
def list_referrals(
    priority: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Referral)
    if priority:
        q = q.filter(Referral.triage_priority == priority.upper())
    if status:
        q = q.filter(Referral.status == status.upper())

    referrals = q.order_by(Referral.created_at.desc()).all()

    result = []
    for r in referrals:
        # ── JOIN patient to get actual name + village ──────────────────────
        patient = db.query(Patient).filter(Patient.id == r.patient_id).first()
        specialist = None
        if r.assigned_specialist_id:
            specialist = db.query(Specialist).filter(
                Specialist.id == r.assigned_specialist_id
            ).first()

        result.append({
            "id": r.id,
            # Bug 1 fix: return actual patient name, not just the ID
            "patient_id":   r.patient_id,
            "patient_name": patient.name    if patient    else r.patient_id,
            "village":      patient.village if patient    else "—",
            "district":     patient.district if patient   else "—",
            "category":     r.triage_category             or "—",
            "priority":     r.triage_priority,
            "specialist":   specialist.name if specialist else "—",
            "status":       r.status,
            "created_at":   r.created_at,
        })
    return result