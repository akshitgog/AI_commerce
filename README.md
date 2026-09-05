# AI Commerce Gateway

An intelligent, full-stack e-commerce gateway featuring an AI-driven buyer assistant, a comprehensive merchant dashboard, and secure, idempotent transaction execution via Razorpay.

## Overview

The **AI Commerce Gateway** reimagines the checkout experience by putting an AI agent at the center of the buyer journey. Buyers interact with a conversational interface that can search catalogs, answer questions, and dynamically generate purchase proposals. Merchants manage their catalog and policies via a modern dashboard, where they can review transactions that exceed automated policy limits.

## System Architecture

The project is structured into two main components: a Next.js frontend and a FastAPI backend following Domain-Driven Design (DDD) principles.

### 1. Frontend (`/frontend`)
* **Framework:** Next.js (App Router) with React.
* **Styling & UI:** Tailwind CSS, `shadcn/ui`, and Lucide icons.
* **State Management:** A custom React Context-based store (`store.ts`) that orchestrates API calls and local state synchronization.
* **Proxy Routing:** API requests to `/api/*` are dynamically proxied to the Python backend via Next.js rewrites, bypassing CORS and standardizing routes.

### 2. Backend (`/src/ai_commerce_gateway`)
* **Framework:** Python (FastAPI) and Uvicorn.
* **Architecture:** Strict Domain-Driven Design (DDD). The logic is cleanly separated into Domain models, Application services, Infrastructure (adapters/DB), and API routers.
* **Database:** SQLite (local development) or PostgreSQL (production via Supabase), managed via SQLAlchemy and Alembic.
* **AI Integration:** Custom LLM clients integrated with Fireworks AI (Qwen 3p7 Plus) to power the Buyer Assistant. The AI executes deterministic tool calls (like `search_catalog` and `create_purchase_proposal`).
* **Payment Gateway:** Razorpay integration for secure checkout. Includes HMAC signature verification and idempotent webhook processing.
* **Security:** State-machine enforced transactions (e.g., preventing payment execution on unapproved proposals), fully audited event sourcing, and idempotency keys to prevent duplicate charges.

## Transaction State Machine

Transactions in the gateway follow a strict, auditable lifecycle:
1. **PROPOSED:** AI or user generates a purchase proposal.
2. **BUYER_AUTH_REQUIRED:** Buyer reviews the proposal and authorizes it.
3. **MERCHANT_POLICY_PENDING:** The proposal is evaluated against the merchant's auto-accept policies.
4. **MERCHANT_REVIEW_REQUIRED:** If the proposal exceeds the auto-accept limit, it enters a manual review queue in the merchant dashboard.
5. **PAYMENT_PENDING:** Once approved, the Razorpay checkout widget is initialized.
6. **VERIFYING:** Payment signature is validated on the backend.
7. **SUCCEEDED / FAILED:** Final terminal states.

## Getting Started

### Prerequisites
* Node.js (v18+)
* Python 3.10+
* `uv` (Python package manager)

### Local Development Setup

1. **Backend Environment Variables:**
   Copy the `.env.example.example` to `.env` in the root directory. Ensure your Razorpay and Fireworks AI keys are set. By default, it uses a local SQLite database (`commerce_dev.db`).

2. **Start the Backend:**
   Run the provided batch script to initialize the virtual environment and start the FastAPI server on port 8001:
   ```bash
   .\start-backend.bat
   ```

3. **Start the Frontend:**
   In a separate terminal window, run the frontend batch script to start the Next.js server on port 3000:
   ```bash
   .\start-frontend.bat
   ```

4. **Access the Application:**
   * **Buyer Chat:** `http://localhost:3000/buyer`
   * **Merchant Dashboard:** `http://localhost:3000/merchant`

## Project Documentation
All previous architectural decisions, design specifications, and audit logs have been moved to the `/docs` directory to keep the root directory clean.
