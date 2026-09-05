# Testing Guide: Image Upload & Supabase Integration

## 🎯 What We Implemented

✅ **Phase 1:** Image Upload System (Local + S3 + GCS + Supabase)
✅ **Phase 2:** LLM Error Handling UI
✅ **Phase 3:** Download Exports (Audit + Transactions)
✅ **Supabase:** Project created, ready to use

---

## 🚀 Quick Test (5 minutes)

### Step 1: Start Backend (Terminal 1)
```bash
cd C:\Users\Galactus\OneDrive\Desktop\commerce-integrated
.venv\Scripts\python.exe -m uvicorn src.ai_commerce_gateway.api.app:app --host 127.0.0.1 --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Step 2: Start Frontend (Terminal 2)
```bash
cd C:\Users\Galactus\OneDrive\Desktop\commerce-integrated\frontend
npm run dev
```

**Expected output:**
```
▲ Next.js 15.1.6
- Local:        http://localhost:3000
```

### Step 3: Test Image Upload
1. Open: http://localhost:3000/merchant/ai-catalog
2. Enter product description: "USB Cable, $10, 100 units"
3. Click **"Generate"** → AI extracts fields
4. **Upload 1-3 images** (JPEG/PNG, < 5MB each)
5. Click **"Create Draft"**
6. ✅ Verify images appear in product list

**Where images are stored:**
- Local: `uploads/merchants/mer_demo/products/prod_xxx/pimg_xxx_image.jpg`
- Accessible at: `http://localhost:8000/media/merchants/.../image.jpg`

---

## 📸 Test Features

### 1. Image Upload ✅
- ✅ Upload up to 3 images per product
- ✅ Supports JPEG, PNG, WebP, GIF
- ✅ Max 5MB per image
- ✅ Images served at `/media` endpoint
- ✅ Delete images via product editor

### 2. LLM Error Handling ✅
**Test it:**
1. Remove API key from `.env` (comment out `FIREWORKS_API_KEY`)
2. Try AI Catalog
3. ✅ Should see warning banner with "Use Manual Catalog" link

### 3. Download Exports ✅
**Test audit export:**
1. Create a test transaction (use buyer chat)
2. Go to: http://localhost:3000/merchant/audit
3. Select transaction
4. Click **"CSV"** or **"JSON"** button
5. ✅ File downloads automatically

**Test transaction export:**
1. Go to: http://localhost:3000/merchant/transactions
2. Click **"CSV"** or **"JSON"** button
3. ✅ Downloads transaction list

---

## 🔄 Switch to Supabase (Optional)

### Current Setup (Working)
```yaml
# config/local.yaml
database:
  url: sqlite:///commerce_dev.db
storage:
  provider: local
```

**Pros:** ✅ Works immediately, no setup
**Cons:** ❌ Data lost on deployment restart

---

### Supabase Setup (Persistent)

#### Option 1: Supabase Storage Only
Keep SQLite, use Supabase for images:

```yaml
# config/local.yaml
database:
  url: sqlite:///commerce_dev.db  # Keep SQLite
storage:
  provider: supabase  # Use Supabase Storage
```

**Setup steps:**
1. Create `product-images` bucket: https://supabase.com/dashboard/project/kzukufnkjriccoztuggu/storage/buckets
2. Make it public (enable "Public bucket")
3. Restart backend

**Pros:** ✅ Images persist forever (1GB free)
**Cons:** ❌ Still using SQLite (local data)

---

#### Option 2: Full Supabase (Database + Storage)

```yaml
# config/local.yaml
database:
  url: postgresql://postgres:[PASSWORD]@db.kzukufnkjriccoztuggu.supabase.co:5432/postgres
storage:
  provider: supabase
```

**Setup steps:**
1. Install PostgreSQL driver:
   ```bash
   pip install psycopg[binary]
   ```
2. Get database password: https://supabase.com/dashboard/project/kzukufnkjriccoztuggu/settings/database
3. Create `product-images` bucket (see Option 1)
4. Update `config/local.yaml` with password
5. Restart backend

**Pros:** ✅ Everything persists, production-ready
**Cons:** ❌ 5 min setup

---

## 🐛 Troubleshooting

### Backend won't start
**Error:** `ModuleNotFoundError: No module named 'psycopg2'`
**Fix:** You're using PostgreSQL URL but driver not installed
```bash
pip install psycopg[binary]
# OR switch back to SQLite in config/local.yaml
```

### Images not uploading
**Check:**
1. Is `STORAGE_PROVIDER` set correctly?
2. Does `uploads/` directory exist? (created automatically)
3. Check browser console for errors
4. Verify backend logs show the upload attempt

### Supabase connection fails
**Check:**
1. Is `SUPABASE_SERVICE_ROLE_KEY` in `.env`?
2. Did you create the `product-images` bucket?
3. Is the bucket public?
4. Check Supabase project isn't paused (free tier sleeps after 1 week inactivity)

### LLM error banner not showing
**Check:**
1. Is API key actually removed/invalid?
2. Check browser console for `ApiError`
3. Verify backend returns 502 status (check Network tab)

---

## 📊 Current Configuration

**Database:** SQLite (local file `commerce_dev.db`)
**Storage:** Local filesystem (`uploads/` directory)
**LLM:** Fireworks AI (key in `.env` or `config/local.yaml`)

**Supabase Project:**
- **URL:** https://kzukufnkjriccoztuggu.supabase.co
- **Database:** PostgreSQL 17 (ready to use)
- **Storage:** 1GB free (bucket needs to be created)

---

## 🎉 Success Criteria

After testing, you should have:

✅ **Local Demo Working:**
- Backend running on port 8000
- Frontend running on port 3000
- Can create products with AI extraction
- Can upload 1-3 images per product
- Images display in product list
- Can export audit trails (CSV/JSON)
- Can export transactions (CSV/JSON)
- LLM error handling works

✅ **Ready for Deployment:**
- All code committed to Git
- `.env` in `.gitignore` (secrets safe)
- Render config ready (`deploy/render.yaml`)
- Vercel config ready (`deploy/vercel.json`)
- Supabase project created (optional)

---

## 📦 Files Created/Modified

### Backend
- ✅ `src/ai_commerce_gateway/storage/s3.py` - AWS S3 implementation
- ✅ `src/ai_commerce_gateway/storage/gcs.py` - Google Cloud Storage
- ✅ `src/ai_commerce_gateway/storage/supabase.py` - Supabase Storage
- ✅ `src/ai_commerce_gateway/storage/factory.py` - Storage factory
- ✅ `src/ai_commerce_gateway/api/merchant/router.py` - Image upload endpoints
- ✅ `src/ai_commerce_gateway/api/app.py` - Static file serving
- ✅ `src/ai_commerce_gateway/core/config.py` - Cloud storage config

### Frontend
- ✅ `frontend/src/lib/api/client.ts` - Image upload API methods
- ✅ `frontend/src/lib/services/store.ts` - Real image upload/delete
- ✅ `frontend/src/app/merchant/ai-catalog/page.tsx` - Image upload UI + error banner
- ✅ `frontend/src/app/merchant/audit/page.tsx` - Export buttons
- ✅ `frontend/src/app/merchant/transactions/page.tsx` - Export buttons

### Configuration
- ✅ `config/default.yaml` - Changed to `storage.provider: local`
- ✅ `config/local.yaml` - SQLite + local storage config
- ✅ `.env` - Supabase credentials
- ✅ `deploy/render.yaml` - Cloud storage env vars
- ✅ `.env.example` - Complete documentation
- ✅ `pyproject.toml` - Added boto3 + google-cloud-storage

### Documentation
- ✅ `IMPLEMENTATION_SUMMARY.md` - Complete feature docs
- ✅ `SUPABASE_SETUP.md` - Supabase integration guide
- ✅ `TESTING_GUIDE.md` - This file

---

## ⏭️ Next Steps

1. **Test locally** (follow steps above) - 5 min
2. **Deploy to Render** - Add env vars, push to Git - 10 min
3. **Deploy to Vercel** - Connect repo, deploy - 5 min
4. **(Optional) Setup Supabase Storage** - Create bucket - 5 min

**Total time to production:** ~25 minutes

---

## 💡 Pro Tips

1. **Use Supabase for multi-day demos** - Files persist, no data loss
2. **Use local storage for live calls** - Simpler, zero config
3. **S3/GCS for production** - Best performance, unlimited storage
4. **Export data regularly** - Use CSV/JSON exports as backup

---

**Need help?** Check `IMPLEMENTATION_SUMMARY.md` or `SUPABASE_SETUP.md` for detailed docs.

**Ready to test!** 🚀
