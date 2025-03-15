FROM rust:1.70-slim as builder

WORKDIR /app
RUN apt-get update && apt-get install -y pkg-config libssl-dev

COPY Cargo.toml Cargo.lock ./
COPY src ./src

RUN cargo build --release

FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y ca-certificates libssl1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/genesis ./
COPY data ./data

ENV RUST_LOG=info
CMD ["./genesis"]
