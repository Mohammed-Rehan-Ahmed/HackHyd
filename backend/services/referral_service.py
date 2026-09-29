"""
Referral Service
─────────────────
1. Queries hospital DB for bed availability + specialist availability
2. Selects the best hospital for the patient's triage category
3. Creates a digital referral ticket
4. Triggers WebSocket notification to the receiving hospital
"""

import uuid
import json
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from models.referral import Referral
from models.hospital import Hospital, Specialist
from models.patient import Patient, PatientJourneyLog
from models.asha_worker import ASHAWorker
from services.triage_engine import TriageResult

logger = logging.getLogger(__name__)


class ReferralService:

    def generate_ticket_id(self) -> str:
        date_str = datetime.utcnow().strftime("%Y%m%d")
        short = str(uuid.uuid4())[:8].upper()
        return f"REF-{date_str}-{short}"

    def find_best_hospital(
        self,
        db: Session,
        triage_result: TriageResult,
        exclude_hospital_ids: Optional[List[str]] = None,
    ) -> Tuple[Optional[Hospital], Optional[Specialist]]:
        """
        Queries the hospital database to find the most suitable hospital:
          - Must have available beds (ICU if CRITICAL)
          - Must have required specialist available
          - Preference: tertiary > secondary > phc (for HIGH/CRITICAL)
        """
        exclude = exclude_hospital_ids or []

        # Build query
        query = db.query(Hospital).filter(
            Hospital.is_active == True,
            Hospital.id.notin_(exclude),
        )

        if triage_result.priority == "CRITICAL":
            query = query.filter(
                Hospital.available_icu_beds > 0,
                Hospital.type.in_(["secondary", "tertiary"]),
            )
        elif triage_result.priority == "HIGH":
            query = query.filter(
                Hospital.available_beds > 0,
                Hospital.type.in_(["secondary", "tertiary"]),
            )
        else:
            query = query.filter(Hospital.available_beds > 0)

        # Order: tertiary first
        type_order = {"tertiary": 0, "secondary": 1, "phc": 2}
        hospitals: List[Hospital] = query.all()
        hospitals.sort(key=lambda h: type_order.get(h.type, 3))

        specialist = None
        chosen_hospital = None

        for hospital in hospitals:
            specialties = json.loads(hospital.specialties or "[]")
            # Check if specialist is available
            spec = db.query(Specialist).filter(
                Specialist.hospital_id == hospital.id,
                Specialist.specialty == triage_result.specialist_needed,
                Specialist.is_available == True,
            ).first()

            if spec:
                chosen_hospital = hospital
                specialist = spec
                break
            elif triage_result.priority in ("CRITICAL", "HIGH") and chosen_hospital is None:
                # Take the best hospital even without specialist match
                chosen_hospital = hospital

        return chosen_hospital, specialist

    def create_referral(
        self,
        db: Session,
        patient: Patient,
        triage_result: TriageResult,
        asha_worker_id: str,
        hospital: Hospital,
        specialist: Optional[Specialist] = None,
        origin_phc_id: Optional[str] = None,
        transport_mode: str = "ambulance",
    ) -> Referral:
        """Creates and persists the digital referral ticket."""
        ticket_id = self.generate_ticket_id()

        referral = Referral(
            id=ticket_id,
            patient_id=patient.id,
            asha_worker_id=asha_worker_id,
            origin_phc_id=origin_phc_id,
            destination_hospital_id=hospital.id,
            assigned_specialist_id=specialist.id if specialist else None,
            triage_score=triage_result.score,
            triage_priority=triage_result.priority,
            triage_category=triage_result.category,
            triage_notes="; ".join(triage_result.reasoning),
            status="PENDING",
            transport_mode=transport_mode,
            created_at=datetime.utcnow(),
            hospital_notified=False,
        )

        # Decrement available beds optimistically
        if triage_result.needs_icu and hospital.available_icu_beds > 0:
            hospital.available_icu_beds -= 1
        elif hospital.available_beds > 0:
            hospital.available_beds -= 1

        db.add(referral)

        # Log journey
        db.add(PatientJourneyLog(
            patient_id=patient.id,
            referral_id=ticket_id,
            status="REFERRED",
            location=hospital.name,
            notes=f"Ticket {ticket_id} generated. Priority: {triage_result.priority}",
            logged_by=asha_worker_id,
        ))

        # Update ASHA worker stats
        worker = db.query(ASHAWorker).filter(ASHAWorker.id == asha_worker_id).first()
        if worker:
            worker.total_referrals += 1

        db.commit()
        db.refresh(referral)
        logger.info(f"[REFERRAL] Ticket {ticket_id} created for patient {patient.id} → {hospital.name}")
        return referral

    def build_hospital_notification(
        self,
        referral: Referral,
        patient: Patient,
        triage_result: TriageResult,
        specialist: Optional[Specialist],
    ) -> dict:
        """Builds the WebSocket payload pushed to the hospital dashboard."""
        return {
            "type": "NEW_REFERRAL",
            "referral_id": referral.id,
            "priority": triage_result.priority,
            "priority_color": triage_result.color,
            "action_required": triage_result.action,
            "patient": {
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
                "village": patient.village,
            },
            "triage": {
                "score": triage_result.score,
                "category": triage_result.category,
                "specialist_needed": triage_result.specialist_needed,
                "needs_icu": triage_result.needs_icu,
                "vitals_flags": triage_result.vitals_flags,
            },
            "assigned_specialist": {
                "name": specialist.name,
                "contact": specialist.contact,
            } if specialist else None,
            "transport_mode": referral.transport_mode,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def build_asha_confirmation(self, referral: Referral, hospital: Hospital) -> dict:
        """Builds the WebSocket payload sent back to the ASHA worker's app."""
        return {
            "type": "REFERRAL_CONFIRMED",
            "ticket_id": referral.id,
            "hospital_name": hospital.name,
            "hospital_address": f"{hospital.district}, {hospital.state}",
            "hospital_emergency": hospital.emergency_number,
            "priority": referral.triage_priority,
            "transport_mode": referral.transport_mode,
            "message": (
                f"Referral {referral.id} confirmed. "
                f"Proceed to {hospital.name} immediately."
                if referral.triage_priority in ("CRITICAL", "HIGH")
                else f"Referral {referral.id} created. Visit {hospital.name} at the earliest."
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }


referral_service = ReferralService()
