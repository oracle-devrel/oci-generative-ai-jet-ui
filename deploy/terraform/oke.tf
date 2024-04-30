locals {
  cluster_k8s_latest_version = reverse(sort(data.oci_containerengine_cluster_option.oke.kubernetes_versions))[0]
  lb_subnet_cidr             = "10.22.128.0/27"
  workers_subnet_cidr        = "10.22.144.0/20"
  cp_subnet_cidr             = "10.22.0.8/29"
  vcn_cidr                   = "10.22.0.0/16"
}

module "oke" {
  source  = "oracle-terraform-modules/oke/oci"
  version = "5.1.5"

  tenancy_id     = var.tenancy_ocid
  compartment_id = var.compartment_ocid
  region         = var.region
  home_region    = var.tenancy_ocid

  providers = {
    oci      = oci
    oci.home = oci.home
  }

  kubernetes_version = local.cluster_k8s_latest_version
  cluster_name       = "${local.project_name}-${local.deploy_id}-oke"
  vcn_name           = "${local.project_name}-${local.deploy_id}-vcn"

  assign_public_ip_to_control_plane = true
  control_plane_is_public     = true
  control_plane_allowed_cidrs = ["0.0.0.0/0"]

  create_bastion  = false
  create_operator = false

  ssh_private_key_path = var.ssh_private_key_path
  ssh_public_key       = var.ssh_public_key

  # IAM - Policies
  create_iam_autoscaler_policy = "never"
  create_iam_kms_policy        = "never"
  create_iam_operator_policy   = "never"
  create_iam_worker_policy     = "never"
  # Network module - VCN
  subnets = {
    bastion = {
      create = "never"
    }
    operator = {
      create = "never"
    }
    cp = {
      create = "always",
      cidr   = local.cp_subnet_cidr
    }
    pub_lb = {
      create = "always",
      cidr   = local.lb_subnet_cidr
    }
    workers = {
      create = "always",
      cidr   = local.workers_subnet_cidr
    }
    int_lb = {
      create = "never"
    }
    pods = {
      create = "never"
    }
  }
  nsgs = {
    bastion  = { create = "never" }
    operator = { create = "never" }
    cp       = { create = "always" }
    int_lb   = { create = "never" }
    pub_lb   = { create = "always" } // never
    workers  = { create = "always" }
    pods     = { create = "always" } // never
  }

  assign_dns    = true
  create_vcn    = true
  vcn_cidrs     = [local.vcn_cidr]
  vcn_dns_label = "oke"

  # lockdown_default_seclist = true
  # allow_rules_public_lb = {
  #   "Allow TCP ingress to public load balancers for HTTPS traffic from anywhere" : { protocol = 6, port = 443, source = "0.0.0.0/0", source_type = "CIDR_BLOCK" },
  #   "Allow TCP ingress to public load balancers for HTTP traffic from anywhere" : { protocol = 6, port = 80, source = "0.0.0.0/0", source_type = "CIDR_BLOCK" }
  # }
  # Network module - security
  # allow_node_port_access            = true
  # allow_worker_internet_access      = true
  # allow_worker_ssh_access           = true
  # enable_waf                        = false
  # load_balancers                    = "public"
  # preferred_load_balancer = "public"
  # worker_is_public = false

  # Cluster module
  create_cluster = true
  cni_type       = "npn"
  cluster_type   = "enhanced"

  pods_cidr         = "10.244.0.0/16"
  services_cidr     = "10.96.0.0/16"
  use_signed_images = false
  use_defined_tags  = false

  # Workers
  worker_pool_mode = "node-pool"
  worker_pool_size = 2

  worker_pools = {
    node_pool_1 = {
      shape = "VM.Standard.E4.Flex",
      ocpus = 1,
      memory = 32,
      boot_volume_size = 120,
      create = true
    }
  }
}

data "oci_containerengine_cluster_kube_config" "kube_config" {
  cluster_id = module.oke.cluster_id
}


resource "local_file" "kubeconfig" {
  content  = data.oci_containerengine_cluster_kube_config.kube_config.content
  filename = "${path.module}/generated/kubeconfig"
}
