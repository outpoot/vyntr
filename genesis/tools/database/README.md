# Database Tools

Tools for setting up and managing the PostgreSQL (vector) database.

## Overview
> [!NOTE]
> Update the password in `docker-compose.yml` before deployment.
> Never use the default password in production.

Get started with:
```bash
docker compose up -d
```

```bash
psql -h localhost -U postgres -f init.sql
```
Please add your connection URI to `.env` in the main folder of this repository, as mentioned in the main `README.md`.

```javascript
// ...
PRIVATE_DB_URL="postgresql://postgres:REPLACE_ME@localhost:5432/search_db"
// ...
```