# SENTINEL — Project Viva Fact Check

## 1. What problem does SENTINEL solve?
SENTINEL protects ordinary consumers from digital fraud (phishing, SMS scams, fake job offers, malicious QR codes, and UPI scams) by analyzing suspicious content before the user interacts with it or loses money.

## 2. What is unique about SENTINEL?
Unlike enterprise tools, SENTINEL is built for consumers. It doesn't require an account, explains threats in plain, jargon-free language, operates transparently with deterministic risk scoring (not just an LLM black box), and includes an aggregated Community Scam Map.

## 3. What existing platforms exist?
Existing tools fall into two categories:
1. Enterprise Threat Intelligence (VirusTotal, CrowdStrike) — powerful but require technical expertise to interpret.
2. Official Reporting Portals (Cybercrime.gov.in) — reactive, designed for after a crime has occurred.

## 4. What are their limitations?
Enterprise tools overwhelm consumers with raw malware data. Reporting portals do not prevent scams in real-time. Neither provides clear, actionable "What does this mean?" or "What should I do now?" guidance for non-technical users.

## 5. Why did you use Agentic AI?
We used an Agentic Orchestrator to route inputs to specialized tools dynamically. A screenshot might need OCR, while a QR code needs decoding. The agent coordinates these deterministic tools to extract evidence without relying on a single monolithic LLM to "guess" everything.

## 6. What exactly does the agent do?
The Orchestration layer (SentinelAgent) identifies the artifact (e.g. image vs text), selects the correct specialized tools (e.g., `qr_decoder`, `ocr_reader`, `url_analyzer`), executes them to gather structured Evidence, and hands that evidence to the Risk Engine.

## 7. Does the LLM decide the final verdict?
**NO.** The LLM never decides the verdict. A deterministic Risk Engine calculates the 0-100 score based on weighted evidence. The LLM is only used at the very end to rewrite the technical evidence into a plain-language summary for the user.

## 8. Why use RAG?
Retrieval-Augmented Generation (RAG) is used to pull specific, trusted safety guidelines (e.g., "How to handle a UPI refund scam") into the explanation based on the exact tactics detected. This prevents the LLM from hallucinating generic or incorrect safety advice.

## 9. What is the role of the risk engine?
The Risk Engine applies weighted math to the collected Evidence. It handles corroboration (e.g., multiple weak signals compounding into a high risk) and maps the final 0-100 score to one of four rigid bands: LOW, MEDIUM, HIGH, CRITICAL.

## 10. How is a scam classified?
Scams are classified by checking text against known tactical indicators (urgency, OTP requests, fee requests), evaluating URLs for structural spoofing, and running content through targeted ML models. Evidence points accumulate toward a final risk threshold.

## 11. How are URLs analyzed?
URLs are structurally parsed for domain mismatches, typosquatting, and unusual TLDs. They are also optionally evaluated against the Google Safe Browsing API. We do NOT perform live, server-side crawling (DOM rendering) to avoid SSRF vulnerabilities.

## 12. How are QR codes handled?
QR codes are visually decoded using pyzbar. If the payload is a URL, it is routed to the URL analyzer. If it is a UPI payload, it is parsed for payee and amount data to check for fake "refund" or "collect" requests.

## 13. Why OpenCV/QR decoder instead of CNN?
QR codes are standardized mathematical patterns. Deterministic decoders (like zbar) are exponentially faster, perfectly accurate, and computationally cheaper than attempting to train a CNN to "read" a QR code matrix.

## 14. How does OCR fit into the pipeline?
OCR extracts raw text from screenshots. That text is then treated as a standard message and routed through the text analysis pipeline to find scam indicators and suspicious links.

## 15. What datasets/models are actually used?
We utilize specialized text classification models trained on real SMS/phishing datasets, rule-based heuristics for UPI/URL spoofing, and FastText/FAISS for the RAG embedding retrieval. 

## 16. How is the system evaluated?
The pipeline is evaluated through 70+ automated pytest suites testing component isolation, deterministic risk bounds, URL parsing safety, and explanation generation resilience. E2E Playwright tests cover the UI.

## 17. How is user privacy handled?
No account is required. History is kept locally in the browser. When a user submits a scam report to the community, descriptions are sanitized, screenshots are stripped of EXIF data, and locations are strictly aggregated to city/region level on the Scam Map.

## 18. Why is login not required?
Friction prevents adoption. Consumers need to check a suspicious message in 10 seconds. Forcing them to create an account defeats the purpose of an emergency safety tool.

## 19. How does Scam Map work?
The Scam Map visualizes aggregated community reports. Individual reports (including exact addresses and screenshots) are never exposed. It groups data by region and scam type to show local threat trends safely.

## 20. What happens if the AI/API is unavailable?
The system degrades gracefully. If the LLM is down, a deterministic template-based explanation is returned. If OCR fails, the user is prompted to paste the text manually.

## 21. What are the current limitations?
- Voice analysis is not implemented (Phase 2).
- Deepfake voice detection is not implemented (Phase 2).
- Dynamic website/DOM crawling is not implemented to prevent SSRF risks.
- Cloud-synced history across devices is not supported (intentionally local-only).

## 22. What is future scope?
Adding WebRTC-based real-time voice call screening, integrating live DOM snapshotting via headless browsers in isolated sandboxes, and expanding the Community Scam Map with real-time alerting.
