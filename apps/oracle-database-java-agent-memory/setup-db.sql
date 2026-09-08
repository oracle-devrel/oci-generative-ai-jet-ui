GRANT RESOURCE TO pdbadmin;
GRANT CTXAPP TO pdbadmin;
GRANT CREATE MINING MODEL TO pdbadmin;
GRANT UNLIMITED TABLESPACE TO pdbadmin;

-- Create directory for ONNX model file (requires sysdba)
CREATE OR REPLACE DIRECTORY DM_DUMP AS '/opt/oracle/dumps';
GRANT READ, WRITE ON DIRECTORY DM_DUMP TO pdbadmin;

EXIT;
