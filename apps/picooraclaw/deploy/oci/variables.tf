# --- ORM-provided (hidden) ---
variable "tenancy_ocid" {
  description = "OCI tenancy OCID"
  type        = string
}

variable "region" {
  description = "OCI region"
  type        = string
}

variable "compartment_ocid" {
  description = "Compartment to deploy into"
  type        = string
}

# --- Instance Configuration ---
variable "instance_shape" {
  description = "Compute instance shape"
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "instance_ocpus" {
  description = "Number of OCPUs"
  type        = number
  default     = 2
}

variable "instance_memory_in_gbs" {
  description = "Memory in GB"
  type        = number
  default     = 12
}

variable "ssh_public_key" {
  description = "SSH public key for instance access"
  type        = string
}

# --- Database Configuration ---
variable "use_autonomous_db" {
  description = "Use Autonomous Database instead of Oracle DB Free container"
  type        = bool
  default     = false
}

variable "adb_admin_password" {
  description = "Admin password for Autonomous Database (min 12 chars, 1 upper, 1 lower, 1 number)"
  type        = string
  default     = ""
  sensitive   = true
}

# --- Network ---
variable "vcn_cidr" {
  description = "VCN CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}
