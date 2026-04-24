"""Generate the 10 Sprint Q UC1 golden-path invoice PDFs from manifest.yaml.

Idempotent: running twice overwrites the existing PDFs with byte-identical
output for the same manifest (reportlab + fixed metadata). No binary blobs
in git — run this script to regenerate.

Usage (from repo root)::

    .venv/Scripts/python.exe data/fixtures/invoices_sprint_q/generate_invoices.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

FIXTURE_DIR = Path(__file__).parent


def _draw_simple(c: canvas.Canvas, f: dict[str, Any]) -> None:
    """Simple single-line invoice with header + one amount."""
    e = f["expected"]
    c.setFont("Helvetica-Bold", 16)
    c.drawString(25 * mm, 270 * mm, "INVOICE" if f["lang"] == "en" else "SZAMLA")
    c.setFont("Helvetica", 11)
    y = 250 * mm
    lines = [
        (f"Invoice No: {e['invoice_number']}", f"Szamlaszam: {e['invoice_number']}"),
        (f"Supplier: {e['vendor_name']}", f"Szallito: {e['vendor_name']}"),
        (f"Customer: {e['buyer_name']}", f"Vevo: {e['buyer_name']}"),
        (f"Issue date: {e['issue_date']}", f"Kiallitas datuma: {e['issue_date']}"),
        (f"Due date: {e['due_date']}", f"Fizetesi hatarido: {e['due_date']}"),
        (f"Currency: {e['currency']}", f"Penznem: {e['currency']}"),
    ]
    for en_line, hu_line in lines:
        c.drawString(25 * mm, y, hu_line if f["lang"] == "hu" else en_line)
        y -= 7 * mm

    y -= 10 * mm
    c.setFont("Helvetica-Bold", 13)
    total_label = "Vegosszeg" if f["lang"] == "hu" else "Total"
    c.drawString(25 * mm, y, f"{total_label}: {e['gross_total']:,} {e['currency']}")


def _draw_tabular(c: canvas.Canvas, f: dict[str, Any]) -> None:
    """Invoice with a line-item table and VAT breakdown."""
    e = f["expected"]
    c.setFont("Helvetica-Bold", 16)
    c.drawString(25 * mm, 275 * mm, "INVOICE" if f["lang"] == "en" else "SZAMLA")

    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, 260 * mm, f"No: {e['invoice_number']}")
    c.drawString(25 * mm, 253 * mm, f"From: {e['vendor_name']}")
    c.drawString(25 * mm, 246 * mm, f"To: {e['buyer_name']}")
    c.drawString(120 * mm, 260 * mm, f"Issue: {e['issue_date']}")
    c.drawString(120 * mm, 253 * mm, f"Due:   {e['due_date']}")
    c.drawString(120 * mm, 246 * mm, f"Currency: {e['currency']}")

    c.setFillColor(colors.lightgrey)
    c.rect(25 * mm, 225 * mm, 160 * mm, 8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    headers = (
        ["Description", "Qty", "Unit price", "Total"]
        if f["lang"] == "en"
        else ["Leiras", "Mennyiseg", "Egysegar", "Osszesen"]
    )
    c.drawString(27 * mm, 227 * mm, headers[0])
    c.drawString(100 * mm, 227 * mm, headers[1])
    c.drawString(130 * mm, 227 * mm, headers[2])
    c.drawString(165 * mm, 227 * mm, headers[3])

    c.setFont("Helvetica", 10)
    net = int(e["gross_total"] / 1.27) if f["lang"] == "hu" else int(e["gross_total"] / 1.27)
    rows = [
        (
            "Consulting services" if f["lang"] == "en" else "Tanacsadasi szolgaltatas",
            10,
            int(net / 10),
            net,
        ),
    ]
    y = 217 * mm
    for desc, qty, price, tot in rows:
        c.drawString(27 * mm, y, desc)
        c.drawString(100 * mm, y, str(qty))
        c.drawString(130 * mm, y, f"{price:,}")
        c.drawString(165 * mm, y, f"{tot:,}")
        y -= 7 * mm

    y -= 10 * mm
    net_label = "Netto" if f["lang"] == "hu" else "Net"
    vat_label = "AFA 27%" if f["lang"] == "hu" else "VAT 27%"
    gross_label = "Brutto" if f["lang"] == "hu" else "Gross"
    c.drawString(130 * mm, y, f"{net_label}:")
    c.drawString(165 * mm, y, f"{net:,}")
    y -= 7 * mm
    c.drawString(130 * mm, y, f"{vat_label}:")
    c.drawString(165 * mm, y, f"{e['gross_total'] - net:,}")
    y -= 7 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(130 * mm, y, f"{gross_label}:")
    c.drawString(165 * mm, y, f"{e['gross_total']:,} {e['currency']}")


def _draw_multi_section(c: canvas.Canvas, f: dict[str, Any]) -> None:
    """Multi-section invoice with vendor/buyer blocks + multi-page friendly."""
    e = f["expected"]
    c.setFont("Helvetica-Bold", 18)
    c.drawString(25 * mm, 275 * mm, "INVOICE" if f["lang"] == "en" else "SZAMLA")

    # Section: identity
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, 258 * mm, "From" if f["lang"] == "en" else "Szallito")
    c.drawString(110 * mm, 258 * mm, "To" if f["lang"] == "en" else "Vevo")

    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, 251 * mm, e["vendor_name"])
    c.drawString(25 * mm, 245 * mm, "Tax ID: HU-12345678")
    c.drawString(110 * mm, 251 * mm, e["buyer_name"])
    c.drawString(110 * mm, 245 * mm, "Tax ID: HU-87654321")

    # Section: metadata
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, 225 * mm, "Invoice details" if f["lang"] == "en" else "Szamla adatok")
    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, 217 * mm, f"Number / Szamlaszam: {e['invoice_number']}")
    c.drawString(25 * mm, 210 * mm, f"Issue date / Kiallitas: {e['issue_date']}")
    c.drawString(25 * mm, 203 * mm, f"Due date / Fizetesi hatarido: {e['due_date']}")
    c.drawString(25 * mm, 196 * mm, f"Currency / Penznem: {e['currency']}")

    # Section: items
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, 180 * mm, "Items / Tetelek")
    net = int(e["gross_total"] / 1.27)
    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, 172 * mm, "Complex engineering project — Phase 1")
    c.drawString(140 * mm, 172 * mm, f"{int(net * 0.6):,}")
    c.drawString(25 * mm, 165 * mm, "Complex engineering project — Phase 2")
    c.drawString(140 * mm, 165 * mm, f"{int(net * 0.4):,}")

    # Section: totals
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, 145 * mm, "Summary / Osszegzes")
    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, 137 * mm, f"Net / Netto: {net:,}")
    c.drawString(25 * mm, 130 * mm, f"VAT 27% / AFA: {e['gross_total'] - net:,}")
    c.setFont("Helvetica-Bold", 13)
    c.drawString(25 * mm, 120 * mm, f"Gross / Brutto: {e['gross_total']:,} {e['currency']}")


def _draw(f: dict[str, Any]) -> Path:
    out = FIXTURE_DIR / f["pdf"]
    c = canvas.Canvas(str(out), pagesize=A4)
    cohort = f["cohort"]
    if cohort == "simple":
        _draw_simple(c, f)
    elif cohort == "tabular":
        _draw_tabular(c, f)
    elif cohort == "multi_section":
        _draw_multi_section(c, f)
    else:
        raise ValueError(f"unknown cohort: {cohort}")
    c.showPage()
    c.save()
    return out


def main() -> int:
    manifest = yaml.safe_load((FIXTURE_DIR / "manifest.yaml").read_text(encoding="utf-8"))
    for f in manifest["fixtures"]:
        path = _draw(f)
        print(
            f"[ok] {path.relative_to(FIXTURE_DIR.parent.parent)}  ({path.stat().st_size:,} bytes)"
        )
    print(f"[done] {len(manifest['fixtures'])} invoices generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
