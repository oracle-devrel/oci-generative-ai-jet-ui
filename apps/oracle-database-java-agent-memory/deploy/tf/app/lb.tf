resource "oci_core_public_ip" "public_reserved_ip" {
  compartment_id = var.compartment_ocid
  lifetime       = "RESERVED"

  lifecycle {
    ignore_changes = [private_ip_id]
  }
}

variable "load_balancer_shape_details_maximum_bandwidth_in_mbps" {
  default = 100
}

variable "load_balancer_shape_details_minimum_bandwidth_in_mbps" {
  default = 10
}

resource "oci_load_balancer" "lb" {
  shape          = "flexible"
  compartment_id = var.compartment_ocid

  subnet_ids = [oci_core_subnet.public_subnet.id]

  shape_details {
    maximum_bandwidth_in_mbps = var.load_balancer_shape_details_maximum_bandwidth_in_mbps
    minimum_bandwidth_in_mbps = var.load_balancer_shape_details_minimum_bandwidth_in_mbps
  }

  display_name = "LB ${local.project_name}${local.deploy_id}"

  reserved_ips {
    id = oci_core_public_ip.public_reserved_ip.id
  }
}

resource "oci_load_balancer_backend_set" "lb-backend-set-web" {
  name             = "lb-backend-set-web"
  load_balancer_id = oci_load_balancer.lb.id
  policy           = "ROUND_ROBIN"

  health_checker {
    port     = "8501"
    protocol = "HTTP"
    url_path = "/"
  }
}

resource "oci_load_balancer_backend_set" "lb-backend-set-api" {
  name             = "lb-backend-set-api"
  load_balancer_id = oci_load_balancer.lb.id
  policy           = "ROUND_ROBIN"

  health_checker {
    port     = "8080"
    protocol = "HTTP"
    url_path = "/actuator/health"
  }
}

resource "oci_load_balancer_listener" "lb-listener" {
  load_balancer_id         = oci_load_balancer.lb.id
  name                     = "http"
  default_backend_set_name = oci_load_balancer_backend_set.lb-backend-set-web.name
  port                     = 80
  protocol                 = "HTTP"
  routing_policy_name      = oci_load_balancer_load_balancer_routing_policy.routing_policy.name

  connection_configuration {
    idle_timeout_in_seconds = "600"
  }
}

resource "oci_load_balancer_backend" "lb-backend-web" {
  load_balancer_id = oci_load_balancer.lb.id
  backendset_name  = oci_load_balancer_backend_set.lb-backend-set-web.name
  ip_address       = module.web.private_ip
  port             = 8501
  backup           = false
  drain            = false
  offline          = false
  weight           = 1
}

resource "oci_load_balancer_backend" "lb-backend-api" {
  load_balancer_id = oci_load_balancer.lb.id
  backendset_name  = oci_load_balancer_backend_set.lb-backend-set-api.name
  ip_address       = module.backend.private_ip
  port             = 8080
  backup           = false
  drain            = false
  offline          = false
  weight           = 1
}

resource "oci_load_balancer_load_balancer_routing_policy" "routing_policy" {
  condition_language_version = "V1"
  load_balancer_id           = oci_load_balancer.lb.id
  name                       = "routing_policy"

  rules {
    name      = "routing_to_api"
    condition = "any(http.request.url.path sw (i '/api'))"
    actions {
      name             = "FORWARD_TO_BACKENDSET"
      backend_set_name = oci_load_balancer_backend_set.lb-backend-set-api.name
    }
  }

  rules {
    name      = "routing_to_actuator"
    condition = "any(http.request.url.path sw (i '/actuator'))"
    actions {
      name             = "FORWARD_TO_BACKENDSET"
      backend_set_name = oci_load_balancer_backend_set.lb-backend-set-api.name
    }
  }
}
