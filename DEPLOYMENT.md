# Quick Deployment Guide

## Fastest Options (5-10 minutes)

### 1. RENDER.COM (Recommended - 100% Free)

**Step-by-step:**

1. Go to https://render.com and sign up (use GitHub account)

2. Click "New +" button → Select "Web Service"

3. Connect your GitHub repository
   - If not connected, click "Connect GitHub" and authorize
   - Search for your repository name

4. Configure your service:
   - **Name**: `invoice-generator` (or your choice)
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: Leave empty
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

5. Select Free Plan (0$/month)

6. Click "Create Web Service"

7. Wait 5-10 minutes for deployment

8. Your app will be live at: `https://invoice-generator-xxxx.onrender.com`

**Notes:**
- Free tier spins down after 15 minutes of inactivity
- Takes ~30 seconds to wake up on first request
- Perfect for personal use

---

### 2. PYTHONANYWHERE (Free - Easy Setup)

**Step-by-step:**

1. Create account at https://www.pythonanywhere.com

2. Go to "Files" tab → Upload files OR use Git:
   ```bash
   git clone https://github.com/yourusername/invoice-generator.git
   ```

3. Open a Bash console and install dependencies:
   ```bash
   cd invoice-generator
   pip install --user -r requirements.txt
   ```

4. Go to "Web" tab → "Add a new web app"
   - Choose "Flask"
   - Python version: 3.10
   - Path: `/home/yourusername/invoice-generator/app.py`

5. Edit WSGI configuration file:
   ```python
   import sys
   path = '/home/yourusername/invoice-generator'
   if path not in sys.path:
       sys.path.append(path)
   
   from app import app as application
   ```

6. Reload web app

7. Visit: `https://yourusername.pythonanywhere.com`

---

### 3. RAILWAY (Very Easy)

**Step-by-step:**

1. Go to https://railway.app and sign up

2. Click "New Project" → "Deploy from GitHub repo"

3. Connect GitHub and select repository

4. Railway auto-detects and deploys (no configuration needed!)

5. Click "Generate Domain" under settings

6. Your app is live at the generated URL

**Note:** Free tier includes $5 credit/month

---

## Push to GitHub First

Before deploying, push your code:

```bash
# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Invoice generator web app"

# Create repository on GitHub, then:
git remote add origin https://github.com/yourusername/invoice-generator.git
git branch -M main
git push -u origin main
```

---

## Testing Locally First

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Visit http://localhost:5000
```

---

## Troubleshooting

### App won't start?
- Check logs in platform dashboard
- Ensure requirements.txt is correct
- Verify Python version compatibility

### Can't generate PDF?
- Check file permissions
- Ensure `generated_invoices` folder is created (app does this automatically)

### Site is slow?
- Free tiers sleep after inactivity
- Consider upgrading to paid tier if needed
- Render: ~$7/month for always-on
- PythonAnywhere: ~$5/month

---

## Recommended: RENDER

For most users, Render is the best choice:
✅ Completely free
✅ Automatic deployments from GitHub
✅ Easy setup
✅ Good performance
✅ Reliable

Only downside: 15-minute inactivity timeout (acceptable for personal use)
