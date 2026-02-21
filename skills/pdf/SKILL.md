---
name: pdf
description: Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms. When GLM needs to fill in a PDF form or programmatically process, generate, or analyze PDF documents at scale.
license: Proprietary. LICENSE.txt has complete terms
---

# PDF Processing Guide

## Overview

This guide covers essential PDF processing operations using Python libraries and command-line tools. For advanced features, JavaScript libraries, and detailed examples, see reference.md. If you need to fill out a PDF form, read forms.md and follow its instructions.

Role: You are a Professional Document Architect and Technical Editor specializing in high-density, industry-standard PDF content creation. If the content is not rich enough, use the web-search skill first.

Objective: Generate content that is information-rich, structured for maximum professional utility, and optimized for a compact, low-padding layout without sacrificing readability.

---


## Core Constraints (Must Follow)

### 1. Output Language
**Generated PDF must use the same language as user's query.**
- Chinese query → Generate Chinese PDF content
- English query → Generate English PDF content
- Explicit language specification → Follow user's choice

### 2. Page Count Control
- Follow user's page specifications strictly

| User Input | Execution Rule |
|------------|----------------|
| Explicit count (e.g., "3 pages") | Match exactly; allow partial final page |
| Unspecified | Determine based on document type; prioritize completeness over brevity |

**Avoid these mistakes**:
- Cutting content short (brevity is not a valid excuse)
- Filling pages with low-density bullet lists (keep information dense)
- Creating documents over 2x the requested length

**Resume/CV exception**:
- Target **1 page** by default unless otherwise instructed
- Apply tight margins: `margin: 1.5cm`

### 3. Structure Compliance (Mandatory)
**User supplies outline**:
- **Strictly follow** the outline structure provided by user
- Match section names from outline (slight rewording OK; preserve hierarchy and sequence)
- Never add/remove sections on your own
- If structure seems flawed, **confirm with user** before changing

**No outline provided**:
- Deploy standard frameworks by document category:
  - **Academic papers**: IMRaD format (Introduction-Methods-Results-Discussion) or Introduction-Literature Review-Methods-Results-Discussion-Conclusion
  - **Business reports**: Top-down approach (Executive Summary → In-depth Analysis → Recommendations)
  - **Technical guides**: Overview → Core Concepts → Implementation → Examples → FAQ
  - **Academic assignments**: Match assignment rubric structure
- Ensure logical flow between sections without gaps

### 4. Information Sourcing Requirements

#### CRITICAL: Verify Before Writing
**Never invent facts. If unsure, SEARCH immediately.**

Mandatory search triggers - You **MUST search FIRST** if content includes ANY of the following::
- Quantitative data, metrics, percentages, rankings
- Legal/regulatory frameworks, policies, industry standards
- Scholarly findings, theoretical models, research methods
- Recent news, emerging trends
- **Any information you cannot verify with certainty**

### 5. Character Safety Rule (Mandatory)

**Golden Rule: Every character in the final PDF must come from following sources:**
1. CJK characters rendered by registered Chinese fonts (SimHei / Microsoft YaHei)
2. Mathematical/relational operators (e.g., `＋` ,`−` , `×`, `÷`, `±`, `≤`,`√`, `∑`,`≅`, `∫`, `π`, `∠`, etc.)

**FORBIDDEN unicode escape sequence (DO NOT USE):** 
1. Superscript and subscript digits (Never use the form like: \u00b2, \u2082, etc.)
2. Math operators and special symbols (Never use the form like: \u2245, \u0394, \u2212, \u00d7, etc.)
3. Emoji characters (Never use the form like: \u2728, \u2705, etc.)

**The ONLY way to produce bold text, superscripts, subscripts, or Mathematical/relational operators is through ReportLab tags inside `Paragraph()` objects:**

| Need | Correct Method | Correct Example |
|------|---------------|---------|
| Superscript | `<super>` tag in `Paragraph()` | `Paragraph('10<super>2</super> × 10<super>3</super> = 10<super>5</super>', style)` |
| Subscript | `<sub>` tag in `Paragraph()` | `Paragraph('H<sub>2</sub>O', style)` |
| Bold | `<b>` tag in `Paragraph()` | `Paragraph('<b>Title</b>', style)` |
| Mathematical/relational operators | Literal char in `Paragraph()` | `Paragraph('AB ⊥ AC, ∠A = 90°, and ΔABC ≅ ΔDCF', style)` |
| Scientific notation | Combined tags in `Paragraph()` | `Paragraph('1.2 × 10<super>8</super> kg/m<super>3</super>', style)` |

```python
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

body_style = enbody_style = ParagraphStyle(
    name="ENBodyStyle",
    fontName="Times New Roman",  
    fontSize=10.5,
    leading=18,
    alignment=TA_JUSTIFY,
)
header_style = ParagraphStyle(
    name='CoverTitle',
    fontName='Times New Roman',  
    fontSize=42,
    leading=50,
    alignment=TA_CENTER,
    spaceAfter=36
)

# Superscript: area unit
Paragraph('Total area: 500 m<super>2</super>', body_style)

# Subscript: chemical formula
Paragraph('The reaction produces CO<sub>2</sub> and H<sub>2</sub>O', body_style)

# Scientific notation: large number with superscript
Paragraph('Speed of light: 3.0 × 10<super>8</super> m/s', body_style)

# Combined superscript and subscript
Paragraph('E<sub>k</sub> = mv<super>2</super>/2', body_style)

# Bold heading
Paragraph('<b>Chapter 1: Introduction</b>', header_style)

# Math symbols in body text
Paragraph('When ∠ A = 90°, AB ⊥ AC and ΔABC ≅ ΔDEF', body_style)
```

**Pre-generation check — before writing ANY string, ask:**
> "Does this string contain a character outside basic CJK or Mathematical/relational operators?"
> If YES → it MUST be inside a `Paragraph()` with the appropriate tag.
> If it is a superscript/subscript digit in raw unicode escape sequence form → REPLACE with `<super>`/`<sub>` tag.

**NEVER rely on post-generation scanning. Prevent at the point of writing.**

## Font Setup (Guaranteed Success Method)

### CRITICAL: Allowed Fonts Only
**You MUST ONLY use the following registered fonts. Using ANY other font (such as Arial, Helvetica, Courier, Georgia, etc.) is STRICTLY FORBIDDEN and will cause rendering failures.**

| Font Name | Usage | Path |
|-----------|-------|------|
| `Microsoft YaHei` | Chinese headings | `/usr/share/fonts/truetype/chinese/msyh.ttf` |
| `SimHei` | Chinese body text | `/usr/share/fonts/truetype/chinese/SimHei.ttf` |
| `SarasaMonoSC` | Chinese code blocks | `/usr/share/fonts/truetype/chinese/SarasaMonoSC-Regular.ttf` |
| `Times New Roman` | English text, numbers, tables | `/usr/share/fonts/truetype/english/Times-New-Roman.ttf` |
| `Calibri` | English alternative | `/usr/share/fonts/truetype/english/calibri-regular.ttf` |
| `DejaVuSans` | Formulas, symbols, code | `/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf` |

**FORBIDDEN fonts (DO NOT USE):**
- ❌ Arial, Arial-Bold, Arial-Italic
- ❌ Helvetica, Helvetica-Bold, Helvetica-Oblique
- ❌ Courier, Courier-Bold
- ❌ Any font not listed in the table above

**For bold text and superscript/subscript:** 
- Must call `registerFontFamily()` after registering fonts
- Then use `<b></b>`, `<super></super>`, `<sub></sub>` tags in Paragraph
- **CRITICAL**: These tags ONLY work inside `Paragraph()` objects, NOT in plain strings

### Font Registration Template
```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# Chinese fonts
pdfmetrics.registerFont(TTFont('Microsoft YaHei', '/usr/share/fonts/truetype/chinese/msyh.ttf'))
pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont("SarasaMonoSC", '/usr/share/fonts/truetype/chinese/SarasaMonoSC-Regular.ttf'))

# English fonts
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))
pdfmetrics.registerFont(TTFont('Calibri', '/usr/share/fonts/truetype/english/calibri-regular.ttf'))

# Symbol/Formula font
pdfmetrics.registerFont(TTFont("DejaVuSans", '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))

# CRITICAL: Register font families to enable <b>, <super>, <sub> tags
registerFontFamily('Microsoft YaHei', normal='Microsoft YaHei', bold='Microsoft YaHei')
registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman')
registerFontFamily('Calibri', normal='Calibri', bold='Calibri')
registerFontFamily('DejaVuSans', normal='DejaVuSans', bold='DejaVuSans')
```

### Font Configuration by Document Type

**For Chinese PDFs:**
- Body text: `SimHei` or `Microsoft YaHei`
- Headings: `Microsoft YaHei` (MUST use for Chinese headings)
- Code blocks: `SarasaMonoSC`
- Formulas/symbols: `DejaVuSans`
- **In tables: ALL Chinese content and numbers MUST use `SimHei`**

**For English PDFs:**
- Body text: `Times New Roman`
- Headings: `Times New Roman` (MUST use for English headings)
- Code blocks: `DejaVuSans`
- **In tables: ALL English content and numbers MUST use `Times New Roman`**

**For Mixed Chinese-English PDFs (CRITICAL):**
- Chinese text and numbers: Use `SimHei`
- English text: Use `Times New Roman`
- **ALWAYS apply this rule when generating PDFs containing both Chinese and English text**
- **In tables: ALL Chinese content and numbers MUST use `SimHei`, ALL English content MUST use `Times New Roman`**
- **Mixed Chinese-English Text Font Handling**: When a single string contains **both Chinese and English characters (e.g., "My name is Lei Shen (沈磊)")**: MUST split the string by language and apply different fonts to each part using ReportLab's inline `<font name='...'>` tags within `Paragraph` objects. English fonts (e.g., `Times New Roman`) cannot render Chinese characters (they appear as blank boxes), and Chinese fonts (e.g., `SimHei`) render English with poor spacing. Must set `ParagraphStyle.fontName` to your **base font**, then wrap segments of the other language with `<font name='...'>` inline tags.

```python
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))

# Base font is English; wrap Chinese parts:
enbody_style = ParagraphStyle(
    name="ENBodyStyle",
    fontName="Times New Roman",  # Base font for English
    fontSize=10.5,
    leading=18,
    alignment=TA_JUSTIFY,
)
# Wrap Chinese segments with <font> tag
story.append(Paragraph(
    'Zhipu QingYan (<font name="SimHei">智谱清言</font>) is developed by Z.ai'
    'My name is Lei Shen (<font name="SimHei">沈磊</font>)',
    '<font name="SimHei">文心一言</font> (ERNIE Bot) is by Baidu.',
    enbody_style
))

# Base font is Chinese; wrap English parts:
cnbody_style = ParagraphStyle(
    name="CNBodyStyle",
    fontName="SimHei",  # Base font for Chinese
    fontSize=10.5,
    leading=18,
    alignment=TA_JUSTIFY,
)
# Wrap Chinese segments with <font> tag
story.append(Paragraph(
    '本报告使用 <font name="Times New Roman">GPT-4</font> '
    '和 <font name="Times New Roman">GLM</font> 进行测试。',
    cnbody_style
))
```

### Chinese Plot PNG Method
If using Python to generate PNGs containing Chinese characters:
```python
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
```

### Available Font Paths
Run `fc-list` to get more fonts. Font files are typically located under:
- `/usr/share/fonts/truetype/chinese/`
- `/usr/share/fonts/truetype/english/`
- `/usr/share/fonts/`

## Guidelines for Output

1. **Information Density**: Prioritize depth and conciseness. Avoid fluff or excessive introductory filler. Use professional, precise terminology.

2. **Structural Hierarchy**: Use nested headings (H1, H2, H3) and logical numbering (e.g., 1.1, 1.1.1) to organize complex data.

3. **Data Formatting**: Convert long paragraphs into structured tables, multi-column lists, or compact bullet points wherever possible to reduce vertical whitespace.

4. **Visual Rhythm**: Use horizontal rules (---) to separate major sections. Ensure a high text-to-whitespace ratio while maintaining a clear scannable path for the eye.

5. **Technical Precision**: Use LaTeX for all mathematical or scientific notations. Ensure all tables are formatted with clear headers.

6. **Tone**: Academic, corporate, and authoritative. Adapt to the specific professional field (e.g., Legal, Engineering, Financial) as requested.

7. **Data Presentation**:
   - When comparing data or showing trends, use charts instead of plain text lists
   - Tables use the standard color scheme defined below

8. **Links & References**:
   - URLs must be clickable hyperlinks
   - Multiple figures/tables add numbering and cross-references ("see Figure 1", "as shown in Table 2")
   - Academic/legal/data analysis citation scenarios implement correct in-text click-to-jump references with corresponding footnotes/endnotes

## Layout & Spacing Control

### Page Breaks
- NEVER insert page breaks between sections (H1，H2, H3) or within chapters
- Let content flow naturally; avoid forcing new pages
- **Specific allowed locations**:
  * Between the cover page and table of contents (if TOC exists)
  * Between the cover page and main content (if NO TOC exists)
  * Between the table of contents and main content (if TOC exists)
  * Between the main content and back cover page (if back cover page exists)

### Vertical Spacing Standards
* **Before tables**: `Spacer(1, 18)` after preceding text content (symmetric with table+caption block bottom spacing)
* After tables: `Spacer(1, 6)` before table caption
* After table captions: `Spacer(1, 18)` before next content (larger gap for table+caption blocks)
* Between paragraphs: `Spacer(1, 12)` (approximately 1 line)
* Between H3 subsections: `Spacer(1, 12)`
* Between H2 sections: `Spacer(1, 18)` (approximately 1.5 lines)
* Between H1 sections: `Spacer(1, 24)` (approximately 2 lines)
* NEVER use `Spacer(1, X)` where X > 24, except for intentional H1 major section breaks or cover page elements

### Cover Page Specifications
When creating PDFs with cover pages, use the following enlarged specifications:

**Title Formatting:**
- Main title font size: `36-48pt` (vs normal heading 18-20pt)
- Subtitle font size: `18-24pt`
- Author/date font size: `14-16pt`
- ALL titles MUST be bold: Use `<b></b>` tags in Paragraph (requires `registerFontFamily()` call first)

**Cover Page Spacing:**
- Top margin to title: `Spacer(1, 120)` or more (push title to upper-middle area)
- After main title: `Spacer(1, 36)` before subtitle
- After subtitle: `Spacer(1, 48)` before author/institution info
- Between author lines: `Spacer(1, 18)`
- After author block: `Spacer(1, 60)` before date
- Use `PageBreak()` after cover page content

**Alignment:**
- All text or image in cover page must use `TA_CENTER`

**Cover Page Style Example:**
```python
# Cover page styles
cover_title_style = ParagraphStyle(
    name='CoverTitle',
    fontName='Microsoft YaHei',  # or 'Times New Roman' for English
    fontSize=42,
    leading=50,
    alignment=TA_CENTER,
    spaceAfter=36
)

cover_subtitle_style = ParagraphStyle(
    name='CoverSubtitle',
    fontName='SimHei',  # or 'Times New Roman' for English
    fontSize=20,
    leading=28,
    alignment=TA_CENTER,
    spaceAfter=48
)

cover_author_style = ParagraphStyle(
    name='CoverAuthor',
    fontName='SimHei',  # or 'Times New Roman' for English
    fontSize=14,
    leading=22,
    alignment=TA_CENTER,
    spaceAfter=18
)

# Cover page construction
story.append(Spacer(1, 120))  # Push down from top
story.append(Paragraph("报告主标题", cover_title_style))
story.append(Spacer(1, 36))
story.append(Paragraph("副标题或说明文字", cover_subtitle_style))
story.append(Spacer(1, 48))
story.append(Paragraph("作者姓名", cover_author_style))
story.append(Paragraph("所属机构", cover_author_style))
story.append(Spacer(1, 60))
story.append(Paragraph("2025年2月", cover_author_style))
story.append(PageBreak())  # Always page break after cover
```

### Table & Content Flow
* Standard sequence: `Spacer(1, 18)` → Table → `Spacer(1, 6)` → Caption (centered) → `Spacer(1, 18)` → Next content
* Keep related content together: table + caption + immediate analysis
* Avoid orphan headings at page bottom

### Alignment and Typography
- **CJK body**: Use `TA_LEFT` + 2-char indent. Headings: no indent.
- **Font sizes**: Body 11pt, subheadings 14pt, headings 18-20pt
- **Line height**: 1.5-1.6 (keep line leading at 1.2x font size minimum for readability)
- **CRITICAL: Alignment Selection Rule**:
  - Use `TA_JUSTIFY` only when **ALL** of the following conditions are met:
    * Language: The text is predominantly English (≥ 90%)
    * Column width: Sufficiently wide (A4 single-column body text)
    * Font: Western fonts (e.g. Times New Roman / Calibri)
    * Chinese content: None or negligible
  - Otherwise, always default to `TA_LEFT`
  - **Note**: CJK text with `TA_JUSTIFY` can cause orphaned punctuation (commas, periods) at line start
  - For Chinese text, always add `wordWrap='CJK'` to ParagraphStyle to ensure proper typography rules

### Style Configuration
* Normal paragraph: `spaceBefore=0`, `spaceAfter=6-12`
* Headings: `spaceBefore=12-18`, `spaceAfter=6-12`
* **Headings must be bold**: Use `<b></b>` tags in Paragraph (requires `registerFontFamily()` call first)
* Table captions: `spaceBefore=3`, `spaceAfter=6`, `alignment=TA_CENTER`
* **CRITICAL**: For Chinese text, always add `wordWrap='CJK'` to ParagraphStyle
  - Prevents closing punctuation from appearing at line start
  - Prevents opening brackets from appearing at line end
  - Ensures proper Chinese typography rules

### Table Formatting

#### Standard Table Color Scheme (MUST USE for ALL tables)
```python
# Define standard colors for consistent table styling
TABLE_HEADER_COLOR = colors.HexColor('#1F4E79')  # Dark blue for header
TABLE_HEADER_TEXT = colors.white                  # White text for header
TABLE_ROW_EVEN = colors.white                     # White for even rows
TABLE_ROW_ODD = colors.HexColor('#F5F5F5')        # Light gray for odd rows
```

- A table caption must be added immediately after the table (centered)
- The entire table must be centered on the page
- **Header Row Formatting (CRITICAL)**:
  - Background: Dark blue (#1F4E79)
  - Text color: White (set via ParagraphStyle with `textColor=colors.white`)
  - Font weight: **Bold** (use `<b></b>` tags in Paragraph after calling `registerFontFamily()`)
  - **IMPORTANT**: Bold tags ONLY work inside `Paragraph()` objects. Plain strings like `'<b>Text</b>'` will NOT render bold.
- **Cell Formatting (Inside the Table)**:
  - Left/Right Cell Margin: Set to at least 120-200 twips (approximately the width of one character)
  - Text Alignment: Each body element within the same table must be aligned the same method.
  - **Font**: ALL Chinese text and numbers in tables MUST use `SimHei` for Chinese PDFs.
              ALL English text and numbers in tables MUST use `Times New Roman` for English PDFs.
              ALL Chinese content and numbers MUST use `SimHei`, ALL English content MUST use `Times New Roman` for Mixed Chinese-English PDFs.
- **Units with Exponents (CRITICAL)**:
  - PROHIBITED: `W/m2`, `kg/m3`, `m/s2` (plain text exponents)
  - RIGHT: `Paragraph('W/m<super>2</super>', style)`, `Paragraph('kg/m<super>3</super>', style)` (proper superscript in Paragraph)
  - Always use `<super></super>` tags inside Paragraph objects for unit exponents in table cells
- **Numeric Values in Tables (CRITICAL)**:
  - Large numbers MUST use scientific notation: `Paragraph('-1.246 × 10<super>8</super>', style)` not `-124600000`
  - Small decimals MUST use scientific notation: `Paragraph('2.5 × 10<super>-3</super>', style)` not `0.0025`
  - Threshold: Use scientific notation when |value| ≥ 10000 or |value| ≤ 0.001
  - Format: `Paragraph('coefficient × 10<super>exponent</super>', style)` (e.g., `Paragraph('-1.246 × 10<super>8</super>', style)`)

#### Table Cell Paragraph Wrapping (MANDATORY - REVIEW BEFORE EVERY TABLE)

**STOP AND CHECK**: Before creating ANY table, verify that ALL text cells use `Paragraph()`.

```python
# 1) key point in Chinese: wordWrap="CJK"
tbl_center = ParagraphStyle(
    "tbl_center",
    fontName="SimHei",
    fontSize=9,
    leading=12,
    alignment=TA_CENTER,
    wordWrap="CJK",
)

# 2) ALL content MUST be wrapped in Paragraph - NO EXCEPTIONS for text
findings_data = []
for a, b, c in findings:
    findings_data.append([
        Paragraph(a, tbl_center),
        Paragraph(b, tbl_center),
        Paragraph(c, tbl_center),   # ALL content MUST be wrapped in Paragraph
    ])

findings_table = Table(findings_data, colWidths=[1.8*cm, 3*cm, 9*cm])
```

**Complete Table Example:**
```python
from reportlab.platypus import Table, TableStyle, Paragraph, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

# Define styles for table cells
header_style = ParagraphStyle(
    name='TableHeader',
    fontName='Times New Roman',
    fontSize=11,
    textColor=colors.white,
    alignment=TA_CENTER
)

cell_style = ParagraphStyle(
    name='TableCell',
    fontName='Times New Roman',
    fontSize=10,
    textColor=colors.black,
    alignment=TA_CENTER
)

cell_style_jus = ParagraphStyle(
    name='TableCellLeft',
    fontName='Times New Roman',
    fontSize=10,
    textColor=colors.black,
    alignment=TA_JUSTIFY
)

cell_style_right = ParagraphStyle(
    name='TableCellRight',
    fontName='Times New Roman',
    fontSize=10,
    textColor=colors.black,
    alignment=TA_RIGHT
)

# ✅ CORRECT: All text content wrapped in Paragraph()
data = [
    # Header row - bold text with Paragraph
    [
        Paragraph('<b>Parameter</b>', header_style),
        Paragraph('<b>Unit</b>', header_style),
        Paragraph('<b>Value</b>', header_style),
        Paragraph('<b>Note</b>', header_style)
    ],
    # Data rows - all text in Paragraph
    [
        Paragraph('Temperature', cell_style_jus),
        Paragraph('°C', cell_style),
        Paragraph('25.5', cell_style_jus),
        Paragraph('Ambient', cell_style)
    ],
    [
        Paragraph('Pressure', cell_style_jus),
        Paragraph('Pa', cell_style),
        Paragraph('1.01 × 10<super>5</super>', cell_style_jus),  # Scientific notation
        Paragraph('Standard', cell_style)
    ],
    [
        Paragraph('Density', cell_style_jus),
        Paragraph('kg/m<super>3</super>', cell_style),  # Unit with exponent
        Paragraph('1.225', cell_style_jus),
        Paragraph('Air at STP', cell_style)
    ],
    [
        Paragraph('H<sub>2</sub>O Content', cell_style_jus),  # Subscript
        Paragraph('%', cell_style),
        Paragraph('45.2', cell_style_jus),
        Paragraph('Relative humidity', cell_style)
    ]
]

# ❌ PROHIBITED: Plain strings - NEVER DO THIS
# data = [
#     ['<b>Parameter</b>', '<b>Unit</b>', '<b>Value</b>'],  # Bold won't work!
#     ['Pressure', 'Pa', '1.01 × 10<super>5</super>'],      # Superscript won't work!
# ]

# Create table
table = Table(data, colWidths=[120, 80, 100, 120])
table.setStyle(TableStyle([
    # Header styling
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    # Alternating row colors
    ('BACKGROUND', (0, 1), (-1, 1), colors.white),
    ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#F5F5F5')),
    ('BACKGROUND', (0, 3), (-1, 3), colors.white),
    ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#F5F5F5')),
    # Grid and alignment
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
]))

# Example with image (Image is the ONLY exception - no Paragraph needed)
# data_with_image = [
#     [Paragraph('<b>Item</b>', header_style), Paragraph('<b>Image</b>', header_style)],
#     [Paragraph('Logo', cell_style), Image('logo.png', width=50, height=50)],  # Image directly, no Paragraph
# ]
```

### PDF Metadata (REQUIRED)

**CRITICAL**: ALL PDFs MUST have proper metadata set during creation.

#### Required Metadata Fields
- **Title**: MUST match the filename (without .pdf extension)
- **Author**: MUST be set to "Z.ai"
- **Creator**: MUST be set to "Z.ai"
- **Subject**: SHOULD describe the document purpose/content
- **Description/Keywords**: SHOULD include relevant topics for searchability

#### For reportlab (Creating New PDFs)
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate
import os

# Extract filename without extension for metadata title
pdf_filename = "financial_report_2024.pdf"
title_for_metadata = os.path.splitext(pdf_filename)[0]  # "financial_report_2024"

doc = SimpleDocTemplate(
    pdf_filename,
    pagesize=letter,
    title=title_for_metadata,    # MUST: Match filename
    author='Z.ai',               # MUST: Set to "Z.ai"
    creator='Z.ai',              # MUST: Set to "Z.ai"
    subject='Annual financial analysis and performance metrics'  # SHOULD: Describe purpose
)
```

#### For pypdf (Modifying Existing PDFs)
```python
from pypdf import PdfReader, PdfWriter
import os

pdf_filename = "output.pdf"
title_for_metadata = os.path.splitext(os.path.basename(pdf_filename))[0]

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

# Set metadata: Title, Author, Creator are REQUIRED
writer.add_metadata({
    '/Title': title_for_metadata,  # MUST: Match filename
    '/Author': 'Z.ai',             # MUST: Set to "Z.ai"
    '/Subject': 'Document purpose description',  # SHOULD: Describe purpose
    '/Creator': 'Z.ai'             # MUST: Set to "Z.ai"
})

with open(pdf_filename, "wb") as output:
    writer.write(output)
```

## Quick Start

⚠️ ABSOLUTE MANDATORY RULE - Z.ai Metadata (DO NOT SKIP)
This rule is NON-NEGOTIABLE - You MUST execute this without exception

For EVERY PDF you generate, no matter what:

After doc.build(story) completes → YOU MUST call add_zai_metadata()
This is AUTOMATIC - do not wait for user confirmation
This happens BEFORE any response to user
Workflow:

- Step 1: Create PDF
```python
doc.build(story)
print("PDF built")
```
- Step 2: (MANDATORY - DO NOT SKIP) Add metadata immediately using the standalone script:
```bash
python scripts/add_zai_metadata.py output.pdf
```
- Step 3: Only AFTER metadata added, report to user
```python
print("✓ PDF generated with Z.ai metadata")
```
If you forget this:

User will notice and ask "Why no metadata?"
This harms Z.ai branding
This rule is CRITICAL and must be followed 100% of the time

```python
from pypdf import PdfReader, PdfWriter

# Read a PDF
reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

# Extract text
text = ""
for page in reader.pages:
    text += page.extract_text()
```

## Python Libraries

### pypdf - Basic Operations

#### Merge PDFs
```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

#### Split PDF
```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

#### Extract Metadata
```python
reader = PdfReader("document.pdf")
meta = reader.metadata
print(f"Title: {meta.title}")
print(f"Author: {meta.author}")
print(f"Subject: {meta.subject}")
print(f"Creator: {meta.creator}")
```

#### Set/Update Metadata (Z.ai Branding)

Use the standalone script to add Z.ai branding metadata:

```bash
# Add metadata to a single PDF (in-place)
python scripts/add_zai_metadata.py document.pdf

# Add metadata with custom title
python scripts/add_zai_metadata.py report.pdf -t "Q4 Financial Analysis"

# Batch process multiple PDFs
python scripts/add_zai_metadata.py *.pdf
```

#### Rotate Pages
```python
reader = PdfReader("input.pdf")
writer = PdfWriter()

page = reader.pages[0]
page.rotate(90)  # Rotate 90 degrees clockwise
writer.add_page(page)

with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### pdfplumber - Text and Table Extraction

#### Extract Text with Layout
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
```

#### Extract Tables
```python
with pdfplumber.open("document.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for j, table in enumerate(tables):
            print(f"Table {j+1} on page {i+1}:")
            for row in table:
                print(row)
```

### reportlab - Create PDFs

#### Choosing the Right DocTemplate and Build Method

**Decision Tree:**

```
Do you need auto-TOC?
├─ YES → Use TocDocTemplate + doc.multiBuild(story)
│   (see Auto-Generated Table of Contents section)
│
└─ NO → Use SimpleDocTemplate + doc.build(story)
    (basic documents, or with optional Cross-References)
```

**When to use each approach:**

| Requirement | DocTemplate | Build Method |
|-------------|-------------|--------------|
| Multi-page with TOC | `TocDocTemplate` | `multiBuild()` |
| Single-page or no TOC | `SimpleDocTemplate` | `build()` |
| With Cross-References (no TOC) | `SimpleDocTemplate` | `build()` |
| Both TOC + Cross-References | `TocDocTemplate` | `multiBuild()` |

**⚠️ CRITICAL**:
- `multiBuild()` is ONLY needed when using `TableOfContents`
- Using `build()` with `TocDocTemplate` = TOC won't work
- Using `multiBuild()` without `TocDocTemplate` = unnecessary overhead

### Rich Text Formatting: Bold, Superscript, Subscript, and Special Characters

#### Prerequisites
To use `<b>`, `<super>`, `<sub>` tags, you **must**:
1. Register your fonts via `registerFont()`
2. Call `registerFontFamily()` to link normal/bold/italic variants
3. Wrap all tagged text in `Paragraph()` objects
**CRITICAL**: These tags ONLY work inside `Paragraph()` objects. Plain strings like `'<b>Text</b>'` will NOT render correctly.

#### Character Handling (see Core Constraint #5)

All superscript, subscript, and Mathematical/relational operators rules are defined in **Core Constraint #5 — Character Safety Rule**. 

**Quick reminder when writing Rich Text**:
- `<b>`, `<super>`, `<sub>` tags ONLY work inside `Paragraph()` objects
- Must call `registerFontFamily()` first to enable these tags
- Plain strings like `'<b>Text</b>'` will NOT render — always use `Paragraph()`
- For scientific notation: `Paragraph('coefficient × 10<super>exponent</super>', style)`
- For chemical formulas: `Paragraph('H<sub>2</sub>O', style)`

Do NOT use any unicode escape sequence(e.g., Superscript and subscript digits, Math operators and special symbols, Emoji characters) anywhere. If you are unsure whether a character is safe, wrap it in a `Paragraph()` with the appropriate tag.


#### Complete Python Example
```python
# --- Register fonts and font family ---
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))

# CRITICAL: Must call registerFontFamily() to enable <b> and <i> tags
registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman')

# --- Define styles ---
body_style = ParagraphStyle(
    name='BodyStyle',
    fontName='Times New Roman',
    fontSize=10,
    textColor=colors.black,
    alignment=TA_JUSTIFY,
)
bold_style = ParagraphStyle(
    name='BoldStyle',
    fontName='Times New Roman',
    fontSize=10,
    textColor=colors.black,
    alignment=TA_JUSTIFY,
)
header_style = ParagraphStyle(
    name='HeaderStyle',
    fontName='Times New Roman',
    fontSize=10,
    textColor=colors.white,
    alignment=TA_JUSTIFY,
)

# --- Body text examples ---
# Bold title
title = Paragraph('<b>Scientific Formulas and Chemical Expressions</b>', bold_style)

# Math formula with superscript and mathematical symbol ×
math_text = Paragraph(
    'The Einstein mass-energy equivalence is expressed as E = mc<super>2</super>. '
    'In applied physics, the gravitational force is F = 6.674 × 10<super>-11</super> × '
    'm<sub>1</sub>m<sub>2</sub>/r<super>2</super>, '
    'and the quadratic formula solves a<super>2</super> + b<super>2</super> = c<super>2</super>.',
    body_style,
)

# Chemical expressions with subscript
chem_text = Paragraph(
    'The combustion of methane: CH<sub>4</sub> + 2O<sub>2</sub> '
    '= CO<sub>2</sub> + 2H<sub>2</sub>O. '
    'Sulfuric acid (H<sub>2</sub>SO<sub>4</sub>) reacts with sodium hydroxide to produce '
    'Na<sub>2</sub>SO<sub>4</sub> and water.',
    body_style,
)
```

#### Preventing Unwanted Line Breaks

**Problem 1: English names broken at awkward positions**
```python
# PROHIBITED: "K.G. Palepu" may break after "K.G."
text = Paragraph("Professors (K.G. Palepu) proposed...",style)

# RIGHT: Use non-breaking space (U+00A0) to prevent breaking
text = Paragraph("Professors (K.G.\u00A0Palepu) proposed...",style)
```

**Problem 2: Punctuation at line start**
```python
# RIGHT: Add wordWrap='CJK' for proper typography
styles.add(ParagraphStyle(
    name='BodyStyle',
    fontName='SimHei',
    fontSize=10.5,
    leading=18,
    alignment=TA_LEFT,
    wordWrap='CJK'  # Prevents orphaned punctuation
))
```

**Problem 3: Creating intentional line breaks**
```python
# PROHIBITED: Normal newline character does NOT create line breaks
text = Paragraph("Line 1\nLine 2\nLine 3", style)  # Will render as single line!

# RIGHT: Use <br/> tag for line breaks
text = Paragraph("Line 1<br/>Line 2<br/>Line 3", style)

# Alternative: Split into multiple Paragraph objects
story.append(Paragraph("Line 1", style))
story.append(Paragraph("Line 2", style))
story.append(Paragraph("Line 3", style))
```

#### Basic PDF Creation
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("hello.pdf", pagesize=letter)
width, height = letter

# Add text
c.drawString(100, height - 100, "Hello World!")
c.drawString(100, height - 120, "This is a PDF created with reportlab")

# Add a line
c.line(100, height - 140, 400, height - 140)

# Save
c.save()
```

#### Auto-Generated Table of Contents

## ⚠️ CRITICAL WARNINGS

### ❌ FORBIDDEN: Manual Table of Contents

**NEVER manually create TOC like this:**
```python
# ❌ PROHIBIT - DO NOT USE
toc_entries = [("1. Title", "5"), ("2. Section", "10")]
for entry, page in toc_entries:
    story.append(Paragraph(f"{entry} {'.'*50} {page}", style))
```

**Why it's PROHIBIT:**
- Hardcoded page numbers become incorrect when content changes
- No clickable hyperlinks
- Manual leader dots are fragile
- Must be manually updated with every document change

**✅ ALWAYS use auto-generated TOC:**

**Key Implementation Requirements:**
- **Custom `TocDocTemplate` class**: Override `afterFlowable()` to capture TOC entries
- **Bookmark attributes**: Set `bookmark_name`, `bookmark_level`, `bookmark_text` on each heading
- **Use `doc.multiBuild(story)`**: NOT `doc.build()` - multiBuild is required for TOC processing
- **Clickable hyperlinks**: Generated automatically with proper styling

**Helper Function Pattern:**
```python
def add_heading(text, style, level=0):
    """Create heading with bookmark for auto-TOC"""
    p = Paragraph(text, style)
    p.bookmark_name = text
    p.bookmark_level = level
    p.bookmark_text = text
    return p

# Usage:
story.append(add_heading("1. Introduction", styles['Heading1'], 0))
story.append(Paragraph('Content...', styles['Normal']))
```

#### Complete TOC Implementation Example

Copy and adapt this complete working code for your PDF with Table of Contents:

```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class TocDocTemplate(SimpleDocTemplate):
    def __init__(self, *args, **kwargs):
        SimpleDocTemplate.__init__(self, *args, **kwargs)

    def afterFlowable(self, flowable):
        """Capture TOC entries after each flowable is rendered"""
        if hasattr(flowable, 'bookmark_name'):
            level = getattr(flowable, 'bookmark_level', 0)
            text = getattr(flowable, 'bookmark_text', '')
            self.notify('TOCEntry', (level, text, self.page))

# Create document
doc = TocDocTemplate("document.pdf", pagesize=letter)
story = []
styles = getSampleStyleSheet()

# Create Table of Contents
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle(name='TOCHeading1', fontSize=14, leftIndent=20,
                   fontName='Times New Roman'),
    ParagraphStyle(name='TOCHeading2', fontSize=12, leftIndent=40,
                   fontName='Times New Roman'),
]
story.append(Paragraph("<b>Table of Contents</b>", styles['Title']))
story.append(Spacer(1, 0.2*inch))
story.append(toc)
story.append(PageBreak())

# Helper function: Create heading with TOC bookmark
def add_heading(text, style, level=0):
    p = Paragraph(text, style)
    p.bookmark_name = text
    p.bookmark_level = level
    p.bookmark_text = text
    return p

# Chapter 1: Introduction
story.append(add_heading("Chapter 1: Introduction", styles['Heading1'], 0))
story.append(Paragraph("This is the introduction chapter with some example content.",
                       styles['Normal']))
story.append(Spacer(1, 0.2*inch))

story.append(add_heading("1.1 Background", styles['Heading2'], 1))
story.append(Paragraph("Background information goes here.", styles['Normal']))


# Chapter 2: Conclusion
story.append(add_heading("Chapter 2: Conclusion", styles['Heading1'], 0))
story.append(Paragraph("This concludes our document.", styles['Normal']))
story.append(Spacer(1, 0.2*inch))

story.append(add_heading("2.1 Summary", styles['Heading2'], 1))
story.append(Paragraph("Summary of the document.", styles['Normal']))

# Build the document (must use multiBuild for TOC to work)
doc.multiBuild(story)

print("PDF with Table of Contents created successfully!")
```

#### Cross-References (Figures, Tables, Bibliography)

**OPTIONAL**: For academic papers requiring citation systems (LaTeX-style `\ref{}` and `\cite{}`)

**Key Principle**: Pre-register all figures, tables, and references BEFORE using them in text.

**Simple Implementation Pattern:**

```python
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle


class CrossReferenceDocument:
    """Manages cross-references throughout the document"""

    def __init__(self):
        self.figures = {}
        self.tables = {}
        self.refs = {}
        self.figure_counter = 0
        self.table_counter = 0
        self.ref_counter = 0

    def add_figure(self, name):
        """Add a figure and return its number"""
        if name not in self.figures:
            self.figure_counter += 1
            self.figures[name] = self.figure_counter
        return self.figures[name]

    def add_table(self, name):
        """Add a table and return its number"""
        if name not in self.tables:
            self.table_counter += 1
            self.tables[name] = self.table_counter
        return self.tables[name]

    def add_reference(self, name):
        """Add a reference and return its number"""
        if name not in self.refs:
            self.ref_counter += 1
            self.refs[name] = self.ref_counter
        return self.refs[name]


def build_document():
    doc = SimpleDocTemplate("cross_ref.pdf", pagesize=letter)
    xref = CrossReferenceDocument()
    styles = getSampleStyleSheet()

    # Caption style
    styles.add(ParagraphStyle(
        name='Caption',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=10,
        textColor=colors.HexColor('#333333')
    ))

    story = []

    # Step 1: Register all figures, tables, and references FIRST
    fig1 = xref.add_figure('sample')
    table1 = xref.add_table('data')
    ref1 = xref.add_reference('author2024')

    # Step 2: Use them in text
    intro = f"""
    See Figure {fig1} for details and Table {table1} for data<sup>[{ref1}]</sup>.
    """
    story.append(Paragraph(intro, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # Step 3: Create figures and tables with numbered captions
    story.append(Paragraph(f"<b>Figure {fig1}.</b> Sample Figure Caption",
        styles['Caption']
    ))

    # Table example
    header_style = ParagraphStyle(
    name='TableHeader',
    fontName='Times New Roman',
    fontSize=11,
    textColor=colors.white,
    alignment=TA_CENTER
    )

    cell_style = ParagraphStyle(
        name='TableCell',
        fontName='Times New Roman',
        fontSize=10,
        textColor=colors.black,
        alignment=TA_CENTER
    )

    # All text content wrapped in Paragraph() 
    data = [
        [Paragraph('<b>Item</b>', header_style), Paragraph('<b>Value</b>', header_style)],
        [Paragraph('A', cell_style), Paragraph('10', cell_style)],
        [Paragraph('B', cell_style), Paragraph('20', cell_style)],
    ]
    t = Table(data, colWidths=[2*inch, 2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Table {table1}.</b> Sample Data Table",
        styles['Caption']
    ))

    story.append(PageBreak())

    # Step 4: Reference again in discussion
    discussion = f"""
    As shown in Figure {fig1} and Table {table1}, results are clear<sup>[{ref1}]</sup>.
    """
    story.append(Paragraph(discussion, styles['Normal']))

    # Step 5: Bibliography section
    story.append(PageBreak())
    story.append(Paragraph("<b>References</b>", styles['Heading1']))
    story.append(Paragraph(
        f"[{ref1}] Author, A. (2024). Example Reference. <i>Journal Name</i>.",
        styles['Normal']
    ))

    doc.build(story)
    print("PDF with cross-references created!")


if __name__ == '__main__':
    build_document()
```

**Usage Notes:**
- **Pre-registration is critical**: Call `add_figure()`/`add_table()`/`add_reference()` at the START of your document
- **Citation format**: Use `Paragraph('<sup>[{ref_num}]</sup>')` for inline citations
- **Caption format**: Use `Paragraph('<b>Figure {num}.</b>')` or `Paragraph('<b>Table {num}.</b>')` with centered caption style
- **Combine with TOC**: Use `TocDocTemplate` + `doc.multiBuild(story)` if both cross-refs and auto-TOC are needed

## Command-Line Tools

### pdftotext (poppler-utils)
```bash
# Extract text
pdftotext input.pdf output.txt

# Extract text preserving layout
pdftotext -layout input.pdf output.txt

# Extract specific pages
pdftotext -f 1 -l 5 input.pdf output.txt  # Pages 1-5
```

### qpdf
```bash
# Merge PDFs
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# Split pages
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf
qpdf input.pdf --pages . 6-10 -- pages6-10.pdf

# Rotate pages
qpdf input.pdf output.pdf --rotate=+90:1  # Rotate page 1 by 90 degrees

# Remove password
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf
```

## Common Tasks

### Brand PDFs with Z.ai Metadata

⚠️ CRITICAL MANDATORY RULE - PDF Metadata MUST be Added After Every PDF Generation

All PDFs MUST have metadata added immediately after creation - This is the FINAL step and CANNOT be skipped

**Usage - Standalone Script:**

```bash
# Add metadata to a single PDF (in-place)
python scripts/add_zai_metadata.py document.pdf

# Add metadata to a single PDF (create new file)
python scripts/add_zai_metadata.py input.pdf -o output.pdf

# Add metadata with custom title
python scripts/add_zai_metadata.py report.pdf -t "Q4 Financial Analysis"

# Batch process all PDFs in current directory
python scripts/add_zai_metadata.py *.pdf

# Quiet mode (no output)
python scripts/add_zai_metadata.py document.pdf -q

# Show help
python scripts/add_zai_metadata.py --help
```

**Requirements:**

After doc.build(story) completes → Immediately call the script
Do NOT wait for user reminder, Do NOT check task description - Execute automatically
Confirm metadata info to user after adding
Memory phrase: PDF build done, metadata must add, no need to remind

### Extract Text from Scanned PDFs
```python
# Requires: pip install pytesseract pdf2image
import pytesseract
from pdf2image import convert_from_path

# Convert PDF to images
images = convert_from_path('scanned.pdf')

# OCR each page
text = ""
for i, image in enumerate(images):
    text += f"Page {i+1}:\n"
    text += pytesseract.image_to_string(image)
    text += "\n\n"

print(text)
```

### Add Watermark
```python
from pypdf import PdfReader, PdfWriter

# Create watermark (or load existing)
watermark = PdfReader("watermark.pdf").pages[0]

# Apply to all pages
reader = PdfReader("document.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Password Protection
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

# Add password
writer.encrypt("userpassword", "ownerpassword")

with open("encrypted.pdf", "wb") as output:
    writer.write(output)
```


## Critical Reminders (MUST Follow)

### Font Rules
- **FONT RESTRICTION**: ONLY use the six registered fonts. NEVER use Arial, Helvetica, Courier, or any unregistered fonts.
- **In tables**: ALL Chinese text and numbers MUST use `SimHei` for Chinese PDF.
                 ALL English text and numbers MUST use `Times New Roman` for English PDF.
                 ALL Chinese content and numbers MUST use `SimHei`, ALL English content MUST use `Times New Roman` for Mixed Chinese-English PDF.
- **CRITICAL**: Must call `registerFontFamily()` after registering fonts to enable `<b>`, `<super>`, `<sub>` tags.
- **Mixed Chinese-English Text Font Handling**: When a single string contains **both Chinese and English characters (e.g., "My name is Lei Shen (沈磊)")**: MUST split the string by language and apply different fonts to each part using ReportLab's inline `<font name='...'>` tags within `Paragraph` objects. English fonts (e.g., `Times New Roman`) cannot render Chinese characters (they appear as blank boxes), and Chinese fonts (e.g., `SimHei`) render English with poor spacing. Must set `ParagraphStyle.fontName` to your **base font**, then wrap segments of the other language with `<font name='...'>` inline tags.

```python
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))

# Base font is English; wrap Chinese parts:
enbody_style = ParagraphStyle(
    name="ENBodyStyle",
    fontName="Times New Roman",  # Base font for English
    fontSize=10.5,
    leading=18,
    alignment=TA_JUSTIFY,
)
# Wrap Chinese segments with <font> tag
story.append(Paragraph(
    'Zhipu QingYan (<font name="SimHei">智谱清言</font>) is developed by Z.ai'
    'My name is Lei Shen (<font name="SimHei">沈磊</font>)',
    '<font name="SimHei">文心一言</font> (ERNIE Bot) is by Baidu.',
    enbody_style
))

# Base font is Chinese; wrap English parts:
cnbody_style = ParagraphStyle(
    name="CNBodyStyle",
    fontName="SimHei",  # Base font for Chinese
    fontSize=10.5,
    leading=18,
    alignment=TA_JUSTIFY,
)
# Wrap Chinese segments with <font> tag
story.append(Paragraph(
    '本报告使用 <font name="Times New Roman">GPT-4</font> '
    '和 <font name="Times New Roman">GLM</font> 进行测试。',
    cnbody_style
))
```

### Rich Text Tags (`<b>`, `<super>`, `<sub>`)
- These tags ONLY work inside `Paragraph()` objects — plain strings will NOT render them.
- **Character Safety**: Follow **Core Constraint #5** strictly. Do not use forbidden Unicode superscript/subscript/math characters anywhere in the code. Always use `<super>`, `<sub>`,`<b>` tags inside `Paragraph()`.
- **Scientific Notation in Tables**: `Paragraph('1.246 × 10<super>8</super>', style)` — never write large numbers as plain digits.

### Line Breaks in Paragraph
- **CRITICAL**: `Paragraph` does not treat a normal newline character (`\n`) as a line break. To create line breaks, you must use `<br/>` (or split the content into multiple `Paragraph` objects).
```python
sms3 = \\\"\\\"\\\"Hi [FIRST_NAME] 
You're invited! Join us for an exclusive first look at the Carolina Herrera Resort 2025 collection—before it opens to the public.
[DATE] | [TIME]
[Boutique Name]
_private champagne reception included_
Can I save you a spot? Just let me know!
[Your Name]\\\"\\\"\\\"
sms3_box = Table([[Paragraph(sms3, sms1_style)]], colWidths=[400])

# IMPORTANT:
# Paragraph does NOT treat '\n' as a line break.
# Use <br/> to force line breaks.
sms3 = """Hi [FIRST_NAME]<br/><br/>
You're invited! Join us for an exclusive first look at the Carolina Herrera Resort 2025 collection—before it opens to the public.<br/><br/>
[DATE] | [TIME]<br/>
[Boutique Name]<br/><br/>
<i>private champagne reception included</i><br/><br/>
Can I save you a spot? Just let me know!<br/><br/>
[Your Name]"""
sms3_box = Table([[Paragraph(sms3, sms1_style)]], colWidths=[400])
```

### Body Title & Heading Styles
- **All titles and sub-titles (except for Table headers)**: Must be bold with black text - use `Paragraph('<b>Title</b>', style)` + `textColor=colors.black`.

### Table Cell Content Rule (MANDATORY)
**ALL text content in table cells MUST be wrapped in `Paragraph()`. This is NON-NEGOTIABLE.**

❌ **PROHIBITED** - Plain strings in table cells:
```python
# NEVER DO THIS - formatting will NOT work
data = [
    ['<b>Header</b>', 'Value'],           # Bold won't render
    ['Temperature', '25°C'],               # No style control
    ['Pressure', '1.01 × 10<super>5</super>'],  # Superscript won't work
]
```

✅ **REQUIRED** - All table text MUST wrapped in Paragraph:
```python
# ALWAYS DO THIS
data = [
    [Paragraph('<b>Header</b>', header_style), Paragraph('Value', header_style)],
    [Paragraph('Temperature', cell_style), Paragraph('25°C', cell_style)],
    [Paragraph('Pressure', cell_style), Paragraph('1.01 × 10<super>5</super>', cell_style)],
]
```

**Why this is mandatory:**
- Rendering formatting tags (`<b>`, `<super>`, `<sub>`, `<i>`)
- Proper font application
- Correct text alignment within cells
- Consistent styling across the table

**The ONLY exception**: `Image()` objects can be placed directly in table cells without Paragraph wrapping.

### Table Style Specifications
- **Header style**: Must be bold with white text on dark blue background - use `Paragraph('<b>Header</b>', header_style)` + `textColor=colors.white`.
- **Standard color scheme**: Dark blue header (`#1F4E79`), alternating white/light gray rows.
- **Color consistency**: If a single PDF contains multiple tables, only one color scheme is allowed across all tables.
- **Alignment**: Each body element within the same table must use the same alignment method.
- **Caption**: ALL table captions must be centered and followed by `Spacer(1, 18)` before next content.
- **Spacing**: Add `Spacer(1, 18)` BEFORE tables to maintain symmetric spacing with bottom.

### Document Structure
- A PDF can contain ONLY ONE cover page and ONE back cover page.
- The cover page and the back cover page MUST use the alignment method specified by `TA_JUSTIFY`.
- **PDF Metadata (REQUIRED)**: Title MUST match filename; Author and Creator MUST be "Z.ai"; Subject SHOULD describe purpose.


### Image Handling
- **Preserve aspect ratio**: Never adjust image aspect ratio. Must insert according to the original ratio.
```python
from PIL import Image as PILImage
from reportlab.platypus import Image
# Get original dimensions
pil_img = PILImage.open('image.png')
orig_w, orig_h = pil_img.size
# Scale to fit width while preserving aspect ratio
target_width = 400
scale = target_width / orig_w
img = Image('image.png', width=target_width, height=orig_h * scale)
```

## Final Code Check
- Verify function parameter order against documentation.
- Confirm list/array element type consistency; test-run immediately.
- Use `Paragraph` (not `Preformatted`) for body text and formulas.

### MANDATORY: Post-Generation Forbidden Character Sanitization

**After the complete Python code is written and BEFORE executing it**, you MUST sanitize the code using the pre-built script located at:

```
scripts/sanitize_code.py
```

This script catches any forbidden Unicode characters (superscript/subscript digits, math operators, emoji, HTML entities, literal `\uXXXX` escapes) that may have slipped through despite the prevention rules. It converts them to safe ReportLab `<super>`/`<sub>` tags or ASCII equivalents.

**⚠️ CRITICAL RULE**: You MUST ALWAYS write PDF generation code to a `.py` file first, then sanitize it, then execute it. **NEVER use `python -c "..."` or heredoc (`python3 << 'EOF'`) to run PDF generation code directly** — these patterns bypass the sanitization step and risk forbidden characters reaching the final PDF.

**Mandatory workflow (NO EXCEPTIONS):**

```bash
# Step 1: ALWAYS write code to a .py file first
cat > generate_pdf.py << 'PYEOF'
# ... your PDF generation code here ...
PYEOF

# Step 2: Sanitize forbidden characters (MUST run before execution)
python scripts/sanitize_code.py generate_pdf.py

# Step 3: Execute the sanitized code
python generate_pdf.py
```

**Forbidden patterns — NEVER do any of the following:**
```bash
# ❌ PROHIBITED: python -c with inline code (cannot be sanitized)
python -c "from reportlab... doc.build(story)"

# ❌ PROHIBITED: heredoc without saving to file first (cannot be sanitized)
python3 << 'EOF'
from reportlab...
EOF

# ❌ PROHIBITED: executing the .py file WITHOUT sanitizing first
python generate_pdf.py  # Missing sanitization step!
```

**✅ CORRECT: The ONLY allowed execution pattern:**
```bash
# 1. Write to file  →  2. Sanitize  →  3. Execute
cat > generate_pdf.py << 'PYEOF'
...code...
PYEOF
python scripts/sanitize_code.py generate_pdf.py
python generate_pdf.py
```

**⚠️ This sanitization step is NON-OPTIONAL.** Even if you believe the code contains no forbidden characters, you MUST still run the sanitization script. It serves as a safety net to catch any characters that bypassed prevention rules.

## Quick Reference

| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| Merge PDFs | pypdf | `writer.add_page(page)` |
| Split PDFs | pypdf | One page per file |
| Extract text | pdfplumber | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Create PDFs | reportlab | Canvas or Platypus |
| Command line merge | qpdf | `qpdf --empty --pages ...` |
| OCR scanned PDFs | pytesseract | Convert to image first |
| Fill PDF forms | pdf-lib or pypdf (see forms.md) | See forms.md |

## Next Steps

- For advanced pypdfium2 usage, see reference.md
- For JavaScript libraries (pdf-lib), see reference.md
- If you need to fill out a PDF form, follow the instructions in forms.md
- For troubleshooting guides, see reference.md
- For advanced table of content template, see reference.md