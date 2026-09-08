locals {
  project_name = var.project_name
  deploy_id    = random_string.deploy_id.result
  anywhere     = "0.0.0.0/0"
  tcp          = "6"
}