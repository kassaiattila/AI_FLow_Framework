# Sprint O (v1.4.11) UC3 Attachment-Aware Intent Fixture

> 25 synthetic .eml fixtures for measuring the Sprint K → Sprint O
> classifier misclassification baseline. Paired with
> `scripts/measure_uc3_baseline.py`.

## Layout

| File                      | Purpose                                                         |
|---------------------------|-----------------------------------------------------------------|
| `manifest.yaml`           | Ground-truth intent per fixture + cohort / category metadata.   |
| `generate_fixtures.py`    | Rebuilds all 25 `.eml` files from the manifest (idempotent).    |
| `NNN_slug.eml`            | 25 fixture emails (RFC822). Attachments are embedded MIME parts.|

## Cohort split (25 total)

| Cohort                | Count | Signal source                                      |
|-----------------------|-------|----------------------------------------------------|
| `invoice_attachment`  | 6     | PDF attachment carries invoice number + amount.    |
| `contract_docx`       | 6     | DOCX attachment carries contract clauses.          |
| `body_only`           | 6     | Body + subject only (Sprint K sweet spot).         |
| `mixed`               | 7     | Ambiguous — deliberate traps (log PDFs, marketing brochures, complaints about invoices, etc.). |

## Intent category coverage (abstract, per plan 112)

- **EXTRACT** — invoice / contract → Sprint K intents `invoice_received`, `order`.
- **INFORMATION_REQUEST** — inquiries, calendar invites → `inquiry`, `calendar_invite`.
- **SUPPORT** — bug reports / technical help → `support`.
- **SPAM** — marketing + automated system notifications → `marketing`, `notification`.

The manifest also carries `complaint` (mapped as `INFORMATION_REQUEST` adjacent
for this sprint — it is an intent the attachment signal should NOT override).

## Regenerating

```
.venv/Scripts/python.exe data/fixtures/emails_sprint_o/generate_fixtures.py
```

Deterministic: re-running against the same manifest produces byte-identical
`.eml` output. Attachment payloads (PDF via `reportlab`, DOCX via
`python-docx`) are generated inline from the specs in `generate_fixtures.py`.

## STOP conditions (from S126 session prompt)

1. **Fixture build > 90 minutes** → drop synthetic PDFs, fall back to text-only
   `.eml` (HALT otherwise per the session prompt).
2. **Fixture directory > 100 MB** → gitignore + document seed generation in
   `docs/fixture_seed.md`. Current footprint: ~390 KB.
3. **Baseline misclass rate < 15%** → sprint value unproven, halt and
   hand back to user.

## Git tracking

All 25 `.eml` files are tracked. The fixture corpus is committed so CI can
replay the baseline script on every PR once the S127 extractor lands.
