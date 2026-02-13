-- Run this in Supabase SQL Editor to create the criminaldata table
-- Dashboard: https://supabase.com/dashboard → Your project → SQL Editor → New query

CREATE TABLE IF NOT EXISTS criminaldata (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  father_name TEXT DEFAULT '',
  mother_name TEXT DEFAULT '',
  gender TEXT DEFAULT '',
  dob DATE,
  blood_group TEXT DEFAULT '',
  identification_mark TEXT DEFAULT '',
  nationality TEXT DEFAULT '',
  religion TEXT DEFAULT '',
  crimes_done TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- If your project uses Row Level Security (RLS), uncomment the next lines so the app can read/write:
-- ALTER TABLE criminaldata ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Allow anon access" ON criminaldata FOR ALL TO anon USING (true) WITH CHECK (true);
