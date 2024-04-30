data "oci_generative_ai_models" "genai_models" {
    compartment_id = var.compartment_ocid

    capability = ["TEXT_GENERATION"]
    state = "ACTIVE"
    vendor = "cohere"
}