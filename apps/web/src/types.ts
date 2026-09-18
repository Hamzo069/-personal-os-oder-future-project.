/** Types mirroring the API's Pydantic schemas (see apps/api/app/schemas). */

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  default_currency: string;
  created_at: string;
}

export interface Category {
  id: string;
  name: string;
  color: string;
  is_default: boolean;
}

export type TransactionSource = "manual" | "receipt";

export interface Transaction {
  id: string;
  date: string;
  merchant: string;
  description: string | null;
  amount: string; // decimal as string - never a float
  currency: string;
  vat_rate: string | null;
  vat_amount: string | null;
  category: Category | null;
  receipt_id: string | null;
  source: TransactionSource;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionInput {
  date: string;
  merchant: string;
  description?: string | null;
  amount: string;
  currency: string;
  vat_rate?: string | null;
  vat_amount?: string | null;
  category_id?: string | null;
  notes?: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface TransactionFilters {
  date_from?: string;
  date_to?: string;
  category_id?: string;
  q?: string;
  min_amount?: string;
  max_amount?: string;
  source?: TransactionSource;
  page?: number;
  page_size?: number;
  sort?: "date_desc" | "date_asc" | "amount_desc" | "amount_asc";
}

export type ReceiptStatus = "uploaded" | "processing" | "extracted" | "confirmed" | "failed";

export interface ReceiptExtraction {
  merchant: string | null;
  date: string | null;
  total_amount: number | null;
  currency: string | null;
  vat_rate: number | null;
  vat_amount: number | null;
  category: string | null;
  description: string | null;
  line_items: { description: string; quantity: number | null; total: number | null }[];
  confidence: number;
  notes: string | null;
}

export interface Receipt {
  id: string;
  original_filename: string;
  media_type: string;
  size_bytes: number;
  status: ReceiptStatus;
  extracted: ReceiptExtraction | null;
  confidence: number | null;
  error_message: string | null;
  suggested_category_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CategoryTotal {
  category_id: string | null;
  category_name: string;
  color: string;
  total: string;
  count: number;
}

export interface MonthTotal {
  month: string;
  total: string;
  count: number;
}

export interface MerchantTotal {
  merchant: string;
  total: string;
  count: number;
}

export interface Summary {
  date_from: string;
  date_to: string;
  currency: string;
  total: string;
  count: number;
  vat_total: string;
  average: string;
  previous_period_total: string;
  change_percent: number | null;
  receipts_pending_review: number;
  by_category: CategoryTotal[];
  by_month: MonthTotal[];
  top_merchants: MerchantTotal[];
}

export interface AIQueryResponse {
  question: string;
  answer: string;
  plan: Record<string, unknown>;
  result: Record<string, unknown>;
}

export interface AIUsage {
  calls: number;
  input_tokens: number;
  output_tokens: number;
  by_kind: Record<string, number>;
}
