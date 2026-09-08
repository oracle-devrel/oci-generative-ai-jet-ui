terraform {
  required_providers {
    oci = {
      source                = "oracle/oci"
      version               = "~> 6.35.0"
      configuration_aliases = [oci.home]
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5.2"
      # https://registry.terraform.io/providers/hashicorp/local/
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7.1"
      # https://registry.terraform.io/providers/hashicorp/random/
    }
    archive = {
      source = "hashicorp/archive"
      version = "~> 2.7.0"
      # https://registry.terraform.io/providers/hashicorp/archive/
    }
  }
}
