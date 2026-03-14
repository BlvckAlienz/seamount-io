-- FILE: supabase/migrations/003_p2p_jobs_queue.sql

CREATE TABLE public.p2p_jobs (
  id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  job_type     TEXT NOT NULL,
  payload      JSONB NOT NULL,
  status       TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','processing','completed','failed')),
  retry_count  INTEGER DEFAULT 0,
  max_retries  INTEGER DEFAULT 5,
  error        TEXT,
  created_at   TIMESTAMPTZ DEFAULT now(),
  updated_at   TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.p2p_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admins manage jobs" ON public.p2p_jobs
  FOR ALL USING ((auth.jwt() ->> 'role') = 'admin');