FROM rust:1.81-slim as builder

WORKDIR /usr/src/genesis
COPY . .

RUN apt-get update && apt-get install -y pkg-config libssl-dev && \
    cargo build --release --target-dir /usr/src/genesis/target

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y ca-certificates libssl3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/src/genesis/target/release/genesis /app/
COPY data /app/data

ENV RUST_LOG=info
CMD ["./genesis"]
