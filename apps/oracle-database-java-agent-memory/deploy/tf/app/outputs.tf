output "deployment_name" {
  value = "${local.project_name}${local.deploy_id}"
}

output "lb_public_ip" {
  value = oci_core_public_ip.public_reserved_ip.ip_address
}

output "ops_public_ip" {
  value = module.ops.public_ip
}

output "backend_private_ip" {
  value = module.backend.private_ip
}

output "web_private_ip" {
  value = module.web.private_ip
}

output "ollama_private_ip" {
  value = module.ollama.private_ip
}

output "db_name" {
  value = module.adbs.db_name
}

output "db_service_name" {
  value = "${local.project_name}${local.deploy_id}_high"
}

output "db_admin_password" {
  value     = module.adbs.admin_password
  sensitive = true
}

output "onnx_object_uri" {
  value = local.onnx_object_uri
}
