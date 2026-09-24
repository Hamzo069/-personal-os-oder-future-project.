import { Download, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { useCategories, useCreateTransaction, useDeleteTransaction, useTransactions, useUpdateTransaction } from "@/api/hooks";
import { TransactionForm, emptyValues, type TransactionFormValues } from "@/components/TransactionForm";
import { Alert, Badge, Button, Dialog, EmptyState, Input, Select, Spinner } from "@/components/ui";
import { ApiError, apiUrl, getAccessToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatMoney } from "@/lib/format";
import type { Transaction, TransactionFilters } from "@/types";

const PAGE_SIZE = 25;

function toFormValues(tx: Transaction): TransactionFormValues {
  return {
    date: tx.date,
    merchant: tx.merchant,
    amount: tx.amount,
    currency: tx.currency,
    vat_rate: tx.vat_rate ?? "",
    vat_amount: tx.vat_amount ?? "",
    category_id: tx.category?.id ?? "",
    description: tx.description ?? "",
    notes: tx.notes ?? "",
  };
}

export function TransactionsPage() {
  const { user } = useAuth();
  const [filters, setFilters] = useState<TransactionFilters>({ page: 1, page_size: PAGE_SIZE, sort: "date_desc" });
  const [editing, setEditing] = useState<Transaction | "new" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const categories = useCategories();
  const transactions = useTransactions(filters);
  const create = useCreateTransaction();
  const update = useUpdateTransaction();
  const remove = useDeleteTransaction();

  const setFilter = (patch: Partial<TransactionFilters>) => setFilters((f) => ({ ...f, ...patch, page: 1 }));
  const total = transactions.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const onError = (err: unknown) => setError(err instanceof ApiError ? err.message : "Request failed");

  const exportCsv = async () => {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) if (v && !["page", "page_size"].includes(k)) params.set(k, String(v));
    const response = await fetch(`${apiUrl("/transactions/export")}?${params}`, {
      headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
      credentials: "include",
    });
    if (!response.ok) return setError("Export failed");
    const url = URL.createObjectURL(await response.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: "ledgerlens-transactions.csv" });
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Transactions</h1>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={exportCsv}>
            <Download className="h-4 w-4" aria-hidden /> CSV
          </Button>
          <Button onClick={() => setEditing("new")}>
            <Plus className="h-4 w-4" aria-hidden /> Add expense
          </Button>
        </div>
      </div>

      <div className="grid gap-2 rounded-xl border border-slate-200 bg-white p-3 sm:grid-cols-2 lg:grid-cols-5">
        <Input placeholder="Search merchant, description…" aria-label="Search" value={filters.q ?? ""} onChange={(e) => setFilter({ q: e.target.value })} className="lg:col-span-2" />
        <Select aria-label="Category" value={filters.category_id ?? ""} onChange={(e) => setFilter({ category_id: e.target.value || undefined })}>
          <option value="">All categories</option>
          {categories.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Input type="date" aria-label="From" value={filters.date_from ?? ""} onChange={(e) => setFilter({ date_from: e.target.value || undefined })} />
        <Input type="date" aria-label="To" value={filters.date_to ?? ""} onChange={(e) => setFilter({ date_to: e.target.value || undefined })} />
      </div>

      {error && <Alert>{error}</Alert>}

      {transactions.isLoading ? (
        <Spinner />
      ) : !transactions.data?.items.length ? (
        <EmptyState
          title="No expenses found"
          description="Add one manually or upload a receipt and let the AI fill in the details."
          action={<Button onClick={() => setEditing("new")}>Add expense</Button>}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2"><SortButton current={filters.sort} asc="date_asc" desc="date_desc" onChange={(sort) => setFilter({ sort })}>Date</SortButton></th>
                <th className="px-4 py-2">Merchant</th>
                <th className="px-4 py-2">Category</th>
                <th className="px-4 py-2 text-right"><SortButton current={filters.sort} asc="amount_asc" desc="amount_desc" onChange={(sort) => setFilter({ sort })}>Amount</SortButton></th>
                <th className="px-4 py-2 text-right">VAT</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {transactions.data.items.map((tx) => (
                <tr key={tx.id} className="hover:bg-slate-50">
                  <td className="whitespace-nowrap px-4 py-2 text-slate-600">{formatDate(tx.date)}</td>
                  <td className="px-4 py-2">
                    <p className="font-medium text-slate-900">{tx.merchant}</p>
                    {tx.description && <p className="truncate text-xs text-slate-500">{tx.description}</p>}
                  </td>
                  <td className="px-4 py-2">
                    {tx.category ? <Badge color={tx.category.color}>{tx.category.name}</Badge> : <span className="text-xs text-slate-400">–</span>}
                    {tx.source === "receipt" && <span className="ml-2 text-xs text-slate-400">receipt</span>}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2 text-right font-medium tabular-nums">{formatMoney(tx.amount, tx.currency)}</td>
                  <td className="whitespace-nowrap px-4 py-2 text-right text-xs tabular-nums text-slate-500">
                    {tx.vat_rate ? `${Number(tx.vat_rate).toFixed(0)} %` : "–"}
                  </td>
                  <td className="whitespace-nowrap px-2 py-2 text-right">
                    <button className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100" onClick={() => setEditing(tx)} aria-label={`Edit ${tx.merchant}`}>
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      className="rounded-md p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600"
                      onClick={() => window.confirm(`Delete expense at ${tx.merchant}?`) && remove.mutate(tx.id, { onError })}
                      aria-label={`Delete ${tx.merchant}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
            <span>{total} expense{total === 1 ? "" : "s"}</span>
            <span className="flex items-center gap-2">
              <Button size="sm" variant="ghost" disabled={(filters.page ?? 1) <= 1} onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) - 1 }))}>
                Previous
              </Button>
              Page {filters.page} / {pages}
              <Button size="sm" variant="ghost" disabled={(filters.page ?? 1) >= pages} onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) + 1 }))}>
                Next
              </Button>
            </span>
          </div>
        </div>
      )}

      <Dialog open={editing !== null} title={editing === "new" ? "Add expense" : "Edit expense"} onClose={() => setEditing(null)}>
        {editing && (
          <TransactionForm
            key={editing === "new" ? "new" : editing.id}
            initial={editing === "new" ? emptyValues(user?.default_currency) : toFormValues(editing)}
            categories={categories.data ?? []}
            submitLabel={editing === "new" ? "Add expense" : "Save changes"}
            loading={create.isPending || update.isPending}
            onCancel={() => setEditing(null)}
            onSubmit={(input) => {
              const done = { onSuccess: () => setEditing(null), onError };
              if (editing === "new") create.mutate(input, done);
              else update.mutate({ id: editing.id, ...input }, done);
            }}
          />
        )}
      </Dialog>
    </div>
  );
}

function SortButton({
  current,
  asc,
  desc,
  onChange,
  children,
}: {
  current?: TransactionFilters["sort"];
  asc: TransactionFilters["sort"];
  desc: TransactionFilters["sort"];
  onChange: (sort: TransactionFilters["sort"]) => void;
  children: string;
}) {
  const active = current === asc || current === desc;
  return (
    <button type="button" onClick={() => onChange(current === desc ? asc : desc)} className={active ? "font-semibold text-slate-800" : ""}>
      {children} {current === asc ? "↑" : current === desc ? "↓" : ""}
    </button>
  );
}
