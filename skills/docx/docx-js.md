# DOCX Library Tutorial

Generate .docx files with JavaScript/TypeScript.

**Important: Read this entire document before starting.** Critical formatting rules and common pitfalls are covered throughout - skipping sections may result in corrupted files or rendering issues.

## Setup
Assumes docx is already installed globally
If not installed: first try  `bun add docx`, then `npm install -g docx`
```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, Media, 
        Header, Footer, AlignmentType, PageOrientation, LevelFormat, ExternalHyperlink, 
        InternalHyperlink, TableOfContents, HeadingLevel, BorderStyle, WidthType, TabStopType, 
        TabStopPosition, UnderlineType, ShadingType, VerticalAlign, SymbolRun, PageNumber,
        FootnoteReferenceRun, Footnote, PageBreak } = require('docx');

// Create & Save
const doc = new Document({ sections: [{ children: [/* content */] }] });
Packer.toBuffer(doc).then(buffer => fs.writeFileSync("doc.docx", buffer)); // Node.js
Packer.toBlob(doc).then(blob => { /* download logic */ }); // Browser
```

## Delivery Standard

**Generic styling and mediocre aesthetics = mediocre delivery.**

Deliver studio-quality Word documents with deep thought on content, functionality, and styling. Users often don't explicitly request advanced features (covers, TOC, backgrounds, back covers, footnotes, charts)—deeply understand needs and proactively extend. 

The following formatting standards are to be strictly applied without exception:

- Line Spacing: The entire document must use 1.3x line spacing.
- Chart/Figure Placement: All charts, graphs, and figures must be explicitly centered horizontally on the page.

```javascript
new Table({
  alignment: AlignmentType.CENTER, 
  rows: [
    new TableRow({
      children: [
        new TableCell({
          children: [
            new Paragraph({
              text: "centered text",
              alignment: AlignmentType.CENTER, 
            }),
          ],
          verticalAlign: VerticalAlign.CENTER, 
          shading: { fill: colors.tableBg },
          borders: cellBorders,
        }),
      ],
    }),
  ],
});
```

- The text in charts must have left/right/up/bottom margin. 
- Image Handling：Preserve aspect ratio**: Never adjust image aspect ratio. Must insert according to the original ratio.
- Do not use background shading to all table section headers.

Compliance with these specifications is mandatory.

## Language Consistency

**Document language = User conversation language** (including filename, body text, headings, headers, TOC hints, chart labels, and all other text).

## Headers and Footers - REQUIRED BY DEFAULT

Most documents **MUST** include headers and footers. The specific style (alignment, format, content) should match the document's overall design.

- **Header**: Typically document title, company name, or chapter name
- **Footer**: Typically page numbers (format flexible: "X / Y", "Page X", "— X —", etc.)
- **Cover/Back cover**: Use `TitlePage` setting to hide header/footer on first page

## Fonts
If the user do not require specific fonts, you must follow the fonts rule belowing:
### For Chinese:
| Element | Font Family | Font Size (Half-points) | Properties |
| :--- | :--- | :--- | :--- |
| Normal Body | Microsoft YaHei (微软雅黑) | 21 (10.5pt / 五号) | Standard for readability. |
| Heading 1 | SimHei (黑体) | 32 (16pt / 三号) | Bold, high impact. |
| Heading 2 | SimHei (黑体) | 28 (14pt / 四号) | Bold. |
| Caption | Microsoft YaHei | 20 (10pt) | For tables and charts. | 

 - Microsoft YaHei, located at /usr/share/fonts/truetype/chinese/msyh.ttf  
 - SimHei, located at /usr/share/fonts/truetype/chinese/SimHei.ttf
 - Code blocks: SarasaMonoSC, located at /usr/share/fonts/truetype/chinese/SarasaMonoSC-Regular.ttf
 - Formulas / symbols: DejaVuSans, located at /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf
 - For body text and formulas, use Paragraph instead of Preformatted.


### For English
| Element | Font Family | Font Size (Half-points) | Properties |
| :--- | :--- | :--- | :--- |
| Normal Body | Calibri | 22 (11pt) | Highly legible; slightly larger than 10.5pt to match visual "weight." |
| Heading 1 | Times New Roman | 36 (18pt) | Bold, Serif; provides a clear "Newspaper" style hierarchy. |
| Heading 2 | Times New Roman | 28 (14pt) | Bold; classic and professional. |
| Caption | Calibri | 18 (9pt) | Clean and compact for metadata and notes. |

- Times New Roman, located at /usr/share/fonts/truetype/english/Times-New-Roman.ttf
- Calibri,located at /usr/share/fonts/truetype/english/calibri-regular.ttf

## Spacing & Paragraph Alignment
Task: Apply the following formatting rules to the provided text for a professional bilingual (Chinese/English) layout.
### Paragraph & Indentation:
Chinese Body: First-line indent of 2 characters (420 twips).
English Body: No first-line indent; use block format (space between paragraphs).
Alignment: Justified (Both) for all body text; Centered for Titles and Table Headers.
### Line & Paragraph Spacing（keep in mind）
Line Spacing: Set to 1.3 (250 twips) lines for both languages. 
Heading 1: 600 twips before, 300 twips after.
### Mixed-Language Kerning:
Insert a standard half-width space between Chinese characters and English words/numbers (e.g., "共 20 个 items").
### Punctuation:
Use full-width punctuation for Chinese text and half-width punctuation for English text.

## Professional Elements (Critical)

Produce documents that surpass user expectations by proactively incorporating high-end design elements without being prompted. Quality Benchmark: Visual excellence reflecting the standards of a top-tier designer in 2025.

**Cover & Visual:**
 - Double-Sided Branding: All formal documents (proposals, reports, contracts, bids) and creative assets (invitations, greeting cards) must include both a standalone front and back cover.
 - Internal Accents: Body pages may include subtle background elements to enhance the overall aesthetic depth.

**Structure:**
- Navigation: For any document with three or more sections, include a Table of Contents (TOC) immediately followed by a "refresh hint."

**Data Presentation:**
- Visual Priority: Use professional charts to illustrate trends or comparisons rather than plain text lists.
- Table Aesthetics: Apply light gray headers or the "three-line" professional style; strictly avoid the default Word blue.

**Links & References:**
- Interactive Links: All URLs must be formatted as clickable, active hyperlinks.
- Cross-Referencing: Number all figures and tables systematically (e.g., "see Figure 1") and use internal cross-references.
- Academic/Legal Rigor: For research or data-heavy documents, implement clickable in-text citations paired with accurate footnotes or endnotes.

### TOC Refresh Hint

Because Word TOCs utilize field codes, page numbers may become unaligned during generation. You must append the following gray hint text after the TOC to guide the user:
  Note: This Table of Contents is generated via field codes. To ensure page number accuracy after editing, please right-click the TOC and select "Update Field."

### Outline Adherence

- **User provides outline**: Follow strictly, no additions, deletions, or reordering
- **No outline provided**: Use standard structure
  - Academic: Introduction → Literature Review → Methodology → Results → Discussion → Conclusion.
  - Business: Executive Summary → Analysis → Recommendations.
  - Technical: Overview → Principles → Implementation → Examples → FAQ.

### Scene Completeness

Anticipate the functional requirements of the specific scenario. Examples include, but are not limited to:
- **Exam paper** → Include name/class/ID fields, point allocations for every question, and a dedicated grading table.
- **Contract** → Provide signature and seal blocks for all parties, date placeholders, contract ID numbers, and an attachment list.
- **Meeting minutes** → List attendees and absentees, define action items with assigned owners, and note the next meeting time.

## Design Philosophy

### Color Scheme

**Low saturation tones**, avoid Word default blue and matplotlib default high saturation.

**Flexibly choose** color schemes based on document scenario:

| Style | Palette | Suitable Scenarios |
|-------|---------|-------------------|
| Morandi | Soft muted tones | Arts, editorial, lifestyle |
| Earth tones | Brown, olive, natural | Environmental, organic industries |
| Nordic | Cool gray, misty blue | Minimalism, technology, software |
| Japanese Wabi-sabi | Gray, raw wood, zen | Traditional, contemplative, crafts |
| French elegance | Off-white, dusty pink | Luxury, fashion, high-end retail |
| Industrial | Charcoal, rust, concrete | Manufacturing, engineering, construction |
| Academic | Navy, burgundy, ivory | Research, education, legal |
| Ocean mist | Misty blue, sand | Marine, wellness, travel |
| Forest moss | Olive, moss green | Nature, sustainability, forestry |
| Desert dusk | Ochre, sandy gold | Warmth, regional, historical |

**Color scheme must be consistent within the same document.**

### highlighting 
Use low saturation color schemes for font highlighting.

### Layout

White space (margins, paragraph spacing), clear hierarchy (H1 > H2 > body), proper padding (text shouldn't touch borders).

### Pagination Control

Word uses flow layout, not fixed pages.

### Alignment and Typography (keep in mind!!!)
CJK body: justify + 2-char indent. English: left. Table numbers: right. Headings: no indent.
For both languages, Must use a line spacing of 1.3x (250 twips). Do not use single line spacing !!!

### Table Formatting（Very inportant）
- A caption must be added immediately after the table, keep in mind! 
- The entire table must be centered horizontally on the page. keep in mind!
#### Cell Formatting (Inside the Table)
Left/Right Cell Margin: Set to at least 120-200 twips (approximately the width of one character).
Up/Down Cell Margin: Set to at least 100 twips
Text Alignment(must follow !!!):
- Horizontal Alignment: Center-aligned. This creates a clean vertical axis through the table column.
- Vertical Alignment: Center-aligned. Text must be positioned exactly in the middle of the cell's height to prevent it from "floating" too close to the top or bottom borders.
- Cell Margins (Padding):
Left/Right: Set to 120–200 twips (approx. 0.2–0.35 cm). This ensures text does not touch the borders, maintaining legibility.
Top/Bottom: Set to at least 60–100 twips to provide a consistent vertical buffer around the text.


### Page break
There must be page break between cover page and the content, between table of content and the content also, should NOT put cover page and content in a single page.

## Page Layout & Margins (A4 Standard)
The layout uses a 1440 twip (1 inch) margin for content, with specialized margins for the cover.

| Section       | Top Margin | Bottom/Left/Right | Twips Calculation                         |
|---------------|------------|-------------------|-------------------------------------------|
| Cover Page    | 0          | 0                 | For edge-to-edge background images.       |
| Main Content  | 1800       | 1440              | Extra top space for the header.           |
| **Twips Unit** | **1 inch = 1440 twips** | **A4 Width = 11906** | **A4 Height = 16838** |

## Text & Formatting
```javascript
// IMPORTANT: Never use \n for line breaks - always use separate Paragraph elements
// ❌ WRONG: new TextRun("Line 1\nLine 2")
// ✅ CORRECT: new Paragraph({ children: [new TextRun("Line 1")] }), new Paragraph({ children: [new TextRun("Line 2")] })

// First-line indent for body paragraphs
// IMPORTANT: Chinese documents typically use 2-character indent (about 480 DXA for 12pt SimSun)
new Paragraph({
  indent: { firstLine: 480 }, // 2-character first-line indent for Chinese body text
  children: [new TextRun({ text: "This is the main text (Chinese). The first line is indented by two characters.", font: "SimSun" })]
})

// Basic text with all formatting options
new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 200, after: 200 },
  indent: { left: 720, right: 720, firstLine: 480 }, // Can combine with left/right indent
  children: [
    new TextRun({ text: "Bold", bold: true }),
    new TextRun({ text: "Italic", italics: true }),
    new TextRun({ text: "Underlined", underline: { type: UnderlineType.DOUBLE, color: "FF0000" } }),
    new TextRun({ text: "Colored", color: "FF0000", size: 28, font: "Times New Roman" }), // Times New Roman (system font)
    new TextRun({ text: "Highlighted", highlight: "yellow" }),
    new TextRun({ text: "Strikethrough", strike: true }),
    new TextRun({ text: "x2", superScript: true }),
    new TextRun({ text: "H2O", subScript: true }),
    new TextRun({ text: "SMALL CAPS", smallCaps: true }),
    new SymbolRun({ char: "2022", font: "Symbol" }), // Bullet •
    new SymbolRun({ char: "00A9", font: "Arial" })   // Copyright © - Arial for symbols
  ]
})
```

## Styles & Professional Formatting

```javascript
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Times New Roman", size: 24 } } }, // 12pt default (system font)
    paragraphStyles: [
      // Document title style - override built-in Title style
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: 56, bold: true, color: "000000", font: "Times New Roman" },
        paragraph: { spacing: { before: 240, after: 120 }, alignment: AlignmentType.CENTER } },
      // IMPORTANT: Override built-in heading styles by using their exact IDs
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: "000000", font: "Times New Roman" }, // 16pt
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } }, // outlineLevel enables TOC generation if needed
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: "000000", font: "Times New Roman" }, // 14pt
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } },
      // Custom styles use your own IDs
      { id: "myStyle", name: "My Style", basedOn: "Normal",
        run: { size: 28, bold: true, color: "000000" },
        paragraph: { spacing: { after: 120 }, alignment: AlignmentType.CENTER } }
    ],
    characterStyles: [{ id: "myCharStyle", name: "My Char Style",
      run: { color: "FF0000", bold: true, underline: { type: UnderlineType.SINGLE } } }]
  },
  sections: [{
    properties: { page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children: [
      new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("Document Title")] }), // Uses overridden Title style
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Heading 1")] }), // Uses overridden Heading1 style
      new Paragraph({ style: "myStyle", children: [new TextRun("Custom paragraph style")] }),
      new Paragraph({ children: [
        new TextRun("Normal with "),
        new TextRun({ text: "custom char style", style: "myCharStyle" })
      ]})
    ]
  }]
});
```

**Font Management Strategy (CRITICAL):**

**ALWAYS prioritize system-installed fonts** for reliability, performance, and cross-platform compatibility:

1. **System fonts FIRST** (no download, immediate availability):
   - English: **Times New Roman** (professional standard)
   - Chinese: **SimSun/宋体** (formal document standard)
   - Universal fallbacks: Arial, Calibri, Helvetica

2. **Avoid custom font downloads** unless absolutely necessary for specific branding
3. **Test font availability** before deployment

**Professional Font Combinations (System Fonts Only):**
- **Times New Roman (Headers) + Times New Roman (Body)** - Classic, professional, universally supported
- **Arial (Headers) + Arial (Body)** - Clean, modern, universally supported
- **Times New Roman (Headers) + Arial (Body)** - Classic serif headers with modern body

**Chinese Document Font Guidelines (System Fonts):**
- **Body text**: Use **SimSun/宋体** - the standard system font for Chinese formal documents
- **Headings**: Use **SimHei/黑体** - bold sans-serif for visual hierarchy
- **Default size**: 12pt (size: 24) for body, 14-16pt for headings
- **CRITICAL**: SimSun for body text, SimHei ONLY for headings - never use SimHei for entire document

```javascript
// English document style configuration (Times New Roman)
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Times New Roman", size: 24 } } }, // 12pt for body
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Times New Roman" }, // 16pt for H1
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Times New Roman" }, // 14pt for H2
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } }
    ]
  }
});

// Chinese document style configuration (SimSun/SimHei)
const doc = new Document({
  styles: {
    default: { document: { run: { font: "SimSun", size: 24 } } }, // SimSun 12pt for body
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "SimHei" }, // SimHei 16pt for H1
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "SimHei" }, // SimHei 14pt for H2
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } }
    ]
  }
});
```

**Key Styling Principles:**
- **ALWAYS use system-installed fonts** (Times New Roman for English, SimSun for Chinese)
- **Override built-in styles**: Use exact IDs like "Heading1", "Heading2", "Heading3" to override Word's built-in heading styles
- **HeadingLevel constants**: `HeadingLevel.HEADING_1` uses "Heading1" style, `HeadingLevel.HEADING_2` uses "Heading2" style, etc.
- **outlineLevel**: Set `outlineLevel: 0` for H1, `outlineLevel: 1` for H2, etc. (optional, only needed if TOC will be added)
- **Use custom styles** instead of inline formatting for consistency
- **Set a default font** using `styles.default.document.run.font` - Times New Roman for English, SimSun for Chinese
- **Establish visual hierarchy** with different font sizes (titles > headers > body)
- **Add proper spacing** with `before` and `after` paragraph spacing
- **Use colors sparingly**: Default to black (000000) and shades of gray for titles and headings (heading 1, heading 2, etc.)
- **Set consistent margins** (1440 = 1 inch is standard)


## Lists (ALWAYS USE PROPER LISTS - NEVER USE UNICODE BULLETS)

### ⚠️ CRITICAL: Numbered List References - Read This Before Creating Lists!

**Each independently numbered list MUST use a UNIQUE reference name**

**Rules**:
- Same `reference` = continues numbering (1,2,3 → 4,5,6)
- Different `reference` = restarts at 1 (1,2,3 → 1,2,3)

**When to use a new reference?**
- ✓ Numbered lists under new headings/sections
- ✓ Any list that needs independent numbering
- ✗ Subsequent items of the same list (keep using same reference)

**Reference naming suggestions**:
- `list-section-1`, `list-section-2`, `list-section-3`
- `list-chapter-1`, `list-chapter-2`
- `list-requirements`, `list-constraints` (name based on content)

```javascript
// ❌ WRONG: All lists use the same reference
numbering: {
  config: [
    { reference: "my-list", levels: [...] }  // Only one config
  ]
}
// Result:
// Chapter 1
//   1. Item A
//   2. Item B
// Chapter 2
//   3. Item C    ← WRONG! Should start from 1
//   4. Item D

// ✅ CORRECT: Each list uses different reference
numbering: {
  config: [
    { reference: "list-chapter-1", levels: [...] },
    { reference: "list-chapter-2", levels: [...] },
    { reference: "list-chapter-3", levels: [...] }
  ]
}
// Result:
// Chapter 1
//   1. Item A
//   2. Item B
// Chapter 2
//   1. Item C    ✓ CORRECT! Restarts from 1
//   2. Item D
// Chapter 3
//   1. Item E    ✓ CORRECT! Restarts from 1
//   2. Item F
```

### Basic List Syntax

```javascript
// Bullets - ALWAYS use the numbering config, NOT unicode symbols
// CRITICAL: Use LevelFormat.BULLET constant, NOT the string "bullet"
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullet-list",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "first-numbered-list",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "second-numbered-list", // Different reference = restarts at 1
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
    ]
  },
  sections: [{
    children: [
      // Bullet list items
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun("First bullet point")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun("Second bullet point")] }),
      // Numbered list items
      new Paragraph({ numbering: { reference: "first-numbered-list", level: 0 },
        children: [new TextRun("First numbered item")] }),
      new Paragraph({ numbering: { reference: "first-numbered-list", level: 0 },
        children: [new TextRun("Second numbered item")] }),
      // ⚠️ CRITICAL: Different reference = INDEPENDENT list that restarts at 1
      // Same reference = CONTINUES previous numbering
      new Paragraph({ numbering: { reference: "second-numbered-list", level: 0 },
        children: [new TextRun("Starts at 1 again (because different reference)")] })
    ]
  }]
});

// ⚠️ CRITICAL: NEVER use unicode bullets - they create fake lists that don't work properly
// new TextRun("• Item")           // WRONG
// new SymbolRun({ char: "2022" }) // WRONG
// ✅ ALWAYS use numbering config with LevelFormat.BULLET for real Word lists
```

## Tables
```javascript
// Complete table with margins, borders, headers, and bullet points
const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };

new Table({
  columnWidths: [4680, 4680], // ⚠️ CRITICAL: Set column widths at table level - values in DXA (twentieths of a point)
  // ⚠️ MANDATORY: margins MUST be set to prevent text touching borders
  margins: { top: 100, bottom: 100, left: 180, right: 180 }, // Minimum comfortable padding
  rows: [
    new TableRow({
      tableHeader: true,
      children: [
        new TableCell({
          borders: cellBorders,
          width: { size: 4680, type: WidthType.DXA }, // ALSO set width on each cell
          // ⚠️ CRITICAL: Always use ShadingType.CLEAR to prevent black backgrounds in Word.
          shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, 
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ 
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Header", bold: true, size: 22 })]
          })]
        }),
        new TableCell({
          borders: cellBorders,
          width: { size: 4680, type: WidthType.DXA }, // ALSO set width on each cell
          shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
          children: [new Paragraph({ 
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Bullet Points", bold: true, size: 22 })]
          })]
        })
      ]
    }),
    new TableRow({
      children: [
        new TableCell({
          borders: cellBorders,
          width: { size: 4680, type: WidthType.DXA }, // ALSO set width on each cell
          children: [new Paragraph({ children: [new TextRun("Regular data")] })]
        }),
        new TableCell({
          borders: cellBorders,
          width: { size: 4680, type: WidthType.DXA }, // ALSO set width on each cell
          children: [
            new Paragraph({ 
              numbering: { reference: "bullet-list", level: 0 },
              children: [new TextRun("First bullet point")] 
            }),
            new Paragraph({ 
              numbering: { reference: "bullet-list", level: 0 },
              children: [new TextRun("Second bullet point")] 
            })
          ]
        })
      ]
    })
  ]
})
```

**IMPORTANT: Table Width & Borders**
- Use BOTH `columnWidths: [width1, width2, ...]` array AND `width: { size: X, type: WidthType.DXA }` on each cell
- Values in DXA (twentieths of a point): 1440 = 1 inch, Letter usable width = 9360 DXA (with 1" margins)
- Apply borders to individual `TableCell` elements, NOT the `Table` itself

**Precomputed Column Widths (Letter size with 1" margins = 9360 DXA total):**
- **2 columns:** `columnWidths: [4680, 4680]` (equal width)
- **3 columns:** `columnWidths: [3120, 3120, 3120]` (equal width)

## Links & Navigation
```javascript
// TOC example
// new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
//
// CRITICAL: If adding TOC, use HeadingLevel only, NOT custom styles
// ❌ WRONG: new Paragraph({ heading: HeadingLevel.HEADING_1, style: "customHeader", children: [new TextRun("Title")] })
// ✅ CORRECT: new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Title")] })

// REQUIRED: After generating the DOCX, add TOC placeholders for first-open experience
// Always run: python skills/docx/scripts/add_toc_placeholders.py document.docx --entries '[...]'
// This adds placeholder entries that appear before the user updates the TOC (modifies file in-place)
// Extract headings from your document to generate accurate entries

// External link
new Paragraph({
  children: [new ExternalHyperlink({
    children: [new TextRun({ text: "Google", style: "Hyperlink" })],
    link: "https://www.google.com"
  })]
}),

// Internal link & bookmark
new Paragraph({
  children: [new InternalHyperlink({
    children: [new TextRun({ text: "Go to Section", style: "Hyperlink" })],
    anchor: "section1"
  })]
}),
new Paragraph({
  children: [new TextRun("Section Content")],
  bookmark: { id: "section1", name: "section1" }
}),

```

Use `new Paragraph({ children: [new PageBreak()] })` at the start of the next section to ensure TOC is isolated.

## Images & Media
```javascript
// Basic image with sizing & positioning
// CRITICAL: Always specify 'type' parameter - it's REQUIRED for ImageRun
new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new ImageRun({
    type: "png", // NEW REQUIREMENT: Must specify image type (png, jpg, jpeg, gif, bmp, svg)
    data: fs.readFileSync("image.png"),
    transformation: { width: 200, height: 150, rotation: 0 }, // rotation in degrees
    altText: { title: "Logo", description: "Company logo", name: "Name" } // IMPORTANT: All three fields are required
  })]
})
```

## Page Breaks
```javascript
// Manual page break
new Paragraph({ children: [new PageBreak()] }),

// Page break before paragraph
new Paragraph({
  pageBreakBefore: true,
  children: [new TextRun("This starts on a new page")]
})

// ⚠️ CRITICAL: NEVER use PageBreak standalone - it will create invalid XML that Word cannot open
// ❌ WRONG: new PageBreak() 
// ✅ CORRECT: new Paragraph({ children: [new PageBreak()] })
```

## Cover Page
**If the document has a cover page, the cover content should be centered both horizontally and vertically.**

**Important notes for cover pages:**
- **Horizontal centering**: Use `alignment: AlignmentType.CENTER` on all cover page paragraphs
- **Vertical centering**: Use `spacing: { before: XXXX }` on elements to visually center content (adjust based on page height)
- **Separate section**: Create a dedicated section for the cover page to separate it from main content
- **Page break**: Use `new Paragraph({ children: [new PageBreak()] })` at the start of the next section to ensure cover is isolated

## Headers/Footers & Page Setup
```javascript
const doc = new Document({
  sections: [{
    properties: {
      page: {
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }, // 1440 = 1 inch
        size: { orientation: PageOrientation.LANDSCAPE },
        pageNumbers: { start: 1, formatType: "decimal" } // "upperRoman", "lowerRoman", "upperLetter", "lowerLetter"
      }
    },
    headers: {
      default: new Header({ children: [new Paragraph({ 
        alignment: AlignmentType.RIGHT,
        children: [new TextRun("Header Text")]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ 
        alignment: AlignmentType.CENTER,
        children: [new TextRun("Page "), new TextRun({ children: [PageNumber.CURRENT] }), new TextRun(" of "), new TextRun({ children: [PageNumber.TOTAL_PAGES] })]
      })] })
    },
    children: [/* content */]
  }]
});
```

## Tabs
```javascript
new Paragraph({
  tabStops: [
    { type: TabStopType.LEFT, position: TabStopPosition.MAX / 4 },
    { type: TabStopType.CENTER, position: TabStopPosition.MAX / 2 },
    { type: TabStopType.RIGHT, position: TabStopPosition.MAX * 3 / 4 }
  ],
  children: [new TextRun("Left\tCenter\tRight")]
})
```

## Constants & Quick Reference
- **Underlines:** `SINGLE`, `DOUBLE`, `WAVY`, `DASH`
- **Borders:** `SINGLE`, `DOUBLE`, `DASHED`, `DOTTED`  
- **Numbering:** `DECIMAL` (1,2,3), `UPPER_ROMAN` (I,II,III), `LOWER_LETTER` (a,b,c)
- **Tabs:** `LEFT`, `CENTER`, `RIGHT`, `DECIMAL`
- **Symbols:** `"2022"` (•), `"00A9"` (©), `"00AE"` (®), `"2122"` (™), `"00B0"` (°), `"F070"` (✓), `"F0FC"` (✗)

## Critical Issues & Common Mistakes
- **CRITICAL for cover pages**: If the document has a cover page, the cover content should be centered both horizontally (AlignmentType.CENTER) and vertically (use spacing.before to adjust)
- **CRITICAL: PageBreak must ALWAYS be inside a Paragraph** - standalone PageBreak creates invalid XML that Word cannot open
- **ALWAYS use ShadingType.CLEAR for table cell shading** - Never use ShadingType.SOLID (causes black background).
- Measurements in DXA (1440 = 1 inch) | Each table cell needs ≥1 Paragraph | If TOC is added, it requires HeadingLevel styles only
- **CRITICAL: ALWAYS use system-installed fonts** - Times New Roman for English, SimSun for Chinese - NEVER download custom fonts unless absolutely necessary
- **ALWAYS use custom styles** with appropriate system fonts for professional appearance and proper visual hierarchy
- **ALWAYS set a default font** using `styles.default.document.run.font` - **Times New Roman** for English, **SimSun** for Chinese
- **CRITICAL for Chinese documents**: Use SimSun for body text, SimHei ONLY for headings - NEVER use SimHei for entire document
- **CRITICAL for Chinese body text**: Add first-line indent with `indent: { firstLine: 480 }` (approximately 2 characters for 12pt font)
- **ALWAYS use columnWidths array for tables** + individual cell widths for compatibility
- **NEVER use unicode symbols for bullets** - always use proper numbering configuration with `LevelFormat.BULLET` constant (NOT the string "bullet")
- **NEVER use \n for line breaks anywhere** - always use separate Paragraph elements for each line
- **ALWAYS use TextRun objects within Paragraph children** - never use text property directly on Paragraph
- **CRITICAL for images**: ImageRun REQUIRES `type` parameter - always specify "png", "jpg", "jpeg", "gif", "bmp", or "svg"
- **CRITICAL for bullets**: Must use `LevelFormat.BULLET` constant, not string "bullet", and include `text: "•"` for the bullet character
- **CRITICAL for numbering**: Each numbering reference creates an INDEPENDENT list. Same reference = continues numbering (1,2,3 then 4,5,6). Different reference = restarts at 1 (1,2,3 then 1,2,3). Use unique reference names for each separate numbered section!
- **CRITICAL for TOC**: When using TableOfContents, headings must use HeadingLevel ONLY - do NOT add custom styles to heading paragraphs or TOC will break.
- **CRITICAL for Tables**: Set `columnWidths` array + individual cell widths, apply borders to cells not table
- **MANDATORY for Tables**: ALWAYS set `margins` at Table level - this prevents text from touching borders and is required for professional quality. NEVER omit this property.
- **Set table margins at TABLE level** for consistent cell padding (avoids repetition per cell)