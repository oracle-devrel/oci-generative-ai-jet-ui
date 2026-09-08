
import oracledb
import yaml
import requests
import zipfile
import io
import sys

# Configuration
ZIP_URL = "https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/VBRD9P8ZFWkKvnfhrWxkpPe8K03-JIoM5h_8EJyJcpE80c108fuUjg7R5L5O7mMZ/n/adwc4pm/b/OML-Resources/o/all_MiniLM_L12_v2_augmented.zip"
ONNX_FILENAME = "all_MiniLM_L12_v2.onnx"
MODEL_NAME = "ALL_MINILM_L12_V2"
DIRECTORY_NAME = "DATA_PUMP_DIR"

def get_db_connection():
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    return oracledb.connect(
        user=config["ORACLE_DB_USERNAME"],
        password=config["ORACLE_DB_PASSWORD"],
        dsn=config["ORACLE_DB_DSN"]
    )

def download_and_extract_model():
    print(f"📥 Downloading model from {ZIP_URL}...")
    response = requests.get(ZIP_URL)
    response.raise_for_status()
    
    print("📦 Extracting ONNX file...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # List files to find the exact name if needed, but we assume it matches
        for name in z.namelist():
            if name.endswith(".onnx"):
                print(f"   Found {name}")
                return z.read(name)
    raise ValueError("ONNX file not found in ZIP archive")

def upload_blob_to_db_file(conn, file_content):
    cursor = conn.cursor()
    
    # 1. Create Temp Table
    print("🛠️ Creating temporary table for upload...")
    try:
        cursor.execute("DROP TABLE TEMP_ONNX_UPLOAD PURGE")
    except oracledb.DatabaseError:
        pass
        
    cursor.execute("CREATE TABLE TEMP_ONNX_UPLOAD (id NUMBER, data BLOB)")
    
    # 2. Insert BLOB
    print(f"Tb Uploading {len(file_content)} bytes to database table...")
    blob_var = cursor.var(oracledb.DB_TYPE_BLOB)
    blob_var.setvalue(0, file_content)
    cursor.execute("INSERT INTO TEMP_ONNX_UPLOAD VALUES (1, :1)", [blob_var])
    conn.commit()
    
    # 3. Write to File using UTL_FILE
    print(f"💾 Writing blob to {DIRECTORY_NAME}/{ONNX_FILENAME}...")
    plsql = f"""
    DECLARE
        l_blob BLOB;
        l_file UTL_FILE.FILE_TYPE;
        l_buffer RAW(32767);
        l_amount BINARY_INTEGER := 32767;
        l_pos INTEGER := 1;
        l_len INTEGER;
    BEGIN
        SELECT data INTO l_blob FROM TEMP_ONNX_UPLOAD WHERE id = 1;
        l_len := DBMS_LOB.GETLENGTH(l_blob);
        l_file := UTL_FILE.FOPEN('{DIRECTORY_NAME}', '{ONNX_FILENAME}', 'wb', 32767);
        
        WHILE l_pos <= l_len LOOP
            IF l_pos + l_amount - 1 > l_len THEN
                l_amount := l_len - l_pos + 1;
            END IF;
            DBMS_LOB.READ(l_blob, l_amount, l_pos, l_buffer);
            UTL_FILE.PUT_RAW(l_file, l_buffer, TRUE);
            l_pos := l_pos + l_amount;
        END LOOP;
        
        UTL_FILE.FCLOSE(l_file);
    EXCEPTION
        WHEN OTHERS THEN
            IF UTL_FILE.IS_OPEN(l_file) THEN
                UTL_FILE.FCLOSE(l_file);
            END IF;
            RAISE;
    END;
    """
    cursor.execute(plsql)
    
    # 4. Cleanup Table
    cursor.execute("DROP TABLE TEMP_ONNX_UPLOAD PURGE")
    print("✅ File uploaded successfully.")

def load_onnx_model(conn):
    cursor = conn.cursor()
    print(f"🤖 Loading ONNX model '{MODEL_NAME}' via DBMS_VECTOR...")
    
    # Drop existing model if forced
    try:
        cursor.execute(f"BEGIN DBMS_VECTOR.DROP_ONNX_MODEL(model_name => '{MODEL_NAME}', force => true); END;")
    except oracledb.DatabaseError as e:
        print(f"   (Info: Drop failed or not needed: {e})")
        
    # Load Model
    cursor.execute(f"""
    BEGIN
        DBMS_VECTOR.LOAD_ONNX_MODEL(
            directory => '{DIRECTORY_NAME}',
            file_name => '{ONNX_FILENAME}',
            model_name => '{MODEL_NAME}',
            metadata  => JSON('{{
                "function": "embedding",
                "embeddingOutput": "embedding",
                "input": {{ "input": ["DATA"] }}
            }}')
        );
    END;
    """)
    print(f"✅ Model '{MODEL_NAME}' loaded successfully!")

def check_model_exists(conn):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT model_name FROM user_mining_models WHERE model_name = :1", [MODEL_NAME])
        result = cursor.fetchone()
        return result is not None
    except oracledb.DatabaseError as e:
        print(f"⚠️ Error checking model existence: {e}")
        return False

def ensure_model_loaded(conn=None, force_reload=False):
    """
    Checks if the model exists in the DB. If not, downloads and loads it.
    Returns True if model is ready, False otherwise.
    """
    should_close_conn = False
    if conn is None:
        try:
            conn = get_db_connection()
            should_close_conn = True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

    try:
        if not force_reload:
            print(f"🔍 Checking for existing model '{MODEL_NAME}' in Oracle DB...")
            if check_model_exists(conn):
                print(f"✅ Model '{MODEL_NAME}' already exists. Skipping download.")
                return True
            else:
                print(f"⚠️ Model '{MODEL_NAME}' not found. Initiating automatic setup...")

        onnx_content = download_and_extract_model()
        upload_blob_to_db_file(conn, onnx_content)
        load_onnx_model(conn)
        return True
    
    except Exception as e:
        print(f"❌ Error ensuring model loaded: {e}")
        return False
    finally:
        if should_close_conn:
            conn.close()

def main():
    try:
        conn = get_db_connection()
        print("🔌 Connected to Oracle DB")
        
        # Check if model already exists?
        # By default, use ensure_model_loaded logic which checks first
        success = ensure_model_loaded(conn, force_reload=True) # Keeping force=True for direct script execution as per likely intent of running THIS script directly
        
        if success:
             print("\n🎉 Success! Model is ready for use.")
        else:
             print("\n❌ Failed to load model.")
        
        conn.close()
        print("\n🎉 Success! Model is ready for use.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
