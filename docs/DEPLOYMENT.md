# Deployment Guide

## ✅ New Simple Architecture

**Everything in .env** - Same config for local and production!

---

## 🏠 Local Development

**Just start the servers:**

```bash
# Terminal 1 - Backend (reads .env automatically)
.venv\Scripts\python.exe -m uvicorn src.ai_commerce_gateway.api.app:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

**That's it!** No YAML files to manage. Everything in `.env`

---

## 🚀 Production Deployment (Render)

### Step 1: Push Code to GitHub

```bash
git add .
git commit -m "feat: complete image upload and exports"
git push origin main
```

### Step 2: Deploy Backend to Render

1. Go to: https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Render will auto-detect `deploy/render.yaml`

### Step 3: Add Environment Variables

**In Render Dashboard → Environment tab, add these:**

```bash
# Database (Production - Use PostgreSQL)
DATABASE_URL=postgresql://postgres:[REDACTED]@db.kzukufnkjriccoztuggu.supabase.co:5432/postgres

# LLM
FIREWORKS_API_KEY=[REDACTED]
LLM_MODEL=openai/accounts/fireworks/models/glm-5p2
LLM_BASE_URL=https://api.fireworks.ai/inference/v1

# Storage (Production - Use Supabase)
STORAGE_PROVIDER=supabase
STORAGE_BUCKET=product-images
SUPABASE_URL=https://kzukufnkjriccoztuggu.supabase.co
SUPABASE_SERVICE_ROLE_KEY=[REDACTED]

# Razorpay
RAZORPAY_KEY_ID=[REDACTED]
RAZORPAY_KEY_SECRET=[REDACTED]

# Sessions (Render auto-generates these)
BUYER_SESSIONS_SECRET=[Leave blank - Render generates]
BUYER_SESSIONS_ISSUER_KEY=[Leave blank - Render generates]
```

**Click "Save Changes"** → Render auto-deploys!

### Step 4: Deploy Frontend to Vercel

1. Go to: https://vercel.com/
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repository
4. Set **Root Directory:** `frontend`
5. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
   ```
6. Click **"Deploy"**

---

## 🔄 Update Configuration After Deployment

### Change Database
```bash
# In Render Dashboard → Environment
DATABASE_URL=postgresql://new-database-url
```
**Save** → Auto-redeploys

### Change Storage Provider
```bash
# Switch from local to Supabase
STORAGE_PROVIDER=supabase

# Or switch to S3
STORAGE_PROVIDER=s3
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```
**Save** → Auto-redeploys

### Change LLM Provider
```bash
# Switch from Fireworks to OpenAI
FIREWORKS_API_KEY=sk-...  # Use OpenAI key
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=  # Remove (OpenAI is default)
```
**Save** → Auto-redeploys

---

## 📊 Configuration Matrix

| Environment | Database | Storage | Config Location |
|-------------|----------|---------|-----------------|
| **Local** | SQLite | Local files | `.env` file |
| **Production** | PostgreSQL | Supabase Storage | Render dashboard |

---

## 🎯 Benefits of This Approach

✅ **Same config system everywhere** - no surprises  
✅ **Easy to switch providers** - change one env var  
✅ **Test prod config locally** - copy .env values  
✅ **No YAML confusion** - one source of truth  
✅ **Git-safe** - .env is gitignored  

---

## 🐛 Troubleshooting

### "Environment variable not found"
**Check:** `.env` file exists and has the variable  
**Fix:** Copy from `.env.example` template

### "Database connection failed"
**Check:** `DATABASE_URL` is correct  
**Fix:** Verify password has no spaces

### "Storage not configured"
**Check:** `STORAGE_PROVIDER` is set  
**Fix:** Set to `local`, `supabase`, `s3`, or `gcs`

---

## 📝 Quick Reference

**Local Setup:**
1. Copy `.env.example` → `.env`
2. Fill in your secrets
3. `uvicorn ...` (backend reads .env)

**Deploy:**
1. Copy all `.env` variables → Render dashboard
2. Change `DATABASE_URL` → PostgreSQL
3. Change `STORAGE_PROVIDER` → supabase
4. Deploy!

---

**Simple, consistent, works everywhere!** 🚀
