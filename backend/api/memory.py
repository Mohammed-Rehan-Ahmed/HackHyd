"""
Memory API
───────────
GET  /api/memory/patient       — recall history for a patient by name + village
GET  /api/memory/village       — recall village-level health patterns
GET  /api/memory/phc           — recall PHC doctor availability history
POST /api/memory/retain-outcome — store treatment outcome after discharge
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.memory_service import (
    recall_patient_history,
    recall_village_patterns,
    recall_phc_availability,
    retain_outcome,
)

router = APIRouter()


@router.get("/patient")
async def get_patient_memory(
    name: str = Query(..., description="Patient full name"),
    village: str = Query(..., description="Patient's village"),
    age: Optional[int] = Query(None, description="Patient age (optional, improves match)"),
    gender: Optional[str] = Query(None, description="Patient gender"),
    contact: Optional[str] = Query(None, description="Patient contact number"),
):
    """
    Recall everything Hindsight knows about this patient.
    Used by the ASHA app before submitting a new referral.

    If the same patient comes again, this endpoint returns their
    full past referral history, symptoms, diagnosis, and outcome.
    """
    result = await recall_patient_history(
        patient_name=name,
        village=village,
        age=age,
        gender=gender,
        contact=contact,
    )
    return {
        "patient_name": name,
        "village": village,
        "returning_patient": result.get("found", False),
        "history_summary": result.get("summary", ""),
        "raw_memories": result.get("raw_memories", []),
        "memory_count": len(result.get("raw_memories", [])),
    }


@router.get("/village")
async def get_village_patterns(
    village: str = Query(...),
    district: str = Query(...),
):
    """Return common health patterns and referral history for a village."""
    return await recall_village_patterns(village=village, district=district)


@router.get("/phc")
async def get_phc_availability(phc_id: str = Query(...)):
    """Return PHC doctor availability history from memory."""
    return await recall_phc_availability(phc_id=phc_id)


class OutcomeRequest(BaseModel):
    referral_id: str
    patient_name: str
    village: str
    asha_worker_id: str
    diagnosis: str
    medication: str
    outcome: str
    phc_id: Optional[str] = None


@router.post("/retain-outcome")
async def store_outcome(body: OutcomeRequest):
    """
    Store the final treatment outcome into Hindsight memory.
    Called when a referral status moves to DISCHARGED.
    """
    await retain_outcome(
        referral_id=body.referral_id,
        patient_name=body.patient_name,
        village=body.village,
        asha_worker_id=body.asha_worker_id,
        diagnosis=body.diagnosis,
        medication=body.medication,
        outcome=body.outcome,
        phc_id=body.phc_id,
    )
    return {"message": "Outcome stored in memory", "referral_id": body.referral_id}