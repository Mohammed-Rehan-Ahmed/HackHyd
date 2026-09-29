"""
Triage API — with Hindsight persistent memory
───────────────────────────────────────────────
POST /api/triage/evaluate  — Run triage only (no DB write, no memory)
POST /api/triage/refer     — Full workflow:
                              1. recall()  — check returning patient
                              2. register patient
                              3. run triage engine
                              4. find best hospital (bed + specialist query)
                              5. create digital referral ticket
                              6. ask_triage_agent() — Groq + memory clinical note
                              7. retain()  — store in Hindsight
                              8. WebSocket notify hospital + ASHA worker
"""

import uuid
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from database.db import get_db
from models.patient import Patient, PatientJourneyLog
from services.triage_engine import PatientInput, VitalsInput, triage_engine
from services.referral_service import referral_service
from services.notification_service import NotificationService
from services.memory_service import (
    recall_patient_history,
    retain_referral,
    ask_triage_agent,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class VitalsSchema(BaseModel):
    temperature: Optional[float] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    pulse_rate: Optional[int] = None
    spo2: Optional[float] = None
    weight: Optional[float] = None


class TriageRequest(BaseModel):
    symptoms: List[str] = Field(..., min_items=1)
    age: int
    gender: str
    symptom_duration_hours: int = 0
    vitals: Optional[VitalsSchema] = None
    is_pregnant: bool = False
    comorbidities: List[str] = []
    notes: str = ""


class ReferAndNotifyRequest(BaseModel):
    patient_name: str
    age: int
    gender: str
    village: str
    district: str
    contact: Optional[str] = None
    symptoms: List[str]
    symptom_duration_hours: int = 0
    vitals: Optional[VitalsSchema] = None
    is_pregnant: bool = False
    comorbidities: List[str] = []
    notes: str = ""
    asha_worker_id: str
    origin_phc_id: Optional[str] = None
    transport_mode: str = "ambulance"


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/evaluate")
async def evaluate_triage(req: TriageRequest):
    """Triage only — no DB, no memory."""
    vitals = VitalsInput(**req.vitals.dict()) if req.vitals else None
    patient_input = PatientInput(
        symptoms=req.symptoms, age=req.age, gender=req.gender,
        symptom_duration_hours=req.symptom_duration_hours,
        vitals=vitals, is_pregnant=req.is_pregnant,
        comorbidities=req.comorbidities, notes=req.notes,
    )
    result = triage_engine.evaluate(patient_input)
    return {
        "score": result.score, "priority": result.priority,
        "category": result.category, "specialist_needed": result.specialist_needed,
        "action": result.action, "color": result.color,
        "needs_icu": result.needs_icu, "needs_referral": result.needs_referral,
        "symptom_breakdown": result.symptom_breakdown,
        "vitals_flags": result.vitals_flags, "reasoning": result.reasoning,
    }


@router.post("/refer")
async def triage_and_refer(
    req: ReferAndNotifyRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Full workflow with Hindsight memory:

    BEFORE  → recall() to detect returning patient
    DURING  → triage + hospital selection + ticket creation
    AFTER   → Groq clinical note (memory-augmented) + retain()
    """

    # ── Step 0: RECALL — check if this patient has been here before ───────────
    logger.info(f"[MEMORY] Recalling history for {req.patient_name} / {req.village}")
    past_history = await recall_patient_history(
    patient_name=req.patient_name,
    village=req.village,
    age=req.age,
    gender=req.gender,       # ← add this
    contact=req.contact,     # ← add this
)
    returning_patient = past_history.get("found", False)
    if returning_patient:
        logger.info(f"[MEMORY] ⚠️ RETURNING PATIENT detected: {req.patient_name}")

    # ── Step 1: Register patient ──────────────────────────────────────────────
    patient_id = f"PAT-{str(uuid.uuid4())[:8].upper()}"
    patient = Patient(
        id=patient_id,
        name=req.patient_name,
        age=req.age,
        gender=req.gender,
        village=req.village,
        district=req.district,
        contact=req.contact,
        symptoms=json.dumps(req.symptoms),
        symptom_duration_hours=req.symptom_duration_hours,
        notes=req.notes,
        asha_worker_id=req.asha_worker_id,
        temperature=req.vitals.temperature if req.vitals else None,
        blood_pressure_systolic=req.vitals.bp_systolic if req.vitals else None,
        blood_pressure_diastolic=req.vitals.bp_diastolic if req.vitals else None,
        pulse_rate=req.vitals.pulse_rate if req.vitals else None,
        spo2=req.vitals.spo2 if req.vitals else None,
        weight=req.vitals.weight if req.vitals else None,
    )
    db.add(patient)
    db.add(PatientJourneyLog(
        patient_id=patient_id,
        status="REGISTERED",
        location=req.village,
        notes=f"Registered by ASHA {req.asha_worker_id}. Returning: {returning_patient}",
        logged_by=req.asha_worker_id,
    ))

    # ── Step 2: Triage ────────────────────────────────────────────────────────
    vitals = VitalsInput(**req.vitals.dict()) if req.vitals else None
    patient_input = PatientInput(
        symptoms=req.symptoms, age=req.age, gender=req.gender,
        symptom_duration_hours=req.symptom_duration_hours,
        vitals=vitals, is_pregnant=req.is_pregnant,
        comorbidities=req.comorbidities, notes=req.notes,
    )
    triage_result = triage_engine.evaluate(patient_input)

    # ── Step 3: Find best hospital ────────────────────────────────────────────
    hospital, specialist = referral_service.find_best_hospital(db, triage_result)
    if not hospital:
        db.commit()
        return {
            "status": "NO_BED_AVAILABLE",
            "patient_id": patient_id,
            "returning_patient": returning_patient,
            "past_history": past_history.get("summary", ""),
            "triage": {
                "score": triage_result.score,
                "priority": triage_result.priority,
                "action": triage_result.action,
            },
        }

    # ── Step 4: Create referral ticket ────────────────────────────────────────
    referral = referral_service.create_referral(
        db=db, patient=patient, triage_result=triage_result,
        asha_worker_id=req.asha_worker_id, hospital=hospital,
        specialist=specialist, origin_phc_id=req.origin_phc_id,
        transport_mode=req.transport_mode,
    )

    # ── Step 5: Groq clinical note (memory-augmented) ─────────────────────────
    triage_dict = {
        "score": triage_result.score,
        "priority": triage_result.priority,
        "category": triage_result.category,
        "specialist_needed": triage_result.specialist_needed,
        "action": triage_result.action,
    }
    clinical_note = await ask_triage_agent(
        patient_name=req.patient_name,
        village=req.village,
        symptoms=req.symptoms,
        triage_result=triage_dict,
        past_history=past_history,
    )

    # ── Step 6: RETAIN — store this referral in Hindsight ────────────────────
    await retain_referral(
        patient_name=req.patient_name,
        age=req.age,
        gender=req.gender,
        village=req.village,
        district=req.district,
        symptoms=req.symptoms,
        triage_priority=triage_result.priority,
        triage_score=triage_result.score,
        triage_category=triage_result.category,
        referral_id=referral.id,
        hospital_name=hospital.name,
        specialist_name=specialist.name if specialist else None,
        specialist_specialty=specialist.specialty if specialist else None,
        asha_worker_id=req.asha_worker_id,
        phc_id=req.origin_phc_id,
        transport_mode=req.transport_mode,
    )
    logger.info(f"[MEMORY] ✅ Referral {referral.id} retained in Hindsight")

    # ── Step 7: WebSocket notifications ──────────────────────────────────────
    manager = request.app.state.manager
    notification_service = NotificationService(manager)

    hospital_payload = referral_service.build_hospital_notification(
        referral, patient, triage_result, specialist
    )
    # Enrich hospital payload with memory context
    hospital_payload["clinical_note"] = clinical_note
    hospital_payload["returning_patient"] = returning_patient
    if returning_patient:
        hospital_payload["past_history_summary"] = past_history.get("summary", "")

    asha_payload = referral_service.build_asha_confirmation(referral, hospital)

    await notification_service.push_referral_to_hospital(hospital.id, hospital_payload)
    await notification_service.push_confirmation_to_asha(req.asha_worker_id, asha_payload)

    referral.hospital_notified = True
    db.commit()

    return {
        "status": "REFERRAL_CREATED",
        "ticket_id": referral.id,
        "patient_id": patient_id,
        # ── Memory context ────────────────────────────────────────────────────
        "returning_patient": returning_patient,
        "past_history": {
            "found": past_history.get("found", False),
            "summary": past_history.get("summary", ""),
            "memory_count": len(past_history.get("raw_memories", [])),
        },
        "clinical_note": clinical_note,          # Groq-generated, memory-augmented
        # ── Triage ────────────────────────────────────────────────────────────
        "triage": {
            "score": triage_result.score,
            "priority": triage_result.priority,
            "category": triage_result.category,
            "action": triage_result.action,
            "color": triage_result.color,
            "needs_icu": triage_result.needs_icu,
        },
        # ── Hospital ──────────────────────────────────────────────────────────
        "hospital": {
            "id": hospital.id,
            "name": hospital.name,
            "district": hospital.district,
            "emergency_number": hospital.emergency_number,
            "available_beds": hospital.available_beds,
        },
        "specialist": {
            "name": specialist.name,
            "specialty": specialist.specialty,
            "contact": specialist.contact,
        } if specialist else None,
        "transport_mode": req.transport_mode,
    }
