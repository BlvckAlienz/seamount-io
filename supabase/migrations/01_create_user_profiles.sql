-- File Location: backend/sql/01_create_user_profiles.sql
-- Description: Creates the public user_profiles table, sets up the trigger, and enables RLS.

-- 1. Drop existing trigger and function if they exist to ensure a clean slate.
drop trigger if exists on_auth_user_created on auth.users;
drop function if exists public.handle_new_user;

-- 2. Create the user_profiles table.
-- This table will store public-facing user data that complements the private auth.users table.
create table if not exists public.user_profiles (
  id uuid references auth.users not null primary key,
  updated_at timestamp with time zone,
  email varchar(255) unique,
  first_name text,
  last_name text,
  country_code varchar(2),
  kyc_level int default 0 not null,
  kyc_status text default 'none' not null,
  algorand_address text,
  evm_address text,
  
  constraint email_validation check (email ~* '^[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$')
);

-- 3. Create the function to populate user_profiles on new user signup.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.user_profiles (id, email, updated_at)
  values (new.id, new.email, now());
  return new;
end;
$$;

-- 4. Create the trigger to call the function when a new user is created in auth.users.
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- 5. Enable Row Level Security (RLS) on the user_profiles table.
-- This is a critical security step.
alter table public.user_profiles enable row level security;

-- 6. Create RLS policies.
-- These policies define who can access or modify which rows.
drop policy if exists "Users can view their own profile." on public.user_profiles;
create policy "Users can view their own profile."
on public.user_profiles for select
using ( auth.uid() = id );

drop policy if exists "Users can update their own profile." on public.user_profiles;
create policy "Users can update their own profile."
on public.user_profiles for update
using ( auth.uid() = id );

-- Optional: Add a comment to the table for clarity
comment on table public.user_profiles is 'Public profile information for each user, linked to auth.users.';