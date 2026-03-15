export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

export const DOCUMENT_TYPES = [
  "SALES_RECEIPT",
  "QUOTE",
  "INVOICE",
  "PROFORMA_INVOICE",
  "DELIVERY_NOTE",
  "CREDIT_NOTE",
  "DEBIT_NOTE",
  "PURCHASE_ORDER",
  "GOODS_RECEIPT_NOTE",
  "SALES_ORDER",
  "STATEMENT",
  "REFUND_NOTE",
  "WORK_ORDER",
  "MATERIAL_REQUISITION",
  "CUTTING_LIST",
  "COMPLETION_CERTIFICATE",
  "KITCHEN_ORDER_TICKET",
  "FOLIO",
  "RESERVATION_CONFIRMATION",
  "REGISTRATION_CARD",
  "CANCELLATION_NOTE",
  "PAYMENT_VOUCHER",
  "PETTY_CASH_VOUCHER",
  "STOCK_TRANSFER_NOTE",
  "STOCK_ADJUSTMENT_NOTE",
  "CASH_SESSION_RECONCILIATION",
] as const;

export const VALID_PERMISSIONS = [
  "CMD_EXECUTE_GENERIC",
  "ADMIN_CONFIGURE",
  "POS_SELL",
  "CASH_MOVE",
  "INVENTORY_MOVE",
  "DOC_ISSUE",
  "RESTAURANT_SERVE",
  "WORKSHOP_MANAGE",
  "HOTEL_MANAGE",
  "PROCUREMENT_APPROVE",
  "HR_MANAGE",
  "REPORTING_VIEW",
  "INVENTORY_AUDIT",
] as const;

export const ACTOR_TYPES = ["HUMAN", "SYSTEM", "DEVICE", "AI"] as const;

export const DEFAULT_ROLES = [
  "ADMIN",
  "CASHIER",
  "MANAGER",
  "AUDITOR",
  "REPORTER",
  "GUEST",
] as const;

export const REGIONS = [
  { code: "KE", name: "Kenya", currency: "KES" },
  { code: "TZ", name: "Tanzania", currency: "TZS" },
  { code: "UG", name: "Uganda", currency: "UGX" },
  { code: "RW", name: "Rwanda", currency: "RWF" },
  { code: "NG", name: "Nigeria", currency: "NGN" },
  { code: "GH", name: "Ghana", currency: "GHS" },
  { code: "ZA", name: "South Africa", currency: "ZAR" },
  { code: "CI", name: "Côte d'Ivoire", currency: "XOF" },
  { code: "EG", name: "Egypt", currency: "EGP" },
  { code: "ET", name: "Ethiopia", currency: "ETB" },
] as const;

export const PROMO_TYPES = [
  { value: "DISCOUNT", label: "Discount", description: "Percentage off monthly rate" },
  { value: "CREDIT", label: "Credit", description: "Account credit in local currency" },
  { value: "EXTENDED_TRIAL", label: "Extended Trial", description: "Extra trial days" },
  { value: "ENGINE_BONUS", label: "Engine Bonus", description: "Free engine for limited time" },
  { value: "BUNDLE_DISCOUNT", label: "Bundle Discount", description: "Discount for engine bundle" },
] as const;

export const PAYOUT_METHODS = [
  { value: "MPESA", label: "M-Pesa" },
  { value: "MOBILE_MONEY", label: "Mobile Money" },
  { value: "BANK_TRANSFER", label: "Bank Transfer" },
] as const;

/**
 * All backend engines mapped from `engines/` directories.
 * category: FREE engines are included in every tenant plan automatically.
 * category: PAID engines require a combo subscription.
 */
export const BACKEND_ENGINES = [
  // FREE — every tenant gets these
  { key: "cash", displayName: "Cash", category: "FREE" as const, description: "Cash drawer, sessions, float tracking" },
  { key: "documents", displayName: "Documents", category: "FREE" as const, description: "Receipts, invoices, quotes — all document types" },
  { key: "reporting", displayName: "Reporting", category: "FREE" as const, description: "KPI recording and daily snapshots" },
  { key: "customer", displayName: "Customer", category: "FREE" as const, description: "Customer profiles and lookup" },

  // PAID — Retail & Commerce
  { key: "retail", displayName: "Retail (POS/Duka)", category: "PAID" as const, description: "Point of sale, shop management, sales, refunds" },
  { key: "restaurant", displayName: "Restaurant (F&B)", category: "PAID" as const, description: "Orders, tables, kitchen tickets, bills, splits" },
  { key: "inventory", displayName: "Inventory", category: "PAID" as const, description: "Stock tracking, transfers, adjustments" },
  { key: "procurement", displayName: "Procurement", category: "PAID" as const, description: "Purchase orders, goods receipt, supplier payments" },

  // PAID — Workshop / Fabrication
  { key: "workshop", displayName: "Workshop (Fundi)", category: "PAID" as const, description: "Quotes, jobs, cutting lists, invoicing, installations" },

  // PAID — Hotel & Hospitality
  { key: "hotel_reservation", displayName: "Hotel Reservation", category: "PAID" as const, description: "Bookings, check-in/out, guest registration" },
  { key: "hotel_folio", displayName: "Hotel Folio", category: "PAID" as const, description: "Guest charges, folio settlement, company billing" },
  { key: "hotel_property", displayName: "Hotel Property", category: "PAID" as const, description: "Room types, rates, property configuration" },
  { key: "hotel_housekeeping", displayName: "Hotel Housekeeping", category: "PAID" as const, description: "Room status, cleaning schedules, inspections" },
  { key: "hotel_booking_engine", displayName: "Hotel Booking Engine", category: "PAID" as const, description: "Online booking widget for direct reservations" },
  { key: "hotel_channel", displayName: "Hotel Channel Manager", category: "PAID" as const, description: "OTA integrations (Booking.com, Expedia, etc.)" },

  // PAID — Finance & HR
  { key: "accounting", displayName: "Accounting", category: "PAID" as const, description: "Journals, ledger, obligations, AR aging" },
  { key: "hr", displayName: "HR & Payroll", category: "PAID" as const, description: "Employee records, payroll, deductions" },

  // PAID — Engagement
  { key: "promotion", displayName: "Promotions", category: "PAID" as const, description: "Discounts, credit notes, promo campaigns" },
  { key: "loyalty", displayName: "Loyalty", category: "PAID" as const, description: "Points, rewards, customer retention" },
  { key: "wallet", displayName: "Wallet", category: "PAID" as const, description: "Customer wallet, top-ups, payments" },
  { key: "qr_menu", displayName: "QR Menu", category: "PAID" as const, description: "Digital menu for restaurants via QR code" },
  { key: "cart_qr", displayName: "Cart QR", category: "PAID" as const, description: "QR-based cart for self-service ordering" },
] as const;

// ─── BOS PRICING DOCTRINE ─────────────────────────────────────────────────────

/**
 * Global Reference Prices per engine (USD/month).
 * These are the base prices before region affordability weight is applied.
 * Internal only — never shown to users directly.
 */
export const ENGINE_REFERENCE_PRICES: Record<string, number> = {
  cash: 0, documents: 0, reporting: 0, customer: 0,
  retail: 15, restaurant: 15, inventory: 10, procurement: 10,
  workshop: 15,
  hotel_reservation: 12, hotel_folio: 12, hotel_property: 8, hotel_housekeeping: 8,
  hotel_booking_engine: 15, hotel_channel: 20,
  accounting: 12, hr: 12,
  promotion: 8, loyalty: 8, wallet: 10, qr_menu: 5, cart_qr: 5,
};

/**
 * Region Affordability Weights — INTERNAL/HIDDEN.
 * weight × USD reference price × usdToLocal = local currency price.
 * Never exposed in any user-facing UI.
 */
export const REGION_AFFORDABILITY_WEIGHTS: Record<string, { weight: number; usdToLocal: number }> = {
  KE: { weight: 0.35, usdToLocal: 130 },
  TZ: { weight: 0.30, usdToLocal: 2500 },
  UG: { weight: 0.30, usdToLocal: 3700 },
  RW: { weight: 0.35, usdToLocal: 1300 },
  NG: { weight: 0.30, usdToLocal: 1550 },
  GH: { weight: 0.30, usdToLocal: 14 },
  ZA: { weight: 0.60, usdToLocal: 18 },
  CI: { weight: 0.30, usdToLocal: 600 },
  EG: { weight: 0.40, usdToLocal: 50 },
  ET: { weight: 0.25, usdToLocal: 57 },
};

/**
 * Country Tax Rules — determines tax treatment per billing country.
 */
export const COUNTRY_TAX_RULES: Record<string, {
  vat_rate: number;
  digital_tax_rate: number;
  has_vat: boolean;
  b2b_reverse_charge: boolean;
  registration_required: boolean;
  threshold_usd: number;
  tax_name: string;
}> = {
  KE: { vat_rate: 0.16, digital_tax_rate: 0.015, has_vat: true, b2b_reverse_charge: false, registration_required: true, threshold_usd: 0, tax_name: "VAT" },
  TZ: { vat_rate: 0.18, digital_tax_rate: 0, has_vat: true, b2b_reverse_charge: false, registration_required: true, threshold_usd: 0, tax_name: "VAT" },
  UG: { vat_rate: 0.18, digital_tax_rate: 0, has_vat: true, b2b_reverse_charge: false, registration_required: true, threshold_usd: 0, tax_name: "VAT" },
  RW: { vat_rate: 0.18, digital_tax_rate: 0, has_vat: true, b2b_reverse_charge: false, registration_required: true, threshold_usd: 0, tax_name: "VAT" },
  NG: { vat_rate: 0.075, digital_tax_rate: 0.06, has_vat: true, b2b_reverse_charge: false, registration_required: true, threshold_usd: 0, tax_name: "VAT" },
  GH: { vat_rate: 0.15, digital_tax_rate: 0, has_vat: true, b2b_reverse_charge: false, registration_required: true, threshold_usd: 0, tax_name: "VAT" },
  ZA: { vat_rate: 0.15, digital_tax_rate: 0, has_vat: true, b2b_reverse_charge: false, registration_required: true, threshold_usd: 0, tax_name: "VAT" },
  CI: { vat_rate: 0.18, digital_tax_rate: 0, has_vat: true, b2b_reverse_charge: false, registration_required: true, threshold_usd: 0, tax_name: "TVA" },
  EG: { vat_rate: 0.14, digital_tax_rate: 0, has_vat: true, b2b_reverse_charge: false, registration_required: true, threshold_usd: 0, tax_name: "VAT" },
  ET: { vat_rate: 0.15, digital_tax_rate: 0, has_vat: true, b2b_reverse_charge: false, registration_required: true, threshold_usd: 0, tax_name: "VAT" },
};

/** Business Type definitions — affects which engines are recommended. */
export const BUSINESS_TYPES = [
  { key: "retail", label: "Retail / Shop", engines: ["retail", "inventory", "procurement"] },
  { key: "restaurant", label: "Restaurant / F&B", engines: ["restaurant", "inventory"] },
  { key: "hotel", label: "Hotel / Hospitality", engines: ["hotel_reservation", "hotel_folio", "hotel_property", "hotel_housekeeping"] },
  { key: "workshop", label: "Workshop / Fabrication", engines: ["workshop", "inventory", "procurement"] },
  { key: "services", label: "Professional Services", engines: ["accounting", "hr"] },
] as const;

/** Add-on engines beyond business type defaults. */
export const ADDON_ENGINES = [
  { key: "accounting", label: "Accounting" },
  { key: "hr", label: "HR & Payroll" },
  { key: "promotion", label: "Promotions" },
  { key: "loyalty", label: "Loyalty Program" },
  { key: "wallet", label: "Customer Wallet" },
  { key: "qr_menu", label: "QR Menu" },
  { key: "cart_qr", label: "Cart QR" },
  { key: "hotel_booking_engine", label: "Online Booking Engine" },
  { key: "hotel_channel", label: "Channel Manager" },
] as const;

/** Payer model — who pays the bill. */
export const PAYER_MODELS = [
  { value: "HQ_PAYS", label: "HQ Pays", description: "Headquarters pays for all branches. Single invoice, one billing country." },
  { value: "BRANCH_PAYS", label: "Branch Pays", description: "Each branch pays independently. Invoice per branch, tax per branch country." },
] as const;

/** B2B/B2C buyer qualification. */
export const BUYER_TYPES = [
  { value: "B2C", label: "Individual / Consumer", description: "No tax registration. VAT always charged." },
  { value: "B2B", label: "Registered Business", description: "Has tax registration number. Reverse charge may apply." },
  { value: "PENDING", label: "Pending Verification", description: "Tax number submitted, awaiting verification. VAT charged provisionally." },
] as const;

/** Region expansion gates — 4 gates before a country goes live. */
export const EXPANSION_GATES = [
  { key: "country_logic", label: "Country Logic Locked", description: "Currency, affordability weight, USD conversion rate configured" },
  { key: "b2b_b2c_qualification", label: "B2B/B2C Qualification Locked", description: "Tax rules, reverse charge, registration requirements defined" },
  { key: "registration_path", label: "Registration Path Exists", description: "Digital tax registration or subsidiary/branch pathway documented" },
  { key: "reporting_correction", label: "Reporting & Correction Path", description: "Credit note, adjustment invoice, and tax correction workflows configured" },
] as const;

/** AI usage tiers for plan builder. */
export const AI_USAGE_TIERS = [
  { key: "none", label: "No AI", price_usd: 0, description: "No AI features" },
  { key: "basic", label: "Basic AI", price_usd: 5, description: "AI-assisted reports and basic automation" },
  { key: "advanced", label: "Advanced AI", price_usd: 15, description: "Full AI: predictions, anomaly detection, smart recommendations" },
] as const;
