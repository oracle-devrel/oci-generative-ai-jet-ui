# OCI IAM LangChain Demo (Single Agent)

## Overview

This project demonstrates how a LangChain application can securely access Oracle Database using OCI IAM OAuth2 authentication.

The application:

* Authenticates users using OCI IAM OAuth2 access tokens
* Propagates end-user identity to the database
* Uses Oracle Deep Data Security for authorization and data access control
* Uses LangChain and OCI Generative AI to provide a natural language interface over enterprise data

---

## Architecture

### Components

* OCI IAM Domain
* LangChain
* OCI Generative AI
* Oracle Database with Deep Data Security

### Current Scope

This implementation demonstrates a single-agent architecture where the authenticated OCI IAM user token is propagated through the application and used for database authorization.

---
## Prerequisites

Before running the demo, ensure the following components are configured.

### Database

* Oracle Database configured with a TCPS listener.
* SSL certificates and wallets configured for secure client-server communication.

### OCI IAM

* OCI IAM Domain configured.
* Client application, Midtier application, and Database application created and configured in OCI IAM.
* Required scopes configured.
* Employee and Manager groups created in OCI IAM.
* End-user accounts created and assigned to the appropriate groups.

### Local Environment

* OCI SDK configuration file available under `~/.oci/config`.
* Python 3.10–3.12 installed.
* Oracle Python Driver (`oracledb`) installed.
* Access to the OCI IAM token generation scripts and configuration files.


## Steps to Reproduce

### 1. Configure OCI SDK

Create the OCI configuration directory:

```bash
mkdir -p ~/.oci
```

Create the OCI configuration file:

```bash
vi ~/.oci/config
```

Copy your OCI API private key (`.pem`) file into the OCI directory and update the configuration:

```text
[DEFAULT]
user=<user_ocid>
fingerprint=<fingerprint>
key_file=/home/<username>/.oci/oci_api_key.pem
tenancy=<tenancy_ocid>
region=us-chicago-1
```

---

### 2. Install Oracle Python Driver

Python 3.10–3.12 is recommended. The demo has been validated using Python 3.12.12.

```bash
python3.12 -m pip install oracledb
```

---

### 3. Obtain Project Files

Clone the repository and navigate to:

```text
python-langchain-oci/
```

---

### 4. Configure Environment Variables

Place the provided `.env` file under:

```text
python-langchain-oci/
```

Update all environment-specific values.

---

### 5. Update OCI IAM Configuration

Update:

```text
oci_app_default_config.ini
```

with the appropriate environment-specific values.

---

### 6. Set Up Database Objects

Modify the OCI IAM identity provider configuration section in:

```text
setup.sql
```

Run:

```sql
@setup.sql
```

This creates the required database objects, data roles, data grants, and Deep Data Security configuration used by the demo.

---

### 7. Generate OAuth Tokens

Execute:

```bash
python get_user_token.py oci_app_default_config.ini
```

The script generates:

* OCI IAM user access tokens
* Mid-tier application access tokens

and stores them under the tokens directory.

---

<<<<<<< HEAD

=======
>>>>>>> 1aaf956 (Readme updated)
### 9. Configure OCI Generative AI Settings

Update:

```text
app_config.py
```

with the appropriate:

* OCI Compartment OCID
* OCI Profile
* OCI Configuration File Location
* OCI Generative AI Model Configuration

---

### 10. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 11. Run the Application

Run as an employee user:

```bash
python3.12 langchain_app.py emma
```

Run as a manager user:

```bash
python3.12 langchain_app.py marvin
```

---

## Expected Behavior

* Employee users can access only their own HR information.
* Manager users can access information for employees within their reporting hierarchy.
* All database access is authorized using the propagated OCI IAM user identity.
