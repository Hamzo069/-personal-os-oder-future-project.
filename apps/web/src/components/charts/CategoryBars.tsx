import { formatMoney } from "@/lib/format";
import type { CategoryTotal } from "@/types";

/** Horizontal bars with direct labels - identity never relies on colour alone. */
export function CategoryBars({ data, currency }: { data: CategoryTotal[]; currency: string }) {
  const max = Math.max(...data.map((c) => Number.parseFloat(c.total)), 0);
  if (!data.length) return <p className="text-sm text-slate-500">No expenses in this period.</p>;
  return (
    <ul className="space-y-3">
      {data.map((c) => {
        const value = Number.parseFloat(c.total);
        const width = max > 0 ? Math.max((value / max) * 100, 1.5) : 0;
        return (
          <li key={c.category_id ?? "none"}>
            <div className="mb-1 flex items-center justify-between gap-3 text-sm">
              <span className="flex min-w-0 items-center gap-2 text-slate-700">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: c.color }} aria-hidden />
                <span className="truncate">{c.category_name}</span>
                <span className="text-xs text-slate-400">({c.count})</span>
              </span>
              <span className="shrink-0 font-medium tabular-nums text-slate-900">{formatMoney(c.total, currency)}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-100" role="presentation">
              <div className="h-2 rounded-full" style={{ width: `${width}%`, backgroundColor: c.color }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
