resource "oci_core_vcn" "picooraclaw" {
  compartment_id = var.compartment_ocid
  display_name   = "picooraclaw-vcn"
  cidr_blocks    = [var.vcn_cidr]
  dns_label      = "picovcn"
}

resource "oci_core_internet_gateway" "picooraclaw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.picooraclaw.id
  display_name   = "picooraclaw-igw"
  enabled        = true
}

resource "oci_core_route_table" "picooraclaw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.picooraclaw.id
  display_name   = "picooraclaw-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.picooraclaw.id
  }
}

resource "oci_core_security_list" "picooraclaw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.picooraclaw.id
  display_name   = "picooraclaw-sl"

  # Allow all egress
  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
    stateless   = false
  }

  # SSH
  ingress_security_rules {
    source    = "0.0.0.0/0"
    protocol  = "6"
    stateless = false
    tcp_options {
      min = 22
      max = 22
    }
  }

  # Gateway API
  ingress_security_rules {
    source    = "0.0.0.0/0"
    protocol  = "6"
    stateless = false
    tcp_options {
      min = 18790
      max = 18790
    }
  }

  # ICMP
  ingress_security_rules {
    source    = "0.0.0.0/0"
    protocol  = "1"
    stateless = false
    icmp_options {
      type = 3
      code = 4
    }
  }
}

resource "oci_core_subnet" "picooraclaw" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.picooraclaw.id
  display_name               = "picooraclaw-subnet"
  cidr_block                 = cidrsubnet(var.vcn_cidr, 8, 1)
  dns_label                  = "picosub"
  route_table_id             = oci_core_route_table.picooraclaw.id
  security_list_ids          = [oci_core_security_list.picooraclaw.id]
  prohibit_public_ip_on_vnic = false
}
