-- FitTrack JSON Duality Views
-- Oracle 23ai Free - Document API over relational schema
-- Version: 1.0.0

-- =====================================================
-- USERS DUALITY VIEW
-- Provides document-style access to user data
-- =====================================================
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW users_dv AS
SELECT JSON {
    '_id': u.id,
    'email': u.email,
    'password_hash': u.password_hash,
    'email_verified': CASE WHEN u.email_verified = 1 THEN TRUE ELSE FALSE END,
    'email_verified_at': u.email_verified_at,
    'status': u.status,
    'role': u.role,
    'premium_expires_at': u.premium_expires_at,
    'point_balance': u.point_balance,
    'last_login_at': u.last_login_at,
    'created_at': u.created_at,
    'updated_at': u.updated_at,
    'version': u.version
}
FROM users u WITH INSERT UPDATE DELETE;

-- =====================================================
-- PROFILES DUALITY VIEW
-- =====================================================
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW profiles_dv AS
SELECT JSON {
    '_id': p.id,
    'user_id': p.user_id,
    'display_name': p.display_name,
    'date_of_birth': p.date_of_birth,
    'state_of_residence': p.state_of_residence,
    'biological_sex': p.biological_sex,
    'fitness_level': p.fitness_level,
    'age_bracket': p.age_bracket,
    'tier_code': p.tier_code,
    'height_inches': p.height_inches,
    'weight_pounds': p.weight_pounds,
    'goals': p.goals,
    'created_at': p.created_at,
    'updated_at': p.updated_at
}
FROM profiles p WITH INSERT UPDATE DELETE;

-- =====================================================
-- TRACKER_CONNECTIONS DUALITY VIEW
-- =====================================================
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW tracker_connections_dv AS
SELECT JSON {
    '_id': tc.id,
    'user_id': tc.user_id,
    'provider': tc.provider,
    'is_primary': CASE WHEN tc.is_primary = 1 THEN TRUE ELSE FALSE END,
    'access_token': tc.access_token,
    'refresh_token': tc.refresh_token,
    'token_expires_at': tc.token_expires_at,
    'last_sync_at': tc.last_sync_at,
    'sync_status': tc.sync_status,
    'error_message': tc.error_message,
    'created_at': tc.created_at,
    'updated_at': tc.updated_at
}
FROM tracker_connections tc WITH INSERT UPDATE DELETE;

-- =====================================================
-- ACTIVITIES DUALITY VIEW
-- =====================================================
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW activities_dv AS
SELECT JSON {
    '_id': a.id,
    'user_id': a.user_id,
    'connection_id': a.connection_id,
    'external_id': a.external_id,
    'activity_type': a.activity_type,
    'start_time': a.start_time,
    'end_time': a.end_time,
    'duration_minutes': a.duration_minutes,
    'intensity': a.intensity,
    'metrics': a.metrics,
    'points_earned': a.points_earned,
    'processed': CASE WHEN a.processed = 1 THEN TRUE ELSE FALSE END,
    'created_at': a.created_at,
    'updated_at': a.updated_at
}
FROM activities a WITH INSERT UPDATE DELETE;

-- =====================================================
-- POINT_TRANSACTIONS DUALITY VIEW
-- =====================================================
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW point_transactions_dv AS
SELECT JSON {
    '_id': pt.id,
    'user_id': pt.user_id,
    'transaction_type': pt.transaction_type,
    'amount': pt.amount,
    'balance_after': pt.balance_after,
    'reference_type': pt.reference_type,
    'reference_id': pt.reference_id,
    'description': pt.description,
    'created_at': pt.created_at,
    'updated_at': pt.updated_at
}
FROM point_transactions pt WITH INSERT UPDATE DELETE;

-- =====================================================
-- SPONSORS DUALITY VIEW
-- =====================================================
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW sponsors_dv AS
SELECT JSON {
    '_id': s.id,
    'name': s.name,
    'contact_name': s.contact_name,
    'contact_email': s.contact_email,
    'contact_phone': s.contact_phone,
    'website_url': s.website_url,
    'logo_url': s.logo_url,
    'status': s.status,
    'notes': s.notes,
    'created_at': s.created_at,
    'updated_at': s.updated_at
}
FROM sponsors s WITH INSERT UPDATE DELETE;

-- =====================================================
-- DRAWINGS DUALITY VIEW
-- =====================================================
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW drawings_dv AS
SELECT JSON {
    '_id': d.id,
    'drawing_type': d.drawing_type,
    'name': d.name,
    'description': d.description,
    'ticket_cost_points': d.ticket_cost_points,
    'drawing_time': d.drawing_time,
    'ticket_sales_close': d.ticket_sales_close,
    'eligibility': d.eligibility,
    'status': d.status,
    'total_tickets': d.total_tickets,
    'random_seed': d.random_seed,
    'created_by': d.created_by,
    'completed_at': d.completed_at,
    'created_at': d.created_at,
    'updated_at': d.updated_at
}
FROM drawings d WITH INSERT UPDATE DELETE;

-- =====================================================
-- PRIZES DUALITY VIEW
-- =====================================================
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW prizes_dv AS
SELECT JSON {
    '_id': p.id,
    'drawing_id': p.drawing_id,
    'sponsor_id': p.sponsor_id,
    'rank': p.rank,
    'name': p.name,
    'description': p.description,
    'value_usd': p.value_usd,
    'quantity': p.quantity,
    'fulfillment_type': p.fulfillment_type,
    'image_url': p.image_url,
    'created_at': p.created_at,
    'updated_at': p.updated_at
}
FROM prizes p WITH INSERT UPDATE DELETE;

-- =====================================================
-- TICKETS DUALITY VIEW
-- =====================================================
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW tickets_dv AS
SELECT JSON {
    '_id': t.id,
    'drawing_id': t.drawing_id,
    'user_id': t.user_id,
    'ticket_number': t.ticket_number,
    'purchase_transaction_id': t.purchase_transaction_id,
    'is_winner': CASE WHEN t.is_winner = 1 THEN TRUE ELSE FALSE END,
    'prize_id': t.prize_id,
    'created_at': t.created_at,
    'updated_at': t.updated_at
}
FROM tickets t WITH INSERT UPDATE DELETE;

-- =====================================================
-- PRIZE_FULFILLMENTS DUALITY VIEW
-- =====================================================
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW prize_fulfillments_dv AS
SELECT JSON {
    '_id': pf.id,
    'ticket_id': pf.ticket_id,
    'prize_id': pf.prize_id,
    'user_id': pf.user_id,
    'status': pf.status,
    'shipping_address': pf.shipping_address,
    'tracking_number': pf.tracking_number,
    'carrier': pf.carrier,
    'notes': pf.notes,
    'notified_at': pf.notified_at,
    'address_confirmed_at': pf.address_confirmed_at,
    'shipped_at': pf.shipped_at,
    'delivered_at': pf.delivered_at,
    'forfeit_at': pf.forfeit_at,
    'created_at': pf.created_at,
    'updated_at': pf.updated_at
}
FROM prize_fulfillments pf WITH INSERT UPDATE DELETE;

-- =====================================================
-- COMPOSITE VIEWS (Read-only for complex queries)
-- =====================================================

-- User with Profile (for user-facing queries)
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW user_profile_dv AS
SELECT JSON {
    '_id': u.id,
    'email': u.email,
    'status': u.status,
    'role': u.role,
    'point_balance': u.point_balance,
    'profile': (
        SELECT JSON {
            'display_name': p.display_name,
            'tier_code': p.tier_code,
            'age_bracket': p.age_bracket,
            'fitness_level': p.fitness_level
        }
        FROM profiles p WITH NOINSERT NOUPDATE NODELETE
        WHERE p.user_id = u.id
    ),
    'created_at': u.created_at
}
FROM users u WITH NOINSERT NOUPDATE NODELETE;

-- Drawing with Prizes (for drawing detail view)
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW drawing_details_dv AS
SELECT JSON {
    '_id': d.id,
    'drawing_type': d.drawing_type,
    'name': d.name,
    'description': d.description,
    'ticket_cost_points': d.ticket_cost_points,
    'drawing_time': d.drawing_time,
    'ticket_sales_close': d.ticket_sales_close,
    'status': d.status,
    'total_tickets': d.total_tickets,
    'prizes': [
        SELECT JSON {
            '_id': p.id,
            'rank': p.rank,
            'name': p.name,
            'value_usd': p.value_usd,
            'quantity': p.quantity,
            'fulfillment_type': p.fulfillment_type
        }
        FROM prizes p WITH NOINSERT NOUPDATE NODELETE
        WHERE p.drawing_id = d.id
        ORDER BY p.rank
    ]
}
FROM drawings d WITH NOINSERT NOUPDATE NODELETE;

-- User Tickets with Drawing Info (for user ticket history)
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW user_tickets_dv AS
SELECT JSON {
    '_id': t.id,
    'user_id': t.user_id,
    'ticket_number': t.ticket_number,
    'is_winner': CASE WHEN t.is_winner = 1 THEN TRUE ELSE FALSE END,
    'drawing': (
        SELECT JSON {
            '_id': d.id,
            'name': d.name,
            'drawing_type': d.drawing_type,
            'drawing_time': d.drawing_time,
            'status': d.status
        }
        FROM drawings d WITH NOINSERT NOUPDATE NODELETE
        WHERE d.id = t.drawing_id
    ),
    'created_at': t.created_at
}
FROM tickets t WITH NOINSERT NOUPDATE NODELETE;

-- Fulfillment Details (for admin fulfillment management)
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW fulfillment_details_dv AS
SELECT JSON {
    '_id': pf.id,
    'status': pf.status,
    'shipping_address': pf.shipping_address,
    'tracking_number': pf.tracking_number,
    'carrier': pf.carrier,
    'user': (
        SELECT JSON {
            '_id': u.id,
            'email': u.email
        }
        FROM users u WITH NOINSERT NOUPDATE NODELETE
        WHERE u.id = pf.user_id
    ),
    'prize': (
        SELECT JSON {
            '_id': p.id,
            'name': p.name,
            'fulfillment_type': p.fulfillment_type,
            'value_usd': p.value_usd
        }
        FROM prizes p WITH NOINSERT NOUPDATE NODELETE
        WHERE p.id = pf.prize_id
    ),
    'created_at': pf.created_at,
    'updated_at': pf.updated_at
}
FROM prize_fulfillments pf WITH NOINSERT NOUPDATE NODELETE;

COMMIT;
