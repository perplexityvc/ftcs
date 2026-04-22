#!/usr/bin/env python3
"""
Optimized OCR Table Extraction to Excel
Version 4.3 - Now with centralized settings
Extracts accounting tables and creates formatted Excel output
"""
import subprocess
import re
import csv
import sys
import os
import shutil
import builtins


def print(*args, **kwargs):
    """Print wrapper that falls back to ASCII-safe output on encoding errors."""
    try:
        builtins.print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = [str(arg).encode('ascii', 'replace').decode('ascii') for arg in args]
        builtins.print(*safe_args, **kwargs)

# Import settings
try:
    from settings import (
        ocr, preprocessing, table_detection, cleaning, 
        table_structure, paths, year_filter, error_correction,
        output, logging, batch, validation
    )
    SETTINGS_LOADED = True
except ImportError:
    # If settings.py not found, use inline defaults
    print("⚠ Warning: settings.py not found, using default settings")
    SETTINGS_LOADED = False
    
    # Create simple namespace for defaults
    class Settings: pass
    
    ocr = Settings()
    ocr.CONFIDENCE_THRESHOLD = 15
    ocr.PSM_MODE = '6'
    ocr.OUTPUT_FORMAT = 'tsv'
    ocr.TESSERACT_PATH = ''
    
    preprocessing = Settings()
    preprocessing.PIL_THRESHOLD = 122
    preprocessing.CONTRAST_ENHANCEMENT = 1.2
    preprocessing.APPLY_SHARPENING = True
    preprocessing.APPLY_BINARIZATION = True
    preprocessing.APPLY_VERTICAL_MASK = True
    preprocessing.MASK_TOP_RATIO = 0.33
    preprocessing.MASK_BOTTOM_RATIO = 0.15
    preprocessing.SAVE_MASKED_PREVIEW = True
    preprocessing.MASKED_PREVIEW_DIR = 'masked_inspection'
    
    table_detection = Settings()
    table_detection.ROW_GROUPING_TOLERANCE = 20
    table_detection.COLUMN_GROUPING_TOLERANCE = 45
    table_detection.EMPTY_COLUMN_THRESHOLD = 0.20
    
    cleaning = Settings()
    cleaning.STANDARD_DOC_NUMBER = 'B674'
    cleaning.MIN_DATE_LENGTH = 8
    cleaning.MIN_DOC_NUMBER_LENGTH = 2
    cleaning.DATE_REQUIRED_CHAR = '/'
    
    table_structure = Settings()
    table_structure.STANDARD_HEADERS = ['C/R Table', 'Date', 'Trans No', 'G/L', 'Doc No.', 'Orig Amount', 'Acc Amount']
    table_structure.HEADER_KEYWORDS = ['date', 'trans', 'number', 'amount', 'document', 'sel']
    table_structure.TABLE_NUMBER_PATTERNS = [
        r'C/R\s+Table\s+([A-Z0-9]+)',
        r'Table\s+([A-Z][A-Z0-9]{2,5})',
        r'C/R.*?([A-Z]{2}\d{2})',
    ]
    table_structure.MAX_TABLE_NUMBER_LENGTH = 10
    table_structure.MIN_TABLE_NUMBER_LENGTH = 2
    
    paths = Settings()
    paths.DEFAULT_INPUT_IMAGE = 'frame_0015.png'
    paths.DEFAULT_INPUT_FOLDER = 'frames_masked/frames_masked'
    paths.TEMP_PREPROCESSED_IMAGE = 'preprocessed.png'
    paths.DEFAULT_OUTPUT_CSV = 'extracted_table.csv'
    paths.EXCEL_GENERATOR_SCRIPT = 'create_excel.py'
    paths.TEMP_PREPROCESSED_IMAGE = 'preprocessed.png'
    paths.DEFAULT_OUTPUT_CSV = 'extracted_table.csv'
    paths.EXCEL_GENERATOR_SCRIPT = 'create_excel.py'
    
    year_filter = Settings()
    year_filter.TWO_DIGIT_YEAR_CUTOFF = 50
    year_filter.DEFAULT_CENTURY = 2000
    year_filter.ALTERNATIVE_CENTURY = 1900
    
    error_correction = Settings()
    
    output = Settings()
    output.CSV_ENCODING = 'utf-8'
    output.PREVIEW_ROWS = 10
    output.PREVIEW_COLUMN_WIDTH = 15
    
    logging = Settings()
    logging.CONSOLE_WIDTH = 70
    logging.SHOW_PROGRESS = True
    logging.SHOW_TIMING = True
    logging.VERBOSE_MODE = True
    
    batch = Settings()
    batch.CONTINUE_ON_ERROR = True
    batch.CLEANUP_TEMP_FILES = True
    
    validation = Settings()


def preprocess_image(input_path, output_path, use_binarization=None, mask_top_ratio=None, mask_bottom_ratio=None):
    """Preprocess green-on-black terminal image using Pillow"""
    
    try:
        from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageDraw
        
        # Load image
        img = Image.open(input_path)
        
        # Convert to grayscale
        img = img.convert('L')

        apply_binarization = (
            getattr(preprocessing, 'APPLY_BINARIZATION', True)
            if use_binarization is None else bool(use_binarization)
        )

        if apply_binarization:
            # Invert colors (green-on-black -> black-on-white)
            img = ImageOps.invert(img)

            # Apply threshold (binary conversion)
            threshold = preprocessing.PIL_THRESHOLD  # From settings (default 122 = 48% of 255)
            img = img.point(lambda x: 255 if x > threshold else 0, mode='1')

            # Convert back to grayscale for better OCR
            img = img.convert('L')
        
        # Apply sharpening if enabled
        if preprocessing.APPLY_SHARPENING:
            img = img.filter(ImageFilter.SHARPEN)
        
        # Apply contrast enhancement if configured
        if preprocessing.CONTRAST_ENHANCEMENT != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(preprocessing.CONTRAST_ENHANCEMENT)

        # Apply vertical masking before OCR
        if getattr(preprocessing, 'APPLY_VERTICAL_MASK', True):
            width, height = img.size
            top_ratio = float(getattr(preprocessing, 'MASK_TOP_RATIO', 0.33) if mask_top_ratio is None else mask_top_ratio)
            bottom_ratio = float(getattr(preprocessing, 'MASK_BOTTOM_RATIO', 0.15) if mask_bottom_ratio is None else mask_bottom_ratio)
            top_pixels = int(height * max(0.0, min(1.0, top_ratio)))
            bottom_pixels = int(height * max(0.0, min(1.0, bottom_ratio)))
            draw = ImageDraw.Draw(img)

            if top_pixels > 0:
                draw.rectangle([0, 0, width - 1, min(top_pixels - 1, height - 1)], fill=0)

            if bottom_pixels > 0:
                start_y = max(0, height - bottom_pixels)
                draw.rectangle([0, start_y, width - 1, height - 1], fill=0)
        
        # Save preprocessed image
        img.save(output_path)
        
        # Only show message in verbose mode
        if hasattr(logging, 'VERBOSE_MODE') and logging.VERBOSE_MODE and logging.SHOW_PROGRESS:
            print(f"     Using Pillow for preprocessing")
        
        return output_path
        
    except ImportError:
        print(f"     ⚠ Pillow not installed!")
        print(f"     Install with: pip install Pillow")
        print(f"     Using original image (OCR accuracy may be reduced)")
        return input_path

    except Exception as e:
        if logging.SHOW_PROGRESS:
            print(f"     ⚠ Preprocessing failed: {e}")
            print(f"     Using original image")
        return input_path


def save_masked_preview(preprocessed_image_path, source_image_path):
    """Save a copy of masked/preprocessed image for visual inspection."""
    if not getattr(preprocessing, 'SAVE_MASKED_PREVIEW', True):
        return None

    try:
        preview_dir = getattr(preprocessing, 'MASKED_PREVIEW_DIR', 'masked_inspection')
        os.makedirs(preview_dir, exist_ok=True)

        source_name = os.path.basename(source_image_path)
        source_stem, source_ext = os.path.splitext(source_name)
        ext = source_ext if source_ext else '.png'
        preview_path = os.path.join(preview_dir, f"{source_stem}_masked{ext}")

        shutil.copy2(preprocessed_image_path, preview_path)
        return preview_path
    except Exception as e:
        if logging.SHOW_PROGRESS:
            print(f"     ⚠ Could not save masked preview: {e}")
        return None


def _get_tesseract_candidates():
    """Build ordered tesseract command candidates from settings and platform defaults."""
    candidates = []

    configured_path = getattr(ocr, 'TESSERACT_PATH', '')
    if configured_path:
        configured_path = configured_path.strip().strip('"')
        if os.path.isdir(configured_path):
            if sys.platform == 'win32':
                candidates.append(os.path.join(configured_path, 'tesseract.exe'))
            candidates.append(os.path.join(configured_path, 'tesseract'))
        else:
            candidates.append(configured_path)

    if sys.platform == 'win32':
        candidates.extend(['tesseract.exe', 'tesseract'])
    else:
        candidates.append('tesseract')

    unique_candidates = []
    for candidate in candidates:
        if candidate and candidate not in unique_candidates:
            unique_candidates.append(candidate)

    return unique_candidates


def _run_tesseract(args, capture_output=True, text=True, **kwargs):
    """Run tesseract using configured path first, then platform fallbacks."""
    commands_to_try = _get_tesseract_candidates()

    last_error = None
    for cmd_name in commands_to_try:
        try:
            cmd = [cmd_name] + args
            return subprocess.run(cmd, capture_output=capture_output, text=text, **kwargs)
        except FileNotFoundError as err:
            last_error = err

    if last_error:
        raise last_error

    raise FileNotFoundError("Tesseract executable not found")

def extract_table_number(image_path):
    """Extract C/R Table number from image header using regex"""
    try:
        result = _run_tesseract([image_path, 'stdout', '--psm', ocr.PSM_MODE])
        ocr_text = result.stdout
        
        # Try each pattern from settings
        for pattern in table_structure.TABLE_NUMBER_PATTERNS:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                table_id = match.group(1).strip()
                # Validate using settings
                if (len(table_id) >= table_structure.MIN_TABLE_NUMBER_LENGTH and 
                    len(table_id) <= table_structure.MAX_TABLE_NUMBER_LENGTH):
                    return table_id
        
        return "N/A"
        
    except Exception as e:
        return "N/A"

def ocr_extract(image_path):
    """Extract text with Tesseract"""
    try:
        result = _run_tesseract([image_path, 'stdout', '--psm', ocr.PSM_MODE, ocr.OUTPUT_FORMAT])
    except FileNotFoundError:
        print("     ✗ Tesseract not found. Install it and ensure it is in PATH.")
        if sys.platform == 'win32':
            print("     On Windows, set OCRSettings.TESSERACT_PATH in settings.py or add Tesseract to PATH.")
        return None

    return result.stdout if result.returncode == 0 else None

def parse_ocr_output(tsv_data):
    """Parse Tesseract TSV output"""
    words = []
    for line in tsv_data.strip().split('\n')[1:]:
        parts = line.split('\t')
        if len(parts) < 12:
            continue
        
        try:
            text = parts[11].strip()
            conf = float(parts[10])
            left = int(parts[6])
            top = int(parts[7])
            
            # Use confidence threshold from settings
            if text and conf > ocr.CONFIDENCE_THRESHOLD:
                words.append({'text': text, 'x': left, 'y': top})
        except:
            continue
    
    # Adaptive confidence: if very few words detected, lower threshold and retry
    if len(words) < 20:
        words = []
        lower_threshold = max(5, ocr.CONFIDENCE_THRESHOLD - 10)  # Lower by 10, min 5
        
        for line in tsv_data.strip().split('\n')[1:]:
            parts = line.split('\t')
            if len(parts) < 12:
                continue
            
            try:
                text = parts[11].strip()
                conf = float(parts[10])
                left = int(parts[6])
                top = int(parts[7])
                
                # Use lower threshold for small tables
                if text and conf > lower_threshold:
                    words.append({'text': text, 'x': left, 'y': top})
            except:
                continue
    
    return words

def group_into_rows(words):
    """Group words into rows by Y-coordinate"""
    rows_dict = {}
    for word in words:
        row_key = round(word['y'] / 20) * 20
        if row_key not in rows_dict:
            rows_dict[row_key] = []
        rows_dict[row_key].append(word)
    
    # Sort rows vertically
    rows = []
    for _, row_words in sorted(rows_dict.items()):
        row_words.sort(key=lambda w: w['x'])
        rows.append(row_words)
    
    return rows

def smart_column_detection(rows):
    """Intelligently detect column boundaries"""
    # Analyze first 5 rows to find column patterns
    x_positions = []
    for row in rows[:5]:
        x_positions.extend([w['x'] for w in row])
    
    if not x_positions:
        return []
    
    x_positions.sort()
    
    # Find clusters with dynamic threshold
    columns = []
    cluster = [x_positions[0]]
    
    for x in x_positions[1:]:
        if x - cluster[-1] < 50:  # Within 50px = same column
            cluster.append(x)
        else:
            columns.append(sum(cluster) // len(cluster))
            cluster = [x]
    
    if cluster:
        columns.append(sum(cluster) // len(cluster))
    
    return columns

def build_table(rows, columns):
    """Build structured table"""
    table = []
    
    for row_words in rows:
        if not row_words:
            continue
        
        row_data = [''] * len(columns)
        
        for word in row_words:
            # Find nearest column
            dists = [abs(word['x'] - col) for col in columns]
            col_idx = dists.index(min(dists))
            
            if row_data[col_idx]:
                row_data[col_idx] += ' ' + word['text']
            else:
                row_data[col_idx] = word['text']
        
        # Skip empty rows
        if any(cell.strip() for cell in row_data):
            table.append(row_data)
    
    return table

def clean_date_format(date_str):
    """Clean date string to only contain dd/mm/yyyy format"""
    if not date_str:
        return date_str
    
    # Remove common invalid characters
    invalid_chars = [
        '_', '—', '–', '−',  # Various dashes
        'â€"', 'â€"', 'â€"',  # UTF-8 encoding artifacts
        '‐', '‑', '‒', '―',  # Different dash types
        ' ', '\t', '\n',      # Whitespace
        ',', ';', ':',        # Punctuation
        '|', '\\',            # Other characters
    ]
    
    cleaned = date_str
    for char in invalid_chars:
        cleaned = cleaned.replace(char, '')
    
    # Keep only digits and forward slashes
    cleaned = ''.join(c for c in cleaned if c.isdigit() or c == '/')
    
    # Fix common malformed patterns
    
    # Pattern 1: DD/MMYYYY → DD/MM/YYYY (missing middle slash)
    match = re.match(r'^(\d{1,2})/(\d{2})(\d{4})$', cleaned)
    if match:
        day, month, year = match.groups()
        cleaned = f"{day}/{month}/{year}"
        return cleaned
    
    # Pattern 2: DD/MMMYYYY → DD/MM/YYYY (extra digit in month)
    match = re.match(r'^(\d{1,2})/(\d)(\d{2})(\d{4})$', cleaned)
    if match:
        day, m1, m2, year = match.groups()
        cleaned = f"{day}/{m1}{m2}/{year}"
        return cleaned
    
    # Pattern 3: DDMMYYYY → DD/MM/YYYY (no slashes at all)
    match = re.match(r'^(\d{2})(\d{2})(\d{4})$', cleaned)
    if match:
        day, month, year = match.groups()
        cleaned = f"{day}/{month}/{year}"
        return cleaned
    
    # Ensure format is dd/mm/yyyy or d/m/yyyy
    # Should have exactly 2 slashes
    if cleaned.count('/') != 2:
        return cleaned  # Return as-is if format doesn't match
    
    # Validate the date has reasonable structure
    parts = cleaned.split('/')
    if len(parts) == 3:
        day, month, year = parts
        # Day: 1-31, Month: 1-12, Year: 1900-2100
        try:
            if 1 <= int(day) <= 31 and 1 <= int(month) <= 12 and 1900 <= int(year) <= 2100:
                return cleaned
        except:
            pass
    
    return cleaned

def clean_data(table):
    """Clean OCR errors and standardize data"""
    cleaned = []
    
    for row in table:
        cleaned_row = []
        for col_idx, cell in enumerate(row):
            # Remove extra spaces
            cell = ' '.join(cell.split())
            
            # Clean date column (first column) - remove invalid characters
            if col_idx == 0:
                cell = clean_date_format(cell)
            
            # Fix common OCR errors
            cell = cell.replace(' .', '.')
            cell = cell.replace('D0', '00')
            cell = re.sub(r'(\d)\s+(\d)', r'\1\2', cell)  # Fix split numbers
            
            # Normalize number formats - replace comma with period
            # Check if it looks like a number with comma (1,17 or 1,417)
            if re.match(r'^\d+,\d+$', cell):
                cell = cell.replace(',', '.')
            
            # Clean currency - remove signs from amount columns
            cell = re.sub(r'(\d+\.?\d*)\s*[-+=]', r'\1', cell)  # Remove trailing signs
            cell = re.sub(r'[-+=]\s*(\d+\.?\d*)', r'\1', cell)  # Remove leading signs
            cell = cell.replace('=', '').replace('+', '').replace('-', '') if any(c.isdigit() for c in cell) else cell
            
            cleaned_row.append(cell)
        
        cleaned.append(cleaned_row)
    
    return cleaned

def remove_empty_columns(table):
    """Remove columns that are mostly empty"""
    if not table:
        return table
    
    num_cols = len(table[0])
    col_counts = [0] * num_cols
    
    # Count non-empty cells per column
    for row in table:
        for idx, cell in enumerate(row):
            if cell.strip():
                col_counts[idx] += 1
    
    # Keep columns with at least 20% data
    threshold = len(table) * 0.2
    keep_cols = [i for i, count in enumerate(col_counts) if count >= threshold]
    
    # Filter table
    filtered = []
    for row in table:
        filtered_row = [row[i] for i in keep_cols if i < len(row)]
        filtered.append(filtered_row)
    
    return filtered

def cleanup_table_header_and_rows(table, table_number, year_filter_value=None):
    """Clean up table: merge header rows, standardize column names, filter invalid rows"""
    if len(table) < 2:
        return table
    
    # Use standard header from settings
    standard_header = table_structure.STANDARD_HEADERS
    
    # Start with standard header
    cleaned = [standard_header]
    
    filtered_by_year = 0
    
    # Process data rows (skip any header rows)
    for row_idx, row in enumerate(table):
        # Skip if it looks like a header row
        if row_idx == 0:
            continue
            
        row_text = ' '.join(str(cell).lower() for cell in row)
        if any(keyword in row_text for keyword in table_structure.HEADER_KEYWORDS):
            continue
        
        # Ensure row has enough columns (original 7 columns)
        while len(row) < 7:
            row.append('')
        
        # Extract values based on position (from original table structure)
        # Original: [C/R Table, Date, Trans No, G/L, Doc No., Orig Amount, Acc Amount]
        # New:      [C/R Table, Date, Doc No., Orig Amount, Acc Amount]
        cr_table = str(row[0]).strip() if len(row) > 0 else table_number
        date = str(row[1]).strip() if len(row) > 1 else ''
        # Skip trans_no (row[2])
        # Skip gl_code (row[3])
        doc_no = str(row[4]).strip() if len(row) > 4 else ''
        orig_amt = str(row[5]).strip() if len(row) > 5 else ''
        acc_amt = str(row[6]).strip() if len(row) > 6 else ''
        
        # Validation using settings
        has_date = date and cleaning.DATE_REQUIRED_CHAR in date and len(date) >= cleaning.MIN_DATE_LENGTH
        has_doc_no = doc_no and len(doc_no) >= cleaning.MIN_DOC_NUMBER_LENGTH
        
        if not has_date or not has_doc_no:
            continue  # Skip invalid rows
        
        # Year filter if specified
        if year_filter_value:
            # Extract year from date
            year_match = re.search(r'(\d{4})$', date)  # 4-digit year at end
            if not year_match:
                year_match = re.search(r'/(\d{2})$', date)  # 2-digit year at end
                if year_match:
                    # Convert 2-digit to 4-digit using settings
                    year_2digit = int(year_match.group(1))
                    if year_2digit <= year_filter.TWO_DIGIT_YEAR_CUTOFF:
                        year_str = str(year_filter.DEFAULT_CENTURY + year_2digit)
                    else:
                        year_str = str(year_filter.ALTERNATIVE_CENTURY + year_2digit)
                else:
                    year_str = None
            else:
                year_str = year_match.group(1)
            
            # Filter by year
            if year_str != year_filter_value:
                filtered_by_year += 1
                continue
        
        # Create cleaned row (only selected columns)
        cleaned_row = [cr_table, date, doc_no, orig_amt, acc_amt]
        cleaned.append(cleaned_row)
    
    if year_filter_value and filtered_by_year > 0:
        print(f"     Filtered out {filtered_by_year} rows not matching year {year_filter_value}")
    
    return cleaned

def fill_missing_data(table):
    """Intelligently fill missing data and fix OCR errors"""
    if len(table) < 2:
        return table
    
    # Identify columns
    header = table[0] if table else []
    header_lower = [h.lower() for h in header]
    
    # Find column indices
    doc_col = next((i for i, h in enumerate(header_lower) if 'document' in h or 'number' in h), -1)
    amount_cols = [i for i, h in enumerate(header_lower) if 'amount' in h]
    date_col = next((i for i, h in enumerate(header_lower) if 'date' in h), 0)
    trans_col = next((i for i, h in enumerate(header_lower) if 'trans' in h and 'no' in h), 1)
    
    # B674 is the standard document number
    most_common_doc = 'B674'
    
    # Fill and correct
    filled = []
    for row_idx, row in enumerate(table):
        if row_idx == 0:  # Skip header
            filled.append(row)
            continue
        
        filled_row = list(row)
        
        # Fix Trans No. OCR errors (90xxx → 00xxx, 60xxx → 00xxx)
        if trans_col >= 0 and trans_col < len(filled_row) and filled_row[trans_col]:
            trans_no = filled_row[trans_col]
            if trans_no.startswith('90') or trans_no.startswith('60'):
                if len(trans_no) == 5 and trans_no[2:].isdigit():
                    filled_row[trans_col] = '00' + trans_no[2:]
        
        # Fix OCR errors in document column (BB?4, BBb74, BB74 -> B674)
        if doc_col >= 0 and doc_col < len(filled_row) and filled_row[doc_col]:
            doc_val = filled_row[doc_col]
            if 'BB' in doc_val or 'Bb' in doc_val:
                filled_row[doc_col] = 'B674'
        
        # Fill missing document numbers
        if doc_col >= 0 and doc_col < len(filled_row):
            if not filled_row[doc_col] and len(filled_row) > 2 and filled_row[2]:
                filled_row[doc_col] = most_common_doc
        
        # Fill missing amounts
        if len(amount_cols) >= 2:
            orig_col, acct_col = amount_cols[0], amount_cols[1]
            if orig_col < len(filled_row) and acct_col < len(filled_row):
                if filled_row[orig_col] and not filled_row[acct_col]:
                    filled_row[acct_col] = filled_row[orig_col]
                elif not filled_row[orig_col] and filled_row[acct_col]:
                    filled_row[orig_col] = filled_row[acct_col]
        
        # Fill missing date
        if date_col < len(filled_row) and not filled_row[date_col] and row_idx > 1:
            prev_row = filled[row_idx - 1]
            if date_col < len(prev_row) and prev_row[date_col]:
                filled_row[date_col] = prev_row[date_col]
        
        filled.append(filled_row)
    
    return filled

def remove_empty_rows(table):
    """Remove rows that are completely empty or contain only whitespace/special characters"""
    cleaned = []
    
    for row in table:
        # Check if row has any meaningful content
        meaningful_cells = 0
        
        for cell in row:
            # Remove whitespace and special characters for checking
            cell_clean = cell.strip().replace('_', '').replace('—', '').replace('–', '').replace('-', '').replace(',', '')
            # Check if cell has alphanumeric content
            if cell_clean and any(c.isalnum() for c in cell_clean):
                meaningful_cells += 1
        
        # Keep row only if it has at least 2 meaningful cells (avoid single-word garbage)
        if meaningful_cells >= 2:
            cleaned.append(row)
    
    return cleaned

def find_header_row(table):
    """Identify header row"""
    keywords = ['date', 'trans', 'document', 'amount', 'number', 'code']
    
    for idx, row in enumerate(table[:5]):
        row_text = ' '.join(row).lower()
        if sum(1 for kw in keywords if kw in row_text) >= 2:
            return idx
    
    return 0

def save_csv(table, output_path):
    """Save as CSV with UTF-8 encoding"""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(table)

def generate_excel_code(table, script_path):
    """Generate Python code to create formatted Excel"""
    code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# Table data
data = {repr(table)}

# Create workbook
wb = Workbook()
ws = wb.active
ws.title = "Extracted Table"

# Define styles
header_font = Font(bold=True, color='FFFFFF', size=11)
header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
header_align = Alignment(horizontal='center', vertical='center')

data_font = Font(name='Arial', size=10)
data_align = Alignment(horizontal='left', vertical='center')
number_align = Alignment(horizontal='right', vertical='center')

border = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)

# Write data
for r_idx, row in enumerate(data, 1):
    for c_idx, value in enumerate(row, 1):
        cell = ws.cell(row=r_idx, column=c_idx, value=value)
        cell.border = border
        
        if r_idx == 1:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
        else:
            cell.font = data_font
            # Right-align numbers
            if value and any(c.isdigit() for c in str(value)):
                cell.alignment = number_align
            else:
                cell.alignment = data_align

# Auto-adjust column widths
for col in ws.columns:
    max_length = max(len(str(cell.value or '')) for cell in col)
    col_letter = col[0].column_letter
    ws.column_dimensions[col_letter].width = min(max_length + 2, 40)

# Freeze header row
ws.freeze_panes = 'A2'

# Save
wb.save('extracted_table.xlsx')
print("Excel file created: extracted_table.xlsx")
'''
    
    # Write with UTF-8 encoding to handle special characters on Windows
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(code)

def extract_with_template(image_path, year_filter_value=None):
    """
    Template-based extraction for small tables
    Uses regex patterns to extract data from OCR text directly
    More reliable for tables with few rows where column detection fails
    """
    # Get raw OCR text
    try:
        result = _run_tesseract([image_path, 'stdout', '--psm', '6'], check=False, encoding='utf-8')
        text = result.stdout

        # DEBUG: Print OCR output length and preview
        if logging.SHOW_PROGRESS:
            lines_with_2025 = [l for l in text.split('\n') if '2025' in l]
            print(f"     DEBUG: OCR text length: {len(text)} chars")
            print(f"     DEBUG: Lines with 2025: {len(lines_with_2025)}")
            
    except Exception as e:
        if logging.SHOW_PROGRESS:
            print(f"     ⚠ Template OCR failed: {e}")
        return [], "N/A"
    
    if not text:
        return [], "N/A"
    
    # Extract C/R Table number
    table_match = re.search(r'C/R\s+Table\s+([A-Z0-9]+)', text, re.IGNORECASE)
    table_number = table_match.group(1) if table_match else "N/A"
    
    # Pattern to match data rows:
    # [underscore/dash] DD/MM/YYYY NNNNN NNNNNNNNNN XXXX NN.NN- NN.NN-
    
    # Normalize line endings (Windows uses \r\n, Unix uses \n)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove extra newlines to make pattern matching easier
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # Enhanced pattern to match more dash/underscore variations
    # Include: _ (underscore), - (hyphen), — (em dash U+2014), – (en dash U+2013)
    # Made more tolerant of OCR errors in amounts (letters, commas, spaces)
    # Note: Includes both 't' and 'T' as OCR sometimes misreads 7 as t
    pattern = r'[_\-—–]\s*(\d{1,2}/\d{1,2}/\d{4})\s+(\d{5})\s+(\d{10})\s+([A-Z0-9]+)\s+([\d.,\silIoOaeftT]+[\-=]?)\s+([\d.,\silIoOaeftT]+[\-=]?)'
    
    rows = []
    match_count = 0
    filtered_count = 0
    
    for match in re.finditer(pattern, text):
        match_count += 1
        date = match.group(1)
        trans_no = match.group(2)
        gl_code = match.group(3)
        doc_no = match.group(4)
        orig_amt = match.group(5)
        acc_amt = match.group(6)
        
        # Apply year filter if specified
        if year_filter_value:
            year_match = re.search(r'(\d{4})$', date)
            if year_match and year_match.group(1) != year_filter_value:
                filtered_count += 1
                continue
        
        # Clean amounts (remove trailing minus/equals and fix OCR errors)
        def clean_amount(amt):
            # Remove trailing - or =
            amt = amt.rstrip('-=')
            # Fix common OCR errors
            amt = amt.replace(',', '.')  # Comma to period
            amt = amt.replace('i', '1')  # lowercase i to 1
            amt = amt.replace('I', '1')  # uppercase I to 1
            amt = amt.replace('l', '1')  # lowercase l to 1
            amt = amt.replace('o', '0')  # lowercase o to 0
            amt = amt.replace('O', '0')  # uppercase O to 0
            amt = amt.replace('a', '1')  # lowercase a to 1
            amt = amt.replace('e', '0')  # lowercase e to 0
            amt = amt.replace('f', '1')  # lowercase f to 1
            amt = amt.replace('t', '')   # lowercase t (OCR error for 7)
            amt = amt.replace('T', '')   # uppercase T
            amt = amt.replace(' ', '')   # Remove spaces
            # Keep only digits and periods
            amt = ''.join(c for c in amt if c.isdigit() or c == '.')
            return amt
        
        orig_amt = clean_amount(orig_amt)
        acc_amt = clean_amount(acc_amt)
        
        # Skip if amounts are invalid after cleaning
        if not orig_amt or not acc_amt:
            filtered_count += 1
            continue
        
        rows.append([table_number, date, doc_no, orig_amt, acc_amt])
    
    # DEBUG: Print matching stats
    if logging.SHOW_PROGRESS:
        print(f"     DEBUG: Pattern matched: {match_count} rows")
        print(f"     DEBUG: Year filtered out: {filtered_count} rows")
        print(f"     DEBUG: Empty after cleaning: {match_count - filtered_count - len(rows)} rows")
        print(f"     DEBUG: Rows kept: {len(rows)}")
        if len(rows) > 0:
            print(f"     DEBUG: Sample row: {rows[0]}")
    
    return rows, table_number


def should_use_template_extraction(words, rows):
    """
    Decide if template-based extraction should be used
    
    IMPORTANT: Template extraction is more reliable than column detection
    for this specific table format, so we use it for ALL images.
    
    Template extraction correctly handles:
    - OCR errors in amounts (i, l, o, a, f, T)
    - Closely-spaced duplicate rows
    - Inconsistent column spacing
    - Small tables
    
    Returns True for all cases to ensure maximum accuracy.
    """
    # Always use template extraction for this table format
    return True
    
    # Original logic (commented out):
    # if len(words) < 50:
    #     return True
    # if len(rows) < 8:
    #     return True
    # return False


def main(
    input_image=None,
    year_filter_value=None,
    use_preprocessing=True,
    use_binarization=True,
    mask_top_ratio=None,
    mask_bottom_ratio=None,
):
    import time
    start_time = time.time()
    
    print("=" * logging.CONSOLE_WIDTH)
    print(" " * 15 + "OCR TABLE EXTRACTION TO EXCEL")
    print("=" * logging.CONSOLE_WIDTH)
    
    # Paths - using settings
    if input_image is None:
        input_image = paths.DEFAULT_INPUT_IMAGE
    
    if year_filter_value:
        print(f"\n*** YEAR FILTER: Only extracting data from year {year_filter_value} ***\n")
    
    preprocessed = paths.TEMP_PREPROCESSED_IMAGE
    csv_output = paths.DEFAULT_OUTPUT_CSV
    excel_generator = paths.EXCEL_GENERATOR_SCRIPT
    
    # Process
    if use_preprocessing:
        print("\n[1/7] Preprocessing image...")
        ocr_image = preprocess_image(
            input_image,
            preprocessed,
            use_binarization=use_binarization,
            mask_top_ratio=mask_top_ratio,
            mask_bottom_ratio=mask_bottom_ratio,
        )
        preview_path = save_masked_preview(ocr_image, input_image)

        # Show absolute path for debugging
        import os
        abs_path = os.path.abspath(preprocessed)
        print(f"     Preprocessed image saved to: {abs_path}")
        if preview_path:
            print(f"     Masked preview saved to: {os.path.abspath(preview_path)}")
        print("     ✓ Complete")
    else:
        print("\n[1/7] Preprocessing image...")
        print("     Preprocessing disabled (--no-preprocess)")
        ocr_image = input_image
        preview_path = None
        print("     ✓ Using original image for OCR")
    
    # Extract C/R Table number from original image (before preprocessing)
    print("\n[2/7] Extracting C/R Table number...")
    table_number = extract_table_number(input_image)
    print(f"     ✓ C/R Table: {table_number}")
    
    print("\n[3/7] Running OCR...")
    tsv_data = ocr_extract(ocr_image)
    if not tsv_data:
        print("     ✗ OCR failed")
        return
    print("     ✓ Text extracted")
    
    print("\n[4/7] Parsing OCR data...")
    words = parse_ocr_output(tsv_data)
    print(f"     ✓ Found {len(words)} text elements")
    
    print("\n[5/7] Grouping into rows...")
    rows = group_into_rows(words)
    print(f"     ✓ Grouped into {len(rows)} rows")
    
    # Check if we should use template-based extraction for small tables
    if should_use_template_extraction(words, rows):
        print("\n     ⚠ Small table detected - using template-based extraction")
        template_rows, template_table_number = extract_with_template(ocr_image, year_filter_value)
        
        if template_rows:
            # Use template results
            table_number = template_table_number
            
            # Build table with standard headers
            table = [['C/R Table', 'Date', 'Doc No.', 'Orig Amount', 'Acc Amount']]
            table.extend(template_rows)
            
            print(f"     ✓ Template extracted {len(template_rows)} rows")
            
            # Skip to output section
            print(f"     ✓ Table: {len(table)} rows × {len(table[0])} columns")
            
            print("\n[8/8] Exporting...")
            save_csv(table, csv_output)
            generate_excel_code(table, excel_generator)
            
            # Show absolute paths
            import os
            print(f"     ✓ CSV: {os.path.abspath(csv_output)}")
            print(f"     ✓ Excel generator: {os.path.abspath(excel_generator)}")
            
            # Summary
            print("\n" + "=" * 70)
            print("EXTRACTION COMPLETE!")
            print("=" * 70)
            print("\nFiles created:")
            print(f"  1. CSV file (ready to open in Excel): {csv_output}")
            print(f"  2. Python script for .xlsx format:    {excel_generator}")
            
            print("\nTo create formatted .xlsx file:")
            print("  $ pip install openpyxl")
            print(f"  $ python {excel_generator}")
            
            # Preview
            print("\n" + "=" * 70)
            print("DATA PREVIEW:")
            print("=" * 70)
            for idx, row in enumerate(table[:12], 1):
                row_str = ' │ '.join(f"{cell:15s}" for cell in row[:6])
                print(f"{idx:2d}. {row_str}")
            
            if len(table) > 12:
                print(f"... ({len(table) - 12} more rows)")
            
            # Timing information
            end_time = time.time()
            elapsed = end_time - start_time
            if logging.SHOW_TIMING:
                print("\n" + "=" * 70)
                print(f"Processing time: {elapsed:.2f} seconds")
                print(f"Rows extracted: {len(table) - 1}")
                print("=" * 70)
            
            return elapsed, len(table) - 1
    
    # Continue with normal column-based extraction
    print("\n[6/7] Detecting columns...")
    columns = smart_column_detection(rows)
    print(f"     ✓ Detected {len(columns)} columns")
    
    print("\n[6/7] Building table...")
    table = build_table(rows, columns)
    table = clean_data(table)
    table = remove_empty_columns(table)
    
    # Move header to top BEFORE fill_missing_data
    header_idx = find_header_row(table)
    if header_idx > 0:
        table = table[header_idx:]
    
    # Add C/R Table column to header and all rows
    if table:
        # Insert "C/R Table" as first column in header
        table[0].insert(0, 'C/R Table')
        
        # Add table number to all data rows
        for row_idx in range(1, len(table)):
            table[row_idx].insert(0, table_number)
    
    table = fill_missing_data(table)  # Add intelligent gap filling
    table = remove_empty_rows(table)  # Remove empty rows
    
    # Clean up headers and filter invalid rows
    print(f"     Initial: {len(table)} rows")
    table = cleanup_table_header_and_rows(table, table_number, year_filter_value)
    print(f"     After cleanup: {len(table)} rows (including header)")
    
    # Fallback: If normal extraction yielded very few rows, try template
    if len(table) <= 1:  # Only header or empty
        print(f"     ⚠ Few rows detected - trying template-based extraction as fallback")
        template_rows, template_table_number = extract_with_template(ocr_image, year_filter_value)
        
        if template_rows and len(template_rows) > 0:
            # Use template results
            table_number = template_table_number
            table = [['C/R Table', 'Date', 'Doc No.', 'Orig Amount', 'Acc Amount']]
            table.extend(template_rows)
            print(f"     ✓ Template extracted {len(template_rows)} rows")
    
    print(f"     Filtered out rows without Date or Doc No.")
    
    print(f"     ✓ Table: {len(table)} rows × {len(table[0])} columns")
    
    print("\n[8/8] Exporting...")
    save_csv(table, csv_output)
    generate_excel_code(table, excel_generator)
    
    # Show absolute paths
    import os
    print(f"     ✓ CSV: {os.path.abspath(csv_output)}")
    print(f"     ✓ Excel generator: {os.path.abspath(excel_generator)}")
    
    # Summary
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE!")
    print("=" * 70)
    print("\nFiles created:")
    print(f"  1. CSV file (ready to open in Excel): {csv_output}")
    print(f"  2. Python script for .xlsx format:    {excel_generator}")
    
    print("\nTo create formatted .xlsx file:")
    print("  $ pip install openpyxl")
    print(f"  $ python {excel_generator}")
    
    # Preview
    print("\n" + "=" * 70)
    print("DATA PREVIEW:")
    print("=" * 70)
    for idx, row in enumerate(table[:12], 1):
        row_str = ' │ '.join(f"{cell:15s}" for cell in row[:6])
        print(f"{idx:2d}. {row_str}")
    
    if len(table) > 12:
        print(f"... ({len(table) - 12} more rows)")
    
    # Timing information
    end_time = time.time()
    elapsed = end_time - start_time
    if logging.SHOW_TIMING:
        print("\n" + "=" * 70)
        print(f"Processing time: {elapsed:.2f} seconds")
        print(f"Rows extracted: {len(table) - 1}")  # Exclude header
        print("=" * 70)
    
    return elapsed, len(table) - 1  # Return timing and row count

def batch_process_images(
    image_folder=None,
    output_csv=None,
    year_filter_value=None,
    use_preprocessing=True,
    use_binarization=True,
    mask_top_ratio=None,
    mask_bottom_ratio=None,
):
    """Process all images in a folder and combine results into single CSV"""
    import glob
    import os
    import time
    
    # Disable verbose mode for batch processing
    original_verbose = logging.VERBOSE_MODE if hasattr(logging, 'VERBOSE_MODE') else True
    if hasattr(logging, 'VERBOSE_MODE'):
        logging.VERBOSE_MODE = False
    
    print("=" * logging.CONSOLE_WIDTH)
    print(" " * 15 + "BATCH OCR PROCESSING")
    print("=" * logging.CONSOLE_WIDTH)
    
    # Use defaults from settings if not provided
    if image_folder is None:
        image_folder = paths.DEFAULT_INPUT_FOLDER
        print(f"\nUsing default input folder: {image_folder}")
    
    if output_csv is None:
        output_csv = paths.DEFAULT_BATCH_OUTPUT
        print(f"Using default output file: {output_csv}")
    
    if year_filter_value:
        print(f"\n*** YEAR FILTER: Only extracting data from year {year_filter_value} ***\n")
    
    # Find all PNG images in folder
    image_pattern = os.path.join(image_folder, '*.png')
    image_files = sorted(glob.glob(image_pattern))
    
    if not image_files:
        print(f"✗ No PNG images found in: {image_folder}")
        return
    
    print(f"Found {len(image_files)} images to process:\n")
    for img in image_files:
        print(f"  - {os.path.basename(img)}")
    
    print("\n" + "=" * 70)
    
    # Collect all data rows (skip headers from each file)
    all_rows = []
    header_written = False
    
    # Track statistics for each image
    processing_stats = []
    
    for idx, image_path in enumerate(image_files, 1):
        image_name = os.path.basename(image_path)
        print(f"\n[{idx}/{len(image_files)}] Processing: {image_name}")
        print("-" * 70)
        
        # Start timing for this image
        img_start_time = time.time()
        
        try:
            # Create temporary output path
            temp_csv = f'temp_extract_{idx}.csv'
            
            # Extract table from this image
            input_image = image_path
            preprocessed = f'temp_preprocessed_{idx}.png'
            csv_output = temp_csv
            excel_generator = 'create_excel.py'
            
            # Run extraction (simplified inline version)
            if use_preprocessing:
                ocr_image = preprocess_image(
                    input_image,
                    preprocessed,
                    use_binarization=use_binarization,
                    mask_top_ratio=mask_top_ratio,
                    mask_bottom_ratio=mask_bottom_ratio,
                )
                preview_path = save_masked_preview(ocr_image, input_image)
                if preview_path:
                    print(f"     Masked preview: {os.path.abspath(preview_path)}")
            else:
                print("     Preprocessing disabled (--no-preprocess)")
                ocr_image = input_image
            table_number = extract_table_number(input_image)
            print(f"     C/R Table: {table_number}")
            
            tsv_data = ocr_extract(ocr_image)
            if not tsv_data:
                print(f"     ✗ OCR failed for {image_name}")
                img_elapsed = time.time() - img_start_time
                processing_stats.append({
                    'image': image_name,
                    'rows': 0,
                    'time': img_elapsed,
                    'status': 'FAILED'
                })
                continue
            
            words = parse_ocr_output(tsv_data)
            rows = group_into_rows(words)
            
            # Check if small table - use template extraction
            if should_use_template_extraction(words, rows):
                template_rows, template_table_number = extract_with_template(ocr_image, year_filter_value)
                if template_rows:
                    # Build table with template results
                    table = [['C/R Table', 'Date', 'Doc No.', 'Orig Amount', 'Acc Amount']]
                    table.extend(template_rows)
                    table_number = template_table_number
                else:
                    # Template failed, try normal extraction
                    columns = smart_column_detection(rows)
                    table = build_table(rows, columns)
                    table = clean_data(table)
                    table = remove_empty_columns(table)
                    header_idx = find_header_row(table)
                    if header_idx > 0:
                        table = table[header_idx:]
                    if table:
                        table[0].insert(0, 'C/R Table')
                        for row_idx in range(1, len(table)):
                            table[row_idx].insert(0, table_number)
                    table = fill_missing_data(table)
                    table = remove_empty_rows(table)
                    table = cleanup_table_header_and_rows(table, table_number, year_filter_value)
            else:
                # Normal column-based extraction
                columns = smart_column_detection(rows)
                table = build_table(rows, columns)
                table = clean_data(table)
                table = remove_empty_columns(table)
                
                header_idx = find_header_row(table)
                if header_idx > 0:
                    table = table[header_idx:]
                
                if table:
                    table[0].insert(0, 'C/R Table')
                    for row_idx in range(1, len(table)):
                        table[row_idx].insert(0, table_number)
                
                table = fill_missing_data(table)
                table = remove_empty_rows(table)
                table = cleanup_table_header_and_rows(table, table_number, year_filter_value)
                
                # Fallback: If normal extraction yielded very few rows, try template
                if len(table) <= 1:  # Only header or empty
                    template_rows, template_table_number = extract_with_template(ocr_image, year_filter_value)
                    if template_rows and len(template_rows) > 0:
                        table_number = template_table_number
                        table = [['C/R Table', 'Date', 'Doc No.', 'Orig Amount', 'Acc Amount']]
                        table.extend(template_rows)
            
            # Add rows to combined list (skip header after first file)
            if not header_written:
                all_rows.extend(table)  # Include header from first file
                header_written = True
            else:
                all_rows.extend(table[1:])  # Skip header from subsequent files
            
            # Calculate elapsed time for this image
            img_elapsed = time.time() - img_start_time
            row_count = len(table) - 1  # Exclude header
            
            print(f"     ✓ Extracted {row_count} rows in {img_elapsed:.2f}s")
            
            # Store stats
            processing_stats.append({
                'image': image_name,
                'rows': row_count,
                'time': img_elapsed,
                'status': 'OK'
            })
            
            # Cleanup temp files
            try:
                if os.path.exists(preprocessed):
                    os.remove(preprocessed)
                if os.path.exists(temp_csv):
                    os.remove(temp_csv)
            except:
                pass
            
        except Exception as e:
            img_elapsed = time.time() - img_start_time
            print(f"     ✗ Error processing {image_name}: {e}")
            processing_stats.append({
                'image': image_name,
                'rows': 0,
                'time': img_elapsed,
                'status': 'ERROR'
            })
            continue
    
    # Save combined results
    if all_rows:
        save_csv(all_rows, output_csv)
        
        print("\n" + "=" * 70)
        print("BATCH PROCESSING COMPLETE!")
        print("=" * 70)
        print(f"\nCombined results saved to: {output_csv}")
        print(f"Total rows extracted: {len(all_rows)-1} (excluding header)")
        print(f"Total images processed: {len(image_files)}")
        
        # Processing summary table
        if processing_stats:
            print("\n" + "=" * 70)
            print("PROCESSING SUMMARY:")
            print("=" * 70)
            
            # Filter stats - only show images with rows > 0
            successful_stats = [s for s in processing_stats if s['rows'] > 0]
            failed_stats = [s for s in processing_stats if s['rows'] == 0]
            
            if successful_stats:
                # Table header
                print(f"\n{'Image Name':<35} {'Rows':>8} {'Time (s)':>10} {'Status':>10}")
                print("-" * 70)
                
                # Table rows (only successful extractions)
                total_rows = 0
                total_success_time = 0.0
                
                for stat in successful_stats:
                    print(f"{stat['image']:<35} {stat['rows']:>8} {stat['time']:>10.2f} {'✓':>10}")
                    total_rows += stat['rows']
                    total_success_time += stat['time']
                
                # Calculate totals for ALL images (including failures)
                total_time_all = sum(s['time'] for s in processing_stats)
                total_images = len(processing_stats)
                avg_time_all = total_time_all / total_images if total_images > 0 else 0
                avg_rows = total_rows / len(successful_stats) if successful_stats else 0
                
                # Summary statistics
                print("-" * 70)
                print(f"{'TOTAL:':<35} {total_rows:>8} {total_time_all:>10.2f}")
                print(f"{'AVERAGE:':<35} {avg_rows:>8.1f} {avg_time_all:>10.2f}")
            
            # Show summary line
            success_count = len(successful_stats)
            total_count = len(processing_stats)
            print(f"\nSuccess: {success_count}/{total_count} images ({100*success_count/total_count:.1f}%)")
            
            # Show failed images if any (brief summary)
            if failed_stats:
                failed_time = sum(s['time'] for s in failed_stats)
                print(f"Failed: {len(failed_stats)} images (0 rows extracted, {failed_time:.2f}s wasted)")
                if len(failed_stats) <= 5:
                    # Show names if only a few failures
                    for stat in failed_stats:
                        print(f"  ✗ {stat['image']} ({stat['time']:.2f}s)")
                else:
                    # Just count if many failures
                    print(f"  (See processing log above for details)")
        
        # Show preview
        print("\n" + "=" * 70)
        print("DATA PREVIEW:")
        print("=" * 70)
        for idx, row in enumerate(all_rows[:10], 1):
            row_str = ' │ '.join(f"{str(cell):15s}" for cell in row[:6])
            print(f"{idx:2d}. {row_str}")
        
        if len(all_rows) > 10:
            print(f"... ({len(all_rows) - 10} more rows)")
    else:
        print("\n✗ No data extracted from any images")
    
    # Restore verbose mode
    if hasattr(logging, 'VERBOSE_MODE'):
        logging.VERBOSE_MODE = original_verbose


def _parse_cli_float_option(argv, option_name):
    """Parse float value after a CLI option."""
    if option_name not in argv:
        return None

    idx = argv.index(option_name)
    if len(argv) <= idx + 1:
        raise ValueError(f"{option_name} requires a numeric value")

    try:
        return float(argv[idx + 1])
    except ValueError as exc:
        raise ValueError(f"{option_name} must be a number") from exc


def _parse_mask_ratio(percent_value, option_name):
    """Convert mask percentage (0-100) to ratio (0-1)."""
    if percent_value is None:
        return None
    if percent_value < 0.0 or percent_value > 100.0:
        raise ValueError(f"{option_name} must be between 0 and 100")
    return percent_value / 100.0

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    if '--help' in sys.argv or '-h' in sys.argv:
        print(f"""
OCR Table Extraction Tool - Version 4.3

USAGE:

1. Single Image:
   python extract.py image.png
   python extract.py image.png --year 2020

2. Batch Processing:
   python extract.py --batch folder_path output.csv
   python extract.py --batch folder_path output.csv --year 2020
   
3. Batch with Defaults (uses settings.py):
   python extract.py --batch
   python extract.py --batch --year 2020
   python extract.py --batch output.csv --year 2020

OPTIONS:
   --year YYYY          Filter results to only include specified year
   --batch              Process all PNG images in a folder
   --no-preprocess      Disable image preprocessing/masking before OCR
   --grayscale-only     Disable binarization and keep grayscale image
   --mask-top PERCENT   Mask top percentage (0-100, default from settings)
   --mask-bottom PERCENT Mask bottom percentage (0-100, default from settings)
   --help, -h           Show this help message

DEFAULT SETTINGS (configured in settings.py):
   Input folder:  {paths.DEFAULT_INPUT_FOLDER}
   Output file:   {paths.DEFAULT_BATCH_OUTPUT}
   Input image:   {paths.DEFAULT_INPUT_IMAGE}

EXAMPLES:

   # Single image
   python extract.py frame_0004.png

   # Single image with year filter
   python extract.py frame_0004.png --year 2020

   # Batch process with explicit paths
   python extract.py --batch ./images combined_output.csv

   # Batch process with defaults from settings.py
   python extract.py --batch

   # Batch process with year filter (using defaults)
   python extract.py --batch --year 2020

   # Batch with custom output but default input folder
   python extract.py --batch my_output.csv --year 2020
        """)
        sys.exit(0)
    
    # Check for batch mode
    if '--batch' in sys.argv:
        batch_idx = sys.argv.index('--batch')
        
        # Check if folder path is provided
        folder_path = None
        output_file = None
        
        # Try to get folder and output from arguments
        if len(sys.argv) > batch_idx + 1:
            next_arg = sys.argv[batch_idx + 1]
            # If next arg is not another flag, it's the folder path
            if not next_arg.startswith('--'):
                folder_path = next_arg
                # Try to get output file
                if len(sys.argv) > batch_idx + 2:
                    potential_output = sys.argv[batch_idx + 2]
                    if not potential_output.startswith('--'):
                        output_file = potential_output
        
        # Use defaults from settings if not provided
        if folder_path is None:
            print(f"No folder specified, using default from settings: {paths.DEFAULT_INPUT_FOLDER}")
        
        if output_file is None:
            print(f"No output file specified, using default from settings: {paths.DEFAULT_BATCH_OUTPUT}")
        
        # Check for year filter
        year_filter_value = None
        if '--year' in sys.argv:
            year_idx = sys.argv.index('--year')
            if len(sys.argv) > year_idx + 1:
                year_filter_value = sys.argv[year_idx + 1]
        
        use_preprocessing = '--no-preprocess' not in sys.argv
        use_binarization = '--grayscale-only' not in sys.argv

        try:
            mask_top_ratio = _parse_mask_ratio(_parse_cli_float_option(sys.argv, '--mask-top'), '--mask-top')
            mask_bottom_ratio = _parse_mask_ratio(_parse_cli_float_option(sys.argv, '--mask-bottom'), '--mask-bottom')
        except ValueError as e:
            print(f"✗ {e}")
            sys.exit(1)

        batch_process_images(
            folder_path,
            output_file,
            year_filter_value,
            use_preprocessing,
            use_binarization,
            mask_top_ratio,
            mask_bottom_ratio,
        )
    
    else:
        # Single image mode
        year_filter = None
        if '--year' in sys.argv:
            year_idx = sys.argv.index('--year')
            if len(sys.argv) > year_idx + 1:
                year_filter = sys.argv[year_idx + 1]
        
        # Get image path
        image_path = None
        for arg in sys.argv[1:]:
            if not arg.startswith('--') and arg not in [year_filter]:
                image_path = arg
                break
        
        if image_path:
            print(f"Using custom image: {image_path}")
            use_preprocessing = '--no-preprocess' not in sys.argv
            use_binarization = '--grayscale-only' not in sys.argv

            try:
                mask_top_ratio = _parse_mask_ratio(_parse_cli_float_option(sys.argv, '--mask-top'), '--mask-top')
                mask_bottom_ratio = _parse_mask_ratio(_parse_cli_float_option(sys.argv, '--mask-bottom'), '--mask-bottom')
            except ValueError as e:
                print(f"✗ {e}")
                sys.exit(1)

            main(image_path, year_filter, use_preprocessing, use_binarization, mask_top_ratio, mask_bottom_ratio)
        else:
            use_preprocessing = '--no-preprocess' not in sys.argv
            use_binarization = '--grayscale-only' not in sys.argv

            try:
                mask_top_ratio = _parse_mask_ratio(_parse_cli_float_option(sys.argv, '--mask-top'), '--mask-top')
                mask_bottom_ratio = _parse_mask_ratio(_parse_cli_float_option(sys.argv, '--mask-bottom'), '--mask-bottom')
            except ValueError as e:
                print(f"✗ {e}")
                sys.exit(1)

            main(None, year_filter, use_preprocessing, use_binarization, mask_top_ratio, mask_bottom_ratio)
