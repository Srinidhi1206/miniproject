import { expect, test } from "@playwright/test";
import { Buffer } from "node:buffer";

// The MVP definition of done, as a test: no login → paste → analyze →
// live progress → score, reasons, actions → analyze another.

test("message scan: from landing page to explained result", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("check it");

  await page.getByRole("tab", { name: /Message/ }).click();
  await page.getByRole("radio", { name: "WhatsApp" }).click();
  await page.getByPlaceholder(/Dear customer/).fill(
    "Hi, I am buying your sofa listed on OLX. I will pay by QR code. Just scan the QR I send and enter your UPI PIN to receive 15000.",
  );
  await page.getByRole("button", { name: /Analyze message/ }).click();

  // Real progress from the agent stream
  await expect(page.getByRole("status")).toContainText(/text_classifier/);

  await page.waitForURL(/\/analysis\/[0-9a-f]{32}/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/scam/i);
  await expect(page.getByText(/Critical risk|High risk/)).toBeVisible();
  await expect(page.getByText("What SENTINEL found")).toBeVisible();
  await expect(page.getByText(/UPI PIN/).first()).toBeVisible();
  await expect(page.getByText("What you should do")).toBeVisible();

  await page.getByRole("button", { name: /View technical details/ }).click();
  await expect(page.getByRole("heading", { name: "Agent trace" })).toBeVisible();

  await page.getByRole("link", { name: /Analyze another/ }).click();
  await expect(page).toHaveURL(/\/analyze/);
});

test("link scan explains a look-alike domain", async ({ page }) => {
  await page.goto("/analyze?mode=url");
  await page.getByPlaceholder("https://example.com/login").fill("http://paypa1-resolution.com/login/verify");
  await page.getByRole("button", { name: /Analyze link/ }).click();
  await page.waitForURL(/\/analysis\//);
  await expect(page.getByText(/isn.t paypal.s official website/i).first()).toBeVisible();
});

test("QR upload with no QR code gives a helpful error", async ({ page }) => {
  await page.goto("/analyze?mode=qr");
  // 1x1 white PNG
  const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC", "base64");
  await page.locator('input[type="file"]').setInputFiles({ name: "blank.png", mimeType: "image/png", buffer: png });
  await page.getByRole("button", { name: /Analyze QR code/ }).click();
  await expect(page.getByRole("alert").filter({ hasText: /couldn't detect a QR code/ })).toBeVisible();
});

test("report a scam returns a report ID", async ({ page }) => {
  await page.goto("/report?type=job");
  await page.getByLabel(/What happened/).fill("Offered a task job on Telegram, then asked to deposit money to unlock tasks.");
  await page.getByLabel(/Approximate location/).selectOption("pune");
  await page.getByRole("button", { name: "Submit report" }).click();
  await expect(page.getByText(/SC-\d{4}-\d{5}/)).toBeVisible();
});

test("scam map shows aggregated cities and labels demo data", async ({ page }) => {
  await page.goto("/map");
  await expect(page.locator(".leaflet-interactive").first()).toBeVisible();
  await expect(page.getByText(/Demo data/i).first()).toBeVisible();
});
