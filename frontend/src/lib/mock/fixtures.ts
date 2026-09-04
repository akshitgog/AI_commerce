// Demo fixtures for the AI Commerce Gateway prototype.
// Mirrors the shared handoff spec: merchant "Demo Electronics", buyer "Demo
// Buyer", a ₹899 charger (auto-accept path), a ₹1,299 keyboard (manual review
// path) and one DRAFT product (not buyer-discoverable).
// Money is always integer minor units: ₹899 = 89900.

import type { Merchant, Policy, Product } from "../types";

export const DEMO_MERCHANT: Merchant = {
  id: "mer_demo_1",
  name: "Demo Electronics",
};

export const DEMO_BUYER_ID = "buyer_demo_1";
export const DEMO_BUYER_NAME = "Demo Buyer";

/** Neutral inline SVG data-URI placeholder for demo product imagery. */
function placeholderImage(label: string): string {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480">` +
    `<rect width="640" height="480" fill="#f1f5f9"/>` +
    `<rect x="1" y="1" width="638" height="478" fill="none" stroke="#cbd5e1" stroke-width="2"/>` +
    `<rect x="270" y="150" width="100" height="140" rx="12" fill="#e2e8f0" stroke="#cbd5e1" stroke-width="2"/>` +
    `<text x="320" y="340" font-family="system-ui, sans-serif" font-size="20" fill="#64748b" text-anchor="middle">${label}</text>` +
    `</svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

const FIXTURE_TS = "2026-01-15T09:30:00.000Z";

export const DEMO_PRODUCTS: Product[] = [
  {
    id: "prod_charger_1",
    merchantId: DEMO_MERCHANT.id,
    sku: "USB-C-65W-001",
    title: "65W USB-C Charger",
    description: "Compact 65W GaN fast charger with USB-C Power Delivery.",
    category: "Chargers",
    price: { amount_minor: 89900, currency: "INR" },
    availableQuantity: 10,
    status: "PUBLISHED",
    version: 3,
    images: [
      {
        id: "img_charger_1",
        url: placeholderImage("65W USB-C Charger"),
        alt: "65W USB-C charger",
        isPrimary: true,
        position: 0,
      },
    ],
    updatedAt: FIXTURE_TS,
  },
  {
    id: "prod_keyboard_1",
    merchantId: DEMO_MERCHANT.id,
    sku: "KB-MECH-001",
    title: "Premium Mechanical Keyboard",
    description: "Hot-swappable mechanical keyboard with tactile switches.",
    category: "Keyboards",
    price: { amount_minor: 129900, currency: "INR" },
    availableQuantity: 5,
    status: "PUBLISHED",
    version: 1,
    images: [
      {
        id: "img_keyboard_1",
        url: placeholderImage("Premium Mechanical Keyboard"),
        alt: "Premium mechanical keyboard",
        isPrimary: true,
        position: 0,
      },
    ],
    updatedAt: FIXTURE_TS,
  },
  {
    id: "prod_cable_1",
    merchantId: DEMO_MERCHANT.id,
    sku: "CB-USBC-2M",
    title: "USB-C Cable 2m",
    description: "",
    category: null,
    price: { amount_minor: 29900, currency: "INR" },
    availableQuantity: 40,
    status: "DRAFT",
    version: 1,
    images: [],
    updatedAt: FIXTURE_TS,
  },
];

export const DEMO_POLICY: Policy = {
  mode: "AUTO_BELOW_LIMIT",
  maxAmount: { amount_minor: 100000, currency: "INR" }, // ₹1,000 auto-accept limit
  version: 2,
};

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

/** Fresh deep copy of the demo catalog (used for store init and demo reset). */
export function initialCatalog(): Product[] {
  return clone(DEMO_PRODUCTS);
}

/** Fresh deep copy of the demo merchant. */
export function initialMerchant(): Merchant {
  return { ...DEMO_MERCHANT };
}

/** Fresh deep copy of the demo policy. */
export function initialPolicy(): Policy {
  return clone(DEMO_POLICY);
}
