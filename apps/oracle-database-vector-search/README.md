# Pet Store Vector Search Demo with Oracle AI Database and GraalVM

A Spring Boot application built with GraalVM that demonstrates semantic search using Oracle Vector Store and OpenAI embeddings.

Find full details in a [blog post](https://medium.com/oracledevs/fast-ai-search-with-graalvm-spring-boot-and-oracle-database-4e8ba46c9a74). 

## Prerequisites

- [GraalVM](https://www.graalvm.org/downloads/), or install with `sdk install java 25.0.1-graal`
- Oracle Database with Vector support (e.g., [Oracle 26ai Free](https://www.oracle.com/database/free/))
- OpenAI API key

## Configuration

### 1. Download Oracle Database Wallet for authentication

Configure and download your Autonomous Database [wallet](https://docs.oracle.com/en/cloud/paas/autonomous-database/serverless/adbsb/connect-download-wallet.html) and extract it to `src/main/resources/wallet/`.

Update the database service name in [application.properties](src/main/resources/application.properties#L3).

### 2. Set Environment Variables

```shell
export OPENAI_API_KEY=
export DB_PASSWORD=
```

## Running the Application

```shell
mvn spring-boot:run
```

The application automatically loads sample pet store inventory data on startup.

Now let's build it with Native Image:

```shell
mvn -Pnative native:compile
➜ eza -l ./target | grep "store"
... 107M ... vector-pet-store
./target/vector-pet-store
```

## API usage

You can search for the pet store items using natural language:

```shell
curl "http://localhost:8080/petstore/search?query=Treats%20for%20small%20loud%20dogs"
# or with httpie
http localhost:8080/petstore/search query=="find cat food with tuna"
```

Example requests:
- "Find dog toys" → finds "Labrador Bark Control Chews", "Heavy Duty Rope for Large Breeds"
- "Find cat food" → finds "Gourmet Tuna Soufflé for Cats", "Gourmet Chicken Soup for Cats"

The API returns semantically similar products using vector similarity search.

## Alternative: Run Oracle Database Locally

Using Docker or Podman:

```shell
podman run -d \
  -p 1521:1521 \
  --name oracle-free \
  -e ORACLE_PASSWORD=mypassword \
  -e APP_USER=appuser \
  -e APP_USER_PASSWORD=mypassword \
  -v oracle-data:/opt/oracle/oradata \
  gvenzl/oracle-free:latest
```

Update `application.properties` with the local connection details and run the app.

## Performance with GraalVM Native Image

- **Startup**: ~1.5 seconds 🚀
- **Package size**: ~107 MB standalone executable
- **Memory**: Significantly lower ☁️

Native Image compiles your Spring Boot application ahead-of-time into a self-contained executable with faster startup (typically 20-30x), lower memory footprint (typically 3-5x), and compact deployment.
