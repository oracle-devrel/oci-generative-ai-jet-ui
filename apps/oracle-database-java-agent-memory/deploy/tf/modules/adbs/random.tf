resource "random_password" "admin_password" {
  length           = 20
  special          = true
  min_numeric      = 3
  min_special      = 3
  min_lower        = 3
  min_upper        = 3
  override_special = "#_-"
}
