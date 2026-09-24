# Data

| Path | Source | Licence | Committed? |
|---|---|---|---|
| `raw/sms_spam/` | [UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection) — 5,574 real SMS labelled spam/ham | CC BY 4.0 | No — run `python scripts/fetch_datasets.py` |
| `raw/phiusiil/` | [UCI PhiUSIIL Phishing URL Dataset](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset) — 235,795 URLs | CC BY 4.0 | No |
| `raw/tranco/` | [Tranco top-1M list](https://tranco-list.eu/) — research ranking of popular domains | Free for research | No |
| `curated/sentinel_messages.csv` | **Author-written, fictional** messages (≈100 scam, ≈100 legitimate) covering India-specific patterns missing from the 2011 SMS corpus: UPI collect/QR tricks, KYC, task jobs, digital arrest, loan apps, genuine bank/OTP/delivery notices | Project licence | Yes |

## Notes on the curated set

* Every scam example is fictional. Phone numbers, UPI IDs and domains are invented.
* Legitimate examples deliberately include transactional messages that *look* alarming
  (OTP notices, debit alerts, bill reminders) so the model learns that "OTP" or "Rs" alone
  is not a scam signal.
* It is small and author-labelled, so it is weighted ×3 in training and evaluated
  separately (`holdout_curated` in `models/text_scam_lr.metrics.json`).

`processed/` is reserved for derived datasets (not used by the MVP pipeline).
