# Deploy Criminal Detection System (Free)

**Easiest free option: Render.com** — no credit card, connect GitHub and deploy.

---

## Option 1: Render (recommended, free)

### Before you start
- Push your project to **GitHub** (if not already).
- Your **Supabase** project is already used by the app (config in `config.py`). For production, keep `config.py` as-is or use environment variables (see below).

### Steps

1. **Sign up**
   - Go to [render.com](https://render.com) → **Get Started for Free** (GitHub login).

2. **Create a Web Service**
   - Dashboard → **New +** → **Web Service**.
   - Connect your **GitHub** account and select the repo that contains this project.
   - Choose the branch (e.g. `main`).

3. **Settings**
   - **Name:** `criminal-detection-system` (or any name).
   - **Region:** Pick one close to you.
   - **Runtime:** **Python 3**.
   - **Build Command:**  
     `pip install -r requirements.txt`
   - **Start Command:**  
     `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Instance type:** **Free**.

4. **Environment variables (optional but good for production)**
   - In the same screen, open **Environment** / **Environment Variables**.
   - Add:
     - `SECRET_KEY` = any long random string (e.g. from [randomkeygen.com](https://randomkeygen.com)).
   - Your Supabase URL and key are in `config.py`. To override them on Render, add:
     - `SUPABASE_URL` = your Supabase project URL  
     - `SUPABASE_KEY` = your Supabase anon key  

5. **Deploy**
   - Click **Create Web Service**.
   - Render will build and deploy. First build can take **5–10 minutes** (OpenCV is large).
   - When it’s live, open the URL shown (e.g. `https://criminal-detection-system.onrender.com`).

6. **Usage**
   - Open the URL → login (default `admin@1234` / `12345678`) or create an account.
   - **Free tier:** service sleeps after ~15 min of no traffic; first open after that may take ~30–60 seconds to wake up.

---

## Free tier limitations (Render)

| Limitation | Detail |
|------------|--------|
| **Sleep** | Service spins down after ~15 min inactivity. Next request wakes it (may take up to ~1 min). |
| **No persistent disk** | Files written on the server (e.g. new face samples, profile pics) are **lost on redeploy or restart**. Your Supabase data stays; only server-local files don’t persist. |
| **Build time** | OpenCV makes the first build slow; that’s normal. |

To keep uploaded face images and profile pics across deploys, you’d need to store them in **Supabase Storage** (code change) or use a paid persistent disk on Render.

---

## Option 2: Railway (free tier)

1. Go to [railway.app](https://railway.app) → **Login** with GitHub.
2. **New Project** → **Deploy from GitHub repo** → select this repo.
3. Add **variables** if needed: `SECRET_KEY`, and Supabase keys if you don’t use `config.py`.
4. Railway will detect Python; set **Start Command** to:  
   `gunicorn app:app`
5. Deploy; use the generated URL.

Free tier has a monthly usage limit; after that you’d need to add a card or switch to another free option.

---

## Checklist before deploy

- [ ] Code pushed to GitHub (including `app.py`, `templates/`, `static/`, `requirements.txt`, `config.py`, `facerec.py`, `register.py`, `dbHandler.py`, `face_cascade.xml`).
- [ ] Supabase project is set up and `config.py` has the right URL, key, and table name (or use env vars on Render/Railway).
- [ ] Do **not** commit real secrets to the repo; use environment variables for production `SECRET_KEY` and Supabase keys if the repo is public.

---

## After deploy

- Use **https** (Render/Railway provide it).
- Default login: `admin@1234` / `12345678` — change password or create a new user and don’t rely on default in production.
