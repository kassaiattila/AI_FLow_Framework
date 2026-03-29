#!/usr/bin/env python3
"""EML/MSG email viewer - decode MIME emails to readable text.

Usage:
    python scripts/eml_viewer.py test_emails/example.eml
    python scripts/eml_viewer.py test_emails/example.eml --output decoded/
    python scripts/eml_viewer.py test_emails/ --output decoded/
"""

import email
import sys
from email import policy
from pathlib import Path


def decode_eml(eml_path: Path) -> str:
    """Parse .eml file and return human-readable text."""
    with open(eml_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    lines: list[str] = []

    # Headers
    lines.append(f"From:    {msg['from'] or '(none)'}")
    lines.append(f"To:      {msg['to'] or '(none)'}")
    if msg["cc"]:
        lines.append(f"Cc:      {msg['cc']}")
    lines.append(f"Subject: {msg['subject'] or '(none)'}")
    lines.append(f"Date:    {msg['date'] or '(none)'}")
    lines.append("")
    lines.append("=" * 72)
    lines.append("")

    # Body - prefer plain text, fall back to HTML stripped
    body = msg.get_body(preferencelist=("plain",))
    if body:
        lines.append(body.get_content())
    else:
        body = msg.get_body(preferencelist=("html",))
        if body:
            html = body.get_content()
            # Basic HTML tag stripping for readability
            import re

            text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
            text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"<[^>]+>", "", text)
            text = re.sub(r"&nbsp;", " ", text)
            text = re.sub(r"&amp;", "&", text)
            text = re.sub(r"&lt;", "<", text)
            text = re.sub(r"&gt;", ">", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
            lines.append("[HTML content - tags stripped]")
            lines.append("")
            lines.append(text.strip())
        else:
            lines.append("[No text or HTML body found]")

    # Attachments list
    attachments = []
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = part.get_filename() or "(unnamed)"
            size = len(part.get_content() if isinstance(part.get_content(), bytes) else b"")
            attachments.append((filename, size))

    if attachments:
        lines.append("")
        lines.append("=" * 72)
        lines.append("Attachments:")
        for fname, size in attachments:
            if size > 0:
                lines.append(f"  - {fname} ({size:,} bytes)")
            else:
                lines.append(f"  - {fname}")

    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_dir = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_dir = Path(sys.argv[idx + 1])

    # Collect .eml files
    if input_path.is_dir():
        eml_files = sorted(input_path.glob("**/*.eml"))
    elif input_path.is_file() and input_path.suffix == ".eml":
        eml_files = [input_path]
    else:
        print(f"Error: {input_path} is not an .eml file or directory")
        sys.exit(1)

    if not eml_files:
        print(f"No .eml files found in {input_path}")
        sys.exit(1)

    for eml_file in eml_files:
        try:
            decoded = decode_eml(eml_file)
        except Exception as e:
            print(f"Error decoding {eml_file.name}: {e}", file=sys.stderr)
            continue

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_file = output_dir / f"{eml_file.stem}.txt"
            out_file.write_text(decoded, encoding="utf-8")
            print(f"  {eml_file.name} -> {out_file}")
        else:
            if len(eml_files) > 1:
                print(f"\n{'#' * 72}")
                print(f"# {eml_file.name}")
                print(f"{'#' * 72}\n")
            print(decoded)


if __name__ == "__main__":
    main()
