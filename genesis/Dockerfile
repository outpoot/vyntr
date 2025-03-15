FROM rust:1.81-slim as builder

WORKDIR /usr/src/genesis
COPY . .

RUN apt-get update && apt-get install -y pkg-config libssl-dev \
    && cargo build --release

FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y ca-certificates libssl1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/local/bin
COPY --from=builder /usr/src/genesis/target/release/genesis .
COPY data /usr/local/bin/data

ENV RUST_LOG=info
CMD ["genesis"]
