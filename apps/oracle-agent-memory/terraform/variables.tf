variable "tenancy_ocid" {
  description = "Your OCI tenancy OCID. Find it under Profile → Tenancy in the Console."
  type        = string
}

variable "compartment_ocid" {
  description = "Compartment to create resources in. Defaults to the root (tenancy) compartment."
  type        = string
  default     = ""
}

variable "region" {
  description = "OCI region. Must be one where Generative AI is available."
  type        = string
  default     = "us-chicago-1"

  validation {
    condition     = contains(["us-chicago-1", "us-ashburn-1", "eu-frankfurt-1", "uk-london-1", "ap-osaka-1"], var.region)
    error_message = "Pick a region with Generative AI: us-chicago-1, us-ashburn-1, eu-frankfurt-1, uk-london-1, or ap-osaka-1."
  }
}

variable "db_name" {
  description = "Internal database name (alphanumeric, 14 chars max)."
  type        = string
  default     = "voiceagent"
}

variable "db_display_name" {
  description = "Human-readable database name shown in the Console."
  type        = string
  default     = "agent-memory-db"
}

locals {
  compartment_id = var.compartment_ocid != "" ? var.compartment_ocid : var.tenancy_ocid
}
