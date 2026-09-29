"""
Patient model — stores data submitted by ASHA workers.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, index=True)
    # Personal info
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)  # M / F / Other
    contact = Column(String, nullable=True)
    village = Column(String, nullable=False)
    district = Column(String, nullable=False)
    state = Column(String, default="Telangana")
    # Vitals (captured by ASHA worker)
    temperature = Column(Float, nullable=True)        # °C
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    pulse_rate = Column(Integer, nullable=True)
    spo2 = Column(Float, nullable=True)               # Oxygen saturation %
    weight = Column(Float, nullable=True)             # kg
    # Symptoms — stored as JSON string
    symptoms = Column(Text, nullable=False)
    symptom_duration_hours = Column(Integer, default=0)
    # Additional notes by ASHA worker
    notes = Column(Text, nullable=True)
    # Metadata
    asha_worker_id = Column(String, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    referrals = relationship("Referral", back_populates="patient")


class PatientJourneyLog(Base):
    """Tracks every status change in a patient's journey."""
    __tablename__ = "patient_journey_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String, nullable=False)
    referral_id = Column(String, nullable=True)
    status = Column(String, nullable=False)           # registered, triaged, referred, admitted, discharged
    location = Column(String, nullable=True)          # village / PHC name / hospital name
    notes = Column(Text, nullable=True)
    logged_by = Column(String, nullable=True)
    logged_at = Column(DateTime, default=datetime.utcnow)
