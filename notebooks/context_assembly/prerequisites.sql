-- Administrator reference only. Replace DEMO_OWNER with the intended non-SYS owner.
-- Run grants only if missing; the notebook never grants privileges itself.
GRANT CREATE SESSION, CREATE TABLE, CREATE PROCEDURE TO DEMO_OWNER;
GRANT CREATE ANY CONTEXT TO DEMO_OWNER;
GRANT EXECUTE ON SYS.DBMS_RLS TO DEMO_OWNER;
GRANT EXECUTE ON SYS.DBMS_FLASHBACK TO DEMO_OWNER;
-- Supply quota on the demo owner's tablespace, Oracle Text and vector privileges
-- appropriate to the target environment. Do not grant EXEMPT ACCESS POLICY.
