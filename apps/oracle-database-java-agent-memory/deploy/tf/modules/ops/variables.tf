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

variable "user_ocid" {
  type = string
}

variable "fingerprint" {
  type = string
}

variable "private_api_key_content" {
  type      = string
  sensitive = true
}

variable "ads" {
  type = list(any)
}

variable "db_admin_password" {
  type      = string
  sensitive = true
}

variable "db_service_name" {
  type = string
}

variable "db_wallet_par_full_path" {
  type = string
}

variable "instance_shape" {
  type = string
}

variable "ssh_private_key_path" {
  type = string
}

variable "ssh_public_key" {
  type = string
}

variable "ansible_ops_artifact_par_full_path" {
  type = string
}

variable "onnx_model_name" {
  type = string
}

variable "onnx_object_uri" {
  type = string
}

variable "onnx_object_name" {
  type = string
}

variable "onnx_bucket_name" {
  type = string
}

variable "onnx_bucket_namespace" {
  type = string
}
