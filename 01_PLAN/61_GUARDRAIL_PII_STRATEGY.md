# AIFlow Guardrail PII Strategy — Per-Skill Configuration

> **Verzio:** 1.0 | **Datum:** 2026-04-05
> **Kontextus:** Sprint B B0.1 — A fix PII masking MEGHIUSITJA az uzleti funkciokat!
> **Elofeltetel:** Sprint A (A5) — GuardrailFramework KESZ (InputGuard, OutputGuard, ScopeGuard)

---

## 1. Problema

A fix (minden skill-re azonos) PII masking **uzleti akadalyt jelent**:
- **Invoice processing:** adoszam, bankszamla, cegnev, osszeg = mind PII, de KELL az LLM prompt-ban
- **Email intent:** email cim, nev, ceginformacio = PII, de routing-hoz szukseges
- **Chat (ASZF RAG):** SEMMI PII nem kell — teljes masking biztonsagos

Megoldas: **per-skill PII konfiguracio** a `guardrails.yaml`-ben.

---

## 2. Per-Skill PII Konfiguracio

| Skill | pii_masking | allowed_pii | Indoklas |
|-------|-------------|-------------|----------|
| aszf_rag_chat | `on` (full) | `[]` | Chat — SEMMI PII nem szukseges. Teljes vedelem. |
| email_intent_processor | `partial` | `[email, name, company]` | Routing-hoz kell a felado/cimzett. |
| invoice_processor | `off` | `[all]` | Szamla mezok (adoszam, bankszamla, osszeg) = PII. |
| process_documentation | `on` | `[]` | Dokumentum generalas — nincs PII szukseg. |
| cubix_course_capture | `on` | `[]` | Video transcript — nincs PII szukseg. |

---

## 3. GuardrailConfig Bovites

### Jelenlegi (A5 — src/aiflow/guardrails/config.py)

```python
@dataclass
class GuardrailConfig:
    input_guard_enabled: bool = True
    output_guard_enabled: bool = True
    scope_guard_enabled: bool = True
    pii_masking: bool = True          # ← FIX, minden skill-re azonos
    max_input_length: int = 2000
```

### Bovitett (B0.1 — tervezett)

```python
from enum import Enum

class PIIMaskingMode(str, Enum):
    ON = "on"           # Teljes masking — semmi PII nem jut at
    PARTIAL = "partial" # Csak az allowed_pii tipusok jutnak at
    OFF = "off"         # Nincs masking — minden PII atlathato (pl. szamla)

@dataclass
class GuardrailConfig:
    input_guard_enabled: bool = True
    output_guard_enabled: bool = True
    scope_guard_enabled: bool = True
    pii_masking_mode: PIIMaskingMode = PIIMaskingMode.ON  # Default: vedett
    allowed_pii_types: list[str] = field(default_factory=list)  # partial mod-ban
    pii_logging: bool = False  # Ha True: logoljuk MIT maskoltunk (audit trail)
    max_input_length: int = 2000
```

---

## 4. Per-Skill guardrails.yaml Pelda

### aszf_rag_chat (full protection)

```yaml
# skills/aszf_rag_chat/guardrails.yaml
input:
  pii_masking: "on"
  allowed_pii: []
  max_length: 2000
  injection_check: true
output:
  require_citation: true
  hallucination_threshold: 0.7
  pii_leak_check: true
scope:
  allowed_topics: ["jog", "biztositas", "aszf", "szolgaltatas"]
  blocked_topics: ["politika", "orvosi tanacs", "befektetesi tanacs"]
  dangerous_patterns: ["hogyan torzek be", "hogyan hackeljem"]
```

### invoice_processor (PII OFF — szamla kontextus)

```yaml
# skills/invoice_processor/guardrails.yaml
input:
  pii_masking: "off"
  pii_logging: true     # Audit: logoljuk hogy milyen PII-t latott
  max_length: 5000      # Szamlak hosszabbak lehetnek
  injection_check: true
output:
  validate_amounts: true
  validate_dates: true
  pii_leak_check: false  # A szamla adatok KELLENEK az outputban
```

### email_intent_processor (partial — routing-hoz kell)

```yaml
# skills/email_intent_processor/guardrails.yaml
input:
  pii_masking: "partial"
  allowed_pii: ["email", "name", "company"]
  max_length: 3000
  injection_check: true
output:
  require_confidence: 0.7
  max_intents: 3
  pii_leak_check: true  # Ne szivarodjon ki tobb mint amit allowed
```

---

## 5. Teszteles Modszertan

### Unit tesztek (B1.2-ben implementalando)

```python
# tests/unit/guardrails/test_pii_config.py

def test_on_mode_masks_all_pii():
    """ON mod: minden PII tipust maszkol."""
    config = GuardrailConfig(pii_masking_mode=PIIMaskingMode.ON)
    result = input_guard.check(text_with_pii, config)
    assert "adoszam" not in result.sanitized_text
    assert "bankszamla" not in result.sanitized_text

def test_off_mode_passes_all_pii():
    """OFF mod: semmi PII-t nem maszkol (szamla kontextus)."""
    config = GuardrailConfig(pii_masking_mode=PIIMaskingMode.OFF)
    result = input_guard.check(text_with_pii, config)
    assert "12345678" in result.sanitized_text  # adoszam atjut

def test_partial_mode_allows_specified():
    """PARTIAL mod: csak az allowed tipusok jutnak at."""
    config = GuardrailConfig(
        pii_masking_mode=PIIMaskingMode.PARTIAL,
        allowed_pii_types=["email", "name"]
    )
    result = input_guard.check(text_with_pii, config)
    assert "user@example.com" in result.sanitized_text  # email atjut
    assert "12345678" not in result.sanitized_text       # adoszam maszkolt
```

### Promptfoo tesztek (B1.2-ben)

Minden skill-hez 3 PII-specifikus test case:
1. **Known PII input → helyes masking az adott mod szerint**
2. **PII leak check output → helyes detektalas**
3. **Edge case: magyar PII formatum** (adoszam 8 jegy, bankszamla 8-8-8)

---

## 6. Implementacios Terv

| Lepes | Sprint B fazis | Feladat |
|-------|---------------|---------|
| 1 | B0.1 (jelen dok) | PII strategia dokumentacio |
| 2 | B1.1 | `freetext_pii_detector` LLM prompt (regex NEM tud: "Kiss Janos az OTP-nel") |
| 3 | B1.2 | Per-skill `guardrails.yaml` (5 fajl) |
| 4 | B1.2 | GuardrailConfig bovites (PIIMaskingMode enum) |
| 5 | B1.2 | InputGuard modositas: pii_masking_mode + allowed_pii_types |
| 6 | B1.2 | Unit tesztek (on/off/partial mod) |
| 7 | B4 | Skill hardening: per-skill PII config validacio |

---

## 7. Magyar PII Tipusok (InputGuard referencia)

| Tipus | Regex minta | Pelda |
|-------|------------|-------|
| Adoszam | `\b\d{8}-\d-\d{2}\b` vagy `\b\d{8}\b` | 12345678-2-42 |
| Bankszamla | `\b\d{8}-\d{8}(-\d{8})?\b` | 11773016-01234567-00000000 |
| TAJ szam | `\b\d{3}[ -]?\d{3}[ -]?\d{3}\b` | 123 456 789 |
| Szemelyi ig. | `\b\d{6}[A-Z]{2}\b` | 123456AB |
| Telefonszam | `\+36[ -]?\d{1,2}[ -]?\d{3}[ -]?\d{4}` | +36 30 123 4567 |
| Email | standard email regex | user@example.com |
| Iranyitoszam + varos | `\b\d{4}\b` + magyar varosnevek | 1011 Budapest |
