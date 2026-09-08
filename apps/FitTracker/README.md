# Vibe Coding with Oracle 26ai: FitTrack

> A complete fitness gamification platform built live during our webinar — demonstrating AI-assisted development with Oracle's JSON Duality Views.

**Webinar Recording**: [LinkedIn Event](https://www.linkedin.com/events/7411444379934031872/)

---

## What's Inside

This repository contains **FitTrack**, a gamified fitness platform built entirely during today's live vibe coding session. Users connect fitness trackers, earn points from physical activities, then spend points on sweepstakes tickets for prize drawings.

| Metric          | Value             |
| --------------- | ----------------- |
| Lines of Python | ~3,150            |
| Repositories    | 12 complete       |
| API Routes      | Fully implemented |
| Build Time      | One live session  |

---

## What We Built

### Tech Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn
- **Database**: Oracle 26ai Free with JSON Duality Views
- **Cache/Queue**: Redis 7
- **Fitness Data**: Terra API (Apple Health, Google Fit, Fitbit)
- **Auth**: JWT (HS256 dev, RS256 prod)

### Architecture

```
src/fittrack/
├── api/
│   ├── routes/          # FastAPI endpoint modules
│   └── schemas/         # Pydantic request/response models
├── services/            # Business logic layer
├── repositories/        # Data access (Oracle + JSON Duality Views)
├── models/              # Domain models and enums
├── workers/             # Background job processors (Redis Queue)
└── core/                # Config, database, exceptions
```

### Database Migrations

The live session naturally evolved toward clean separation:

| File                     | Purpose                                      |
| ------------------------ | -------------------------------------------- |
| `001_initial_schema.sql` | Relational tables with integrity constraints |
| `002_duality_views.sql`  | JSON Duality Views for document-style API    |

This mirrors production deployment patterns: schema first, then the document API layer.

---

## JSON Duality Views in Action

The core innovation demonstrated is Oracle's JSON Duality Views — storing data relationally while accessing it as documents:

```python
# Traditional relational INSERT
cursor.execute("""
    INSERT INTO users (id, email, password_hash, role, status)
    VALUES (:id, :email, :hash, :role, :status)
""", params)

# With JSON Duality View - same table, document API
cursor.execute("""
    INSERT INTO users_dv (data) VALUES (:1)
""", [json.dumps({
    "_id": user_id,
    "email": email,
    "passwordHash": password_hash,
    "role": "user",
    "status": "pending"
})])
```

**Why this matters**:

- Document flexibility for developers
- Relational integrity for the database
- No sync lag between document and relational views
- Single source of truth

---

## Running the Project

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Oracle 26ai Free (runs in Docker)

### Quick Start

```bash
# First-time setup
make setup

# Start all services (Oracle, Redis, API, Workers)
make dev

# Run tests
make test

# Seed sample data
make db-seed
```

### Key Endpoints

| Endpoint                  | Purpose                   |
| ------------------------- | ------------------------- |
| `GET /api/v1/health`      | Liveness/readiness checks |
| `POST /api/v1/users`      | User registration         |
| `GET /api/v1/users/{id}`  | User profile              |
| `POST /api/v1/activities` | Log fitness activity      |
| `GET /api/v1/drawings`    | List sweepstakes          |
| `POST /api/v1/tickets`    | Purchase entry            |

---

## The FitTrack Concept

**What it does**: Users connect fitness trackers, earn points from physical activity, spend points on sweepstakes tickets, compete on tiered leaderboards.

**Competition Tiers**: 31 brackets based on demographics (age, sex, fitness level) ensure fair competition:

- `M-18-29-BEG` (Male, 18-29, Beginner)
- `F-40-49-ADV` (Female, 40-49, Advanced)
- `OPEN` (All users)

**Point System**:

- 10 pts per 1,000 steps (max 20K/day)
- 1-3 pts per active minute (by intensity)
- 50 pts per workout (max 3/day)
- Daily cap: 1,000 points (anti-gaming)

**Sweepstakes**: Daily, weekly, monthly, annual drawings with CSPRNG selection and full audit trails.

---

## What We Learned

### 1. AI-Assisted Development Works

Building a complete backend with 12 repositories, full API surface, and database migrations in a single live session demonstrates the power of vibe coding with good context files.

### 2. JSON Duality Views Change the Game

No more choosing between document flexibility and relational integrity. No more syncing document stores with relational databases. The database handles both views natively.

### 3. Context Files Are Essential

The `CLAUDE.md` file made AI-assisted development dramatically more effective. Good context = good output.

### 4. Separation Emerges Naturally

The decision to split migrations (tables → duality views) wasn't planned — it emerged during the session. That's a sign of good architecture: the right structure becomes obvious as you build.

---

## Resources

- **Oracle JSON Duality Views**: [Documentation](https://docs.oracle.com/en/database/oracle/oracle-database/23/jsnvu/)
- **FastAPI**: [Documentation](https://fastapi.tiangolo.com/)
- **python-oracledb**: [Documentation](https://python-oracledb.readthedocs.io/)
- **Terra API**: [Documentation](https://docs.tryterra.co/)

---

## Questions?

Reach out on [LinkedIn](https://www.linkedin.com/in/rickhoulihan/) or open an issue in this repo.

---

_Built live with Oracle 26ai, FastAPI, and vibe coding._
