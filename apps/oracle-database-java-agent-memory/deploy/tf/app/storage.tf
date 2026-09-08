resource "time_static" "deploy_time" {}

resource "oci_objectstorage_bucket" "artifacts_bucket" {
  compartment_id = var.compartment_ocid
  name           = "artifacts_${local.project_name}${local.deploy_id}"
  namespace      = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
}

# --- Ansible playbook artifacts ---

resource "oci_objectstorage_object" "ansible_ops_artifact_object" {
  bucket      = oci_objectstorage_bucket.artifacts_bucket.name
  source      = data.archive_file.ansible_ops_artifact.output_path
  namespace   = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  object      = "ansible_ops_artifact.zip"
  content_md5 = data.archive_file.ansible_ops_artifact.output_md5
}

resource "oci_objectstorage_preauthrequest" "ansible_ops_artifact_par" {
  namespace    = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  bucket       = oci_objectstorage_bucket.artifacts_bucket.name
  name         = "ansible_ops_artifact_par"
  access_type  = "ObjectRead"
  object_name  = oci_objectstorage_object.ansible_ops_artifact_object.object
  time_expires = timeadd(time_static.deploy_time.rfc3339, "${var.artifacts_par_expiration_in_days * 24}h")
}

resource "oci_objectstorage_object" "ansible_backend_artifact_object" {
  bucket      = oci_objectstorage_bucket.artifacts_bucket.name
  source      = data.archive_file.ansible_backend_artifact.output_path
  namespace   = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  object      = "ansible_backend_artifact.zip"
  content_md5 = data.archive_file.ansible_backend_artifact.output_md5
}

resource "oci_objectstorage_preauthrequest" "ansible_backend_artifact_par" {
  namespace    = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  bucket       = oci_objectstorage_bucket.artifacts_bucket.name
  name         = "ansible_backend_artifact_par"
  access_type  = "ObjectRead"
  object_name  = oci_objectstorage_object.ansible_backend_artifact_object.object
  time_expires = timeadd(time_static.deploy_time.rfc3339, "${var.artifacts_par_expiration_in_days * 24}h")
}

resource "oci_objectstorage_object" "ansible_web_artifact_object" {
  bucket      = oci_objectstorage_bucket.artifacts_bucket.name
  source      = data.archive_file.ansible_web_artifact.output_path
  namespace   = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  object      = "ansible_web_artifact.zip"
  content_md5 = data.archive_file.ansible_web_artifact.output_md5
}

resource "oci_objectstorage_preauthrequest" "ansible_web_artifact_par" {
  namespace    = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  bucket       = oci_objectstorage_bucket.artifacts_bucket.name
  name         = "ansible_web_artifact_par"
  access_type  = "ObjectRead"
  object_name  = oci_objectstorage_object.ansible_web_artifact_object.object
  time_expires = timeadd(time_static.deploy_time.rfc3339, "${var.artifacts_par_expiration_in_days * 24}h")
}

resource "oci_objectstorage_object" "ansible_ollama_artifact_object" {
  bucket      = oci_objectstorage_bucket.artifacts_bucket.name
  source      = data.archive_file.ansible_ollama_artifact.output_path
  namespace   = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  object      = "ansible_ollama_artifact.zip"
  content_md5 = data.archive_file.ansible_ollama_artifact.output_md5
}

resource "oci_objectstorage_preauthrequest" "ansible_ollama_artifact_par" {
  namespace    = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  bucket       = oci_objectstorage_bucket.artifacts_bucket.name
  name         = "ansible_ollama_artifact_par"
  access_type  = "ObjectRead"
  object_name  = oci_objectstorage_object.ansible_ollama_artifact_object.object
  time_expires = timeadd(time_static.deploy_time.rfc3339, "${var.artifacts_par_expiration_in_days * 24}h")
}

# --- Backend JAR ---

resource "oci_objectstorage_object" "backend_jar_artifact_object" {
  bucket      = oci_objectstorage_bucket.artifacts_bucket.name
  source      = data.archive_file.backend_jar_artifact.output_path
  namespace   = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  object      = "backend_jar_artifact.zip"
  content_md5 = data.archive_file.backend_jar_artifact.output_md5
}

resource "oci_objectstorage_preauthrequest" "backend_jar_artifact_par" {
  namespace    = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  bucket       = oci_objectstorage_bucket.artifacts_bucket.name
  name         = "backend_jar_artifact_par"
  access_type  = "ObjectRead"
  object_name  = oci_objectstorage_object.backend_jar_artifact_object.object
  time_expires = timeadd(time_static.deploy_time.rfc3339, "${var.artifacts_par_expiration_in_days * 24}h")
}

# --- Streamlit web sources ---

resource "oci_objectstorage_object" "web_streamlit_artifact_object" {
  bucket      = oci_objectstorage_bucket.artifacts_bucket.name
  source      = data.archive_file.web_streamlit_artifact.output_path
  namespace   = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  object      = "web_streamlit_artifact.zip"
  content_md5 = data.archive_file.web_streamlit_artifact.output_md5
}

resource "oci_objectstorage_preauthrequest" "web_streamlit_artifact_par" {
  namespace    = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  bucket       = oci_objectstorage_bucket.artifacts_bucket.name
  name         = "web_streamlit_artifact_par"
  access_type  = "ObjectRead"
  object_name  = oci_objectstorage_object.web_streamlit_artifact_object.object
  time_expires = timeadd(time_static.deploy_time.rfc3339, "${var.artifacts_par_expiration_in_days * 24}h")
}

# --- Database wallet (uploaded as base64-encoded zip) ---

resource "oci_objectstorage_object" "db_wallet_artifact_object" {
  bucket    = oci_objectstorage_bucket.artifacts_bucket.name
  content   = module.adbs.wallet_zip_base64
  namespace = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  object    = "db_wallet_artifact.zip"
}

resource "oci_objectstorage_preauthrequest" "db_wallet_artifact_par" {
  namespace    = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  bucket       = oci_objectstorage_bucket.artifacts_bucket.name
  name         = "db_wallet_artifact_par"
  access_type  = "ObjectRead"
  object_name  = oci_objectstorage_object.db_wallet_artifact_object.object
  time_expires = timeadd(time_static.deploy_time.rfc3339, "${var.artifacts_par_expiration_in_days * 24}h")
}

# --- ONNX embedding model (large binary, 133 MB) ---
# Loaded into Autonomous DB by ops via DBMS_VECTOR.LOAD_ONNX_MODEL_CLOUD.

resource "oci_objectstorage_object" "onnx_model_object" {
  bucket    = oci_objectstorage_bucket.artifacts_bucket.name
  source    = "${path.module}/${var.onnx_model_local_path}"
  namespace = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  object    = "all_MiniLM_L12_v2.onnx"
}

locals {
  onnx_object_uri = "https://objectstorage.${var.region}.oraclecloud.com/n/${data.oci_objectstorage_namespace.objectstorage_namespace.namespace}/b/${oci_objectstorage_bucket.artifacts_bucket.name}/o/${oci_objectstorage_object.onnx_model_object.object}"
}
