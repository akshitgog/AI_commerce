# AI Commerce Gateway: Project Pitch & Post-Mortem

## 1. Problem Statement
Traditional e-commerce platforms are rigid, static, and heavily reliant on manual navigation. Buyers are forced to dig through complex category menus, filter through irrelevant search results, and go through a strictly linear checkout process. On the flip side, merchants struggle with tedious catalog management and inflexible pricing/approval rules. There is a lack of conversational, dynamic interaction where a buyer can simply say "I need a 65W USB charger" and be instantly guided to checkout.

## 2. Our Architecture
To solve this, we built the **AI Commerce Gateway**, a conversational, AI-driven e-commerce platform built on strict engineering principles.

*   **Frontend (Next.js & React):** A fast, modern Single Page Application (SPA) using Tailwind CSS and shadcn/ui. It uses a centralized React Context store (store.ts) to manage complex multi-actor states (buyers vs. merchants) and proxies all API requests dynamically.
*   **Backend (Python FastAPI):** Built on strict **Domain-Driven Design (DDD)**. The system isolates business logic (Domains) from the web layer (Routers) and database layer (Repositories). It is backed by SQLAlchemy, making it seamlessly compatible with both local SQLite for development and PostgreSQL (Supabase) for production.
*   **AI Integration:** We embedded Fireworks AI (Qwen 3p7 Plus) directly into the buyer journey. Rather than just a chatbot, the AI is a deterministic agent equipped with strict tool-calling schemas (search_catalog, create_purchase_proposal).
*   **Transaction State Machine & Payments:** Integrated with Razorpay, the system enforces a strict, idempotent state machine (PROPOSED -> MERCHANT_POLICY_PENDING -> PAYMENT_PENDING -> VERIFYING -> SUCCEEDED). Payments cannot be executed without cryptographically verified signatures.

## 3. How the Architecture Solves the Problem
By merging an LLM with strict DDD contracts, we give the user the freedom of natural language while maintaining the safety of a bank-grade checkout system. 
*   **For Buyers:** They can chat naturally. The AI intelligently extracts their intent, queries the strictly-typed catalog repository, and proposes a transaction.
*   **For Merchants:** They have a unified dashboard to manage AI-extracted product drafts, set auto-accept policies, and manually review high-value or risky transactions.

---

## 4. The 2 AM Crisis: What Broke & How We Fixed It
During our final late-night integration testing, several critical systems collided and failed in a cascade. Here is exactly what broke and how we engineered the solutions:

### Bug A: The AI "No Catalog" Blindspot
*   **What Broke:** The AI assistant was confidently stating "no catalog items found" even when products clearly existed.
*   **The Cause:** The AI was generating drafts, but they were stuck in an unpublished DRAFT state. Furthermore, the LLM was occasionally forgetting to inject the required merchant_id into its tool calls.
*   **The Fix:** We updated the OpenAILLMClient system prompt in the backend to strictly require the LLM to extract the merchant_id from context, ensuring the DB queries were perfectly scoped.

### Bug B: The "Save Changes" 422 Crash
*   **What Broke:** Merchants couldn't publish the AI-generated product drafts. Clicking "Save changes" silently failed.
*   **The Cause:** The frontend was sending the sku field in its update payload. Our backend DDD contracts strictly forbid updating sku because it is an immutable business identifier, resulting in a hidden 422 Unprocessable Entity error.
*   **The Fix:** We modified the product-editor.tsx frontend component to strip the sku field from the update payload, allowing products to successfully transition from DRAFT to PUBLISHED so the AI could see them.

### Bug C: The Infinite Razorpay Buffering loop
*   **What Broke:** The user successfully entered their test card, the Razorpay modal closed with a success token, but the UI just spun indefinitely ("Verifying...") until it timed out.
*   **The Cause:** Next.js proxies routes through /api/. The frontend was mistakenly requesting http://127.0.0.1:8001/v1/checkout/razorpay/verify. However, the backend mounted the payment verification endpoint at the absolute root (/checkout/razorpay/verify) without the /v1 prefix. 
*   **The Fix:** The frontend received a 404 Not Found, couldn't parse the error, threw an undefined AppError reference exception, and got stuck in an infinite polling loop. We fixed the Next.js client.ts to request /api/checkout/razorpay/verify (which proxies perfectly to the root) and corrected the frontend error handler to use ApiError, ensuring safe, reliable payment verification.

### Bug D: The Ghost Reviews (SPA State Stale)
*   **What Broke:** Transactions successfully hit the merchant's policy limit and went into MERCHANT_REVIEW_REQUIRED, but the Merchant Dashboard Review Queue showed "0 items".
*   **The Cause:** Because Next.js is a Single Page Application (SPA), navigating from the buyer chat to the merchant dashboard didn't force a page reload. The local memory state (state.reviews) was stale.
*   **The Fix:** We updated the efreshMerchantDecision function in store.ts. Now, whenever a transaction hits a policy limit, it silently fetches the newest review list from the backend in the background. The dashboard is now instantly in sync without requiring a manual browser refresh.
