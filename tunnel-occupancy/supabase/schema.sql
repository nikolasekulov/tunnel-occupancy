create table if not exists public.occupancy (
 observed_at timestamptz primary key,
 percentage numeric(5,2) not null check (percentage >= 0 and percentage <= 100),
 source text not null default 'nonstopgym-tunnel'
);
create index if not exists occupancy_recent_idx on public.occupancy (observed_at desc);
alter table public.occupancy enable row level security;
-- Read-only public dashboard. Writes require the server-side service role key.
create policy "Anyone can read measured occupancy" on public.occupancy for select to anon using (true);
grant select on public.occupancy to anon;
