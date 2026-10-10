import { describe, expect, it } from "vitest";

import { localOnlySkipReason } from "@/e2e/local-only";

// The E2E "report a scam" test submits real data; it may only run against a local stack.
describe("localOnlySkipReason (E2E write-test guard)", () => {
  it.each([
    "http://localhost:3000",
    "http://localhost",
    "https://localhost:3000/",
    "http://LOCALHOST:3000",          // URL parsing lower-cases the hostname
    "http://127.0.0.1:3000",
    "http://127.0.0.1",
    "http://[::1]:3000",
    "http://[::1]",
  ])("allows the local base URL %s", (url) => {
    expect(localOnlySkipReason(url)).toBeNull();
  });

  it.each([
    ["Vercel production", "https://miniproject-sage-rho.vercel.app"],
    ["Render API", "https://sentinel-api-ov6m.onrender.com"],
    ["localhost as a subdomain label", "http://localhost.example.com:3000"],
    ["localhost as a prefix", "http://localhost-evil.example"],
    ["localhost in the userinfo", "http://localhost@evil.example"],
    ["localhost in the path", "https://evil.example/localhost"],
    ["localhost in the query", "https://evil.example/?h=127.0.0.1"],
    ["another loopback-looking address", "http://127.0.0.2:3000"],
    ["unspecified address", "http://0.0.0.0:3000"],
  ])("skips %s (%s)", (_label, url) => {
    const reason = localOnlySkipReason(url);
    expect(reason).toMatch(/^Skipped: ".+" is not a local host/);
  });

  it.each([undefined, null, "", "   "])("skips a missing base URL (%j)", (url) => {
    expect(localOnlySkipReason(url)).toMatch(/^Skipped: no E2E base URL is set/);
  });

  it.each(["localhost:3000x", "not a url", "http://", "://localhost", "http://[::1"])(
    "skips a malformed base URL (%s)", (url) => {
      expect(localOnlySkipReason(url)).toMatch(/^Skipped: .*(not a valid URL|not an http\(s\) URL)/);
    },
  );

  it.each(["file://localhost/tmp/x.html", "ftp://localhost/", "localhost:3000"])(
    "skips a non-http(s) base URL even when the host is local (%s)", (url) => {
      expect(localOnlySkipReason(url)).toMatch(/^Skipped: .*(not an http\(s\) URL|not a valid URL)/);
    },
  );
});
