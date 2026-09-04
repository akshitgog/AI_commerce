# AI Commerce Gateway — Shared Design System

## Direction
Precision Fintech Operations.

Personality: trustworthy, precise, calm, intelligent, operational, premium.

Use a clean light-mode interface with warm/light neutral page backgrounds, white surfaces, subtle cool-gray borders, near-black primary text, muted secondary text, one restrained primary action accent, and semantic success/warning/failure/recovery treatments.

Avoid neon AI aesthetics, crypto styling, glassmorphism, giant gradients, decorative charts, robot illustrations, stock photography, marketplace styling, and copied Razorpay branding.

## Layout
Desktop is the primary demo experience. Use generous page whitespace with compact operational components. Merchant uses a persistent sidebar and minimal top bar. Buyer uses a centered conversation canvas with an optional transaction-progress panel after a proposal exists.

## Typography
Use a modern sans-serif. Establish hierarchy with size, weight, spacing, and contrast. Prefer tabular numerals for money, quantities, timestamps, and transaction references.

## Components
Use subtle borders, medium radii, restrained shadows, compact tables, clear badges, structured cards, and professional timelines. Avoid excessive rounded containers.

## Status language
Every status must include text/iconography; color cannot be the only signal.

Success: verified final success only.
Warning/attention: pending action or recoverable attention.
Recovery: distinct from failure; calm and informational.
Failure: confirmed unsuccessful terminal outcome.

## Recovery treatment
Recovery must communicate:
- provider result is temporarily uncertain;
- authoritative provider truth is being checked;
- no duplicate payment will be attempted.

Do not show Pay Again or Retry Payment while UNKNOWN/RECONCILING.

## Motion
Use small fades, slides, skeletons, and restrained progress indicators. No bouncing elements, animated backgrounds, or theatrical AI-thinking effects.

## Responsive behavior
On narrow screens, sidebar becomes a drawer, tables collapse secondary columns, cards become full width, buyer chat becomes single-column, and transaction progress moves below conversation.

## Accessibility
Provide keyboard access, visible focus, sufficient contrast, accessible labels, and live-region announcements for meaningful transaction-status changes.
