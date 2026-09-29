"""
Intelligent Triage Engine
─────────────────────────
Evaluates patient symptoms + vitals to produce a priority score,
urgency category, specialist recommendation, and referral decision.

Algorithm:
  1. Base symptom score  — weighted sum of reported symptoms
  2. Vitals modifier     — abnormal vitals boost the score
  3. Age modifier        — very young / elderly patients get a bump
  4. Duration modifier   — longer symptom duration increases urgency
  5. Comorbidity check   — chronic conditions escalate priority

Score → Priority mapping:
  ≥ 15 : CRITICAL  (immediate referral, ICU bed query)
  ≥ 8  : HIGH      (referral within 2 hrs)
  ≥ 4  : MEDIUM    (PHC-level treatment first, monitor)
  < 4  : LOW       (outpatient guidance)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import json


# ─────────────────────────────────────────────────────────────────────────────
# Symptom Knowledge Base
# ─────────────────────────────────────────────────────────────────────────────

SYMPTOM_DB: Dict[str, Dict] = {
    # Cardiac
    "chest_pain":               {"score": 10, "category": "cardiac",       "specialist": "Cardiology"},
    "palpitations":             {"score": 5,  "category": "cardiac",       "specialist": "Cardiology"},
    "sudden_arm_pain":          {"score": 8,  "category": "cardiac",       "specialist": "Cardiology"},
    # Neurological
    "unconscious":              {"score": 12, "category": "neurological",   "specialist": "Neurology"},
    "seizures":                 {"score": 10, "category": "neurological",   "specialist": "Neurology"},
    "stroke_symptoms":          {"score": 12, "category": "neurological",   "specialist": "Neurology"},
    "severe_headache":          {"score": 6,  "category": "neurological",   "specialist": "Neurology"},
    "vision_loss":              {"score": 7,  "category": "neurological",   "specialist": "Neurology"},
    "confusion":                {"score": 7,  "category": "neurological",   "specialist": "Neurology"},
    # Respiratory
    "breathlessness":           {"score": 9,  "category": "respiratory",    "specialist": "Pulmonology"},
    "severe_cough":             {"score": 4,  "category": "respiratory",    "specialist": "General Medicine"},
    "cyanosis":                 {"score": 11, "category": "respiratory",    "specialist": "Pulmonology"},
    "wheezing":                 {"score": 5,  "category": "respiratory",    "specialist": "General Medicine"},
    # Trauma
    "severe_bleeding":          {"score": 10, "category": "trauma",         "specialist": "Surgery"},
    "burns":                    {"score": 7,  "category": "trauma",         "specialist": "Surgery"},
    "fracture":                 {"score": 6,  "category": "orthopedic",     "specialist": "Orthopedics"},
    "head_injury":              {"score": 9,  "category": "trauma",         "specialist": "Neurosurgery"},
    # Obstetric
    "pregnancy_complications":  {"score": 10, "category": "obstetric",      "specialist": "Obstetrics"},
    "labour_pain":              {"score": 8,  "category": "obstetric",      "specialist": "Obstetrics"},
    "vaginal_bleeding":         {"score": 9,  "category": "obstetric",      "specialist": "Obstetrics"},
    # Toxicology
    "snake_bite":               {"score": 12, "category": "toxicology",     "specialist": "Emergency Medicine"},
    "poisoning":                {"score": 10, "category": "toxicology",     "specialist": "Emergency Medicine"},
    "scorpion_sting":           {"score": 7,  "category": "toxicology",     "specialist": "Emergency Medicine"},
    # Infectious
    "high_fever":               {"score": 7,  "category": "infectious",     "specialist": "General Medicine"},
    "dengue_symptoms":          {"score": 7,  "category": "infectious",     "specialist": "General Medicine"},
    "malaria_symptoms":         {"score": 7,  "category": "infectious",     "specialist": "General Medicine"},
    "jaundice":                 {"score": 6,  "category": "gastro",         "specialist": "Gastroenterology"},
    # Gastro
    "severe_abdominal_pain":    {"score": 7,  "category": "gastro",         "specialist": "Surgery"},
    "vomiting_blood":           {"score": 9,  "category": "gastro",         "specialist": "Gastroenterology"},
    "severe_diarrhea":          {"score": 5,  "category": "gastro",         "specialist": "General Medicine"},
    # Renal
    "severe_pain_urination":    {"score": 5,  "category": "renal",          "specialist": "Nephrology"},
    "no_urine_output":          {"score": 8,  "category": "renal",          "specialist": "Nephrology"},
    # Pediatric
    "child_convulsion":         {"score": 10, "category": "pediatric",      "specialist": "Pediatrics"},
    "child_severe_malnutrition":{"score": 7,  "category": "pediatric",      "specialist": "Pediatrics"},
    "child_not_breathing":      {"score": 12, "category": "pediatric",      "specialist": "Pediatrics"},
    # General / Low urgency
    "mild_fever":               {"score": 2,  "category": "general",        "specialist": "General Medicine"},
    "headache":                 {"score": 2,  "category": "general",        "specialist": "General Medicine"},
    "body_ache":                {"score": 2,  "category": "general",        "specialist": "General Medicine"},
    "fatigue":                  {"score": 1,  "category": "general",        "specialist": "General Medicine"},
    "vomiting":                 {"score": 3,  "category": "gastro",         "specialist": "General Medicine"},
    "diarrhea":                 {"score": 2,  "category": "gastro",         "specialist": "General Medicine"},
    "skin_rash":                {"score": 2,  "category": "dermatology",    "specialist": "General Medicine"},
}

PRIORITY_LABELS = {
    "CRITICAL": {"min_score": 15, "color": "#FF0000", "action": "Immediate referral. Notify hospital NOW."},
    "HIGH":     {"min_score": 8,  "color": "#FF6600", "action": "Refer within 2 hours. Alert specialist."},
    "MEDIUM":   {"min_score": 4,  "color": "#FFAA00", "action": "PHC treatment first. Monitor every 30 min."},
    "LOW":      {"min_score": 0,  "color": "#00AA00", "action": "Outpatient care. Review in 24 hours."},
}


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VitalsInput:
    temperature: Optional[float] = None           # °C
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    pulse_rate: Optional[int] = None
    spo2: Optional[float] = None
    weight: Optional[float] = None


@dataclass
class PatientInput:
    symptoms: List[str]
    age: int
    gender: str                                    # M / F / Other
    symptom_duration_hours: int = 0
    vitals: Optional[VitalsInput] = None
    is_pregnant: bool = False
    comorbidities: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class TriageResult:
    score: int
    priority: str                                  # CRITICAL / HIGH / MEDIUM / LOW
    category: str                                  # primary symptom category
    specialist_needed: str
    action: str
    color: str
    needs_icu: bool
    needs_referral: bool
    reasoning: List[str]
    symptom_breakdown: List[Dict]
    vitals_flags: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# Triage Engine
# ─────────────────────────────────────────────────────────────────────────────

class TriageEngine:
    """
    Stateless triage calculator. Call `.evaluate(patient_input)` to get a TriageResult.
    """

    def evaluate(self, patient: PatientInput) -> TriageResult:
        reasoning: List[str] = []
        vitals_flags: List[str] = []
        symptom_breakdown: List[Dict] = []

        # ── 1. Symptom scoring ────────────────────────────────────────────────
        base_score = 0
        category_votes: Dict[str, int] = {}
        specialist_votes: Dict[str, int] = {}

        for sym in patient.symptoms:
            sym_key = sym.lower().replace(" ", "_")
            if sym_key in SYMPTOM_DB:
                entry = SYMPTOM_DB[sym_key]
                s = entry["score"]
                base_score += s
                cat = entry["category"]
                spec = entry["specialist"]
                category_votes[cat] = category_votes.get(cat, 0) + s
                specialist_votes[spec] = specialist_votes.get(spec, 0) + s
                symptom_breakdown.append({"symptom": sym_key, "score": s, "category": cat})
                reasoning.append(f"Symptom '{sym_key}' → +{s} pts ({cat})")
            else:
                # Unknown symptom — give a default low score
                base_score += 2
                symptom_breakdown.append({"symptom": sym_key, "score": 2, "category": "unknown"})
                reasoning.append(f"Unknown symptom '{sym_key}' → +2 pts (default)")

        # ── 2. Vitals modifier ────────────────────────────────────────────────
        vitals_score = 0
        if patient.vitals:
            v = patient.vitals
            if v.temperature is not None:
                if v.temperature >= 40.0:
                    vitals_score += 4; vitals_flags.append("Hyperpyrexia (≥40°C) +4")
                elif v.temperature >= 38.5:
                    vitals_score += 2; vitals_flags.append("High fever (≥38.5°C) +2")
                elif v.temperature <= 35.5:
                    vitals_score += 3; vitals_flags.append("Hypothermia (≤35.5°C) +3")

            if v.spo2 is not None:
                if v.spo2 < 85:
                    vitals_score += 6; vitals_flags.append(f"Critical SpO₂ ({v.spo2}%) +6")
                elif v.spo2 < 90:
                    vitals_score += 4; vitals_flags.append(f"Low SpO₂ ({v.spo2}%) +4")
                elif v.spo2 < 95:
                    vitals_score += 2; vitals_flags.append(f"Borderline SpO₂ ({v.spo2}%) +2")

            if v.bp_systolic is not None:
                if v.bp_systolic > 180:
                    vitals_score += 4; vitals_flags.append(f"Hypertensive crisis (SBP {v.bp_systolic}) +4")
                elif v.bp_systolic < 90:
                    vitals_score += 5; vitals_flags.append(f"Hypotension (SBP {v.bp_systolic}) +5")

            if v.pulse_rate is not None:
                if v.pulse_rate > 130 or v.pulse_rate < 40:
                    vitals_score += 4; vitals_flags.append(f"Abnormal pulse ({v.pulse_rate} bpm) +4")
                elif v.pulse_rate > 100:
                    vitals_score += 1; vitals_flags.append(f"Tachycardia ({v.pulse_rate} bpm) +1")

        # ── 3. Age modifier ───────────────────────────────────────────────────
        age_score = 0
        if patient.age <= 1:
            age_score = 4; reasoning.append("Neonate/infant (<1 yr) → +4")
        elif patient.age <= 5:
            age_score = 3; reasoning.append("Child (≤5 yrs) → +3")
        elif patient.age >= 70:
            age_score = 3; reasoning.append("Elderly (≥70 yrs) → +3")
        elif patient.age >= 60:
            age_score = 1; reasoning.append("Senior (≥60 yrs) → +1")

        # ── 4. Duration modifier ──────────────────────────────────────────────
        duration_score = 0
        if patient.symptom_duration_hours >= 48:
            duration_score = 3; reasoning.append(f"Symptoms ≥48h → +3")
        elif patient.symptom_duration_hours >= 24:
            duration_score = 2; reasoning.append(f"Symptoms ≥24h → +2")
        elif patient.symptom_duration_hours >= 12:
            duration_score = 1; reasoning.append(f"Symptoms ≥12h → +1")

        # ── 5. Pregnancy modifier ─────────────────────────────────────────────
        pregnancy_score = 0
        if patient.is_pregnant:
            pregnancy_score = 3; reasoning.append("Pregnant patient → +3")

        # ── 6. Comorbidity modifier ───────────────────────────────────────────
        comorbidity_score = 0
        for condition in patient.comorbidities:
            comorbidity_score += 2
            reasoning.append(f"Comorbidity '{condition}' → +2")

        # ── Total score ───────────────────────────────────────────────────────
        total_score = (
            base_score + vitals_score + age_score +
            duration_score + pregnancy_score + comorbidity_score
        )

        # ── Priority determination ────────────────────────────────────────────
        priority = "LOW"
        for label, info in PRIORITY_LABELS.items():
            if total_score >= info["min_score"]:
                priority = label
                break

        priority_info = PRIORITY_LABELS[priority]

        # ── Dominant category & specialist ────────────────────────────────────
        dominant_category = (
            max(category_votes, key=category_votes.get)
            if category_votes else "general"
        )
        dominant_specialist = (
            max(specialist_votes, key=specialist_votes.get)
            if specialist_votes else "General Medicine"
        )

        needs_icu = (
            priority == "CRITICAL" or
            (patient.vitals and patient.vitals.spo2 is not None and patient.vitals.spo2 < 88)
        )
        needs_referral = priority in ("CRITICAL", "HIGH")

        return TriageResult(
            score=total_score,
            priority=priority,
            category=dominant_category,
            specialist_needed=dominant_specialist,
            action=priority_info["action"],
            color=priority_info["color"],
            needs_icu=needs_icu,
            needs_referral=needs_referral,
            reasoning=reasoning,
            symptom_breakdown=symptom_breakdown,
            vitals_flags=vitals_flags,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Module-level instance
# ─────────────────────────────────────────────────────────────────────────────
triage_engine = TriageEngine()
