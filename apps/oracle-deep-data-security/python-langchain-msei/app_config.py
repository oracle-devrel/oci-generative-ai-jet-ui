#!/bin/python
#
# $Header: app_config.py 14-may-2026.13:38:18 tanisaga Exp $
#
# app_config.py
#
# Copyright (c) 2026, Oracle and/or its affiliates.
#
#    NAME
#      app_config.py - Configuration for 
#      LangChain Agent Sample HR application.
#
#    DESCRIPTION
#      Defines Defines OCI Generative AI Service model 
#      identifiers and configuration used by the 
#      LangChain Agent Sample HR application
#
#    NOTES
#      This sample uses OCI Generative AI Service for LLM inference.
#      The selected model is configured through MODEL_IDS and
#      model_choice.
#      Configure the OCI config file, profile, compartment ID,
#      default model choice, and token limit before running.
#
#    MODIFIED   (MM/DD/YY)
#    tanisaga    05/14/26 - Creation

# Add OCI Generative AI Service model IDs.
MODEL_IDS = {}

@dataclass(frozen=True)
class AppConfig:
    # OCI Generative AI configuration
    oci_config_file: str = <oci_config>
    oci_profile: str = <oci_profile>
    COMPARTMENT_ID = <oci-compartment-id>

    model_choice: str = <model_choice>
    max_tokens: int =<max_tokens>
