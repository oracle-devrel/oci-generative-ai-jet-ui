# FitTrack

> Gamified fitness platform with sweepstakes rewards and tiered competitions.

## Overview

FitTrack transforms fitness activity into a competitive, rewarding experience. Users connect fitness trackers, earn points from physical activities, then spend points on sweepstakes tickets for prize drawings. Tiered competition brackets ensure fair competition among users with similar demographics and fitness baselines.

**Target Market**: US only, 18+, sweepstakes-compliant states (excludes NY, FL, RI)

## Tech Stack

| Component    | Choice                | Why                                         |
| ------------ | --------------------- | ------------------------------------------- |
| Backend      | Python 3.12 + FastAPI | Async support, type hints, auto OpenAPI     |
| Database     | Oracle 23ai Free      | JSON Duality Views, client requirement      |
| Cache        | Redis                 | Session management, leaderboard caching     |
| Queue        | Redis (RQ)            | Background job processing                   |
| Frontend     | React 18 + Vite       | Responsive SPA                              |
| Fitness Data | Terra API             | Aggregates Apple Health, Google Fit, Fitbit |

## Database Requirements

**CRITICAL**: Oracle 23ai with JSON Duality Views exclusively.

- Use `python-oracledb` driver directly (thin mode for dev, thick for prod)
- Store entities as JSON documents via Duality Views over relational tables
- Relational tables provide integrity; Duality Views provide document API
- Create functional indexes on queried JSON paths
- No SQLAlchemy ORM - use repositories with raw oracledb

```python
# Example: Reading via Duality View
cursor.execute("SELECT data FROM user_profile_dv WHERE JSON_VALUE(data, '$._id') = :id", [user_id])

# Example: Insert via Duality View
cursor.execute("INSERT INTO user_profile_dv (data) VALUES (:1)", [json.dumps(user_doc)])
```

## Project Layout

```
fittrack/
├── src/fittrack/
│   ├── api/              # FastAPI routes, schemas, dependencies
│   │   ├── routes/       # Endpoint modules by domain
│   │   └── schemas/      # Pydantic request/response models
│   ├── services/         # Business logic layer
│   ├── repositories/     # Data access layer (Oracle)
│   ├── models/           # Domain models and enums
│   ├── workers/          # Background job handlers
│   └── core/             # Config, security, exceptions
├── tests/
│   ├── unit/             # Pure unit tests
│   ├── integration/      # DB and API tests
│   └── factories/        # Test data factories
├── migrations/           # Database migrations
├── scripts/              # Seed data, utilities
└── devtools/             # Test HTML page, dev utilities
```

## Domain Concepts

| Term       | Meaning                                                    |
| ---------- | ---------------------------------------------------------- |
| Points     | Currency earned from activities, spent on tickets          |
| Ticket     | Entry into a sweepstakes drawing                           |
| Drawing    | Sweepstakes event (daily/weekly/monthly/annual)            |
| Tier       | Competition bracket: `{SEX}-{AGE_BRACKET}-{FITNESS_LEVEL}` |
| Connection | OAuth link to fitness tracker (Terra API)                  |
| Activity   | Normalized fitness data (steps, workout, active_minutes)   |

## Tier System

31 competition tiers total:

- **30 demographic tiers**: 5 age brackets × 2 sex categories × 3 fitness levels
- **1 open tier**: All users regardless of demographics

Tier codes: `M-18-29-BEG`, `F-40-49-ADV`, `OPEN`

## Key Business Rules

- **Point daily cap**: 1,000 points max per day (anti-gaming)
- **Workout bonus cap**: Max 3 workout bonuses per day
- **Step cap**: Points only for first 20,000 steps/day
- **Points don't expire** and cannot be transferred
- **Tickets are final** - no refunds after purchase
- **Eligibility**: 18+, verified email, eligible US state
- **Drawing execution**: CSPRNG selection, immutable audit trail

## Point Earning Rates

| Activity                      | Rate                 | Cap              |
| ----------------------------- | -------------------- | ---------------- |
| Steps                         | 10 pts / 1,000 steps | 20,000 steps/day |
| Light active minutes          | 1 pt / minute        | -                |
| Moderate active minutes       | 2 pts / minute       | -                |
| Vigorous active minutes       | 3 pts / minute       | -                |
| Workout completed (≥20 min)   | 50 pts bonus         | 3/day            |
| Daily step goal (10K)         | 100 pts bonus        | 1/day            |
| Weekly streak (7 active days) | 250 pts bonus        | 1/week           |

## Drawing Types

| Type    | Frequency         | Ticket Cost | Close Time  |
| ------- | ----------------- | ----------- | ----------- |
| Daily   | Every day         | 100 pts     | 8:55 PM EST |
| Weekly  | Sundays           | 500 pts     | 8:55 PM EST |
| Monthly | Last day of month | 2,000 pts   | 8:55 PM EST |
| Annual  | Dec 31            | 10,000 pts  | 8:55 PM EST |

## API Patterns

- Base path: `/api/v1/`
- Auth: JWT Bearer tokens (RS256), 1hr access / 30d refresh
- Errors: RFC 7807 Problem Details format
- Pagination: `?page=1&limit=20` with `pagination` in response
- Dates: ISO 8601 with timezone

```json
// Error response format
{
  "type": "https://fittrack.com/errors/insufficient-points",
  "title": "Insufficient Points",
  "status": 400,
  "detail": "You need 500 points but only have 350",
  "instance": "/api/v1/drawings/abc123/tickets"
}
```

## Commands

```bash
make setup        # First-time setup (creates .env, installs deps)
make dev          # Start all services (API, DB, Redis, workers)
make test         # Run all tests
make test-cov     # Run tests with coverage report
make db-migrate   # Run pending migrations
make db-seed      # Seed database with synthetic data
make db-reset     # Drop and recreate database with seed data
make lint         # Run linting (ruff)
make format       # Format code (black, isort)
```

## Environment Variables

```bash
# Required
DATABASE_URL=oracle+oracledb://fittrack:password@localhost:1521/FREEPDB1
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=<generate-256-bit-key>
TERRA_API_KEY=<from-terra-dashboard>
TERRA_DEV_ID=<from-terra-dashboard>

# Optional
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

## Gotchas

- **Point balance race condition**: Use optimistic locking (version column) on `users.point_balance` for concurrent ticket purchases
- **Tier codes are computed**: Never store tier_code directly - always derive from profile fields
- **Oracle JSON paths are case-sensitive**: `$.userId` ≠ `$.userid`
- **Terra webhook signatures**: Verify HMAC-SHA256 signature on all webhooks
- **Drawing ticket numbers**: Assigned at sales close, not at purchase time
- **Time zones**: All drawing times are EST/EDT - convert carefully

## Security Notes

- Passwords: Argon2id hashing, 12+ chars with complexity
- OAuth tokens: AES-256-GCM encrypted before storage
- Admin endpoints: Require `role: admin` in JWT claims
- Rate limits: 10/min anon, 100/min auth, 500/min admin
- Drawing execution: Requires admin MFA (v1.1), logged to immutable audit

## Testing Patterns

```python
# Use factories for test data
from tests.factories import UserFactory, DrawingFactory

def test_ticket_purchase():
    user = UserFactory(point_balance=1000)
    drawing = DrawingFactory(ticket_cost_points=100, status="open")
    # ...

# Integration tests use real Oracle via testcontainers
@pytest.fixture
def db_session():
    # Spins up Oracle 23ai Free container
    ...
```

## Constraints

- MVP: US only, 18+, excludes NY/FL/RI (sweepstakes laws)
- MVP: Email/password auth only (social login in v1.1)
- MVP: Web responsive only (native apps in v1.1)
- Data sync: 15-minute batch intervals (real-time in v1.2)
- Premium features: Deferred to v1.1

## References

- PRD: `docs/FitTrack-PRD-v1.0.md`
- API Docs: `http://localhost:8000/docs` (when running)
- Terra API: https://docs.tryterra.co/
- Oracle JSON Duality: https://docs.oracle.com/en/database/oracle/oracle-database/23/jsnvu/
