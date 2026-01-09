-- Starter schema for the digital assistant.
-- Adjust table names and foreign keys to match your app's auth model.

create extension if not exists "pgcrypto";

create table if not exists assistant_user_prefs (
  user_id uuid primary key,
  timezone text not null default 'UTC',
  summary_time time not null default '08:00',
  summary_enabled boolean not null default true,
  delivery_channels text[] not null default '{sms}',
  phone_number text,
  summary_last_sent_on date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists assistant_daily_summaries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  summary_date date not null,
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists assistant_daily_summaries_user_date_idx
  on assistant_daily_summaries (user_id, summary_date);

create table if not exists assistant_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  flow text not null,
  status text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  metadata jsonb
);

create table if not exists assistant_notification_outbox (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  channel text not null,
  payload jsonb not null,
  status text not null default 'pending',
  sent_at timestamptz,
  created_at timestamptz not null default now()
);
