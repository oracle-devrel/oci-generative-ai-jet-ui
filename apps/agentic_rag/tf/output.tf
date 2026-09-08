output "deployment" {
  value = "${local.project_name}${local.deploy_id}"
}

output "adb_name" {
    value = oci_database_autonomous_database.adb.db_name
}

output "adb_display_name" {
    value = oci_database_autonomous_database.adb.display_name
}

output "adb_admin_password" {
  value = random_password.adb_admin_password.result
  sensitive = true
}

output "oke_cluster_id" {
  value = module.oke.cluster_id
}