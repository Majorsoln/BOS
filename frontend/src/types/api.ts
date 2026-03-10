export interface ApiResponse<T = Record<string, unknown>> {
  status: "ok" | "error";
  data?: T;
  code?: string;
  message?: string;
}

export interface Business {
  business_id: string;
  name: string;
  default_currency: string;
  default_language: string;
  address?: string;
  city?: string;
  country_code?: string;
  phone?: string;
  email?: string;
  tax_id?: string;
  logo_url?: string;
}

export interface Branch {
  branch_id: string;
  name: string;
  timezone: string;
}

export interface Actor {
  actor_id: string;
  actor_type: string;
  display_name: string;
  status: string;
}

export interface Role {
  role_id: string;
  name: string;
  permissions: string[];
}

export interface RoleAssignment {
  actor_id: string;
  role_id: string;
  role_name: string;
  status: string;
  branch_id?: string;
}

export interface CustomerProfile {
  customer_id: string;
  display_name: string;
  phone: string;
  email: string;
  address: string;
  status: string;
}

export interface FeatureFlag {
  flag_name: string;
  enabled: boolean;
}

export interface TaxRule {
  tax_code: string;
  rate: number;
}

export interface IssuedDocument {
  document_id: string;
  document_type: string;
  document_number: string;
  business_id: string;
  issued_at: string;
  hash: string;
}

export interface ApiKeyRecord {
  key_id: string;
  actor_id: string;
  actor_type: string;
  status: string;
  created_at: string;
}
