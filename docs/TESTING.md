# Testing

Run backend checks from the repository root:

```powershell
uv run pytest
uv run ruff check .
uv run mypy
```

Run frontend checks from `frontend`:

```powershell
npm run build
npm run lint
```

`npm run lint` currently reports legacy type and hook warnings in the frontend. Treat a successful production build plus the backend test suite as the baseline release check until that technical debt is resolved.

## Manual acceptance flow

1. Create or publish a product in the merchant dashboard.
2. Discover it in the buyer assistant and create a purchase proposal.
3. Confirm that buyer approval and merchant policy checks occur before payment initiation.
4. Use Razorpay **Test Mode** only.
5. Verify the final transaction state and audit record in the merchant dashboard.

## Health checks

- Liveness: `GET /health/live`
- Readiness: `GET /health/ready`

The Vercel production proxy exposes these at `/api/health/live` and `/api/health/ready`.
