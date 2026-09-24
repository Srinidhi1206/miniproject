"""Idempotent seed data.

  * scam_locations — city-level gazetteer (approximate centre coordinates).
  * safety_guides  — loaded from backend/knowledge/*.md (same corpus as RAG).
  * DEMO scam reports — clearly flagged `is_demo=True`, fictional, generated
    with a fixed seed so every install shows the same demo map. The UI labels
    them "DEMO DATA" and lets users hide them. Disable with SEED_DEMO=0.
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import SafetyGuide, ScamLocation, ScamReport
from app.rag.knowledge import load_knowledge

# slug, city, region, lat, lng
LOCATIONS: list[tuple[str, str, str, float, float]] = [
    ("mumbai", "Mumbai", "Maharashtra", 19.076, 72.8777),
    ("pune", "Pune", "Maharashtra", 18.5204, 73.8567),
    ("nagpur", "Nagpur", "Maharashtra", 21.1458, 79.0882),
    ("delhi", "New Delhi", "Delhi", 28.6139, 77.209),
    ("gurugram", "Gurugram", "Haryana", 28.4595, 77.0266),
    ("noida", "Noida", "Uttar Pradesh", 28.5355, 77.391),
    ("lucknow", "Lucknow", "Uttar Pradesh", 26.8467, 80.9462),
    ("kanpur", "Kanpur", "Uttar Pradesh", 26.4499, 80.3319),
    ("varanasi", "Varanasi", "Uttar Pradesh", 25.3176, 82.9739),
    ("bengaluru", "Bengaluru", "Karnataka", 12.9716, 77.5946),
    ("mysuru", "Mysuru", "Karnataka", 12.2958, 76.6394),
    ("mangaluru", "Mangaluru", "Karnataka", 12.9141, 74.856),
    ("hyderabad", "Hyderabad", "Telangana", 17.385, 78.4867),
    ("warangal", "Warangal", "Telangana", 17.9689, 79.5941),
    ("visakhapatnam", "Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185),
    ("vijayawada", "Vijayawada", "Andhra Pradesh", 16.5062, 80.648),
    ("chennai", "Chennai", "Tamil Nadu", 13.0827, 80.2707),
    ("coimbatore", "Coimbatore", "Tamil Nadu", 11.0168, 76.9558),
    ("madurai", "Madurai", "Tamil Nadu", 9.9252, 78.1198),
    ("kochi", "Kochi", "Kerala", 9.9312, 76.2673),
    ("thiruvananthapuram", "Thiruvananthapuram", "Kerala", 8.5241, 76.9366),
    ("kolkata", "Kolkata", "West Bengal", 22.5726, 88.3639),
    ("bhubaneswar", "Bhubaneswar", "Odisha", 20.2961, 85.8245),
    ("patna", "Patna", "Bihar", 25.5941, 85.1376),
    ("ranchi", "Ranchi", "Jharkhand", 23.3441, 85.3096),
    ("guwahati", "Guwahati", "Assam", 26.1445, 91.7362),
    ("ahmedabad", "Ahmedabad", "Gujarat", 23.0225, 72.5714),
    ("surat", "Surat", "Gujarat", 21.1702, 72.8311),
    ("vadodara", "Vadodara", "Gujarat", 22.3072, 73.1812),
    ("jaipur", "Jaipur", "Rajasthan", 26.9124, 75.7873),
    ("jodhpur", "Jodhpur", "Rajasthan", 26.2389, 73.0243),
    ("bhopal", "Bhopal", "Madhya Pradesh", 23.2599, 77.4126),
    ("indore", "Indore", "Madhya Pradesh", 22.7196, 75.8577),
    ("raipur", "Raipur", "Chhattisgarh", 21.2514, 81.6296),
    ("chandigarh", "Chandigarh", "Chandigarh", 30.7333, 76.7794),
    ("ludhiana", "Ludhiana", "Punjab", 30.901, 75.8573),
    ("dehradun", "Dehradun", "Uttarakhand", 30.3165, 78.0322),
    ("srinagar", "Srinagar", "Jammu and Kashmir", 34.0837, 74.7973),
    ("goa", "Panaji", "Goa", 15.4909, 73.8278),
    ("mewat", "Nuh", "Haryana", 28.1024, 77.0012),
    ("jamtara", "Jamtara", "Jharkhand", 23.9626, 86.8024),
]

# Weighted mix for demo data (roughly shaped like public reporting trends: UPI and
# job/task scams dominate). Values are illustrative, NOT real statistics.
_DEMO_TYPES = [("upi", 30), ("job", 22), ("phishing", 16), ("investment", 10), ("call", 9),
               ("fake_website", 6), ("qr", 5), ("other", 2)]
_DEMO_TEXT = {
    "upi": "DEMO: Buyer asked me to scan a QR to receive payment for an item I was selling.",
    "job": "DEMO: Offered a part-time 'rate hotels' job, then asked to deposit money for prepaid tasks.",
    "phishing": "DEMO: SMS said my bank KYC expired and linked to a fake login page.",
    "investment": "DEMO: Added to a stock-tips WhatsApp group promising guaranteed returns.",
    "call": "DEMO: Caller claimed to be from customs about a parcel with illegal items.",
    "fake_website": "DEMO: Online store with huge discounts took payment and never delivered.",
    "qr": "DEMO: QR sticker on a parking meter led to a payment page.",
    "other": "DEMO: Received a suspicious message asking for personal details.",
}


def seed_locations(db: Session) -> int:
    existing = set(db.scalars(select(ScamLocation.slug)).all())
    added = 0
    for slug, city, region, lat, lng in LOCATIONS:
        if slug not in existing:
            db.add(ScamLocation(slug=slug, city=city, region=region, lat=lat, lng=lng))
            added += 1
    db.commit()
    return added


def seed_guides(db: Session) -> int:
    """Upsert guides from the knowledge base so edits to the markdown propagate."""
    count = 0
    for doc in load_knowledge():
        g = db.scalar(select(SafetyGuide).where(SafetyGuide.slug == doc.slug)) or SafetyGuide(slug=doc.slug)
        g.title, g.category, g.summary = doc.title, doc.category, doc.summary
        g.body_markdown, g.tags, g.read_minutes, g.order = doc.body, list(doc.tags), doc.read_minutes, doc.order
        db.add(g)
        count += 1
    db.commit()
    return count


def seed_demo_reports(db: Session, n: int = 160) -> int:
    if db.scalar(select(func.count(ScamReport.id)).where(ScamReport.is_demo.is_(True))):
        return 0
    rng = random.Random(2026)  # fixed seed: reproducible demo data, not a prediction of anything
    locs = db.scalars(select(ScamLocation)).all()
    if not locs:
        return 0
    # Larger cities get more demo reports.
    weights = [5 if l.slug in {"mumbai", "delhi", "bengaluru", "hyderabad", "kolkata", "chennai", "pune"} else
               3 if l.slug in {"jamtara", "mewat", "noida", "gurugram", "jaipur", "ahmedabad"} else 1 for l in locs]
    types, type_w = zip(*_DEMO_TYPES)
    now = datetime.now(timezone.utc)
    for i in range(n):
        stype = rng.choices(types, weights=type_w)[0]
        loc = rng.choices(locs, weights=weights)[0]
        created = now - timedelta(days=rng.triangular(0, 180, 20), hours=rng.uniform(0, 24))
        lost = round(rng.choice([0, 0, 0, rng.uniform(200, 5000), rng.uniform(5000, 90000)]), 0) or None
        db.add(ScamReport(public_id=f"DEMO-{i + 1:04d}", created_at=created, scam_type=stype,
                          description=_DEMO_TEXT[stype], amount_lost=lost, location_id=loc.id, is_demo=True))
    db.commit()
    return n


def remove_demo_reports(db: Session) -> int:
    res = db.execute(delete(ScamReport).where(ScamReport.is_demo.is_(True)))
    db.commit()
    return res.rowcount or 0


def seed_all(db: Session) -> dict[str, int]:
    out = {"locations": seed_locations(db), "guides": seed_guides(db)}
    if os.getenv("SEED_DEMO", "1") != "0":
        out["demo_reports"] = seed_demo_reports(db)
    return out
