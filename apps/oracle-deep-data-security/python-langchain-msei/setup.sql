Rem
Rem $Header: setup.sql 14-may-2026.13:40:55 tanisaga Exp $
Rem
Rem setup.sql
Rem
Rem Copyright (c) 2026, Oracle and/or its affiliates.
Rem
Rem    NAME
Rem      setup.sql - Setup script for 
Rem      LangChain Agent Sample HR application
Rem
Rem    DESCRIPTION
Rem      Creates sample employee and manager tables, sample users,
Rem      data roles, and Deep Data Security grants required for the
Rem      LangChain Agent Sample HR application.
Rem
Rem    NOTES
Rem      Update Azure application identifiers, database credentials,
Rem      users, and tenant details before execution.
Rem
Rem    BEGIN SQL_FILE_METADATA
Rem    SQL_SOURCE_FILE: tkmain_3/tzfd/src/setup.sql
Rem    SQL_SHIPPED_FILE:
Rem    SQL_PHASE:
Rem    SQL_STARTUP_MODE: NORMAL
Rem    SQL_IGNORABLE_ERRORS: NONE
Rem    SQL_CALLING_FILE:
Rem    END SQL_FILE_METADATA
Rem
Rem    MODIFIED   (MM/DD/YY)
Rem    tanisaga    05/14/26 - Created
Rem


SET ECHO ON
SET FEEDBACK 1
SET NUMWIDTH 10
SET LINESIZE 80
SET TRIMSPOOL ON
SET TAB OFF
SET PAGESIZE 100

define passwd=<sys_password>
define db_usr_passwd=<db_password>
define conn_str=<connection_string>

---

## -- 1. Create Sample Employee and Manager Tables

connect hr/hr@&conn_str;

CREATE TABLE hr.employee_records (
employee_id NUMBER PRIMARY KEY,
employee_name VARCHAR2(100),
email VARCHAR2(250),
salary NUMBER,
phone VARCHAR2(30)
);

CREATE TABLE hr.manager_records (
manager_id NUMBER PRIMARY KEY,
employee_id NUMBER,
manager_name VARCHAR2(100),
CONSTRAINT fk_employee
FOREIGN KEY (employee_id)
REFERENCES hr.employee_records(employee_id)
);

-- Insert sample employee records
-- Ensure EMAIL matches the UPN/email configured in your Entra ID app

INSERT INTO hr.employee_records VALUES
(101, 'Emma Baker',
'[emma.baker@example.com](mailto:emma.baker@example.com)',
90000,
'111-111-1111');

INSERT INTO hr.employee_records VALUES
(102, 'Marvin Greenberg',
'[marvin.greenberg@example.com](mailto:marvin.greenberg@example.com)',
120000,
'222-222-2222');

INSERT INTO hr.employee_records VALUES
(103, 'Hannah Smith',
'[hannah.smith@example.com](mailto:hannah.smith@example.com)',
150000,
'333-333-3333');

-- Insert sample manager mappings

INSERT INTO hr.manager_records VALUES
(1, 101, 'Marvin Greenberg');

INSERT INTO hr.manager_records VALUES
(2, 102, 'Hannah Smith');

COMMIT;

---

## -- 2. Create Connection Pool User and Data Roles

connect sys/&passwd@&conn_str as sysdba

drop user IF EXISTS db_usr cascade;

create user db_usr identified by &db_usr_passwd;

grant connect to db_usr;

grant CREATE END USER SECURITY CONTEXT to db_usr;

-- Replace values below with your Azure application details

create or replace data role EMPLOYEE_FS_ROLE
mapped to
'azure_role=<employee_role>';

create or replace data role MANAGER_FS_ROLE
mapped to
'azure_role=<manager_role>';

---

## -- 3. Identity Provider Configuration
-- Refer to the quick-start guide present in the ReadME.


## -- 4. Deep Data Security Grants

CREATE OR REPLACE DATA GRANT hr.gnt1 AS
SELECT (ALL COLUMNS EXCEPT salary)
ON hr.employee_records
WHERE 1=1
TO EMPLOYEE_FS_ROLE;

CREATE OR REPLACE DATA GRANT hr.gnt2 AS
SELECT ON hr.employee_records
WHERE UPPER(email) = UPPER(ORA_END_USER_CONTEXT.username)
TO EMPLOYEE_FS_ROLE;

CREATE OR REPLACE DATA GRANT hr.gnt3 AS
SELECT ON hr.employee_records
WHERE employee_id IN (
SELECT employee_id
FROM hr.manager_records
)
TO MANAGER_FS_ROLE;
