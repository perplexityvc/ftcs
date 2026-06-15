"""
OCR Table Extraction Settings
Version 4.2
All configurable parameters in one place
"""

import os

# ============================================================================
# OCR SETTINGS
# ============================================================================

class OCRSettings:
    """OCR extraction settings"""
    
    # Tesseract OCR confidence threshold (0-100)
    # Lower = more text captured but may include noise
    # Higher = cleaner but may miss faint text
    CONFIDENCE_THRESHOLD = 15
    
    # Tesseract page segmentation mode
    # 6 = Assume a single uniform block of text
    PSM_MODE = '6'
    
    # OCR engine mode
    # 3 = Default (based on what is available)
    # 0 = Legacy engine only
    # 1 = Neural nets LSTM engine only
    # 2 = Legacy + LSTM engines
    OCR_ENGINE_MODE = 3
    
    # OCR output format
    OUTPUT_FORMAT = 'tsv'  # Tab-separated values with positioning data

    # Optional explicit Tesseract executable path.
    # Leave empty to use PATH lookup.
    # Windows examples:
    #   TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    #   TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR'  # directory also supported
    TESSERACT_PATH = ''


# ============================================================================
# IMAGE PREPROCESSING SETTINGS
# ============================================================================

class PreprocessingSettings:
    """Image preprocessing settings"""
    
    # PIL/Pillow threshold value (0-255)
    # 122 is approximately 48% of 255
    # Lower = darker threshold (more black pixels)
    # Higher = lighter threshold (more white pixels)
    PIL_THRESHOLD = 122
    
    # Contrast enhancement factor (1.0 = no change)
    # Values > 1.0 increase contrast
    # Values < 1.0 decrease contrast
    CONTRAST_ENHANCEMENT = 1.2
    
    # Sharpening filter
    # True = apply sharpening (recommended for OCR)
    # False = no sharpening
    APPLY_SHARPENING = True

    # Binarization mode
    # True = threshold to black/white before OCR
    # False = keep grayscale image
    APPLY_BINARIZATION = True

    # Vertical masking before OCR
    # Top and bottom portions are blacked out on preprocessed images
    APPLY_VERTICAL_MASK = True
    MASK_TOP_RATIO = 0.33
    MASK_BOTTOM_RATIO = 0.15

    # Save masked/preprocessed preview images for manual inspection
    SAVE_MASKED_PREVIEW = True
    MASKED_PREVIEW_DIR = 'masked_inspection'

    # Masked preview color mode
    # False = save preview in original color (default, for visual inspection)
    # True  = save preview in grayscale
    MASKED_PREVIEW_GRAYSCALE = False

    # Draw OCR bounding boxes and confidence on masked preview image
    # Boxes are color-coded: green >= 80%, yellow 50-79%, red < 50%
    MASKED_PREVIEW_SHOW_BBOXES = True


# ============================================================================
# TABLE DETECTION SETTINGS
# ============================================================================

class TableDetectionSettings:
    """Table structure detection settings"""
    
    # Row grouping - Y-coordinate tolerance (pixels)
    # Words within this vertical distance are grouped into same row
    # Reduced from 20 to 15 to better detect closely-spaced rows
    ROW_GROUPING_TOLERANCE = 15
    
    # Column detection - X-coordinate tolerance (pixels)
    # Words within this horizontal distance are grouped into same column
    COLUMN_GROUPING_TOLERANCE = 45
    
    # Minimum number of rows to consider valid table
    MIN_TABLE_ROWS = 1  # Reduced from 2 to handle small tables
    
    # Empty column removal threshold (percentage)
    # Remove columns with more than this percentage of empty cells
    EMPTY_COLUMN_THRESHOLD = 0.20  # 20%


# ============================================================================
# DATA CLEANING SETTINGS
# ============================================================================

class CleaningSettings:
    """Data cleaning and validation settings"""
    
    # Characters to remove from dates
    DATE_CHARS_TO_REMOVE = [
        '_', '—', '–', '−',           # Various dashes
        'â€"', 'â€"', 'â€"',           # UTF-8 encoding artifacts
        '‐', '‑', '‒', '―',           # Different dash types
        ' ', '\t', '\n',              # Whitespace
        ',', ';', ':',                # Punctuation
        '|', '\\',                    # Other characters
    ]
    
    # Date format validation
    DATE_FORMAT = r'^\d{1,2}/\d{1,2}/\d{4}$'  # dd/mm/yyyy or d/m/yyyy
    
    # Valid date ranges
    MIN_DAY = 1
    MAX_DAY = 31
    MIN_MONTH = 1
    MAX_MONTH = 12
    MIN_YEAR = 1900
    MAX_YEAR = 2100
    
    # Characters to remove from numbers
    NUMBER_CHARS_TO_REMOVE = ['=', '+', '-']
    
    # Minimum date length (characters)
    MIN_DATE_LENGTH = 8
    
    # Minimum document number length (characters)
    MIN_DOC_NUMBER_LENGTH = 2
    
    # Date must contain this character
    DATE_REQUIRED_CHAR = '/'
    
    # Minimum meaningful cells required to keep row
    MIN_MEANINGFUL_CELLS = 3
    
    # Standard document number (for gap filling)
    STANDARD_DOC_NUMBER = 'B674'


# ============================================================================
# TABLE STRUCTURE SETTINGS
# ============================================================================

class TableStructureSettings:
    """Standard table structure and column names"""
    
    # Standard column headers (in order)
    # Removed: Trans No, G/L
    STANDARD_HEADERS = [
        'C/R Table',
        'Date',
        'Doc No.',
        'Orig Amount',
        'Acc Amount'
    ]
    
    # Keywords that indicate a header row (to skip)
    HEADER_KEYWORDS = ['date', 'trans', 'number', 'amount', 'document', 'sel']
    
    # C/R Table extraction area (Y-coordinate, pixels from top)
    TABLE_NUMBER_HEADER_AREA = 350
    
    # Patterns for extracting C/R Table number
    TABLE_NUMBER_PATTERNS = [
        r'C/R\s+Table\s+([A-Z0-9]+)',  # C/R Table PI03
        r'Table\s+([A-Z][A-Z0-9]{2,5})',  # Table PI03
        r'C/R.*?([A-Z]{2}\d{2})',  # PI03, C101, etc.
    ]
    
    # Maximum table number length
    MAX_TABLE_NUMBER_LENGTH = 10
    
    # Minimum table number length
    MIN_TABLE_NUMBER_LENGTH = 2


# ============================================================================
# FILE PATH SETTINGS
# ============================================================================

class PathSettings:
    """Default file paths and naming"""
    
    # Default input image (if none specified)
    DEFAULT_INPUT_IMAGE = 'frame_0015.png'
    
    # Default input folder for batch processing
    DEFAULT_INPUT_FOLDER = 'frames_masked\frames_masked'
    
    # Temporary preprocessed image name
    TEMP_PREPROCESSED_IMAGE = 'preprocessed.png'
    
    # Default output CSV name
    DEFAULT_OUTPUT_CSV = 'extracted_table.csv'
    
    # Excel generator script name
    EXCEL_GENERATOR_SCRIPT = 'create_excel.py'
    
    # Batch processing temporary file prefix
    BATCH_TEMP_PREFIX = 'temp_extract_'
    
    # Batch processing temporary preprocessed prefix
    BATCH_TEMP_PREPROCESS_PREFIX = 'temp_preprocessed_'
    
    # Default batch output name
    DEFAULT_BATCH_OUTPUT = 'combined_output.csv'
    
    # Supported image formats for batch processing
    SUPPORTED_IMAGE_FORMATS = ['*.png', '*.PNG', '*.jpg', '*.jpeg', '*.bmp', '*.tif', '*.tiff', '*.webp']


# ============================================================================
# YEAR FILTER SETTINGS
# ============================================================================

class YearFilterSettings:
    """Year filtering settings"""
    
    # Year range assumptions for 2-digit years
    # Years 00-50 are assumed to be 2000-2050
    # Years 51-99 are assumed to be 1951-1999
    TWO_DIGIT_YEAR_CUTOFF = 50
    
    # Default century for 2-digit years below cutoff
    DEFAULT_CENTURY = 2000
    
    # Alternative century for 2-digit years above cutoff
    ALTERNATIVE_CENTURY = 1900


# ============================================================================
# OCR ERROR CORRECTION SETTINGS
# ============================================================================

class ErrorCorrectionSettings:
    """Known OCR error patterns and corrections"""
    
    # Transaction number corrections
    # OCR often misreads leading "00" as other digits
    TRANS_NO_CORRECTIONS = {
        'prefix_corrections': [
            ('90', '00'),  # 90080 → 00080
            ('60', '00'),  # 60096 → 00096
        ]
    }
    
    # Document number corrections
    # OCR confuses similar characters
    DOC_NO_CORRECTIONS = {
        'pattern_corrections': [
            (r'BB.*', 'B674'),  # BB74, BBb74, BB?4 → B674
            (r'Bb.*', 'B674'),
        ]
    }
    
    # Common character substitutions
    CHAR_SUBSTITUTIONS = {
        'D0': '00',  # D0 → 00
        ' .': '.',   # Space before decimal
    }
    
    # Character translation table for amount normalization
    # Tesseract confuses these terminal-font glyphs in numeric columns
    AMOUNT_CHAR_TRANSLATION = {
        ',': '.', '=': '-', '—': '-', '–': '-',
        'I': '1', 'l': '1', 'i': '1', '|': '1',
        'O': '0', 'o': '0',
        # In this terminal font, T/t are common OCR substitutes for the digit 7
        'T': '7', 't': '7',
    }


# ============================================================================
# OUTPUT FORMATTING SETTINGS
# ============================================================================

class OutputSettings:
    """Output formatting settings"""
    
    # CSV encoding
    CSV_ENCODING = 'utf-8'
    
    # CSV line terminator
    CSV_LINE_TERMINATOR = '\n'
    
    # Excel column width limits
    EXCEL_MIN_COLUMN_WIDTH = 10
    EXCEL_MAX_COLUMN_WIDTH = 40
    
    # Excel header style
    EXCEL_HEADER_FONT_COLOR = 'FFFFFF'
    EXCEL_HEADER_FILL_COLOR = '366092'
    EXCEL_HEADER_FONT_SIZE = 11
    
    # Excel data font
    EXCEL_DATA_FONT_NAME = 'Arial'
    EXCEL_DATA_FONT_SIZE = 10
    
    # Number of preview rows to show
    PREVIEW_ROWS = 10
    
    # Output column names for CSV/Excel export
    OUTPUT_COLUMNS = [
        'source_image',
        'cr_table',
        'row_no',
        'transaction_date',
        'pfx_document_number',
        'original_amount',
        'accounting_amount',
        'raw_ocr_line',
    ]


# ============================================================================
# LOGGING AND OUTPUT SETTINGS
# ============================================================================

class LoggingSettings:
    """Console output and logging settings"""
    
    # Show progress messages
    SHOW_PROGRESS = True
    
    # Show detailed OCR statistics
    SHOW_OCR_STATS = True
    
    # Show data preview after extraction
    SHOW_DATA_PREVIEW = True
    
    # Show timing information
    SHOW_TIMING = True
    
    # Verbose mode (show detailed preprocessing messages)
    # Set to False in batch mode to reduce clutter
    VERBOSE_MODE = True
    
    # Console output width (characters)
    CONSOLE_WIDTH = 70
    
    # Preview column width (characters)
    PREVIEW_COLUMN_WIDTH = 15


# ============================================================================
# BATCH PROCESSING SETTINGS
# ============================================================================

class BatchSettings:
    """Batch processing settings"""
    
    # Continue processing if one file fails
    CONTINUE_ON_ERROR = True
    
    # Clean up temporary files after each image
    CLEANUP_TEMP_FILES = True
    
    # Maximum number of files to process (0 = unlimited)
    MAX_FILES_TO_PROCESS = 0
    
    # Sort files before processing
    SORT_FILES = True
    
    # Show progress for each file
    SHOW_FILE_PROGRESS = True


# ============================================================================
# VALIDATION SETTINGS
# ============================================================================

class ValidationSettings:
    """Data validation rules"""
    
    # Require date field for valid row
    REQUIRE_DATE = True
    
    # Require document number for valid row
    REQUIRE_DOC_NUMBER = True
    
    # Require transaction number for valid row
    REQUIRE_TRANS_NUMBER = False
    
    # Allow empty amounts
    ALLOW_EMPTY_AMOUNTS = True
    
    # Date format validation regex
    DATE_FORMAT_REGEX = r'\d{1,2}/\d{1,2}/\d{2,4}'
    
    # Transaction number format (5 digits)
    TRANS_NO_FORMAT_REGEX = r'^\d{5}$'
    
    # GL Code format (10 digits)
    GL_CODE_FORMAT_REGEX = r'^\d{10}$'


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_all_settings():
    """Get all settings as a dictionary"""
    settings = {}
    
    for cls_name in dir():
        cls = globals()[cls_name]
        if isinstance(cls, type) and cls_name.endswith('Settings'):
            settings[cls_name] = {}
            for attr in dir(cls):
                if not attr.startswith('_') and attr.isupper():
                    settings[cls_name][attr] = getattr(cls, attr)
    
    return settings


def print_settings():
    """Print all current settings"""
    all_settings = get_all_settings()
    
    print("=" * 70)
    print(" " * 20 + "CURRENT SETTINGS")
    print("=" * 70)
    
    for category, settings in all_settings.items():
        print(f"\n{category}:")
        print("-" * 70)
        for key, value in settings.items():
            print(f"  {key:40s} = {value}")
    
    print("=" * 70)


# ============================================================================
# QUICK ACCESS SETTINGS
# ============================================================================

# Create instances for easy access
ocr = OCRSettings()
preprocessing = PreprocessingSettings()
table_detection = TableDetectionSettings()
cleaning = CleaningSettings()
table_structure = TableStructureSettings()
paths = PathSettings()
year_filter = YearFilterSettings()
error_correction = ErrorCorrectionSettings()
output = OutputSettings()
logging = LoggingSettings()
batch = BatchSettings()
validation = ValidationSettings()


if __name__ == "__main__":
    # When run directly, show all settings
    print_settings()
