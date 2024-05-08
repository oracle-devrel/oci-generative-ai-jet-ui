locals {
  model_collection = data.oci_generative_ai_models.genai_models.model_collection[0]
  cohere_models = tolist([for each in local.model_collection.items : each
    if contains(each.capabilities, "TEXT_GENERATION")
  && each.vendor == "cohere"])
}

output "project" {
  value = "${var.project_name}${random_string.deploy_id.result}"
}

# output "load_balancer" {
#   value = oci_core_public_ip.reserved_ip.ip_address
# }

# output "web_instances" {
#   value = oci_core_instance.web[*].private_ip
# }

# output "backend_instances" {
#   value = oci_core_instance.backend[*].private_ip
# }

output "cohere_model_id" {
  value = local.cohere_models[0].id
}

# output "ssh_bastion_session_backend" {
#   value = oci_bastion_session.backend_session.ssh_metadata.command
# }

# output "ssh_bastion_session_web" {
#   value = oci_bastion_session.web_session.ssh_metadata.command
# }

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