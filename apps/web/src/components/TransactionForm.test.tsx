import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TransactionForm, emptyValues } from "@/components/TransactionForm";
import type { Category } from "@/types";

const categories: Category[] = [
  { id: "c1", name: "Food & Drinks", color: "#eda100", is_default: true },
  { id: "c2", name: "Travel & Transport", color: "#1baf7a", is_default: true },
];

describe("TransactionForm", () => {
  it("validates before submitting", async () => {
    const onSubmit = vi.fn();
    render(<TransactionForm initial={emptyValues("EUR")} categories={categories} submitLabel="Save" onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText("Merchant is required")).toBeInTheDocument();
    expect(screen.getByText("Enter an amount like 12.34")).toBeInTheDocument();
  });

  it("normalises values into the API shape", async () => {
    const onSubmit = vi.fn();
    render(<TransactionForm initial={emptyValues("EUR")} categories={categories} submitLabel="Save" onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText("Merchant"), "  Rewe ");
    await userEvent.type(screen.getByLabelText("Amount (incl. VAT)"), "12,3");
    await userEvent.type(screen.getByLabelText("VAT rate (%)"), "7");
    await userEvent.selectOptions(screen.getByLabelText("Category"), "c1");
    await userEvent.clear(screen.getByLabelText("Currency"));
    await userEvent.type(screen.getByLabelText("Currency"), "eur");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      merchant: "Rewe",
      amount: "12.30",
      currency: "EUR",
      vat_rate: "7.00",
      vat_amount: null,
      category_id: "c1",
      description: null,
      notes: null,
    });
  });
});
