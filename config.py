# Supabase Configuration
# Use env vars on production (e.g. Render): SUPABASE_URL, SUPABASE_KEY, TABLE_NAME
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yiucslrokdevbvhxbvlk.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlpdWNzbHJva2RldmJ2aHhidmxrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc3MTk0MTEsImV4cCI6MjA4MzI5NTQxMX0.yr4nQZN0i-sbnjVGc9JwVLo8H52Bhcq9bHYri2wNx5o")
TABLE_NAME = os.environ.get("TABLE_NAME", "criminaldata")

