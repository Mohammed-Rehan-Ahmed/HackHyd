"""
ASHA (Accredited Social Health Activist) worker model.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer
from datetime import datetime
from database.db import Base


class ASHAWorker(Base):
    __tablename__ = "asha_workers"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    village = Column(String, nullable=False)
    district = Column(String, nullable=False)
    state = Column(String, default="Telangana")
    phc_id = Column(String, nullable=True)          # Assigned PHC
    contact = Column(String, nullable=True)
    language_preference = Column(String, default="Telugu")
    total_referrals = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
