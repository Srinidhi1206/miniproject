/*
 * Regenerates the documentation images in docs/images/.
 *
 *   cd frontend
 *   NODE_PATH=node_modules node ../scripts/capture_docs.cjs diagrams
 *   NODE_PATH=node_modules node ../scripts/capture_docs.cjs testing <dir-with-test-transcripts>
 *   NODE_PATH=node_modules node ../scripts/capture_docs.cjs ui [base-url]        # default: live site
 *   NODE_PATH=node_modules node ../scripts/capture_docs.cjs report-receipt <base-url>   # local stack only
 *
 * UI screenshots are taken from the REAL running app (no mocked responses).
 * `ui` never submits a scam report, so it doesn't add test data to the public map.
 * Uses Playwright with an installed browser channel (PLAYWRIGHT_CHANNEL, default msedge).
 */
const fs = require("fs");
const path = require("path");
const { chromium, devices } = require("@playwright/test");

const ROOT = path.resolve(__dirname, "..");
const IMG = path.join(ROOT, "docs", "images");
const CHANNEL = process.env.PLAYWRIGHT_CHANNEL || "msedge";
const LIVE = "https://miniproject-sage-rho.vercel.app";
const sample = (f) => path.join(ROOT, "samples", f);
const out = (dir, f) => { fs.mkdirSync(path.join(IMG, dir), { recursive: true }); return path.join(IMG, dir, f); };
const log = (...a) => console.log("  ✓", ...a);

async function diagrams(browser) {
  const page = await browser.newPage({ viewport: { width: 1480, height: 1000 }, deviceScaleFactor: 1.5 });
  await page.goto("file://" + path.join(ROOT, "docs", "diagrams", "architecture.html").replace(/\\/g, "/"));
  for (const [id, name] of [["system", "01-system-architecture"], ["pipeline", "02-analysis-pipeline"],
                            ["ml", "03-models-and-risk-engine"], ["data", "04-data-model"]]) {
    await page.locator(`#${id}`).screenshot({ path: out("architecture", `${name}.png`) });
    log(`architecture/${name}.png`);
  }
}

async function testing(browser, dir) {
  const items = [
    ["backend_pytest.txt", "01-backend-pytest", "Backend · pytest (154 tests)"],
    ["frontend_vitest.txt", "02-frontend-vitest", "Frontend · Vitest unit tests"],
    ["frontend_checks.txt", "03-frontend-typecheck-lint", "Frontend · TypeScript typecheck + ESLint"],
    ["frontend_build.txt", "04-frontend-production-build", "Frontend · production build (Vercel configuration)"],
    ["playwright_production.txt", "05-playwright-e2e-production", "End-to-end · Playwright against the live site"],
    ["review_samples.txt", "06-sample-review-25-cases", "Pipeline review · 25 labelled samples"],
    ["production_ocr.txt", "07-production-ocr-verification", "Production · screenshot OCR + health"],
    ["model_metrics.txt", "08-model-evaluation-metrics", "Model & system evaluation metrics"],
  ];
  const page = await browser.newPage({ viewport: { width: 1200, height: 600 }, deviceScaleFactor: 1.25 });
  for (const [file, name, title] of items) {
    const p = path.join(dir, file);
    if (!fs.existsSync(p)) { console.log("  - skip (missing)", file); continue; }
    const esc = fs.readFileSync(p, "utf8").replace(/\r/g, "").trimEnd()
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/^(.*\b(PASSED|passed|✓|ok|OK|Compiled successfully|matched)\b.*)$/gm, '<span class="ok">$1</span>')
      .replace(/^(\$ .*)$/gm, '<span class="cmd">$1</span>');
    await page.setContent(`<!doctype html><html><body style="margin:0;background:#f5f3ee;padding:24px">
      <div id="term" style="width:1150px;border-radius:10px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.18)">
        <div style="background:#2a2d35;color:#c8ccd4;font:13px Segoe UI,sans-serif;padding:9px 14px;display:flex;gap:8px;align-items:center">
          <span style="width:12px;height:12px;border-radius:50%;background:#ff5f57;display:inline-block"></span>
          <span style="width:12px;height:12px;border-radius:50%;background:#febc2e;display:inline-block"></span>
          <span style="width:12px;height:12px;border-radius:50%;background:#28c840;display:inline-block"></span>
          <span style="margin-left:10px">SENTINEL — ${title}</span></div>
        <pre style="margin:0;background:#17191e;color:#d9dbe0;font:12.5px/1.45 Consolas,monospace;padding:16px 18px;white-space:pre-wrap;word-break:break-word">${esc}</pre>
      </div>
      <style>.ok{color:#9be37a}.cmd{color:#c6f24e}</style></body></html>`);
    await page.locator("#term").screenshot({ path: out("testing", `${name}.png`) });
    log(`testing/${name}.png`);
  }
}

async function ui(browser, base) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const shot = async (name, opts = {}) => { await page.waitForTimeout(400); await page.screenshot({ path: out("ui", name), ...opts }); log("ui/" + name); };
  const result = async () => { await page.waitForURL(/\/analysis\/[0-9a-f]{32}/, { timeout: 180000 }); await page.getByRole("heading", { level: 1 }).waitFor(); };

  await page.goto(base + "/"); await page.waitForLoadState("networkidle");
  await shot("01-landing.png");
  await shot("02-landing-full-page.png", { fullPage: true });

  // Message → live progress → result
  await page.goto(base + "/analyze");
  await page.getByLabel("Insert an example message").selectOption({ label: "Example: bank KYC SMS" });
  await shot("03-scanner-message.png");
  await page.getByRole("button", { name: /Analyze message/ }).click();
  await page.getByRole("status").waitFor(); await page.waitForTimeout(700);
  await shot("04-live-analysis-progress.png");
  await result();
  const messageReport = page.url();
  await shot("05-result-scam-message.png");
  await shot("06-result-full-page.png", { fullPage: true });
  await page.getByRole("button", { name: /View technical details/ }).click();
  await page.waitForTimeout(500);
  await page.locator("article").locator("> div").last().screenshot({ path: out("ui", "07-technical-details.png") }).catch(() => {});
  await page.getByText("Risk engine breakdown").scrollIntoViewIfNeeded();
  await shot("07-technical-details.png");

  // Safe message
  await page.goto(base + "/analyze");
  await page.getByLabel("Insert an example message").selectOption({ label: "Example: message from a friend" });
  await page.getByRole("button", { name: /Analyze message/ }).click(); await result();
  await shot("08-result-safe-message.png");

  // Link
  await page.goto(base + "/analyze?mode=url");
  await page.getByPlaceholder("https://example.com/login").fill("http://paypa1-resolution.com/login/verify");
  await page.getByRole("button", { name: /Analyze link/ }).click(); await result();
  await shot("09-result-suspicious-link.png");

  // QR (UPI refund bait)
  await page.goto(base + "/analyze?mode=qr");
  await page.locator('input[type="file"]').setInputFiles(sample("qr_upi_refund_bait.png"));
  await shot("10-scanner-qr-upload.png");
  await page.getByRole("button", { name: /Analyze QR code/ }).click(); await result();
  await shot("11-result-qr-upi.png", { fullPage: true });

  // Screenshot → OCR (website streaming path)
  await page.goto(base + "/analyze?mode=image");
  await page.locator('input[type="file"]').setInputFiles(sample("screenshot_with_url.png"));
  await page.getByRole("button", { name: /Analyze screenshot/ }).click(); await result();
  await shot("12-result-screenshot-ocr.png", { fullPage: true });

  // Friendly error states
  await page.goto(base + "/analyze?mode=url");
  await page.getByPlaceholder("https://example.com/login").fill("javascript:alert(1)");
  await page.getByRole("button", { name: /Analyze link/ }).click();
  await page.getByRole("alert").first().waitFor();
  await shot("13-error-invalid-link.png");
  await page.goto(base + "/analyze?mode=qr");
  await page.locator('input[type="file"]').setInputFiles(sample("qr_undecodable_blank.png"));
  await page.getByRole("button", { name: /Analyze QR code/ }).click();
  await page.getByText(/couldn't detect a QR code/).waitFor({ timeout: 60000 });
  await shot("14-error-qr-not-found.png");

  // Product pages (history now contains this session's real analyses)
  for (const [route, name, full] of [["/dashboard", "15-dashboard.png", true], ["/history", "16-history.png", false],
                                    ["/map", "17-scam-map.png", true], ["/safety", "19-safety-center.png", true],
                                    ["/safety/upi-safety", "20-safety-guide.png", true], ["/settings", "21-settings-privacy.png", false]]) {
    await page.goto(base + route); await page.waitForLoadState("networkidle"); await page.waitForTimeout(route === "/map" ? 2500 : 800);
    await shot(name, { fullPage: full });
  }
  // Report form filled but NOT submitted (keeps test data off the public map)
  await page.goto(base + "/report?type=upi"); await page.waitForLoadState("networkidle");
  await page.getByLabel(/What happened/).fill("A buyer on a marketplace asked me to scan a QR code to receive payment and enter my UPI PIN.");
  await page.getByLabel(/Approximate location/).selectOption("hyderabad");
  await shot("18-report-scam-form.png", { fullPage: true });

  // Mobile
  const m = await browser.newContext({ ...devices["Pixel 7"] });
  const mp = await m.newPage();
  await mp.goto(base + "/"); await mp.waitForLoadState("networkidle"); await mp.waitForTimeout(500);
  await mp.screenshot({ path: out("ui", "22-mobile-landing.png") }); log("ui/22-mobile-landing.png");
  await mp.goto(messageReport); await mp.getByRole("heading", { level: 1 }).waitFor(); await mp.waitForTimeout(500);
  await mp.screenshot({ path: out("ui", "23-mobile-result.png") }); log("ui/23-mobile-result.png");
  await mp.goto(base + "/dashboard"); await mp.waitForLoadState("networkidle");
  await mp.getByRole("button", { name: "Open navigation" }).click(); await mp.waitForTimeout(600);
  await mp.screenshot({ path: out("ui", "24-mobile-navigation.png") }); log("ui/24-mobile-navigation.png");
  await m.close(); await ctx.close();
}

async function reportReceipt(browser, base) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(base + "/report?type=upi"); await page.waitForLoadState("networkidle");
  await page.getByLabel(/What happened/).fill("A buyer on a marketplace asked me to scan a QR code to receive payment and enter my UPI PIN.");
  await page.getByLabel(/Approximate location/).selectOption("hyderabad");
  await page.getByRole("button", { name: "Submit report" }).click();
  await page.getByText(/SC-\d{4}-\d{5}/).waitFor(); await page.waitForTimeout(600);
  await page.screenshot({ path: out("ui", "18b-report-scam-receipt.png") }); log("ui/18b-report-scam-receipt.png");
}

(async () => {
  const [mode, arg] = process.argv.slice(2);
  const browser = await chromium.launch({ channel: CHANNEL });
  try {
    if (mode === "diagrams") await diagrams(browser);
    else if (mode === "testing") await testing(browser, arg);
    else if (mode === "ui") await ui(browser, arg || LIVE);
    else if (mode === "report-receipt") await reportReceipt(browser, arg);
    else throw new Error("mode must be diagrams | testing <dir> | ui [url] | report-receipt <url>");
  } finally { await browser.close(); }
})().catch((e) => { console.error("FAILED:", e.message); process.exit(1); });
