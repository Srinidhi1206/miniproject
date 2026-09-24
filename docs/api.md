# SENTINEL — REST API

Base URL (local): `http://localhost:8000`. Interactive docs: **`/docs`** (Swagger UI)
and `/openapi.json`.

## Conventions

* JSON in/out, except file uploads (`multipart/form-data`).
* **Optional header `X-Sentinel-Client`**: anonymous device id (8–64 chars,
  `[A-Za-z0-9-]`). Links analyses to a device history. Required only for
  `/api/history` and `/api/stats`.
* **Errors** always have this shape (no stack traces):

```json
{ "error": { "code": "INVALID_URL", "message": "That doesn't look like a valid web address — …", "hint": "Paste the full link…" } }
```

| Status | Codes |
|---|---|
| 400 | `INVALID_URL`, `TEXT_TOO_SHORT`, `EMPTY_FILE`, `CORRUPT_IMAGE`, `INVALID_LOCATION`, `CLIENT_ID_REQUIRED` |
| 404 | `NOT_FOUND` |
| 413 | `FILE_TOO_LARGE`, `TEXT_TOO_LONG`, `IMAGE_TOO_LARGE` |
| 415 | `UNSUPPORTED_FILE` |
| 422 | `INVALID_INPUT` (schema), `QR_NOT_FOUND`, `NO_CONTENT` |
| 429 | `RATE_LIMITED` |
| 501 | `CAPABILITY_UNAVAILABLE` (voice) |
| 500 | `INTERNAL_ERROR` |

## Analysis

The spec suggested one endpoint per input type; we kept that (it makes validation
per type explicit) and added `?stream=true` to every analyze endpoint instead of
separate streaming routes.

### `POST /api/analyze/text`
```json
{ "text": "Dear customer your account will be blocked…", "channel": "sms" }
```
`channel`: `sms | whatsapp | email | job_offer | social | other` (SMS and
WhatsApp share one text pipeline; the channel is kept as context).

### `POST /api/analyze/url`
```json
{ "url": "http://sbi-kyc-verify.co/update" }
```
The URL is parsed and analysed lexically; it is never fetched.

### `POST /api/analyze/image` — multipart `file` (+ optional `channel`)
### `POST /api/analyze/qr` — multipart `file`
PNG, JPEG, WEBP, BMP, GIF; ≤ `MAX_UPLOAD_MB` (8 MB default).

### `POST /api/analyze/audio`
Always `501 CAPABILITY_UNAVAILABLE` in the current configuration.

### Streaming (`?stream=true`)
`Content-Type: application/x-ndjson`, one JSON object per line:

```json
{"type":"stage","stage":"validate"}
{"type":"step","step":{"tool":"input_router","stage":"validate","label":"Input identified as text","status":"done","duration_ms":0,"note":"route: text_classifier → url_extractor"}}
{"type":"stage","stage":"analyze"}
{"type":"step","step":{"tool":"text_classifier","stage":"analyze","status":"done","duration_ms":4,"note":"P(scam)=0.97; 2 indicators"}}
…
{"type":"result","result":{ …AnalysisResult… }}
```
Errors after the stream started arrive as `{"type":"error","status":422,"error":{…}}`.

### `AnalysisResult`
```jsonc
{
  "id": "590839e9eb244fb8bf341f3ba99f249e",
  "created_at": "2026-09-24T13:40:12Z",
  "input_type": "TEXT", "channel": "whatsapp",
  "input_preview": "Hi, I am buying your sofa…",          // long digit runs masked
  "classification": "SCAM",                              // SAFE | SUSPICIOUS | SCAM
  "verdict": "Very likely a scam",
  "risk_score": 98, "risk_level": "CRITICAL",            // LOW | MEDIUM | HIGH | CRITICAL
  "confidence": 0.97,
  "findings": [ { "code": "PIN_REQUEST", "label": "Asks you to enter or share your UPI PIN / card PIN",
                  "severity": "critical", "weight": 18, "source": "text_rules",
                  "detail": "A UPI PIN is only ever used to SEND money…", "excerpt": "…enter your UPI PIN to receive 15000." } ],
  "reassurances": [],
  "recommendations": [ { "id": "no_pin_receive", "title": "Never enter your UPI PIN to 'receive' money", "detail": "…", "priority": "critical" } ],
  "explanation": { "summary": "…", "why_it_matters": ["…"], "sources": [ { "slug": "upi-safety", "title": "UPI safety", "section": "…", "score": 0.61 } ], "generated_by": "template+rag" },
  "extracted": { "text": null, "text_source": "user", "ocr_confidence": null, "qr_payload": null, "qr_payload_kind": null, "upi": null, "urls": [] },
  "breakdown": { "components": [ { "component": "text", "subject": "…", "score": 98, "model_points": 67.9, "rule_points": 30, "overrides": [], "model": { "name": "tfidf-logreg", "version": "20260924.1347", "target": "text", "probability": 0.97, "label": "scam", "top_features": [ { "feature": "receive", "weight": 0.41 } ] }, "evidence": [ … ] } ],
                 "base_score": 98, "corroboration_bonus": 0, "final_score": 98, "formula": "…" },
  "trace": [ { "tool": "text_classifier", "stage": "analyze", "label": "…", "status": "done", "duration_ms": 4, "note": "…" } ],
  "limitations": [],
  "duration_ms": 14
}
```

### `GET /api/analysis/{id}`
Returns a stored `AnalysisResult` (without extracted raw text). Ids are random
128-bit values — knowing the id is what grants access, like an unlisted link.

## History (device-scoped, header required)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/history?q=&type=TEXT&level=HIGH&sort=newest&limit=20&offset=0` | `sort`: `newest`, `oldest`, `risk_desc`, `risk_asc` → `{items, total}` |
| DELETE | `/api/history` | deletes this device's analyses (204) |
| GET | `/api/stats` | `{total_scans, threats_detected, suspicious, safe, scans_today, by_type, last_scan_at}` |

## Community

| Method | Path | Notes |
|---|---|---|
| GET | `/api/reports/options` | scam types, city list, limits |
| POST | `/api/reports` | multipart: `scam_type`*, `description`* (10–2000), `amount_lost`, `location` (city slug), `analysis_id`, `evidence` (image) → `201 {report_id: "SC-2026-00161", …, next_steps}` |
| GET | `/api/scam-map?type=upi&region=Karnataka&days=90&include_demo=true` | city-level aggregates only: `{locations[{city, region, lat, lng, total, by_type}], totals_by_type, total_reports, demo_reports, community_reports, regions}` |
| GET | `/api/safety-guides?category=` | guide summaries |
| GET | `/api/safety-guides/{slug}` | guide with `body_markdown` |

## System

`GET /api/health` — database status and, per capability, `ready`,
`disabled`, `not_configured` or `unavailable`, with model versions and metrics.

## Rate limits

`RATE_LIMIT_PER_MINUTE` (default 30) per client IP on `/api/analyze/*` and
`POST /api/reports`. In-memory; use Redis for multi-worker deployments.
