# Audit Schema Reference - Hackathon Critical Requirement

## Overview

The audit system is the **CORE HACKATHON REQUIREMENT** - a complete, secure, structured logging system that tracks every action in the commerce gateway with full traceability.

---

## 1. Catalog Audit Schema

**File**: `src/ai_commerce_gateway/application/catalog_audit.py`

### Purpose
Tracks all merchant catalog mutations (product changes, policy updates, sessions) with full actor attribution and state diffs.

### Schema (CatalogAuditEvent)

```python
@dataclass(frozen=True, slots=True)
class CatalogAuditEvent:
    actor_id: str              # Who performed the action (user ID, system ID)
    actor_type: str            # Type of actor (MERCHANT_USER, SYSTEM, etc.)
    action: str                # What happened (product.create, product.publish, policy.update, etc.)
    merchant_id: str           # Tenant ID
    target_type: str           # What was modified (product, policy, session, image)
    target_id: str             # ID of the thing modified
    correlation_id: str        # Request correlation ID (traces across services)
    causation: str | None      # Parent event reference (idempotency key, confirmation JTI)
    before: dict | None        # State before change (minimal safe snapshot)
    after: dict | None         # State after change (minimal safe snapshot)
    version_before: int | None # Optimistic lock version before
    version_after: int | None  # Optimistic lock version after
    occurred_at: datetime      # When the event occurred
```

### JSON Output Format

```json
{
  "event": "catalog.audit",
  "actor_id": "user_1",
  "actor_type": "MERCHANT_USER",
  "action": "product.publish",
  "merchant_id": "mer_demo",
  "target_type": "product",
  "target_id": "prod_001",
  "correlation_id": "corr_abc123...",
  "causation": "conf_xyz789",
  "before": {
    "status": "UNPUBLISHED",
    "price_minor": 100000,
    "currency": "INR",
    "available_quantity": 50
  },
  "after": {
    "status": "PUBLISHED",
    "price_minor": 100000,
    "currency": "INR",
    "available_quantity": 50
  },
  "version_before": 2,
  "version_after": 3,
  "occurred_at": "2026-09-05T13:45:23.123456+00:00"
}
```

### Security Rules (CRITICAL)

**From the code comments:**
> Hard rule (SECURITY.md): no secrets, LLM API keys, confirmation tokens or raw sensitive payloads ever appear in these events. The field set is allowlisted by construction — only operational identifiers and states.

**Product Snapshot** (safe minimal state):
- Only includes: status, price_minor, currency, available_quantity
- Explicitly EXCLUDES: descriptions (may contain PII), images, full details

### Usage

```python
from ai_commerce_gateway.application.catalog_audit import (
    CatalogAuditEvent,
    emit_catalog_audit,
    product_snapshot
)

# Example: Publishing a product
emit_catalog_audit(
    CatalogAuditEvent(
        actor_id=actor.user_id,
        actor_type=actor.role,
        action="product.publish",
        merchant_id=merchant_id,
        target_type="product",
        target_id=product_id,
        correlation_id=get_correlation_id(),
        causation=idempotency_key,
        before=product_snapshot(old_product),
        after=product_snapshot(new_product),
        version_before=command.expected_version,
        version_after=command.expected_version + 1,
        occurred_at=datetime.now(timezone.utc),
    )
)
```

---

## 2. Transaction Audit Schema

**File**: `src/ai_commerce_gateway/domain/transactions.py`

### Purpose
Tracks the complete lifecycle of transactions - from proposal through authorization, merchant decision, payment execution, and verification.

### Schema (TransactionEvent)

```python
@dataclass(frozen=True, slots=True)
class TransactionEvent:
    id: str                    # Unique event ID (tevt_xxx)
    transaction_id: str        # Transaction being tracked
    event_type: str            # Event type (state.changed, verification.completed, etc.)
    occurred_at: datetime      # When the event occurred
    actor: ActorRef            # Who/what triggered the event
    reason: str | None         # Human-readable reason/description
    metadata: dict             # Additional structured data
```

### Transaction State Machine Events

The transaction lifecycle emits events at each state transition:

1. **CREATED** → Transaction initialized
2. **BUYER_AUTHORIZED** → Buyer approved the proposal
3. **MERCHANT_DECIDED** → Merchant approved/denied
4. **EXECUTING** → Payment execution started
5. **PAYMENT_PENDING** → Awaiting payment provider confirmation
6. **VERIFYING** → Verifying with payment provider
7. **SUCCEEDED** / **FAILED** / **DENIED** → Final states
8. **UNKNOWN** / **RECONCILING** → Error states requiring manual intervention

### JSON Output Format

```json
{
  "id": "tevt_abc123",
  "transaction_id": "txn_xyz789",
  "event_type": "state.changed",
  "occurred_at": "2026-09-05T13:45:23.123456+00:00",
  "actor": {
    "id": "user_1",
    "type": "BUYER"
  },
  "reason": "Buyer authorized purchase",
  "metadata": {
    "from_state": "CREATED",
    "to_state": "BUYER_AUTHORIZED",
    "authorization_id": "auth_def456"
  }
}
```

---

## 3. AI Orchestration Audit

**File**: `src/ai_commerce_gateway/application/buyer_adapter/audit.py`

### Purpose
Tracks LLM tool calls in the buyer chat - what the AI agent decided to do, what tools it called, and what the outcomes were.

### Schema (AiOrchestrationAuditEvent)

```python
@dataclass(frozen=True, slots=True)
class AiOrchestrationAuditEvent:
    request_id: str            # Chat request ID
    correlation_id: str        # Request correlation ID
    actor_id: str              # Buyer ID
    turn: int                  # Turn number in conversation
    tool: str                  # Tool name called by LLM
    outcome: str               # requested/completed/error
    result_reference: str | None  # Reference to result (e.g., "search_catalog_items:3")
    created_at: datetime       # When the event was created
```

### JSON Output Format

```json
{
  "request_id": "req_abc123",
  "correlation_id": "corr_xyz789",
  "actor_id": "buyer_1",
  "turn": 0,
  "tool": "search_catalog",
  "outcome": "completed",
  "result_reference": "search_catalog_items:3",
  "created_at": "2026-09-05T13:45:23.123456+00:00"
}
```

---

## How Audit Works End-to-End

### 1. Merchant Dashboard `/merchant/audit`

**Frontend**: `frontend/src/app/merchant/audit/page.tsx`

Shows complete audit trail for any transaction:
- Timeline of all events
- Actor attribution (who did what)
- State transitions
- Timestamps
- Reason codes
- Metadata

**Export Formats**:
- CSV: Tabular event log
- JSON: Complete structured data

### 2. Buyer Progress Panel

**Component**: `frontend/src/components/buyer/buyer-chat-shell.tsx`

Shows real-time transaction progress:
- Gate progress visualization (6 gates)
- Current state
- Authorization status
- Merchant decision status
- Payment status

### 3. Backend Logging

All audit events are emitted as structured JSON logs:
```python
audit_logger.info(json.dumps(record, sort_keys=True, default=str))
```

**Logger Name**: `ai_commerce_gateway.catalog_audit`

**Location**: Logs go to stdout/stderr and can be ingested by:
- CloudWatch
- Datadog
- Splunk
- ELK Stack
- Any JSON log aggregator

---

## Why This Is Hackathon-Critical

### 1. **Complete Traceability**
Every action has:
- Who did it (actor_id, actor_type)
- What happened (action, target)
- When (occurred_at with microsecond precision)
- Why (causation, reason)
- Context (correlation_id for cross-service tracing)

### 2. **State Reconstruction**
Before/after snapshots allow:
- Point-in-time state recovery
- Debugging what changed
- Understanding how a product/transaction evolved

### 3. **Security & Compliance**
- No secrets ever logged (allowlist-by-construction)
- Immutable audit trail (frozen dataclasses, append-only logs)
- Full actor attribution for compliance (who authorized what)

### 4. **Multi-Gate Approval Transparency**
The 6-gate system (Buyer Auth → Policy → Review → Execution → Verification → Completion) is fully auditable:
- Each gate transition emits events
- Merchant can see why something went to review queue
- Buyer can see where their transaction is stuck
- Debugging payment failures is trivial (full timeline)

### 5. **AI Transparency**
AI orchestration audit shows:
- What the LLM decided to do (search_catalog, create_proposal)
- What results it got
- How many turns it took
- Full buyer chat transparency

---

## API Endpoints

### Get Transaction Audit
```
GET /merchants/{merchant_id}/transactions/{transaction_id}/audit
```

Returns:
```json
{
  "transaction": {...},
  "timeline": [
    {
      "id": "tevt_abc",
      "event_type": "state.changed",
      "occurred_at": "...",
      "actor": {"id": "buyer_1", "type": "BUYER"},
      "reason": "Buyer authorized purchase",
      "metadata": {...}
    }
  ]
}
```

### Export Formats
- CSV: `/merchants/{merchant_id}/transactions/{transaction_id}/audit?format=csv`
- JSON: `/merchants/{merchant_id}/transactions/{transaction_id}/audit?format=json`

---

## Testing the Audit System

### 1. Generate Audit Events
```bash
# Create a transaction that goes through all gates
python scripts/e2e_test.py
```

### 2. View in Frontend
```
http://127.0.0.1:3000/merchant/audit
```

### 3. Check Backend Logs
```bash
tail -f .tmp-signoff/backend8001.err.log | grep "catalog.audit"
```

### 4. Query Database
```python
from ai_commerce_gateway.infrastructure.database.models import TransactionEvent
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

engine = create_engine("sqlite:///commerce_dev.db")
with Session(engine) as session:
    events = session.execute(
        select(TransactionEvent)
        .where(TransactionEvent.transaction_id == "txn_xxx")
        .order_by(TransactionEvent.occurred_at)
    ).scalars().all()
    
    for event in events:
        print(f"{event.occurred_at} | {event.event_type} | {event.actor}")
```

---

## Demonstration Talking Points

For hackathon judges:

1. **"Show me what happened to this transaction"**
   - Open `/merchant/audit`
   - Select any transaction
   - Show complete timeline with actor attribution

2. **"How do you ensure security?"**
   - Point to allowlist-by-construction in code
   - Show no secrets in audit logs
   - Explain minimal product snapshots

3. **"Can you trace this across services?"**
   - Show `correlation_id` linking buyer chat → backend → payment provider
   - Show how causation chains events together

4. **"What did the AI decide to do?"**
   - Show AI orchestration audit
   - Point out tool calls and outcomes
   - Explain transparency for AI actions

5. **"Can you export this for compliance?"**
   - Download CSV and JSON
   - Show complete structured data
   - Explain ingestion into log aggregators

---

## Files to Show Judges

1. `src/ai_commerce_gateway/application/catalog_audit.py` - Core audit schema
2. `frontend/src/app/merchant/audit/page.tsx` - Audit UI
3. `frontend/src/components/shared/audit-timeline.tsx` - Timeline visualization
4. Backend logs showing actual audit events
5. Downloaded CSV/JSON exports

---

## Summary

The audit system is a **complete, production-ready, security-hardened traceability solution** that:
- ✅ Tracks every action with full attribution
- ✅ Maintains complete state history
- ✅ Never leaks secrets
- ✅ Enables compliance and debugging
- ✅ Provides transparency for AI decisions
- ✅ Exports to standard formats
- ✅ Integrates with log aggregators

This is the **CORE VALUE PROPOSITION** of the AI Commerce Gateway for the hackathon.
