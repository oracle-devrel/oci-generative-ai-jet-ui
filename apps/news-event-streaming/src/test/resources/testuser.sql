alter session set container = freepdb1;

-- Create app user
create user testuser identified by testpwd quota unlimited on users;
grant connect, resource to testuser;

-- Grants for the Kafka Java Client for Oracle AI Database Transactional Event Queues
grant aq_user_role to testuser;
grant execute on dbms_aq to  testuser;
grant execute on dbms_aqadm to testuser;
grant select on gv_$session to testuser;
grant select on v_$session to testuser;
grant select on gv_$instance to testuser;
grant select on gv_$listener_network to testuser;
grant select on sys.dba_rsrc_plan_directives to testuser;
grant select on gv_$pdbs to testuser;
grant select on user_queue_partition_assignment_table to testuser;
exec dbms_aqadm.grant_priv_for_rm_plan('testuser');
commit;

