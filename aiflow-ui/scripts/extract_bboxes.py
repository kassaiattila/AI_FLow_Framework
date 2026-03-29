"""Extract text bounding boxes from a PDF using Docling.
Outputs JSON with normalized coordinates (0-1) for frontend overlay.

Usage: python extract_bboxes.py <input.pdf> <output.json>
"""
import sys
import json
from docling.document_converter import DocumentConverter


def extract(pdf_path: str) -> dict:
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc = result.document

    # Get page dimensions
    pages = {}
    for pg in doc.pages.values():
        pages[pg.page_no] = {"width": pg.size.width, "height": pg.size.height}

    # Extract all text blocks with bounding boxes
    blocks = []
    for item in doc.texts:
        if not hasattr(item, "prov") or not item.prov:
            continue
        for p in item.prov:
            if not hasattr(p, "bbox"):
                continue
            b = p.bbox
            page_no = p.page_no
            page_dims = pages.get(page_no, {"width": 595, "height": 842})
            pw = page_dims["width"]
            ph = page_dims["height"]

            # Convert PDF coords (origin bottom-left) to normalized screen coords (origin top-left)
            # PDF: L=left, T=top-in-pdf (higher=upper), R=right, B=bottom-in-pdf (lower=lower)
            # But Docling bbox: l=left, t=top, r=right, b=bottom in PDF coordinate system
            # where Y increases upward. So screen_y_top = page_height - pdf_t
            x = b.l / pw
            y = (ph - b.t) / ph  # flip Y: PDF top → screen top
            w = (b.r - b.l) / pw
            h = (b.t - b.b) / ph  # height in normalized units

            blocks.append({
                "page": page_no,
                "text": item.text[:200],
                "bbox": {
                    "x": round(x, 4),
                    "y": round(y, 4),
                    "width": round(w, 4),
                    "height": round(h, 4),
                },
            })

    return {
        "pages": pages,
        "blocks": blocks,
        "total_blocks": len(blocks),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_bboxes.py <input.pdf> <output.json>")
        sys.exit(1)

    data = extract(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Extracted {data['total_blocks']} blocks from {len(data['pages'])} pages")
