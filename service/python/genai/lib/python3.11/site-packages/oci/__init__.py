# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from . import auth, config, constants, decorators, exceptions, regions, pagination, retry, fips, circuit_breaker, alloy
from .base_client import BaseClient
from .request import Request
from .response import Response
from .signer import Signer
from .version import __version__  # noqa
from .waiter import wait_until
import os
import sys

fips.enable_fips_mode()

if os.getenv("OCI_PYTHON_SDK_NO_SERVICE_IMPORTS", "").lower() in ["true", "1"]:
    pass
else:
    __all__ = [
        "BaseClient", "Error", "Request", "Response", "Signer", "config", "constants", "decorators", "exceptions", "regions", "wait_until", "pagination", "auth", "retry", "fips", "circuit_breaker", "alloy",
        "access_governance_cp", "adm", "ai_anomaly_detection", "ai_document", "ai_language", "ai_speech", "ai_vision", "analytics", "announcements_service", "apigateway", "apm_config", "apm_control_plane", "apm_synthetics", "apm_traces", "application_migration", "appmgmt_control", "artifacts", "audit", "autoscaling", "bastion", "bds", "blockchain", "budget", "certificates", "certificates_management", "cims", "cloud_bridge", "cloud_guard", "cloud_migrations", "compute_cloud_at_customer", "compute_instance_agent", "container_engine", "container_instances", "core", "dashboard_service", "data_catalog", "data_flow", "data_integration", "data_labeling_service", "data_labeling_service_dataplane", "data_safe", "data_science", "database", "database_management", "database_migration", "database_tools", "devops", "disaster_recovery", "dns", "dts", "em_warehouse", "email", "events", "file_storage", "fleet_software_update", "functions", "fusion_apps", "generative_ai", "generative_ai_inference", "generic_artifacts_content", "golden_gate", "governance_rules_control_plane", "healthchecks", "identity", "identity_data_plane", "identity_domains", "integration", "jms", "jms_java_downloads", "key_management", "license_manager", "limits", "load_balancer", "lockbox", "log_analytics", "logging", "loggingingestion", "loggingsearch", "management_agent", "management_dashboard", "marketplace", "marketplace_publisher", "media_services", "monitoring", "mysql", "network_firewall", "network_load_balancer", "nosql", "object_storage", "oce", "oci_control_center", "ocvp", "oda", "onesubscription", "ons", "opa", "opensearch", "operator_access_control", "opsi", "optimizer", "os_management", "os_management_hub", "osp_gateway", "osub_billing_schedule", "osub_organization_subscription", "osub_subscription", "osub_usage", "psql", "queue", "recovery", "redis", "resource_manager", "resource_search", "rover", "sch", "secrets", "service_catalog", "service_manager_proxy", "service_mesh", "stack_monitoring", "streaming", "tenant_manager_control_plane", "threat_intelligence", "usage", "usage_api", "vault", "vbs_inst", "visual_builder", "vn_monitoring", "vulnerability_scanning", "waa", "waas", "waf", "work_requests"
    ]
    if sys.version_info >= (3, 7) and os.getenv("OCI_PYTHON_SDK_LAZY_IMPORTS_DISABLED", "False").lower() != "true":
        def __getattr__(x):
            # Loads the oci modules only when they are needed instead of loading them all at start to reduce the initial
            # import time and memory used by the SDK.
            if x in __all__:
                import importlib
                return importlib.import_module(__name__ + "." + x)
            raise AttributeError("module " + __name__ + " has no attribute" + x)
    else:
        from . import access_governance_cp, adm, ai_anomaly_detection, ai_document, ai_language, ai_speech, ai_vision, analytics, announcements_service, apigateway, apm_config, apm_control_plane, apm_synthetics, apm_traces, application_migration, appmgmt_control, artifacts, audit, autoscaling, bastion, bds, blockchain, budget, certificates, certificates_management, cims, cloud_bridge, cloud_guard, cloud_migrations, compute_cloud_at_customer, compute_instance_agent, container_engine, container_instances, core, dashboard_service, data_catalog, data_flow, data_integration, data_labeling_service, data_labeling_service_dataplane, data_safe, data_science, database, database_management, database_migration, database_tools, devops, disaster_recovery, dns, dts, em_warehouse, email, events, file_storage, fleet_software_update, functions, fusion_apps, generative_ai, generative_ai_inference, generic_artifacts_content, golden_gate, governance_rules_control_plane, healthchecks, identity, identity_data_plane, identity_domains, integration, jms, jms_java_downloads, key_management, license_manager, limits, load_balancer, lockbox, log_analytics, logging, loggingingestion, loggingsearch, management_agent, management_dashboard, marketplace, marketplace_publisher, media_services, monitoring, mysql, network_firewall, network_load_balancer, nosql, object_storage, oce, oci_control_center, ocvp, oda, onesubscription, ons, opa, opensearch, operator_access_control, opsi, optimizer, os_management, os_management_hub, osp_gateway, osub_billing_schedule, osub_organization_subscription, osub_subscription, osub_usage, psql, queue, recovery, redis, resource_manager, resource_search, rover, sch, secrets, service_catalog, service_manager_proxy, service_mesh, stack_monitoring, streaming, tenant_manager_control_plane, threat_intelligence, usage, usage_api, vault, vbs_inst, visual_builder, vn_monitoring, vulnerability_scanning, waa, waas, waf, work_requests
