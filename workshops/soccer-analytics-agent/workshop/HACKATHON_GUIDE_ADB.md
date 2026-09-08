# 🏆 HACK THE WORLD CUP 2026: Complete Hackathon Guide

**Stack**: Oracle Cloud (OCI) + Oracle AI Autonomous Database + APEX + Oracle ML + Select AI (GenAI)
**Budget**: $300 USD Oracle Academy credits (~$15 actual usage)
**Data**: 48,944 matches | 44,569 goals | 666 shootouts | Historical 1872-2024

---

## QUICK START

### Available CSV Files
1. **results.csv** - 48,944 international matches (1872-2024)
2. **goalscorers.csv** - 44,569 goal records
3. **shootouts.csv** - 666 penalty shootout results
4. **former_names.csv** - 35 country name changes

### Time Allocation
- Week 1: Levels 1-2 (Setup + Data)
- Week 2: Levels 3-4 (Analytics + APEX)
- Week 3: Level 5 (Machine Learning)
- Week 4: Level 6 + Bonus + Polish

---

## 🎯 LEVEL 1: INFRASTRUCTURE (2 hours, $0)

### Objective
Deploy Oracle AI Autonomous Database on OCI

### Steps

1. **Create OCI Account**
   - Visit: https://www.oracle.com/cloud/free/
   - Register with university email
   - Claim Oracle Academy $300 credits

2. **Deploy Autonomous Database**
   ```
   Navigation: Oracle AI Database → Autonomous AI Database → Create Autonomous AI Database

   Configuration:
   - Display Name: WorldCupDB
   - Database Name: WorldCupDB
   - Compartment: Select any department or root
   - Workload type: Lakehouse
   - Choose database version: 26ai
   - OCPU: 1 (Always Free) - Be sure you have 26ai, otherwise, don't select Always Free
   - Storage: 20GB
   - Admin Password: [Strong password - save this!] WorldCupDB1234
   - Network: Secure access from everywhere
   ```

3. **Download Wallet**
   - Click "DB Connection" → "Download client credentilas (Wallet)"
   - Save Wallet_WorldCupDB.zip
   - Extract to secure location

4. **Access Database**
   - Click "Database actions" → "SQL"
   - Login as ADMIN
   - Test: `SELECT SYSDATE FROM DUAL;`

5. **Create Schema**
   ```sql
   CREATE USER worldcup IDENTIFIED BY "YourPassword123#";
   GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO worldcup;
   GRANT CREATE VIEW, CREATE SESSION TO worldcup;
   GRANT DWROLE TO worldcup;
   ```

6. **REST Enablement**
Access to Database Users:
- Look for WORLDCUP - Enable REST
- Authorization Required - REST Enable User


### ✅ Deliverables
- Screenshot of active ADB
- Connection test proof
- Credentials document

---

## 📊 LEVEL 2: DATA ENGINEERING (3 hours, $0.50)

### Objective

Load football data and create analytical views

### Load Data

**Method: Database Actions Data Load Tool**

1. Connect as WORLDCUP user
2. Database Actions → Data Studio - Data Load
3. Load Data
4. Select Files → results.csv → Edit
5. Check:
    - Create Table - MATCH_RESUTLS
    - Date format is YYYY-MM-DD - Close
7. Repeat for shootouts.csv and goalscorers.csv
8. For goalscorers mapping:
    - Change minutes from number to Varchar2 - Close
8. Start → Run


### Create Indixes

1. Connect as WORLDCUP user
2. Database Actions → SQL

```sql
CREATE INDEX idx_results_date ON match_results(date_rw);
CREATE INDEX idx_results_teams ON match_results(home_team, away_team);
CREATE INDEX idx_goalscorers_scorer ON goalscorers(scorer);
```

### Create Analytical Views

```sql
-- View 1: Competitive matches only
CREATE OR REPLACE FORCE EDITIONABLE VIEW "VW_COMPETITIVE_MATCHES" ("DATE_RW", "HOME_TEAM", "AWAY_TEAM", "HOME_SCORE", "AWAY_SCORE", "TOURNAMENT", "CITY", "COUNTRY", "NEUTRAL", "WINNER") AS
  SELECT
    m."DATE_RW",m."HOME_TEAM",m."AWAY_TEAM",m."HOME_SCORE",m."AWAY_SCORE",m."TOURNAMENT",m."CITY",m."COUNTRY",m."NEUTRAL",
    CASE
        WHEN home_score > away_score THEN home_team
        WHEN away_score > home_score THEN away_team
        ELSE 'Draw'
    END AS winner
FROM match_results m
WHERE tournament IN (
    'FIFA World Cup')
AND date_rw >= DATE '1950-01-01';

-- View 2: Team statistics
CREATE OR REPLACE VIEW vw_team_statistics AS
WITH team_matches AS (
    SELECT home_team AS team,
           CASE WHEN home_score > away_score THEN 1 ELSE 0 END AS wins,
           home_score AS goals_for, away_score AS goals_against
    FROM vw_competitive_matches
    UNION ALL
    SELECT away_team AS team,
           CASE WHEN away_score > home_score THEN 1 ELSE 0 END AS wins,
           away_score AS goals_for, home_score AS goals_against
    FROM vw_competitive_matches
)
SELECT
    team,
    COUNT(*) AS total_matches,
    SUM(wins) AS total_wins,
    ROUND(SUM(wins) * 100.0 / COUNT(*), 2) AS win_percentage,
    SUM(goals_for) AS total_goals_scored,
    SUM(goals_for) - SUM(goals_against) AS goal_difference
FROM team_matches
GROUP BY team;

-- View 3: 2026 Venues
CREATE TABLE wc2026_venues (
    venue_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    venue_name VARCHAR2(200),
    city VARCHAR2(100),
    country VARCHAR2(50),
    latitude NUMBER(10,6),
    longitude NUMBER(10,6),
    altitude_meters NUMBER
);

INSERT INTO wc2026_venues
  (venue_name, city, country, latitude, longitude, altitude_meters)
VALUES
  ('Estadio Azteca', 'Mexico City', 'Mexico', 19.302969, -99.150635, 2240),
  ('SoFi Stadium', 'Los Angeles', 'USA', 33.953467, -118.339038, 30),
  ('MetLife Stadium', 'New York', 'USA', 40.813611, -74.074444, 3);
```

### ✅ Deliverables
- 48,944 matches loaded
- 4+ analytical views
- Data quality report

---

## 🔍 LEVEL 3: BUSINESS INTELLIGENCE (4 hours, $0.25)

### Required: 5 Complex SQL Queries

**Query 1: Spain's High-Temperature Performance**
```sql
WITH spain_matches AS (
    SELECT
        CASE
            WHEN (home_team = 'Spain' AND home_score > away_score) OR
                 (away_team = 'Spain' AND away_score > home_score) THEN 1
            ELSE 0
        END AS is_win
    FROM match_results
    WHERE (home_team = 'Spain' OR away_team = 'Spain')
)
SELECT
    COUNT(*) AS total_matches,
    SUM(is_win) AS wins,
    ROUND(SUM(is_win) * 100.0 / COUNT(*), 2) AS win_percentage
FROM spain_matches;
```

**Query 2: Top World Cup Scorers**
```sql
SELECT
    g.scorer,
    COUNT(*) AS total_goals,
    COUNT(DISTINCT g.DATE_RW) AS matches_played,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT g.date_rw), 2) AS goals_per_match
FROM goalscorers g
JOIN match_results m ON g.DATE_RW = m.DATE_RW
WHERE m.tournament = 'FIFA World Cup'
  AND g.own_goal = 'FALSE'
GROUP BY g.SCORER
ORDER BY total_goals DESC
FETCH FIRST 10 ROWS ONLY;
```

**Query 3: Home Advantage Analysis**
```sql
SELECT
    CASE WHEN neutral = 'TRUE' THEN 'Neutral' ELSE 'Home' END AS venue_type,
    COUNT(*) AS matches,
    SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) AS home_wins,
    ROUND(SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS home_win_pct
FROM vw_competitive_matches
GROUP BY CASE WHEN neutral = 'TRUE' THEN 'Neutral' ELSE 'Home' END;
```

**Query 4: Penalty Shootout Masters**
```sql
SELECT
    winner AS team,
    COUNT(*) AS shootout_wins,
    ROUND(COUNT(*) * 100.0 / (
        SELECT COUNT(*) FROM shootouts
        WHERE home_team = winner OR away_team = winner
    ), 2) AS win_rate
FROM shootouts
GROUP BY winner
ORDER BY shootout_wins DESC
FETCH FIRST 10 ROWS ONLY;
```

**Query 5: Tournament Evolution**
```sql
SELECT
    TRUNC(EXTRACT(YEAR FROM date_rw) / 10) * 10 AS decade,
    COUNT(*) AS matches,
    ROUND(AVG(home_score + away_score), 2) AS avg_goals_per_match
FROM match_results
WHERE tournament = 'FIFA World Cup'
GROUP BY TRUNC(EXTRACT(YEAR FROM date_rw) / 10) * 10
ORDER BY decade;
```

### ✅ Deliverables
- 5+ complex queries with different techniques
- Analysis report with insights

---

## 🎨 LEVEL 4: APEX DASHBOARD (5 hours, $0.50)

### Access APEX
1. ADB Console → Tool configuration → Copy Public access URL
2. Log in as ADMIN
3. Create Workspace → Create Workspace from Existing Schema:
 - Database User: WORLDCUP
 - Workspace Name: WORLDCUP_WS
 - Workspace Username: WORLDCUP_WS_USER
 - Workspace Password: "YourPassword123#"
4. Create Workspace
5. Login to workspace
6. Sign in as WORLDCUP_WS workspace and WORLDCUP_WS_USER

### Create Application
1. App Builder → Create a New App
2. Name: "World Cup 2026 Analytics" → Create Application
3. Create Page:
   - Dashboard → Next → Name: Dashboard → Primary and 2 secondary charts → Create Page
4. Go back to Application 100 Tab
5. Create Page:
   - Interactive report → Next → Name: Team Browser → View Name: VW_TEAM_STATISTICS → Create Page
6. Go back to Application 100 Tab
7. Create Page:
   - Map → Next → Name: Venue Map → SQL Query:
   ```sql
    SELECT
    venue_name,
    city || ', ' || country AS location,
    latitude,
    longitude
    FROM wc2026_venues;
    ```
   → Next → Points → Geomery Column:LOCATION(Varchar2) → Create Page
8. Go back to Application 100 Tab
9. Create Page:
  - Interactive report → Next → Name: Match History → Table: MATCH_RESULTS → Create Page - Filter by FIFA

### Dashboard Page Components

**Region 1: Bar Chart - Matches Over Time**

1. Select Page: Dasboard
2. Chart 1
3. Title: Matches Over Time
4. Table Name: match_results

```sql
SELECT EXTRACT(YEAR FROM date_rw) AS year, COUNT(*) AS matches
FROM match_results
WHERE EXTRACT(YEAR FROM date_rw) >= 1950
AND TOURNAMENT = 'FIFA World Cup'
GROUP BY EXTRACT(YEAR FROM date_rw)
ORDER BY year;
```

**Region 2: Pie Chart - Top Teams**

1. Select Page: Dasboard
2. Chart 2
3. Title: Top Teams
4. Table Name: vw_team_statistics

```sql
SELECT team, total_wins
FROM vw_team_statistics
ORDER BY total_wins DESC
FETCH FIRST 10 ROWS ONLY;CREATE OR REPLACE FORCE EDITIONABLE VIEW "VW_COMPETITIVE_MATCHES" ("DATE_RW", "HOME_TEAM", "AWAY_TEAM", "HOME_SCORE", "AWAY_SCORE", "TOURNAMENT", "CITY", "COUNTRY", "NEUTRAL", "WINNER") AS
  SELECT m."DATE_RW",m."HOME_TEAM",m."AWAY_TEAM",m."HOME_SCORE",m."AWAY_SCORE",m."TOURNAMENT",m."CITY",m."COUNTRY",m."NEUTRAL",
    CASE
      WHEN home_score > away_score THEN home_team
      WHEN away_score > home_score THEN away_team
      ELSE 'Draw'
    END AS winner
FROM match_results m
WHERE tournament IN ('FIFA World Cup')
AND date_rw >= DATE '1950-01-01';
```

**Region 3: Bar Chart - Goalers**

1. Select Page: Dasboard
2. Chart 2
3. Title: Goalers
4. Table Name: match_results

```sql
SELECT SCORER, COUNT(1) GOAL
    FROM match_results mr,
         GOALSCORERS g
    where tournament = 'FIFA World Cup'
    AND MR.DATE_RW = G.DATE_RW
    AND MR.HOME_TEAM = G.HOME_TEAM
    AND OWN_GOAL ='FALSE'
    GROUP BY SCORER
    ORDER BY GOAL DESC;
```


### ✅ Deliverables
- Functional APEX app URL
- 4+ interactive pages
- Professional styling

---
# 🤖 LEVEL 5: MACHINE LEARNING WITH PYTHON USING ORACLE DATA SCIENCE (6 hours, $0.50)

## DETAILED IMPLEMENTATION USING PYTHON

### Objective
Train a machine learning model using Python (scikit-learn) to predict 2026 World Cup outcomes.

### Prerequisites
- Python 3.8+ installed locally
- Oracle Data Science
- Database wallet downloaded from Level 1

---

## Step 1: Setup Python Environment

OCI - Analytics & AI - Data Science
Create Project
Name: worldcup_ds
Create notebook session
Name: worldcup_nb
Create
Open
Python 3 (ipykernel)
Create Notebook

**Install Required Libraries:**

Python 3
```bash
# Install packages
!pip install pandas numpy scikit-learn oracledb matplotlib seaborn joblib
```

**Test Oracle Connection:**
```python
import oracledb


# Configure connection
username = "worldcup"
password = "YourPassword123#"
dsn = "your_connection_string"  # From tnsnames.ora


username = "worldcup"
password = "YourPassword123#"
dsn = "worldcupdb_high"  # From tnsnames.ora

connection = oracledb.connect(
    user=username,
    password=password,
    dsn=dsn,
    config_dir="./wallet",
    wallet_location="./wallet",
    wallet_password='WorldCupDB1234'
)
print("✅ Connected to Oracle!")
connection.close()
```

---

Execute `notebooks/world_cup_ml_tutorial.ipynb` to train the model and get the results.

---

## ✅ LEVEL 5 DELIVERABLES

### Python Scripts:
- [x] `extract_data.py` - Oracle extraction
- [x] `feature_engineering.py` - Feature creation
- [x] `train_model.py` - Model training
- [x] `predict_2026.py` - Generate predictions
- [x] `upload_to_oracle.py` - Database upload

### Outputs:
- [x] `models/best_model.pkl` - Trained model
- [x] `output/confusion_matrix.png` - Evaluation chart
- [x] `output/feature_importance.png` - Feature analysis

### Oracle Database:
- [x] `PREDICCIONES_FINAL` table (frozen, read-only)

### Requirements:
- ✅ Accuracy > 50%
- ✅ All classes predicted
- ✅ Probability scores included
- ✅ Predictions frozen for September

---

**Estimated Time**: 6-7 hours
**Cost**: ~$0.50 (database operations only)

✅ **Level 5 Complete with Python!**

---
# 🧠 LEVEL 6: GENERATIVE AI WITH ORACLE OCI (5 hours, $2)

## CURRENT WORKSHOP PATH: GROK 4 + LANGCHAIN ORACLEVS HYBRID RETRIEVAL

### Objective
The live workshop now uses Grok 4 through OCI Generative AI Inference plus Oracle AI Database as the memory and retrieval layer. After Level 5 creates `PREDICCIONES_FINAL`, run `scripts/load_langchain_vectors.py --reset` to build the `langchain-oracledb` `OracleVS` table `SOCCER_LANGCHAIN_DOCS` from prediction documents and football facts. The final chat should use `hybrid_retrieve` / startup hybrid grounding first, then use `vector_search` only as the semantic-only baseline or fallback.

### Why hybrid retrieval instead of semantic-only RAG?
- **Prediction evidence becomes retrievable knowledge** — cached XGBoost rows from `PREDICCIONES_FINAL` are converted into LangChain `Document` rows.
- **Hybrid beats plain similarity for demos** — keyword/team names plus vector similarity recover exact matchup evidence better than semantic-only fact search.
- **Oracle stays the vector store** — embeddings, OracleVS rows, Oracle Text/HYBRID VECTOR INDEX support, and relational source tables all live in the database.
- **Grok 4 composes the final answer** — the LLM sees hybrid evidence and tool results, then writes the user-facing explanation.

> Legacy Select AI / APEX instructions below are retained for the original hackathon guide, but the agent workshop path is Grok 4 + LangChain OracleVS hybrid retrieval.

---

## Step 1: Enable OCI Generative AI Service

### Check Service Availability

1. **Login to OCI Console** → https://cloud.oracle.com
2. **Navigate**: Analytics & AI → **Generative AI**
3. **Verify region availability**:
   - Available regions: US East (Ashburn), US West (Phoenix), UK South (London), Germany Central (Frankfurt)
   - If not available: Switch to available region or use Cohere fallback

### Create OCI API Keys for Authentication

1. **Navigate to User Settings**:
   - Click profile icon (top right) → **User Settings**
   - Use your own generated OCIDs/API keys. Never paste real secrets into this guide.

2. **Generate User API Key**:
   - Cloud
   - Identity & Security
   - Domains
   - Default
   - User Management
   - Select your user - in Default section
   - API Keys - Add API Keys
   - Select **Generate API Key Pair**
   - Click **Download Private Key** (save as `oci_api_key.pem`)
   - Click **Download Public Key** (optional, for reference)
   - Click **Add**

   Do not commit the generated API key, fingerprint, OCIDs, or private key. Store them in your local OCI config or `.env` only.

3. **Save Configuration Details**:
   ```
   [DEFAULT]
   user=ocid1.user.oc1..aaaaaa... [YOUR USER OCID]
   fingerprint=xx:xx:xx:xx:xx... [YOUR FINGERPRINT]
   tenancy=ocid1.tenancy.oc1..aaa... [YOUR TENANCY OCID]
   region=us-ashburn-1 [YOUR REGION]
   key_file=~/oci_api_key.pem [PATH TO PRIVATE KEY]
   ```
   - **Important**: Save all these values - you'll need them!

---


## Step 2: Configure Database Credentials for OCI

### Create OCI Credential in Autonomous Database

**Connect as ADMIN user**, then run:

```sql
-- Grant necessary privileges to worldcup user
GRANT EXECUTE ON DBMS_CLOUD TO worldcup;
GRANT EXECUTE ON DBMS_CLOUD_AI TO worldcup;
GRANT CREATE MINING MODEL TO worldcup;
```

**Switch to WORLDCUP user**, then create credential:

```sql
-- Method 1: Using API Key Authentication (Recommended)
BEGIN
  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => 'OCI_GENAI_CRED',
    user_ocid       => '<YOUR_USER_OCID>',
    tenancy_ocid    => '<YOUR_TENANCY_OCID>',
    private_key     => '<PASTE YOUR ENTIRE PRIVATE KEY HERE>',
    fingerprint     => 'aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99' -- Your fingerprint
  );
END;
/

-- Verify credential was created
SELECT credential_name, username
FROM user_credentials
WHERE credential_name = 'OCI_GENAI_CRED';
```


## Step 3: Configure Select AI with OCI Generative AI

### Using Meta Llama 3.3 (70B)

**Connect as WORLDCUP user**, then run:

```sql
-- Create AI profile with Meta Llama
BEGIN
  -- Drop existing profile if exists
  BEGIN
    DBMS_CLOUD_AI.DROP_PROFILE(
      profile_name => 'WORLDCUP_AI_PROFILE'
    );
  EXCEPTION
    WHEN OTHERS THEN NULL;
  END;

  -- Create new profile with OCI GenAI and Llama
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => 'WORLDCUP_AI_PROFILE',
    attributes   => JSON_OBJECT(
      'provider' VALUE 'oci',
      'credential_name' VALUE 'OCI_GENAI_CRED',
      'model' VALUE 'meta.llama-3.3-70b-instruct',  -- Most powerful Llama model
      'oci_apiformat' VALUE 'GENERIC',
      'object_list' VALUE JSON_ARRAY(
        JSON_OBJECT('owner' VALUE 'WORLDCUP', 'name' VALUE 'MATCH_RESULTS'),
        JSON_OBJECT('owner' VALUE 'WORLDCUP', 'name' VALUE 'GOALSCORERS'),
        JSON_OBJECT('owner' VALUE 'WORLDCUP', 'name' VALUE 'VW_TEAM_STATISTICS'),
        JSON_OBJECT('owner' VALUE 'WORLDCUP', 'name' VALUE 'SHOOTOUTS')
      ),
      'temperature' VALUE 0.1,  -- Lower = more deterministic SQL
      'max_tokens' VALUE 500
    )
  );

  DBMS_OUTPUT.PUT_LINE('✅ AI Profile created with Meta Llama 3.3 70B');
END;
/
```


### Verify Profile Creation

```sql
-- List all AI profiles
SELECT profile_name, status
FROM user_cloud_ai_profiles;
```

---

## Step 4: Test Select AI

### Enable Profile for Session

```sql
-- Set active AI profile
EXEC DBMS_CLOUD_AI.SET_PROFILE('WORLDCUP_AI_PROFILE');

```

### Test Queries

**Test 1: Simple Count Query**
```sql
SELECT AI "How many matches has Spain played?";

-- Expected: AI translates to SQL like:
-- SELECT COUNT(*) FROM match_results
-- WHERE home_team = 'Spain' OR away_team = 'Spain'
```

**Test 2: Statistical Query**
```sql
EXEC DBMS_CLOUD_AI.SET_PROFILE('WORLDCUP_AI_PROFILE');
SELECT AI "What is Spain's win percentage in competitive matches?";

-- Expected: Uses vw_team_statistics view
-- SELECT win_percentage FROM vw_team_statistics WHERE team = 'Spain'
```

**Test 3: Top Scorers**
```sql
EXEC DBMS_CLOUD_AI.SET_PROFILE('WORLDCUP_AI_PROFILE');
SELECT AI "Who are the top 5 goal scorers in World Cup history?";

-- Expected: Joins goalscorers with match_results, filters by tournament
```

**Test 4: Complex Aggregation**
```sql
EXEC DBMS_CLOUD_AI.SET_PROFILE('WORLDCUP_AI_PROFILE');
SELECT AI "Compare Spain's and Germany's performance in the last 20 years";

-- Expected: Multi-table query with date filtering and comparison
```

**Test 5: Head-to-Head**
```sql
EXEC DBMS_CLOUD_AI.SET_PROFILE('WORLDCUP_AI_PROFILE');
SELECT AI "What is the head-to-head record between Brazil and Argentina?";

-- Expected: Filters matches between these teams, counts wins/draws
```
---

## Step 5: Build APEX Chat Interface

### Create Chat Page in APEX

1. **Navigate to APEX**: Database Actions → APEX
2. **Create New Page**:
   - Page Type: **Blank Page**
   - Next
   - Page Name: "AI Football Assistant"


3. Create a Page Item called PROMPT of type Textarea and a button to submit the prompt.
4. Create a  Classic Report Region and Type as Function Body returning SQL Query. Enable Use Generic Column Names property and enter number of  columns in Generic Column Count.

5. Enter PL/SQL Function Body as follows. DBMS_CLOUD_AI.GENERATE returns the SQL query using SELECT AI.
  BEGIN
    IF :PROMPT IS NOT NULL THEN
        RETURN DBMS_CLOUD_AI.GENERATE(:PROMPT,
                              profile_name => 'OCI_GENAI');
     END IF;
   END;

6. In the Attributes tab of the Report region, set Heading Type as Column Names
7. When the page is run, you can ask a question and get a response from the database


## Optional Step : Enhance Table Metadata for Better AI

**Add helpful comments to tables/columns:**

```sql
-- Table comments
COMMENT ON TABLE match_results IS 'Historical international football match results from 1872 to present. Includes World Cups, regional tournaments, and qualifiers.';

COMMENT ON TABLE goalscorers IS 'Individual goal records showing who scored, when, and match context. Includes penalty and own goal indicators.';

-- Column comments (helps AI understand data)
COMMENT ON COLUMN match_results.home_score IS 'Number of goals scored by home team (non-negative integer)';
COMMENT ON COLUMN match_results.away_score IS 'Number of goals scored by away team (non-negative integer)';
COMMENT ON COLUMN match_results.neutral IS 'TRUE if match played at neutral venue, FALSE if home advantage';
COMMENT ON COLUMN match_results.tournament IS 'Official tournament name - FIFA World Cup, UEFA Euro, Copa America, etc';

-- This helps the LLM generate better SQL queries!
```

---

## ✅ LEVEL 6 DELIVERABLES

### Configuration:
- [x] OCI API keys configured
- [x] OCI_GENAI_CRED credential created
- [x] WORLDCUP_AI_PROFILE using Meta Llama 3.1
- [x] Select AI enabled and tested

### APEX Application:
- [x] Chat interface page created
- [x] Real-time AI responses working
- [x] Error handling implemented
- [x] Professional UI with styling

### Testing:
- [x] 5+ test queries successful
- [x] Simple queries (counts, filters)
- [x] Complex queries (joins, aggregations)
- [x] Prediction queries (ML results)
- [x] Comparison queries (team vs team)

### Documentation:
- [x] Screenshots of chat interface
- [x] Video demo (3-5 min)
- [x] Configuration steps documented
- [x] Sample questions list