# LangChain Agent Sample HR application

This is a sample Python application that uses the Deep Data Security
feature of Oracle Database.

This sample application uses Python, LangChain, and 
OCI Generative AI Service to build a natural language HR assistant 
over Oracle HR.EMPLOYEES.

The Oracle Python EndUserSecurityContext provider is configured to
propagate the authenticated end user's security context to the database,
where Deep Data Security data grants enforce row and column level access
control based on the user's privileges.

OCI Generative AI Service is used as the LLM provider through 
LangChain's ChatOCIGenAI integration. 
Similar initialization can be done for other LLM providers
supported by LangChain.

---

## Project Structure

```text
langchain_demo/

langchain_app.py          (Application entry point)
langchain_tools.py        (LangChain tools and prompts)
db_connection.py          (Oracle DB connection setup)
get_user_token.py         (MSEI authentication)
app_config.py             (Application configuration)
requirements.txt          (Dependencies)

```

---

## Prerequisites

* Python 3.11+ (newer Python versions are also supported)
* Oracle Database with Deep Data security feature enabled
* MSEI setup
* OCI Generative AI access (Or any other LLM provider supported by LangChain)

Oracle Database, Entra ID applications, users, roles, and 
Deep Data Security policies should be configured 
according to the quick-start guide.

https://docs-uat.us.oracle.com/en/database/oracle/oracle-database/26/ddscg/configure-oracle-deep-data-security-sample-application.html#GUID-0569587E-2D81-4109-878D-EFE9A36258B5

---
## Configure OCI SDK

Create the OCI configuration directory inside your home directory:

```bash
mkdir -p ~/.oci
```
Create the OCI config file:

```bash
vi ~/.oci/config
```
Copy your OCI API private key (`.pem`) file into the OCI directory.
Paste your OCI SDK configuration into the file:

```bash
[idcs-ord]
user=<user_ocid>
fingerprint=<fingerprint>
key_file=/home/<username>/.oci/oci_api_key.pem
tenancy=<tenancy_ocid>
region=us-chicago-1
```
## Install Oracle Python Driver

Python 3.10–3.12 is recommended. The demo has been validated using Python 3.12.12.

```bash
python3.12 -m pip install oracledb
```

Verify the installation:
```bash
python3.12 -c "import oracledb; print(oracledb.__version__)"
```
Output:
```bash
4.0.0b1
```
## Update app_config.py

Update the values in `app_config.py` before running the application.
For the list of all available Generative AI models (including their IDs),
visit the official Oracle documentation at: 
https://docs.oracle.com/en-us/iaas/Content/generative-ai/model-endpoint-regions.htm

## Setup Script

Run the setup script to create Deep Data Security entities before starting the application.
Update `setup.sql` with your environment-specific application and database values.


```bash
sqlplus sys/<password>@<db> as sysdba
@setup.sql
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Setup Proxy

Set up the required network/database proxy before running the application.

---

## Run the Application

```bash
python3.12 langchain_app.py
```

---

## Example Query

```text
Show employee salaries that are visible to me
```

---

