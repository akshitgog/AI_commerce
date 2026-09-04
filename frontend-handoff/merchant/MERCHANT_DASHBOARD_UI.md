# Merchant Control Center — UI Specification

## Mission
Give a nontechnical merchant a precise operational interface to publish products, configure AI-purchase policy, review proposals, inspect transactions, and reconstruct financial history.

## Application shell
Persistent desktop sidebar:
- Overview
- Products
- Policy
- Review Queue
- Transactions
- Audit
- Settings

Top bar: breadcrumb/page title, Test Mode indicator, merchant identity, user menu.

## Overview
Build an operations command center, not a generic analytics dashboard.

Top compact cards:
- Published Products
- Awaiting Review
- Processing
- Recovering

Make Needs Attention prominent, followed by Recent Transactions.

## Products
Use an operational table with columns:
Product | SKU | Price | Stock | Status | Version | Updated | Actions

Product cell includes a small image, title, and category. Support Add product, edit, publish/unpublish, view, and delete draft where permitted.

## Product editor
Two-column desktop layout.

Main: product information, description, category, images, attributes.
Side: pricing, inventory, publication.

Support 1–3 product images with preview, reorder, remove, alt text, and primary indicator. Optional AI description assistance is secondary and must never control price, currency, stock, or publication.

## Policy
Show three clear selectable policies:
- Review every purchase — MANUAL_ALL
- Automatically accept below a limit — AUTO_BELOW_LIMIT
- Block AI purchases — DENY_ALL

For AUTO_BELOW_LIMIT expose the amount limit clearly. Explain consequences in plain language before Save.

## Review Queue
Treat as a merchant decision inbox. Each item shows product/image, quantity, buyer reference, trusted total, buyer authorization, proposal expiry, and review reason.

Keep Buyer authorization and Merchant decision visually separate. Provide View details, Deny, and Approve actions only where state permits.

## Transactions
Dense fintech table:
Transaction | Product | Amount | Buyer Auth | Merchant Decision | Payment | Updated

Use human-readable statuses such as Awaiting Buyer, Awaiting Merchant, Ready, Processing, Payment Pending, Recovering, Succeeded, Failed, Cancelled, Expired.

## Transaction Detail
This is a hero screen. Header shows transaction reference, product, amount, and current status. Show a lifecycle progression and separate cards for:
- Purchase Proposal
- Buyer Authorization
- Merchant Decision
- Payment
- Recovery

Recovery must explain that provider confirmation is being checked and that no duplicate payment will be attempted.

## Audit
Use a vertical causal timeline. Each event may show timestamp, actor, action, reason, previous/new state, correlation ID, and redacted provider reference. Keep raw JSON hidden by default.

## Trust rule
Merchant UI controls merchant-owned decisions and renders backend state. It must not implement transaction authority, provider verification, idempotency, or reconciliation logic in the browser.
