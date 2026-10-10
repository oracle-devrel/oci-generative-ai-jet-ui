-- Administrator grants for the existing user configured as DB_USER.
-- Connect to the same PDB/service used by the notebook before running this script.
-- This script does not create users or tablespaces or restart the database.
WHENEVER SQLERROR EXIT SQL.SQLCODE
SET ECHO OFF VERIFY OFF
ACCEPT notebook_user CHAR PROMPT 'Existing notebook username (DB_USER): '
GRANT CREATE SESSION, CREATE TABLE, CREATE PROCEDURE, CREATE MINING MODEL,
  CTXAPP TO &notebook_user;
GRANT CREATE ANY CONTEXT TO &notebook_user;
GRANT EXECUTE ON SYS.DBMS_RLS TO &notebook_user;
GRANT EXECUTE ON SYS.DBMS_FLASHBACK TO &notebook_user;
GRANT EXECUTE ON SYS.DBMS_VECTOR TO &notebook_user;
-- Ensure sufficient quota on the user's existing default tablespace.
-- If needed, an administrator can grant quota, substituting that tablespace:
-- ALTER USER &notebook_user QUOTA 1G ON <existing_default_tablespace>;
-- The user must be non-SYS and must not have EXEMPT ACCESS POLICY.
-- Configure vector memory separately if needed; see the notebook's local setup.
UNDEFINE notebook_user
EXIT
