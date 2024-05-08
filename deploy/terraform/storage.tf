resource "oci_objectstorage_bucket" "artifacts_bucket" {
  compartment_id = var.compartment_ocid
  name           = "artifacts_${local.project_name}_${local.deploy_id}"
  namespace      = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
}

resource "oci_objectstorage_object" "wallet_object" {
  bucket    = oci_objectstorage_bucket.artifacts_bucket.name
  content   = oci_database_autonomous_database_wallet.adb_wallet.content
  namespace = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  object    = "wallet.zip.b64"
}


resource "oci_objectstorage_preauthrequest" "wallet_par" {
  namespace    = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  bucket       = oci_objectstorage_bucket.artifacts_bucket.name
  name         = "wallet_par"
  access_type  = "ObjectRead"
  object_name = oci_objectstorage_object.wallet_object.object
  time_expires = timeadd(timestamp(), "${var.artifacts_par_expiration_in_days * 24}h")
}