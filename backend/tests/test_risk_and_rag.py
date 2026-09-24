from app.rag.index import retrieve
from app.rag.knowledge import load_knowledge, parse_doc
from app.risk import engine as risk
from app.schemas.analysis import Evidence, ModelOutput, RiskLevel


def ev(code, weight, severity="medium"):
    return Evidence(code=code, label=code, severity=severity, weight=weight, source="test")


def model(p, target="text"):
    return ModelOutput(name="m", version="1", target=target, probability=p, label="scam" if p >= .5 else "legit")


def test_bands_match_spec():
    assert [risk.band(s) for s in (0, 29, 30, 59, 60, 79, 80, 100)] == [
        RiskLevel.LOW, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.MEDIUM,
        RiskLevel.HIGH, RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.CRITICAL]


def test_text_component_formula():
    c = risk.score_text("x", model(0.5), [ev("A", 8), ev("B", 10)])
    assert c.model_points == 35.0 and c.rule_points == 18 and c.score == 53


def test_text_rule_points_are_capped():
    c = risk.score_text("x", model(0.1), [ev(str(i), 12) for i in range(6)])
    assert c.rule_points == 30


def test_critical_tactic_floor():
    c = risk.score_text("x", model(0.05), [ev("OTP_REQUEST", 18, "critical")])
    assert c.score == 60 and c.overrides


def test_url_brand_impersonation_floor_and_trusted_discount():
    risky = risk.score_url("u", model(0.2, "url"), [ev("BRAND_IMPERSONATION", 22, "critical")])
    assert risky.score >= 70
    safe = risk.score_url("u", model(0.3, "url"), [ev("KNOWN_DOMAIN", -40, "positive")])
    assert safe.score == 0


def test_combine_uses_max_plus_corroboration():
    a = risk.score_text("t", model(1.0), [ev("A", 10)])       # 80
    b = risk.score_url("u", model(1.0, "url"), [ev("B", 5)])  # 60
    c = risk.score_url("u2", model(0.0, "url"), [])           # 0
    br = risk.combine([c, b, a])
    assert br.base_score == 80 and br.corroboration_bonus == 5 and br.final_score == 85
    assert [x.score for x in br.components] == [80, 60, 0]


def test_upi_bait_note_floor():
    c = risk.score_upi("upi", [ev("UPI_BAIT_NOTE", 18, "critical")])
    assert c.score == 75


def test_knowledge_base_loads_and_chunks():
    docs = load_knowledge()
    assert len(docs) >= 10
    assert all(d.chunks for d in docs)
    doc = parse_doc("---\nslug: s\ntitle: T\ntags: [A, B]\n---\n\n## One\nFirst para.\n\nSecond.\n\n## Two\nText")
    assert [c.section for c in doc.chunks] == ["One", "Two"] and doc.chunks[0].lead == "First para."


def test_retrieval_is_grounded_in_evidence_codes():
    hits = retrieve("asks you to enter UPI PIN to receive money", ["PIN_REQUEST", "RECEIVE_MONEY_TRICK"], k=3)
    assert hits[0][0].slug in {"upi-safety", "qr-scams"}
    hits = retrieve("registration fee for job offer letter", ["UPFRONT_FEE", "TASK_JOB"], k=2)
    assert hits[0][0].slug == "job-scams"
