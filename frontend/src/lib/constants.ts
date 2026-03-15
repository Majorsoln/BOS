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
