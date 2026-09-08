resource "random_string" "deploy_id" {
  length  = 2
  special = false
  upper   = false
}