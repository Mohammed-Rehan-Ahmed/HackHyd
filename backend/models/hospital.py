"""
Hospital and Specialist models.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)          # phc / secondary / tertiary
    district = Column(String, nullable=False)
    state = Column(String, default="Telangana")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Bed availability
    total_beds = Column(Integer, default=0)
    available_beds = Column(Integer, default=0)
    icu_beds = Column(Integer, default=0)
    available_icu_beds = Column(Integer, default=0)

    # Contact
    contact_number = Column(String, nullable=True)
    emergency_number = Column(String, nullable=True)

    # Capabilities
    specialties = Column(Text, nullable=True)     # JSON list
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    referrals = relationship("Referral", back_populates="hospital")
    specialists = relationship("Specialist", back_populates="hospital")


class Specialist(Base):
    __tablename__ = "specialists"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    hospital_id = Column(String, ForeignKey("hospitals.id"), nullable=False)
    is_available = Column(Boolean, default=True)
    contact = Column(String, nullable=True)

    hospital = relationship("Hospital", back_populates="specialists")
