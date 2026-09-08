# Implementation Plan: FitTrack

## Executive Summary

FitTrack is a gamified fitness platform that transforms physical activity into a competitive, rewarding experience. Users connect fitness trackers, earn points from activities, and spend points on sweepstakes tickets for prize drawings. The platform features 31 competition tiers (30 demographic-based + 1 open) to ensure fair competition.

This implementation plan is organized into **8 checkpoints**, progressing from foundation through production readiness. Each checkpoint delivers demonstrable, integrated functionality with comprehensive test coverage.

### Key Technical Decisions

| Decision            | Choice               | Rationale                                             |
| ------------------- | -------------------- | ----------------------------------------------------- |
| Database            | Oracle 23ai Free     | JSON Duality Views, OCI alignment, client requirement |
| Fitness Integration | Terra API            | Unified API for Apple Health, Google Fit, Fitbit      |
| Authentication      | Email/password + JWT | Social login deferred to v1.1 for MVP simplicity      |
| Background Jobs     | Redis + RQ           | Simple, reliable, Python-native                       |
| Caching             | Redis                | Session management, leaderboard performance           |

### Major Risks

| Risk                               | Impact                    | Mitigation                                               |
| ---------------------------------- | ------------------------- | -------------------------------------------------------- |
| Terra API rate limits              | Sync failures             | Implement queuing, batch requests, caching               |
| Oracle 23ai container availability | Dev environment issues    | Test container setup early, document workarounds         |
| Point manipulation attempts        | Financial/legal liability | Server-side validation, audit logging, anomaly detection |
| Sweepstakes compliance             | Legal exposure            | Conservative state list, legal review before launch      |

---

## Checkpoint Overview

| CP  | Title                                | Dependencies | Key Deliverables                                        |
| --- | ------------------------------------ | ------------ | ------------------------------------------------------- |
| 1   | Foundation: Environment & Data Layer | None         | Docker, DB, all models, CRUD APIs, seed data, test page |
| 2   | Authentication & Authorization       | CP1          | JWT auth, RBAC, email verification, protected routes    |
| 3   | Fitness Tracker Integration          | CP1, CP2     | Terra API, OAuth flows, data sync, activity logging     |
| 4   | Points & Activity System             | CP1-CP3      | Points calculation, daily caps, balance management      |
| 5   | Competition System                   | CP1-CP4      | Tiers, leaderboards, rankings, caching                  |
| 6   | Sweepstakes Engine                   | CP1-CP5      | Drawings, tickets, winner selection, audit trail        |
| 7   | Admin Dashboard & Fulfillment        | CP1-CP6      | Admin UI, sponsor management, prize fulfillment         |
| 8   | Production Readiness                 | CP1-CP7      | Monitoring, security hardening, deployment configs      |

---

## Checkpoint 1: Foundation - Environment & Data Layer

### Objective

Establish the complete development environment, implement all database models with JSON Duality Views, create CRUD APIs for all entities, generate synthetic test data, and provide a test HTML page for API validation. This checkpoint creates the foundation that all subsequent checkpoints build upon.

### Prerequisites

- [x] Development machine with Docker Desktop
- [x] Python 3.12+
- [x] Node.js 20+ (for frontend tooling)
- [x] PRD reviewed and decisions finalized

### Deliverables

#### Infrastructure Deliverables

| Component            | Path                       | Description                                              |
| -------------------- | -------------------------- | -------------------------------------------------------- |
| Docker Compose       | `docker-compose.yml`       | Oracle 23ai Free, Redis, API service                     |
| Makefile             | `Makefile`                 | All dev commands (setup, dev, test, db-\*, lint, format) |
| Environment Template | `.env.example`             | All required environment variables                       |
| CI Pipeline          | `.github/workflows/ci.yml` | Lint, test, build on PR                                  |
| pyproject.toml       | `pyproject.toml`           | Project config, dependencies, tool configs               |

#### Code Deliverables

| Component     | Path                                | Description                                |
| ------------- | ----------------------------------- | ------------------------------------------ |
| App Entry     | `src/fittrack/main.py`              | FastAPI application factory                |
| Config        | `src/fittrack/core/config.py`       | Settings with pydantic-settings            |
| Database      | `src/fittrack/core/database.py`     | Oracle connection pool, session management |
| Exceptions    | `src/fittrack/core/exceptions.py`   | RFC 7807 error handling                    |
| Health Routes | `src/fittrack/api/routes/health.py` | Liveness/readiness endpoints               |

#### Model Deliverables

| Model             | Path                                 | Description                                   |
| ----------------- | ------------------------------------ | --------------------------------------------- |
| User              | `src/fittrack/models/user.py`        | User account with status, role, point_balance |
| Profile           | `src/fittrack/models/profile.py`     | Demographics, tier assignment                 |
| TrackerConnection | `src/fittrack/models/connection.py`  | OAuth tokens for fitness trackers             |
| Activity          | `src/fittrack/models/activity.py`    | Normalized fitness activities                 |
| PointTransaction  | `src/fittrack/models/transaction.py` | Point earn/spend ledger                       |
| Drawing           | `src/fittrack/models/drawing.py`     | Sweepstakes drawings                          |
| Ticket            | `src/fittrack/models/ticket.py`      | Drawing entries                               |
| Prize             | `src/fittrack/models/prize.py`       | Drawing prizes                                |
| PrizeFulfillment  | `src/fittrack/models/fulfillment.py` | Prize delivery tracking                       |
| Sponsor           | `src/fittrack/models/sponsor.py`     | Prize sponsors                                |

#### Repository Deliverables

| Repository            | Path                                       | Description                        |
| --------------------- | ------------------------------------------ | ---------------------------------- |
| BaseRepository        | `src/fittrack/repositories/base.py`        | Generic CRUD operations            |
| UserRepository        | `src/fittrack/repositories/user.py`        | User-specific queries              |
| ProfileRepository     | `src/fittrack/repositories/profile.py`     | Profile with tier calculation      |
| ConnectionRepository  | `src/fittrack/repositories/connection.py`  | Token encryption/decryption        |
| ActivityRepository    | `src/fittrack/repositories/activity.py`    | Activity queries with date filters |
| TransactionRepository | `src/fittrack/repositories/transaction.py` | Point ledger operations            |
| DrawingRepository     | `src/fittrack/repositories/drawing.py`     | Drawing queries by status/type     |
| TicketRepository      | `src/fittrack/repositories/ticket.py`      | Ticket counts, user entries        |
| PrizeRepository       | `src/fittrack/repositories/prize.py`       | Prize management                   |
| FulfillmentRepository | `src/fittrack/repositories/fulfillment.py` | Fulfillment workflow               |
| SponsorRepository     | `src/fittrack/repositories/sponsor.py`     | Sponsor CRUD                       |

#### Database Deliverables

| Item                          | Description                                                 |
| ----------------------------- | ----------------------------------------------------------- |
| Migration: 001_initial_schema | Creates all tables with constraints and indexes             |
| Migration: 002_duality_views  | Creates JSON Duality Views for all entities                 |
| Seed Script                   | `scripts/seed_data.py` - Generates realistic synthetic data |

#### API Endpoint Deliverables

| Method | Path                        | Description                | Auth  |
| ------ | --------------------------- | -------------------------- | ----- |
| GET    | `/health/live`              | Liveness probe             | No    |
| GET    | `/health/ready`             | Readiness probe (DB check) | No    |
| GET    | `/api/v1/users`             | List users (paginated)     | Admin |
| GET    | `/api/v1/users/{id}`        | Get user by ID             | Admin |
| POST   | `/api/v1/users`             | Create user                | Admin |
| PUT    | `/api/v1/users/{id}`        | Update user                | Admin |
| DELETE | `/api/v1/users/{id}`        | Soft delete user           | Admin |
| GET    | `/api/v1/profiles`          | List profiles              | Admin |
| GET    | `/api/v1/profiles/{id}`     | Get profile                | Admin |
| POST   | `/api/v1/profiles`          | Create profile             | Admin |
| PUT    | `/api/v1/profiles/{id}`     | Update profile             | Admin |
| GET    | `/api/v1/connections`       | List connections           | Admin |
| GET    | `/api/v1/connections/{id}`  | Get connection             | Admin |
| POST   | `/api/v1/connections`       | Create connection          | Admin |
| DELETE | `/api/v1/connections/{id}`  | Delete connection          | Admin |
| GET    | `/api/v1/activities`        | List activities (filtered) | Admin |
| GET    | `/api/v1/activities/{id}`   | Get activity               | Admin |
| POST   | `/api/v1/activities`        | Create activity            | Admin |
| GET    | `/api/v1/transactions`      | List transactions          | Admin |
| GET    | `/api/v1/transactions/{id}` | Get transaction            | Admin |
| POST   | `/api/v1/transactions`      | Create transaction         | Admin |
| GET    | `/api/v1/drawings`          | List drawings              | Admin |
| GET    | `/api/v1/drawings/{id}`     | Get drawing                | Admin |
| POST   | `/api/v1/drawings`          | Create drawing             | Admin |
| PUT    | `/api/v1/drawings/{id}`     | Update drawing             | Admin |
| DELETE | `/api/v1/drawings/{id}`     | Cancel drawing             | Admin |
| GET    | `/api/v1/tickets`           | List tickets               | Admin |
| GET    | `/api/v1/tickets/{id}`      | Get ticket                 | Admin |
| POST   | `/api/v1/tickets`           | Create ticket              | Admin |
| GET    | `/api/v1/prizes`            | List prizes                | Admin |
| GET    | `/api/v1/prizes/{id}`       | Get prize                  | Admin |
| POST   | `/api/v1/prizes`            | Create prize               | Admin |
| PUT    | `/api/v1/prizes/{id}`       | Update prize               | Admin |
| GET    | `/api/v1/fulfillments`      | List fulfillments          | Admin |
| GET    | `/api/v1/fulfillments/{id}` | Get fulfillment            | Admin |
| PUT    | `/api/v1/fulfillments/{id}` | Update fulfillment         | Admin |
| GET    | `/api/v1/sponsors`          | List sponsors              | Admin |
| GET    | `/api/v1/sponsors/{id}`     | Get sponsor                | Admin |
| POST   | `/api/v1/sponsors`          | Create sponsor             | Admin |
| PUT    | `/api/v1/sponsors/{id}`     | Update sponsor             | Admin |
| DELETE | `/api/v1/sponsors/{id}`     | Deactivate sponsor         | Admin |

#### Synthetic Data Deliverables

| Data Type           | Quantity | Description                                             |
| ------------------- | -------- | ------------------------------------------------------- |
| Admin Users         | 3        | Platform administrators                                 |
| Premium Users       | 15       | Premium tier users across multiple tiers                |
| Regular Users       | 50       | Free users across all 31 tiers                          |
| Tracker Connections | 60       | Mix of Fitbit, Google Fit, Apple Health                 |
| Activities          | 500+     | 30 days of activity history per user                    |
| Point Transactions  | 1000+    | Earn and spend transactions                             |
| Sponsors            | 5        | Sample sponsors with logos                              |
| Drawings            | 15       | Mix of daily, weekly, monthly (open, closed, completed) |
| Tickets             | 200+     | User entries across drawings                            |
| Prizes              | 20       | Various prize types and values                          |
| Fulfillments        | 10       | Various fulfillment statuses                            |

#### Test Page Deliverables

| Component    | Path                                  | Description                 |
| ------------ | ------------------------------------- | --------------------------- |
| Test Page    | `devtools/test_page.html`             | Single-page API tester      |
| Static Serve | `src/fittrack/api/routes/devtools.py` | Serves test page (dev only) |

**Test Page Features:**

- Tabbed interface for each entity type
- Forms for all CRUD operations
- Response viewer with syntax highlighting
- Database seed/reset controls
- Sample data viewer with pagination
- Quick-filter by common queries
- JWT token input for auth testing
- Environment indicator (dev/staging)

#### Test Deliverables

| Test Suite         | Path                                     | Coverage Target |
| ------------------ | ---------------------------------------- | --------------- |
| Repository Tests   | `tests/integration/test_repositories.py` | >90%            |
| API Endpoint Tests | `tests/integration/test_api_*.py`        | >85%            |
| Factory Tests      | `tests/unit/test_factories.py`           | 100%            |
| Model Tests        | `tests/unit/test_models.py`              | >90%            |
| Config Tests       | `tests/unit/test_config.py`              | 100%            |

### Acceptance Criteria

```gherkin
Feature: Development Environment Setup

  Scenario: Fresh clone to running system
    Given a fresh clone of the repository
    When I run "make setup && make dev"
    Then all services start within 5 minutes
    And the API responds at http://localhost:8000/health/live
    And the test page loads at http://localhost:8000/devtools

Feature: Database Seeding

  Scenario: Seed database with synthetic data
    Given the development environment is running
    When I run "make db-seed"
    Then the database contains at least 50 users
    And each user has a profile with tier assignment
    And there are activities spanning 30 days
    And there are drawings in various statuses

Feature: CRUD API Operations

  Scenario: Create and retrieve a user
    Given the API is running
    When I POST a valid user to /api/v1/users
    Then I receive a 201 response with user ID
    And I can GET the user at /api/v1/users/{id}
    And the user data matches what I submitted

  Scenario: List entities with pagination
    Given the database has 50+ users
    When I GET /api/v1/users?page=1&limit=10
    Then I receive 10 users
    And the response includes pagination metadata
    And I can navigate to page 2

Feature: Test Page Functionality

  Scenario: View seeded data
    Given the database is seeded
    When I open the test page
    And I select the "Users" tab
    Then I see a paginated list of users
    And I can filter by role or status

  Scenario: Create entity via test page
    Given the test page is open
    When I fill in the "Create User" form
    And I click "Submit"
    Then I see a success message
    And the new user appears in the list
```

### Security Considerations

- Admin API key required for all CRUD endpoints (temporary, replaced by JWT in CP2)
- Database credentials stored in environment variables
- No PII in logs (mask email, DOB in debug output)
- SQL injection prevention via parameterized queries
- Input validation with Pydantic schemas

### Definition of Done

- [ ] Docker Compose starts Oracle 23ai, Redis, and API successfully
- [ ] All 11 models implemented with Pydantic validation
- [ ] All 11 repositories implemented with CRUD operations
- [ ] All CRUD API endpoints functional and documented
- [ ] Database migrations create all tables and duality views
- [ ] Seed script generates realistic data for all entities
- [ ] Test page allows CRUD operations on all entities
- [ ] Repository tests achieve >90% coverage
- [ ] API tests achieve >85% coverage
- [ ] `make setup && make dev` works in <5 minutes from fresh clone
- [ ] CI pipeline runs lint and tests on PR
- [ ] README documents setup process

---

## Checkpoint 2: Authentication & Authorization

### Objective

Implement secure JWT-based authentication with email verification, role-based access control (RBAC), and protected API routes. Users can register, verify email, login, and access resources based on their role.

### Prerequisites

- [x] Checkpoint 1 completed
- [x] SMTP service available (Mailpit for dev)

### Deliverables

#### Code Deliverables

| Component         | Path                               | Description                         |
| ----------------- | ---------------------------------- | ----------------------------------- |
| Auth Service      | `src/fittrack/services/auth.py`    | Login, register, token management   |
| Password Utils    | `src/fittrack/core/security.py`    | Argon2id hashing, JWT encode/decode |
| Email Service     | `src/fittrack/services/email.py`   | Email verification, password reset  |
| Auth Dependencies | `src/fittrack/api/deps.py`         | get_current_user, require_role      |
| Auth Routes       | `src/fittrack/api/routes/auth.py`  | Auth endpoints                      |
| User Routes       | `src/fittrack/api/routes/users.py` | User self-service endpoints         |

#### API Endpoint Deliverables

| Method | Path                           | Description              | Auth          |
| ------ | ------------------------------ | ------------------------ | ------------- |
| POST   | `/api/v1/auth/register`        | Register new user        | No            |
| POST   | `/api/v1/auth/verify-email`    | Verify email with token  | No            |
| POST   | `/api/v1/auth/login`           | Authenticate, get tokens | No            |
| POST   | `/api/v1/auth/refresh`         | Refresh access token     | Refresh Token |
| POST   | `/api/v1/auth/logout`          | Invalidate refresh token | Yes           |
| POST   | `/api/v1/auth/forgot-password` | Initiate password reset  | No            |
| POST   | `/api/v1/auth/reset-password`  | Complete password reset  | No            |
| GET    | `/api/v1/users/me`             | Get current user profile | Yes           |
| PUT    | `/api/v1/users/me`             | Update current user      | Yes           |
| PUT    | `/api/v1/users/me/password`    | Change password          | Yes           |
| DELETE | `/api/v1/users/me`             | Delete account           | Yes           |

#### Test Deliverables

| Test Suite           | Path                                 | Coverage Target |
| -------------------- | ------------------------------------ | --------------- |
| Auth Service Tests   | `tests/unit/test_auth_service.py`    | >90%            |
| Security Utils Tests | `tests/unit/test_security.py`        | >95%            |
| Auth API Tests       | `tests/integration/test_auth_api.py` | >90%            |
| RBAC Tests           | `tests/integration/test_rbac.py`     | >90%            |

### Acceptance Criteria

```gherkin
Feature: User Registration

  Scenario: Successful registration
    Given I am a new user
    When I POST valid registration data to /auth/register
    Then I receive a 201 response
    And a verification email is sent
    And I cannot login until email is verified

  Scenario: Registration with invalid age
    Given I am under 18
    When I POST registration data with my DOB
    Then I receive a 400 error
    And the error indicates age requirement

  Scenario: Registration from ineligible state
    Given I live in New York
    When I POST registration data with state "NY"
    Then I receive a 400 error
    And the error explains state ineligibility

Feature: Authentication

  Scenario: Successful login
    Given I am a registered, verified user
    When I POST valid credentials to /auth/login
    Then I receive access and refresh tokens
    And the access token expires in 1 hour

  Scenario: Login with wrong password
    Given I am a registered user
    When I POST incorrect password
    Then I receive a 401 error
    And the error does not reveal if email exists

Feature: Authorization

  Scenario: Access protected endpoint with token
    Given I have a valid access token
    When I GET /users/me with Bearer token
    Then I receive my user data

  Scenario: Admin-only endpoint access
    Given I am a regular user
    When I try to access /admin/users
    Then I receive a 403 Forbidden error
```

### Security Considerations

- Passwords: Argon2id with memory=65536, iterations=3, parallelism=4
- JWT: RS256 signing, 1hr access token, 30d refresh token
- Refresh tokens stored hashed in database
- Account lockout after 5 failed attempts (15 min)
- Rate limiting on auth endpoints (5/min for login)
- Email verification tokens expire in 24 hours
- Password reset tokens expire in 1 hour

### Definition of Done

- [ ] Users can register with email, password, DOB, state
- [ ] Email verification flow works end-to-end
- [ ] Login returns JWT access and refresh tokens
- [ ] Token refresh extends session
- [ ] Password reset flow works end-to-end
- [ ] RBAC enforced on all protected endpoints
- [ ] Account lockout implemented
- [ ] Rate limiting on auth endpoints
- [ ] Test page updated with auth functionality
- [ ] All tests passing with required coverage

---

## Checkpoint 3: Fitness Tracker Integration

### Objective

Implement Terra API integration for fitness tracker connectivity. Users can connect Apple Health, Google Fit, or Fitbit accounts and have their activity data synced automatically every 15 minutes.

### Prerequisites

- [x] Checkpoint 2 completed
- [x] Terra API credentials obtained

### Deliverables

#### Code Deliverables

| Component          | Path                                     | Description                      |
| ------------------ | ---------------------------------------- | -------------------------------- |
| Terra Service      | `src/fittrack/services/terra.py`         | Terra API client wrapper         |
| Connection Service | `src/fittrack/services/connection.py`    | OAuth flow management            |
| Sync Service       | `src/fittrack/services/sync.py`          | Activity data normalization      |
| Sync Worker        | `src/fittrack/workers/sync_worker.py`    | Background sync job              |
| Webhook Handler    | `src/fittrack/api/routes/webhooks.py`    | Terra webhook receiver           |
| Connection Routes  | `src/fittrack/api/routes/connections.py` | User-facing connection endpoints |

#### API Endpoint Deliverables

| Method | Path                                      | Description            | Auth        |
| ------ | ----------------------------------------- | ---------------------- | ----------- |
| GET    | `/api/v1/connections`                     | List my connections    | User        |
| POST   | `/api/v1/connections/{provider}/initiate` | Start OAuth flow       | User        |
| POST   | `/api/v1/connections/{provider}/callback` | Complete OAuth         | User        |
| DELETE | `/api/v1/connections/{provider}`          | Disconnect tracker     | User        |
| POST   | `/api/v1/connections/{provider}/sync`     | Force sync             | User        |
| POST   | `/webhooks/terra`                         | Terra webhook receiver | Webhook Sig |

#### Test Deliverables

| Test Suite           | Path                                        | Coverage Target |
| -------------------- | ------------------------------------------- | --------------- |
| Terra Service Tests  | `tests/unit/test_terra_service.py`          | >85%            |
| Sync Service Tests   | `tests/unit/test_sync_service.py`           | >90%            |
| Connection API Tests | `tests/integration/test_connections_api.py` | >85%            |
| Webhook Tests        | `tests/integration/test_webhooks.py`        | >90%            |

### Acceptance Criteria

```gherkin
Feature: Tracker Connection

  Scenario: Connect Fitbit account
    Given I am a logged-in user
    When I POST to /connections/fitbit/initiate
    Then I receive an authorization URL
    And the URL points to Terra's OAuth flow

  Scenario: Complete OAuth callback
    Given I authorized the connection
    When Terra redirects to our callback
    Then a connection is created
    And initial data sync is triggered

Feature: Activity Sync

  Scenario: Automatic background sync
    Given I have a connected tracker
    And 15 minutes have passed since last sync
    When the sync worker runs
    Then new activities are fetched from Terra
    And activities are normalized and stored
    And duplicate activities are skipped

  Scenario: Receive Terra webhook
    Given I have a connected tracker
    When Terra sends a data webhook
    Then the webhook signature is verified
    And new activities are processed immediately
```

### Security Considerations

- Terra webhook signature verification (HMAC-SHA256)
- OAuth tokens encrypted with AES-256-GCM before storage
- Refresh tokens proactively refreshed before expiry
- Connection-specific encryption keys derived from master key

### Definition of Done

- [ ] Users can connect all three tracker types via Terra
- [ ] OAuth flow works end-to-end
- [ ] Background sync runs every 15 minutes
- [ ] Terra webhooks processed correctly
- [ ] Activities normalized to common format
- [ ] Duplicate activities detected and skipped
- [ ] Connection errors handled gracefully
- [ ] Test page shows connection status and sync history
- [ ] All tests passing with required coverage

---

## Checkpoint 4: Points & Activity System

### Objective

Implement the complete points system including activity-based point earning, daily caps, bonus achievements, and point balance management with optimistic locking for concurrent operations.

### Prerequisites

- [x] Checkpoint 3 completed

### Deliverables

#### Code Deliverables

| Component        | Path                                    | Description                       |
| ---------------- | --------------------------------------- | --------------------------------- |
| Points Service   | `src/fittrack/services/points.py`       | Point calculation and awarding    |
| Activity Service | `src/fittrack/services/activity.py`     | Activity processing and summaries |
| Points Worker    | `src/fittrack/workers/points_worker.py` | Background point calculation      |
| Activity Routes  | `src/fittrack/api/routes/activities.py` | Activity endpoints                |
| Points Routes    | `src/fittrack/api/routes/points.py`     | Points endpoints                  |

#### API Endpoint Deliverables

| Method | Path                          | Description              | Auth |
| ------ | ----------------------------- | ------------------------ | ---- |
| GET    | `/api/v1/activities`          | My activity history      | User |
| GET    | `/api/v1/activities/summary`  | Today/week/month summary | User |
| GET    | `/api/v1/points/balance`      | Current point balance    | User |
| GET    | `/api/v1/points/transactions` | Transaction history      | User |

#### Test Deliverables

| Test Suite                        | Path                                   | Coverage Target |
| --------------------------------- | -------------------------------------- | --------------- |
| Points Service Tests              | `tests/unit/test_points_service.py`    | >95%            |
| Activity Service Tests            | `tests/unit/test_activity_service.py`  | >90%            |
| Points Calculation Property Tests | `tests/unit/test_points_properties.py` | N/A             |
| Points API Tests                  | `tests/integration/test_points_api.py` | >90%            |

### Acceptance Criteria

```gherkin
Feature: Point Earning

  Scenario: Earn points from steps
    Given I walked 5,000 steps today
    When points are calculated
    Then I earn 50 points (10 per 1,000 steps)

  Scenario: Daily point cap
    Given I have already earned 950 points today
    When I complete an activity worth 100 points
    Then I only receive 50 points (capped at 1,000)
    And the remaining 50 points are forfeited

  Scenario: Daily step goal bonus
    Given I have walked 9,500 steps
    When I walk 500 more steps (reaching 10,000)
    Then I earn regular step points
    And I earn the 100 point daily goal bonus

Feature: Point Balance

  Scenario: Concurrent point operations
    Given my balance is 1,000 points
    When two ticket purchases of 500 points happen simultaneously
    Then one succeeds and one fails (optimistic lock)
    And my balance is 500 points (not -0 or 0)
```

### Security Considerations

- Point calculations happen server-side only
- Optimistic locking on point_balance prevents race conditions
- Audit trail for all point transactions
- Anomaly detection flags unusual earning patterns

### Definition of Done

- [ ] Points calculated correctly per rate table
- [ ] Daily caps enforced (1,000 points, 3 workouts, 20K steps)
- [ ] Bonus achievements awarded correctly
- [ ] Point balance uses optimistic locking
- [ ] Transaction history complete and accurate
- [ ] Activity summaries show today/week/month
- [ ] Test page displays points and activities
- [ ] Property-based tests verify calculation logic
- [ ] All tests passing with required coverage

---

## Checkpoint 5: Competition System

### Objective

Implement the tier assignment system, leaderboards with caching, and ranking calculations. Users can view their ranking within their tier and browse leaderboards across different time periods.

### Prerequisites

- [x] Checkpoint 4 completed

### Deliverables

#### Code Deliverables

| Component           | Path                                         | Description                     |
| ------------------- | -------------------------------------------- | ------------------------------- |
| Tier Service        | `src/fittrack/services/tier.py`              | Tier calculation and assignment |
| Leaderboard Service | `src/fittrack/services/leaderboard.py`       | Ranking calculations            |
| Leaderboard Cache   | `src/fittrack/services/leaderboard_cache.py` | Redis caching layer             |
| Leaderboard Worker  | `src/fittrack/workers/leaderboard_worker.py` | Background ranking updates      |
| Leaderboard Routes  | `src/fittrack/api/routes/leaderboards.py`    | Leaderboard endpoints           |

#### API Endpoint Deliverables

| Method | Path                           | Description          | Auth |
| ------ | ------------------------------ | -------------------- | ---- |
| GET    | `/api/v1/leaderboards/daily`   | Daily leaderboard    | User |
| GET    | `/api/v1/leaderboards/weekly`  | Weekly leaderboard   | User |
| GET    | `/api/v1/leaderboards/monthly` | Monthly leaderboard  | User |
| GET    | `/api/v1/leaderboards/alltime` | All-time leaderboard | User |
| GET    | `/api/v1/users/{id}/public`    | Public user profile  | User |

#### Test Deliverables

| Test Suite                | Path                                          | Coverage Target |
| ------------------------- | --------------------------------------------- | --------------- |
| Tier Service Tests        | `tests/unit/test_tier_service.py`             | >95%            |
| Leaderboard Service Tests | `tests/unit/test_leaderboard_service.py`      | >90%            |
| Leaderboard Cache Tests   | `tests/integration/test_leaderboard_cache.py` | >85%            |
| Leaderboard API Tests     | `tests/integration/test_leaderboards_api.py`  | >90%            |

### Acceptance Criteria

```gherkin
Feature: Tier Assignment

  Scenario: Automatic tier assignment
    Given I complete my profile with age=35, sex=male, fitness=intermediate
    Then I am assigned tier "M-30-39-INT"
    And I appear on that tier's leaderboard

  Scenario: Open tier opt-in
    Given I am assigned to a demographic tier
    When I opt into the Open tier
    Then I appear on both my demographic and Open leaderboards

Feature: Leaderboards

  Scenario: View my tier leaderboard
    Given I am in tier "F-18-29-BEG"
    When I GET /leaderboards/weekly
    Then I see rankings for my tier
    And I see my own ranking highlighted
    And I see users ranked ±10 positions from me

  Scenario: Leaderboard reset
    Given it is Monday 00:00 EST
    When the weekly leaderboard resets
    Then all weekly rankings start at 0
    And the previous week's final rankings are archived
```

### Security Considerations

- Tier assignment cannot be directly modified by users
- Public profiles show only display name and tier (no PII)
- Leaderboard data cached to prevent DB overload
- Rate limiting on leaderboard queries

### Definition of Done

- [ ] Tier codes calculated from profile fields
- [ ] All 31 tiers supported (30 demographic + Open)
- [ ] Leaderboards show top 100 + user's position
- [ ] Rankings update within 15 minutes
- [ ] Redis caching reduces DB load
- [ ] Public profiles expose only public data
- [ ] Test page displays leaderboards
- [ ] All tests passing with required coverage

---

## Checkpoint 6: Sweepstakes Engine

### Objective

Implement the complete sweepstakes system including drawing management, ticket purchasing, winner selection with CSPRNG, and result publication. This is the core gamification feature of FitTrack.

### Prerequisites

- [x] Checkpoint 5 completed

### Deliverables

#### Code Deliverables

| Component       | Path                                     | Description                        |
| --------------- | ---------------------------------------- | ---------------------------------- |
| Drawing Service | `src/fittrack/services/drawing.py`       | Drawing lifecycle management       |
| Ticket Service  | `src/fittrack/services/ticket.py`        | Ticket purchase and validation     |
| Winner Service  | `src/fittrack/services/winner.py`        | CSPRNG selection, result recording |
| Drawing Worker  | `src/fittrack/workers/drawing_worker.py` | Scheduled drawing execution        |
| Drawing Routes  | `src/fittrack/api/routes/drawings.py`    | Drawing endpoints                  |

#### API Endpoint Deliverables

| Method | Path                            | Description             | Auth |
| ------ | ------------------------------- | ----------------------- | ---- |
| GET    | `/api/v1/drawings`              | List available drawings | User |
| GET    | `/api/v1/drawings/{id}`         | Get drawing details     | User |
| POST   | `/api/v1/drawings/{id}/tickets` | Purchase tickets        | User |
| GET    | `/api/v1/drawings/{id}/results` | Get drawing results     | User |
| GET    | `/api/v1/drawings/my-entries`   | My drawing entries      | User |
| GET    | `/api/v1/drawings/my-wins`      | My prizes won           | User |

#### Test Deliverables

| Test Suite              | Path                                          | Coverage Target |
| ----------------------- | --------------------------------------------- | --------------- |
| Drawing Service Tests   | `tests/unit/test_drawing_service.py`          | >90%            |
| Ticket Service Tests    | `tests/unit/test_ticket_service.py`           | >95%            |
| Winner Service Tests    | `tests/unit/test_winner_service.py`           | >95%            |
| Drawing API Tests       | `tests/integration/test_drawings_api.py`      | >90%            |
| Drawing Execution Tests | `tests/integration/test_drawing_execution.py` | >95%            |

### Acceptance Criteria

```gherkin
Feature: Ticket Purchase

  Scenario: Successful ticket purchase
    Given I have 1,000 points
    And there is an open daily drawing (100 pts/ticket)
    When I purchase 5 tickets
    Then my balance is reduced to 500 points
    And I have 5 tickets for the drawing
    And a point transaction is recorded

  Scenario: Insufficient points
    Given I have 50 points
    When I try to purchase a 100 point ticket
    Then I receive a 400 error
    And my balance is unchanged

Feature: Drawing Execution

  Scenario: Successful drawing
    Given a drawing with 1,000 tickets closes
    When the drawing is executed
    Then ticket numbers are assigned sequentially
    And a winner is selected via CSPRNG
    And the random seed is recorded for audit
    And winners are notified via email
    And results are published

  Scenario: Drawing with no tickets
    Given a drawing with 0 tickets closes
    When the drawing would execute
    Then the drawing is cancelled
    And no winner is selected
```

### Security Considerations

- CSPRNG using Python secrets module
- Immutable audit trail for all drawing operations
- Ticket snapshot created at sales close (no modifications after)
- Drawing execution requires scheduled job (no manual API)
- Results published automatically (no manual editing)

### Definition of Done

- [ ] Drawings support all four types (daily, weekly, monthly, annual)
- [ ] Ticket purchases deduct points atomically
- [ ] Drawing execution uses CSPRNG
- [ ] Complete audit trail for drawings
- [ ] Winner notification via email
- [ ] Results published to all users
- [ ] User can view their entries and wins
- [ ] Test page allows ticket purchases
- [ ] All tests passing with required coverage

---

## Checkpoint 7: Admin Dashboard & Prize Fulfillment

### Objective

Implement the administrative interface for managing drawings, sponsors, prizes, users, and prize fulfillment. Admins can create drawings, manage sponsors, and track prize delivery.

### Prerequisites

- [x] Checkpoint 6 completed

### Deliverables

#### Code Deliverables

| Component             | Path                                     | Description                |
| --------------------- | ---------------------------------------- | -------------------------- |
| Admin Drawing Service | `src/fittrack/services/admin/drawing.py` | Drawing CRUD for admins    |
| Admin Sponsor Service | `src/fittrack/services/admin/sponsor.py` | Sponsor management         |
| Admin User Service    | `src/fittrack/services/admin/user.py`    | User moderation            |
| Fulfillment Service   | `src/fittrack/services/fulfillment.py`   | Prize fulfillment workflow |
| Admin Routes          | `src/fittrack/api/routes/admin/*.py`     | Admin API endpoints        |
| React Admin UI        | `frontend/src/admin/*`                   | Admin dashboard React app  |

#### API Endpoint Deliverables

| Method | Path                                     | Description               | Auth  |
| ------ | ---------------------------------------- | ------------------------- | ----- |
| POST   | `/api/v1/admin/drawings`                 | Create drawing            | Admin |
| PUT    | `/api/v1/admin/drawings/{id}`            | Update drawing            | Admin |
| POST   | `/api/v1/admin/drawings/{id}/execute`    | Manual execution          | Admin |
| DELETE | `/api/v1/admin/drawings/{id}`            | Cancel drawing            | Admin |
| GET    | `/api/v1/admin/sponsors`                 | List sponsors             | Admin |
| POST   | `/api/v1/admin/sponsors`                 | Create sponsor            | Admin |
| PUT    | `/api/v1/admin/sponsors/{id}`            | Update sponsor            | Admin |
| GET    | `/api/v1/admin/fulfillments`             | List pending fulfillments | Admin |
| PUT    | `/api/v1/admin/fulfillments/{id}`        | Update fulfillment        | Admin |
| POST   | `/api/v1/admin/fulfillments/{id}/ship`   | Mark shipped              | Admin |
| GET    | `/api/v1/admin/users`                    | List/search users         | Admin |
| PUT    | `/api/v1/admin/users/{id}/status`        | Suspend/ban user          | Admin |
| POST   | `/api/v1/admin/users/{id}/adjust-points` | Adjust points             | Admin |
| GET    | `/api/v1/admin/analytics/overview`       | Dashboard metrics         | Admin |

#### Test Deliverables

| Test Suite                | Path                                     | Coverage Target |
| ------------------------- | ---------------------------------------- | --------------- |
| Admin Service Tests       | `tests/unit/test_admin_services.py`      | >90%            |
| Fulfillment Service Tests | `tests/unit/test_fulfillment_service.py` | >90%            |
| Admin API Tests           | `tests/integration/test_admin_api.py`    | >85%            |

### Acceptance Criteria

```gherkin
Feature: Drawing Management

  Scenario: Create a drawing
    Given I am an admin
    When I create a new weekly drawing with prizes
    Then the drawing is created in "draft" status
    And I can publish it to "scheduled" status

Feature: Prize Fulfillment

  Scenario: Process winner fulfillment
    Given a user won a physical prize
    When they confirm their shipping address
    Then the fulfillment moves to "address_confirmed"
    And admin can mark it as shipped with tracking

  Scenario: Handle forfeit timeout
    Given a winner hasn't confirmed address in 14 days
    When the forfeit check runs
    Then the fulfillment is marked "forfeited"
    And the prize may be re-drawn

Feature: User Moderation

  Scenario: Suspend suspicious account
    Given a user has anomalous activity patterns
    When I suspend their account
    Then they cannot login
    And their tickets remain valid
    And they receive notification email
```

### Security Considerations

- All admin actions logged to audit trail
- Admin role verified on every request
- Sensitive operations require confirmation
- Point adjustments require reason/justification

### Definition of Done

- [ ] Admins can create/edit/cancel drawings
- [ ] Sponsor management fully functional
- [ ] Prize fulfillment workflow complete
- [ ] User suspension/ban working
- [ ] Point adjustments with audit trail
- [ ] Basic analytics dashboard
- [ ] Admin UI functional (basic React)
- [ ] All tests passing with required coverage

---

## Checkpoint 8: Production Readiness

### Objective

Prepare the application for production deployment including comprehensive monitoring, security hardening, performance optimization, and deployment configurations for OCI.

### Prerequisites

- [x] Checkpoint 7 completed
- [x] OCI environment provisioned

### Deliverables

#### Infrastructure Deliverables

| Component         | Path                             | Description                 |
| ----------------- | -------------------------------- | --------------------------- |
| Terraform Configs | `infrastructure/terraform/*.tf`  | OCI resource definitions    |
| Helm Charts       | `infrastructure/helm/fittrack/*` | Kubernetes deployment       |
| Production Docker | `Dockerfile.prod`                | Optimized production image  |
| Nginx Config      | `infrastructure/nginx/*.conf`    | Reverse proxy configuration |

#### Code Deliverables

| Component          | Path                                | Description                       |
| ------------------ | ----------------------------------- | --------------------------------- |
| Metrics Middleware | `src/fittrack/core/metrics.py`      | Prometheus metrics                |
| Structured Logging | `src/fittrack/core/logging.py`      | JSON logging with correlation IDs |
| Health Checks      | `src/fittrack/api/routes/health.py` | Enhanced health endpoints         |
| Rate Limiting      | `src/fittrack/core/rate_limit.py`   | Redis-based rate limiting         |
| Security Headers   | `src/fittrack/core/security.py`     | HSTS, CSP, X-Frame-Options        |

#### Documentation Deliverables

| Document           | Path                         | Description                 |
| ------------------ | ---------------------------- | --------------------------- |
| Deployment Guide   | `docs/DEPLOYMENT.md`         | Production deployment steps |
| Runbook            | `docs/RUNBOOK.md`            | Operational procedures      |
| Security Checklist | `docs/SECURITY_CHECKLIST.md` | Pre-launch security review  |

#### Test Deliverables

| Test Type        | Tool      | Description               |
| ---------------- | --------- | ------------------------- |
| Load Testing     | k6        | 5,000 concurrent users    |
| Security Scan    | OWASP ZAP | DAST vulnerability scan   |
| Dependency Audit | Safety    | Known vulnerability check |

### Acceptance Criteria

```gherkin
Feature: Production Deployment

  Scenario: Deploy to staging
    Given all tests pass
    When I run the deployment pipeline
    Then the application deploys to staging
    And health checks pass
    And monitoring dashboards populate

Feature: Performance

  Scenario: Handle peak load
    Given 5,000 concurrent users
    When the load test runs
    Then API response times remain under 500ms (p95)
    And no errors occur
    And the system auto-scales appropriately

Feature: Security

  Scenario: Security headers present
    Given the application is running
    When I inspect response headers
    Then HSTS is enabled
    And CSP is configured
    And X-Frame-Options denies framing
```

### Security Considerations

- TLS 1.3 enforced
- Security headers on all responses
- Rate limiting on all endpoints
- OWASP ZAP scan passes
- Dependency vulnerabilities addressed
- Secrets managed via OCI Vault

### Definition of Done

- [ ] Terraform provisions all OCI resources
- [ ] Helm chart deploys to OKE cluster
- [ ] Prometheus metrics exported
- [ ] Grafana dashboards created
- [ ] Structured logging with correlation IDs
- [ ] Rate limiting functional
- [ ] Load test passes (5,000 users)
- [ ] Security scan passes
- [ ] Deployment guide complete
- [ ] Runbook documents all procedures

---

## Risk Register

| ID  | Risk                                       | Probability | Impact   | Mitigation                                                      |
| --- | ------------------------------------------ | ----------- | -------- | --------------------------------------------------------------- |
| R1  | Oracle 23ai container unavailable/unstable | Medium      | High     | Test early, document workarounds, have PostgreSQL fallback plan |
| R2  | Terra API rate limits cause sync failures  | Medium      | Medium   | Implement request queuing, batch optimization, caching          |
| R3  | Point balance race conditions              | Medium      | High     | Optimistic locking, comprehensive integration tests             |
| R4  | Drawing manipulation attempts              | Low         | Critical | CSPRNG, audit trails, no manual result editing                  |
| R5  | Sweepstakes legal compliance issues        | Low         | Critical | Legal review before launch, conservative state list             |
| R6  | Performance degradation at scale           | Medium      | Medium   | Redis caching, database indexing, load testing                  |
| R7  | Third-party API changes                    | Medium      | Medium   | Abstract integration layer, monitor announcements               |
| R8  | Data breach                                | Low         | Critical | Encryption at rest/transit, minimal PII, access controls        |

## Assumptions

| ID  | Assumption                                     | Impact if Wrong                   | Validation                                |
| --- | ---------------------------------------------- | --------------------------------- | ----------------------------------------- |
| A1  | Oracle 23ai Free container works for local dev | Significant rework needed         | Test in CP1 first week                    |
| A2  | Terra API covers all needed fitness data       | Alternative integrations required | Review Terra docs, test with real devices |
| A3  | 15-minute sync interval acceptable to users    | User complaints, churn            | Beta user feedback                        |
| A4  | Daily 1,000 point cap prevents gaming          | Gaming or user frustration        | Monitor outliers, adjust as needed        |
| A5  | Email verification sufficient for MVP security | Account takeovers                 | Security monitoring, MFA in v1.1          |
| A6  | Three fitness trackers cover target market     | Low adoption                      | Market research                           |
| A7  | Gift cards sufficient for launch prizes        | Low engagement                    | User surveys                              |

## Technical Debt Tracking

| Item                               | Introduced | Planned Resolution      | Priority |
| ---------------------------------- | ---------- | ----------------------- | -------- |
| Admin API key authentication (CP1) | CP1        | Replace with JWT in CP2 | High     |
| Basic React admin UI               | CP7        | Polish in post-MVP      | Medium   |
| Manual prize fulfillment           | CP7        | Automate in v1.1        | Low      |
| 15-minute sync interval            | CP3        | Real-time in v1.2       | Low      |
