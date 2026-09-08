# FitTrack Product Requirements Document

**Version:** 1.0 | **Status:** Draft - For Development Review
**Date:** January 2026
**Target Platform:** Oracle Cloud Infrastructure (OCI)
**Target Market:** United States (18+, sweepstakes-compliant states)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [User Personas](#2-user-personas)
3. [User Stories](#3-user-stories)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [System Architecture](#6-system-architecture)
7. [Data Model](#7-data-model)
8. [API Design](#8-api-design)
9. [UI/UX Wireframe Descriptions](#9-uiux-wireframe-descriptions)
10. [Security Considerations](#10-security-considerations)
11. [Testing Strategy](#11-testing-strategy)
12. [Deployment & DevOps](#12-deployment--devops)
13. [Success Metrics](#13-success-metrics)
14. [Risks & Mitigations](#14-risks--mitigations)
15. [Milestones & Phases](#15-milestones--phases)
16. [Open Questions & Assumptions](#16-open-questions--assumptions)

---

## 1. Executive Summary

### 1.1 Problem Statement

Fitness motivation remains one of the most significant barriers to achieving health goals. Studies consistently show that while most people set fitness intentions, fewer than 20% maintain their programs beyond the first three months. The primary causes are lack of accountability, absence of tangible rewards for effort, and isolation from supportive communities.

### 1.2 Solution

FitTrack transforms fitness activity into a competitive, rewarding experience. Users earn points based on their tracked physical activities, then spend those points on sweepstakes tickets for daily, weekly, monthly, and annual prize drawings. The gamification layer provides immediate gratification for effort, while tiered competition brackets ensure fair competition among users with similar demographics and fitness baselines.

### 1.3 Value Proposition

| Stakeholder  | Value                                                                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Users**    | Tangible rewards for fitness effort, fair competition within peer groups, community engagement, access to professional fitness guidance (premium) |
| **Sponsors** | Access to highly engaged, health-conscious demographic with measurable brand exposure through prize sponsorship                                   |
| **Platform** | Sustainable revenue through premium subscriptions and sponsor partnerships without relying on intrusive advertising                               |

### 1.4 MVP Scope Summary

| Dimension    | MVP Scope                                               |
| ------------ | ------------------------------------------------------- |
| Geography    | United States only, sweepstakes-compliant states        |
| User Age     | 18+ only                                                |
| Platforms    | Responsive web application (mobile apps in v1.1+)       |
| Integrations | Apple Health, Google Fit, Fitbit                        |
| Data Sync    | Batch processing (15-minute intervals)                  |
| Monetization | Premium subscriptions only (ads deferred)               |
| Prize Admin  | Manual admin management (sponsor self-service deferred) |

---

## 2. User Personas

### 2.1 Primary Persona: The Motivated Beginner

| Attribute         | Detail                                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Name**          | Sarah Chen                                                                                                                                  |
| **Age**           | 32                                                                                                                                          |
| **Occupation**    | Marketing Manager                                                                                                                           |
| **Fitness Level** | Beginner to Intermediate                                                                                                                    |
| **Goals**         | Lose 20 pounds, establish consistent exercise routine, find accountability                                                                  |
| **Pain Points**   | Has tried and abandoned multiple fitness apps, lacks motivation without external rewards, feels intimidated by hardcore fitness communities |
| **Tech Comfort**  | High - uses smartphone apps daily, comfortable with wearables                                                                               |
| **Devices**       | iPhone, Apple Watch                                                                                                                         |

**Why FitTrack:** The prize incentive provides tangible motivation she lacks intrinsically. Tiered competition means she competes against others at her level, not marathon runners.

### 2.2 Secondary Persona: The Competitive Athlete

| Attribute         | Detail                                                                                                                 |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Name**          | Marcus Johnson                                                                                                         |
| **Age**           | 28                                                                                                                     |
| **Occupation**    | Software Developer                                                                                                     |
| **Fitness Level** | Advanced                                                                                                               |
| **Goals**         | Maintain peak fitness, find new competitive outlets, connect with like-minded community                                |
| **Pain Points**   | Traditional fitness apps feel stale, wants recognition for effort, seeks additional motivation beyond personal records |
| **Tech Comfort**  | Very High - early adopter                                                                                              |
| **Devices**       | Android, Fitbit                                                                                                        |

**Why FitTrack:** Premium tier offers access to professional coaching and exclusive prize pools. Leaderboard competition satisfies competitive drive.

### 2.3 Tertiary Persona: The Health-Conscious Professional

| Attribute         | Detail                                                                                |
| ----------------- | ------------------------------------------------------------------------------------- |
| **Name**          | Linda Rodriguez                                                                       |
| **Age**           | 45                                                                                    |
| **Occupation**    | Financial Analyst                                                                     |
| **Fitness Level** | Moderate                                                                              |
| **Goals**         | Maintain health as she ages, prevent chronic conditions, balanced approach to fitness |
| **Pain Points**   | Time-constrained, needs flexible options, wants age-appropriate competition           |
| **Tech Comfort**  | Moderate                                                                              |
| **Devices**       | iPhone, basic Fitbit                                                                  |

**Why FitTrack:** Age-bracketed competition is fair and motivating. Premium access to nutritionists aligns with holistic health goals.

---

## 3. User Stories

### 3.1 User Registration & Onboarding

| ID     | User Story                                                                                                                                 | Priority  | Acceptance Criteria                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------ | --------- | ---------------------------------------------------------------------------------------- |
| US-001 | As a new user, I want to register using my email address so that I can create my FitTrack account.                                         | Must Have | Email verification sent within 60 seconds; duplicate emails rejected with friendly error |
| US-002 | As a new user, I want to verify my age (18+) during registration so that I can participate in sweepstakes legally.                         | Must Have | System rejects DOB indicating age < 18; clear error messaging                            |
| US-003 | As a new user, I want to confirm my state of residence so the system can determine my eligibility for sweepstakes.                         | Must Have | Ineligible states display appropriate messaging and alternative options                  |
| US-004 | As a new user, I want to complete a fitness profile (age, sex, current fitness level) so I can be placed in appropriate competition tiers. | Must Have | Profile completion required before accessing main features                               |
| US-005 | As a new user, I want to connect my fitness tracker (Apple Health, Google Fit, or Fitbit) so my activities can be automatically tracked.   | Must Have | OAuth flow completes successfully; initial data sync within 5 minutes                    |
| US-006 | As a user, I want to review and accept the terms of service and sweepstakes rules so I understand my rights and obligations.               | Must Have | ToS acceptance timestamp recorded; rules accessible at any time                          |

### 3.2 Activity Tracking & Points

| ID     | User Story                                                                                                                             | Priority    | Acceptance Criteria                                                             |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------- |
| US-010 | As a user, I want my fitness activities to be automatically synced from my connected tracker so I don't have to manually log workouts. | Must Have   | Activities appear within 15 minutes of completion                               |
| US-011 | As a user, I want to earn points based on my activities (steps, workouts, active minutes) so I can accumulate rewards.                 | Must Have   | Points calculated correctly per rate table; balance updates immediately         |
| US-012 | As a user, I want to see my current point balance prominently displayed so I know how many tickets I can purchase.                     | Must Have   | Balance visible on all primary screens; updates in real-time after transactions |
| US-013 | As a user, I want to view my point earning history so I can understand how my activities translate to rewards.                         | Should Have | History shows date, activity, points earned; filterable by date range           |
| US-014 | As a user, I want points to be awarded at different rates for different activities so that diverse exercise is rewarded fairly.        | Must Have   | Rate table implemented correctly; vigorous activity earns more than light       |

### 3.3 Competition & Leaderboards

| ID     | User Story                                                                                                                 | Priority    | Acceptance Criteria                                                  |
| ------ | -------------------------------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------- |
| US-020 | As a user, I want to be automatically placed in a competition tier based on my profile so I compete against similar users. | Must Have   | Tier assignment matches profile attributes; user can view their tier |
| US-021 | As a user, I want to view my ranking within my competition tier so I know where I stand.                                   | Must Have   | Rank displayed prominently; updates within 15 minutes of activity    |
| US-022 | As a user, I want to see daily, weekly, and monthly leaderboards so I can track competition across different timeframes.   | Must Have   | All three leaderboard types functional; correct reset timing         |
| US-023 | As a user, I want to view other users' public profiles (username, tier, rank) so I can see my competition.                 | Should Have | Profile shows only public info; privacy respected                    |

### 3.4 Sweepstakes & Prizes

| ID     | User Story                                                                                                                  | Priority    | Acceptance Criteria                                                      |
| ------ | --------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------ |
| US-030 | As a user, I want to view available prize drawings (daily, weekly, monthly, annual) so I can decide how to spend my points. | Must Have   | All active drawings visible; prize details, odds, and closing time clear |
| US-031 | As a user, I want to purchase sweepstakes tickets using my points so I can enter prize drawings.                            | Must Have   | Transaction completes; points deducted; ticket count confirmed           |
| US-032 | As a user, I want to buy multiple tickets for a single drawing so I can increase my chances of winning.                     | Must Have   | No limit on ticket quantity (points permitting); bulk purchase supported |
| US-033 | As a user, I want to receive notification when I win a prize so I can claim my reward.                                      | Must Have   | Email and in-app notification within 5 minutes of drawing                |
| US-034 | As a user, I want to provide shipping information for physical prizes so they can be delivered.                             | Must Have   | Address validation; confirmation before submission                       |
| US-035 | As a user, I want to see past drawing results so I can verify the system is fair and see winners.                           | Should Have | Results include winner usernames, ticket counts, total entries           |

### 3.5 Premium Features (v1.1)

| ID     | User Story                                                                                                       | Priority           | Acceptance Criteria                              |
| ------ | ---------------------------------------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------ |
| US-040 | As a free user, I want to upgrade to premium so I can access exclusive prize drawings and professional services. | Should Have (v1.1) | Payment flow completes; premium status immediate |
| US-041 | As a premium user, I want to access premium-only prize pools with higher-value rewards.                          | Should Have (v1.1) | Premium drawings visible only to premium users   |
| US-042 | As a premium user, I want to book sessions with fitness professionals through the platform.                      | Should Have (v1.1) | Booking system functional; calendar integration  |

### 3.6 Administration

| ID     | User Story                                                                                                                       | Priority    | Acceptance Criteria                                               |
| ------ | -------------------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------- |
| US-050 | As an admin, I want to create and configure prize drawings (type, date, ticket cost, prizes) so users have opportunities to win. | Must Have   | Drawing creation workflow complete; validation of required fields |
| US-051 | As an admin, I want to register sponsors and their prize offerings so drawings can be populated with rewards.                    | Must Have   | Sponsor CRUD operations; prize inventory management               |
| US-052 | As an admin, I want to execute drawings (select winners randomly) and record results for audit purposes.                         | Must Have   | CSPRNG selection; complete audit trail; results immutable         |
| US-053 | As an admin, I want to manage prize fulfillment workflow so winners receive their prizes.                                        | Must Have   | Status tracking: pending → shipped → delivered                    |
| US-054 | As an admin, I want to view platform analytics so I can monitor business health.                                                 | Should Have | Dashboard with key metrics; export capability                     |
| US-055 | As an admin, I want to suspend or ban users who violate terms of service.                                                        | Must Have   | Account status management; appeal workflow                        |

---

## 4. Functional Requirements

### 4.1 User Management

#### 4.1.1 Registration

The system shall support email-based registration with email verification. Users must provide:

- Email address (unique, verified)
- Password (minimum 12 characters, complexity: uppercase, lowercase, number, special character)
- Date of birth (must calculate to 18+ years)
- State of residence (validated against eligible states list)
- Acceptance of Terms of Service and Sweepstakes Rules

> **[DECISION NEEDED]** Should we support social login (Google, Apple) in MVP, or defer to v1.1?

#### 4.1.2 Eligible States

The following states have restrictions or requirements that exclude them from MVP:

| Excluded State | Reason                                             |
| -------------- | -------------------------------------------------- |
| New York       | Registration/bonding requirements                  |
| Florida        | Registration requirements for certain prize values |
| Rhode Island   | Registration requirements                          |

> **[ASSUMPTION]** Legal review will finalize the complete list of eligible states before launch.

#### 4.1.3 Fitness Profile

Users must complete a fitness profile to be placed in competition tiers:

| Field          | Type         | Options                                                                | Required |
| -------------- | ------------ | ---------------------------------------------------------------------- | -------- |
| Age Range      | Select       | 18-29, 30-39, 40-49, 50-59, 60+                                        | Yes      |
| Biological Sex | Select       | Male, Female                                                           | Yes      |
| Fitness Level  | Select       | Beginner, Intermediate, Advanced                                       | Yes      |
| Primary Goal   | Multi-select | Weight Loss, Muscle Building, Endurance, General Health, Stress Relief | No       |
| Height         | Number       | Inches                                                                 | No       |
| Weight         | Number       | Pounds                                                                 | No       |

> **[ASSUMPTION]** Biological sex is used solely for creating fair competition tiers based on physiological differences in baseline fitness metrics. Users can choose any display name they prefer.

#### 4.1.4 Competition Tier Structure

Users are placed into competition tiers based on a matrix of attributes:

| Dimension     | Tiers                            |
| ------------- | -------------------------------- |
| Age Bracket   | 18-29, 30-39, 40-49, 50-59, 60+  |
| Sex Category  | Male, Female                     |
| Fitness Level | Beginner, Intermediate, Advanced |

This creates **30 possible tier combinations** (5 × 2 × 3). Users compete on leaderboards within their specific tier combination.

**Tier Examples:**

- `M-18-29-BEG` = Male, 18-29, Beginner
- `F-40-49-ADV` = Female, 40-49, Advanced

> **[DECISION NEEDED]** Should users be able to opt into an "Open" tier that includes all users regardless of demographics?

### 4.2 Fitness Tracker Integration

#### 4.2.1 Supported Platforms (MVP)

| Platform     | Integration Method                                 | Data Available                                     | Rate Limits            |
| ------------ | -------------------------------------------------- | -------------------------------------------------- | ---------------------- |
| Apple Health | HealthKit API (requires iOS app or web workaround) | Steps, workouts, active calories, heart rate       | N/A (on-device)        |
| Google Fit   | REST API (OAuth 2.0)                               | Steps, workouts, active minutes, calories          | 86,400 requests/day    |
| Fitbit       | Web API (OAuth 2.0)                                | Steps, workouts, active minutes, sleep, heart rate | 150 requests/hour/user |

> **[DECISION NEEDED]** Apple Health requires a native iOS app for direct integration. Options: (a) Build minimal iOS app for MVP, (b) Use third-party aggregator service, (c) Defer Apple Health to v1.1. Recommend option (b) with service like Terra API.

#### 4.2.2 Data Normalization

All fitness data is normalized to a common internal format:

```json
{
  "activity_id": "uuid",
  "user_id": "uuid",
  "source": "fitbit|google_fit|apple_health",
  "activity_type": "steps|workout|active_minutes",
  "start_time": "ISO8601",
  "end_time": "ISO8601",
  "duration_minutes": 30,
  "intensity": "light|moderate|vigorous",
  "metrics": {
    "steps": 5000,
    "calories": 250,
    "heart_rate_avg": 120
  },
  "points_earned": 75,
  "synced_at": "ISO8601"
}
```

#### 4.2.3 Data Synchronization

MVP uses batch synchronization with a **15-minute polling interval**:

1. Scheduled job runs every 15 minutes
2. Retrieves list of users due for sync (`last_sync + 15 min < now`)
3. For each user, calls appropriate fitness API with stored OAuth tokens
4. Normalizes activity data to internal format
5. Deduplicates activities (same type + overlapping time window)
6. Calculates and awards points based on activity type and intensity
7. Updates user point balance and activity log
8. Updates leaderboard rankings

**Duplicate Detection:** When a user has multiple trackers connected, the system uses the following priority for overlapping activities:

1. User-designated primary tracker
2. Most detailed data (more metrics available)
3. First received

### 4.3 Points System

#### 4.3.1 Point Earning Rates

| Activity Type             | Unit                        | Points    | Notes                         |
| ------------------------- | --------------------------- | --------- | ----------------------------- |
| Steps                     | Per 1,000 steps             | 10        | Capped at 20,000 steps/day    |
| Active Minutes (Light)    | Per minute                  | 1         | Heart rate < 50% max          |
| Active Minutes (Moderate) | Per minute                  | 2         | Heart rate 50-70% max         |
| Active Minutes (Vigorous) | Per minute                  | 3         | Heart rate > 70% max          |
| Workout Completed         | Per workout (≥20 min)       | 50 bonus  | Max 3 workouts/day            |
| Daily Step Goal           | Per achievement (10K steps) | 100 bonus | Once per day                  |
| Weekly Streak             | 7 consecutive active days   | 250 bonus | "Active" = ≥30 active minutes |

**Daily Maximum:** 1,000 points per day to prevent extreme outliers and gaming.

> **[DECISION NEEDED]** Should point earning rates be adjusted based on user tier to normalize for physiological differences?

#### 4.3.2 Point Balance Rules

- Users maintain a single point balance
- Points do not expire
- Points cannot be transferred between users
- Points cannot be converted to cash value
- Point balance displayed on all primary screens

#### 4.3.3 Anti-Gaming Measures

| Measure             | Implementation                                              |
| ------------------- | ----------------------------------------------------------- |
| Daily cap           | 1,000 points maximum per day                                |
| Workout cap         | Maximum 3 workout bonuses per day                           |
| Anomaly detection   | Flag accounts with >3 standard deviations from tier average |
| Device verification | Track device IDs; flag multiple accounts per device         |
| Manual review queue | Suspicious accounts queued for admin review before payouts  |

### 4.4 Sweepstakes Engine

#### 4.4.1 Drawing Types

| Type    | Frequency         | Drawing Time | Ticket Cost   | Typical Prize Value |
| ------- | ----------------- | ------------ | ------------- | ------------------- |
| Daily   | Every day         | 9:00 PM EST  | 100 points    | $25-$50             |
| Weekly  | Every Sunday      | 9:00 PM EST  | 500 points    | $100-$500           |
| Monthly | Last day of month | 9:00 PM EST  | 2,000 points  | $500-$2,000         |
| Annual  | December 31       | 9:00 PM EST  | 10,000 points | $5,000+             |

#### 4.4.2 Drawing Configuration (Admin)

```json
{
  "drawing_id": "uuid",
  "type": "daily|weekly|monthly|annual",
  "name": "Daily Drawing - January 15, 2026",
  "description": "Win a $50 Amazon Gift Card!",
  "ticket_cost_points": 100,
  "drawing_time": "2026-01-15T21:00:00-05:00",
  "ticket_sales_close": "2026-01-15T20:55:00-05:00",
  "prizes": [
    {
      "prize_id": "uuid",
      "rank": 1,
      "name": "$50 Amazon Gift Card",
      "description": "Digital gift card delivered via email",
      "value_usd": 50.0,
      "quantity": 1,
      "sponsor_id": "uuid",
      "fulfillment_type": "digital|physical"
    }
  ],
  "eligibility": {
    "user_type": "all|premium",
    "min_account_age_days": 7
  },
  "status": "draft|scheduled|open|closed|completed|cancelled"
}
```

#### 4.4.3 Drawing Execution

1. **T-5 minutes:** Ticket sales close for the drawing
2. **T-0:** Drawing execution begins
   - System creates immutable snapshot of all tickets
   - Assigns sequential ticket numbers
   - Uses CSPRNG (OCI Vault random number generation) to select winning number(s)
   - Records seed value and algorithm for audit
3. **T+1 minute:** Winners notified via email and in-app push
4. **T+5 minutes:** Results published to all users
5. **Ongoing:** Prize fulfillment workflow initiated

#### 4.4.4 Prize Fulfillment Workflow

```
[PENDING] → [WINNER_NOTIFIED] → [ADDRESS_CONFIRMED] → [SHIPPED] → [DELIVERED]
                                        ↓
                                [ADDRESS_INVALID] → [ADDRESS_CONFIRMED]
```

| Status            | Trigger                        | Actions                           |
| ----------------- | ------------------------------ | --------------------------------- |
| PENDING           | Drawing completed              | Create fulfillment record         |
| WINNER_NOTIFIED   | Auto                           | Send email + in-app notification  |
| ADDRESS_CONFIRMED | User confirms/provides address | Validate address; notify admin    |
| SHIPPED           | Admin enters tracking          | Send tracking to user             |
| DELIVERED         | Admin confirms or carrier API  | Close fulfillment; update records |

**Timeouts:**

- Address confirmation: 7 days (then forfeit warning)
- Final forfeit: 14 days after drawing
- Forfeited prizes: Re-drawn or returned to sponsor per agreement

### 4.5 Leaderboards & Rankings

#### 4.5.1 Leaderboard Types

| Type     | Reset Timing           | Scope                    |
| -------- | ---------------------- | ------------------------ |
| Daily    | Midnight EST           | Points earned today      |
| Weekly   | Monday 00:00 EST       | Points earned this week  |
| Monthly  | 1st of month 00:00 EST | Points earned this month |
| All-Time | Never                  | Cumulative points earned |

#### 4.5.2 Ranking Algorithm

Rankings are calculated based on **total points earned** (not current balance) within the period. Ties are broken by:

1. Earlier achievement of the point total
2. More active days in period
3. User ID (deterministic fallback)

#### 4.5.3 Leaderboard Display

- Users see their rank prominently
- Top 100 users in tier displayed
- Users can see ±10 positions around their rank
- Tier totals shown (e.g., "Rank 45 of 1,247 in your tier")

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric                     | Target (MVP)      | Target (Scale)         |
| -------------------------- | ----------------- | ---------------------- |
| Page Load Time             | < 2 seconds (p95) | < 1 second (p95)       |
| API Response Time          | < 500ms (p95)     | < 200ms (p95)          |
| Leaderboard Update Latency | ≤ 15 minutes      | ≤ 1 minute (real-time) |
| Activity Sync Latency      | ≤ 15 minutes      | ≤ 5 minutes            |
| Drawing Execution Time     | < 30 seconds      | < 10 seconds           |
| Concurrent Users           | 5,000             | 100,000+               |

### 5.2 Scalability

| Component | MVP Architecture               | Scale Architecture                  |
| --------- | ------------------------------ | ----------------------------------- |
| Web Tier  | 2 OCI Compute instances + LB   | OKE (Kubernetes) auto-scaling       |
| API Tier  | 2 OCI Compute instances        | OKE with HPA                        |
| Database  | Oracle Autonomous DB (2 OCPU)  | Oracle Autonomous DB (auto-scaling) |
| Cache     | OCI Cache with Redis (2 nodes) | OCI Cache cluster (6+ nodes)        |
| Queue     | OCI Queue (single queue)       | OCI Streaming (partitioned)         |

### 5.3 Availability

| Metric                         | Target                                        |
| ------------------------------ | --------------------------------------------- |
| Uptime SLA                     | 99.9% (8.76 hours downtime/year)              |
| RTO (Recovery Time Objective)  | 1 hour                                        |
| RPO (Recovery Point Objective) | 15 minutes                                    |
| Maintenance Windows            | Sundays 2-4 AM EST (announced 72 hours ahead) |

### 5.4 Security

See [Section 10: Security Considerations](#10-security-considerations) for detailed requirements.

### 5.5 Compliance

| Requirement      | Scope                     | Implementation                             |
| ---------------- | ------------------------- | ------------------------------------------ |
| CCPA             | California users          | Privacy controls, data export, deletion    |
| PCI-DSS          | Payment processing (v1.1) | Use compliant payment processor (Stripe)   |
| Sweepstakes Laws | All operating states      | Legal review; state-specific rules display |
| Age Verification | All users                 | DOB collection; 18+ requirement            |

---

## 6. System Architecture

### 6.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ORACLE CLOUD INFRASTRUCTURE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────────────────────────────────────────┐   │
│  │   OCI DNS   │     │              OCI WAF + Load Balancer            │   │
│  └─────────────┘     └─────────────────────────────────────────────────┘   │
│                                          │                                  │
│         ┌────────────────────────────────┼────────────────────────────┐    │
│         │                                │                            │    │
│         ▼                                ▼                            ▼    │
│  ┌─────────────┐              ┌─────────────────┐            ┌───────────┐ │
│  │  Web Tier   │              │    API Tier     │            │  Admin UI │ │
│  │  (React)    │              │(Python/FastAPI) │            │  (React)  │ │
│  │  2 instances│              │   2 instances   │            │ 1 instance│ │
│  └─────────────┘              └─────────────────┘            └───────────┘ │
│                                          │                                  │
│         ┌────────────────────────────────┼────────────────────────────┐    │
│         │                                │                            │    │
│         ▼                                ▼                            ▼    │
│  ┌─────────────┐              ┌─────────────────┐            ┌───────────┐ │
│  │ OCI Cache   │              │  Oracle Auton.  │            │ OCI Queue │ │
│  │  (Redis)    │              │   Database      │            │           │ │
│  │  Sessions   │              │  (JSON + Rel.)  │            │  Async    │ │
│  │  Rankings   │              │                 │            │  Jobs     │ │
│  └─────────────┘              └─────────────────┘            └───────────┘ │
│                                          │                                  │
│                               ┌──────────┴──────────┐                      │
│                               │                     │                      │
│                               ▼                     ▼                      │
│                        ┌─────────────┐       ┌─────────────┐               │
│                        │ OCI Vault   │       │OCI Object   │               │
│                        │ (Secrets,   │       │Storage      │               │
│                        │  CSPRNG)    │       │(Assets)     │               │
│                        └─────────────┘       └─────────────┘               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        BACKGROUND SERVICES                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │   │
│  │  │ Sync Worker  │  │ Points Calc  │  │ Drawing Exec │  │Leaderboard│ │   │
│  │  │ (15 min)     │  │   Worker     │  │   Worker     │  │  Worker   │ │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
          ▼                            ▼                            ▼
   ┌─────────────┐            ┌─────────────────┐           ┌─────────────┐
   │ Apple Health│            │   Google Fit    │           │   Fitbit    │
   │     API     │            │      API        │           │    API      │
   └─────────────┘            └─────────────────┘           └─────────────┘
```

### 6.2 Component Descriptions

| Component          | Technology                      | Purpose                                    |
| ------------------ | ------------------------------- | ------------------------------------------ |
| **Web Tier**       | React 18 + Vite                 | Responsive SPA for end users               |
| **Admin UI**       | React 18 + Vite                 | Administrative dashboard                   |
| **API Tier**       | Python 3.12 + FastAPI           | RESTful API services                       |
| **Database**       | Oracle Autonomous JSON Database | Primary data store with JSON Duality Views |
| **Cache**          | OCI Cache (Redis)               | Session management, leaderboard caching    |
| **Queue**          | OCI Queue                       | Asynchronous job processing                |
| **Object Storage** | OCI Object Storage              | Static assets, user uploads                |
| **Vault**          | OCI Vault                       | Secrets management, CSPRNG for drawings    |
| **WAF**            | OCI WAF                         | DDoS protection, bot mitigation            |

### 6.3 Technology Choices Rationale

| Choice                        | Rationale                                                                                                                                               |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Oracle Autonomous JSON DB** | JSON Duality Views enable document-style development with relational integrity; auto-scaling; managed service reduces ops burden                        |
| **Python + FastAPI**          | High-performance async framework; native type hints with Pydantic validation; automatic OpenAPI documentation; excellent python-oracledb driver support |
| **React**                     | Component-based architecture; strong mobile-responsive capabilities; rich ecosystem                                                                     |
| **OCI-native services**       | Integrated IAM, networking, monitoring; single-vendor support; cost optimization                                                                        |

---

## 7. Data Model

### 7.1 Entity Relationship Overview

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    USERS     │───────│   PROFILES   │───────│    TIERS     │
└──────────────┘       └──────────────┘       └──────────────┘
       │                      │
       │                      │
       ▼                      ▼
┌──────────────┐       ┌──────────────┐
│  CONNECTIONS │       │  ACTIVITIES  │
│(OAuth tokens)│       │              │
└──────────────┘       └──────────────┘
       │                      │
       │                      ▼
       │               ┌──────────────┐       ┌──────────────┐
       │               │   POINTS     │───────│   TICKETS    │
       │               │TRANSACTIONS  │       │              │
       │               └──────────────┘       └──────────────┘
       │                                             │
       │                                             ▼
       │                                      ┌──────────────┐
       └──────────────────────────────────────│   DRAWINGS   │
                                              └──────────────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │    PRIZES    │
                                              └──────────────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │   SPONSORS   │
                                              └──────────────┘
```

### 7.2 Core Entities

#### 7.2.1 Users

```sql
CREATE TABLE users (
    user_id             RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    email               VARCHAR2(255) NOT NULL UNIQUE,
    password_hash       VARCHAR2(255) NOT NULL,
    email_verified      NUMBER(1) DEFAULT 0,
    email_verified_at   TIMESTAMP,
    status              VARCHAR2(20) DEFAULT 'active'
                        CHECK (status IN ('pending','active','suspended','banned')),
    role                VARCHAR2(20) DEFAULT 'user'
                        CHECK (role IN ('user','premium','admin')),
    premium_expires_at  TIMESTAMP,
    point_balance       NUMBER(10) DEFAULT 0,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    last_login_at       TIMESTAMP,

    CONSTRAINT chk_point_balance CHECK (point_balance >= 0)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
```

#### 7.2.2 Profiles

```sql
CREATE TABLE profiles (
    profile_id          RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    user_id             RAW(16) NOT NULL REFERENCES users(user_id),
    display_name        VARCHAR2(50) NOT NULL,
    date_of_birth       DATE NOT NULL,
    state_of_residence  VARCHAR2(2) NOT NULL,
    biological_sex      VARCHAR2(10) CHECK (biological_sex IN ('male','female')),
    age_bracket         VARCHAR2(10) CHECK (age_bracket IN ('18-29','30-39','40-49','50-59','60+')),
    fitness_level       VARCHAR2(20) CHECK (fitness_level IN ('beginner','intermediate','advanced')),
    tier_code           VARCHAR2(20),
    height_inches       NUMBER(3),
    weight_pounds       NUMBER(4),
    goals               JSON,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at          TIMESTAMP DEFAULT SYSTIMESTAMP,

    CONSTRAINT uk_profiles_user UNIQUE (user_id)
);

CREATE INDEX idx_profiles_tier ON profiles(tier_code);
```

#### 7.2.3 Tracker Connections

```sql
CREATE TABLE tracker_connections (
    connection_id       RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    user_id             RAW(16) NOT NULL REFERENCES users(user_id),
    provider            VARCHAR2(20) NOT NULL
                        CHECK (provider IN ('apple_health','google_fit','fitbit')),
    is_primary          NUMBER(1) DEFAULT 0,
    access_token        VARCHAR2(2000),  -- Encrypted
    refresh_token       VARCHAR2(2000),  -- Encrypted
    token_expires_at    TIMESTAMP,
    last_sync_at        TIMESTAMP,
    sync_status         VARCHAR2(20) DEFAULT 'pending'
                        CHECK (sync_status IN ('pending','syncing','success','error')),
    error_message       VARCHAR2(500),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at          TIMESTAMP DEFAULT SYSTIMESTAMP,

    CONSTRAINT uk_connection_user_provider UNIQUE (user_id, provider)
);
```

#### 7.2.4 Activities

```sql
CREATE TABLE activities (
    activity_id         RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    user_id             RAW(16) NOT NULL REFERENCES users(user_id),
    connection_id       RAW(16) REFERENCES tracker_connections(connection_id),
    external_id         VARCHAR2(255),
    activity_type       VARCHAR2(30) NOT NULL
                        CHECK (activity_type IN ('steps','workout','active_minutes')),
    start_time          TIMESTAMP NOT NULL,
    end_time            TIMESTAMP,
    duration_minutes    NUMBER(5),
    intensity           VARCHAR2(20) CHECK (intensity IN ('light','moderate','vigorous')),
    metrics             JSON,
    points_earned       NUMBER(5) DEFAULT 0,
    processed           NUMBER(1) DEFAULT 0,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,

    CONSTRAINT uk_activity_external UNIQUE (user_id, connection_id, external_id)
);

CREATE INDEX idx_activities_user_date ON activities(user_id, start_time);
CREATE INDEX idx_activities_unprocessed ON activities(processed) WHERE processed = 0;
```

#### 7.2.5 Point Transactions

```sql
CREATE TABLE point_transactions (
    transaction_id      RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    user_id             RAW(16) NOT NULL REFERENCES users(user_id),
    transaction_type    VARCHAR2(20) NOT NULL
                        CHECK (transaction_type IN ('earn','spend','adjust','expire')),
    amount              NUMBER(10) NOT NULL,
    balance_after       NUMBER(10) NOT NULL,
    reference_type      VARCHAR2(30),  -- 'activity', 'ticket_purchase', 'admin_adjust'
    reference_id        RAW(16),
    description         VARCHAR2(255),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE INDEX idx_transactions_user ON point_transactions(user_id, created_at);
```

#### 7.2.6 Drawings

```sql
CREATE TABLE drawings (
    drawing_id          RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    drawing_type        VARCHAR2(20) NOT NULL
                        CHECK (drawing_type IN ('daily','weekly','monthly','annual')),
    name                VARCHAR2(255) NOT NULL,
    description         CLOB,
    ticket_cost_points  NUMBER(6) NOT NULL,
    drawing_time        TIMESTAMP NOT NULL,
    ticket_sales_close  TIMESTAMP NOT NULL,
    eligibility         JSON,  -- {"user_type": "all", "min_account_age_days": 7}
    status              VARCHAR2(20) DEFAULT 'draft'
                        CHECK (status IN ('draft','scheduled','open','closed','completed','cancelled')),
    total_tickets       NUMBER(10) DEFAULT 0,
    random_seed         VARCHAR2(255),  -- For audit
    created_by          RAW(16) REFERENCES users(user_id),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    completed_at        TIMESTAMP
);

CREATE INDEX idx_drawings_status ON drawings(status, drawing_time);
```

#### 7.2.7 Tickets

```sql
CREATE TABLE tickets (
    ticket_id           RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    drawing_id          RAW(16) NOT NULL REFERENCES drawings(drawing_id),
    user_id             RAW(16) NOT NULL REFERENCES users(user_id),
    ticket_number       NUMBER(10),  -- Assigned at drawing close
    purchase_transaction_id RAW(16) REFERENCES point_transactions(transaction_id),
    is_winner           NUMBER(1) DEFAULT 0,
    prize_id            RAW(16),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE INDEX idx_tickets_drawing ON tickets(drawing_id);
CREATE INDEX idx_tickets_user ON tickets(user_id, drawing_id);
```

#### 7.2.8 Prizes

```sql
CREATE TABLE prizes (
    prize_id            RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    drawing_id          RAW(16) NOT NULL REFERENCES drawings(drawing_id),
    sponsor_id          RAW(16) REFERENCES sponsors(sponsor_id),
    rank                NUMBER(3) NOT NULL,  -- 1st, 2nd, 3rd place
    name                VARCHAR2(255) NOT NULL,
    description         CLOB,
    value_usd           NUMBER(10,2),
    quantity            NUMBER(3) DEFAULT 1,
    fulfillment_type    VARCHAR2(20) CHECK (fulfillment_type IN ('digital','physical')),
    image_url           VARCHAR2(500),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

#### 7.2.9 Prize Fulfillment

```sql
CREATE TABLE prize_fulfillments (
    fulfillment_id      RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    ticket_id           RAW(16) NOT NULL REFERENCES tickets(ticket_id),
    prize_id            RAW(16) NOT NULL REFERENCES prizes(prize_id),
    user_id             RAW(16) NOT NULL REFERENCES users(user_id),
    status              VARCHAR2(30) DEFAULT 'pending'
                        CHECK (status IN ('pending','winner_notified','address_confirmed',
                                         'address_invalid','shipped','delivered','forfeited')),
    shipping_address    JSON,
    tracking_number     VARCHAR2(100),
    carrier             VARCHAR2(50),
    notes               CLOB,
    notified_at         TIMESTAMP,
    address_confirmed_at TIMESTAMP,
    shipped_at          TIMESTAMP,
    delivered_at        TIMESTAMP,
    forfeit_at          TIMESTAMP,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at          TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

#### 7.2.10 Sponsors

```sql
CREATE TABLE sponsors (
    sponsor_id          RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    name                VARCHAR2(255) NOT NULL,
    contact_name        VARCHAR2(255),
    contact_email       VARCHAR2(255),
    contact_phone       VARCHAR2(20),
    website_url         VARCHAR2(500),
    logo_url            VARCHAR2(500),
    status              VARCHAR2(20) DEFAULT 'active'
                        CHECK (status IN ('active','inactive')),
    notes               CLOB,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at          TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

### 7.3 JSON Duality Views

Leveraging Oracle's JSON Duality Views for simplified document-style access:

```sql
CREATE JSON DUALITY VIEW user_profile_dv AS
SELECT JSON {
    '_id': u.user_id,
    'email': u.email,
    'status': u.status,
    'role': u.role,
    'pointBalance': u.point_balance,
    'profile': (
        SELECT JSON {
            'displayName': p.display_name,
            'ageBracket': p.age_bracket,
            'biologicalSex': p.biological_sex,
            'fitnessLevel': p.fitness_level,
            'tierCode': p.tier_code,
            'goals': p.goals
        }
        FROM profiles p WHERE p.user_id = u.user_id
    ),
    'connections': [
        SELECT JSON {
            'provider': c.provider,
            'isPrimary': c.is_primary,
            'lastSyncAt': c.last_sync_at,
            'syncStatus': c.sync_status
        }
        FROM tracker_connections c WHERE c.user_id = u.user_id
    ],
    'createdAt': u.created_at,
    'lastLoginAt': u.last_login_at
}
FROM users u;
```

---

## 8. API Design

### 8.1 API Overview

| Aspect         | Specification                 |
| -------------- | ----------------------------- |
| Style          | REST                          |
| Base URL       | `https://api.fittrack.com/v1` |
| Authentication | JWT (Bearer tokens)           |
| Content Type   | `application/json`            |
| Versioning     | URL path (`/v1/`)             |

### 8.2 Authentication Endpoints

#### POST /auth/register

Register a new user account.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "SecureP@ssw0rd!",
  "dateOfBirth": "1990-05-15",
  "stateOfResidence": "TX",
  "acceptedTerms": true,
  "acceptedSweepstakesRules": true
}
```

**Response (201 Created):**

```json
{
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "status": "pending",
  "message": "Verification email sent. Please check your inbox."
}
```

**Errors:**

- `400` - Validation error (invalid email, weak password, underage, ineligible state)
- `409` - Email already registered

#### POST /auth/login

Authenticate and receive JWT tokens.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "SecureP@ssw0rd!"
}
```

**Response (200 OK):**

```json
{
  "accessToken": "eyJhbGciOiJSUzI1NiIs...",
  "refreshToken": "dGhpcyBpcyBhIHJlZnJl...",
  "expiresIn": 3600,
  "user": {
    "userId": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "role": "user",
    "pointBalance": 1250
  }
}
```

#### POST /auth/refresh

Refresh an expired access token.

#### POST /auth/verify-email

Verify email with token from verification email.

#### POST /auth/forgot-password

Initiate password reset flow.

#### POST /auth/reset-password

Complete password reset with token.

### 8.3 User Endpoints

#### GET /users/me

Get current user's complete profile.

**Response (200 OK):**

```json
{
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "status": "active",
  "role": "user",
  "pointBalance": 1250,
  "profile": {
    "displayName": "FitRunner42",
    "ageBracket": "30-39",
    "biologicalSex": "male",
    "fitnessLevel": "intermediate",
    "tierCode": "M-30-39-INT",
    "goals": ["weight_loss", "endurance"]
  },
  "connections": [
    {
      "provider": "fitbit",
      "isPrimary": true,
      "lastSyncAt": "2026-01-15T14:30:00Z",
      "syncStatus": "success"
    }
  ],
  "stats": {
    "totalPointsEarned": 15420,
    "drawingsEntered": 45,
    "prizesWon": 2
  },
  "createdAt": "2025-11-01T10:00:00Z"
}
```

#### PUT /users/me/profile

Update user profile (triggers tier recalculation if relevant fields change).

#### GET /users/{userId}/public

Get another user's public profile (for leaderboards).

### 8.4 Tracker Connection Endpoints

#### GET /connections

List user's connected fitness trackers.

#### POST /connections/{provider}/initiate

Start OAuth flow for connecting a tracker.

**Response (200 OK):**

```json
{
  "authorizationUrl": "https://www.fitbit.com/oauth2/authorize?client_id=...",
  "state": "random-state-token"
}
```

#### POST /connections/{provider}/callback

Complete OAuth flow with authorization code.

#### DELETE /connections/{provider}

Disconnect a fitness tracker.

#### POST /connections/{provider}/sync

Force immediate sync (rate limited).

### 8.5 Activity Endpoints

#### GET /activities

Get user's activity history with pagination and filtering.

**Query Parameters:**

- `startDate` - ISO date
- `endDate` - ISO date
- `type` - `steps`, `workout`, `active_minutes`
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20, max: 100)

**Response (200 OK):**

```json
{
  "activities": [
    {
      "activityId": "...",
      "activityType": "workout",
      "startTime": "2026-01-15T07:00:00Z",
      "endTime": "2026-01-15T07:45:00Z",
      "durationMinutes": 45,
      "intensity": "vigorous",
      "metrics": {
        "calories": 450,
        "heartRateAvg": 145
      },
      "pointsEarned": 185,
      "source": "fitbit"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "totalItems": 156,
    "totalPages": 8
  }
}
```

#### GET /activities/summary

Get activity summary for dashboard.

**Response (200 OK):**

```json
{
  "today": {
    "steps": 8542,
    "activeMinutes": 45,
    "workouts": 1,
    "pointsEarned": 195,
    "pointsCap": 1000,
    "pointsRemaining": 805
  },
  "thisWeek": {
    "steps": 52340,
    "activeMinutes": 280,
    "workouts": 5,
    "pointsEarned": 1420,
    "streakDays": 4
  },
  "thisMonth": {
    "steps": 198000,
    "activeMinutes": 1050,
    "workouts": 18,
    "pointsEarned": 5230
  }
}
```

### 8.6 Points Endpoints

#### GET /points/balance

Get current point balance.

#### GET /points/transactions

Get point transaction history.

**Response (200 OK):**

```json
{
  "transactions": [
    {
      "transactionId": "...",
      "type": "earn",
      "amount": 100,
      "balanceAfter": 1350,
      "description": "Daily step goal achieved",
      "createdAt": "2026-01-15T00:05:00Z"
    },
    {
      "transactionId": "...",
      "type": "spend",
      "amount": -500,
      "balanceAfter": 850,
      "description": "Weekly drawing ticket purchase (x1)",
      "createdAt": "2026-01-14T18:30:00Z"
    }
  ],
  "pagination": { ... }
}
```

### 8.7 Drawing Endpoints

#### GET /drawings

List available and recent drawings.

**Query Parameters:**

- `status` - `open`, `closed`, `completed`
- `type` - `daily`, `weekly`, `monthly`, `annual`

**Response (200 OK):**

```json
{
  "drawings": [
    {
      "drawingId": "...",
      "type": "daily",
      "name": "Daily Drawing - January 16, 2026",
      "ticketCostPoints": 100,
      "drawingTime": "2026-01-16T21:00:00-05:00",
      "ticketSalesClose": "2026-01-16T20:55:00-05:00",
      "status": "open",
      "totalTickets": 4521,
      "userTickets": 3,
      "prizes": [
        {
          "rank": 1,
          "name": "$50 Amazon Gift Card",
          "valueUsd": 50.0,
          "quantity": 1,
          "sponsor": {
            "name": "Amazon",
            "logoUrl": "..."
          }
        }
      ]
    }
  ]
}
```

#### GET /drawings/{drawingId}

Get detailed drawing information.

#### POST /drawings/{drawingId}/tickets

Purchase tickets for a drawing.

**Request:**

```json
{
  "quantity": 5
}
```

**Response (201 Created):**

```json
{
  "ticketsPurchased": 5,
  "pointsSpent": 500,
  "newPointBalance": 750,
  "totalUserTickets": 8,
  "transactionId": "..."
}
```

**Errors:**

- `400` - Insufficient points, invalid quantity
- `403` - Drawing closed, user ineligible
- `404` - Drawing not found

#### GET /drawings/{drawingId}/results

Get drawing results (after completion).

**Response (200 OK):**

```json
{
  "drawingId": "...",
  "completedAt": "2026-01-15T21:00:15-05:00",
  "totalTickets": 4521,
  "winners": [
    {
      "rank": 1,
      "prizeName": "$50 Amazon Gift Card",
      "winner": {
        "displayName": "FitRunner42",
        "ticketsHeld": 8
      },
      "winningTicketNumber": 2847
    }
  ],
  "userParticipation": {
    "ticketsHeld": 3,
    "won": false
  }
}
```

### 8.8 Leaderboard Endpoints

#### GET /leaderboards/{period}

Get leaderboard for a specific period.

**Path Parameters:**

- `period` - `daily`, `weekly`, `monthly`, `alltime`

**Query Parameters:**

- `tier` - Tier code (defaults to user's tier)
- `page` - Page number
- `limit` - Items per page (max: 100)

**Response (200 OK):**

```json
{
  "period": "weekly",
  "tierCode": "M-30-39-INT",
  "tierName": "Male 30-39 Intermediate",
  "totalUsersInTier": 1247,
  "resetTime": "2026-01-20T00:00:00-05:00",
  "userRank": {
    "rank": 45,
    "pointsEarned": 1420,
    "displayName": "FitRunner42"
  },
  "rankings": [
    {
      "rank": 1,
      "displayName": "SpeedDemon99",
      "pointsEarned": 4250
    },
    {
      "rank": 2,
      "displayName": "IronWill",
      "pointsEarned": 4180
    }
  ],
  "pagination": { ... }
}
```

### 8.9 Admin Endpoints

All admin endpoints require `role: admin` in JWT.

#### Drawings Management

- `POST /admin/drawings` - Create drawing
- `PUT /admin/drawings/{id}` - Update drawing
- `POST /admin/drawings/{id}/execute` - Execute drawing (select winners)
- `DELETE /admin/drawings/{id}` - Cancel drawing

#### Sponsors Management

- `GET /admin/sponsors` - List sponsors
- `POST /admin/sponsors` - Create sponsor
- `PUT /admin/sponsors/{id}` - Update sponsor
- `DELETE /admin/sponsors/{id}` - Deactivate sponsor

#### Prize Fulfillment

- `GET /admin/fulfillments` - List pending fulfillments
- `PUT /admin/fulfillments/{id}` - Update fulfillment status
- `POST /admin/fulfillments/{id}/ship` - Mark as shipped with tracking

#### User Management

- `GET /admin/users` - List/search users
- `PUT /admin/users/{id}/status` - Suspend/ban user
- `POST /admin/users/{id}/adjust-points` - Manual point adjustment

#### Analytics

- `GET /admin/analytics/overview` - Dashboard metrics
- `GET /admin/analytics/registrations` - Registration trends
- `GET /admin/analytics/activity` - Activity metrics
- `GET /admin/analytics/drawings` - Drawing participation

---

## 9. UI/UX Wireframe Descriptions

### 9.1 Information Architecture

```
├── Public Pages
│   ├── Landing Page
│   ├── How It Works
│   ├── Prizes
│   ├── Login
│   └── Register
│
├── Authenticated User Pages
│   ├── Dashboard (Home)
│   ├── Activity
│   │   ├── Today
│   │   ├── History
│   │   └── Achievements
│   ├── Leaderboards
│   │   ├── My Tier
│   │   └── Browse Tiers
│   ├── Drawings
│   │   ├── Available
│   │   ├── My Entries
│   │   └── Results/History
│   ├── Profile
│   │   ├── Settings
│   │   ├── Connected Devices
│   │   └── Notifications
│   └── Premium (upsell/manage)
│
└── Admin Pages
    ├── Dashboard
    ├── Users
    ├── Drawings
    ├── Sponsors
    ├── Fulfillment
    └── Analytics
```

### 9.2 Key Screens

#### 9.2.1 User Dashboard

The dashboard is the primary landing page after login, providing at-a-glance status:

**Layout (Mobile-First):**

```
┌─────────────────────────────────────┐
│  [Logo]              [Points: 1,250]│
├─────────────────────────────────────┤
│  Welcome back, Sarah!               │
│                                     │
│  ┌─────────────────────────────┐   │
│  │    TODAY'S PROGRESS          │   │
│  │    ═══════════════════       │   │
│  │    Steps: 8,542 / 10,000     │   │
│  │    [████████░░] 85%          │   │
│  │                              │   │
│  │    Active Min: 45            │   │
│  │    Points Earned: 195        │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │    YOUR RANKING              │   │
│  │    #45 in F-30-39-INT        │   │
│  │    Weekly: 1,420 pts         │   │
│  │    [View Leaderboard →]      │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │    NEXT DRAWING              │   │
│  │    Daily - $50 Gift Card     │   │
│  │    Closes in: 4h 32m         │   │
│  │    Your tickets: 3           │   │
│  │    [Buy Tickets]             │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │    RECENT WINS               │   │
│  │    🎉 SpeedDemon99 won       │   │
│  │       Weekly - Fitbit Charge │   │
│  └─────────────────────────────┘   │
│                                     │
├─────────────────────────────────────┤
│  [Home] [Activity] [Draws] [Profile]│
└─────────────────────────────────────┘
```

#### 9.2.2 Drawings List

```
┌─────────────────────────────────────┐
│  ← Drawings                         │
├─────────────────────────────────────┤
│  [Open] [Upcoming] [Past Results]   │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │  🎁 DAILY DRAWING            │   │
│  │  $50 Amazon Gift Card        │   │
│  │                              │   │
│  │  Cost: 100 pts | Ends: 4h 32m│   │
│  │  Total Tickets: 4,521        │   │
│  │  Your Tickets: 3             │   │
│  │                              │   │
│  │  [Buy Tickets]               │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  🎁 WEEKLY DRAWING           │   │
│  │  Fitbit Charge 6             │   │
│  │                              │   │
│  │  Cost: 500 pts | Ends: 3d 4h │   │
│  │  Total Tickets: 12,847       │   │
│  │  Your Tickets: 0             │   │
│  │                              │   │
│  │  [Buy Tickets]               │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  🏆 MONTHLY DRAWING          │   │
│  │  Peloton Bike                │   │
│  │  Value: $1,445               │   │
│  │                              │   │
│  │  Cost: 2,000 pts             │   │
│  │  Ends: 15d 4h                │   │
│  │                              │   │
│  │  [Buy Tickets]               │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

#### 9.2.3 Ticket Purchase Modal

```
┌─────────────────────────────────────┐
│           Buy Tickets          [X]  │
├─────────────────────────────────────┤
│                                     │
│  Daily Drawing                      │
│  $50 Amazon Gift Card               │
│                                     │
│  ─────────────────────────────────  │
│                                     │
│  Ticket Cost: 100 points each       │
│  Your Balance: 1,250 points         │
│                                     │
│  Quantity:  [-]  5  [+]             │
│                                     │
│  ─────────────────────────────────  │
│                                     │
│  Total Cost: 500 points             │
│  Remaining Balance: 750 points      │
│                                     │
│  ─────────────────────────────────  │
│                                     │
│  Current odds: 1 in 905             │
│  After purchase: 1 in 566           │
│                                     │
│  ┌─────────────────────────────┐   │
│  │     CONFIRM PURCHASE         │   │
│  └─────────────────────────────┘   │
│                                     │
│  Ticket purchases are final.        │
│                                     │
└─────────────────────────────────────┘
```

#### 9.2.4 Leaderboard

```
┌─────────────────────────────────────┐
│  ← Leaderboard                      │
├─────────────────────────────────────┤
│  [Daily] [Weekly] [Monthly] [All]   │
├─────────────────────────────────────┤
│  Your Tier: Female 30-39 Inter.     │
│  [Change Tier ▼]                    │
├─────────────────────────────────────┤
│                                     │
│  YOUR POSITION                      │
│  ┌─────────────────────────────┐   │
│  │  #45 of 1,247               │   │
│  │  1,420 points this week     │   │
│  │  Top 4%                     │   │
│  └─────────────────────────────┘   │
│                                     │
├─────────────────────────────────────┤
│  Rank  User           Points        │
├─────────────────────────────────────┤
│  🥇 1  SpeedDemon99    4,250        │
│  🥈 2  IronWill        4,180        │
│  🥉 3  FitQueen        3,920        │
│     4  RunnerX         3,845        │
│     5  HealthNut       3,710        │
│    ...                              │
│    44  StepMaster      1,435        │
│  → 45  You (Sarah)     1,420  ←     │
│    46  GoalGetter      1,405        │
│    ...                              │
│                                     │
│         [Load More]                 │
│                                     │
└─────────────────────────────────────┘
```

### 9.3 Design System Notes

| Element         | Specification                       |
| --------------- | ----------------------------------- |
| Primary Color   | `#2C5282` (Blue)                    |
| Secondary Color | `#38A169` (Green - success/points)  |
| Accent Color    | `#D69E2E` (Gold - prizes/wins)      |
| Error Color     | `#E53E3E` (Red)                     |
| Typography      | Inter (headings), System UI (body)  |
| Border Radius   | 8px (cards), 4px (buttons)          |
| Spacing Scale   | 4px base (4, 8, 12, 16, 24, 32, 48) |

---

## 10. Security Considerations

### 10.1 Threat Model

| Threat               | Impact   | Likelihood | Mitigation                                               |
| -------------------- | -------- | ---------- | -------------------------------------------------------- |
| Account takeover     | High     | Medium     | MFA (v1.1), rate limiting, breach detection              |
| Point manipulation   | High     | Medium     | Server-side validation, audit logging, anomaly detection |
| Drawing manipulation | Critical | Low        | CSPRNG, audit trail, admin 2FA                           |
| Data breach          | High     | Low        | Encryption at rest/transit, minimal PII, access controls |
| DDoS                 | Medium   | Medium     | OCI WAF, rate limiting, auto-scaling                     |
| Bot/fake accounts    | Medium   | High       | CAPTCHA, device fingerprinting, velocity checks          |

### 10.2 Authentication & Authorization

#### 10.2.1 Authentication

- **Method:** JWT with RS256 signing
- **Access Token Lifetime:** 1 hour
- **Refresh Token Lifetime:** 30 days
- **Password Requirements:** 12+ characters, complexity enforced
- **Account Lockout:** 5 failed attempts → 15 minute lockout, progressive backoff
- **Session Management:** Single active session per device; "logout all devices" option

#### 10.2.2 Authorization (RBAC)

| Role      | Permissions                                                                |
| --------- | -------------------------------------------------------------------------- |
| `guest`   | View public pages, register                                                |
| `user`    | All guest + manage own account, participate in drawings, view leaderboards |
| `premium` | All user + access premium drawings, professional services                  |
| `admin`   | All permissions + user management, drawing management, analytics           |

### 10.3 Data Protection

#### 10.3.1 Encryption

| Data State   | Method                                   |
| ------------ | ---------------------------------------- |
| In Transit   | TLS 1.3 (minimum TLS 1.2)                |
| At Rest      | Oracle TDE (Transparent Data Encryption) |
| Secrets      | OCI Vault with customer-managed keys     |
| OAuth Tokens | AES-256-GCM encryption before storage    |

#### 10.3.2 PII Handling

| Data Element     | Classification | Retention                   | Access                 |
| ---------------- | -------------- | --------------------------- | ---------------------- |
| Email            | PII            | Account lifetime + 30 days  | User, Admin            |
| Date of Birth    | PII            | Account lifetime            | System only (age calc) |
| Shipping Address | PII            | Prize fulfillment + 90 days | User, Admin            |
| Password         | Sensitive      | N/A (hashed)                | None                   |
| Activity Data    | Personal       | 2 years                     | User, System           |
| IP Address       | PII            | 90 days (logs)              | Admin, Security        |

### 10.4 API Security

- **Rate Limiting:**
  - Anonymous: 10 requests/minute
  - Authenticated: 100 requests/minute
  - Admin: 500 requests/minute
- **Input Validation:** Strict schema validation on all inputs
- **Output Encoding:** JSON responses properly encoded
- **CORS:** Whitelist of allowed origins
- **CSRF:** SameSite cookies + custom header validation
- **Security Headers:** HSTS, X-Frame-Options, CSP, etc.

### 10.5 Drawing Integrity

The sweepstakes drawing process requires additional security measures:

1. **Random Number Generation:** OCI Vault CSPRNG
2. **Audit Trail:** Immutable log of all drawing actions
3. **Admin Authentication:** MFA required for drawing execution
4. **Ticket Snapshot:** Immutable snapshot created at sales close
5. **Result Publication:** Automated, no manual editing possible
6. **Third-Party Audit:** Annual audit by independent firm

### 10.6 Compliance Checklist

| Requirement         | Status   | Notes                            |
| ------------------- | -------- | -------------------------------- |
| CCPA Privacy Policy | Required | Legal to draft                   |
| Terms of Service    | Required | Legal to draft                   |
| Sweepstakes Rules   | Required | State-specific versions needed   |
| Age Verification    | Required | DOB collection + 18+ validation  |
| Data Export         | Required | User can export their data       |
| Data Deletion       | Required | Account deletion within 30 days  |
| Cookie Consent      | Required | Banner for non-essential cookies |

---

## 11. Testing Strategy

### 11.1 Testing Pyramid

```
          ╱╲
         ╱  ╲
        ╱ E2E╲         ~10% of tests
       ╱──────╲
      ╱        ╲
     ╱Integration╲     ~20% of tests
    ╱────────────╲
   ╱              ╲
  ╱     Unit       ╲   ~70% of tests
 ╱──────────────────╲
```

### 11.2 Unit Testing

| Component            | Framework                      | Coverage Target                |
| -------------------- | ------------------------------ | ------------------------------ |
| API Services         | pytest                         | 80%+                           |
| React Components     | React Testing Library          | 70%+                           |
| Utility Functions    | pytest                         | 90%+                           |
| Database Functions   | pytest + Oracle Test Container | 80%+                           |
| Property-Based Tests | pytest + Hypothesis            | Points calculation, tier logic |

**Focus Areas:**

- Points calculation logic
- Tier assignment logic
- Drawing eligibility rules
- Input validation (Pydantic schemas)

### 11.3 Integration Testing

| Integration        | Approach                                          |
| ------------------ | ------------------------------------------------- |
| API → Database     | Test containers with Oracle XE; pytest-asyncio    |
| API → Fitness APIs | Mock servers (respx for httpx)                    |
| API → OCI Services | OCI SDK mocks + limited live tests                |
| Auth Flows         | Full flow tests with test users; httpx TestClient |

### 11.4 End-to-End Testing

| Tool       | Purpose                 |
| ---------- | ----------------------- |
| Playwright | Cross-browser E2E tests |
| Scenarios  | Critical user journeys  |

**Critical E2E Scenarios:**

1. New user registration → profile completion → tracker connection → first activity sync
2. Point earning → ticket purchase → drawing entry → result viewing
3. Admin drawing creation → scheduling → execution → winner notification
4. Premium upgrade flow (v1.1)

### 11.5 Performance Testing

| Test Type        | Tool       | Targets                     |
| ---------------- | ---------- | --------------------------- |
| Load Testing     | k6         | 5,000 concurrent users      |
| Stress Testing   | k6         | Find breaking point         |
| Soak Testing     | k6         | 24-hour sustained load      |
| API Benchmarking | autocannon | Individual endpoint latency |

**Key Performance Scenarios:**

- Drawing close (high ticket purchase volume)
- Leaderboard updates (bulk read operations)
- Activity sync batch processing
- Peak evening hours simulation

### 11.6 Security Testing

| Test Type           | Frequency              | Provider                        |
| ------------------- | ---------------------- | ------------------------------- |
| SAST                | Every PR               | Snyk / GitHub Advanced Security |
| DAST                | Weekly                 | OWASP ZAP                       |
| Dependency Scanning | Daily                  | Snyk                            |
| Penetration Testing | Pre-launch + Quarterly | Third-party firm                |

---

## 12. Deployment & DevOps

### 12.1 Environments

| Environment | Purpose                | Infrastructure     |
| ----------- | ---------------------- | ------------------ |
| Development | Local development      | Docker Compose     |
| CI          | Automated testing      | OCI DevOps runners |
| Staging     | Pre-production testing | OCI (scaled down)  |
| Production  | Live system            | OCI (full scale)   |

### 12.2 CI/CD Pipeline

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Code   │───▶│  Build  │───▶│  Test   │───▶│ Deploy  │───▶│ Monitor │
│  Push   │    │         │    │         │    │ Staging │    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                  │
                                          ┌──────┴──────┐
                                          │   Manual    │
                                          │  Approval   │
                                          └──────┬──────┘
                                                 │
                                          ┌──────▼──────┐
                                          │   Deploy    │
                                          │ Production  │
                                          └─────────────┘
```

**Pipeline Stages:**

1. **Code Push:**
   - Trigger: PR to main branch
   - Actions: Lint (ruff), format check (black), type check (mypy)

2. **Build:**
   - Validate Python dependencies
   - Build React app
   - Build Docker images
   - Push to OCI Container Registry

3. **Test:**
   - Unit tests with pytest (parallel)
   - Integration tests
   - E2E tests (Playwright)
   - Security scans

4. **Deploy Staging:**
   - Automatic on main branch merge
   - Run smoke tests
   - Performance baseline check

5. **Deploy Production:**
   - Manual approval required
   - Blue-green deployment
   - Automated rollback on health check failure

### 12.3 Infrastructure as Code

| Component            | Tool                                  |
| -------------------- | ------------------------------------- |
| OCI Resources        | Terraform                             |
| Kubernetes Manifests | Helm charts                           |
| Database Schema      | Alembic (Python migrations)           |
| Secrets              | OCI Vault + External Secrets Operator |

### 12.4 Monitoring & Observability

| Aspect     | Tool                          | Purpose                        |
| ---------- | ----------------------------- | ------------------------------ |
| Metrics    | OCI Monitoring + Prometheus   | System and application metrics |
| Logging    | OCI Logging + Loki            | Centralized log aggregation    |
| Tracing    | OCI APM                       | Distributed request tracing    |
| Alerting   | OCI Notifications + PagerDuty | Incident notification          |
| Dashboards | Grafana                       | Visualization                  |

**Key Alerts:**

| Alert                | Condition                   | Severity |
| -------------------- | --------------------------- | -------- |
| API Error Rate       | > 1% errors (5xx) for 5 min | Critical |
| API Latency          | p95 > 1s for 5 min          | Warning  |
| Database Connections | > 80% pool utilization      | Warning  |
| Sync Failures        | > 10% failure rate          | Warning  |
| Drawing Failure      | Any drawing execution error | Critical |
| Disk Space           | > 80% utilized              | Warning  |

### 12.5 Backup & Disaster Recovery

| Component      | Backup Strategy                     | RPO       | RTO    |
| -------------- | ----------------------------------- | --------- | ------ |
| Database       | Oracle Autonomous automatic backups | 15 min    | 1 hour |
| Object Storage | Cross-region replication            | 15 min    | 1 hour |
| Configuration  | Git repository                      | Real-time | 30 min |

**Disaster Recovery Procedure:**

1. Detect failure (automated health checks)
2. Assess scope (single service vs. regional outage)
3. Execute runbook (automated where possible)
4. Validate recovery
5. Post-incident review

---

## 13. Success Metrics

### 13.1 Key Performance Indicators (KPIs)

#### Business Metrics

| Metric                          | Definition                                | MVP Target | Scale Target |
| ------------------------------- | ----------------------------------------- | ---------- | ------------ |
| Monthly Active Users (MAU)      | Users with ≥1 activity sync               | 10,000     | 500,000      |
| Daily Active Users (DAU)        | Users with ≥1 session                     | 3,000      | 150,000      |
| User Retention (D7)             | % users active 7 days after registration  | 40%        | 50%          |
| User Retention (D30)            | % users active 30 days after registration | 25%        | 35%          |
| Premium Conversion              | % free users upgrading to premium         | 5%         | 8%           |
| Average Revenue Per User (ARPU) | Monthly subscription revenue / MAU        | $0.50      | $2.00        |

#### Engagement Metrics

| Metric                          | Definition                                   | MVP Target | Scale Target |
| ------------------------------- | -------------------------------------------- | ---------- | ------------ |
| Activities per User (Weekly)    | Avg synced activities per active user        | 5          | 10           |
| Points Earned per User (Weekly) | Avg points earned per active user            | 500        | 1,000        |
| Drawing Participation Rate      | % active users entering ≥1 drawing/week      | 30%        | 50%          |
| Tickets per Participant         | Avg tickets purchased per participating user | 3          | 5            |

#### Technical Metrics

| Metric                    | Definition                               | Target |
| ------------------------- | ---------------------------------------- | ------ |
| API Availability          | Successful requests / total requests     | 99.9%  |
| Sync Success Rate         | Successful syncs / attempted syncs       | 99%    |
| Drawing Execution Success | Successful drawings / scheduled drawings | 100%   |
| Page Load Time (p95)      | 95th percentile load time                | < 2s   |
| Error Rate                | 5xx responses / total responses          | < 0.1% |

### 13.2 Measurement Implementation

| Metric     | Collection Method                    | Dashboard          |
| ---------- | ------------------------------------ | ------------------ |
| MAU/DAU    | Database query + analytics events    | Admin Dashboard    |
| Retention  | Cohort analysis (Amplitude/Mixpanel) | Analytics Platform |
| Conversion | Funnel tracking                      | Analytics Platform |
| Engagement | Application events                   | Admin Dashboard    |
| Technical  | OCI Monitoring + APM                 | Grafana            |

---

## 14. Risks & Mitigations

### 14.1 Technical Risks

| Risk                             | Impact                        | Probability | Mitigation                                                  |
| -------------------------------- | ----------------------------- | ----------- | ----------------------------------------------------------- |
| Fitness API rate limits exceeded | Users can't sync              | Medium      | Implement queuing, optimize batch sizes, cache aggressively |
| Fitness API deprecation/changes  | Integration breaks            | Low         | Abstract integration layer, monitor API announcements       |
| Database performance at scale    | Slow leaderboards, poor UX    | Medium      | Proper indexing, read replicas, caching strategy            |
| Drawing system manipulation      | Legal liability, trust damage | Low         | CSPRNG, audit trails, third-party audits                    |
| OAuth token expiration handling  | Sync failures                 | Medium      | Proactive refresh, clear user messaging                     |

### 14.2 Business Risks

| Risk                            | Impact               | Probability | Mitigation                                                        |
| ------------------------------- | -------------------- | ----------- | ----------------------------------------------------------------- |
| Low user acquisition            | Business failure     | Medium      | Marketing plan, referral program, sponsor partnerships            |
| High churn rate                 | Unsustainable growth | Medium      | Engagement features, community building, prize value              |
| Sponsor acquisition difficulty  | Limited prizes       | Medium      | Start with gift cards, demonstrate user engagement                |
| Legal challenges (sweepstakes)  | Operational shutdown | Low         | Legal review, conservative state selection, compliance monitoring |
| Premium conversion below target | Revenue shortfall    | Medium      | Value proposition refinement, trial periods                       |

### 14.3 Operational Risks

| Risk                      | Impact               | Probability | Mitigation                                        |
| ------------------------- | -------------------- | ----------- | ------------------------------------------------- |
| Prize fulfillment delays  | User dissatisfaction | Medium      | Clear SLAs, tracking visibility, backup suppliers |
| Customer support overload | Poor user experience | Medium      | Self-service tools, FAQ, chatbot (v1.1)           |
| Admin operational errors  | Drawing issues       | Low         | Approval workflows, audit logs, admin training    |

---

## 15. Milestones & Phases

### 15.1 Phase Overview

```
    Jan 2026        Feb 2026        Mar 2026        Apr 2026        May 2026
    ────────────────────────────────────────────────────────────────────────
    │   Phase 1    │         Phase 2          │    Phase 3    │   Phase 4  │
    │  Foundation  │       Core Features      │    Testing    │   Launch   │
    │  (4 weeks)   │       (8 weeks)          │   (4 weeks)   │  (2 weeks) │
    ────────────────────────────────────────────────────────────────────────
```

### 15.2 Phase 1: Foundation (Weeks 1-4)

**Objectives:** Infrastructure setup, core architecture, team onboarding

| Week | Deliverables                                                               |
| ---- | -------------------------------------------------------------------------- |
| 1    | OCI environment setup (Terraform), CI/CD pipeline, development environment |
| 2    | Database schema implementation, API scaffolding, authentication system     |
| 3    | User registration flow, email verification, basic profile management       |
| 4    | Admin UI scaffolding, logging/monitoring setup                             |

**Exit Criteria:**

- [ ] Users can register and login
- [ ] CI/CD deploys to staging automatically
- [ ] Monitoring dashboards operational

### 15.3 Phase 2: Core Features (Weeks 5-12)

**Objectives:** Build all MVP functionality

| Week  | Deliverables                                        |
| ----- | --------------------------------------------------- |
| 5-6   | Fitness tracker OAuth flows, data sync engine       |
| 7-8   | Points system, activity logging, balance management |
| 9-10  | Tier system, leaderboard engine, rankings           |
| 11-12 | Drawing system, ticket purchasing, winner selection |

**Exit Criteria:**

- [ ] All three tracker integrations working
- [ ] Points earned from activities correctly
- [ ] Leaderboards displaying and updating
- [ ] Drawings can be created and executed

### 15.4 Phase 3: Testing & Refinement (Weeks 13-16)

**Objectives:** Quality assurance, performance optimization, security hardening

| Week | Deliverables                                             |
| ---- | -------------------------------------------------------- |
| 13   | Integration testing, bug fixes, UX refinements           |
| 14   | Performance testing, optimization, load testing          |
| 15   | Security testing, penetration testing, compliance review |
| 16   | UAT with beta users, final bug fixes                     |

**Exit Criteria:**

- [ ] All critical/high bugs resolved
- [ ] Performance targets met under load
- [ ] Security assessment passed
- [ ] Legal compliance verified

### 15.5 Phase 4: Launch (Weeks 17-18)

**Objectives:** Production deployment, marketing launch, operational readiness

| Week | Deliverables                                                      |
| ---- | ----------------------------------------------------------------- |
| 17   | Production deployment, final testing, soft launch (limited users) |
| 18   | Public launch, monitoring, rapid response team                    |

**Exit Criteria:**

- [ ] Production stable for 48 hours
- [ ] First drawing executed successfully
- [ ] Support processes operational

### 15.6 Post-MVP Roadmap (v1.1+)

| Feature                           | Target Release | Priority |
| --------------------------------- | -------------- | -------- |
| Native iOS/Android apps           | Q3 2026        | High     |
| Premium subscription (Stripe)     | Q2 2026        | High     |
| Social login (Google, Apple)      | Q2 2026        | Medium   |
| Real-time leaderboards            | Q3 2026        | Medium   |
| Professional services marketplace | Q4 2026        | Medium   |
| Sponsor self-service portal       | Q4 2026        | Medium   |
| Team/group competitions           | Q1 2027        | Low      |
| International expansion           | 2027           | Low      |

---

## 16. Open Questions & Assumptions

### 16.1 Decisions Needed

| ID    | Question                                                                             | Impact                       | Owner         | Due Date |
| ----- | ------------------------------------------------------------------------------------ | ---------------------------- | ------------- | -------- |
| D-001 | Social login (Google, Apple) in MVP or v1.1?                                         | Development scope            | Product       | Week 1   |
| D-002 | Apple Health integration approach: native iOS app, third-party aggregator, or defer? | Architecture, timeline, cost | Engineering   | Week 1   |
| D-003 | Should users opt into "Open" tier (all demographics)?                                | UX design, database schema   | Product       | Week 2   |
| D-004 | Point earning rate normalization across tiers?                                       | Game balance, fairness       | Product       | Week 3   |
| D-005 | Final list of eligible states for launch                                             | Legal compliance             | Legal         | Week 2   |
| D-006 | Prize value thresholds requiring tax reporting (1099)                                | Legal, admin workflows       | Legal/Finance | Week 4   |
| D-007 | Premium subscription price point                                                     | Revenue model                | Business      | Week 6   |

### 16.2 Assumptions

| ID    | Assumption                                                                     | Risk if Wrong                           | Validation Plan                            |
| ----- | ------------------------------------------------------------------------------ | --------------------------------------- | ------------------------------------------ |
| A-001 | Biological sex categories (Male/Female) are sufficient for fair tiering        | User complaints, legal issues           | User research, legal review                |
| A-002 | 15-minute sync interval is acceptable for MVP                                  | User dissatisfaction                    | Beta user feedback                         |
| A-003 | Daily 1,000 point cap prevents gaming without frustrating legitimate users     | Either gaming or frustrated power users | Monitor outliers, adjust                   |
| A-004 | Email verification is sufficient for account security (no MFA in MVP)          | Account takeovers                       | Security monitoring, add MFA in v1.1       |
| A-005 | Manual prize fulfillment scales for MVP volume                                 | Admin overload                          | Monitor volume, plan automation trigger    |
| A-006 | Gift cards are sufficient prizes for launch (no sponsor partnerships required) | Low user interest                       | User surveys, sponsor outreach in parallel |
| A-007 | Three fitness tracker integrations cover majority of target market             | Low adoption                            | Market research, user feedback             |

### 16.3 Dependencies

| Dependency                            | Owner       | Status      | Blocker For            |
| ------------------------------------- | ----------- | ----------- | ---------------------- |
| Legal review of Terms of Service      | Legal       | Not Started | Launch                 |
| Legal review of Sweepstakes Rules     | Legal       | Not Started | Drawing feature        |
| State eligibility matrix              | Legal       | Not Started | Registration flow      |
| Fitbit API developer account approval | Engineering | Not Started | Fitbit integration     |
| Google Fit API verification           | Engineering | Not Started | Google Fit integration |
| OCI environment provisioning          | DevOps      | Not Started | All development        |
| Design system and UI mockups          | Design      | Not Started | Frontend development   |

---

## Appendix A: Glossary

| Term                  | Definition                                                                  |
| --------------------- | --------------------------------------------------------------------------- |
| **Active Minutes**    | Minutes spent in physical activity as reported by fitness tracker           |
| **CSPRNG**            | Cryptographically Secure Pseudo-Random Number Generator                     |
| **Drawing**           | A sweepstakes event where winners are randomly selected from ticket holders |
| **JSON Duality View** | Oracle database feature allowing document-style access to relational data   |
| **OCI**               | Oracle Cloud Infrastructure                                                 |
| **Point Balance**     | User's current spendable points                                             |
| **Points Earned**     | Total points accumulated (used for leaderboard ranking)                     |
| **Tier**              | Competition bracket based on user demographics and fitness level            |
| **Ticket**            | Entry into a sweepstakes drawing, purchased with points                     |

---

## Appendix B: Reference Documents

- Oracle Autonomous JSON Database Documentation
- OCI Architecture Best Practices
- Fitbit Web API Reference
- Google Fit REST API Reference
- Apple HealthKit Documentation
- State Sweepstakes Law Summary (to be provided by Legal)

---

_Document Version: 1.0_
_Last Updated: January 2026_
_Next Review: Prior to Phase 2 kickoff_
