"""
Seed initial hospitals, PHCs, and ASHA workers into the database.
"""

from sqlalchemy.orm import Session
from models.hospital import Hospital, Specialist
from models.asha_worker import ASHAWorker
import json


def seed_database(db: Session):
    """Populate the DB with sample data if tables are empty."""

    # ── Hospitals ──────────────────────────────────────────────────────────────
    if db.query(Hospital).count() == 0:
        hospitals = [
            Hospital(
                id="HOSP001",
                name="Nizam's Institute of Medical Sciences",
                type="tertiary",
                district="Hyderabad",
                state="Telangana",
                latitude=17.4126,
                longitude=78.4071,
                total_beds=800,
                available_beds=120,
                icu_beds=50,
                available_icu_beds=8,
                contact_number="+91-40-23489000",
                emergency_number="+91-40-23489999",
                specialties=json.dumps([
                    "Cardiology", "Neurology", "Oncology",
                    "Nephrology", "Orthopedics", "Obstetrics"
                ]),
                is_active=True,
            ),
            Hospital(
                id="HOSP002",
                name="Gandhi Hospital",
                type="secondary",
                district="Secunderabad",
                state="Telangana",
                latitude=17.4399,
                longitude=78.4983,
                total_beds=400,
                available_beds=65,
                icu_beds=20,
                available_icu_beds=3,
                contact_number="+91-40-27505566",
                emergency_number="+91-40-27505999",
                specialties=json.dumps([
                    "General Medicine", "Surgery", "Pediatrics",
                    "Gynecology", "Orthopedics"
                ]),
                is_active=True,
            ),
            Hospital(
                id="PHC001",
                name="PHC Vikarabad",
                type="phc",
                district="Vikarabad",
                state="Telangana",
                latitude=17.3387,
                longitude=77.9047,
                total_beds=30,
                available_beds=12,
                icu_beds=0,
                available_icu_beds=0,
                contact_number="+91-8416-222100",
                emergency_number="+91-8416-222100",
                specialties=json.dumps(["General Medicine", "Maternal Health"]),
                is_active=True,
            ),
            Hospital(
                id="PHC002",
                name="PHC Tandur",
                type="phc",
                district="Vikarabad",
                state="Telangana",
                latitude=17.2484,
                longitude=77.5761,
                total_beds=20,
                available_beds=8,
                icu_beds=0,
                available_icu_beds=0,
                contact_number="+91-8416-233200",
                emergency_number="+91-8416-233200",
                specialties=json.dumps(["General Medicine"]),
                is_active=True,
            ),
        ]
        db.add_all(hospitals)

    # ── Specialists ────────────────────────────────────────────────────────────
    if db.query(Specialist).count() == 0:
        specialists = [
            Specialist(
                id="SPEC001",
                name="Dr. Priya Sharma",
                specialty="Cardiology",
                hospital_id="HOSP001",
                is_available=True,
                contact="+91-9876543210",
            ),
            Specialist(
                id="SPEC002",
                name="Dr. Ramesh Babu",
                specialty="Neurology",
                hospital_id="HOSP001",
                is_available=True,
                contact="+91-9876543211",
            ),
            Specialist(
                id="SPEC003",
                name="Dr. Anitha Reddy",
                specialty="Obstetrics",
                hospital_id="HOSP001",
                is_available=False,
                contact="+91-9876543212",
            ),
            Specialist(
                id="SPEC004",
                name="Dr. Mohammed Khaleel",
                specialty="Pediatrics",
                hospital_id="HOSP002",
                is_available=True,
                contact="+91-9876543213",
            ),
        ]
        db.add_all(specialists)

    # ── ASHA Workers ───────────────────────────────────────────────────────────
    if db.query(ASHAWorker).count() == 0:
        workers = [
            ASHAWorker(
                id="ASHA001",
                name="Lakshmi Devi",
                village="Kodangal",
                district="Vikarabad",
                state="Telangana",
                phc_id="PHC001",
                contact="+91-9988776655",
                language_preference="Telugu",
                is_active=True,
            ),
            ASHAWorker(
                id="ASHA002",
                name="Savitri Bai",
                village="Marpally",
                district="Vikarabad",
                state="Telangana",
                phc_id="PHC002",
                contact="+91-9988776644",
                language_preference="Telugu",
                is_active=True,
            ),
        ]
        db.add_all(workers)

    db.commit()
    print("✅ Seed data loaded.")
