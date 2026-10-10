/**
 * Guard for E2E tests that WRITE data (e.g. submitting a scam report).
 *
 * Such tests must only ever run against a local dev stack: a report submitted to the
 * live site lands on the public scam map. The decision uses the *parsed* hostname with
 * an exact allow-list, never substring matching, so "localhost.example.com" or
 * "http://localhost@evil.example" are not mistaken for local.
 *
 * Pure function with no Playwright import, so it is unit-tested with Vitest
 * (tests/unit/local-only.test.ts).
 */

// WHATWG URL keeps IPv6 hostnames in brackets: new URL("http://[::1]:3000").hostname === "[::1]".
const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "[::1]"]);

/** Returns null when the base URL is local (the test may run), otherwise the reason to skip it. */
export function localOnlySkipReason(baseURL: string | undefined | null): string | null {
  if (!baseURL || !baseURL.trim()) {
    return "Skipped: no E2E base URL is set; this test submits data and only runs against localhost, 127.0.0.1 or ::1.";
  }
  let url: URL;
  try {
    url = new URL(baseURL);
  } catch {
    return `Skipped: the E2E base URL "${baseURL}" is not a valid URL; this test submits data and only runs locally.`;
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    return `Skipped: the E2E base URL "${baseURL}" is not an http(s) URL; this test submits data and only runs locally.`;
  }
  if (!LOCAL_HOSTNAMES.has(url.hostname)) {
    return `Skipped: "${url.hostname}" is not a local host; this test submits a report and must never write to a live site.`;
  }
  return null;
}
