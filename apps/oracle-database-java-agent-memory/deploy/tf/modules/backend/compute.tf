locals {
  cloud_init_content = templatefile("${path.module}/userdata/bootstrap.tftpl", {
    project_name                  = var.project_name
    region_name                   = var.region
    ansible_backend_par_full_path = var.ansible_backend_artifact_par_full_path
    backend_jar_par_full_path     = var.backend_jar_par_full_path
    wallet_par_full_path          = var.wallet_par_full_path
    db_service_name               = var.db_service_name
    db_admin_password             = var.db_admin_password
    ollama_base_url               = "http://${var.ollama_private_ip}:11434"
    ollama_chat_model             = var.ollama_chat_model
  })
}

data "oci_core_images" "ol9_images" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Oracle Linux"
  operating_system_version = "9"
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"

  filter {
    name   = "display_name"
    values = ["^Oracle-Linux-9\\.\\d+-\\d{4}\\.\\d{2}\\.\\d{2}-\\d+$"]
    regex  = true
  }
}

resource "oci_core_instance" "instance" {
  availability_domain = lookup(var.ads[0], "name")
  compartment_id      = var.compartment_ocid
  display_name        = "backend${var.project_name}${var.deploy_id}"
  shape               = var.instance_shape

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(local.cloud_init_content)
  }

  shape_config {
    ocpus         = 1
    memory_in_gbs = 16
  }

  create_vnic_details {
    subnet_id                 = var.subnet_id
    assign_public_ip          = false
    display_name              = "backend${var.project_name}${var.deploy_id}"
    assign_private_dns_record = true
    hostname_label            = "backend${var.project_name}${var.deploy_id}"
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ol9_images.images[0].id
  }

  timeouts {
    create = "60m"
  }
}

resource "time_sleep" "wait_for_instance" {
  depends_on      = [oci_core_instance.instance]
  create_duration = "3m"
}
