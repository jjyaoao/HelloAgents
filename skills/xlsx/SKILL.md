---
name: xlsx
description: "Comprehensive spreadsheet creation, editing, and analysis with support for formulas, formatting, data analysis, and visualization. When GLM needs to work with spreadsheets (.xlsx, .xlsm, .csv, .tsv, etc) for: (1) Creating new spreadsheets with formulas and formatting, (2) Reading or analyzing data, (3) Modify existing spreadsheets while preserving formulas, (4) Data analysis and visualization in spreadsheets, or (5) Recalculating formulas"
license: Proprietary. LICENSE.txt has complete terms
---

# XLSX creation, editing, and analysis

## Overview

A user may ask you to create, edit, or analyze the contents of an .xlsx file. You have different tools and workflows available for different tasks.

Must output excel files.

## Important Requirements

**Python 3 and openpyxl Required for Excel Generation**: You can assume Python 3 as the runtime environment. The `openpyxl` library is required as the primary tool for creating Excel files, managing styles, and writing formulas.

**pandas Utilized for Data Processing**: You can utilize `pandas` for efficient data manipulation and processing tasks. The processed data is subsequently exported to the final Excel file through `openpyxl`.

**LibreOffice Required for Formula Recalculation**: You can utilize `recalc.py` for formula check. You can assume LibreOffice is installed for recalculating formula values using the `recalc.py` script. The script automatically configures LibreOffice on first run.


# Requirements for Outputs

## All Excel files

## Critical Instruction Protocols

### Query Decomposition & Verification
Before generating any code, strictly analyze the user's prompt.
- **Explicit Requests**: Analyze Explicit Needs: Clearly identify the analytical objectives, constraints, required formats, the Excel sheets to be delivered (including sheet names, column definitions, calculation logic, and required metrics), as well as all data fields explicitly requested by the user. These elements define the mandatory delivery scope and specify exactly what must be built in the workbook.
- **Implicit Requests**:Analyze Implicit Needs: Evaluate the business context, intended users of the Excel file, expected interaction patterns (e.g., filtering, sorting, manual inputs), and downstream use cases such as reporting or decision support. These considerations guide how sheets are structured, formulas are designed, and results are presented to ensure usability and clarity.
- **Multi-Part Requests**: If the user asks for "two tables", "three scenarios", or "a summary and a detail sheet", you MUST generate ALL requested components.


### Zero Formula Errors
- Every Excel model MUST be delivered with ZERO formula errors (#REF!, #DIV/0!, #VALUE!, #N/A, #NAME?)

### Preserve Existing Templates (when updating templates)
- Study and EXACTLY match existing format, style, and conventions when modifying files
- Never impose standardized formatting on files with established patterns
- Existing template conventions ALWAYS override these guidelines


## Financial models

### Color Coding Standards
Unless otherwise stated by the user or existing template

#### Industry-Standard Color Conventions
- **Blue text (RGB: 0,0,255)**: Hardcoded inputs, and numbers users will change for scenarios
- **Black text (RGB: 0,0,0)**: ALL formulas and calculations
- **Green text (RGB: 0,128,0)**: Links pulling from other worksheets within same workbook
- **Red text (RGB: 255,0,0)**: External links to other files
- **Yellow background (RGB: 255,255,0)**: Key assumptions needing attention or cells that need to be updated

### Number Formatting Standards

#### Required Format Rules
- **Years**: Format as text strings (e.g., "2024" not "2,024")
- **Currency**: Use $#,##0 format; ALWAYS specify units in headers ("Revenue ($mm)")
- **Zeros**: Use number formatting to make all zeros "-", including percentages (e.g., "$#,##0;($#,##0);-")
- **Percentages**: Default to 0.0% format (one decimal)
- **Multiples**: Format as 0.0x for valuation multiples (EV/EBITDA, P/E)
- **Negative numbers**: Use parentheses (123) not minus -123

### Formula Construction Rules

#### Assumptions Placement
- Place ALL assumptions (growth rates, margins, multiples, etc.) in separate assumption cells
- Use cell references instead of hardcoded values in formulas
- Example: Use =B5*(1+$B$6) instead of =B5*1.05

#### Formula Error Prevention
- Verify all cell references are correct
- Check for off-by-one errors in ranges
- Ensure consistent formulas across all projection periods
- Test with edge cases (zero values, negative numbers)
- Verify no unintended circular references

#### Documentation Requirements for Hardcodes
- Comment or in cells beside (if end of table). Format: "Source: [System/Document], [Date], [Specific Reference], [URL if applicable]"
- Examples:
  - "Source: Company 10-K, FY2024, Page 45, Revenue Note, [SEC EDGAR URL]"
  - "Source: Company 10-Q, Q2 2025, Exhibit 99.1, [SEC EDGAR URL]"
  - "Source: Bloomberg Terminal, 8/15/2025, AAPL US Equity"
  - "Source: FactSet, 8/20/2025, Consensus Estimates Screen"


## Style Rules

Implement all styling directly using the `python-openpyxl` library. The following standards define the visual architecture of the spreadsheets.

### Global Layout & Design Principles
**Layout & Dimensions**
- **Canvas Origin**: Content MUST start at cell **B2** to provide a top-left padding margin. Do not start at A1.
- **Cell Sizing**: Optimize column widths and row heights for data readability. Avoid unscaled cells (e.g., narrow columns with excessive height).
- **Title Row**: Row 2 is reserved for the title. Explicitly set row height to prevent clipping: `row_dimensions[2].height = 30` (adjust upwards if font size requires).
  
**Visual Hierarchy**
- **Professionalism**: Prioritize business-appropriate color schemes. Avoid decorative elements that distract from data.
- **Consistency**: Apply uniform fonts, borders, and colors to similar data types across the workbook.
- **White Space**: Maintain adequate margins to prevent visual crowding.
- **Alternating Row Fill**: When the data area of the table exceeds three rows, alternating row fills (white and gray) are applied by default.
- When making the chart, labels and text elements are kept as concise as possible to maximize readability, and provide a clear reference key or table nearby mapping them to their original full names.


### Font Standards (MUST FOLLOW)
- **English Text**: Always use **Times New Roman** as the default font

```python
# Font configuration example
from openpyxl.styles import Font

# English content
english_font = Font(name='Times New Roman', size=11)

```


### Title Formatting Rules (MUST FOLLOW)
- **NO Background Shading**: Titles must NOT have any background fill/shading (PatternFill)
- **Left Alignment**: All titles must be left-aligned, NOT centered
- **Bold Text**: Use bold font weight to distinguish titles instead of background colors

```python
# ✅ CORRECT Title Style

from openpyxl.styles import Font, Alignment
from openpyxl import Workbook

# Load existing file
wb = Workbook()
sheet = wb.active

title_font = Font(name='Times New Roman', size=18, bold=True, color="000000")
title_alignment = Alignment(horizontal='left', vertical='center')

sheet['B2'] = "Report Title"
sheet['B2'].font = title_font
sheet['B2'].alignment = title_alignment
# NO fill applied - title has no background shading

# ❌ WRONG - Do NOT use background shading on titles
# title_fill = PatternFill(start_color="333333", fill_type="solid")  # FORBIDDEN
# sheet['B2'].fill = title_fill  # FORBIDDEN
```



### Visual Themes
#### 1. Default Style
**Use for:** All non-financial tasks (General data, project management, inventories).

**Color Palette Constraints**
- **Base Colors**: White (#FFFFFF), Black (#000000), and Grey scales ONLY.
- **Accent Color**: **Blue** (varying saturation) is the ONLY allowed accent color for highlighting or differentiation.
- **Restrictions**: 
  - ❌ NO Green, Red, Orange, Purple, Yellow, or Pink.
  - ❌ NO Gradients or Rainbow schemes.

```python
# Palette
from openpyxl.styles import Alignment, Border, Font, Side, PatternFill, 

# Base & Accents
background_white = "FFFFFF"           # background
background_row_alt = "E9E9E9"         # Alternating row fill
grey_header = "333333"   # Section headers
border_grey = "E3DEDE"        # Standard borders
blue_primary = "0B5CAD"       # Primary Accent

# Application Example: Data Headers (NOT Titles)
header_fill = PatternFill(start_color=grey_header, end_color=grey_header, fill_type="solid")
header_font = Font(name='Times New Roman', color="FFFFFF", bold=True)

for cell in sheet['B3:E3'][0]:
    cell.fill = header_fill
    cell.font = header_font

# Example: Title style (NO shading, left-aligned)
title_font = Font(name='Times New Roman', size=18, bold=True, color="000000")
title_alignment = Alignment(horizontal='left', vertical='center')
sheet['B2'].font = title_font
sheet['B2'].alignment = title_alignment
# NO fill for titles
```

#### 2. Professional Finance Style
**Use for:** Financial, fiscal, and market analysis (Stock data, GDP, Budgets, P&L, ROI).

**Market Data Color Convention (Critical)**
Apply the following color logic based on the target region:

| Region | Price Up / Positive | Price Down / Negative |
| --- | --- | --- |
| **China (Mainland)** | **Red** | **Green** |
| **International** | **Green** | **Red** |

```python
# Professional Finance Palette
from openpyxl.styles import PatternFill, Font

text_dark = "000000"
background_light = "E6E8EB"
header_fill_blue = "1B3F66"
metrics_highlight_warm = "F5E6D3"
negative_red = "FF0000"


# Data Headers Example
pfs_header_fill = PatternFill(start_color=header_fill_blue, end_color=header_fill_blue, fill_type="solid")
pfs_header_font = Font(name='Times New Roman', color="FFFFFF", bold=True)

for cell in sheet['B3:E3'][0]:
    cell.fill = pfs_header_fill
    cell.font = pfs_header_font


# Default font - Times New Roman for English
default_font = Font(name='Times New Roman', size=11, color=text_dark)

# Example: Title style (NO shading, left-aligned)
# NO fill for titles
title_font = Font(name='Times New Roman', size=18, bold=True, color="000000")
title_alignment = Alignment(horizontal='left', vertical='center')
sheet['B2'].font = title_font
sheet['B2'].alignment = title_alignment

# Example: Apply header style (for data headers, NOT titles)
header_fill = PatternFill(start_color=grey_header, end_color=grey_header, fill_type="solid")
header_font = Font(name='Times New Roman', color="FFFFFF", bold=True)
for cell in sheet['B3:E3'][0]:  # Data headers, not title row
    cell.fill = header_fill
    cell.font = header_font
```

### Content Color Conventions
Apply specific font colors to indicate data source and functionality (consistent with Financial Model requirements):

- **Blue Font**: Hardcoded inputs and fixed values.
- **Black Font**: Calculated results and formulas.
- **Green Font**: References to other worksheets within the same file.
- **Red Font**: References to external files or sources.


## Chart Creation Notes

### 1. Data Source Must Contain “Actual Values”

* Excel formulas written via **openpyxl** are not automatically calculated, which can cause charts to appear blank because no cached values are available.
* You can use `recalc.py` to calculate the values so that charts reference computed results.
* Finally, use `recalc.py` again to perform a validation check.

### 2. Reference Range Must Match Title Settings

* When `titles_from_data=True` is set, **the first row of the reference range must contain text headers**.
  If this row is empty or contains numeric data, it may result in incorrect series names or data misalignment.
* Ensure that the chart’s reference range starts from the data rows and does not incorrectly include title rows.

### 3. Impact of “Visibility” on Chart Data

* By default, Excel charts do not plot data from hidden rows or columns (auxiliary tables are often hidden).
  You must **explicitly disable the “plot visible cells only” option**, otherwise the chart will appear blank.

```python
# After hiding auxiliary data rows, for each chart object,
# set plot_visible_only to False. This line is required.
chart.plot_visible_only = False
```


# Workflows

## Reading and analyzing data

### Data analysis with pandas
For data analysis, visualization, and basic operations, use **pandas** which provides powerful data manipulation capabilities:

```python
import pandas as pd

# Read Excel
df = pd.read_excel('file.xlsx')  # Default: first sheet
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)  # All sheets as dict

# Analyze
df.head()      # Preview data
df.info()      # Column info
df.describe()  # Statistics

# Write Excel
df.to_excel('output.xlsx', index=False)
```

## Excel File Workflows

## CRITICAL: Use Formulas, Not Hardcoded Values

**Always use Excel formulas instead of calculating values in Python and hardcoding them.** This ensures the spreadsheet remains dynamic and updateable.

### ❌ WRONG - Hardcoding Calculated Values
```python
# Bad: Calculating in Python and hardcoding result
total = df['Sales'].sum()
sheet['B10'] = total  # Hardcodes 5000

# Bad: Computing growth rate in Python
growth = (df.iloc[-1]['Revenue'] - df.iloc[0]['Revenue']) / df.iloc[0]['Revenue']
sheet['C5'] = growth  # Hardcodes 0.15

# Bad: Python calculation for average
avg = sum(values) / len(values)
sheet['D20'] = avg  # Hardcodes 42.5
```

### ✅ CORRECT - Using Excel Formulas
```python
# Good: Let Excel calculate the sum
sheet['B10'] = '=SUM(B2:B9)'

# Good: Growth rate as Excel formula
sheet['C5'] = '=(C4-C2)/C2'

# Good: Average using Excel function
sheet['D20'] = '=AVERAGE(D2:D19)'
```

This applies to ALL calculations - totals, percentages, ratios, differences, etc. The spreadsheet should be able to recalculate when source data changes.

## Common Workflow
1. **Choose tool**: pandas for data, openpyxl for formulas/formatting
2. **Think and Plan**: Plan all sheets structure, formulas, cross-references before coding
3. **Create/Load**: Create new workbook or load existing file
4. **Modify**: Add/edit data, formulas, and formatting
5. **Save**: Write to file
6. **Recalculate formulas (MANDATORY IF USING FORMULAS)**: Use the recalc.py script
   ```bash
   python recalc.py output.xlsx
   ```
7. **Verify and fix any errors**: 
   - The script returns JSON with error details
   - If `status` is `errors_found`, check `error_summary` for specific error types and locations
   - Fix the identified errors and recalculate again
   - Common errors to fix:
     - `#REF!`: Invalid cell references
     - `#DIV/0!`: Division by zero
     - `#NAME?`: Unrecognized formula name
       - **When writing to Excel, do not directly assign plain text that begins with “=” to a cell; otherwise, the system may misinterpret it as an invalid formula and trigger a `#NAME?` error.**
       - **For non-calculative descriptive text (such as legends), be sure to remove the leading equals sign before writing it in code, so it is correctly recognized as a regular string.**
     - `#VALUE!`: Wrong data type in formula
     

### Creating new Excel files

```python
# Using openpyxl for formulas and formatting
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
sheet = wb.active

# Add data
sheet['A1'] = 'Hello'
sheet['B1'] = 'World'
sheet.append(['Row', 'of', 'data'])

# Add formula
sheet['B2'] = '=SUM(A1:A10)'

# Formatting
sheet['A1'].font = Font(bold=True, color='FF0000')
sheet['A1'].fill = PatternFill('solid', start_color='FFFF00')
sheet['A1'].alignment = Alignment(horizontal='center')

# Column width
sheet.column_dimensions['A'].width = 20

wb.save('output.xlsx')
```

### Editing existing Excel files

```python
# Using openpyxl to preserve formulas and formatting
from openpyxl import load_workbook

# Load existing file
wb = load_workbook('existing.xlsx')
sheet = wb.active  # or wb['SheetName'] for specific sheet

# Working with multiple sheets
for sheet_name in wb.sheetnames:
    sheet = wb[sheet_name]
    print(f"Sheet: {sheet_name}")

# Modify cells
sheet['A1'] = 'New Value'
sheet.insert_rows(2)  # Insert row at position 2
sheet.delete_cols(3)  # Delete column 3

# Add new sheet
new_sheet = wb.create_sheet('NewSheet')
new_sheet['A1'] = 'Data'

wb.save('modified.xlsx')
```

## Recalculating formulas

Excel files created or modified by openpyxl contain formulas as strings but not calculated values. Use the provided `recalc.py` script to recalculate formulas:

```bash
python recalc.py <excel_file> [timeout_seconds]
```

Example:
```bash
python recalc.py output.xlsx 30
```

The script:
- Automatically sets up LibreOffice macro on first run
- Recalculates all formulas in all sheets
- Scans ALL cells for Excel errors (#REF!, #DIV/0!, etc.)
- Returns JSON with detailed error locations and counts
- Works on both Linux and macOS

## Formula Verification Checklist

Quick checks to ensure formulas work correctly:

### Essential Verification
- [ ] **Test 2-3 sample references**: Verify they pull correct values before building full model
- [ ] **Column mapping**: Confirm Excel columns match (e.g., column 64 = BL, not BK)
- [ ] **Row offset**: Remember Excel rows are 1-indexed (DataFrame row 5 = Excel row 6)

### Common Pitfalls
- [ ] **NaN handling**: Check for null values with `pd.notna()`
- [ ] **Far-right columns**: FY data often in columns 50+ 
- [ ] **Multiple matches**: Search all occurrences, not just first
- [ ] **Division by zero**: Check denominators before using `/` in formulas (#DIV/0!)
- [ ] **Wrong references**: Verify all cell references point to intended cells (#REF!)
- [ ] **Cross-sheet references**: Use correct format (Sheet1!A1) for linking sheets

### Formula Testing Strategy
- [ ] **Start small**: Test formulas on 2-3 cells before applying broadly
- [ ] **Verify dependencies**: Check all cells referenced in formulas exist
- [ ] **Test edge cases**: Include zero, negative, and very large values

### Interpreting recalc.py Output
The script returns JSON with error details:
```json
{
  "status": "success",           // or "errors_found"
  "total_errors": 0,              // Total error count
  "total_formulas": 42,           // Number of formulas in file
  "error_summary": {              // Only present if errors found
    "#REF!": {
      "count": 2,
      "locations": ["Sheet1!B5", "Sheet1!C10"]
    }
  }
}
```

## Best Practices

### Library Selection
- **pandas**: Best for data analysis, bulk operations, and simple data export
- **openpyxl**: Best for complex formatting, formulas, and Excel-specific features

### Working with openpyxl
- Cell indices are 1-based (row=1, column=1 refers to cell A1)
- Use `data_only=True` to read calculated values: `load_workbook('file.xlsx', data_only=True)`
- **Warning**: If opened with `data_only=True` and saved, formulas are replaced with values and permanently lost
- For large files: Use `read_only=True` for reading or `write_only=True` for writing
- Formulas are preserved but not evaluated - use recalc.py to update values

### Working with pandas
- Specify data types to avoid inference issues: `pd.read_excel('file.xlsx', dtype={'id': str})`
- For large files, read specific columns: `pd.read_excel('file.xlsx', usecols=['A', 'C', 'E'])`
- Handle dates properly: `pd.read_excel('file.xlsx', parse_dates=['date_column'])`

## Code Style Guidelines
**IMPORTANT**: When generating Python code for Excel operations:
- Write minimal, concise Python code without unnecessary comments
- Avoid verbose variable names and redundant operations
- Avoid unnecessary print statements

**For Excel files themselves**:
- Add comments to cells with complex formulas or important assumptions
- Document data sources for hardcoded values
- Include notes for key calculations and model sections