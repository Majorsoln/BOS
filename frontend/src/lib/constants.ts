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
