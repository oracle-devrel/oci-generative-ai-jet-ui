CREATE OR REPLACE FUNCTION HF_OWNER.HF_READ_AUDIT RETURN CLOB AUTHID DEFINER IS
 result CLOB;
 identity_name VARCHAR2(100):=SYS_CONTEXT('USERENV','AUTHENTICATED_IDENTITY');
 memory_schema VARCHAR2(100);
BEGIN
 memory_schema:=CASE identity_name WHEN 'hf_credit' THEN 'HF_CREDIT_MEM' WHEN 'hf_markets' THEN 'HF_MARKETS_MEM' ELSE '--unauthorized--' END;
 SELECT JSON_ARRAYAGG(JSON_OBJECT('event_timestamp' VALUE TO_CHAR(event_timestamp,'YYYY-MM-DD HH24:MI:SS.FF3'),'dbusername' VALUE dbusername,'end_user_name' VALUE end_user_name,'action_name' VALUE action_name,'object_schema' VALUE object_schema,'object_name' VALUE object_name,'sql_text' VALUE sql_text,'return_code' VALUE return_code,'client_identifier' VALUE client_identifier) RETURNING CLOB)
 INTO result FROM (SELECT event_timestamp,dbusername,end_user_name,action_name,object_schema,object_name,sql_text,return_code,client_identifier
 FROM AUDSYS.UNIFIED_AUDIT_TRAIL WHERE client_identifier=SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER') AND (end_user_name=identity_name OR dbusername=memory_schema) AND (object_schema='HF_OWNER' OR object_schema=memory_schema)
 ORDER BY event_timestamp DESC FETCH FIRST 200 ROWS ONLY);
 RETURN NVL(result,'[]');
END;
/
GRANT EXECUTE ON HF_OWNER.HF_READ_AUDIT TO HF_CONNECT;
