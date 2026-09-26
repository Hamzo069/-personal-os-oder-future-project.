/**
 * End-to-end smoke test against a running stack (API on :8000 with AI_PROVIDER=mock, web on :5173).
 *   npx playwright install chromium   # once
 *   npm run test:e2e
 * Env: BASE_URL (default http://localhost:5173), CHROMIUM_PATH (optional), SHOTS (screenshot dir),
 *      IGNORE_HTTPS_ERRORS=1 for a self-signed certificate.
 */
import { chromium } from "playwright";

const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const email = `smoke-${Date.now()}@example.com`;
const password = "smoke-test-password-1";
const shots = process.env.SHOTS ?? ".";

const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const page = await browser.newPage({
  viewport: { width: 1280, height: 860 },
  // For staging stacks with a self-signed certificate, e.g. Caddy serving https://localhost.
  ignoreHTTPSErrors: process.env.IGNORE_HTTPS_ERRORS === "1",
});
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

try {
  // Register
  await page.goto(`${BASE}/register`);
  await page.getByLabel("Name").fill("Smoke Tester");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL(`${BASE}/`);
  await page.getByRole("heading", { name: "Dashboard" }).waitFor();
  console.log("✓ register + dashboard");

  // Add manual expense
  await page.getByRole("link", { name: "Transactions" }).click();
  await page.getByRole("button", { name: "Add expense" }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Merchant").fill("Hetzner Online");
  await dialog.getByLabel("Amount (incl. VAT)").fill("4,51");
  await dialog.getByLabel("VAT rate (%)").fill("19");
  await dialog.getByLabel("Category").selectOption({ label: "Software & Subscriptions" });
  await dialog.getByRole("button", { name: "Add expense" }).click();
  await page.getByText("Hetzner Online").waitFor();
  console.log("✓ manual expense");

  // Upload receipt and review
  await page.getByRole("link", { name: "Receipts" }).click();
  await page.locator('input[type="file"]').setInputFiles(new URL("./receipt.png", import.meta.url).pathname);
  await page.getByRole("button", { name: "Review & book" }).waitFor({ timeout: 15000 });
  console.log("✓ upload + mock extraction");
  await page.screenshot({ path: `${shots}/receipts.png` });
  await page.getByRole("button", { name: "Review & book" }).click();
  const review = page.getByRole("dialog");
  await review.waitFor();
  await review.getByLabel("Merchant").fill("Bäckerei Müller");
  await review.getByLabel("Amount (incl. VAT)").fill("4.80");
  await review.getByLabel("Category").selectOption({ label: "Food & Drinks" });
  await page.screenshot({ path: `${shots}/review.png` });
  await page.getByRole("button", { name: "Confirm & book" }).click();
  await page.getByText("Booked").waitFor();
  console.log("✓ review + confirm");

  // Dashboard reflects both, NL query works
  await page.getByRole("link", { name: "Dashboard" }).click();
  await page.getByText("9,31").first().waitFor();
  await page.getByLabel("Question about your expenses").fill("How much did I spend on Food this month?");
  await page.getByRole("button", { name: "Ask" }).click();
  await page.getByText(/You spent 4.80 EUR/).waitFor();
  console.log("✓ dashboard + NL query");
  await page.screenshot({ path: `${shots}/dashboard.png`, fullPage: true });

  // Mobile layout
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("link", { name: "Settings" }).click();
  await page.getByRole("heading", { name: "Settings" }).waitFor();
  await page.screenshot({ path: `${shots}/mobile-settings.png` });
  console.log("✓ mobile navigation");

  // Logout -> login (mobile: the user menu lives inside the hamburger menu)
  await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("button", { name: "Log out" }).first().click();
  await page.waitForURL(`${BASE}/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "Dashboard" }).waitFor();
  console.log("✓ logout + login");

  if (errors.length) {
    console.log("Browser errors:", errors);
    process.exitCode = 1;
  } else {
    console.log("ALL SMOKE STEPS PASSED");
  }
} catch (e) {
  await page.screenshot({ path: `${shots}/failure.png` });
  console.error("FAILED:", e.message);
  process.exitCode = 1;
} finally {
  await browser.close();
}
