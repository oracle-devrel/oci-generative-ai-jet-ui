output "instance_public_ip" {
  description = "Public IP of the PicoOraClaw instance"
  value       = oci_core_instance.picooraclaw.public_ip
}

output "ssh_command" {
  description = "SSH into the instance"
  value       = "ssh opc@${oci_core_instance.picooraclaw.public_ip}"
}

output "gateway_url" {
  description = "PicoOraClaw gateway health endpoint"
  value       = "http://${oci_core_instance.picooraclaw.public_ip}:18790/health"
}

output "chat_command" {
  description = "Start an interactive chat session"
  value       = "ssh opc@${oci_core_instance.picooraclaw.public_ip} -t picooraclaw agent"
}

output "setup_log" {
  description = "Watch the setup progress"
  value       = "ssh opc@${oci_core_instance.picooraclaw.public_ip} -t 'tail -f /var/log/picooraclaw-setup.log'"
}

output "oracle_password" {
  description = "Generated Oracle DB password (save this!)"
  value       = local.oracle_password
  sensitive   = true
}

output "database_mode" {
  description = "Oracle Database mode used"
  value       = local.oracle_mode
}
