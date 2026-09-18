/**
 * TanStack Query hooks - one small file per resource would also work; kept
 * together here so the API surface used by the UI is visible at a glance.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  AIQueryResponse,
  AIUsage,
  Category,
  Page,
  Receipt,
  Summary,
  Transaction,
  TransactionFilters,
  TransactionInput,
  User,
} from "@/types";

export const keys = {
  categories: ["categories"] as const,
  transactions: (filters: TransactionFilters) => ["transactions", filters] as const,
  transaction: (id: string) => ["transaction", id] as const,
  receipts: ["receipts"] as const,
  receipt: (id: string) => ["receipt", id] as const,
  summary: (from?: string, to?: string) => ["summary", from ?? "", to ?? ""] as const,
  aiUsage: ["ai-usage"] as const,
};

// --- Categories -------------------------------------------------------------

export function useCategories() {
  return useQuery({ queryKey: keys.categories, queryFn: () => api.get<Category[]>("/categories") });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; color: string }) => api.post<Category>("/categories", input),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.categories }),
  });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: { id: string; name?: string; color?: string }) =>
      api.patch<Category>(`/categories/${id}`, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.categories }),
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/categories/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.categories });
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
    },
  });
}

// --- Transactions -----------------------------------------------------------

export function useTransactions(filters: TransactionFilters) {
  return useQuery({
    queryKey: keys.transactions(filters),
    queryFn: () => api.get<Page<Transaction>>("/transactions", { ...filters }),
    placeholderData: (previous) => previous,
  });
}

function invalidateTransactionViews(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["transactions"] });
  qc.invalidateQueries({ queryKey: ["summary"] });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: TransactionInput) => api.post<Transaction>("/transactions", input),
    onSuccess: () => invalidateTransactionViews(qc),
  });
}

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: Partial<TransactionInput> & { id: string }) =>
      api.patch<Transaction>(`/transactions/${id}`, input),
    onSuccess: () => invalidateTransactionViews(qc),
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/transactions/${id}`),
    onSuccess: () => invalidateTransactionViews(qc),
  });
}

// --- Receipts ---------------------------------------------------------------

const ACTIVE: Receipt["status"][] = ["uploaded", "processing"];

export function useReceipts() {
  return useQuery({
    queryKey: keys.receipts,
    queryFn: () => api.get<Receipt[]>("/receipts"),
    // Poll while any receipt is still being extracted in the background.
    refetchInterval: (query) =>
      query.state.data?.some((r) => ACTIVE.includes(r.status)) ? 2000 : false,
  });
}

export function useUploadReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.upload<Receipt>("/receipts", form);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.receipts }),
  });
}

export function useRetryExtraction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Receipt>(`/receipts/${id}/extract`),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.receipts }),
  });
}

export function useConfirmReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: TransactionInput & { id: string }) =>
      api.post<{ receipt: Receipt; transaction_id: string }>(`/receipts/${id}/confirm`, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.receipts });
      invalidateTransactionViews(qc);
    },
  });
}

export function useDeleteReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/receipts/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.receipts });
      invalidateTransactionViews(qc);
    },
  });
}

// --- Insights & AI ----------------------------------------------------------

export function useSummary(from?: string, to?: string) {
  return useQuery({
    queryKey: keys.summary(from, to),
    queryFn: () => api.get<Summary>("/insights/summary", { date_from: from, date_to: to }),
  });
}

export function useAskExpenses() {
  return useMutation({
    mutationFn: (question: string) => api.post<AIQueryResponse>("/ai/query", { question }),
  });
}

export function useAIUsage() {
  return useQuery({ queryKey: keys.aiUsage, queryFn: () => api.get<AIUsage>("/ai/usage") });
}

// --- Account ----------------------------------------------------------------

export function useUpdateProfile() {
  return useMutation({
    mutationFn: (input: { name?: string; default_currency?: string }) => api.patch<User>("/users/me", input),
  });
}

export function useDeleteAccount() {
  return useMutation({ mutationFn: (password: string) => api.delete("/users/me", { password }) });
}
