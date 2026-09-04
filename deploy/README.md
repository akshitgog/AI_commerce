# Free-Tier Deployment Guide

To deploy this application for free, you will use three platforms: **Neon** (Database), **Render** (Backend), and **Vercel** (Frontend).

## 1. Database (Neon.tech or Supabase)
Render's free tier deletes local files (like SQLite) when it sleeps. You need a free cloud Postgres database.
1. Go to [Neon.tech](https://neon.tech/) or [Supabase](https://supabase.com/) and create a free PostgreSQL database.
2. Copy the `DATABASE_URL` (it should look like `postgresql://user:password@host/dbname`).

## 2. Backend (Render.com)
The backend hosts the API and the embedded **MCP Servers**.
1. Push this repository to your GitHub account.
2. Go to [Render.com](https://render.com/) and click **New > Blueprint**.
3. Connect your GitHub repository. Render will automatically read the `deploy/render.yaml` file.
4. Render will ask you to fill in your environment variables:
   - `DATABASE_URL`: The URL you got from step 1.
   - `FIREWORKS_API_KEY`: Your Fireworks AI key.
   - `RAZORPAY_KEY_ID` & `RAZORPAY_KEY_SECRET`: Your Razorpay test keys.
5. Once deployed, copy your backend URL (e.g., `https://ai-commerce-backend.onrender.com`).

## 3. Frontend (Vercel.com)
1. Go to [Vercel.com](https://vercel.com/) and click **Add New > Project**.
2. Import the same GitHub repository.
3. In the setup screen, set the **Root Directory** to `frontend`.
4. Open `frontend/next.config.ts`. You must update the rewrite destination so it points to your new Render backend instead of localhost:
   ```typescript
   // frontend/next.config.ts
   rewrites: async () => [
     {
       source: "/api/:path*",
       destination: "https://your-render-backend-url.onrender.com/:path*", // UPDATE THIS!
     },
   ],
   ```
5. Click **Deploy**.

That is it! Your Next.js frontend is securely hosted on Vercel, talking to your FastAPI backend on Render, connected to your persistent PostgreSQL database on Neon.

