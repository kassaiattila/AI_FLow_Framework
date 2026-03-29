"""Convert PDF pages to PNG images using pypdfium2.
Usage: python pdf_to_png.py <input.pdf> <output_dir>
Creates: output_dir/page_1.png, page_2.png, ...
"""
import sys
import os
import pypdfium2 as pdfium

def convert(pdf_path: str, output_dir: str, dpi: int = 150) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    doc = pdfium.PdfDocument(pdf_path)
    paths = []
    for i in range(len(doc)):
        page = doc[i]
        bitmap = page.render(scale=dpi / 72)
        img = bitmap.to_pil()
        out_path = os.path.join(output_dir, f"page_{i + 1}.png")
        img.save(out_path)
        paths.append(out_path)
        print(f"Rendered page {i + 1}: {out_path}")
    doc.close()
    return paths

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pdf_to_png.py <input.pdf> <output_dir>")
        sys.exit(1)
    result = convert(sys.argv[1], sys.argv[2])
    print(f"Done: {len(result)} pages")
