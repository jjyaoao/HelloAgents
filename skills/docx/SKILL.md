---
name: docx
description: "Comprehensive document creation, editing, and analysis with support for tracked changes, comments, formatting preservation, and text extraction. When GLM needs to work with professional documents (.docx files) for: (1) Creating new documents, (2) Modifying or editing content, (3) Working with tracked changes, (4) Adding comments, or any other document tasks"
license: Proprietary. LICENSE.txt has complete terms
---

# DOCX creation, editing, and analysis

## Overview

A user may ask you to create, edit, or analyze the contents of a .docx file. A .docx file is essentially a ZIP archive containing XML files and other resources that you can read or edit. You have different tools and workflows available for different tasks.

# Design requiremnet

Deliver studio-quality Word documents with deep thought on content, functionality, and styling. Users often don't explicitly request advanced features (covers, TOC, backgrounds, back covers, footnotes, charts)—deeply understand needs and proactively extend. The document must have  1.3x line spacing and have charts centered horizontally.
## Available color（choose one）
- "Ink & Zen" Color Palette (Wabi-Sabi Style)
The design uses a grayscale "Ink" palette to differentiate from standard business blue/morandi styles.
Primary (Titles)：#0B1220  
Body Text：#0F172A   
Secondary (Subtitles)：#2B2B2B   
Accent (UI / Decor)：#9AA6B2  
Table Header / Subtle Background：#F1F5F9 

- Wilderness Oasis": Sage & Deep Forest   
Primary (Titles): #1A1F16 (Deep Forest Ink)  
Body Text: #2D3329 (Dark Moss Gray)  
Secondary (Subtitles): #4A5548 (Neutral Olive)  
Accent (UI/Decor): #94A3B8 (Steady Silver)   
Table/Background: #F8FAF7 (Ultra-Pale Mint White)  

- "Terra Cotta Afterglow": Warm Clay & Greige
Commonly utilized by top-tier consulting firms and architectural studios, this scheme warms up the gray scale to create a tactile sensation similar to premium cashmere.   
Primary (Titles): #26211F (Deep Charcoal Espresso)    
Body Text: #3D3735 (Dark Umber Gray)   
Secondary (Subtitles): #6B6361 (Warm Greige)    
Accent (UI/Decor): #C19A6B (Terra Cotta Gold / Muted Ochre)    
Table/Background: #FDFCFB (Off-White / Paper Texture)

- "Midnight Code": High-Contrast Slate & Silver
Ideal for cutting-edge technology, AI ventures, or digital transformation projects. This palette carries a slight "electric" undertone that provides superior visual penetration.   
Primary (Titles): #020617 (Midnight Black)   
Body Text: #1E293B (Deep Slate Blue)   
Secondary (Subtitles): #64748B (Cool Blue-Gray)    
Accent (UI/Decor): #94A3B8 (Steady Silver)   
Table/Background: #F8FAFC (Glacial Blue-White)  

### Chinese plot PNG method**
If using Python to generate PNGs containing Chinese characters, note that Matplotlib defaults to the DejaVu Sans font which lacks Chinese support; since the environment already has the SimHei font installed, you should set it as the default by configuring:

matplotlib.font_manager.fontManager.addfont('/usr/share/fonts/truetype/chinese/SimHei.ttf')  
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False




## Specialized Element Styling
- Table Borders: Use a "Single" line style with a size of 12 and the Primary Ink color. Internal vertical borders should be set to Nil (invisible) to create a clean, modern horizontal-only look.
- **CRITICAL: Table Cell Margins** - ALL tables MUST set `margins` property at the Table level to prevent text from touching borders. This is mandatory for professional document quality.

### Alignment and Typography
CJK body: justify + 2-char indent. English: left. Table numbers: right. Headings: no indent.
For both languages, Must use a line spacing of 1.3x (250 twips). Do not use single line spacing !!!

### CRITICAL: Chinese Quotes in JavaScript/TypeScript Code
**MANDATORY**: When writing JavaScript/TypeScript code for docx-js, ALL Chinese quotation marks (""", ''') inside strings MUST be escaped as Unicode escape sequences:
- Left double quote "\u201c" (")
- Right double quote "\u201d" (")
- Left single quote "\u2018" (')
- Right single quote "\u2019" (')

**Example - INCORRECT (will cause syntax error):**
```javascript
new TextRun({
  text: "他说"你好""  // ERROR: Chinese quotes break JS syntax
})
```

**Example - CORRECT:**
```javascript
new TextRun({
  text: "他说\u201c你好\u201d"  // Correct: escaped Unicode
})
```

**Alternative - Use template literals:**
```javascript
new TextRun({
  text: `他说"你好"`  // Also works: template literals allow Chinese quotes
})
```

## Workflow Decision Tree

### Reading/Analyzing Content
Use "Text extraction" or "Raw XML access" sections below.

### Creating New Document
Use "Creating a new Word document" workflow.

### Editing Existing Document
- **Your own document + simple changes**
  Use "Basic OOXML editing" workflow

- **Someone else's document**
  Use **"Redlining workflow"** (recommended default)

- **Legal, academic, business, or government docs**
  Use **"Redlining workflow"** (required)

## Reading and analyzing content

**Note**: For .doc (legacy format), first convert with `libreoffice --convert-to docx file.doc`.

### Text extraction
If you just need to read the text contents of a document, you should convert the document to markdown using pandoc. Pandoc provides excellent support for preserving document structure and can show tracked changes:

```bash
# Convert document to markdown with tracked changes
pandoc --track-changes=all path-to-file.docx -o output.md
# Options: --track-changes=accept/reject/all
```

### Raw XML access
You need raw XML access for: comments, complex formatting, document structure, embedded media, and metadata. For any of these features, you'll need to unpack a document and read its raw XML contents.

#### Unpacking a file
`python ooxml/scripts/unpack.py <office_file> <output_directory>`

#### Key file structures
* `word/document.xml` - Main document contents
* `word/comments.xml` - Comments referenced in document.xml
* `word/media/` - Embedded images and media files
* Tracked changes use `<w:ins>` (insertions) and `<w:del>` (deletions) tags

## Creating a new Word document

When creating a new Word document from scratch, use **docx-js**, but use bun instead of node to implement it. which allows you to create Word documents using JavaScript/TypeScript.

### Workflow
1. **MANDATORY - READ ENTIRE FILE**: Read [`docx-js.md`](docx-js.md) (~560 lines) completely from start to finish. **NEVER set any range limits when reading this file.** Read the full file content for detailed syntax, critical formatting rules, and best practices before proceeding with document creation.
2. Create a JavaScript/TypeScript file using Document, Paragraph, TextRun components (You can assume all dependencies are installed, but if not, refer to the dependencies section below)
3. Export as .docx using Packer.toBuffer()

### TOC (Table of Contents)
**If the document has more than three sections, generate a table of contents.**

**Implementation**: Use docx-js `TableOfContents` component to create a live TOC that auto-populates from document headings.

**CRITICAL**: For TOC to work correctly:
- All document headings MUST use `HeadingLevel` (e.g., `HeadingLevel.HEADING_1`)
- Do NOT add custom styles to heading paragraphs
- Place TOC before the actual heading content so it can scan them

**Hint requirement**: A hint paragraph MUST be added immediately after the TOC component with these specifications:
- **Position**: Immediately after the TOC component
- **Alignment**: Center-aligned
- **Color**: Gray (e.g., "999999")
- **Font size**: 18 (9pt)
- **Language**: Matches user conversation language
- **Text content**: Inform the user to right-click the TOC and select "Update Field" to show correct page numbers

### TOC Placeholders (Required Post-Processing)

**REQUIRED**: After generating the DOCX file, you MUST add placeholder TOC entries that appear on first open (before the user updates the TOC). This prevents showing an empty TOC initially.

**Implementation**: Always run the `add_toc_placeholders.py` script after generating the DOCX file:

```bash
python skills/docx/scripts/add_toc_placeholders.py document.docx \
  --entries '[{"level":1,"text":"Chapter 1 Overview","page":"1"},{"level":2,"text":"Section 1.1 Details","page":"1"}]'
```

**Note**: The script supports up to 3 TOC levels for placeholder entries.

**Entry format**:
- `level`: Heading level (1, 2, or 3)
- `text`: The heading text
- `page`: Estimated page number (will be corrected when TOC is updated)

**Auto-generating entries**:
You can extract the actual headings from the document structure to generate accurate entries. Match the heading text and hierarchy from your document content.

**Benefits**:
- Users see TOC content immediately on first open
- Placeholders are automatically replaced when user updates the TOC
- Improves perceived document quality and user experience

### Document Formatting Rules

**Page Break Restrictions**
Page breaks are ONLY allowed in these specific locations:
- Between cover page and table of contents (if TOC exists)
- Between cover page and main content (if NO TOC exists)
- Between table of contents and main content (if TOC exists)

**All content after the table of contents must flow continuously WITHOUT page breaks.**

**Text and Paragraph Rules**
- Complete sentences before starting a new line — do not break sentences across lines
- Use single, consistent style for each complete sentence
- Only start a new paragraph when the current paragraph is logically complete

**List and Bullet Point Formatting**
- Use left-aligned formatting (NOT justified alignment)
- Insert a line break after each list item
- Never place multiple items on the same line (justification stretches text)

## Editing an existing Word document

**Note**: For .doc (legacy format), first convert with `libreoffice --convert-to docx file.doc`.

When editing an existing Word document, use the **Document library** (a Python library for OOXML manipulation). The library automatically handles infrastructure setup and provides methods for document manipulation. For complex scenarios, you can access the underlying DOM directly through the library.

### Workflow
1. **MANDATORY - READ ENTIRE FILE**: Read [`ooxml.md`](ooxml.md) (~600 lines) completely from start to finish. **NEVER set any range limits when reading this file.** Read the full file content for the Document library API and XML patterns for directly editing document files.
2. Unpack the document: `python ooxml/scripts/unpack.py <office_file> <output_directory>`
3. Create and run a Python script using the Document library (see "Document Library" section in ooxml.md)
4. Pack the final document: `python ooxml/scripts/pack.py <input_directory> <office_file>`

The Document library provides both high-level methods for common operations and direct DOM access for complex scenarios.

## Adding Comments (批注)

Comments (批注) allow you to add annotations to documents without modifying the actual content. This is useful for review feedback, explanations, or questions about specific parts of a document.

### Recommended Method: Using python-docx (简单推荐)

The simplest and most reliable way to add comments is using the `python-docx` library:

```python
from docx import Document

# Open the document
doc = Document('input.docx')

# Find paragraphs and add comments
for para in doc.paragraphs:
    if "关键词" in para.text:  # Find paragraphs containing specific text
        doc.add_comment(
            runs=[para.runs[0]],  # Specify the text to comment on
            text="批注内容",
            author="Z.ai"          # Set comment author as Z.ai
        )

# Save the document
doc.save('output.docx')
```

**Key points:**
- Install: `pip install python-docx` or `bun add python-docx`
- Works directly on .docx files (no need to unpack/pack)
- Simple API, reliable results
- Comments appear in Word's comment pane with Z.ai as author

**Common patterns:**

```python
from docx import Document

doc = Document('document.docx')

# Add comment to first paragraph
if doc.paragraphs:
    first_para = doc.paragraphs[0]
    doc.add_comment(
        runs=[first_para.runs[0]] if first_para.runs else [],
        text="Review this introduction",
        author="Z.ai"
    )

# Add comment to specific paragraph by index
target_para = doc.paragraphs[5]  # 6th paragraph
doc.add_comment(
    runs=[target_para.runs[0]],
    text="This section needs clarification",
    author="Z.ai"
)

# Add comments based on text search
for para in doc.paragraphs:
    if "important" in para.text.lower():
        doc.add_comment(
            runs=[para.runs[0]],
            text="Flagged for review",
            author="Z.ai"
        )

doc.save('output.docx')
```

### Alternative Method: Using OOXML (Advanced)

For complex scenarios requiring low-level XML manipulation, you can use the OOXML workflow. This method is more complex but provides finer control.

**Note:** This method requires unpacking/packing documents and may encounter validation issues. Use python-docx unless you specifically need low-level XML control.

#### OOXML Workflow

1. **Unpack the document**: `python ooxml/scripts/unpack.py <file.docx> <output_dir>`

2. **Create and run a Python script**:

```python
from scripts.document import Document

# Initialize with Z.ai as the author
doc = Document('unpacked', author="Z.ai", initials="Z")

# Add comment on a paragraph
para = doc["word/document.xml"].get_node(tag="w:p", contains="paragraph text")
doc.add_comment(start=para, end=para, text="This needs clarification")

# Save changes
doc.save()
```

3. **Pack the document**: `python ooxml/scripts/pack.py <unpacked_dir> <output.docx>`

**When to use OOXML method:**
- You need to work with tracked changes simultaneously
- You need fine-grained control over XML structure
- You're already working with unpacked documents
- You need to manipulate comments in complex ways

**When to use python-docx method (recommended):**
- Adding comments is your primary task
- You want simple, reliable code
- You're working with complete .docx files
- You don't need low-level XML access

## Redlining workflow for document review

This workflow allows you to plan comprehensive tracked changes using markdown before implementing them in OOXML. **CRITICAL**: For complete tracked changes, you must implement ALL changes systematically.

**Batching Strategy**: Group related changes into batches of 3-10 changes. This makes debugging manageable while maintaining efficiency. Test each batch before moving to the next.

**Principle: Minimal, Precise Edits**
When implementing tracked changes, only mark text that actually changes. Repeating unchanged text makes edits harder to review and appears unprofessional. Break replacements into: [unchanged text] + [deletion] + [insertion] + [unchanged text]. Preserve the original run's RSID for unchanged text by extracting the `<w:r>` element from the original and reusing it.

Example - Changing "30 days" to "60 days" in a sentence:
```python
# BAD - Replaces entire sentence
'<w:del><w:r><w:delText>The term is 30 days.</w:delText></w:r></w:del><w:ins><w:r><w:t>The term is 60 days.</w:t></w:r></w:ins>'

# GOOD - Only marks what changed, preserves original <w:r> for unchanged text
'<w:r w:rsidR="00AB12CD"><w:t>The term is </w:t></w:r><w:del><w:r><w:delText>30</w:delText></w:r></w:del><w:ins><w:r><w:t>60</w:t></w:r></w:ins><w:r w:rsidR="00AB12CD"><w:t> days.</w:t></w:r>'
```

### Tracked changes workflow

1. **Get markdown representation**: Convert document to markdown with tracked changes preserved:
   ```bash
   pandoc --track-changes=all path-to-file.docx -o current.md
   ```

2. **Identify and group changes**: Review the document and identify ALL changes needed, organizing them into logical batches:

   **Location methods** (for finding changes in XML):
   - Section/heading numbers (e.g., "Section 3.2", "Article IV")
   - Paragraph identifiers if numbered
   - Grep patterns with unique surrounding text
   - Document structure (e.g., "first paragraph", "signature block")
   - **DO NOT use markdown line numbers** - they don't map to XML structure

   **Batch organization** (group 3-10 related changes per batch):
   - By section: "Batch 1: Section 2 amendments", "Batch 2: Section 5 updates"
   - By type: "Batch 1: Date corrections", "Batch 2: Party name changes"
   - By complexity: Start with simple text replacements, then tackle complex structural changes
   - Sequential: "Batch 1: Pages 1-3", "Batch 2: Pages 4-6"

3. **Read documentation and unpack**:
   - **MANDATORY - READ ENTIRE FILE**: Read [`ooxml.md`](ooxml.md) (~600 lines) completely from start to finish. **NEVER set any range limits when reading this file.** Pay special attention to the "Document Library" and "Tracked Change Patterns" sections.
   - **Unpack the document**: `python ooxml/scripts/unpack.py <file.docx> <dir>`
   - **Note the suggested RSID**: The unpack script will suggest an RSID to use for your tracked changes. Copy this RSID for use in step 4b.

4. **Implement changes in batches**: Group changes logically (by section, by type, or by proximity) and implement them together in a single script. This approach:
   - Makes debugging easier (smaller batch = easier to isolate errors)
   - Allows incremental progress
   - Maintains efficiency (batch size of 3-10 changes works well)

   **Suggested batch groupings:**
   - By document section (e.g., "Section 3 changes", "Definitions", "Termination clause")
   - By change type (e.g., "Date changes", "Party name updates", "Legal term replacements")
   - By proximity (e.g., "Changes on pages 1-3", "Changes in first half of document")

   For each batch of related changes:

   **a. Map text to XML**: Grep for text in `word/document.xml` to verify how text is split across `<w:r>` elements.

   **b. Create and run script**: Use `get_node` to find nodes, implement changes, then `doc.save()`. See **"Document Library"** section in ooxml.md for patterns.

   **Note**: Always grep `word/document.xml` immediately before writing a script to get current line numbers and verify text content. Line numbers change after each script run.

5. **Pack the document**: After all batches are complete, convert the unpacked directory back to .docx:
   ```bash
   python ooxml/scripts/pack.py unpacked reviewed-document.docx
   ```

6. **Final verification**: Do a comprehensive check of the complete document:
   - Convert final document to markdown:
     ```bash
     pandoc --track-changes=all reviewed-document.docx -o verification.md
     ```
   - Verify ALL changes were applied correctly:
     ```bash
     grep "original phrase" verification.md  # Should NOT find it
     grep "replacement phrase" verification.md  # Should find it
     ```
   - Check that no unintended changes were introduced


## Converting Documents to Images

To visually analyze Word documents, convert them to images using a two-step process:

1. **Convert DOCX to PDF**:
   ```bash
   soffice --headless --convert-to pdf document.docx
   ```

2. **Convert PDF pages to JPEG images**:
   ```bash
   pdftoppm -jpeg -r 150 document.pdf page
   ```
   This creates files like `page-1.jpg`, `page-2.jpg`, etc.

Options:
- `-r 150`: Sets resolution to 150 DPI (adjust for quality/size balance)
- `-jpeg`: Output JPEG format (use `-png` for PNG if preferred)
- `-f N`: First page to convert (e.g., `-f 2` starts from page 2)
- `-l N`: Last page to convert (e.g., `-l 5` stops at page 5)
- `page`: Prefix for output files

Example for specific range:
```bash
pdftoppm -jpeg -r 150 -f 2 -l 5 document.pdf page  # Converts only pages 2-5
```

## Code Style Guidelines
**IMPORTANT**: When generating code for DOCX operations:
- Write concise code
- Avoid verbose variable names and redundant operations
- Avoid unnecessary print statements

## Dependencies

Required dependencies (install if not available):

- **pandoc**: `sudo apt-get install pandoc` (for text extraction)
- **docx**: `bun add docx` (for creating new documents)
- **LibreOffice**: `sudo apt-get install libreoffice` (for PDF conversion)
- **Poppler**: `sudo apt-get install poppler-utils` (for pdftoppm to convert PDF to images)
- **defusedxml**: `pip install defusedxml` (for secure XML parsing)
