"""Load the embedding model and an exported BGE reranker when absent."""
import json,os,urllib.request
from pathlib import Path
import oracledb
oracledb.defaults.program='devrel-developerhub-context-assembly-for-agent-memory'
from store import load_config

def ensure_models():
    cfg=load_config()
    with oracledb.connect(user=cfg['DB_USER'],password=cfg['DB_PASSWORD'],dsn=cfg['DB_DSN']) as conn,conn.cursor() as cur:
        models=[('ALL_MINILM_L12_V2',{'function':'embedding','embeddingOutput':'embedding','input':{'input':['DATA']}}),('BGE_RERANKER',{'function':'regression','regressionOutput':'output'})]
        result=[]
        for name,metadata in models:
            cur.execute('SELECT COUNT(*) FROM user_mining_models WHERE model_name=:n',n=name)
            if not cur.fetchone()[0]:
                if name=='ALL_MINILM_L12_V2':
                    url='https://objectstorage.us-ashburn-1.oraclecloud.com/n/adwc4pm/b/OML-Resources/o/all_MiniLM_L12_v2.onnx'
                    with urllib.request.urlopen(url,timeout=600) as response:data=response.read()
                else:
                    path=os.getenv('RERANKER_ONNX_FILE')
                    if not path:raise RuntimeError('Export BAAI/bge-reranker-base with OML4Py, then set RERANKER_ONNX_FILE. See README model prerequisites.')
                    data=Path(path).read_bytes()
                blob=conn.createlob(oracledb.DB_TYPE_BLOB);blob.write(data)
                cur.execute('BEGIN DBMS_VECTOR.LOAD_ONNX_MODEL(:name,:data,JSON(:meta)); END;',name=name,data=blob,meta=json.dumps(metadata))
            cur.execute('SELECT mining_function,creation_date FROM user_mining_models WHERE model_name=:n',n=name);function,created=cur.fetchone()
            result.append({'model':name,'function':function,'created':created.isoformat()})
        cur.execute("SELECT VECTOR_DIMENSION_COUNT(VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING 'memory' AS DATA)) FROM dual");assert cur.fetchone()[0]==384
        cur.execute("SELECT PREDICTION(BGE_RERANKER USING 'memory' AS FIRST_INPUT,'memory' AS SECOND_INPUT) FROM dual");assert cur.fetchone()[0] is not None
        return result
