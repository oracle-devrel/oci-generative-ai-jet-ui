resource "random_string" "deploy_id" {
  length  = 2
  special = false
  upper   = false
}

module "adbs" {
  source = "../modules/adbs"

  project_name                                 = local.project_name
  deploy_id                                    = local.deploy_id
  compartment_ocid                             = var.compartment_ocid
  autonomous_database_compute_count            = var.ecpu_count
  autonomous_database_data_storage_size_in_tbs = var.storage_in_tbs
}

module "ollama" {
  source = "../modules/ollama"

  project_name        = local.project_name
  deploy_id           = local.deploy_id
  config_file_profile = var.config_file_profile
  region              = var.region
  tenancy_ocid        = var.tenancy_ocid
  compartment_ocid    = var.compartment_ocid

  subnet_id      = oci_core_subnet.app_subnet.id
  instance_shape = var.ollama_shape
  ssh_public_key = var.ssh_public_key
  ads            = data.oci_identity_availability_domains.ads.availability_domains

  ollama_chat_model                    = var.ollama_chat_model
  ansible_ollama_artifact_par_full_path = oci_objectstorage_preauthrequest.ansible_ollama_artifact_par.full_path
}

module "ops" {
  source = "../modules/ops"

  project_name        = local.project_name
  deploy_id           = local.deploy_id
  config_file_profile = var.config_file_profile
  region              = var.region
  tenancy_ocid        = var.tenancy_ocid
  compartment_ocid    = var.compartment_ocid

  subnet_id            = oci_core_subnet.public_subnet.id
  instance_shape       = var.instance_shape
  ssh_private_key_path = var.ssh_private_key_path
  ssh_public_key       = var.ssh_public_key
  ads                  = data.oci_identity_availability_domains.ads.availability_domains

  user_ocid               = var.user_ocid
  fingerprint             = var.fingerprint
  private_api_key_content = var.private_api_key_content

  db_admin_password       = module.adbs.admin_password
  db_service_name         = "${local.project_name}${local.deploy_id}_high"
  db_wallet_par_full_path = oci_objectstorage_preauthrequest.db_wallet_artifact_par.full_path

  ansible_ops_artifact_par_full_path = oci_objectstorage_preauthrequest.ansible_ops_artifact_par.full_path

  onnx_model_name      = var.onnx_model_name_in_db
  onnx_object_uri      = local.onnx_object_uri
  onnx_object_name     = oci_objectstorage_object.onnx_model_object.object
  onnx_bucket_name     = oci_objectstorage_bucket.artifacts_bucket.name
  onnx_bucket_namespace = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
}

# Wait for ops to finish DB initialization (touches /home/opc/ops-done.flag)
# before starting the backend, so the DataSeeder doesn't race the ONNX
# model load and hybrid index creation.
resource "null_resource" "ops_wait" {
  depends_on = [module.ops]

  triggers = {
    ops_instance_id = module.ops.id
  }

  connection {
    type        = "ssh"
    host        = module.ops.public_ip
    user        = "opc"
    private_key = file(var.ssh_private_key_path)
    timeout     = "30m"
  }

  provisioner "remote-exec" {
    inline = [
      "echo 'Waiting for ops cloud-init + DB setup to finish...'",
      "while [ ! -f /home/opc/ops-done.flag ]; do sleep 15; done",
      "echo 'ops-done.flag detected — DB ready.'",
    ]
  }
}

module "backend" {
  source = "../modules/backend"

  project_name        = local.project_name
  deploy_id           = local.deploy_id
  config_file_profile = var.config_file_profile
  region              = var.region
  tenancy_ocid        = var.tenancy_ocid
  compartment_ocid    = var.compartment_ocid

  subnet_id      = oci_core_subnet.app_subnet.id
  instance_shape = var.instance_shape
  ssh_public_key = var.ssh_public_key
  ads            = data.oci_identity_availability_domains.ads.availability_domains

  db_service_name   = "${local.project_name}${local.deploy_id}_high"
  db_admin_password = module.adbs.admin_password

  ollama_private_ip = module.ollama.private_ip
  ollama_chat_model = var.ollama_chat_model

  ansible_backend_artifact_par_full_path = oci_objectstorage_preauthrequest.ansible_backend_artifact_par.full_path
  backend_jar_par_full_path              = oci_objectstorage_preauthrequest.backend_jar_artifact_par.full_path
  wallet_par_full_path                   = oci_objectstorage_preauthrequest.db_wallet_artifact_par.full_path

  depends_on = [null_resource.ops_wait]
}

module "web" {
  source = "../modules/web"

  project_name        = local.project_name
  deploy_id           = local.deploy_id
  config_file_profile = var.config_file_profile
  region              = var.region
  tenancy_ocid        = var.tenancy_ocid
  compartment_ocid    = var.compartment_ocid

  subnet_id      = oci_core_subnet.app_subnet.id
  instance_shape = var.instance_shape
  ssh_public_key = var.ssh_public_key
  ads            = data.oci_identity_availability_domains.ads.availability_domains

  backend_private_ip = module.backend.private_ip

  ansible_web_artifact_par_full_path = oci_objectstorage_preauthrequest.ansible_web_artifact_par.full_path
  web_streamlit_par_full_path        = oci_objectstorage_preauthrequest.web_streamlit_artifact_par.full_path
}

# Surface wallet locally so the user can point a laptop backend at Autonomous.
resource "local_file" "adb_wallet_file" {
  content_base64 = module.adbs.wallet_zip_base64
  filename       = "${path.module}/generated/wallet.zip"
}
