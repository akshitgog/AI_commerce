# Design system

## Principles

Trust before novelty; operational clarity before analytics; dense but calm; progressive disclosure
for technical details. Do not copy Razorpay's exact branding.

## Foundation

- Use a responsive sidebar dashboard on desktop and a drawer/bottom-safe navigation pattern on
  mobile. Keep the buyer chat visually separate from merchant administration.
- Use a restrained neutral palette with one accessible action accent. Reserve semantic colors for
  success, warning, destructive and recovery states.
- Use an 8px spacing rhythm, readable content widths and consistent 12–16px control spacing.
- Typography: strong page title, concise section heading, legible body, tabular numerals for money
  and IDs, muted metadata. Never rely on color alone.

## Components

- Cards: purposeful summaries with a clear label, value and next action; avoid decorative KPI grids.
- Tables: compact, sticky headers where useful, responsive column priority, row actions in menus.
- Forms: labels always visible, help/error text near controls, explicit currency, destructive
  confirmations and unsaved-change protection.
- Status badges: pair color with icon/text. Map raw backend states to human language.
- Chat: distinct buyer/assistant messages; product cards are scannable; proposal cards have stronger
  border/background and a “Trusted total” label.
- Transaction cards: show amount, gate progress and current state; never collapse authorization and
  merchant decision into one status.
- Audit timeline: vertical causal sequence with actor, action, reason and timestamp; expandable
  correlation/redacted-reference details.

## System states

- Empty: explain why the area is empty and offer one relevant action.
- Loading: skeleton the final geometry; avoid fake changing values.
- Error: plain-language cause, safe retry where appropriate and correlation ID.
- Recovery: amber/indigo neutral treatment, progress/refresh affordance, explanation that provider
  truth is being checked, and no “Pay again” action.
- Success: show verified final outcome, not merely order creation.

## Responsive and accessible behavior

- Collapse nonessential table columns into a row-detail sheet on narrow screens.
- Keep primary actions reachable without horizontal scrolling.
- Support keyboard navigation, visible focus, semantic landmarks, correct form labels, status live
  regions and reduced motion.
- Meet WCAG AA contrast; give images useful alt text; make touch targets at least 44px where practical.

