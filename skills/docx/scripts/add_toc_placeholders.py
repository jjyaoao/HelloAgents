#!/usr/bin/env python3
"""
Add placeholder entries to Table of Contents in a DOCX file.

This script adds placeholder TOC entries between the 'separate' and 'end'
field characters, so users see some content on first open instead of an empty TOC.
The original file is replaced with the modified version.

Usage:
    python add_toc_placeholders.py <docx_file> --entries <entries_json>

    entries_json format: JSON string with array of objects:
    [
        {"level": 1, "text": "Chapter 1 Overview", "page": "1"},
        {"level": 2, "text": "Section 1.1 Details", "page": "1"}
    ]

    If --entries is not provided, generates generic placeholders.

Example:
    python add_toc_placeholders.py document.docx
    python add_toc_placeholders.py document.docx --entries '[{"level":1,"text":"Introduction","page":"1"}]'
"""

import argparse
import html
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


def add_toc_placeholders(docx_path: str, entries: list = None) -> None:
    """Add placeholder TOC entries to a DOCX file (in-place replacement).

    Args:
        docx_path: Path to DOCX file (will be modified in-place)
        entries: Optional list of placeholder entries. Each entry should be a dict
                 with 'level' (1-3), 'text', and 'page' keys.
    """
    docx_path = Path(docx_path)

    # Create temp directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        extracted_dir = temp_path / "extracted"
        temp_output = temp_path / "output.docx"

        # Extract DOCX
        with zipfile.ZipFile(docx_path, 'r') as zip_ref:
            zip_ref.extractall(extracted_dir)

        # Detect TOC styles from styles.xml
        toc_style_mapping = _detect_toc_styles(extracted_dir / "word" / "styles.xml")
        print(toc_style_mapping)
        # Process document.xml
        document_xml = extracted_dir / "word" / "document.xml"
        if not document_xml.exists():
            raise ValueError("document.xml not found in the DOCX file")

        # Read and process XML
        content = document_xml.read_text(encoding='utf-8')

        # Find TOC structure and add placeholders
        modified_content = _insert_toc_placeholders(content, entries, toc_style_mapping)

        # Write back
        document_xml.write_text(modified_content, encoding='utf-8')

        # Repack DOCX to temp file
        with zipfile.ZipFile(temp_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in extracted_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(extracted_dir)
                    zipf.write(file_path, arcname)

        # Replace original file with modified version (use shutil.move for cross-device support)
        docx_path.unlink()
        shutil.move(str(temp_output), str(docx_path))


def _detect_toc_styles(styles_xml_path: Path) -> dict:
    """Detect TOC style IDs from styles.xml.

    Args:
        styles_xml_path: Path to styles.xml

    Returns:
        Dictionary mapping level (1, 2, 3) to style ID
    """
    default_mapping = {1: "9", 2: "11", 3: "12"}

    if not styles_xml_path.exists():
        return default_mapping

    content = styles_xml_path.read_text(encoding='utf-8')

    # Find styles with names like "toc 1", "toc 2", "toc 3"
    import re
    toc_styles = {}
    for match in re.finditer(r'<w:style[^>]*w:styleId="([^"]*)"[^>]*>.*?<w:name\s+w:val="toc\s+(\d)"', content, re.DOTALL):
        style_id = match.group(1)
        level = int(match.group(2))
        toc_styles[level] = style_id

    # If we found styles, use them; otherwise use defaults
    return toc_styles if toc_styles else default_mapping


def _insert_toc_placeholders(xml_content: str, entries: list = None, toc_style_mapping: dict = None) -> str:
    """Insert placeholder TOC entries into XML content.

    Args:
        xml_content: The XML content of document.xml
        entries: Optional list of placeholder entries
        toc_style_mapping: Dictionary mapping level to style ID

    Returns:
        Modified XML content with placeholders inserted
    """
    # Generate default placeholder entries if none provided
    if entries is None:
        entries = [
            {"level": 1, "text": "Chapter 1 Overview", "page": "1"},
            {"level": 2, "text": "Section 1.1 Details", "page": "1"},
            {"level": 2, "text": "Section 1.2 More Details", "page": "2"},
            {"level": 1, "text": "Chapter 2 Content", "page": "3"},
        ]

    # Use provided mapping or default
    if toc_style_mapping is None:
        toc_style_mapping = {1: "9", 2: "11", 3: "12"}

    # Find the TOC structure: w:p with w:fldChar separate, followed by w:p with w:fldChar end
    # Pattern: <w:p><w:r>...<w:fldChar w:fldCharType="separate"/></w:r></w:p><w:p><w:r><w:fldChar w:fldCharType="end"/>
    separate_end_pattern = (
        r'(<w:p[^>]*><w:r[^>]*>.*?<w:fldChar[^>]*w:fldCharType="separate"[^>]*/></w:r></w:p>)'
        r'(<w:p[^>]*><w:r[^>]*>.*?<w:fldChar[^>]*w:fldCharType="end"[^>]*/></w:r></w:p>)'
    )

    import re

    def replace_with_placeholders(match):
        separate_para = match.group(1)
        end_para = match.group(2)

        # Indentation values in twips (1 inch = 1440 twips)
        # Level 1: 0, Level 2: 0.25" (360), Level 3: 0.5" (720), Level 4+: 0.75" (1080)
        indent_mapping = {1: 0, 2: 360, 3: 720, 4: 1080, 5: 1440, 6: 1800}

        # Generate placeholder paragraphs matching Word's TOC format
        placeholder_paragraphs = []
        for entry in entries:
            level = entry.get('level', 1)
            text = html.escape(entry.get('text', ''))
            page = entry.get('page', '1')

            # Get style ID for this level
            toc_style = toc_style_mapping.get(level, toc_style_mapping.get(1, "9"))

            # Get indentation for this level
            indent = indent_mapping.get(level, 0)
            indent_attr = f'<w:ind w:left="{indent}"/>' if indent > 0 else ''

            # Use w:tab element (not w:tabStop) like Word does
            placeholder_para = f'''<w:p>
  <w:pPr>
    <w:pStyle w:val="{toc_style}"/>
    {indent_attr}
    <w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9026"/></w:tabs>
  </w:pPr>
  <w:r><w:t>{text}</w:t></w:r>
  <w:r><w:tab/></w:r>
  <w:r><w:t>{page}</w:t></w:r>
</w:p>'''
            placeholder_paragraphs.append(placeholder_para)

        # Join with the separate paragraph at start and end paragraph at end
        return separate_para + '\n'.join(placeholder_paragraphs) + end_para

    # Replace the pattern
    modified_content = re.sub(separate_end_pattern, replace_with_placeholders, xml_content, flags=re.DOTALL)

    return modified_content


def main():
    parser = argparse.ArgumentParser(
        description='Add placeholder entries to Table of Contents in a DOCX file (in-place)'
    )
    parser.add_argument('docx_file', help='DOCX file to modify (will be replaced)')
    parser.add_argument(
        '--entries',
        help='JSON string with placeholder entries: [{"level":1,"text":"Chapter 1","page":"1"}]'
    )

    args = parser.parse_args()

    # Parse entries if provided
    entries = None
    if args.entries:
        try:
            entries = json.loads(args.entries)
        except json.JSONDecodeError as e:
            print(f"Error parsing entries JSON: {e}", file=sys.stderr)
            sys.exit(1)

    # Add placeholders
    try:
        add_toc_placeholders(args.docx_file, entries)
        print(f"Successfully added TOC placeholders to {args.docx_file}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
