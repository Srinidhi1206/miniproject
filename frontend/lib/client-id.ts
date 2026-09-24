// Anonymous device identifier: a random UUID kept in this browser only.
// It lets the backend group *this device's* scans into a history without any
// account, name, phone number or email. Clearing site data resets it.

const KEY = "sentinel.device-id";
let memoryId: string | null = null;

function generate(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  // Fallback for very old browsers: 128 bits from getRandomValues.
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function getClientId(): string {
  if (memoryId) return memoryId;
  try {
    const existing = window.localStorage.getItem(KEY);
    if (existing && /^[A-Za-z0-9-]{8,64}$/.test(existing)) {
      memoryId = existing;
      return existing;
    }
    const id = generate();
    window.localStorage.setItem(KEY, id);
    memoryId = id;
    return id;
  } catch {
    // Storage blocked (private mode etc.): keep a per-tab id so scans still work.
    memoryId = memoryId ?? generate();
    return memoryId;
  }
}

export function resetClientId(): string {
  memoryId = null;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
  return getClientId();
}
