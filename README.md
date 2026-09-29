<div align="center">

# 🏥 Rural Healthcare Referral & Journey Management System

### Intelligent automation workflow bridging rural patients with urban specialty hospitals

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--time-orange)](https://websockets.readthedocs.io)
[![Groq](https://img.shields.io/badge/Groq-LLaMA3-purple)](https://groq.com)
[![Hindsight](https://img.shields.io/badge/Hindsight-Vectorize-red)](https://hindsight.vectorize.io)
[![SQLite](https://img.shields.io/badge/SQLite-Database-lightblue?logo=sqlite)](https://sqlite.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://docker.com)

</div>

---

## 📌 Table of Contents

- [Problem Statement](#-problem-statement)
- [Solution Overview](#-solution-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [Triage Algorithm](#-triage-algorithm)
- [Hindsight Memory Layer](#-hindsight-ai-memory-layer)
- [WebSocket Events](#-websocket-events)
- [Frontend Interfaces](#-frontend-interfaces)
- [Database Schema](#-database-schema)
- [Docker Deployment](#-docker-deployment)
- [Workflow Walkthrough](#-workflow-walkthrough)
- [Roadmap](#-roadmap)

---

## 🚨 Problem Statement

Rural India faces a critical gap in healthcare delivery:

- **ASHA workers** in remote villages have no way to know which hospital has beds or specialists available
- **PHCs operate in silos** — no shared visibility, no coordination across facilities
- **Referrals happen on paper chits or unanswered phone calls** — patients arrive at full hospitals after hours of travel
- **No patient history is carried forward** — every visit starts from zero, even for chronic patients
- **Hospitals receive zero advance notice** — they cannot prepare ICU beds, call specialists, or allocate resources before the patient arrives

> People die not because care doesn't exist, but because the right care couldn't be reached in time.

---

## ✅ Solution Overview

This system is an **intelligent, real-time referral and patient journey management platform** that connects village-level ASHA workers directly to urban specialty hospitals through:

1. A **mobile-friendly ASHA worker app** for capturing patient data and symptoms with zero infrastructure dependency
2. A **Python triage engine** that scores symptom severity and assigns CRITICAL / HIGH / MEDIUM / LOW priority instantly
3. A **live hospital matching system** that queries bed and specialist availability in real time
4. **WebSocket-powered alerts** that push urgent notifications to hospital dashboards before the patient even leaves the village
5. A **Hindsight AI persistent memory layer** (via Vectorize + Groq LLaMA-3) that remembers every past referral and flags returning patients automatically

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔴 **Intelligent Triage** | 30+ symptom database with weighted scoring, vitals analysis, age and duration modifiers |
| 🏥 **Live Bed Matching** | Real-time query of available beds (general + ICU) and specialist availability |
| 🎫 **Digital Referral Tickets** | Auto-generated unique ticket IDs (e.g. `REF-20240915-A1B2`) for every referral |
| ⚡ **WebSocket Alerts** | Hospital dashboard receives push notification the moment a referral is created |
| 🧠 **AI Memory (Hindsight)** | Persistent vector memory detects returning patients across sessions using name, village, age, gender, contact |
| 📋 **Patient Journey Tracking** | Full lifecycle from village registration → referral → transit → admission → diagnosis → discharge |
| 📱 **Mobile-First ASHA App** | Works on any Android browser, no app install required, low-bandwidth friendly |
| 🗺️ **Connected PHC Network** | Multiple PHCs share one unified referral network with shared visibility |
| 🐳 **Docker Ready** | One command deployment with docker-compose |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VILLAGE (Rural)                              │
│                                                                     │
│   ASHA Worker                                                       │
│   Mobile App  ──── POST /api/triage/refer ──────────────────────┐  │
│   (HTML/JS)                                                      │  │
└──────────────────────────────────────────────────────────────────│──┘
                                                                   │
                                                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND SERVER                          │
│                                                                     │
│  ┌─────────────┐   ┌──────────────────┐   ┌─────────────────────┐  │
│  │   Triage    │   │  Referral        │   │  WebSocket          │  │
│  │   Engine    │──▶│  Service         │──▶│  Manager            │  │
│  │  (Python)   │   │  (Bed + Spec     │   │  (Room-based push)  │  │
│  └─────────────┘   │   query + ticket)│   └──────────┬──────────┘  │
│                    └──────────────────┘              │             │
│  ┌─────────────────────────────────────┐             │             │
│  │   Hindsight Memory Service          │             │             │
│  │   ┌──────────┐   ┌──────────────┐  │             │             │
│  │   │ recall() │   │  retain()    │  │             │             │
│  │   │ reflect()│   │  (post-ref)  │  │             │             │
│  │   └──────────┘   └──────────────┘  │             │             │
│  │   hindsight-litellm + Groq LLaMA3  │             │             │
│  └─────────────────────────────────────┘             │             │
│                                                      │             │
│  ┌─────────────────────────────────────┐             │             │
│  │   SQLite / PostgreSQL Database      │             │             │
│  │   patients | referrals | hospitals  │             │             │
│  │   specialists | asha_workers        │             │             │
│  └─────────────────────────────────────┘             │             │
└──────────────────────────────────────────────────────│─────────────┘
                                                       │
                    ┌──────────────────────────────────┘
                    │               │
                    ▼               ▼
          ┌─────────────┐   ┌──────────────┐
          │  Hospital   │   │  ASHA Worker │
          │  Dashboard  │   │  App gets    │
          │  🔴 ALERT   │   │  ✅ Ticket   │
          │  (WebSocket)│   │  Confirmed   │
          └─────────────┘   └──────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3.11, FastAPI | REST API + WebSocket server |
| **ORM** | SQLAlchemy 2.0 | Database models and queries |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Persistent storage |
| **Real-time** | WebSockets (native FastAPI) | Live hospital alerts |
| **AI Memory** | Hindsight (Vectorize) | Persistent patient memory across sessions |
| **LLM** | Groq LLaMA-3.1-70B via hindsight-litellm | Clinical note generation, memory reflection |
| **LLM Wrapper** | hindsight-litellm | Groq + memory injection in one call |
| **Frontend** | Vanilla HTML / CSS / JS | Zero-framework, works on low-end phones |
| **Deployment** | Docker + docker-compose | Container-ready single command deploy |
| **Validation** | Pydantic v2 | Request/response schema validation |
| **Auth** | python-jose + passlib | JWT token support (extendable) |

---

## 📁 Project Structure

```
healthcare-referral-system/
│
├── backend/
│   ├── app.py                        # FastAPI app, WebSocket endpoints, startup
│   ├── config.py                     # All settings from environment variables
│   │
│   ├── api/
│   │   ├── triage.py                 # POST /triage/refer — full workflow endpoint
│   │   ├── referrals.py              # CRUD + status update for referrals
│   │   ├── hospitals.py              # Hospital listing + bed availability
│   │   ├── patients.py               # Patient registration + journey log
│   │   ├── asha_workers.py           # ASHA worker management
│   │   └── memory.py                 # Hindsight recall/retain endpoints
│   │
│   ├── models/
│   │   ├── patient.py                # Patient + PatientJourneyLog tables
│   │   ├── referral.py               # Referral ticket table
│   │   ├── hospital.py               # Hospital + Specialist tables
│   │   └── asha_worker.py            # ASHA worker table
│   │
│   ├── services/
│   │   ├── triage_engine.py          # Core scoring algorithm (30+ symptoms)
│   │   ├── referral_service.py       # Ticket creation + hospital matching
│   │   ├── memory_service.py         # Hindsight retain/recall/reflect
│   │   ├── notification_service.py   # WebSocket push + SMS fallback stub
│   │   └── websocket_manager.py      # Room-based connection manager
│   │
│   └── database/
│       ├── db.py                     # SQLAlchemy engine + session factory
│       └── seed_data.py              # Pre-loaded hospitals, PHCs, ASHA workers
│
├── frontend/
│   ├── hospital_dashboard.html       # Real-time hospital alert dashboard
│   └── asha_mobile_app.html          # ASHA worker mobile-first app
│
├── docker/
│   ├── Dockerfile                    # Python 3.11 slim image
│   └── docker-compose.yml            # Full stack deployment config
│
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variable template
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- pip
- A Groq API key — free at [console.groq.com](https://console.groq.com)
- Hindsight API running locally (see step 3 below)

### 1. Clone and install

```bash
git clone https://github.com/your-username/healthcare-referral-system.git
cd healthcare-referral-system

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
DATABASE_URL=sqlite:///./healthcare.db
SECRET_KEY=your-random-secret-string
GROQ_API_KEY=gsk_your_key_here
HINDSIGHT_API_URL=http://localhost:8888
```

### 3. Start Hindsight memory server

```bash
pip install hindsight-api

export GROQ_API_KEY=gsk_your_key_here
export HINDSIGHT_API_LLM_API_KEY=$GROQ_API_KEY

hindsight-api        # Starts on http://localhost:8888
```

### 4. Run the backend

```bash
cd backend
uvicorn app:app --reload --port 8000
```

On first run, the database is created automatically and seeded with:
- 2 Tertiary/Secondary hospitals (NIMS, Gandhi Hospital)
- 2 PHCs (Vikarabad, Tandur)
- 4 Specialists
- 2 ASHA Workers

### 5. Open the frontends

Open these two files directly in your browser — no build step required:

```
frontend/hospital_dashboard.html    →  Hospital staff screen
frontend/asha_mobile_app.html       →  ASHA worker phone app
```

### 6. Explore the API docs

```
http://localhost:8000/docs      →  Swagger UI (interactive)
http://localhost:8000/redoc     →  ReDoc documentation
```

---

## 🔐 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite:///./healthcare.db` | Database connection string |
| `SECRET_KEY` | Yes | — | JWT signing key |
| `DEBUG` | No | `true` | Enable debug logging |
| `GROQ_API_KEY` | Yes | — | Groq API key for LLaMA-3 |
| `GROQ_MODEL` | No | `llama-3.1-70b-versatile` | Groq model name |
| `HINDSIGHT_API_URL` | Yes | `http://localhost:8888` | Hindsight memory server URL |
| `HINDSIGHT_API_KEY` | No | — | Hindsight API key (if auth enabled) |
| `TOKEN_EXPIRE` | No | `60` | JWT expiry in minutes |

---

## 📡 API Reference

### Triage

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/triage/evaluate` | Run triage scoring only — no DB write, no memory |
| `POST` | `/api/triage/refer` | **Full workflow** — register + triage + match + ticket + notify |

#### POST `/api/triage/refer` — Request body

```json
{
  "patient_name": "Ramaiah",
  "age": 62,
  "gender": "Male",
  "village": "Kodangal",
  "district": "Vikarabad",
  "contact": "+91-9988776600",
  "symptoms": ["chest_pain", "breathlessness"],
  "symptom_duration_hours": 4,
  "vitals": {
    "temperature": 37.2,
    "spo2": 88,
    "pulse_rate": 112,
    "bp_systolic": 160,
    "bp_diastolic": 95
  },
  "is_pregnant": false,
  "comorbidities": ["hypertension"],
  "asha_worker_id": "ASHA001",
  "origin_phc_id": "PHC001",
  "transport_mode": "ambulance"
}
```

#### Response

```json
{
  "status": "REFERRAL_CREATED",
  "ticket_id": "REF-20240915-A1B2C3D4",
  "patient_id": "PAT-X9Y8Z7",
  "returning_patient": false,
  "past_history": {
    "found": false,
    "summary": "",
    "memory_count": 0
  },
  "clinical_note": "Patient with hypertension presenting with cardiac symptoms...",
  "triage": {
    "score": 22,
    "priority": "CRITICAL",
    "category": "cardiac",
    "action": "Immediate referral. Notify hospital NOW.",
    "color": "#FF0000",
    "needs_icu": true
  },
  "hospital": {
    "id": "HOSP001",
    "name": "Nizam's Institute of Medical Sciences",
    "district": "Hyderabad",
    "emergency_number": "+91-40-23489999",
    "available_beds": 119
  },
  "specialist": {
    "name": "Dr. Priya Sharma",
    "specialty": "Cardiology",
    "contact": "+91-9876543210"
  }
}
```

### Referrals

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/referrals/` | List all referrals with patient name, village, specialist |
| `GET` | `/api/referrals/{id}` | Get single referral details |
| `PATCH` | `/api/referrals/{id}/status` | Update status (ACCEPTED, ADMITTED, DISCHARGED etc.) |
| `GET` | `/api/referrals/stats/summary` | Count by priority and status |

### Hospitals

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/hospitals/` | List all hospitals with bed counts |
| `GET` | `/api/hospitals/{id}` | Hospital detail with specialists |
| `PATCH` | `/api/hospitals/{id}/beds` | Update available bed count |
| `GET` | `/api/hospitals/{id}/availability` | Live bed + specialist availability check |

### Patients

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/patients/` | List all registered patients |
| `GET` | `/api/patients/{id}` | Patient detail with vitals |
| `GET` | `/api/patients/{id}/journey` | Full journey log (every status change) |

### Memory (Hindsight)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/memory/patient` | Recall patient history by name + village |
| `GET` | `/api/memory/village` | Village-level health pattern summary |
| `GET` | `/api/memory/phc` | PHC doctor availability history |
| `POST` | `/api/memory/retain-outcome` | Store discharge outcome in memory |

### WebSocket

| Path | Room | Description |
|---|---|---|
| `ws://host/ws/hospital/{hospital_id}` | `hospital_{id}` | Hospital dashboard live alerts |
| `ws://host/ws/asha/{worker_id}` | `asha_{id}` | ASHA worker confirmation feed |

---

## 🧠 Triage Algorithm

The triage engine in `backend/services/triage_engine.py` calculates a total urgency score from five components:

```
Total Score = Symptom Score + Vitals Modifier + Age Modifier
            + Duration Modifier + Pregnancy Modifier + Comorbidity Modifier
```

### Symptom Score (base)

Each symptom carries a weight from 1–12:

| Symptom | Score | Category |
|---|---|---|
| Unconscious / Not breathing | 12 | Neurological / Pediatric |
| Stroke symptoms | 12 | Neurological |
| Snake bite | 12 | Toxicology |
| Chest pain | 10 | Cardiac |
| Seizures | 10 | Neurological |
| Severe bleeding | 10 | Trauma |
| Pregnancy complications | 10 | Obstetric |
| Breathlessness | 9 | Respiratory |
| Vomiting blood | 9 | Gastro |
| Head injury | 9 | Trauma |
| Burns | 7 | Trauma |
| High fever / Dengue / Malaria | 7 | Infectious |
| Fracture | 6 | Orthopedic |
| Fatigue / Headache | 1–2 | General |

### Vitals Modifier

| Condition | Bonus |
|---|---|
| SpO₂ < 85% | +6 |
| Hypotension (SBP < 90) | +5 |
| SpO₂ < 90% | +4 |
| Hypertensive crisis (SBP > 180) | +4 |
| Hyperpyrexia (Temp ≥ 40°C) | +4 |
| Abnormal pulse (>130 or <40) | +4 |

### Priority Thresholds

| Score | Priority | Action |
|---|---|---|
| ≥ 15 | 🔴 CRITICAL | Immediate referral. ICU bed reserved. Hospital notified NOW. |
| ≥ 8 | 🟠 HIGH | Refer within 2 hours. Specialist alerted. |
| ≥ 4 | 🟡 MEDIUM | PHC treatment first. Monitor every 30 minutes. |
| < 4 | 🟢 LOW | Outpatient care. Review in 24 hours. |

---

## 🧠 Hindsight AI Memory Layer

Built using **[Hindsight by Vectorize](https://hindsight.vectorize.io)** via the `hindsight-litellm` wrapper with **Groq LLaMA-3.1-70B** as the LLM backend.

### Memory Banks

| Bank ID | Keyed By | Stores |
|---|---|---|
| `village-{slug}` | `patient.village` | All patients and referrals from that village |
| `asha-{worker_id}` | `asha_worker_id` | Full referral history per ASHA worker |
| `phc-{phc_id}` | `origin_phc_id` | PHC doctor availability patterns |

### How It Works

**On every referral submission:**

```
Step 0 — RECALL
  → Query: "Patient Ramaiah, from Kodangal, aged 62, Male, +91-99..."
  → Hindsight TEMPR search (semantic + keyword + entity graph + temporal)
  → If found → returning_patient: true
               reflect() → Groq synthesises clinical summary

Step 1–6 — Normal triage + hospital matching + ticket

Step 7 — RETAIN
  → Stores: "[2024-09-15] Referral REF-001: Ramaiah, 62M, Kodangal,
              chest_pain, CRITICAL, sent to NIMS, Dr. Priya Sharma..."
  → Written to village-kodangal, asha-asha001, phc-phc001 banks
```

### Returning Patient Detection

Matching uses **5 parameters** from the submission form:

```python
recall_patient_history(
    patient_name = "Ramaiah",     # primary key
    village      = "Kodangal",    # primary key
    age          = 62,            # confirmation signal
    gender       = "Male",        # confirmation signal
    contact      = "+91-99...",   # confirmation signal
)
```

**On the ASHA app:**
- As soon as the ASHA worker types the patient name and moves to the next field, `checkPatientHistory()` fires silently in the background
- If a match is found, a **modal popup** appears before the form can be submitted:

```
        ┌─────────────────────────────┐
        │           ⚠️               │
        │    This is an old patient   │
        │                             │
        │  Ramaiah was previously     │
        │  referred on REF-20240901   │
        │  for chest pain (CRITICAL). │
        │  Seen by Dr. Priya Sharma   │
        │  at NIMS Hyderabad.         │
        │                             │
        │  [Cancel]  [Continue Anyway]│
        └─────────────────────────────┘
```

- If the worker clicks **Continue Anyway**, the referral proceeds and the previous history is attached to the hospital alert
- The **hospital dashboard** also receives a `⚠️ RETURNING PATIENT` badge on the incoming alert card along with an AI-generated clinical note from Groq

---

## ⚡ WebSocket Events

### Hospital receives (`/ws/hospital/{id}`)

```json
{
  "type": "NEW_REFERRAL",
  "referral_id": "REF-20240915-A1B2",
  "priority": "CRITICAL",
  "priority_color": "#FF0000",
  "action_required": "Immediate referral. Notify hospital NOW.",
  "returning_patient": true,
  "past_history_summary": "Patient previously seen for cardiac issue...",
  "clinical_note": "Known cardiac patient with hypertension...",
  "patient": { "name": "Ramaiah", "age": 62, "gender": "Male", "village": "Kodangal" },
  "triage": {
    "score": 22,
    "category": "cardiac",
    "specialist_needed": "Cardiology",
    "needs_icu": true,
    "vitals_flags": ["Critical SpO₂ (88%) +6", "Tachycardia (112 bpm) +1"]
  },
  "assigned_specialist": { "name": "Dr. Priya Sharma", "contact": "+91-9876543210" },
  "timestamp": "2024-09-15T10:30:00Z"
}
```

### ASHA worker receives (`/ws/asha/{id}`)

```json
{
  "type": "REFERRAL_CONFIRMED",
  "ticket_id": "REF-20240915-A1B2",
  "hospital_name": "Nizam's Institute of Medical Sciences",
  "hospital_address": "Hyderabad, Telangana",
  "hospital_emergency": "+91-40-23489999",
  "priority": "CRITICAL",
  "transport_mode": "ambulance",
  "message": "Referral confirmed. Proceed to NIMS immediately.",
  "timestamp": "2024-09-15T10:30:01Z"
}
```

---

## 🖥️ Frontend Interfaces

### ASHA Worker Mobile App (`frontend/asha_mobile_app.html`)

Designed to work on any Android browser on a basic smartphone, no app install required.

**Tabs:**
- **Register** — Patient form with symptom chips, vitals input, one-tap referral submission
- **Journey** — View all past referrals and their current statuses
- **Settings** — ASHA worker ID, API URL, PHC ID configuration

**Key behaviours:**
- Symptom selection via tap chips (no typing required)
- Returning patient popup fires automatically before submission
- Yellow warning banner shows past history inline on the form
- Result card shows ticket ID, hospital name, emergency contact, and AI clinical note
- Emergency call button pre-filled with hospital's emergency number

### Hospital Dashboard (`frontend/hospital_dashboard.html`)

Full-screen dark dashboard for emergency desk or nursing station.

**Features:**
- Live stats row — CRITICAL / HIGH / MEDIUM / TOTAL counts update in real time
- Incoming referrals table — patient name, village, condition, priority badge, specialist, status, accept button
- Live alerts panel — push notification cards arrive instantly via WebSocket, colour-coded by priority
- Visual red flash on screen for CRITICAL alerts
- One-click Accept updates referral status and notifies ASHA worker

---

## 🗄️ Database Schema

### `patients`
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | e.g. PAT-X9Y8Z7 |
| name, age, gender | TEXT/INT | Basic demographics |
| village, district, state | TEXT | Location |
| temperature, spo2, pulse_rate, blood_pressure_* | FLOAT/INT | Vitals |
| symptoms | TEXT | JSON array |
| asha_worker_id | TEXT | Who submitted |
| registered_at | DATETIME | Timestamp |

### `referrals`
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | e.g. REF-20240915-A1B2 |
| patient_id | FK → patients | |
| destination_hospital_id | FK → hospitals | |
| assigned_specialist_id | FK → specialists | |
| triage_score, triage_priority, triage_category | INT/TEXT | Triage result |
| status | TEXT | PENDING → ACCEPTED → IN_TRANSIT → ADMITTED → DISCHARGED |
| hospital_notified | BOOLEAN | Was WebSocket push successful |
| diagnosis, medication_prescribed | TEXT | Filled by hospital after admission |

### `hospitals`
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | e.g. HOSP001 |
| type | TEXT | phc / secondary / tertiary |
| total_beds, available_beds | INT | Updated on referral creation |
| icu_beds, available_icu_beds | INT | Reserved for CRITICAL cases |
| specialties | TEXT | JSON array of specialty names |

### `patient_journey_logs`
| Column | Type | Notes |
|---|---|---|
| id | INT PK | Auto-increment |
| patient_id, referral_id | TEXT | References |
| status | TEXT | REGISTERED / REFERRED / ADMITTED / DISCHARGED |
| location | TEXT | Village / PHC / Hospital name |
| logged_at | DATETIME | Timestamp of status change |

---

## 🐳 Docker Deployment

```bash
cd docker
docker compose up --build
```

The backend starts at `http://localhost:8000`.

To switch to PostgreSQL in production, uncomment the `db` service in `docker-compose.yml` and update:

```env
DATABASE_URL=postgresql://healthuser:healthpass@db:5432/healthdb
```

---

## 📋 Workflow Walkthrough

### First-time patient

```
1. ASHA worker opens mobile app in village
2. Fills: Ramaiah, 62, Male, Kodangal, chest_pain + breathlessness
3. Enters vitals: SpO₂=88, BP=160/95, Pulse=112
4. Taps "Evaluate & Refer"
5. System checks Hindsight memory → no past record found
6. Triage engine scores: chest_pain(10) + breathlessness(9) + SpO₂(6)
   + BP(4) + pulse(1) + age(1) + comorbidity(2) = 33 → CRITICAL
7. System queries hospitals → NIMS has ICU beds + Cardiology specialist
8. Referral ticket REF-20240915-A1B2 created
9. Groq generates clinical note using memory context
10. WebSocket fires to HOSP001 dashboard → red alert appears instantly
11. ASHA app shows ticket ID + emergency number + "Proceed to NIMS immediately"
12. Referral retained in Hindsight village-kodangal memory bank
```

### Returning patient (same Ramaiah, months later)

```
1. ASHA worker enters "Ramaiah" in name field
2. checkPatientHistory() fires silently to /api/memory/patient
3. Hindsight TEMPR matches on name + village + age
4. reflect() → Groq synthesises: "Ramaiah, 62M, previously referred
   for cardiac emergency, Dr. Priya Sharma at NIMS, discharged stable"
5. POPUP fires immediately:
   "⚠️ This is an old patient — Previous cardiac history found"
6. ASHA worker reviews and clicks "Continue Anyway"
7. Referral submitted with past_history attached
8. Hospital alert includes ⚠️ RETURNING PATIENT badge + clinical note
9. Hospital already knows: cardiac patient, previously under Dr. Sharma
```

---

## 🗺️ Roadmap

- [ ] **Ambulance GPS integration** — real-time ETA and route tracking on hospital dashboard
- [ ] **Multilingual voice input** — Telugu/Hindi voice support for low-literacy ASHA workers
- [ ] **Predictive bed shortage alerts** — ML model to anticipate surge demand by village patterns
- [ ] **ABHA integration** — link to national Ayushman Bharat Health Account records
- [ ] **Offline mode** — PWA with service workers for zero-connectivity villages, sync when back online
- [ ] **SMS fallback** — Twilio / MSG91 integration when WebSocket connections are unavailable
- [ ] **Insurance claim initiation** — auto-generate referral documents for PM-JAY claim submission
- [ ] **Analytics dashboard** — district-level health heatmaps, ASHA worker performance metrics

---

## 👥 Team

Built as part of an intelligent healthcare workflow automation initiative targeting rural Telangana, India.

**Problem Domain:** Public healthcare gaps in rural settings — PHC-to-hospital referral chain  
**Target Users:** ASHA workers, PHC doctors, district hospital emergency staff  
**Target Geography:** Rural Telangana, India (extendable to any state)

---

## 📄 License

This project is open source under the [MIT License](LICENSE).

---

<div align="center">

**Built with ❤️ for rural India**

*Connecting villages to hospitals. One referral at a time.*

</div>
