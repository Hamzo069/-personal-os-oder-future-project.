/**
 * One form for three use cases: manual entry, editing, and confirming an
 * AI-extracted receipt draft. Validation runs with zod before anything is
 * sent - the API validates again, of course.
 */

import { useState, type FormEvent } from "react";
import { z } from "zod";

import { Button, Field, Input, Select, Textarea } from "@/components/ui";
import { normaliseAmount, todayIso } from "@/lib/format";
import type { Category, TransactionInput } from "@/types";

const schema = z.object({
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Enter a valid date"),
  merchant: z.string().trim().min(1, "Merchant is required").max(200),
  amount: z.string().refine((v) => normaliseAmount(v) !== null && Number(normaliseAmount(v)) > 0, {
    message: "Enter an amount like 12.34",
  }),
  currency: z.string().trim().length(3, "Use a 3-letter code, e.g. EUR"),
  vat_rate: z.string().refine((v) => v === "" || (normaliseAmount(v) !== null && Number(normaliseAmount(v)) <= 100), {
    message: "VAT rate must be between 0 and 100",
  }),
  vat_amount: z.string().refine((v) => v === "" || normaliseAmount(v) !== null, { message: "Enter an amount like 1.23" }),
  category_id: z.string(),
  description: z.string().max(2000),
  notes: z.string().max(2000),
});

export type TransactionFormValues = z.infer<typeof schema>;

export const emptyValues = (currency = "EUR"): TransactionFormValues => ({
  date: todayIso(),
  merchant: "",
  amount: "",
  currency,
  vat_rate: "",
  vat_amount: "",
  category_id: "",
  description: "",
  notes: "",
});

export function toInput(values: TransactionFormValues): TransactionInput {
  return {
    date: values.date,
    merchant: values.merchant.trim(),
    amount: normaliseAmount(values.amount) ?? "0.00",
    currency: values.currency.trim().toUpperCase(),
    vat_rate: values.vat_rate ? normaliseAmount(values.vat_rate) : null,
    vat_amount: values.vat_amount ? normaliseAmount(values.vat_amount) : null,
    category_id: values.category_id || null,
    description: values.description.trim() || null,
    notes: values.notes.trim() || null,
  };
}

interface Props {
  initial: TransactionFormValues;
  categories: Category[];
  submitLabel: string;
  loading?: boolean;
  onSubmit: (input: TransactionInput) => void;
  onCancel?: () => void;
}

export function TransactionForm({ initial, categories, submitLabel, loading, onSubmit, onCancel }: Props) {
  const [values, setValues] = useState<TransactionFormValues>(initial);
  const [errors, setErrors] = useState<Partial<Record<keyof TransactionFormValues, string>>>({});

  const set = (key: keyof TransactionFormValues) => (event: { target: { value: string } }) =>
    setValues((v) => ({ ...v, [key]: event.target.value }));

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const parsed = schema.safeParse(values);
    if (!parsed.success) {
      const next: Partial<Record<keyof TransactionFormValues, string>> = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0] as keyof TransactionFormValues;
        if (!next[key]) next[key] = issue.message;
      }
      setErrors(next);
      return;
    }
    setErrors({});
    onSubmit(toInput(parsed.data));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Date" htmlFor="tx-date" error={errors.date}>
          <Input id="tx-date" type="date" value={values.date} onChange={set("date")} required />
        </Field>
        <Field label="Merchant" htmlFor="tx-merchant" error={errors.merchant}>
          <Input id="tx-merchant" value={values.merchant} onChange={set("merchant")} placeholder="e.g. Hetzner" required />
        </Field>
        <Field label="Amount (incl. VAT)" htmlFor="tx-amount" error={errors.amount}>
          <Input id="tx-amount" inputMode="decimal" value={values.amount} onChange={set("amount")} placeholder="12.34" required />
        </Field>
        <Field label="Currency" htmlFor="tx-currency" error={errors.currency}>
          <Input id="tx-currency" value={values.currency} onChange={set("currency")} maxLength={3} />
        </Field>
        <Field label="VAT rate (%)" htmlFor="tx-vat-rate" error={errors.vat_rate}>
          <Input id="tx-vat-rate" inputMode="decimal" value={values.vat_rate} onChange={set("vat_rate")} placeholder="19" />
        </Field>
        <Field label="VAT amount" htmlFor="tx-vat-amount" error={errors.vat_amount}>
          <Input id="tx-vat-amount" inputMode="decimal" value={values.vat_amount} onChange={set("vat_amount")} placeholder="1.97" />
        </Field>
        <Field label="Category" htmlFor="tx-category" className="sm:col-span-2">
          <Select id="tx-category" value={values.category_id} onChange={set("category_id")}>
            <option value="">Uncategorised</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Description" htmlFor="tx-description" className="sm:col-span-2" error={errors.description}>
          <Input id="tx-description" value={values.description} onChange={set("description")} placeholder="What was this for?" />
        </Field>
        <Field label="Notes" htmlFor="tx-notes" className="sm:col-span-2" error={errors.notes}>
          <Textarea id="tx-notes" value={values.notes} onChange={set("notes")} />
        </Field>
      </div>
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" loading={loading}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
