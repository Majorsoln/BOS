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
] as const;

export const PAYOUT_METHODS = [
  { value: "MPESA", label: "M-Pesa" },
  { value: "MOBILE_MONEY", label: "Mobile Money" },
  { value: "BANK_TRANSFER", label: "Bank Transfer" },
] as const;

// ─── BOS SERVICES ─────────────────────────────────────────────────────────────

/**
 * The 5 core BOS services. Each gives the tenant FULL features
 * for that business vertical — BOS is a Business Operation System.
 * Free engines (cash, documents, reporting, customer) come with every service.
 */
export const BOS_SERVICES = [
  {
    key: "RETAIL",
    name: "BOS Retail",
    description: "Full POS, inventory, sales, receipts, refunds, procurement, reporting",
    engines: ["retail", "inventory", "procurement", "cash", "documents", "reporting", "customer"],
  },
  {
    key: "RESTAURANT",
    name: "BOS Restaurant",
    description: "Tables, KOT, kitchen management, bills, splits, inventory, reporting",
    engines: ["restaurant", "inventory", "cash", "documents", "reporting", "customer"],
  },
  {
    key: "HOTEL",
    name: "BOS Hotel",
    description: "Reservations, folio, housekeeping, check-in/out, channel manager, reporting",
    engines: ["hotel_reservation", "hotel_folio", "hotel_property", "hotel_housekeeping", "hotel_booking_engine", "hotel_channel", "cash", "documents", "reporting", "customer"],
  },
  {
    key: "WORKSHOP",
    name: "BOS Workshop",
    description: "Quotes, jobs, cutting lists, invoicing, inventory, procurement, reporting",
    engines: ["workshop", "inventory", "procurement", "cash", "documents", "reporting", "customer"],
  },
  {
    key: "HR",
    name: "BOS HR",
    description: "Payroll, leave, attendance, deductions, employee records, reporting",
    engines: ["hr", "accounting", "cash", "documents", "reporting", "customer"],
  },
] as const;

/**
 * Capacity dimensions — global tiers, prices set per region by Admin.
 */
export const CAPACITY_DIMENSIONS = [
  {
    key: "BRANCHES",
    label: "Branches",
    description: "Number of business locations",
    tiers: [
      { key: "BRANCH_1", label: "1 Branch", limit: 1 },
      { key: "BRANCH_2_5", label: "2–5 Branches", limit: 5 },
      { key: "BRANCH_6_20", label: "6–20 Branches", limit: 20 },
      { key: "BRANCH_21_50", label: "21–50 Branches", limit: 50 },
      { key: "BRANCH_UNLIMITED", label: "Unlimited", limit: -1 },
    ],
  },
  {
    key: "DOCUMENTS",
    label: "Documents / month",
    description: "Maximum documents generated per month",
    tiers: [
      { key: "DOC_500", label: "500/mo", limit: 500 },
      { key: "DOC_2000", label: "2,000/mo", limit: 2000 },
      { key: "DOC_10000", label: "10,000/mo", limit: 10000 },
      { key: "DOC_UNLIMITED", label: "Unlimited", limit: -1 },
    ],
  },
  {
    key: "USERS",
    label: "User Seats",
    description: "Staff accounts / operator seats",
    tiers: [
      { key: "USER_3", label: "3 Users", limit: 3 },
      { key: "USER_10", label: "10 Users", limit: 10 },
      { key: "USER_25", label: "25 Users", limit: 25 },
      { key: "USER_50", label: "50 Users", limit: 50 },
      { key: "USER_UNLIMITED", label: "Unlimited", limit: -1 },
    ],
  },
  {
    key: "AI_TOKENS",
    label: "AI Tokens",
    description: "AI-powered analytics and automation",
    tiers: [
      { key: "AI_NONE", label: "No AI", limit: 0 },
      { key: "AI_BASIC", label: "Basic (5K tokens)", limit: 5000 },
      { key: "AI_STANDARD", label: "Standard (25K tokens)", limit: 25000 },
      { key: "AI_PRO", label: "Pro (100K tokens)", limit: 100000 },
    ],
  },
] as const;

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

/** Payer model — who pays the bill. */
export const PAYER_MODELS = [
  { value: "HQ_PAYS", label: "HQ Pays", description: "Headquarters pays for all branches. Single invoice." },
  { value: "BRANCH_PAYS", label: "Branch Pays", description: "Each branch pays independently." },
] as const;

/** B2B/B2C buyer qualification. */
export const BUYER_TYPES = [
  { value: "B2C", label: "Individual / Consumer", description: "No tax registration. VAT always charged." },
  { value: "B2B", label: "Registered Business", description: "Has tax registration number." },
] as const;

/** Region expansion gates — 4 gates before a country goes live. */
export const EXPANSION_GATES = [
  { key: "country_logic", label: "Country Logic Locked", description: "Currency, rates configured" },
  { key: "b2b_b2c_qualification", label: "B2B/B2C Qualification Locked", description: "Tax rules, registration defined" },
  { key: "registration_path", label: "Registration Path Exists", description: "Tax registration pathway documented" },
  { key: "reporting_correction", label: "Reporting & Correction Path", description: "Credit note, tax correction workflows configured" },
] as const;

// ─── AGENT MODEL ──────────────────────────────────────────────────────────────

/** Agent types */
export const AGENT_TYPES = [
  { value: "REGION_LICENSE_AGENT", label: "Region License Agent", description: "Licensed operator for a specific region. Manages compliance, collects regional revenue, provides local support. One per region." },
  { value: "REMOTE_AGENT", label: "Remote Agent", description: "Sells and supports tenants in any region with an active RLA. Earns commission per sale. No territory lock." },
] as const;

/**
 * RLA Market Share — set by Platform Admin when appointing.
 * This is the % of regional revenue the RLA retains.
 * Platform keeps the rest.
 */
export const DEFAULT_RLA_MARKET_SHARE_PCT = 30;

/**
 * Discount Types:
 * PLATFORM_DISCOUNT — Platform-funded, limited by platform max.
 * RLA_FUNDED_DISCOUNT — RLA pays from own market share. No platform limit.
 */
export const DISCOUNT_TYPES = [
  { value: "PLATFORM_DISCOUNT", label: "Platform Discount", description: "Discount funded by platform. Capped by platform-set maximum." },
  { value: "RLA_FUNDED_DISCOUNT", label: "RLA-Funded Discount", description: "Discount funded by RLA from their market share. RLA can set any amount." },
] as const;

/** Agent statuses */
export const AGENT_STATUSES = [
  { value: "PROBATION", label: "Probation", color: "warning" },
  { value: "ACTIVE", label: "Active", color: "success" },
  { value: "SUSPENDED", label: "Suspended", color: "outline" },
  { value: "TERMINATED", label: "Terminated", color: "destructive" },
] as const;

/** Default commission ranges by tenant volume */
export const DEFAULT_COMMISSION_RANGES = [
  { min_tenants: 1, max_tenants: 20, rate_pct: 20 },
  { min_tenants: 21, max_tenants: 50, rate_pct: 25 },
  { min_tenants: 51, max_tenants: 100, rate_pct: 28 },
  { min_tenants: 101, max_tenants: 999999, rate_pct: 30 },
] as const;

/** Support ticket categories (L1 — agent handles) */
export const SUPPORT_CATEGORIES = [
  { value: "ONBOARDING", label: "Onboarding" },
  { value: "TRAINING", label: "Training" },
  { value: "BILLING", label: "Billing" },
  { value: "USAGE", label: "General Usage" },
  { value: "TECHNICAL", label: "Technical Issue" },
] as const;

/** Support ticket priorities */
export const SUPPORT_PRIORITIES = [
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
  { value: "URGENT", label: "Urgent" },
] as const;

/** Compliance document types (Regional agents) */
export const COMPLIANCE_DOC_TYPES = [
  { value: "TAX_RULES", label: "Tax Rules Summary" },
  { value: "BUSINESS_REGULATIONS", label: "Business Regulations" },
  { value: "DATA_RESIDENCY", label: "Data Residency Requirements" },
  { value: "PAYMENT_PROCESSORS", label: "Payment Processor Requirements" },
  { value: "REGULATORY_UPDATE", label: "Regulatory Update" },
] as const;
