# AWS to Supabase Migration Guide

## ✅ Migration Complete!

Your Criminal Detection System has been successfully migrated from AWS RDS MySQL to Supabase PostgreSQL.

## What Was Changed

### 1. Database Migration
- **Old**: AWS RDS MySQL (`criminaldb.cpk0ayggcs0v.eu-north-1.rds.amazonaws.com`)
- **New**: Supabase PostgreSQL (`yiucslrokdevbvhxbvlk.supabase.co`)

### 2. Code Changes
- **dbHandler.py**: Updated to use Supabase Python client instead of pymysql
- **config.py**: Created new configuration file with Supabase credentials
- **requirements.txt**: Updated dependencies (removed pymysql, added supabase)

### 3. Database Schema
The `criminaldata` table has been created in Supabase with the following structure:
- `id` (SERIAL PRIMARY KEY) - Auto-incrementing ID
- `name` (VARCHAR) - Criminal name
- `father_name` (VARCHAR) - Father's name
- `mother_name` (VARCHAR) - Mother's name
- `gender` (VARCHAR) - Gender
- `dob` (DATE) - Date of birth
- `blood_group` (VARCHAR) - Blood group
- `identification_mark` (TEXT) - Identification marks
- `nationality` (VARCHAR) - Nationality
- `religion` (VARCHAR) - Religion
- `crimes_done` (TEXT) - Crimes committed

## Configuration

Your Supabase credentials are stored in `config.py`:
- **Project URL**: `https://yiucslrokdevbvhxbvlk.supabase.co`
- **API Key**: Configured (anon/public key)

## Next Steps

### 1. Test the Connection
Run your application to verify everything works:
```bash
python home.py
```

### 2. Migrate Existing Data (Optional)
If you have existing data in your AWS RDS database that you want to migrate:

1. Export data from AWS RDS:
   ```sql
   SELECT * FROM criminaldata;
   ```

2. Import to Supabase using the Supabase dashboard or SQL editor

### 3. Security Considerations
- The current API key in `config.py` is the public (anon) key, which is safe for client-side use
- For production, consider using environment variables:
  ```python
  import os
  SUPABASE_URL = os.getenv("SUPABASE_URL")
  SUPABASE_KEY = os.getenv("SUPABASE_KEY")
  ```

### 4. Row Level Security (RLS)
RLS is enabled on the `criminaldata` table with a permissive policy. For production, you should:
- Create proper authentication
- Set up more restrictive RLS policies based on user roles
- Use service role key for server-side operations (keep it secret!)

## Benefits of Supabase

1. **Free Tier**: Generous free tier for development
2. **Real-time**: Built-in real-time subscriptions (if needed later)
3. **Storage**: Can store images in Supabase Storage (future enhancement)
4. **API**: Automatic REST API generation
5. **Dashboard**: Easy-to-use web interface for database management

## Troubleshooting

### Connection Issues
- Verify your Supabase project is active
- Check that the API key in `config.py` is correct
- Ensure your internet connection is working

### Data Format Issues
- Date format: Use YYYY-MM-DD format for dates
- Text fields: All text is automatically handled

## Support

- Supabase Dashboard: https://supabase.com/dashboard
- Supabase Docs: https://supabase.com/docs
- Your Project: https://yiucslrokdevbvhxbvlk.supabase.co

