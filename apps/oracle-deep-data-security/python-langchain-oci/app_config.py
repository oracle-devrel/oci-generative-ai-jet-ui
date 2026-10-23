#!/bin/python
#
# $Header: app_config.py 12-jun-2026.06:14:00 tanisaga Exp $
#
# app_config.py
#
# Copyright (c) 2026, Oracle and/or its affiliates.
#
#    NAME
#      app_config.py - Application configuration for OCI IAM LangChain demo
#
#    DESCRIPTION
#      Defines OCI configuration, model configuration, and
#      compartment settings used by the OCI IAM LangChain demo.
#
#    NOTES
#      <other useful comments, qualifications, etc.>
#
#    MODIFIED   (MM/DD/YY)
#    tanisaga    06/12/26 - Creation
#
from dataclasses import dataclass

# Add OCI Generative AI Service model IDs.
MODEL_IDS = {
    "<model_choice>": "<model_id>",
}

@dataclass(frozen=True)
class AppConfig:
    # OCI Generative AI configuration
    oci_config_file: str = "<oci_config>"
    oci_profile: str = "<oci_profile>"
    compartment_id: str = "<oci_compartment_id>"
    model_choice: str = "<model_choice>"

    max_tokens: int = 4096