import { describe, expect, it } from "vitest";

import { formatBytes, formatMoney, formatMonth, formatPercent, normaliseAmount } from "@/lib/format";

describe("formatMoney", () => {
  it("formats decimal strings in the given currency", () => {
    expect(formatMoney("1234.5", "EUR").replace(/\s/g, " ")).toBe("1.234,50 " + String.fromCharCode(0x20ac));
    expect(formatMoney(12, "CHF")).toContain("12,00");
  });
  it("handles null and garbage", () => {
    expect(formatMoney(null)).toContain("0,00");
    expect(formatMoney("abc")).toBe("–");
  });
});

describe("normaliseAmount", () => {
  it("accepts comma and dot decimals", () => {
    expect(normaliseAmount("12,3")).toBe("12.30");
    expect(normaliseAmount("12.34")).toBe("12.34");
    expect(normaliseAmount(" 7 ")).toBe("7.00");
  });
  it("rejects invalid input", () => {
    expect(normaliseAmount("12.345")).toBeNull();
    expect(normaliseAmount("-3")).toBeNull();
    expect(normaliseAmount("abc")).toBeNull();
  });
});

describe("misc formatters", () => {
  it("formats months, percentages and bytes", () => {
    expect(formatMonth("2026-08")).toMatch(/Aug/);
    expect(formatPercent(12.34)).toBe("+12.3 %");
    expect(formatPercent(-5)).toBe("-5.0 %");
    expect(formatPercent(null)).toBe("–");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});
