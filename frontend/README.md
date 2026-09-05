# AI Commerce Gateway Web App

This folder contains the customer-facing Next.js application for [AI Commerce Gateway](../README.md): the buyer assistant, checkout journey, merchant dashboard, and merchant AI catalog tools.

## Run locally

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The app proxies `/api/*` requests to the backend so the browser stays on a single origin.

## Configuration

Create `frontend/.env.local` only when the API is not running at the default local address:

```env
BACKEND_ORIGIN=http://127.0.0.1:8000
```

For Vercel, configure `BACKEND_ORIGIN` as a production environment variable that points to the deployed FastAPI service. Do not put backend credentials or payment secrets in this frontend project.

## Useful commands

```bash
npm run dev      # development server
npm run lint     # lint the application
npm run build    # production build
npm run start    # run the built app
```

## Production

The deployed experience is available at [ai-commerce-zeta.vercel.app](https://ai-commerce-zeta.vercel.app). For the complete product architecture, backend setup, and deployment guide, return to the [repository README](../README.md).
