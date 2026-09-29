"""
Healthcare Persistent Memory Service
──────────────────────────────────────
Uses Hindsight (via hindsight-litellm wrapper) + Groq LLM for:

  • retain()  — store referral events after creation
  • recall()  — check if patient / village / PHC was seen before
  • reflect() — synthesize a clinical summary for returning patients

Memory Banks (one per village — entities from the existing codebase):
  village-{village_slug}   →  all patients from that village
  phc-{phc_id}             →  PHC doctor availability patterns
  asha-{worker_id}         →  per-ASHA worker history

Entities extracted automatically:
  patient_name, village, district, phc_id, asha_worker_id,
  symptoms, hospital_name, specialist_name, triage_priority,
  referral_id, diagnosis, medication
"""

import logging
import re
from typing import Optional
from datetime import datetime

import hindsight_litellm
from hindsight_litellm import retain, recall, reflect, aretain, arecall, areflect

from config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap — called once at app startup
# ─────────────────────────────────────────────────────────────────────────────

def init_memory():
    """Configure hindsight-litellm with Groq as the LLM backend."""
    hindsight_litellm.configure(
        hindsight_api_url=settings.HINDSIGHT_API_URL,
        api_key=settings.HINDSIGHT_API_KEY or None,
        store_conversations=True,
        inject_memories=True,
        sync_storage=False,   # async — non-blocking after referral
        verbose=settings.DEBUG,
    )

    hindsight_litellm.set_defaults(
        bank_id="healthcare-global",      # overridden per-call
        budget="mid",
        use_reflect=True,
        reflect_context=(
            "I am a rural healthcare triage agent. "
            "I remember past patient referrals, village health patterns, "
            "PHC doctor availability, and treatment outcomes."
        ),
        max_memories=10,
        max_memory_tokens=2048,
    )

    hindsight_litellm.enable()
    logger.info("✅ Hindsight memory initialised (Groq backend)")


# ─────────────────────────────────────────────────────────────────────────────
# Bank ID helpers
# ─────────────────────────────────────────────────────────────────────────────

def _village_bank(village: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", village.lower()).strip("-")
    return f"village-{slug}"

def _phc_bank(phc_id: str) -> str:
    return f"phc-{phc_id.lower()}"

def _asha_bank(worker_id: str) -> str:
    return f"asha-{worker_id.lower()}"


# ─────────────────────────────────────────────────────────────────────────────
# Entity extraction — reads from the existing codebase's data shapes
# ─────────────────────────────────────────────────────────────────────────────

def build_referral_memory_text(
    patient_name: str,
    age: int,
    gender: str,
    village: str,
    district: str,
    symptoms: list,
    triage_priority: str,
    triage_score: int,
    triage_category: str,
    referral_id: str,
    hospital_name: str,
    specialist_name: Optional[str],
    specialist_specialty: Optional[str],
    asha_worker_id: str,
    phc_id: Optional[str],
    transport_mode: str,
    diagnosis: Optional[str] = None,
    medication: Optional[str] = None,
    outcome: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> str:
    """
    Builds a rich natural-language memory string that Hindsight
    will parse into structured facts, observations, and entities.

    Entities Hindsight auto-extracts:
      patient_name  → graph node  (patient)
      village       → graph node  (location)
      hospital_name → graph node  (facility)
      specialist    → graph node  (person / role)
      phc_id        → graph node  (facility)
      asha_worker   → graph node  (person)
      symptoms      → world facts
      triage_priority → world fact
      referral_id   → experience fact
    """
    ts = timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    symptom_str = ", ".join(symptoms)
    spec_str = f"{specialist_name} ({specialist_specialty})" if specialist_name else "none assigned"
    diag_str = f" Diagnosis: {diagnosis}." if diagnosis else ""
    med_str = f" Medication: {medication}." if medication else ""
    outcome_str = f" Outcome: {outcome}." if outcome else ""

    return (
        f"[{ts}] Referral {referral_id}: "
        f"Patient {patient_name}, {age} years old, {gender}, "
        f"from {village} village, {district} district. "
        f"Reported symptoms: {symptom_str}. "
        f"Triage score: {triage_score}, priority: {triage_priority}, "
        f"category: {triage_category}. "
        f"Referred to {hospital_name}. "
        f"Assigned specialist: {spec_str}. "
        f"Transport: {transport_mode}. "
        f"ASHA worker: {asha_worker_id}. "
        f"PHC: {phc_id or 'direct'}.{diag_str}{med_str}{outcome_str}"
    )


def build_phc_availability_memory(
    phc_id: str,
    doctor_name: str,
    specialty: str,
    is_available: bool,
    notes: Optional[str] = None,
) -> str:
    status = "available" if is_available else "unavailable"
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"[{ts}] PHC {phc_id}: Dr. {doctor_name} ({specialty}) is {status}. "
        f"{notes or ''}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Core memory operations
# ─────────────────────────────────────────────────────────────────────────────

async def retain_referral(
    *,
    patient_name: str,
    age: int,
    gender: str,
    village: str,
    district: str,
    symptoms: list,
    triage_priority: str,
    triage_score: int,
    triage_category: str,
    referral_id: str,
    hospital_name: str,
    specialist_name: Optional[str],
    specialist_specialty: Optional[str],
    asha_worker_id: str,
    phc_id: Optional[str],
    transport_mode: str,
    diagnosis: Optional[str] = None,
    medication: Optional[str] = None,
    outcome: Optional[str] = None,
):
    """
    Store a referral event across three banks:
      1. village bank  — patient-level facts indexed by location
      2. ASHA bank     — worker-level history
      3. PHC bank      — if PHC was involved
    """
    memory_text = build_referral_memory_text(
        patient_name=patient_name, age=age, gender=gender,
        village=village, district=district, symptoms=symptoms,
        triage_priority=triage_priority, triage_score=triage_score,
        triage_category=triage_category, referral_id=referral_id,
        hospital_name=hospital_name, specialist_name=specialist_name,
        specialist_specialty=specialist_specialty,
        asha_worker_id=asha_worker_id, phc_id=phc_id,
        transport_mode=transport_mode, diagnosis=diagnosis,
        medication=medication, outcome=outcome,
    )

    village_bank = _village_bank(village)
    asha_bank    = _asha_bank(asha_worker_id)

    # Store in village bank (primary — used for returning patient lookup)
    await aretain(
        content=memory_text,
        bank_id=village_bank,
        context=f"Referral event from {village}, {district}",
        document_id=referral_id,
    )
    logger.info(f"[MEMORY] Retained in village bank '{village_bank}': {referral_id}")

    # Store in ASHA worker bank
    await aretain(
        content=memory_text,
        bank_id=asha_bank,
        context=f"ASHA worker {asha_worker_id} referral history",
        document_id=referral_id,
    )

    # Store in PHC bank if applicable
    if phc_id:
        await aretain(
            content=memory_text,
            bank_id=_phc_bank(phc_id),
            context=f"PHC {phc_id} referral record",
            document_id=referral_id,
        )


async def recall_patient_history(
    patient_name: str,
    village: str,
    age: Optional[int] = None,
    gender: Optional[str] = None,
    contact: Optional[str] = None,
) -> dict:
    """
    Match on all 5 submitted parameters so partial overlaps don't
    trigger false positives (e.g. same name, different village).
    Hindsight's TEMPR runs keyword + entity graph on the full query.
    """
    village_bank = _village_bank(village)

    # Build a rich query string covering all 5 parameters
    query_parts = [f"Patient named {patient_name}", f"from {village} village"]
    if age:
        query_parts.append(f"aged {age}")
    if gender:
        query_parts.append(f"gender {gender}")
    if contact:
        query_parts.append(f"contact {contact}")

    query = ", ".join(query_parts)

    try:
        reflection = await areflect(
            query=query,
            bank_id=village_bank,
            context=(
                "I am checking if this exact patient was referred before. "
                "Match on name AND village as primary keys. "
                "Age, gender, and contact are secondary confirmation signals. "
                "Only return a positive match if name + village both align. "
                "Summarise their previous referral history, symptoms, "
                "hospital visited, diagnosis, and outcome if available."
            ),
        )
        summary = reflection.text if hasattr(reflection, "text") else str(reflection)

        memories = await arecall(query=query, bank_id=village_bank)
        raw = [
            {"text": m.text, "type": getattr(m, "fact_type", "world")}
            for m in (memories or [])
        ]

        # Treat as found only when memory has a substantive match
        no_match_phrases = [
            "no memories", "no information", "no previous",
            "no record", "not found", "cannot find"
        ]
        found = bool(raw) and not any(
            phrase in summary.lower() for phrase in no_match_phrases
        )

        return {
            "found": found,
            "summary": summary,
            "raw_memories": raw,
            "matched_params": {
                "name": patient_name,
                "village": village,
                "age": age,
                "gender": gender,
                "contact": contact,
            }
        }

    except Exception as e:
        logger.warning(f"[MEMORY] Recall failed for {patient_name}/{village}: {e}")
        return {"found": False, "summary": "", "raw_memories": [], "error": str(e)}

async def recall_village_patterns(village: str, district: str) -> dict:
    """
    Returns common health patterns for a village:
    frequent symptoms, common diagnoses, busy seasons.
    Used by the ASHA worker to prep before visiting a patient.
    """
    village_bank = _village_bank(village)
    query = f"Common health issues and referral patterns in {village}, {district}"
    try:
        reflection = await areflect(
            query=query,
            bank_id=village_bank,
            context=(
                "Summarise health patterns for this village: "
                "most common symptoms, frequent diagnoses, typical severity levels, "
                "and which hospitals are used most."
            ),
        )
        return {
            "village": village,
            "district": district,
            "patterns": reflection.text if hasattr(reflection, "text") else str(reflection),
        }
    except Exception as e:
        logger.warning(f"[MEMORY] Village pattern recall failed: {e}")
        return {"village": village, "district": district, "patterns": "", "error": str(e)}


async def recall_phc_availability(phc_id: str) -> dict:
    """Check past PHC doctor availability patterns from memory."""
    try:
        memories = await arecall(
            query=f"PHC {phc_id} doctor availability",
            bank_id=_phc_bank(phc_id),
        )
        raw = [{"text": m.text} for m in (memories or [])]
        return {"phc_id": phc_id, "availability_history": raw}
    except Exception as e:
        return {"phc_id": phc_id, "availability_history": [], "error": str(e)}


async def retain_outcome(
    referral_id: str,
    patient_name: str,
    village: str,
    asha_worker_id: str,
    diagnosis: str,
    medication: str,
    outcome: str,
    phc_id: Optional[str] = None,
):
    """Called when referral is DISCHARGED — stores the outcome for future recall."""
    village_bank = _village_bank(village)
    content = (
        f"Outcome for referral {referral_id}: "
        f"Patient {patient_name} from {village} was diagnosed with {diagnosis}. "
        f"Medication prescribed: {medication}. "
        f"Outcome: {outcome}. "
        f"ASHA worker: {asha_worker_id}."
    )
    await aretain(
        content=content,
        bank_id=village_bank,
        context="Treatment outcome update",
        document_id=f"{referral_id}-outcome",
    )
    if phc_id:
        await aretain(content=content, bank_id=_phc_bank(phc_id), document_id=f"{referral_id}-outcome")
    logger.info(f"[MEMORY] Outcome retained for {referral_id}")


# ─────────────────────────────────────────────────────────────────────────────
# Groq-powered AI triage assistant (uses hindsight_litellm.completion)
# ─────────────────────────────────────────────────────────────────────────────

async def ask_triage_agent(
    patient_name: str,
    village: str,
    symptoms: list,
    triage_result: dict,
    past_history: dict,
) -> str:
    """
    Uses hindsight_litellm.completion with Groq to generate a
    context-aware triage recommendation, enriched with past memory.

    The LLM receives:
      - current symptoms + triage score
      - Hindsight-recalled past referral history (auto-injected)
      - A clinical reasoning prompt
    """
    symptom_str = ", ".join(symptoms)
    history_note = (
        f"\n\nPAST HISTORY (from Hindsight memory):\n{past_history['summary']}"
        if past_history.get("found") and past_history.get("summary")
        else "\n\nNo previous history found for this patient."
    )

    user_message = (
        f"Patient: {patient_name} from {village} village.\n"
        f"Current symptoms: {symptom_str}.\n"
        f"Triage score: {triage_result['score']}, "
        f"Priority: {triage_result['priority']}, "
        f"Category: {triage_result['category']}.\n"
        f"Recommended specialist: {triage_result['specialist_needed']}."
        f"{history_note}\n\n"
        "Based on this patient's current condition and any past history, "
        "provide a brief clinical note for the receiving hospital. "
        "Flag any patterns, allergies, or recurring conditions if known. "
        "Keep it under 100 words."
    )

    try:
        response = hindsight_litellm.completion(
            model=f"groq/{settings.GROQ_MODEL}",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a clinical triage assistant for a rural healthcare referral system. "
                        "You have access to the patient's past referral history through your memory. "
                        "Always be concise and clinically relevant."
                    ),
                },
                {"role": "user", "content": user_message},
            ],
            hindsight_query=f"Past referrals for {patient_name} in {village}",
            bank_id=_village_bank(village),
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"[MEMORY] Groq triage agent failed: {e}")
        return f"[Memory agent unavailable] Standard triage: {triage_result['action']}"
