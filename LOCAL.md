# Run Local

## Web

Run locally in a terminal with:

```bash
cd web
```

```bash
npm run dev
```

## Backend

Run locally on another terminal with:

```bash
cd backend
```

Edit `/backend/src/main/resources/application.yaml` to have the correct values.

```bash
./gradlew bootRun
```

## Build for distribution

## Build artifacts

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
