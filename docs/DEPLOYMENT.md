# Deployment

AI Commerce Gateway is deployed as two services:

| Service | Platform | Responsibility |
| --- | --- | --- |
| Web app | Vercel | Serves the Next.js frontend and proxies `/api/*` to the backend. |
| API | Render | Runs the FastAPI application, AI integration, policy engine, and payment workflows. |

## Current endpoints

- Web app: <https://ai-commerce-zeta.vercel.app>
- API health: <https://ai-commerce-backend-bgc3.onrender.com/health/live>

## Render

The production Blueprint is the root-level [`render.yaml`](../render.yaml). Create a Render Blueprint from the repository and set the values in the Render Environment dashboard.

Required production configuration:

```text
DATABASE_URL                 Hosted PostgreSQL connection string
FIREWORKS_API_KEY            Fireworks AI credential
LLM_MODEL                    Configured Fireworks model
LLM_BASE_URL                 Fireworks OpenAI-compatible API URL
RAZORPAY_KEY_ID              Razorpay Test Mode key ID
RAZORPAY_KEY_SECRET          Razorpay Test Mode secret
BUYER_SESSIONS_SECRET        Long, random production secret
BUYER_SESSIONS_ISSUER_KEY    Long, random production secret
STORAGE_PROVIDER             supabase when using Supabase Storage
STORAGE_BUCKET               Storage bucket name
SUPABASE_URL                 Supabase project URL
SUPABASE_SERVICE_ROLE_KEY    Supabase service-role credential
```

Never commit any of these values. SQLite is convenient locally, but a hosted PostgreSQL database is required for durable production data on Render.

## Vercel

Import the repository with `frontend` as the root directory. Set this server-only environment variable:

```text
BACKEND_ORIGIN=https://ai-commerce-backend-bgc3.onrender.com
```

Redeploy after changing it. The rewrite in `frontend/next.config.ts` then forwards browser `/api/*` requests to Render without exposing backend credentials to clients.

## Verify after a deployment

```powershell
Invoke-WebRequest https://ai-commerce-zeta.vercel.app/api/health/live
Invoke-WebRequest https://ai-commerce-zeta.vercel.app/api/health/ready
```

For a functional check, refresh the buyer or merchant page after a Render restart so the browser obtains a current server session.
