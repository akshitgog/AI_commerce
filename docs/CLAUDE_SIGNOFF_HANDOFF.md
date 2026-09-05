# Claude Code Handoff: Frontend Sign-Off

## Objective

Make the merchant and buyer frontend demonstrably sign-off ready without damaging unrelated work in this dirty repository. Follow `TESTING_GUIDE.md`, finish the browser verification, fix only proven blockers, and leave an evidence-based sign-off report.

## Safety / repository constraints

- The worktree was already dirty before this task. Preserve all unrelated modifications and deletions.
- Do not restore, delete, or modify the existing deleted files under `frontend-handoff/`, `MASTER_AUDIT.md`, or `.env.example` unless the user explicitly requests it.
- Do not reset or replace `commerce_dev.db` or `test-merchant.db`.
- Do not use `git reset --hard`, broad `git checkout`, or broad cleanup commands.
- Inspect `git diff` before every edit and keep changes tightly scoped.
- Never print API keys or secret values. It is safe to report only whether a secret is configured.
- There is an unidentified/stale listener on port 8000 (last reported PID `20600`). Windows did not expose enough process information to manage it safely. Do not force-kill it blindly.

## Changes already made

### 1. Buyer Orders transaction fields

File: `frontend/src/app/buyer/page.tsx`

The Orders tab previously used backend snake-case/nonexistent fields:

- `product_id`
- `price_minor`
- `currency`
- `status`

It now uses the actual frontend `Transaction` model:

- `productId`
- `amount.amount_minor`
- `amount.currency`
- `state`

The component now imports `Transaction` and no longer uses `any` for each order.

### 2. AI catalog image validation and partial-failure feedback

File: `frontend/src/app/merchant/ai-catalog/page.tsx`

- Added `imageError` state.
- Limits selection to the first three images.
- Rejects selected files larger than 5 MB instead of attempting to upload them.
- Shows an accessible error/warning message with `role="alert"`.
- If product creation succeeds but an image upload fails, preserves the created product ID and tells the merchant to open the editor and retry the image.
- Removed the unnecessary `alt: undefined` argument.
- Added a narrowly scoped lint explanation for the local object-URL preview `<img>`.

### 3. Product image input contract

File: `frontend/src/lib/services/store.ts`

The store contract was inconsistent: AI catalog supplied a `File`, while the product editor supplied a URL. The implementation already attempted to access `image.file`, which broke production type checking.

`ProductImageInput` now supports either:

- `{ file: File; alt?: string; sortOrder?: number }`
- `{ url: string; alt?: string; sortOrder?: number }`

For the existing URL-based editor path, the store fetches the URL, creates a browser `File`, then uses the same multipart upload API. A failed URL fetch produces `Could not load the image URL.`

## Local configuration changes made for testing

These files are ignored/untracked by Git and contain development-only settings. Do not commit secrets.

### Root `.env`

- Changed `LLM_MODEL` from `accounts/fireworks/models/qwen3-14b` to `fireworks_ai/accounts/fireworks/models/qwen3-14b` so LiteLLM can identify the provider.
- Added development buyer-session values:
  - `BUYER_SESSIONS_ISSUER_KEY=dev-issuer-key`
  - `BUYER_SESSIONS_SECRET=dev-session-secret-change-for-production`
- The existing LLM API key was not read, printed, or modified.

### `frontend/.env.local`

Currently contains:

```env
BUYER_SESSIONS_ISSUER_KEY=dev-issuer-key
BACKEND_ORIGIN=http://127.0.0.1:8001
```

Port 8001 is intentional because the stale port-8000 listener continued serving the old configuration.

## Current server state

At handoff time:

- Frontend: `http://127.0.0.1:3000`, listener last reported as PID `17056`.
- Intended backend: `http://127.0.0.1:8001`, listener last reported as PID `8156`.
- Stale backend listener: `http://127.0.0.1:8000`, last reported PID `20600`. Do not assume this is the active backend.
- Temporary logs are under `.tmp-signoff/`, especially:
  - `.tmp-signoff/backend8001.err.log`
  - `.tmp-signoff/backend8001.out.log`
  - `.tmp-signoff/frontend8001.out.log`
  - `.tmp-signoff/frontend8001.err.log`

Re-resolve listener PIDs before stopping anything; never reuse these PID values without checking.

## Verification already completed

### Production build

`npm run build` in `frontend/` passed after the three scoped code changes.

The Next.js 16.3.4 production build compiled, TypeScript passed, and all routes were generated.

### Merchant dashboard visual check

The desktop merchant dashboard rendered cleanly with:

- Full left navigation
- Overview metrics
- Test Mode and merchant identity
- Needs-attention empty state
- Recent-activity empty state
- Correct spacing, borders, hierarchy, and responsive behavior

The merchant visual itself looked sign-off quality.

### Buyer authentication

After adding matching buyer-session development settings and routing to port 8001:

- `POST /v1/buyer/sessions` returned `201 Created`.
- Merchant session creation and initial products/policy/reviews/transactions requests returned successful responses.

This fixes the earlier buyer-login 503 blocker for the active 8001 backend.

### LLM provider recognition

The first failure was:

```text
LLM Provider NOT provided
model=accounts/fireworks/models/qwen3-14b
```

After adding the `fireworks_ai/` prefix, LiteLLM correctly reported provider `fireworks_ai`. The remaining failure is now from Fireworks itself:

```text
Model not found, inaccessible, and/or not deployed
```

This proves the credential reaches Fireworks and provider routing is fixed, but `accounts/fireworks/models/qwen3-14b` is not available to this account.

### Image selector

Before the current restart, two existing PNG files were selected successfully and both previews rendered. Full persistence could not be tested because LLM draft extraction did not reach the Create Draft state.

## Known blockers

### 1. Fireworks model is unavailable

Current effective model:

```text
fireworks_ai/accounts/fireworks/models/qwen3-14b
```

Fireworks returns `NOT_FOUND`. Do not guess another model name. Query the Fireworks model-list endpoint using the configured key without printing the key, select a chat/completions-capable model accessible to this account, update `LLM_MODEL`, restart only the backend on port 8001, and rerun AI extraction.

Suggested safe approach:

1. Load settings through `ai_commerce_gateway.core.config.get_settings()`.
2. Read the API key only in memory.
3. Call the official Fireworks models endpoint with the bearer token.
4. Print only model IDs/capabilities, never headers or the key.
5. Prefer a currently deployed instruction/chat model.
6. Update only `LLM_MODEL` in `.env`.
7. Restart backend 8001 and verify logs show a successful extraction.

### 2. Lint debt

`npm run lint` currently fails with approximately 47 errors and 12 warnings. Most are pre-existing `@typescript-eslint/no-explicit-any` errors in:

- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/services/store.ts`
- buyer chat response handling
- audit/transaction export helpers

Do not disable `no-explicit-any` globally. An earlier attempt to suppress it was removed. Fix API-boundary types explicitly in a separate pass after functional sign-off, keeping mapper behavior unchanged.

### 3. Existing Playwright configuration conflicts with live servers

`frontend/playwright.config.ts` has `reuseExistingServer: false`, so `npx playwright test` refuses to run while ports 3000/8000 are occupied. Next.js 16 also prevents a second dev server from the same directory because `.next/dev/lock` is held, even on another port.

Do not stop user processes blindly. Either:

- stop the verified project frontend/backend processes and run the normal suite, or
- run the suite from an isolated copy/worktree with its own `.next` directory and dedicated SQLite DB.

The seed script destructively recreates a database and only accepts a SQLite file named `commerce_dev.db`; never point it at the user's root `commerce_dev.db`.

## Exact remaining sign-off procedure

### Phase A: Resolve the Fireworks model

1. Query models accessible to the configured Fireworks account.
2. Select and set a valid chat model in `.env` with the LiteLLM prefix.
3. Restart the backend on 8001.
4. Confirm `GET http://127.0.0.1:8001/health/live` returns 200.
5. Confirm `POST /v1/buyer/sessions` returns 201 through the frontend proxy.
6. Open `/merchant/ai-catalog` and generate from `USB Cable, ₹10, 100 units`.
7. Require a visible Draft Preview; inspect backend logs for no LLM errors.

### Phase B: Merchant image flow

1. Select one PNG/JPEG smaller than 5 MB.
2. Verify preview and remove button.
3. Select more than three files and verify the warning.
4. Select a file larger than 5 MB and verify it is rejected with an alert.
5. With a valid generated draft, create the product.
6. Verify success card and navigate to product editor.
7. Verify the uploaded image renders in the editor and `/merchant/products` list.
8. Verify the media URL returns 200.
9. Verify image deletion through the editor only if using disposable test data.

### Phase C: Buyer visual and functional flow

1. Open `/buyer` at desktop width and mobile width.
2. Confirm no buyer-login warning/error in browser console.
3. Search for an existing published product.
4. Verify assistant response, product result card, price, stock, and image.
5. Create a proposal and verify the proposal card.
6. Verify buyer authorization and merchant decision UI.
7. Only execute the mock/test payment after confirming the environment is Test Mode and no live payment credentials are used.
8. Verify payment status, audit timeline, and progress panel.
9. Open `Billing & Orders` and confirm the corrected product ID, amount/currency, and transaction state render correctly.

### Phase D: Merchant transaction/export flow

1. Open `/merchant/transactions` after creating a disposable test transaction.
2. Verify transaction row, amount, authorization, decision, state, and updated time.
3. Download CSV and JSON and inspect non-empty valid content.
4. Open `/merchant/audit`, select the transaction, and verify timeline content.
5. Download audit CSV and JSON and inspect non-empty valid content.

### Phase E: Quality gates

1. Run `npm run build` — must pass.
2. Fix lint errors explicitly; do not globally suppress rules.
3. Run `npm run lint` — target zero errors; document any intentional warnings.
4. Run the Playwright buyer journey in an isolated disposable environment.
5. Add focused tests for:
   - Buyer Orders field mapping
   - Image count/size validation
   - Partial image-upload failure message
   - Transaction and audit downloads
6. Run relevant Python tests for merchant image storage and buyer sessions.
7. Check browser console on merchant and buyer routes for errors/warnings.
8. Re-run `git diff --check`.
9. Review `git diff` and confirm only intended source/config/test files are included.

## Definition of sign-off ready

Do not sign off until all of the following are true:

- Merchant and buyer dashboards are visually correct at desktop and mobile widths.
- Buyer session login succeeds reliably.
- AI product extraction returns a valid draft with the configured Fireworks model.
- Product image upload, persistence, display, and deletion are verified.
- Buyer proposal/authorization/merchant-decision/payment-status journey passes in Test Mode.
- Buyer Billing & Orders shows correct values.
- Transaction and audit CSV/JSON exports download valid data.
- Production build passes.
- Lint has zero errors.
- Automated E2E tests pass in a disposable environment.
- No unrelated user files or databases were modified or deleted.

## Recommended first command/checks for Claude Code

```powershell
git status --short
git diff -- frontend/src/app/buyer/page.tsx frontend/src/app/merchant/ai-catalog/page.tsx frontend/src/lib/services/store.ts
Get-NetTCPConnection -LocalPort 3000,8000,8001 -State Listen -ErrorAction SilentlyContinue
Get-Content -Tail 100 .tmp-signoff/backend8001.err.log
```

Then resolve the Fireworks model before attempting the remaining browser flow.
