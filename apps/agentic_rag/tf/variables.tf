variable "tenancy_ocid" {
  type = string
}

variable "region" {
  type = string
}

variable "config_file_profile" {
  type = string
}

variable "compartment_ocid" {
  type = string
}

variable "ssh_private_key_path" {
  type = string
}

variable "ssh_public_key" {
  type = string
}

variable "project_name" {
  type    = string
  default = "arag"
}

variable "cert_fullchain" {
  type = string
}

variable "cert_private_key" {
  type = string
}


variable "autonomous_database_db_workload" {
  type    = string
  default = "OLTP"
}

variable "autonomous_database_db_license" {
  type    = string
  description = "BRING_YOUR_OWN_LICENSE, LICENSE_INCLUDED"
  default = "BRING_YOUR_OWN_LICENSE"
}

variable "autonomous_database_db_whitelisted_ips" {
  type    = list(string)
  default = ["0.0.0.0/0"] # Don't do this in prod
}

variable "autonomous_database_cpu_core_count" {
  type    = number
  default = 1
}

variable "autonomous_database_data_storage_size_in_tbs" {
  type    = number
  default = 1
}