locals {
  # Generate a random password for Oracle DB if not provided
  oracle_password = var.use_autonomous_db ? var.adb_admin_password : random_password.oracle_db.result
  oracle_mode     = var.use_autonomous_db ? "adb" : "freepdb"
  is_flex_shape   = length(regexall("Flex", var.instance_shape)) > 0
}

resource "random_password" "oracle_db" {
  length  = 16
  special = false
  upper   = true
  lower   = true
  numeric = true
}

resource "oci_core_instance" "picooraclaw" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "picooraclaw"
  shape               = var.instance_shape

  dynamic "shape_config" {
    for_each = local.is_flex_shape ? [1] : []
    content {
      ocpus         = var.instance_ocpus
      memory_in_gbs = var.instance_memory_in_gbs
    }
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ol9.images[0].id
    boot_volume_size_in_gbs = 100
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.picooraclaw.id
    assign_public_ip = true
    display_name     = "picooraclaw-vnic"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
      setup_script      = file("${path.module}/scripts/setup.sh")
      oracle_mode       = local.oracle_mode
      oracle_password   = local.oracle_password
      adb_dsn           = var.use_autonomous_db ? oci_database_autonomous_database.picooraclaw[0].connection_strings[0].all_connection_strings["LOW"] : ""
      adb_wallet_base64 = var.use_autonomous_db ? oci_database_autonomous_database_wallet.picooraclaw[0].content : ""
    }))
  }

  freeform_tags = {
    "app" = "picooraclaw"
  }
}
