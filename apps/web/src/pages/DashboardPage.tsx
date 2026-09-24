import { ArrowDownRight, ArrowUpRight, Receipt as ReceiptIcon } from "lucide-react";
import { Suspense, lazy } from "react";
import { Link } from "react-router";

import { useSummary } from "@/api/hooks";
import { AskExpenses } from "@/components/AskExpenses";
import { CategoryBars } from "@/components/charts/CategoryBars";
import { Alert, Card, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { formatDate, formatMoney, formatPercent } from "@/lib/format";

// The chart library is the largest dependency - load it only with the dashboard.
const MonthlyBarChart = lazy(() =>
  import("@/components/charts/MonthlyBarChart").then((m) => ({ default: m.MonthlyBarChart })),
);

export function DashboardPage() {
  const { user } = useAuth();
  const summary = useSummary();

  if (summary.isLoading) return <Spinner label="Loading your dashboard" />;
  if (summary.isError || !summary.data) return <Alert>Could not load the dashboard.</Alert>;
  const s = summary.data;
  const currency = user?.default_currency ?? s.currency;
  const up = (s.change_percent ?? 0) > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-slate-500">
            {formatDate(s.date_from)} – {formatDate(s.date_to)}
          </p>
        </div>
        {s.receipts_pending_review > 0 && (
          <Link
            to="/receipts"
            className="inline-flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800 hover:bg-amber-100"
          >
            <ReceiptIcon className="h-4 w-4" aria-hidden />
            {s.receipts_pending_review} receipt{s.receipts_pending_review === 1 ? "" : "s"} waiting for review
          </Link>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Total spent" value={formatMoney(s.total, currency)} />
        <Stat
          label="vs. previous period"
          value={formatPercent(s.change_percent)}
          detail={formatMoney(s.previous_period_total, currency)}
          icon={s.change_percent == null ? undefined : up ? ArrowUpRight : ArrowDownRight}
          tone={s.change_percent == null ? "neutral" : up ? "bad" : "good"}
        />
        <Stat label="Expenses" value={String(s.count)} detail={`Ø ${formatMoney(s.average, currency)}`} />
        <Stat label="VAT recorded" value={formatMoney(s.vat_total, currency)} />
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card title="Spending per month" className="lg:col-span-3">
          <Suspense fallback={<div className="h-56 animate-pulse rounded-lg bg-slate-100" aria-hidden />}>
            <MonthlyBarChart data={s.by_month} currency={currency} />
          </Suspense>
        </Card>
        <Card title="By category" className="lg:col-span-2">
          <CategoryBars data={s.by_category.slice(0, 8)} currency={currency} />
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <AskExpenses />
        </div>
        <Card title="Top merchants" className="lg:col-span-2">
          {s.top_merchants.length === 0 ? (
            <p className="text-sm text-slate-500">No expenses yet.</p>
          ) : (
            <ol className="divide-y divide-slate-100">
              {s.top_merchants.map((m, i) => (
                <li key={m.merchant} className="flex items-center justify-between gap-3 py-2 text-sm">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="w-5 text-xs text-slate-400">{i + 1}.</span>
                    <span className="truncate text-slate-800">{m.merchant}</span>
                    <span className="text-xs text-slate-400">({m.count})</span>
                  </span>
                  <span className="shrink-0 font-medium tabular-nums">{formatMoney(m.total, currency)}</span>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  detail,
  icon: Icon,
  tone = "neutral",
}: {
  label: string;
  value: string;
  detail?: string;
  icon?: typeof ArrowUpRight;
  tone?: "neutral" | "good" | "bad";
}) {
  const color = tone === "good" ? "text-green-700" : tone === "bad" ? "text-red-700" : "text-slate-900";
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 flex items-center gap-1 text-2xl font-semibold tabular-nums ${color}`}>
        {Icon && <Icon className="h-5 w-5" aria-hidden />}
        {value}
      </p>
      {detail && <p className="text-xs text-slate-500">{detail}</p>}
    </div>
  );
}
