# Push This Project to GitHub – Step by Step

## Prerequisites
- **Git** installed on your PC. Check: open PowerShell and run `git --version`. If not installed: [git-scm.com](https://git-scm.com/download/win).
- A **GitHub** account. Create one at [github.com](https://github.com) if needed.

---

## Part 1: Create a New Repository on GitHub

1. Log in to [github.com](https://github.com).
2. Click the **+** icon (top right) → **New repository**.
3. Fill in:
   - **Repository name:** e.g. `criminal-detection-system` (or any name you like).
   - **Description:** optional (e.g. "Criminal Detection System - Web App").
   - **Public** (recommended for free).
   - **Do not** check "Add a README", "Add .gitignore", or "Choose a license" (your project already has these).
4. Click **Create repository**.
5. On the next page you’ll see a URL like:
   `https://github.com/YOUR_USERNAME/criminal-detection-system.git`
   Copy this URL — you’ll use it in Part 2.

---

## Part 2: Push Your Local Project to GitHub

Open **PowerShell** (or Command Prompt) and run these commands **one by one**.

### Step 1: Go to your project folder
```powershell
cd "c:\Users\AT\Desktop\cm system"
```

### Step 2: See if a remote named `origin` already exists
```powershell
git remote -v
```
- If you see `origin` pointing to a GitHub URL: that’s your existing repo. Skip Step 3 and go to Step 4.
- If you see nothing (or you want to use a **new** repo): continue to Step 3.

### Step 3: Connect to your GitHub repo (only if needed)
Replace `YOUR_USERNAME` and `REPO_NAME` with your actual GitHub username and repo name:
```powershell
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
```
Example:
```powershell
git remote add origin https://github.com/john/criminal-detection-system.git
```
If you already had `origin` and want to **change** it to a new repo:
```powershell
git remote set-url origin https://github.com/YOUR_USERNAME/REPO_NAME.git
```

### Step 4: Stage all files
```powershell
git add .
```

### Step 5: Commit
```powershell
git commit -m "Add web app and deployment setup"
```

### Step 6: Push to GitHub
First time (and if your branch is `main`):
```powershell
git push -u origin main
```
If GitHub told you to use `master` instead of `main`:
```powershell
git push -u origin master
```
Later, you can just run:
```powershell
git push
```

---

## If Git Asks for Username/Password

- **Username:** your GitHub username.
- **Password:** do **not** use your GitHub account password. Use a **Personal Access Token**:
  1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
  2. **Generate new token (classic)**.
  3. Give it a name, check **repo**, then generate.
  4. Copy the token and paste it when Git asks for a password.

---

## Quick Reference (after repo is connected)

Whenever you make changes and want to update GitHub:

```powershell
cd "c:\Users\AT\Desktop\cm system"
git add .
git commit -m "Describe your change here"
git push
```
