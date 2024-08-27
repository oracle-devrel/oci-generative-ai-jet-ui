
output "project" {
  value = "${var.project_name}${random_string.deploy_id.result}"
}

output "db_service" {
  value = "${local.project_name}${local.deploy_id}"
}

output "db_password" {
  value     = random_password.adb_admin_password.result
  sensitive = true
}

output "kubeconfig" {
  value     = data.oci_containerengine_cluster_kube_config.kube_config.content
  sensitive = true
}

output "oke_cluster_ocid" {
  value = module.oke.cluster_id
}

output "ocir_user" {
  value = oci_identity_user.ocir_user.name
}

output "ocir_user_token" {
  sensitive = true
  value     = oci_identity_auth_token.ocir_user_auth_token.token
}

output "ocir_user_email" {
  sensitive = false
  value     = oci_identity_user.ocir_user.email
}