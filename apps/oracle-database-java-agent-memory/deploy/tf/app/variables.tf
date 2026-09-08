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

variable "ssh_public_key" {
  type = string
}

variable "ssh_private_key_path" {
  type = string
}

variable "project_name" {
  type    = string
  default = "agentmem"
}

variable "instance_shape" {
  type        = string
  default     = "VM.Standard.E4.Flex"
  description = "Shape for backend, web, and ops instances."
}

variable "ollama_shape" {
  type        = string
  default     = "VM.Standard.E4.Flex"
  description = "Shape for the Ollama compute instance. May be a CPU or GPU shape."
}

variable "ollama_chat_model" {
  type    = string
  default = "qwen2.5"
}

variable "ecpu_count" {
  type    = number
  default = 2
}

variable "storage_in_tbs" {
  type    = number
  default = 1
}

variable "onnx_model_local_path" {
  type        = string
  default     = "../../../models/all_MiniLM_L12_v2.onnx"
  description = "Path to the pre-built ONNX embedding model, relative to deploy/tf/app."
}

variable "onnx_model_name_in_db" {
  type    = string
  default = "ALL_MINILM_L12_V2"
}

variable "artifacts_par_expiration_in_days" {
  type    = number
  default = 7
}
