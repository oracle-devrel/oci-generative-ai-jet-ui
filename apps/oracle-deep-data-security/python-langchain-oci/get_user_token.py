#!/bin/python
#
# $Header: get_user_token.py 17-jun-2026.09:55:05 tanisaga Exp $
#
# get_user_token.py
#
# Copyright (c) 2026, Oracle and/or its affiliates.
#
#    NAME
#      get_user_token.py - Script to get IAM user and app tokens
#
#    DESCRIPTION
#      Script to get access
#      token for IAM users and mid-tier app across domains
#
#    NOTES
#      Standalone script, can be called like this:
#         - python get_user_token.py oci_app_default_config.ini
#
#    MODIFIED   (MM/DD/YY)
#    tanisaga    06/17/26 - Creation
#


import requests
import configparser
import base64
import sys
import json
import os

# Function to get IAM user oauth2 token
def get_user_token(client_id, client_secret, username, password, token_url, scope):
    # Prepare Basic Auth header
    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {
        'Authorization': f'Basic {b64_auth}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = {
        'grant_type': 'password',
        'username': username,
        'password': password,
        'scope': scope
    }
    response = requests.post(token_url, headers=headers, data=payload)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        print(f"Failed for {username}: {response.status_code}, {response.text}")
        return None

# Function to get mid-tier app access token
def get_app_token(client_id, client_secret, token_url, scope):
    # Prepare Basic Auth header
    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {
        'Authorization': f'Basic {b64_auth}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = {
        'grant_type': 'client_credentials',
        'scope': scope
    }
    response = requests.post(token_url, headers=headers, data=payload)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        print(f"Failed for app token : {response.status_code}, {response.text}")
        return None

# Function to generate domain specific sql file to set identity parameters
def generate_env_stup(section, domain_url, dbapp_id, dbapp_client_id, dbapp_client_secret):
    iam_idp = {
        "app_id": dbapp_id,
        "domain_url": domain_url
    }
    sql_file_name = f"tzfdiam_setparam_{section}.sql"

    no_cred_obj = os.environ.get('NO_CRED_OBJECT')

    with open(sql_file_name, 'w') as sqlf:
        sqlf.write("SET ECHO ON\n");
        sqlf.write("SET FEEDBACK 1\n");
        sqlf.write("SET NUMWIDTH 10\n");
        sqlf.write("SET LINESIZE 80\n");
        sqlf.write("SET TRIMSPOOL ON\n");
        sqlf.write("SET TAB OFF\n");
        sqlf.write("SET PAGESIZE 100\n");
        sqlf.write("SET VERIFY OFF\n");
        sqlf.write("conn sys/knl_test7@&1 as sysdba\n")
        sqlf.write("alter system set identity_provider_type = 'OCI_IAM' scope=both;\n")
        sqlf.write("alter system set identity_provider_oauth_config='{}';\n"
                .format(json.dumps(iam_idp)))
        sqlf.write("show parameter identity_provider_type;\n")
        sqlf.write("show parameter identity_provider_oauth_config;\n")
        if no_cred_obj is None:
            sqlf.write("exec DBMS_CREDENTIAL.DROP_CREDENTIAL('OCI_IAM_DOMAIN_DB_CRED$');\n")
            sqlf.write(f"exec DBMS_CREDENTIAL.CREATE_CREDENTIAL('OCI_IAM_DOMAIN_DB_CRED$','{dbapp_client_id}','{dbapp_client_secret}');\n")

def main():
    if len(sys.argv) != 2:
        print("Usage: python get_oci_user_token.py config.ini")
        sys.exit(1)

    # Read parameters from .ini file
    config = configparser.ConfigParser(interpolation=None)
    config.read(sys.argv[1])
    output_folder = 'tokens'

    # Create output_folder if it does not exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Store all domain names
    domains = {section: config[section] for section in config.sections() if section.lower().startswith('iam_domain_')}

    # Get mid-tier app tokens
    for section in config.sections():
        if section.lower().startswith('iam_domain_'):
            client_id = config[section].get('midtapp_client_id')
            client_secret = config[section].get('midtapp_client_secret')
            token_url = config[section].get('iam_token_url')
            scope = config[section].get('db_scope')
            domain_url = config[section].get('iam_domain_url')
            dbapp_id = config[section].get('dbapp_application_id')
            dbapp_client_id = config[section].get('dbapp_client_id')
            dbapp_client_secret = config[section].get('dbapp_client_secret')
            print(f"Generate env variable file for domain {section} ...")
            generate_env_stup(section, domain_url, dbapp_id, dbapp_client_id, dbapp_client_secret)
            print(f"Getting mid-tier token for domain {section} ...")
            app_token= get_app_token(client_id, client_secret, token_url, scope)
            if app_token:
                token_filefolder = os.path.join(output_folder, f'{section}')
                if not os.path.exists(token_filefolder):
                    os.makedirs(token_filefolder)
                token_filepath = os.path.join(token_filefolder, f'midtier_token')
                with open(token_filepath, 'w') as f:
                    f.write(app_token)
                print(f"Midtier token scope={scope}")
                print(f"Token saved to {token_filepath}")
            else:
                print("Failed to obtain midtier token.")
                

    # Get token for IAM users
    for section in config.sections():
        if section.lower().startswith('iam_user'):
            user_config = config[section]
            domain_name = user_config.get('domain')
            if not domain_name or domain_name not in domains:
                print(f"[{section}] -- missing or invalid domain reference: {domain_name}")
                continue
            username = user_config.get('username')
            password = user_config.get('password')
            domain_conf = domains[domain_name]
            client_id = domain_conf['clientapp_client_id']
            client_secret = domain_conf['clientapp_client_secret']
            token_url = domain_conf['iam_token_url']
            scope = domain_conf['midtier_scope']
            print(f"Getting token for user {username} in domain {domain_name} ...")
            token = get_user_token(client_id, client_secret, username, password, token_url, scope)
            if token:
                token_filefolder = os.path.join(output_folder, f'{domain_name}')
                if not os.path.exists(token_filefolder):
                    os.makedirs(token_filefolder)
                token_filepath = os.path.join(token_filefolder, f'{username}_token')
                with open(token_filepath, 'w') as f:
                    f.write(token)
                print(f"User token scope={scope}")
                print(f"Token saved to {token_filepath}")
            else:
                print(f"Failed to get token for {username} in domain {domain_name}")

if __name__ == "__main__":
    main()
