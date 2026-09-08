-- FitTrack Initial Schema
-- Oracle 23ai Free - Relational tables for JSON Duality Views
-- Version: 1.0.0

-- =====================================================
-- USERS TABLE
-- =====================================================
CREATE TABLE users (
    id VARCHAR2(36) PRIMARY KEY,
    email VARCHAR2(255) NOT NULL,
    password_hash VARCHAR2(255) NOT NULL,
    email_verified NUMBER(1) DEFAULT 0 NOT NULL,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR2(20) DEFAULT 'pending' NOT NULL,
    role VARCHAR2(20) DEFAULT 'user' NOT NULL,
    premium_expires_at TIMESTAMP WITH TIME ZONE,
    point_balance NUMBER(10) DEFAULT 0 NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    version NUMBER(10) DEFAULT 1 NOT NULL,
    CONSTRAINT users_email_uk UNIQUE (email),
    CONSTRAINT users_status_chk CHECK (status IN ('pending', 'active', 'suspended', 'banned')),
    CONSTRAINT users_role_chk CHECK (role IN ('user', 'premium', 'admin')),
    CONSTRAINT users_point_balance_chk CHECK (point_balance >= 0)
);

CREATE INDEX users_status_idx ON users(status);
CREATE INDEX users_role_idx ON users(role);
CREATE INDEX users_email_lower_idx ON users(LOWER(email));

-- =====================================================
-- PROFILES TABLE
-- =====================================================
CREATE TABLE profiles (
    id VARCHAR2(36) PRIMARY KEY,
    user_id VARCHAR2(36) NOT NULL,
    display_name VARCHAR2(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    state_of_residence CHAR(2) NOT NULL,
    biological_sex VARCHAR2(10) NOT NULL,
    fitness_level VARCHAR2(20) NOT NULL,
    age_bracket VARCHAR2(10),
    tier_code VARCHAR2(20),
    height_inches NUMBER(3),
    weight_pounds NUMBER(4),
    goals JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT profiles_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT profiles_user_uk UNIQUE (user_id),
    CONSTRAINT profiles_sex_chk CHECK (biological_sex IN ('male', 'female')),
    CONSTRAINT profiles_fitness_chk CHECK (fitness_level IN ('beginner', 'intermediate', 'advanced')),
    CONSTRAINT profiles_state_chk CHECK (state_of_residence NOT IN ('NY', 'FL', 'RI'))
);

CREATE INDEX profiles_tier_code_idx ON profiles(tier_code);
CREATE INDEX profiles_state_idx ON profiles(state_of_residence);

-- =====================================================
-- TRACKER_CONNECTIONS TABLE
-- =====================================================
CREATE TABLE tracker_connections (
    id VARCHAR2(36) PRIMARY KEY,
    user_id VARCHAR2(36) NOT NULL,
    provider VARCHAR2(20) NOT NULL,
    is_primary NUMBER(1) DEFAULT 0 NOT NULL,
    access_token CLOB,
    refresh_token CLOB,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR2(20) DEFAULT 'pending' NOT NULL,
    error_message VARCHAR2(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT connections_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT connections_provider_chk CHECK (provider IN ('apple_health', 'google_fit', 'fitbit')),
    CONSTRAINT connections_sync_chk CHECK (sync_status IN ('pending', 'syncing', 'success', 'error')),
    CONSTRAINT connections_user_provider_uk UNIQUE (user_id, provider)
);

CREATE INDEX connections_user_idx ON tracker_connections(user_id);
CREATE INDEX connections_sync_status_idx ON tracker_connections(sync_status);
CREATE INDEX connections_last_sync_idx ON tracker_connections(last_sync_at);

-- =====================================================
-- ACTIVITIES TABLE
-- =====================================================
CREATE TABLE activities (
    id VARCHAR2(36) PRIMARY KEY,
    user_id VARCHAR2(36) NOT NULL,
    connection_id VARCHAR2(36),
    external_id VARCHAR2(255),
    activity_type VARCHAR2(20) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_minutes NUMBER(5),
    intensity VARCHAR2(20),
    metrics JSON,
    points_earned NUMBER(10) DEFAULT 0 NOT NULL,
    processed NUMBER(1) DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT activities_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT activities_connection_fk FOREIGN KEY (connection_id) REFERENCES tracker_connections(id) ON DELETE SET NULL,
    CONSTRAINT activities_type_chk CHECK (activity_type IN ('steps', 'workout', 'active_minutes')),
    CONSTRAINT activities_intensity_chk CHECK (intensity IS NULL OR intensity IN ('light', 'moderate', 'vigorous')),
    CONSTRAINT activities_points_chk CHECK (points_earned >= 0)
);

CREATE INDEX activities_user_idx ON activities(user_id);
CREATE INDEX activities_start_time_idx ON activities(start_time);
CREATE INDEX activities_user_date_idx ON activities(user_id, start_time);
CREATE INDEX activities_processed_idx ON activities(processed) WHERE processed = 0;
CREATE INDEX activities_external_idx ON activities(external_id);

-- =====================================================
-- POINT_TRANSACTIONS TABLE
-- =====================================================
CREATE TABLE point_transactions (
    id VARCHAR2(36) PRIMARY KEY,
    user_id VARCHAR2(36) NOT NULL,
    transaction_type VARCHAR2(20) NOT NULL,
    amount NUMBER(10) NOT NULL,
    balance_after NUMBER(10) NOT NULL,
    reference_type VARCHAR2(50),
    reference_id VARCHAR2(36),
    description VARCHAR2(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT transactions_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT transactions_type_chk CHECK (transaction_type IN ('earn', 'spend', 'adjust', 'expire')),
    CONSTRAINT transactions_amount_chk CHECK (amount > 0),
    CONSTRAINT transactions_balance_chk CHECK (balance_after >= 0)
);

CREATE INDEX transactions_user_idx ON point_transactions(user_id);
CREATE INDEX transactions_user_created_idx ON point_transactions(user_id, created_at DESC);
CREATE INDEX transactions_reference_idx ON point_transactions(reference_type, reference_id);

-- =====================================================
-- SPONSORS TABLE (created before drawings for FK)
-- =====================================================
CREATE TABLE sponsors (
    id VARCHAR2(36) PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    contact_name VARCHAR2(255),
    contact_email VARCHAR2(255),
    contact_phone VARCHAR2(20),
    website_url VARCHAR2(500),
    logo_url VARCHAR2(500),
    status VARCHAR2(20) DEFAULT 'active' NOT NULL,
    notes CLOB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT sponsors_status_chk CHECK (status IN ('active', 'inactive'))
);

CREATE INDEX sponsors_status_idx ON sponsors(status);

-- =====================================================
-- DRAWINGS TABLE
-- =====================================================
CREATE TABLE drawings (
    id VARCHAR2(36) PRIMARY KEY,
    drawing_type VARCHAR2(20) NOT NULL,
    name VARCHAR2(255) NOT NULL,
    description CLOB,
    ticket_cost_points NUMBER(10) NOT NULL,
    drawing_time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticket_sales_close TIMESTAMP WITH TIME ZONE NOT NULL,
    eligibility JSON,
    status VARCHAR2(20) DEFAULT 'draft' NOT NULL,
    total_tickets NUMBER(10) DEFAULT 0 NOT NULL,
    random_seed VARCHAR2(255),
    created_by VARCHAR2(36),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT drawings_created_by_fk FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT drawings_type_chk CHECK (drawing_type IN ('daily', 'weekly', 'monthly', 'annual')),
    CONSTRAINT drawings_status_chk CHECK (status IN ('draft', 'scheduled', 'open', 'closed', 'completed', 'cancelled')),
    CONSTRAINT drawings_cost_chk CHECK (ticket_cost_points > 0),
    CONSTRAINT drawings_tickets_chk CHECK (total_tickets >= 0)
);

CREATE INDEX drawings_status_idx ON drawings(status);
CREATE INDEX drawings_type_idx ON drawings(drawing_type);
CREATE INDEX drawings_time_idx ON drawings(drawing_time);
CREATE INDEX drawings_sales_close_idx ON drawings(ticket_sales_close);

-- =====================================================
-- PRIZES TABLE
-- =====================================================
CREATE TABLE prizes (
    id VARCHAR2(36) PRIMARY KEY,
    drawing_id VARCHAR2(36) NOT NULL,
    sponsor_id VARCHAR2(36),
    rank NUMBER(3) NOT NULL,
    name VARCHAR2(255) NOT NULL,
    description CLOB,
    value_usd NUMBER(10, 2),
    quantity NUMBER(5) DEFAULT 1 NOT NULL,
    fulfillment_type VARCHAR2(20) NOT NULL,
    image_url VARCHAR2(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT prizes_drawing_fk FOREIGN KEY (drawing_id) REFERENCES drawings(id) ON DELETE CASCADE,
    CONSTRAINT prizes_sponsor_fk FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE SET NULL,
    CONSTRAINT prizes_rank_chk CHECK (rank >= 1),
    CONSTRAINT prizes_quantity_chk CHECK (quantity >= 1),
    CONSTRAINT prizes_fulfillment_chk CHECK (fulfillment_type IN ('digital', 'physical')),
    CONSTRAINT prizes_value_chk CHECK (value_usd IS NULL OR value_usd >= 0)
);

CREATE INDEX prizes_drawing_idx ON prizes(drawing_id);
CREATE INDEX prizes_sponsor_idx ON prizes(sponsor_id);

-- =====================================================
-- TICKETS TABLE
-- =====================================================
CREATE TABLE tickets (
    id VARCHAR2(36) PRIMARY KEY,
    drawing_id VARCHAR2(36) NOT NULL,
    user_id VARCHAR2(36) NOT NULL,
    ticket_number NUMBER(10),
    purchase_transaction_id VARCHAR2(36),
    is_winner NUMBER(1) DEFAULT 0 NOT NULL,
    prize_id VARCHAR2(36),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT tickets_drawing_fk FOREIGN KEY (drawing_id) REFERENCES drawings(id) ON DELETE CASCADE,
    CONSTRAINT tickets_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT tickets_transaction_fk FOREIGN KEY (purchase_transaction_id) REFERENCES point_transactions(id) ON DELETE SET NULL,
    CONSTRAINT tickets_prize_fk FOREIGN KEY (prize_id) REFERENCES prizes(id) ON DELETE SET NULL
);

CREATE INDEX tickets_drawing_idx ON tickets(drawing_id);
CREATE INDEX tickets_user_idx ON tickets(user_id);
CREATE INDEX tickets_drawing_user_idx ON tickets(drawing_id, user_id);
CREATE INDEX tickets_winner_idx ON tickets(is_winner) WHERE is_winner = 1;

-- =====================================================
-- PRIZE_FULFILLMENTS TABLE
-- =====================================================
CREATE TABLE prize_fulfillments (
    id VARCHAR2(36) PRIMARY KEY,
    ticket_id VARCHAR2(36) NOT NULL,
    prize_id VARCHAR2(36) NOT NULL,
    user_id VARCHAR2(36) NOT NULL,
    status VARCHAR2(30) DEFAULT 'pending' NOT NULL,
    shipping_address JSON,
    tracking_number VARCHAR2(100),
    carrier VARCHAR2(50),
    notes CLOB,
    notified_at TIMESTAMP WITH TIME ZONE,
    address_confirmed_at TIMESTAMP WITH TIME ZONE,
    shipped_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    forfeit_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fulfillments_ticket_fk FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    CONSTRAINT fulfillments_prize_fk FOREIGN KEY (prize_id) REFERENCES prizes(id) ON DELETE CASCADE,
    CONSTRAINT fulfillments_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fulfillments_ticket_uk UNIQUE (ticket_id),
    CONSTRAINT fulfillments_status_chk CHECK (status IN ('pending', 'winner_notified', 'address_confirmed', 'address_invalid', 'shipped', 'delivered', 'forfeited'))
);

CREATE INDEX fulfillments_status_idx ON prize_fulfillments(status);
CREATE INDEX fulfillments_user_idx ON prize_fulfillments(user_id);

-- =====================================================
-- UPDATE TIMESTAMP TRIGGER (for all tables)
-- =====================================================
CREATE OR REPLACE TRIGGER users_update_trigger
    BEFORE UPDATE ON users
    FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

CREATE OR REPLACE TRIGGER profiles_update_trigger
    BEFORE UPDATE ON profiles
    FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

CREATE OR REPLACE TRIGGER connections_update_trigger
    BEFORE UPDATE ON tracker_connections
    FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

CREATE OR REPLACE TRIGGER activities_update_trigger
    BEFORE UPDATE ON activities
    FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

CREATE OR REPLACE TRIGGER transactions_update_trigger
    BEFORE UPDATE ON point_transactions
    FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

CREATE OR REPLACE TRIGGER sponsors_update_trigger
    BEFORE UPDATE ON sponsors
    FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

CREATE OR REPLACE TRIGGER drawings_update_trigger
    BEFORE UPDATE ON drawings
    FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

CREATE OR REPLACE TRIGGER prizes_update_trigger
    BEFORE UPDATE ON prizes
    FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

CREATE OR REPLACE TRIGGER tickets_update_trigger
    BEFORE UPDATE ON tickets
    FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

CREATE OR REPLACE TRIGGER fulfillments_update_trigger
    BEFORE UPDATE ON prize_fulfillments
    FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

COMMIT;
