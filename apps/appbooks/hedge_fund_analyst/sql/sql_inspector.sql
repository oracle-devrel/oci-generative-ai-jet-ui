CREATE OR REPLACE FUNCTION HF_OWNER.HF_READ_SQL RETURN CLOB AUTHID DEFINER IS result CLOB;
BEGIN
 SELECT JSON_ARRAYAGG(JSON_OBJECT('sql_id' VALUE sql_id,'sql_text' VALUE sql_text,'executions' VALUE executions,'rows_processed' VALUE rows_processed,'last_active_time' VALUE TO_CHAR(last_active_time,'YYYY-MM-DD HH24:MI:SS')) RETURNING CLOB)
 INTO result FROM (SELECT sql_id,sql_text,executions,rows_processed,last_active_time FROM SYS.V_$SQL WHERE INSTR(sql_text,'/* HF:')>0 AND command_type=3 ORDER BY last_active_time DESC FETCH FIRST 100 ROWS ONLY);
 RETURN NVL(result,'[]');
END;
/
GRANT EXECUTE ON HF_OWNER.HF_READ_SQL TO HF_CONNECT;
