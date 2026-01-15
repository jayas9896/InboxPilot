# Migration Strategy

## Local-first
- Run a single process with SQLite storage.
- Optional local LLM (Ollama) for privacy-sensitive tasks.
- Environment variables for secrets.

## Single Host (Hetzner)
- Containerize services with Docker.
- Use a managed or self-hosted Postgres.
- Store attachments or transcripts in an S3-compatible object store.

## Multi-node (Hetzner)
- Introduce a task queue and worker pool.
- Split API, workers, and storage into separate containers.
- Use infrastructure-as-code to reproduce environments.

## Hyperscale (AWS/Azure/GCP)
- Replace SQL with RDS/Cloud SQL using the same schema.
- Replace object storage with S3/GCS via a storage adapter.
- Replace queue with SQS/PubSub/Kafka via a queue adapter.

## Config Separation
- Use explicit config files for local, hetzner, and public cloud profiles.
- Keep provider keys and endpoints in environment variables.
