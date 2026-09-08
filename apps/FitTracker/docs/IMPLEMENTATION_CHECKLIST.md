# FitTrack Implementation Checklist

> Track progress by checking off completed items. Update this document as work progresses.

**Legend:**

- [ ] Not started
- [x] Completed
- [~] In progress (add notes)

---

## Checkpoint 1: Foundation - Environment & Data Layer

### 1.1 Infrastructure Setup

- [ ] Create project directory structure
- [ ] Initialize Git repository with .gitignore
- [ ] Create pyproject.toml with dependencies
  - [ ] FastAPI, uvicorn, python-oracledb
  - [ ] pydantic, pydantic-settings
  - [ ] redis, rq
  - [ ] pytest, pytest-asyncio, pytest-cov
  - [ ] hypothesis (property-based testing)
  - [ ] faker (synthetic data)
  - [ ] ruff, black, mypy (dev tools)
- [ ] Create Makefile with commands
  - [ ] `make setup` - first-time setup
  - [ ] `make dev` - start all services
  - [ ] `make test` - run all tests
  - [ ] `make test-cov` - tests with coverage
  - [ ] `make db-migrate` - run migrations
  - [ ] `make db-seed` - seed database
  - [ ] `make db-reset` - drop and recreate with seed
  - [ ] `make lint` - run ruff
  - [ ] `make format` - run black and isort
- [ ] Create docker-compose.yml
  - [ ] Oracle 23ai Free container
  - [ ] Redis container
  - [ ] API service container
  - [ ] Volume mounts for persistence
- [ ] Create .env.example with all variables
- [ ] Create Dockerfile for API service
- [ ] Create .github/workflows/ci.yml
  - [ ] Lint check (ruff)
  - [ ] Type check (mypy)
  - [ ] Unit tests
  - [ ] Integration tests (with services)
  - [ ] Coverage reporting

### 1.2 Core Application Structure

- [ ] Create src/fittrack/main.py (FastAPI app factory)
- [ ] Create src/fittrack/core/config.py (pydantic-settings)
- [ ] Create src/fittrack/core/database.py
  - [ ] Oracle connection pool setup
  - [ ] Session/connection management
  - [ ] JSON Duality View helpers
- [ ] Create src/fittrack/core/exceptions.py
  - [ ] Base exception classes
  - [ ] RFC 7807 error response handler
  - [ ] Exception-to-HTTP mapping
- [ ] Create src/fittrack/core/pagination.py
  - [ ] Pagination request schema
  - [ ] Pagination response schema
  - [ ] Pagination helper functions
- [ ] Create health check endpoints
  - [ ] GET /health/live (always returns 200)
  - [ ] GET /health/ready (checks DB, Redis)

### 1.3 Models

- [ ] Create src/fittrack/models/base.py (base model with ID, timestamps)
- [ ] Create src/fittrack/models/user.py
  - [ ] Fields: user_id, email, password_hash, email_verified, status, role, point_balance
  - [ ] Status enum: pending, active, suspended, banned
  - [ ] Role enum: user, premium, admin
  - [ ] Validation rules
- [ ] Create src/fittrack/models/profile.py
  - [ ] Fields: profile_id, user_id, display_name, date_of_birth, state_of_residence
  - [ ] Fields: biological_sex, age_bracket, fitness_level, tier_code
  - [ ] Fields: height_inches, weight_pounds, goals (JSON)
  - [ ] Age bracket enum, fitness level enum
  - [ ] Tier code generation logic
- [ ] Create src/fittrack/models/connection.py
  - [ ] Fields: connection_id, user_id, provider, is_primary
  - [ ] Fields: access_token, refresh_token, token_expires_at
  - [ ] Fields: last_sync_at, sync_status, error_message
  - [ ] Provider enum: apple_health, google_fit, fitbit
  - [ ] Sync status enum: pending, syncing, success, error
- [ ] Create src/fittrack/models/activity.py
  - [ ] Fields: activity_id, user_id, connection_id, external_id
  - [ ] Fields: activity_type, start_time, end_time, duration_minutes
  - [ ] Fields: intensity, metrics (JSON), points_earned, processed
  - [ ] Activity type enum: steps, workout, active_minutes
  - [ ] Intensity enum: light, moderate, vigorous
- [ ] Create src/fittrack/models/transaction.py
  - [ ] Fields: transaction_id, user_id, transaction_type, amount, balance_after
  - [ ] Fields: reference_type, reference_id, description
  - [ ] Transaction type enum: earn, spend, adjust, expire
- [ ] Create src/fittrack/models/drawing.py
  - [ ] Fields: drawing_id, drawing_type, name, description, ticket_cost_points
  - [ ] Fields: drawing_time, ticket_sales_close, eligibility (JSON)
  - [ ] Fields: status, total_tickets, random_seed, created_by
  - [ ] Drawing type enum: daily, weekly, monthly, annual
  - [ ] Status enum: draft, scheduled, open, closed, completed, cancelled
- [ ] Create src/fittrack/models/ticket.py
  - [ ] Fields: ticket_id, drawing_id, user_id, ticket_number
  - [ ] Fields: purchase_transaction_id, is_winner, prize_id
- [ ] Create src/fittrack/models/prize.py
  - [ ] Fields: prize_id, drawing_id, sponsor_id, rank, name, description
  - [ ] Fields: value_usd, quantity, fulfillment_type, image_url
  - [ ] Fulfillment type enum: digital, physical
- [ ] Create src/fittrack/models/fulfillment.py
  - [ ] Fields: fulfillment_id, ticket_id, prize_id, user_id, status
  - [ ] Fields: shipping_address (JSON), tracking_number, carrier, notes
  - [ ] Fields: notified_at, address_confirmed_at, shipped_at, delivered_at, forfeit_at
  - [ ] Status enum: pending, winner_notified, address_confirmed, address_invalid, shipped, delivered, forfeited
- [ ] Create src/fittrack/models/sponsor.py
  - [ ] Fields: sponsor_id, name, contact_name, contact_email, contact_phone
  - [ ] Fields: website_url, logo_url, status, notes
  - [ ] Status enum: active, inactive

### 1.4 Database Migrations

- [ ] Create migrations/ directory structure
- [ ] Create migration runner script
- [ ] Create 001_initial_schema.sql
  - [ ] users table with constraints and indexes
  - [ ] profiles table with constraints and indexes
  - [ ] tracker_connections table with constraints
  - [ ] activities table with constraints and indexes
  - [ ] point_transactions table with indexes
  - [ ] drawings table with constraints and indexes
  - [ ] tickets table with indexes
  - [ ] prizes table
  - [ ] prize_fulfillments table with constraints
  - [ ] sponsors table
- [ ] Create 002_duality_views.sql
  - [ ] user_profile_dv (users + profiles)
  - [ ] user_connections_dv
  - [ ] user_activities_dv
  - [ ] drawing_details_dv (drawings + prizes + sponsor)
  - [ ] user_tickets_dv
  - [ ] fulfillment_details_dv
- [ ] Test migrations run cleanly
- [ ] Test migrations are idempotent

### 1.5 Repositories

- [ ] Create src/fittrack/repositories/base.py
  - [ ] Generic CRUD operations via Duality Views
  - [ ] Pagination support
  - [ ] Transaction management
- [ ] Create src/fittrack/repositories/user.py
  - [ ] find_by_email()
  - [ ] find_by_status()
  - [ ] update_point_balance() with optimistic locking
- [ ] Create src/fittrack/repositories/profile.py
  - [ ] find_by_user_id()
  - [ ] find_by_tier()
  - [ ] update_tier_code()
- [ ] Create src/fittrack/repositories/connection.py
  - [ ] find_by_user_and_provider()
  - [ ] find_due_for_sync()
  - [ ] Token encryption/decryption
- [ ] Create src/fittrack/repositories/activity.py
  - [ ] find_by_user_and_date_range()
  - [ ] find_unprocessed()
  - [ ] calculate_daily_totals()
- [ ] Create src/fittrack/repositories/transaction.py
  - [ ] find_by_user()
  - [ ] calculate_balance()
  - [ ] find_by_reference()
- [ ] Create src/fittrack/repositories/drawing.py
  - [ ] find_by_status()
  - [ ] find_by_type()
  - [ ] find_open_drawings()
  - [ ] find_due_for_execution()
- [ ] Create src/fittrack/repositories/ticket.py
  - [ ] find_by_drawing()
  - [ ] find_by_user()
  - [ ] count_by_drawing()
  - [ ] count_by_user_and_drawing()
- [ ] Create src/fittrack/repositories/prize.py
  - [ ] find_by_drawing()
- [ ] Create src/fittrack/repositories/fulfillment.py
  - [ ] find_by_status()
  - [ ] find_by_user()
  - [ ] find_overdue()
- [ ] Create src/fittrack/repositories/sponsor.py
  - [ ] find_active()

### 1.6 API Schemas

- [ ] Create src/fittrack/api/schemas/common.py
  - [ ] PaginationRequest, PaginationResponse
  - [ ] ErrorResponse (RFC 7807)
- [ ] Create src/fittrack/api/schemas/user.py
  - [ ] UserCreate, UserUpdate, UserResponse
- [ ] Create src/fittrack/api/schemas/profile.py
  - [ ] ProfileCreate, ProfileUpdate, ProfileResponse
- [ ] Create src/fittrack/api/schemas/connection.py
  - [ ] ConnectionCreate, ConnectionResponse
- [ ] Create src/fittrack/api/schemas/activity.py
  - [ ] ActivityCreate, ActivityResponse, ActivitySummary
- [ ] Create src/fittrack/api/schemas/transaction.py
  - [ ] TransactionCreate, TransactionResponse
- [ ] Create src/fittrack/api/schemas/drawing.py
  - [ ] DrawingCreate, DrawingUpdate, DrawingResponse
- [ ] Create src/fittrack/api/schemas/ticket.py
  - [ ] TicketCreate, TicketResponse
- [ ] Create src/fittrack/api/schemas/prize.py
  - [ ] PrizeCreate, PrizeUpdate, PrizeResponse
- [ ] Create src/fittrack/api/schemas/fulfillment.py
  - [ ] FulfillmentUpdate, FulfillmentResponse
- [ ] Create src/fittrack/api/schemas/sponsor.py
  - [ ] SponsorCreate, SponsorUpdate, SponsorResponse

### 1.7 API Routes

- [ ] Create src/fittrack/api/routes/users.py
  - [ ] GET /api/v1/users (list, paginated)
  - [ ] GET /api/v1/users/{id}
  - [ ] POST /api/v1/users
  - [ ] PUT /api/v1/users/{id}
  - [ ] DELETE /api/v1/users/{id}
- [ ] Create src/fittrack/api/routes/profiles.py
  - [ ] GET /api/v1/profiles
  - [ ] GET /api/v1/profiles/{id}
  - [ ] POST /api/v1/profiles
  - [ ] PUT /api/v1/profiles/{id}
- [ ] Create src/fittrack/api/routes/connections.py
  - [ ] GET /api/v1/connections
  - [ ] GET /api/v1/connections/{id}
  - [ ] POST /api/v1/connections
  - [ ] DELETE /api/v1/connections/{id}
- [ ] Create src/fittrack/api/routes/activities.py
  - [ ] GET /api/v1/activities (with date filters)
  - [ ] GET /api/v1/activities/{id}
  - [ ] POST /api/v1/activities
- [ ] Create src/fittrack/api/routes/transactions.py
  - [ ] GET /api/v1/transactions
  - [ ] GET /api/v1/transactions/{id}
  - [ ] POST /api/v1/transactions
- [ ] Create src/fittrack/api/routes/drawings.py
  - [ ] GET /api/v1/drawings (with status/type filters)
  - [ ] GET /api/v1/drawings/{id}
  - [ ] POST /api/v1/drawings
  - [ ] PUT /api/v1/drawings/{id}
  - [ ] DELETE /api/v1/drawings/{id}
- [ ] Create src/fittrack/api/routes/tickets.py
  - [ ] GET /api/v1/tickets
  - [ ] GET /api/v1/tickets/{id}
  - [ ] POST /api/v1/tickets
- [ ] Create src/fittrack/api/routes/prizes.py
  - [ ] GET /api/v1/prizes
  - [ ] GET /api/v1/prizes/{id}
  - [ ] POST /api/v1/prizes
  - [ ] PUT /api/v1/prizes/{id}
- [ ] Create src/fittrack/api/routes/fulfillments.py
  - [ ] GET /api/v1/fulfillments
  - [ ] GET /api/v1/fulfillments/{id}
  - [ ] PUT /api/v1/fulfillments/{id}
- [ ] Create src/fittrack/api/routes/sponsors.py
  - [ ] GET /api/v1/sponsors
  - [ ] GET /api/v1/sponsors/{id}
  - [ ] POST /api/v1/sponsors
  - [ ] PUT /api/v1/sponsors/{id}
  - [ ] DELETE /api/v1/sponsors/{id}
- [ ] Register all routers in main.py

### 1.8 Synthetic Data Generation

- [ ] Create tests/factories/base.py (factory base class)
- [ ] Create tests/factories/user.py
  - [ ] Generate realistic emails, passwords
  - [ ] Mix of statuses and roles
- [ ] Create tests/factories/profile.py
  - [ ] Generate realistic demographics
  - [ ] Cover all 31 tiers
  - [ ] Generate US addresses (eligible states)
- [ ] Create tests/factories/connection.py
  - [ ] Mix of providers
  - [ ] Realistic sync states
- [ ] Create tests/factories/activity.py
  - [ ] Generate 30 days of history per user
  - [ ] Realistic step counts, workout durations
  - [ ] Vary by user fitness level
- [ ] Create tests/factories/transaction.py
  - [ ] Generate earn/spend transactions
  - [ ] Maintain balance consistency
- [ ] Create tests/factories/drawing.py
  - [ ] Mix of types and statuses
  - [ ] Realistic prize configurations
- [ ] Create tests/factories/ticket.py
  - [ ] Distribute across drawings
  - [ ] Vary quantity by user
- [ ] Create tests/factories/prize.py
  - [ ] Realistic prize names and values
  - [ ] Mix of digital and physical
- [ ] Create tests/factories/fulfillment.py
  - [ ] Various statuses
  - [ ] Realistic addresses
- [ ] Create tests/factories/sponsor.py
  - [ ] Realistic company names
- [ ] Create scripts/seed_data.py
  - [ ] 3 admin users
  - [ ] 15 premium users
  - [ ] 50 regular users
  - [ ] Connections for 60 users
  - [ ] 500+ activities
  - [ ] 1000+ transactions
  - [ ] 5 sponsors
  - [ ] 15 drawings (various statuses)
  - [ ] 200+ tickets
  - [ ] 20 prizes
  - [ ] 10 fulfillments
- [ ] Test seed script runs successfully
- [ ] Verify data integrity after seeding

### 1.9 Test HTML Page

- [ ] Create devtools/test_page.html
  - [ ] Tabbed interface for each entity
  - [ ] Forms for CRUD operations
  - [ ] Response viewer with JSON formatting
  - [ ] Database seed/reset buttons
  - [ ] Environment indicator
  - [ ] JWT token input field
- [ ] Create devtools/styles.css
  - [ ] Clean, functional design
  - [ ] Responsive layout
  - [ ] Syntax highlighting for JSON
- [ ] Create devtools/app.js
  - [ ] API client functions
  - [ ] Form handling
  - [ ] Response display
  - [ ] Pagination controls
- [ ] Create src/fittrack/api/routes/devtools.py
  - [ ] Serve test page (dev only)
  - [ ] POST /devtools/seed - trigger seeding
  - [ ] POST /devtools/reset - trigger reset
  - [ ] Environment check (disable in prod)
- [ ] Test all CRUD operations via test page
- [ ] Test pagination via test page
- [ ] Test seed/reset via test page

### 1.10 Tests

- [ ] Create tests/conftest.py
  - [ ] Oracle container fixture
  - [ ] Redis container fixture
  - [ ] Database session fixture
  - [ ] API client fixture
- [ ] Create tests/unit/test_models.py
  - [ ] Test all model validations
  - [ ] Test tier code generation
  - [ ] Test enum values
- [ ] Create tests/unit/test_factories.py
  - [ ] Test each factory generates valid data
  - [ ] Test factories respect constraints
- [ ] Create tests/unit/test_config.py
  - [ ] Test config loading
  - [ ] Test validation
- [ ] Create tests/integration/test_repositories.py
  - [ ] Test CRUD for each repository
  - [ ] Test custom queries
  - [ ] Test pagination
  - [ ] Test error handling
- [ ] Create tests/integration/test_api_users.py
- [ ] Create tests/integration/test_api_profiles.py
- [ ] Create tests/integration/test_api_connections.py
- [ ] Create tests/integration/test_api_activities.py
- [ ] Create tests/integration/test_api_transactions.py
- [ ] Create tests/integration/test_api_drawings.py
- [ ] Create tests/integration/test_api_tickets.py
- [ ] Create tests/integration/test_api_prizes.py
- [ ] Create tests/integration/test_api_fulfillments.py
- [ ] Create tests/integration/test_api_sponsors.py
- [ ] Create tests/integration/test_health.py
- [ ] Achieve >90% repository coverage
- [ ] Achieve >85% API coverage

### 1.11 Documentation

- [ ] Create README.md
  - [ ] Project overview
  - [ ] Prerequisites
  - [ ] Quick start (<15 minutes)
  - [ ] Development workflow
  - [ ] Testing instructions
  - [ ] Troubleshooting
- [ ] Update CLAUDE.md with actual paths
- [ ] Create docs/ADR-001-database-choice.md
- [ ] Create docs/ADR-002-api-framework.md
- [ ] Create docs/ADR-003-project-structure.md

### 1.12 Checkpoint 1 Completion Criteria

- [ ] `make setup && make dev` works from fresh clone in <5 minutes
- [ ] `make db-seed` generates complete test data
- [ ] All CRUD endpoints functional and return correct responses
- [ ] Test page loads and all operations work
- [ ] All tests pass with required coverage
- [ ] CI pipeline passes
- [ ] Documentation complete

---

## Checkpoint 2: Authentication & Authorization

### 2.1 Security Utilities

- [ ] Create src/fittrack/core/security.py
  - [ ] Argon2id password hashing
  - [ ] Password verification
  - [ ] JWT token generation (RS256)
  - [ ] JWT token verification
  - [ ] Refresh token generation
  - [ ] Token blacklist management

### 2.2 Auth Service

- [ ] Create src/fittrack/services/auth.py
  - [ ] register() - create user, send verification
  - [ ] verify_email() - verify token, activate user
  - [ ] login() - authenticate, return tokens
  - [ ] refresh() - issue new access token
  - [ ] logout() - invalidate refresh token
  - [ ] forgot_password() - send reset email
  - [ ] reset_password() - verify token, update password
  - [ ] Account lockout logic

### 2.3 Email Service

- [ ] Create src/fittrack/services/email.py
  - [ ] Email verification template
  - [ ] Password reset template
  - [ ] Send email function (SMTP)
  - [ ] Mailpit integration for dev

### 2.4 Auth Dependencies

- [ ] Create src/fittrack/api/deps.py
  - [ ] get_current_user() - extract user from JWT
  - [ ] require_role(role) - enforce role requirement
  - [ ] optional_user() - user if authenticated, None otherwise

### 2.5 Auth Endpoints

- [ ] Create src/fittrack/api/routes/auth.py
  - [ ] POST /auth/register
  - [ ] POST /auth/verify-email
  - [ ] POST /auth/login
  - [ ] POST /auth/refresh
  - [ ] POST /auth/logout
  - [ ] POST /auth/forgot-password
  - [ ] POST /auth/reset-password
- [ ] Create src/fittrack/api/routes/me.py
  - [ ] GET /users/me
  - [ ] PUT /users/me
  - [ ] PUT /users/me/password
  - [ ] DELETE /users/me

### 2.6 Update Existing Routes

- [ ] Add authentication to all existing CRUD routes
- [ ] Implement admin-only access for admin routes
- [ ] Update test page with auth support

### 2.7 Tests

- [ ] Create tests/unit/test_security.py
- [ ] Create tests/unit/test_auth_service.py
- [ ] Create tests/integration/test_auth_api.py
- [ ] Create tests/integration/test_rbac.py

### 2.8 Checkpoint 2 Completion Criteria

- [ ] User registration with email verification works
- [ ] Login returns valid JWT tokens
- [ ] Token refresh extends session
- [ ] Password reset flow complete
- [ ] All routes properly protected
- [ ] Rate limiting on auth endpoints
- [ ] All tests pass

---

## Checkpoint 3: Fitness Tracker Integration

### 3.1 Terra API Client

- [ ] Create src/fittrack/services/terra.py
  - [ ] Initialize Terra client
  - [ ] Generate widget session
  - [ ] Get user data
  - [ ] Deauthenticate user
  - [ ] Handle rate limits

### 3.2 Connection Service

- [ ] Create src/fittrack/services/connection.py
  - [ ] initiate_connection() - start OAuth
  - [ ] complete_connection() - save tokens
  - [ ] disconnect() - revoke and remove
  - [ ] Token encryption/decryption

### 3.3 Sync Service

- [ ] Create src/fittrack/services/sync.py
  - [ ] fetch_activities() - get from Terra
  - [ ] normalize_activity() - convert to internal format
  - [ ] deduplicate() - skip existing
  - [ ] process_user_sync() - full sync flow

### 3.4 Background Worker

- [ ] Create src/fittrack/workers/sync_worker.py
  - [ ] Scheduled job (every 15 min)
  - [ ] Find users due for sync
  - [ ] Process each user
  - [ ] Handle errors gracefully

### 3.5 Webhook Handler

- [ ] Create src/fittrack/api/routes/webhooks.py
  - [ ] POST /webhooks/terra
  - [ ] Signature verification
  - [ ] Process activity webhook
  - [ ] Process deauth webhook

### 3.6 User-Facing Endpoints

- [ ] Update src/fittrack/api/routes/connections.py
  - [ ] GET /connections (user's connections)
  - [ ] POST /connections/{provider}/initiate
  - [ ] POST /connections/{provider}/callback
  - [ ] DELETE /connections/{provider}
  - [ ] POST /connections/{provider}/sync

### 3.7 Tests

- [ ] Create tests/unit/test_terra_service.py
- [ ] Create tests/unit/test_sync_service.py
- [ ] Create tests/integration/test_connections_api.py
- [ ] Create tests/integration/test_webhooks.py

### 3.8 Checkpoint 3 Completion Criteria

- [ ] OAuth flow works for all three providers
- [ ] Activities sync correctly
- [ ] Background sync runs on schedule
- [ ] Webhooks processed correctly
- [ ] Duplicate detection works
- [ ] All tests pass

---

## Checkpoint 4: Points & Activity System

### 4.1 Points Service

- [ ] Create src/fittrack/services/points.py
  - [ ] calculate_step_points()
  - [ ] calculate_active_minute_points()
  - [ ] calculate_workout_bonus()
  - [ ] calculate_daily_goal_bonus()
  - [ ] calculate_streak_bonus()
  - [ ] apply_daily_cap()
  - [ ] award_points() - create transaction, update balance

### 4.2 Activity Service

- [ ] Create src/fittrack/services/activity.py
  - [ ] process_activity() - calculate and award points
  - [ ] get_daily_summary()
  - [ ] get_weekly_summary()
  - [ ] get_monthly_summary()

### 4.3 Points Worker

- [ ] Create src/fittrack/workers/points_worker.py
  - [ ] Process unprocessed activities
  - [ ] Award points batch

### 4.4 API Endpoints

- [ ] Update src/fittrack/api/routes/activities.py
  - [ ] GET /activities (user's activities)
  - [ ] GET /activities/summary
- [ ] Create src/fittrack/api/routes/points.py
  - [ ] GET /points/balance
  - [ ] GET /points/transactions

### 4.5 Tests

- [ ] Create tests/unit/test_points_service.py
- [ ] Create tests/unit/test_activity_service.py
- [ ] Create tests/unit/test_points_properties.py (hypothesis)
- [ ] Create tests/integration/test_points_api.py

### 4.6 Checkpoint 4 Completion Criteria

- [ ] Points calculated correctly per rate table
- [ ] Daily caps enforced
- [ ] Bonuses awarded correctly
- [ ] Optimistic locking prevents race conditions
- [ ] Summaries accurate
- [ ] All tests pass

---

## Checkpoint 5: Competition System

### 5.1 Tier Service

- [ ] Create src/fittrack/services/tier.py
  - [ ] calculate_tier_code()
  - [ ] assign_user_to_tier()
  - [ ] get_tier_info()
  - [ ] handle_open_tier_opt_in()

### 5.2 Leaderboard Service

- [ ] Create src/fittrack/services/leaderboard.py
  - [ ] get_daily_rankings()
  - [ ] get_weekly_rankings()
  - [ ] get_monthly_rankings()
  - [ ] get_alltime_rankings()
  - [ ] get_user_rank()

### 5.3 Leaderboard Cache

- [ ] Create src/fittrack/services/leaderboard_cache.py
  - [ ] Cache rankings in Redis
  - [ ] TTL management
  - [ ] Invalidation on point changes

### 5.4 Leaderboard Worker

- [ ] Create src/fittrack/workers/leaderboard_worker.py
  - [ ] Refresh rankings periodically
  - [ ] Handle period resets

### 5.5 API Endpoints

- [ ] Create src/fittrack/api/routes/leaderboards.py
  - [ ] GET /leaderboards/daily
  - [ ] GET /leaderboards/weekly
  - [ ] GET /leaderboards/monthly
  - [ ] GET /leaderboards/alltime
- [ ] Create src/fittrack/api/routes/public_profiles.py
  - [ ] GET /users/{id}/public

### 5.6 Tests

- [ ] Create tests/unit/test_tier_service.py
- [ ] Create tests/unit/test_leaderboard_service.py
- [ ] Create tests/integration/test_leaderboard_cache.py
- [ ] Create tests/integration/test_leaderboards_api.py

### 5.7 Checkpoint 5 Completion Criteria

- [ ] Tier assignment works for all 31 tiers
- [ ] Leaderboards display correctly
- [ ] Rankings update within 15 minutes
- [ ] Caching reduces DB load
- [ ] All tests pass

---

## Checkpoint 6: Sweepstakes Engine

### 6.1 Drawing Service

- [ ] Create src/fittrack/services/drawing.py
  - [ ] get_open_drawings()
  - [ ] get_user_eligible_drawings()
  - [ ] check_eligibility()
  - [ ] close_drawing()

### 6.2 Ticket Service

- [ ] Create src/fittrack/services/ticket.py
  - [ ] purchase_tickets()
  - [ ] validate_purchase()
  - [ ] get_user_tickets()
  - [ ] assign_ticket_numbers()

### 6.3 Winner Service

- [ ] Create src/fittrack/services/winner.py
  - [ ] execute_drawing()
  - [ ] select_winners() - CSPRNG
  - [ ] record_results()
  - [ ] notify_winners()

### 6.4 Drawing Worker

- [ ] Create src/fittrack/workers/drawing_worker.py
  - [ ] Check for drawings to execute
  - [ ] Execute at scheduled time
  - [ ] Handle failures gracefully

### 6.5 API Endpoints

- [ ] Update src/fittrack/api/routes/drawings.py
  - [ ] GET /drawings (user-facing, with eligibility)
  - [ ] GET /drawings/{id}
  - [ ] POST /drawings/{id}/tickets
  - [ ] GET /drawings/{id}/results
  - [ ] GET /drawings/my-entries
  - [ ] GET /drawings/my-wins

### 6.6 Tests

- [ ] Create tests/unit/test_drawing_service.py
- [ ] Create tests/unit/test_ticket_service.py
- [ ] Create tests/unit/test_winner_service.py
- [ ] Create tests/integration/test_drawings_api.py
- [ ] Create tests/integration/test_drawing_execution.py

### 6.7 Checkpoint 6 Completion Criteria

- [ ] Ticket purchases work correctly
- [ ] Points deducted atomically
- [ ] Drawing execution uses CSPRNG
- [ ] Audit trail complete
- [ ] Winners notified
- [ ] Results published
- [ ] All tests pass

---

## Checkpoint 7: Admin Dashboard & Fulfillment

### 7.1 Admin Services

- [ ] Create src/fittrack/services/admin/drawing.py
- [ ] Create src/fittrack/services/admin/sponsor.py
- [ ] Create src/fittrack/services/admin/user.py
- [ ] Create src/fittrack/services/fulfillment.py

### 7.2 Admin API

- [ ] Create src/fittrack/api/routes/admin/drawings.py
- [ ] Create src/fittrack/api/routes/admin/sponsors.py
- [ ] Create src/fittrack/api/routes/admin/fulfillments.py
- [ ] Create src/fittrack/api/routes/admin/users.py
- [ ] Create src/fittrack/api/routes/admin/analytics.py

### 7.3 Admin UI

- [ ] Create frontend/src/admin/App.jsx
- [ ] Create admin dashboard page
- [ ] Create drawings management page
- [ ] Create sponsors management page
- [ ] Create fulfillments management page
- [ ] Create users management page
- [ ] Create analytics page

### 7.4 Tests

- [ ] Create tests/unit/test_admin_services.py
- [ ] Create tests/unit/test_fulfillment_service.py
- [ ] Create tests/integration/test_admin_api.py

### 7.5 Checkpoint 7 Completion Criteria

- [ ] Admin can manage drawings
- [ ] Admin can manage sponsors
- [ ] Fulfillment workflow complete
- [ ] User moderation works
- [ ] Analytics dashboard functional
- [ ] All tests pass

---

## Checkpoint 8: Production Readiness

### 8.1 Infrastructure

- [ ] Create infrastructure/terraform/\*.tf
- [ ] Create infrastructure/helm/fittrack/\*
- [ ] Create Dockerfile.prod
- [ ] Create infrastructure/nginx/\*.conf

### 8.2 Observability

- [ ] Create src/fittrack/core/metrics.py
- [ ] Create src/fittrack/core/logging.py
- [ ] Update health endpoints
- [ ] Create src/fittrack/core/rate_limit.py
- [ ] Add security headers

### 8.3 Documentation

- [ ] Create docs/DEPLOYMENT.md
- [ ] Create docs/RUNBOOK.md
- [ ] Create docs/SECURITY_CHECKLIST.md

### 8.4 Testing

- [ ] Create load tests with k6
- [ ] Run OWASP ZAP scan
- [ ] Run dependency audit

### 8.5 Checkpoint 8 Completion Criteria

- [ ] Terraform provisions OCI resources
- [ ] Helm deploys to OKE
- [ ] Monitoring operational
- [ ] Load test passes
- [ ] Security scan passes
- [ ] Documentation complete

---

## Progress Summary

| Checkpoint               | Status      | Completion % |
| ------------------------ | ----------- | ------------ |
| CP1: Foundation          | Not Started | 0%           |
| CP2: Authentication      | Not Started | 0%           |
| CP3: Fitness Integration | Not Started | 0%           |
| CP4: Points System       | Not Started | 0%           |
| CP5: Competition         | Not Started | 0%           |
| CP6: Sweepstakes         | Not Started | 0%           |
| CP7: Admin & Fulfillment | Not Started | 0%           |
| CP8: Production          | Not Started | 0%           |

**Last Updated**: [Date]
**Current Focus**: [Checkpoint #]
