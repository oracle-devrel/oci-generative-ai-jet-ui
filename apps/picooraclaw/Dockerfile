# ============================================================
# Stage 1: Build the picooraclaw binary
# ============================================================
FROM golang:1.24-alpine AS builder

RUN apk add --no-cache git make

WORKDIR /src

# Cache dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source and build
COPY . .
RUN make build

# ============================================================
# Stage 2: Minimal runtime image
# ============================================================
FROM alpine:3.21

RUN apk add --no-cache ca-certificates tzdata curl

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://localhost:18790/health || exit 1

# Copy binary
COPY --from=builder /src/build/picooraclaw /usr/local/bin/picooraclaw

# Create picooraclaw home directory
RUN /usr/local/bin/picooraclaw onboard

ENTRYPOINT ["picooraclaw"]
CMD ["gateway"]
