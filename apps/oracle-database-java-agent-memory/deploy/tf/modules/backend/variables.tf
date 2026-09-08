terraform {
  required_providers {
    oci = {
      source = "oracle/oci"
    }
  }
}

variable "project_name" {
  type = string
}

variable "deploy_id" {
  type = string
}

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

variable "subnet_id" {
  type = string
}

variable "ads" {
  type = list(any)
}

variable "instance_shape" {
  type = string
}

variable "ssh_public_key" {
  type = string
}

variable "db_service_name" {
  type = string
}

variable "db_admin_password" {
  type      = string
  sensitive = true
}

variable "ollama_private_ip" {
  type = string
}

variable "ollama_chat_model" {
  type = string
}

variable "ansible_backend_artifact_par_full_path" {
  type = string
}

variable "backend_jar_par_full_path" {
  type = string
}

variable "wallet_par_full_path" {
  type = string
}
