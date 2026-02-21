# PDF Processing Advanced Reference

This document contains advanced PDF processing features, detailed examples, and additional libraries not covered in the main skill instructions.

## pypdfium2 Library (Apache/BSD License)

### Overview
pypdfium2 is a Python binding for PDFium (Chromium's PDF library). It's excellent for fast PDF rendering, image generation, and serves as a PyMuPDF replacement.

### Render PDF to Images
```python
import pypdfium2 as pdfium
from PIL import Image

# Load PDF
pdf = pdfium.PdfDocument("document.pdf")

# Render page to image
page = pdf[0]  # First page
bitmap = page.render(
    scale=2.0,  # Higher resolution
    rotation=0  # No rotation
)

# Convert to PIL Image
img = bitmap.to_pil()
img.save("page_1.png", "PNG")

# Process multiple pages
for i, page in enumerate(pdf):
    bitmap = page.render(scale=1.5)
    img = bitmap.to_pil()
    img.save(f"page_{i+1}.jpg", "JPEG", quality=90)
```

### Extract Text with pypdfium2
```python
import pypdfium2 as pdfium

pdf = pdfium.PdfDocument("document.pdf")
for i, page in enumerate(pdf):
    text = page.get_text()
    print(f"Page {i+1} text length: {len(text)} chars")
```

## JavaScript Libraries

### pdf-lib (MIT License)

pdf-lib is a powerful JavaScript library for creating and modifying PDF documents in any JavaScript environment.

#### Load and Manipulate Existing PDF
```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

async function manipulatePDF() {
    // Load existing PDF
    const existingPdfBytes = fs.readFileSync('input.pdf');
    const pdfDoc = await PDFDocument.load(existingPdfBytes);

    // Get page count
    const pageCount = pdfDoc.getPageCount();
    console.log(`Document has ${pageCount} pages`);

    // Add new page
    const newPage = pdfDoc.addPage([600, 400]);
    newPage.drawText('Added by pdf-lib', {
        x: 100,
        y: 300,
        size: 16
    });

    // Save modified PDF
    const pdfBytes = await pdfDoc.save();
    fs.writeFileSync('modified.pdf', pdfBytes);
}
```

#### Create Complex PDFs from Scratch

**Note**: This JavaScript example uses pdf-lib's built-in StandardFonts. For Python/reportlab, always use the six registered fonts defined in SKILL.md (SimHei, Microsoft YaHei, SarasaMonoSC, Times New Roman, Calibri, DejaVuSans).

```javascript
import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
import fs from 'fs';

async function createPDF() {
    const pdfDoc = await PDFDocument.create();

    // Add fonts
    const helveticaFont = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const helveticaBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

    // Add page
    const page = pdfDoc.addPage([595, 842]); // A4 size
    const { width, height } = page.getSize();

    // Add text with styling
    page.drawText('Invoice #12345', {
        x: 50,
        y: height - 50,
        size: 18,
        font: helveticaBold,
        color: rgb(0.2, 0.2, 0.8)
    });

    // Add rectangle (header background)
    page.drawRectangle({
        x: 40,
        y: height - 100,
        width: width - 80,
        height: 30,
        color: rgb(0.9, 0.9, 0.9)
    });

    // Add table-like content
    const items = [
        ['Item', 'Qty', 'Price', 'Total'],
        ['Widget', '2', '$50', '$100'],
        ['Gadget', '1', '$75', '$75']
    ];

    let yPos = height - 150;
    items.forEach(row => {
        let xPos = 50;
        row.forEach(cell => {
            page.drawText(cell, {
                x: xPos,
                y: yPos,
                size: 12,
                font: helveticaFont
            });
            xPos += 120;
        });
        yPos -= 25;
    });

    const pdfBytes = await pdfDoc.save();
    fs.writeFileSync('created.pdf', pdfBytes);
}
```

#### Advanced Merge and Split Operations
```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

async function mergePDFs() {
    // Create new document
    const mergedPdf = await PDFDocument.create();

    // Load source PDFs
    const pdf1Bytes = fs.readFileSync('doc1.pdf');
    const pdf2Bytes = fs.readFileSync('doc2.pdf');

    const pdf1 = await PDFDocument.load(pdf1Bytes);
    const pdf2 = await PDFDocument.load(pdf2Bytes);

    // Copy pages from first PDF
    const pdf1Pages = await mergedPdf.copyPages(pdf1, pdf1.getPageIndices());
    pdf1Pages.forEach(page => mergedPdf.addPage(page));

    // Copy specific pages from second PDF (pages 0, 2, 4)
    const pdf2Pages = await mergedPdf.copyPages(pdf2, [0, 2, 4]);
    pdf2Pages.forEach(page => mergedPdf.addPage(page));

    const mergedPdfBytes = await mergedPdf.save();
    fs.writeFileSync('merged.pdf', mergedPdfBytes);
}
```

### pdfjs-dist (Apache License)

PDF.js is Mozilla's JavaScript library for rendering PDFs in the browser.

#### Basic PDF Loading and Rendering
```javascript
import * as pdfjsLib from 'pdfjs-dist';

// Configure worker (important for performance)
pdfjsLib.GlobalWorkerOptions.workerSrc = './pdf.worker.js';

async function renderPDF() {
    // Load PDF
    const loadingTask = pdfjsLib.getDocument('document.pdf');
    const pdf = await loadingTask.promise;

    console.log(`Loaded PDF with ${pdf.numPages} pages`);

    // Get first page
    const page = await pdf.getPage(1);
    const viewport = page.getViewport({ scale: 1.5 });

    // Render to canvas
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    const renderContext = {
        canvasContext: context,
        viewport: viewport
    };

    await page.render(renderContext).promise;
    document.body.appendChild(canvas);
}
```

#### Extract Text with Coordinates
```javascript
import * as pdfjsLib from 'pdfjs-dist';

async function extractText() {
    const loadingTask = pdfjsLib.getDocument('document.pdf');
    const pdf = await loadingTask.promise;

    let fullText = '';

    // Extract text from all pages
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();

        const pageText = textContent.items
            .map(item => item.str)
            .join(' ');

        fullText += `\n--- Page ${i} ---\n${pageText}`;

        // Get text with coordinates for advanced processing
        const textWithCoords = textContent.items.map(item => ({
            text: item.str,
            x: item.transform[4],
            y: item.transform[5],
            width: item.width,
            height: item.height
        }));
    }

    console.log(fullText);
    return fullText;
}
```

#### Extract Annotations and Forms
```javascript
import * as pdfjsLib from 'pdfjs-dist';

async function extractAnnotations() {
    const loadingTask = pdfjsLib.getDocument('annotated.pdf');
    const pdf = await loadingTask.promise;

    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const annotations = await page.getAnnotations();

        annotations.forEach(annotation => {
            console.log(`Annotation type: ${annotation.subtype}`);
            console.log(`Content: ${annotation.contents}`);
            console.log(`Coordinates: ${JSON.stringify(annotation.rect)}`);
        });
    }
}
```

## Advanced Command-Line Operations

### poppler-utils Advanced Features

#### Extract Text with Bounding Box Coordinates
```bash
# Extract text with bounding box coordinates (essential for structured data)
pdftotext -bbox-layout document.pdf output.xml

# The XML output contains precise coordinates for each text element
```

#### Advanced Image Conversion
```bash
# Convert to PNG images with specific resolution
pdftoppm -png -r 300 document.pdf output_prefix

# Convert specific page range with high resolution
pdftoppm -png -r 600 -f 1 -l 3 document.pdf high_res_pages

# Convert to JPEG with quality setting
pdftoppm -jpeg -jpegopt quality=85 -r 200 document.pdf jpeg_output
```

#### Extract Embedded Images
```bash
# Extract all embedded images with metadata
pdfimages -j -p document.pdf page_images

# List image info without extracting
pdfimages -list document.pdf

# Extract images in their original format
pdfimages -all document.pdf images/img
```

### qpdf Advanced Features

#### Complex Page Manipulation
```bash
# Split PDF into groups of pages
qpdf --split-pages=3 input.pdf output_group_%02d.pdf

# Extract specific pages with complex ranges
qpdf input.pdf --pages input.pdf 1,3-5,8,10-end -- extracted.pdf

# Merge specific pages from multiple PDFs
qpdf --empty --pages doc1.pdf 1-3 doc2.pdf 5-7 doc3.pdf 2,4 -- combined.pdf
```

#### PDF Optimization and Repair
```bash
# Optimize PDF for web (linearize for streaming)
qpdf --linearize input.pdf optimized.pdf

# Remove unused objects and compress
qpdf --optimize-level=all input.pdf compressed.pdf

# Attempt to repair corrupted PDF structure
qpdf --check input.pdf
qpdf --fix-qdf damaged.pdf repaired.pdf

# Show detailed PDF structure for debugging
qpdf --show-all-pages input.pdf > structure.txt
```

#### Advanced Encryption
```bash
# Add password protection with specific permissions
qpdf --encrypt user_pass owner_pass 256 --print=none --modify=none -- input.pdf encrypted.pdf

# Check encryption status
qpdf --show-encryption encrypted.pdf

# Remove password protection (requires password)
qpdf --password=secret123 --decrypt encrypted.pdf decrypted.pdf
```

## Advanced Python Techniques

### pdfplumber Advanced Features

#### Extract Text with Precise Coordinates
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    page = pdf.pages[0]
    
    # Extract all text with coordinates
    chars = page.chars
    for char in chars[:10]:  # First 10 characters
        print(f"Char: '{char['text']}' at x:{char['x0']:.1f} y:{char['y0']:.1f}")
    
    # Extract text by bounding box (left, top, right, bottom)
    bbox_text = page.within_bbox((100, 100, 400, 200)).extract_text()
```

#### Advanced Table Extraction with Custom Settings
```python
import pdfplumber
import pandas as pd

with pdfplumber.open("complex_table.pdf") as pdf:
    page = pdf.pages[0]
    
    # Extract tables with custom settings for complex layouts
    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "intersection_tolerance": 15
    }
    tables = page.extract_tables(table_settings)
    
    # Visual debugging for table extraction
    img = page.to_image(resolution=150)
    img.save("debug_layout.png")
```

### reportlab Advanced Features

#### Quick TOC Template (Copy-Paste Ready)

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# Register fonts first
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))
registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman')

# Setup
doc = SimpleDocTemplate("report.pdf", pagesize=A4,
                       leftMargin=0.75*inch, rightMargin=0.75*inch)
styles = getSampleStyleSheet()

# Configure heading style
styles['Heading1'].fontName = 'Times New Roman'
styles['Heading1'].textColor = colors.black  # Titles must be black

story = []

# Calculate dimensions
page_width = A4[0]
available_width = page_width - 1.5*inch
page_num_width = 50  # Fixed width for page numbers (enough for 3-4 digits)

# Calculate dots: fill space from title to page number
dots_column_width = available_width - 200 - page_num_width  # Reserve space for title + page
optimal_dot_count = int(dots_column_width / 4.5)  # ~4.5pt per dot at 7pt font

# Define styles
toc_style = ParagraphStyle('TOCEntry', parent=styles['Normal'],
                          fontName='Times New Roman', fontSize=11, leading=16)
dots_style = ParagraphStyle('LeaderDots', parent=styles['Normal'],
                           fontName='Times New Roman', fontSize=7, leading=16)  # Smaller font for more dots

# Build TOC (use Paragraph with <b></b> for bold heading)
toc_data = [
    [Paragraph('<b>Table of Contents</b>', styles['Heading1']), '', ''],
    ['', '', ''],
]

entries = [('Section 1', '5'), ('Section 2', '10')]
for title, page in entries:
    toc_data.append([
        Paragraph(title, toc_style),
        Paragraph('.' * optimal_dot_count, dots_style),
        Paragraph(page, toc_style)
    ])

# Use None for title column (auto-expand), fixed for others
toc_table = Table(toc_data, colWidths=[None, dots_column_width, page_num_width])
toc_table.setStyle(TableStyle([
    ('GRID', (0, 0), (-1, -1), 0, colors.white),
    ('LINEBELOW', (0, 0), (0, 0), 1.5, colors.black),
    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
    ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ('TOPPADDING', (0, 2), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 2), (-1, -1), 3),
    ('TEXTCOLOR', (1, 2), (1, -1), colors.HexColor('#888888')),
]))

story.append(toc_table)
story.append(PageBreak())

doc.build(story)
```

#### Advanced: Table of Contents with Leader Dots

**Critical Rules for TOC with Leader Dots:**

1. **Three-column structure**: [Title, Dots, Page Number] for leader dot style
2. **Column width strategy**:
   - Title: `None` (auto-expands to content)
   - Dots: Calculated width = `available_width - 200 - 50` (reserves space for title + page)
   - Page number: Fixed `50pt` (enough for 3-4 digit numbers, ensures right alignment)
3. **Dynamic dot count**: `int(dots_column_width / 4.5)` for 7pt font (adjust based on font size)
4. **Dot styling**: Small font (7-8pt) and gray color (#888888) for professional look
5. **Alignment sequence**: LEFT (title) → LEFT (dots flow from title) → RIGHT (page numbers)
6. **Zero padding**: Essential for seamless visual connection between columns
7. **Indentation**: Use leading spaces in title text for hierarchy (e.g., "    1.1 Subsection")

**MANDATORY STYLE REQUIREMENTS:**
- ✅ USE FIXED WIDTHS: Percentage-based widths are STRICTLY FORBIDDEN. You MUST use fixed values to guarantee alignment, especially for page numbers.
- ✅ DYNAMIC LEADER DOTS: Hard-coded dot counts are STRICTLY FORBIDDEN. You MUST calculate the number of dots dynamically based on the column width to prevent overflow or wrapping.
- ✅ MINIMUM COLUMN WIDTH: The page number column MUST be at least 40pt wide. Anything less will prevent proper right alignment.
- ✅ DOT FONT SIZE: Leader dot font size MUST NOT EXCEED 8pt. Larger sizes will ruin the dot density and are unacceptable.
- ✅ DOT ALIGNMENT: Dots MUST remain left-aligned to maintain the visual flow from the title. Right-aligning dots is forbidden.
- ✅ ZERO PADDING: Padding between columns MUST be set to exactly 0. Any gap will create a break in the dot line and is not allowed.
- ✅ USE PARAGRAPH OBJECTS: Bold text MUST be wrapped in a Paragraph() object like `Paragraph('<b>Text</b>', style)`. Using plain strings like `'<b>Text</b>'` is strictly STRICTLY FORBIDDEN as styles will not render.

#### CRITICAL: Table Cell Content Must Use Paragraph

**ALL text content in table cells MUST be wrapped in `Paragraph()` objects.** This is essential for:
- Rendering formatting tags (`<b>`, `<super>`, `<sub>`, `<i>`)
- Proper font application
- Correct text alignment within cells
- Consistent styling across the table

**The ONLY exception**: `Image()` objects can be placed directly in table cells without Paragraph wrapping.

```python
from reportlab.platypus import Table, TableStyle, Paragraph, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Define cell styles
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

# ✅ CORRECT: All text wrapped in Paragraph()
data = [
    [
        Paragraph('<b>Name</b>', header_style),
        Paragraph('<b>Formula</b>', header_style),
        Paragraph('<b>Value</b>', header_style)
    ],
    [
        Paragraph('Water', cell_style),
        Paragraph('H<sub>2</sub>O', cell_style),           # Subscript works
        Paragraph('18.015 g/mol', cell_style)
    ],
    [
        Paragraph('Pressure', cell_style),
        Paragraph('1.01 x 10<super>5</super> Pa', cell_style),  # Superscript works
        Paragraph('<b>Standard</b>', cell_style)            # Bold works
    ]
]

# ❌ WRONG: Plain strings - NO formatting will render
# data = [
#     ['<b>Name</b>', '<b>Formula</b>', '<b>Value</b>'],     # Bold won't work!
#     ['Water', 'H<sub>2</sub>O', '18.015 g/mol'],           # Subscript won't work!
# ]

# Image exception - Image objects go directly, no Paragraph needed
# data_with_image = [
#     [Paragraph('<b>Logo</b>', header_style), Paragraph('<b>Description</b>', header_style)],
#     [Image('logo.png', width=50, height=50), Paragraph('Company logo', cell_style)],
# ]

table = Table(data, colWidths=[100, 150, 100])
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
]))
```

#### Debug Tips for Layout Issues

```python
from reportlab.platypus import HRFlowable
from reportlab.lib.colors import red

# Visualize spacing during development
story.append(table)
story.append(HRFlowable(width="100%", color=red, thickness=0.5, spaceBefore=0, spaceAfter=0))
story.append(Spacer(1, 6))
story.append(HRFlowable(width="100%", color=red, thickness=0.5, spaceBefore=0, spaceAfter=0))
story.append(caption)
# This creates visual markers to see actual spacing
```

## Complex Workflows

### Extract Figures/Images from PDF

#### Method 1: Using pdfimages (fastest)
```bash
# Extract all images with original quality
pdfimages -all document.pdf images/img
```

#### Method 2: Using pypdfium2 + Image Processing
```python
import pypdfium2 as pdfium
from PIL import Image
import numpy as np

def extract_figures(pdf_path, output_dir):
    pdf = pdfium.PdfDocument(pdf_path)
    
    for page_num, page in enumerate(pdf):
        # Render high-resolution page
        bitmap = page.render(scale=3.0)
        img = bitmap.to_pil()
        
        # Convert to numpy for processing
        img_array = np.array(img)
        
        # Simple figure detection (non-white regions)
        mask = np.any(img_array != [255, 255, 255], axis=2)
        
        # Find contours and extract bounding boxes
        # (This is simplified - real implementation would need more sophisticated detection)
        
        # Save detected figures
        # ... implementation depends on specific needs
```

### Batch PDF Processing with Error Handling
```python
import os
import glob
from pypdf import PdfReader, PdfWriter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def batch_process_pdfs(input_dir, operation='merge'):
    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    
    if operation == 'merge':
        writer = PdfWriter()
        for pdf_file in pdf_files:
            try:
                reader = PdfReader(pdf_file)
                for page in reader.pages:
                    writer.add_page(page)
                logger.info(f"Processed: {pdf_file}")
            except Exception as e:
                logger.error(f"Failed to process {pdf_file}: {e}")
                continue
        
        with open("batch_merged.pdf", "wb") as output:
            writer.write(output)
    
    elif operation == 'extract_text':
        for pdf_file in pdf_files:
            try:
                reader = PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                
                output_file = pdf_file.replace('.pdf', '.txt')
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                logger.info(f"Extracted text from: {pdf_file}")
                
            except Exception as e:
                logger.error(f"Failed to extract text from {pdf_file}: {e}")
                continue
```

### Advanced PDF Cropping
```python
from pypdf import PdfWriter, PdfReader

reader = PdfReader("input.pdf")
writer = PdfWriter()

# Crop page (left, bottom, right, top in points)
page = reader.pages[0]
page.mediabox.left = 50
page.mediabox.bottom = 50
page.mediabox.right = 550
page.mediabox.top = 750

writer.add_page(page)
with open("cropped.pdf", "wb") as output:
    writer.write(output)
```

## Performance Optimization Tips

### 1. For Large PDFs
- Use streaming approaches instead of loading entire PDF in memory
- Use `qpdf --split-pages` for splitting large files
- Process pages individually with pypdfium2

### 2. For Text Extraction
- `pdftotext -bbox-layout` is fastest for plain text extraction
- Use pdfplumber for structured data and tables
- Avoid `pypdf.extract_text()` for very large documents

### 3. For Image Extraction
- `pdfimages` is much faster than rendering pages
- Use low resolution for previews, high resolution for final output

### 4. For Form Filling
- pdf-lib maintains form structure better than most alternatives
- Pre-validate form fields before processing

### 5. Memory Management
```python
# Process PDFs in chunks
def process_large_pdf(pdf_path, chunk_size=10):
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    for start_idx in range(0, total_pages, chunk_size):
        end_idx = min(start_idx + chunk_size, total_pages)
        writer = PdfWriter()
        
        for i in range(start_idx, end_idx):
            writer.add_page(reader.pages[i])
        
        # Process chunk
        with open(f"chunk_{start_idx//chunk_size}.pdf", "wb") as output:
            writer.write(output)
```

## Troubleshooting Common Issues

### Encrypted PDFs
```python
# Handle password-protected PDFs
from pypdf import PdfReader

try:
    reader = PdfReader("encrypted.pdf")
    if reader.is_encrypted:
        reader.decrypt("password")
except Exception as e:
    print(f"Failed to decrypt: {e}")
```

### Corrupted PDFs
```bash
# Use qpdf to repair
qpdf --check corrupted.pdf
qpdf --replace-input corrupted.pdf
```

### Text Extraction Issues
```python
# Fallback to OCR for scanned PDFs
import pytesseract
from pdf2image import convert_from_path

def extract_text_with_ocr(pdf_path):
    images = convert_from_path(pdf_path)
    text = ""
    for i, image in enumerate(images):
        text += pytesseract.image_to_string(image)
    return text
```

## License Information

- **pypdf**: BSD License
- **pdfplumber**: MIT License
- **pypdfium2**: Apache/BSD License
- **reportlab**: BSD License
- **poppler-utils**: GPL-2 License
- **qpdf**: Apache License
- **pdf-lib**: MIT License
- **pdfjs-dist**: Apache License