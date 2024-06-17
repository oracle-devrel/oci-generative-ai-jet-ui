# Run Local

## Run components

### Run web

Run locally in a terminal with:

```bash
cd web
```

```bash
npm run dev
```

### Run Backend

Run locally on another terminal with:

```bash
cd backend
```

Copy `/backend/src/main/resources/application.yaml` to `/backend/src/main/resources/application-local.yaml` and modify the values required.

It should look like this:

```yaml
spring:
  main:
    banner-mode: "off"
  profiles:
    active: production
  datasource:
    driver-class-name: oracle.jdbc.OracleDriver
    url: jdbc:oracle:thin:@ADB_SERVICE_NAME_GOES_HERE_high?TNS_ADMIN=/PATH/TO/WALLET/UNZIPPED/IN/TERRAFORM/GENERATED
    username: ADMIN
    password: "ADB_PASSWORD_GOES_HERE"
    type: oracle.ucp.jdbc.PoolDataSource
    oracleucp:
      sql-for-validate-connection: SELECT * FROM dual
      connection-pool-name: connectionPoolName1
      initial-pool-size: 5
      min-pool-size: 5
      max-pool-size: 10
  jpa:
    hibernate:
      use-new-id-generator-mappings: false
      ddl-auto: update
oracle:
  jdbc:
    fanEnabled: true

genai:
  endpoint: "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
  region: "us-chicago-1"
  compartment_id: "GENAI_COMPARTMENT_OCID_GOES_HERE"
  chat_model_id: "GEN_AI_CHAT_MODEL_OCID_GOES_HERE"
  summarization_model_id: "GEN_AI_SUMMARIZATION_MODEL_OCID_GOES_HERE"
```

Run the Spring Boot backend application in local profile:

```bash
./gradlew bootRun -Plocal
```

## Other tasks

### Build Java Application:

```bash
cd backend
```

```bash
./gradlew bootJar
```

> `build/libs/backend-0.0.1.jar` jar file generated

```bash
cd ..
```

### Build Web Application:

```bash
cd web
```

```bash
npm run build
```

> `dist` folder generated

```bash
cd ..
```
