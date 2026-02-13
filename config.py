# Supabase Configuration
# Use env vars on production (e.g. Render): SUPABASE_URL, SUPABASE_KEY, TABLE_NAME
import os

def _env(key, default):
    v = os.environ.get(key, "").strip()
    return v if v else default

SUPABASE_URL = _env("SUPABASE_URL", "https://yiucslrokdevbvhxbvlk.supabase.co")
SUPABASE_KEY = _env("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlpdWNzbHJva2RldmJ2aHhidmxrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc3MTk0MTEsImV4cCI6MjA4MzI5NTQxMX0.yr4nQZN0i-sbnjVGc9JwVLo8H52Bhcq9bHYri2wNx5o")
TABLE_NAME = _env("TABLE_NAME", "criminaldata")

