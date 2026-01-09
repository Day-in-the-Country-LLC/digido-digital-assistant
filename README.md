# digido-digital-assistant

LangGraph-powered orchestration service for Digido. This repo hosts the API, the worker that runs assistant flows, and scheduled jobs.

## Local setup

```bash
uv venv
uv sync
```

Create a local env file:

```bash
cp .env.example .env
```

Run the API:

```bash
uv run uvicorn digido_digital_assistant.main:app --reload
```

Run the worker (for scheduled jobs):

```bash
uv run python -m digido_digital_assistant.worker
```

## Environment variables

See `.env.example` for all options. The minimum to hit Supabase and Twilio:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`

## Deployment (GCP)

Recommended:
- Cloud Run service for the API
- Cloud Run job for the worker
- Cloud Scheduler to invoke the worker on a cadence (e.g., every 10 minutes)

The worker determines which users are due based on their timezone and summary preferences stored in Supabase.

## Database setup

A starter schema is in `docs/supabase_schema.sql`. Adjust table names to match your app's existing user/auth model.
