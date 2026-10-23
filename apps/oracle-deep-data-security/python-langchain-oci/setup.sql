Rem
Rem $Header: setup.sql 17-jun-2026.09:59:51 tanisaga Exp $
Rem
Rem setup.sql
Rem
Rem Copyright (c) 2026, Oracle and/or its affiliates.
Rem
Rem   NAME
Rem   setup.sql - Database setup script for the OCI IAM LangChain HR demo
Rem 
Rem   DESCRIPTION
Rem   Configures the sample HR schema, OCI IAM authentication,
Rem   Deep Data Security data roles, and data grants required
Rem   for the OCI IAM LangChain HR demo.
Rem
Rem    NOTES
Rem    Update the environment-specific database connection
Rem    information, OCI IAM application identifiers, and
Rem    credentials before executing this script.
Rem
Rem    BEGIN SQL_FILE_METADATA
Rem    SQL_SOURCE_FILE: tkmain_3/tzfd/src/oci_iam_single_agent/setup.sql
Rem    SQL_SHIPPED_FILE:
Rem    SQL_PHASE:
Rem    SQL_STARTUP_MODE: NORMAL
Rem    SQL_IGNORABLE_ERRORS: NONE
Rem    SQL_CALLING_FILE:
Rem    END SQL_FILE_METADATA
Rem
Rem    MODIFIED   (MM/DD/YY)
Rem    tanisaga    06/17/26 - Created
Rem

SET ECHO ON
SET FEEDBACK 1
SET NUMWIDTH 10
SET LINESIZE 80
SET TRIMSPOOL ON
SET TAB OFF
SET PAGESIZE 100

REM SET ECHO OFF
REM SET FEEDBACK 1
REM SET NUMWIDTH 10
REM SET LINESIZE 80
REM SET TRIMSPOOL ON
REM SET TAB OFF
REM SET PAGESIZE 100
REM SET ECHO ON
define passwd=<sys_password>
define db_usr_passwd=<db_user_password>
define conn_str=<connect_string>
define nstempl_passwd=<nstempl_password>

----------------------------------------------------------------------
-- 1. Create Sample Employee and Manager Tables
----------------------------------------------------------------------

connect hr/hr@&conn_str;

CREATE TABLE hr.employee_records (
    employee_id   NUMBER PRIMARY KEY,
    employee_name VARCHAR2(100),
    email         VARCHAR2(250),
    salary        NUMBER,
    ssn           VARCHAR2(11),
    manager_id    NUMBER
);

INSERT INTO hr.employee_records VALUES
(101, 'Emma Baker', 'EmmaBaker', 90000, '841-11-4324', 102);

INSERT INTO hr.employee_records VALUES
(102, 'Marvin Greenberg', 'MarvinGreenberg', 120000, '166-46-3472', NULL);

INSERT INTO hr.employee_records VALUES
(103, 'Hannah Smith', 'HannahSmith', 150000, '798-13-9372', 102);

COMMIT;

connect sys/&passwd@&conn_str as sysdba

----------------------------------------------------------------------
-- 2. Create Connection Pool User
----------------------------------------------------------------------
create user db_usr identified by &db_usr_passwd;
grant connect to db_usr;
grant CREATE END USER SECURITY CONTEXT to db_usr;

----------------------------------------------------------------------
-- 3. Create OCI IAM Deep Data Security Roles
----------------------------------------------------------------------
create or replace data role employee_role mapped to
'iam_oauth_group=Employee';

create or replace data role manager_role mapped to
'iam_oauth_group=Manager';

----------------------------------------------------------------------
-- 4. Configure OCI IAM Authentication
----------------------------------------------------------------------
ALTER SYSTEM SET IDENTITY_PROVIDER_TYPE=OCI_IAM SCOPE=BOTH;
ALTER SYSTEM SET IDENTITY_PROVIDER_OAUTH_CONFIG=
'{
  "app_id":"6****c",
  "domain_url":"https://idcs-7****.identity.oraclecloud.com:443"
}';
exec DBMS_CREDENTIAL.DROP_CREDENTIAL('OCI_IAM_DOMAIN_DB_CRED$');

BEGIN
DBMS_CREDENTIAL.CREATE_CREDENTIAL(
'OCI_IAM_DOMAIN_DB_CRED$',
'7****0',
'idcscs-******5'
);
END;
/

----------------------------------------------------------------------
-- 5. Create Deep Data Security Grants
----------------------------------------------------------------------

-- Employees can access their own records.
CREATE OR REPLACE DATA GRANT emp_self AS
SELECT
ON hr.employee_records
WHERE email = ORA_END_USER_CONTEXT.USERNAME
TO employee_role;

-- Managers can access records for their direct reports.
CREATE OR REPLACE DATA GRANT mgr_hierarchy AS
SELECT (ALL COLUMNS EXCEPT ssn)
ON hr.employee_records
WHERE manager_id =
(
    SELECT employee_id
    FROM hr.employee_records
    WHERE email = ORA_END_USER_CONTEXT.USERNAME
)
OR email = ORA_END_USER_CONTEXT.USERNAME
TO manager_role;

----------------------------------------------------------------------
-- 6. Create Database Role
----------------------------------------------------------------------

create role dbrole1;
grant create session to dbrole1;
-- grant dbrole1 to employee_fs_role,employee_fs_v1_role,employee_fs_role_iam1,employee_fs_role_iam3,manager_fs_role_iam,manager_fs_role_iam2,employee_fs_v2_role;
grant dbrole1 to employee_role;
grant dbrole1 to manager_role;

----------------------------------------------------------------------
-- 7. Create End User Context Callback Package
----------------------------------------------------------------------
-- Create DB user that owns the end user context callback package
create user nstempl identified by &nstempl_passwd;
grant create session, resource, unlimited tablespace to nstempl;


connect nstempl/&nstempl_passwd@&conn_str
-- Create sample package for the  end user context callback
create or replace package nstempl.TESTPACKAGE AUTHID current_user as
  PROCEDURE testcb;
end testpackage;
/
show errors
 
-- Create package body for the end user context callback
-- The callback instantiate context attribute value on first read
CREATE OR REPLACE PACKAGE BODY nstempl.testpackage AS
   PROCEDURE testcb IS
      sql_stmt VARCHAR2(4000);
   BEGIN
      DBMS_OUTPUT.PUT_LINE('instantiation callback');
      sql_stmt := 'UPDATE END_USER_CONTEXT SET END_USER_CONTEXT.CONTEXT.p3 = 9876543 WHERE owner = ''EUC'' AND name = ''HCM''';
      EXECUTE IMMEDIATE sql_stmt;
   EXCEPTION
      WHEN OTHERS THEN
         DBMS_OUTPUT.PUT_LINE('Error executing UPDATE: ' || SQLERRM);
         RAISE;
   END testcb;
END testpackage;
/
show errors
 
grant execute on nstempl.TESTPACKAGE to dbrole1;
 
conn sys/&passwd@&conn_str as sysdba
----------------------------------------------------------------------
-- 8. Create End User Context
----------------------------------------------------------------------

create user euc identified by <euc_password>;
drop end user context euc.hcm;
CREATE END USER CONTEXT euc.hcm USING JSON SCHEMA '{
    "type": "object",
    "properties": {
         "p1": {
            "type": "integer",
            "default": 123
         },
         "p2": {
            "type": "string",
            "default": "abc"
         },
         "p3": {
            "type": "integer",
            "o:onFirstRead": "nstempl.TESTPACKAGE.testcb"
         },
         "p4": {
            "type": "string",
            "o:onFirstRead": "nstempl.TESTPACKAGE.testcb"
         }
    }
}';

-- Grant privilege to update EUC to end users
grant update any end user context to dbrole1;

-- Grant privilege to select EUC to end users
create or replace data grant EUC.HCM_GRANT AS
SELECT on
SYS.END_USER_CONTEXT
where OWNER = 'EUC' and NAME = 'HCM'
-- to employee_fs_role, employee_fs_role_iam1,employee_fs_role_iam3, manager_fs_role_iam,manager_fs_role_iam2,employee_fs_v1_role, employee_fs_v2_role;
to employee_role, manager_role;


