"""End-to-end API tests through the real agent, models and database."""

import json

from tests.fixtures import blank_png, chat_screenshot_png, qr_png

SCAM_SMS = ("Dear customer your SBI account will be blocked today. Update KYC immediately at "
            "http://sbi-kyc-verify.co/update or call 9876543210")


def test_health_reports_capabilities(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    caps = r.json()["capabilities"]
    assert caps["text_model"]["status"] == "ready"
    assert caps["audio"]["status"] == "unavailable"


def test_analyze_text_scam(client, device):
    r = client.post("/api/analyze/text", json={"text": SCAM_SMS, "channel": "sms"}, headers=device)
    assert r.status_code == 200
    body = r.json()
    assert body["risk_level"] in {"HIGH", "CRITICAL"} and body["classification"] == "SCAM"
    codes = {f["code"] for f in body["findings"]}
    assert {"ACCOUNT_THREAT", "URGENCY", "BRAND_IMPERSONATION"} <= codes
    assert body["recommendations"] and body["explanation"]["sources"]
    assert "9876543210" not in body["input_preview"]  # long numbers masked in stored previews
    assert [s["stage"] for s in body["trace"]][0] == "validate"


def test_analyze_text_benign(client, device):
    r = client.post("/api/analyze/text", json={"text": "Can you pick up Aarav from tuition at 6? I'm stuck in a meeting."},
                    headers=device)
    body = r.json()
    assert body["risk_level"] == "LOW" and body["classification"] == "SAFE"


def test_stream_emits_stages_then_result(client, device):
    with client.stream("POST", "/api/analyze/url?stream=true", json={"url": "http://secure-hdfc-login.web.app"},
                       headers=device) as r:
        assert r.status_code == 200
        events = [json.loads(line) for line in r.iter_lines() if line]
    stages = [e["stage"] for e in events if e["type"] == "stage"]
    assert stages == ["validate", "analyze", "risk", "explain"]
    assert events[-1]["type"] == "result" and events[-1]["result"]["risk_score"] >= 60


def test_invalid_inputs_get_friendly_errors(client):
    assert client.post("/api/analyze/url", json={"url": "javascript:alert(1)"}).json()["error"]["code"] == "INVALID_URL"
    assert client.post("/api/analyze/text", json={"text": "hi"}).json()["error"]["code"] == "TEXT_TOO_SHORT"
    r = client.post("/api/analyze/text", json={})
    assert r.status_code == 422 and "Traceback" not in r.text
    r = client.post("/api/analyze/image", files={"file": ("x.png", b"not an image", "image/png")})
    assert r.status_code == 415
    r = client.post("/api/analyze/audio", files={"file": ("a.mp3", b"ID3....", "audio/mpeg")})
    assert r.status_code == 501 and r.json()["error"]["code"] == "CAPABILITY_UNAVAILABLE"


def test_upload_size_limit(client):
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (9 * 1024 * 1024)
    r = client.post("/api/analyze/image", files={"file": ("big.png", big, "image/png")})
    assert r.status_code == 413 and r.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_qr_upi_bait(client, device):
    png = qr_png("upi://pay?pa=refund.desk@ybl&pn=Refund&am=4999&tn=Cashback%20refund%20receive")
    body = client.post("/api/analyze/qr", files={"file": ("qr.png", png, "image/png")}, headers=device).json()
    assert body["extracted"]["qr_payload_kind"] == "upi"
    assert body["extracted"]["upi"]["amount"] == 4999
    assert body["risk_score"] >= 75
    assert "dont_scan" in {r["id"] for r in body["recommendations"]}


def test_qr_url_goes_through_url_analyzer(client, device):
    png = qr_png("http://sbi-rewards-claim.xyz/kyc/login")
    body = client.post("/api/analyze/qr", files={"file": ("qr.png", png, "image/png")}, headers=device).json()
    tools = [s["tool"] for s in body["trace"]]
    assert tools.index("qr_decoder") < tools.index("url_analyzer")
    assert body["risk_level"] == "CRITICAL"


def test_qr_not_found(client):
    r = client.post("/api/analyze/qr", files={"file": ("b.png", blank_png(), "image/png")})
    assert r.status_code == 422 and r.json()["error"]["code"] == "QR_NOT_FOUND"


def test_screenshot_ocr_pipeline(client, device):
    png = chat_screenshot_png("URGENT: Your Paytm KYC has expired. Your wallet will be blocked today. "
                              "Share the OTP sent to your phone with our executive to reactivate.")
    body = client.post("/api/analyze/image", files={"file": ("s.png", png, "image/png")}, headers=device).json()
    assert body["extracted"]["text_source"] == "ocr"
    assert body["risk_level"] in {"HIGH", "CRITICAL"}
    assert "OTP_REQUEST" in {f["code"] for f in body["findings"]}
    assert body["extracted"].get("text") is None or "KYC" in body["extracted"]["text"]


def test_image_without_content(client):
    r = client.post("/api/analyze/image", files={"file": ("b.png", blank_png(), "image/png")})
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_CONTENT"


def test_history_stats_and_stored_report(client):
    dev = {"X-Sentinel-Client": "pytest-history-0001"}
    ids = [client.post("/api/analyze/text", json={"text": t}, headers=dev).json()["id"]
           for t in (SCAM_SMS, "See you at the library at 4 for the project slides")]
    page = client.get("/api/history?sort=risk_desc", headers=dev).json()
    assert page["total"] == 2 and page["items"][0]["risk_score"] >= page["items"][1]["risk_score"]
    assert client.get("/api/history?type=URL", headers=dev).json()["total"] == 0
    assert client.get("/api/history?q=library", headers=dev).json()["total"] == 1
    stats = client.get("/api/stats", headers=dev).json()
    assert stats["total_scans"] == 2 and stats["threats_detected"] == 1 and stats["safe"] == 1
    stored = client.get(f"/api/analysis/{ids[0]}").json()
    assert stored["id"] == ids[0] and stored["extracted"]["text"] is None  # raw text not persisted
    assert client.get("/api/analysis/doesnotexist").status_code == 404
    assert client.get("/api/history").status_code == 400  # device id required
    assert client.delete("/api/history", headers=dev).status_code == 204
    assert client.get("/api/history", headers=dev).json()["total"] == 0


def test_report_flow_and_map(client, device):
    opts = client.get("/api/reports/options").json()
    assert any(o["slug"] == "pune" for o in opts["locations"])
    before = client.get("/api/scam-map?type=qr&include_demo=false&days=30").json()["community_reports"]
    r = client.post("/api/reports", data={"scam_type": "qr", "description": "QR sticker on a parking meter charged me.",
                                          "amount_lost": "500", "location": "pune"},
                    files={"evidence": ("e.png", chat_screenshot_png("fake parking QR"), "image/png")}, headers=device)
    assert r.status_code == 201
    receipt = r.json()
    assert receipt["report_id"].startswith("SC-") and receipt["evidence_attached"]
    m = client.get("/api/scam-map?type=qr&include_demo=false&days=30").json()
    assert m["community_reports"] == before + 1
    pune = next(l for l in m["locations"] if l["slug"] == "pune")
    assert set(pune) == {"slug", "city", "region", "lat", "lng", "total", "by_type"}  # aggregates only, no PII
    bad = client.post("/api/reports", data={"scam_type": "qr", "description": "short", "location": "atlantis"})
    assert bad.status_code in (400, 422)


def test_demo_data_is_flagged(client):
    m = client.get("/api/scam-map?days=365").json()
    assert m["demo_reports"] > 0
    real = client.get("/api/scam-map?days=365&include_demo=false").json()
    assert real["demo_reports"] == 0


def test_safety_guides(client):
    guides = client.get("/api/safety-guides").json()
    assert {"upi-safety", "job-scams", "qr-scams"} <= {g["slug"] for g in guides}
    g = client.get("/api/safety-guides/upi-safety").json()
    assert "UPI PIN" in g["body_markdown"]
    assert client.get("/api/safety-guides/nope").status_code == 404


def test_safe_qr_is_not_padded_with_warnings(client):
    """Review finding: a harmless website QR said '1 warning sign' and showed UPI-scam guidance."""
    body = client.post("/api/analyze/qr", files={"file": ("q.png", qr_png("https://www.irctc.co.in/"), "image/png")}).json()
    assert body["risk_level"] == "LOW" and body["verdict"] == "No warning signs found"
    assert body["findings"] == []
    assert [c["code"] for c in body["context"]] == ["QR_URL"]          # neutral fact, not a warning
    assert "warning sign" not in body["explanation"]["summary"].replace("didn't find warning signs", "")
    assert body["explanation"]["sources"] == []
    assert not any("UPI" in w for w in body["explanation"]["why_it_matters"])


def test_user_facing_language_has_no_model_jargon(client):
    body = client.post("/api/analyze/text", json={"text": SCAM_SMS}).json()
    user_text = " ".join([body["explanation"]["summary"], *body["explanation"]["why_it_matters"],
                          *[f["label"] + " " + (f["detail"] or "") for f in body["findings"]]])
    for jargon in ("classifier", "probability", "%", "model estimates"):
        assert jargon not in user_text
    # ...while the numbers remain available for technical users.
    assert body["breakdown"]["components"][0]["model"]["probability"] > 0.5


def test_explanation_is_grounded_in_found_evidence(client):
    body = client.post("/api/analyze/text", json={
        "text": "Congratulations, you are selected for a work from home job. Pay Rs 499 registration fee to start."}).json()
    codes = {f["code"] for f in body["findings"]}
    guides = {s["slug"] for s in body["explanation"]["sources"]}
    assert "UPFRONT_FEE" in codes and "job-scams" in guides
    # why_it_matters doesn't repeat the finding rationales verbatim
    details = {f["detail"] for f in body["findings"] if f["detail"]}
    assert not any(d in w for d in details for w in body["explanation"]["why_it_matters"])


def test_medium_url_warning_is_worded_as_caution(client):
    body = client.post("/api/analyze/url", json={"url": "https://bit.ly/3xVidz0"}).json()
    assert body["risk_level"] == "MEDIUM" and body["verdict"] == "Potentially suspicious"
    assert "may be genuine" in body["explanation"]["summary"]
