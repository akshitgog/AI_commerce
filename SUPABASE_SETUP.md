# Supabase Setup Guide

## ✅ Your Supabase Project

**Project Name:** ai-commerce-gateway  
**Project ID:** kzukufnkjriccoztuggu  
**Region:** us-east-1  
**Status:** ACTIVE_HEALTHY

**URLs:**
- Dashboard: https://supabase.com/dashboard/project/kzukufnkjriccoztuggu
- API: https://kzukufnkjriccoztuggu.supabase.co
- Database: db.kzukufnkjriccoztuggu.supabase.co

---

## 🔐 API Keys

### Anon Key (Client-side - already configured)
```
[REDACTED]
```

### Service Role Key (Needed for Storage)
**Get it here:** https://supabase.com/dashboard/project/kzukufnkjriccoztuggu/settings/api

Copy the **service_role** key (the longer one under "Project API keys")

---

## 📦 Step-by-Step Setup

### 1. Create Storage Bucket

Go to: https://supabase.com/dashboard/project/kzukufnkjriccoztuggu/storage/buckets

Click **"New bucket"**:
- **Name:** `product-images`
- **Public bucket:** ✅ Yes (so images are publicly accessible)
- Click **"Create bucket"**

### 2. Set Bucket Policies (Make it Public)

After creating the bucket:
1. Click on `product-images` bucket
2. Go to **"Policies"** tab
3. Click **"New Policy"**
4. Select **"For full customization"**
5. Add this policy:

```sql
-- Allow public read access to all images
CREATE POLICY "Public Access"
ON storage.objects FOR SELECT
USING ( bucket_id = 'product-images' );

-- Allow authenticated uploads (service role)
CREATE POLICY "Service Role Upload"
ON storage.objects FOR INSERT
WITH CHECK ( bucket_id = 'product-images' );

-- Allow authenticated deletes (service role)
CREATE POLICY "Service Role Delete"
ON storage.objects FOR DELETE
USING ( bucket_id = 'product-images' );
```

**Or use the quick template:**
- Click **"Create policy from template"**
- Select **"Allow public read access"**
- Enable for bucket `product-images`

### 3. Get Database Password

Go to: https://supabase.com/dashboard/project/kzukufnkjriccoztuggu/settings/database

Find **"Connection string"** section and copy the password OR generate a new one.

Your connection string format:
```
postgresql://postgres:[YOUR-PASSWORD]@db.kzukufnkjriccoztuggu.supabase.co:5432/postgres
```

---

## 🔧 Environment Configuration

### Local Development (.env or config/local.yaml)

```bash
# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.kzukufnkjriccoztuggu.supabase.co:5432/postgres

# Storage (Supabase Storage)
STORAGE_PROVIDER=supabase
STORAGE_BUCKET=product-images
SUPABASE_URL=https://kzukufnkjriccoztuggu.supabase.co
SUPABASE_SERVICE_ROLE_KEY=[YOUR-SERVICE-ROLE-KEY]
SUPABASE_ANON_KEY=[REDACTED]

# LLM (keep your existing key)
FIREWORKS_API_KEY=[REDACTED]

# Razorpay (keep your existing keys)
RAZORPAY_KEY_ID=[REDACTED]
RAZORPAY_KEY_SECRET=[YOUR-SECRET]
```

### Production Deployment (Render)

Add these environment variables in Render dashboard:

```bash
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.kzukufnkjriccoztuggu.supabase.co:5432/postgres
STORAGE_PROVIDER=supabase
STORAGE_BUCKET=product-images
SUPABASE_URL=https://kzukufnkjriccoztuggu.supabase.co
SUPABASE_SERVICE_ROLE_KEY=[YOUR-SERVICE-ROLE-KEY]
```

---

## 🧪 Testing Setup

### 1. Test Database Connection

```bash
# Install psql if needed, then:
psql "postgresql://postgres:[PASSWORD]@db.kzukufnkjriccoztuggu.supabase.co:5432/postgres"
```

Should connect successfully.

### 2. Test Storage Upload

After starting your backend:
```bash
# Backend will auto-create tables on first run
uvicorn src.ai_commerce_gateway.api.app:app --reload
```

Go to: http://localhost:3000/merchant/ai-catalog
- Upload an image
- Check Supabase Storage dashboard - should see the file!

### 3. Verify Image URL

Images will be available at:
```
https://kzukufnkjriccoztuggu.supabase.co/storage/v1/object/public/product-images/merchants/mer_demo/products/prod_xxx/pimg_xxx_filename.jpg
```

---

## 📊 Free Tier Limits

✅ **Database:** 500MB storage, unlimited queries  
✅ **Storage:** 1GB files, 2GB bandwidth/month  
✅ **Edge Functions:** 500,000 invocations/month  
✅ **Auth:** Unlimited users  

**Your use case:** 
- 1 product with 3 images (5MB each) = **15MB total** ✅ Way under limit!
- Multi-day demo with 50-100 products = **~1GB** ✅ Still fine!

---

## ⚠️ Important Notes

1. **Service Role Key is SECRET** - Never commit to git or share publicly
2. **Database sleeps after 1 week** of inactivity (free tier) - just visit any page to wake it up
3. **Images are PUBLIC** - anyone with the URL can view them (by design)
4. **SSL enforced** - All connections are encrypted

---

## 🐛 Troubleshooting

### "Failed to upload to Supabase Storage"
- Check service role key is correct
- Verify bucket exists and is public
- Check bucket policies allow uploads

### "Database connection failed"
- Check password is correct (no spaces)
- Verify project isn't paused (dashboard shows status)
- Test with psql first

### "Images not loading"
- Check bucket is public
- Verify RLS policies allow SELECT
- Test direct URL in browser

---

## 🎉 You're All Set!

Once you've:
1. ✅ Created `product-images` bucket (public)
2. ✅ Added service role key to env vars
3. ✅ Updated database URL

Your app will:
- ✅ Store all data in Supabase PostgreSQL (persistent)
- ✅ Upload images to Supabase Storage (free CDN)
- ✅ Serve images with fast global delivery
- ✅ Work for multi-day demos without data loss

**Next:** Start your servers and test image upload!
