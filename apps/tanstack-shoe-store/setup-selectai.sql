-- ===========================================
-- Configure Select AI with Anthropic
-- Run as SHOESTORE user after seed data is loaded
-- ===========================================

-- Create credential for Anthropic
BEGIN
  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => 'ANTHROPIC_CRED',
    username        => 'ANTHROPIC',
    password        => '<your-anthropic-api-key>'
  );
END;
/

-- Create AI profile pointing at our tables
BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => 'SHOESTORE_AI',
    attributes   => '{
      "provider": "anthropic",
      "credential_name": "ANTHROPIC_CRED",
      "object_list": [
        {"owner": "SHOESTORE", "name": "PRODUCTS"},
        {"owner": "SHOESTORE", "name": "CUSTOMERS"},
        {"owner": "SHOESTORE", "name": "TRANSACTIONS"}
      ],
      "model": "claude-sonnet-4-20250514"
    }'
  );
END;
/

-- Verify it works
SELECT DBMS_CLOUD_AI.GENERATE(
  prompt       => 'how many products do we have',
  profile_name => 'SHOESTORE_AI',
  action       => 'narrate'
) FROM DUAL;
