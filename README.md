# FTCS - Financial Table Capture System

OCR-powered table extraction utility for accounting-style terminal screenshots. Converts green-on-black terminal images into structured CSV and Excel output using Tesseract OCR with rule-based post-processing.

## Features

- **Template-based extraction** — Regex-driven row parsing optimized for accounting table formats
- **Adaptive OCR** — Automatic confidence threshold lowering for low-quality scans
- **Image preprocessing** — Binarization, contrast enhancement, sharpening, and vertical masking
- **OCR bounding box preview** — Color-coded confidence visualization on masked images
- **Year filtering** — Extract only rows matching a specific year (`--year YYYY`)
- **Batch processing** — Process entire folders of PNG images into a single combined CSV
- **OCR error correction** — Fixes common misreads (e.g., `BB74` → `B674`, `90xxx` → `00xxx`)
- **Excel generation** — Outputs a ready-to-run script for creating formatted `.xlsx` files
- **Fully configurable** — All OCR, preprocessing, cleaning, and path settings in `settings.py`

## Project Structure

```
ftcs-final/
├── extract.py                  # Main extraction pipeline (single + batch modes)
├── settings.py                 # Centralized configuration (OCR, preprocessing, paths, etc.)
├── automgui.py                 # GUI automation for screen capture workflows
├── automation_config.json      # Automation parameters (scroll delay, SSIM tolerance)
├── requirements.txt            # Python dependencies
├── section_001_page_001.png    # Sample input image
├── error.log                   # Error log from previous runs
└── README.md                   # This file
```

## Requirements

- **Python 3.8+**
- **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)** installed and available in `PATH`

  On Windows, you can also set the path explicitly in `settings.py`:
  ```python
  class OCRSettings:
      TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

## Installation

```bash
# Clone the repository
git clone <repo-url> ftcs-final
cd ftcs-final

# Install dependencies
pip install -r requirements.txt

# Verify Tesseract is installed
tesseract --version
```

**Dependencies:**
| Package | Purpose |
|---------|---------|
| `Pillow` | Image preprocessing (binarization, masking, sharpening) |
| `openpyxl` | Excel `.xlsx` file generation |
| `numpy` | Array operations for image processing |
| `opencv-python` | Advanced image processing |
| `scikit-image` | Structural similarity (SSIM) comparison |
| `pyautogui` | GUI automation for screen capture |
| `PyGetWindow` | Window management for automation |

## Usage

### Single Image

```bash
# Basic extraction
python extract.py image.png

# With year filter
python extract.py image.png --year 2020

# Use default image from settings.py
python extract.py
```

### Batch Processing

```bash
# Process folder with explicit output
python extract.py --batch ./images combined_output.csv

# Use defaults from settings.py
python extract.py --batch

# Batch with year filter
python extract.py --batch --year 2020

# Batch with custom output, default input folder
python extract.py --batch my_output.csv --year 2020
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--year YYYY` | Filter results to only include the specified year |
| `--batch` | Process all PNG images in a folder |
| `--no-preprocess` | Disable image preprocessing/masking before OCR |
| `--grayscale-only` | Disable binarization, keep grayscale image |
| `--mask-top PERCENT` | Mask top percentage (0–100, default: 33%) |
| `--mask-bottom PERCENT` | Mask bottom percentage (0–100, default: 15%) |
| `--preview-grayscale` | Save masked preview in grayscale |
| `--no-preview-bboxes` | Disable OCR bounding box overlay on preview |
| `--help`, `-h` | Show help message |

## Output Files

| File | Description |
|------|-------------|
| `extracted_table.csv` | Primary CSV output (single image mode) |
| `combined_output.csv` | Combined CSV output (batch mode) |
| `create_excel.py` | Generated script to create `extracted_table.xlsx` |
| `preprocessed.png` | Temporary preprocessed image (cleaned up after run) |
| `masked_inspection/` | Directory containing masked preview images with OCR bbox overlays |

### Output Columns

| Column | Description |
|--------|-------------|
| `C/R Table` | Cash receipts table identifier |
| `Date` | Transaction date (DD/MM/YYYY) |
| `Doc No.` | Document number (e.g., `B674`) |
| `Orig Amount` | Original transaction amount |
| `Acc Amount` | Accounted amount |

## Configuration

All settings are centralized in `settings.py`. Key configuration classes:

### `OCRSettings`
- `CONFIDENCE_THRESHOLD` — Minimum OCR confidence (0–100, default: 15)
- `PSM_MODE` — Tesseract page segmentation mode (default: `6`)
- `TESSERACT_PATH` — Explicit Tesseract executable path

### `PreprocessingSettings`
- `PIL_THRESHOLD` — Binarization threshold (0–255, default: 122)
- `CONTRAST_ENHANCEMENT` — Contrast multiplier (default: 1.2)
- `APPLY_SHARPENING` — Enable sharpening filter (default: `True`)
- `APPLY_BINARIZATION` — Enable black/white thresholding (default: `True`)
- `APPLY_VERTICAL_MASK` — Enable top/bottom masking (default: `True`)
- `MASK_TOP_RATIO` / `MASK_BOTTOM_RATIO` — Mask proportions (default: 0.33 / 0.15)
- `SAVE_MASKED_PREVIEW` — Save preview images for inspection (default: `True`)
- `MASKED_PREVIEW_SHOW_BBOXES` — Draw OCR confidence boxes on preview (default: `True`)

### `TableStructureSettings`
- `STANDARD_HEADERS` — Output column names
- `TABLE_NUMBER_PATTERNS` — Regex patterns for C/R Table number extraction

### `CleaningSettings`
- `MIN_DATE_LENGTH` — Minimum characters for valid date (default: 8)
- `MIN_DOC_NUMBER_LENGTH` — Minimum characters for doc number (default: 2)
- `STANDARD_DOC_NUMBER` — Fallback document number (default: `B674`)

### `PathSettings`
- `DEFAULT_INPUT_IMAGE` — Default image for single mode
- `DEFAULT_INPUT_FOLDER` — Default folder for batch mode
- `DEFAULT_OUTPUT_CSV` — Default CSV filename
- `DEFAULT_BATCH_OUTPUT` — Default batch output filename

Run `python settings.py` to view all current settings.

## Troubleshooting

### `tesseract: command not found`
Install Tesseract OCR and ensure it's in your system `PATH`, or set `OCRSettings.TESSERACT_PATH` in `settings.py`.

### Low extraction quality
- Adjust `CONFIDENCE_THRESHOLD` (lower to capture more text, higher to reduce noise)
- Tune `PIL_THRESHOLD` for binarization
- Enable/disable `APPLY_SHARPENING` and `CONTRAST_ENHANCEMENT`
- Check `masked_inspection/` preview images to verify preprocessing

### No rows in output
- Verify input image contains a recognizable table format
- Try without `--year` filter
- Check that dates contain `/` and are at least 8 characters
- Review `MIN_DATE_LENGTH` and `MIN_DOC_NUMBER_LENGTH` in settings

### UnicodeEncodeError on Windows
The script includes a safe print wrapper for ASCII fallback. If issues persist, set `PYTHONIOENCODING=utf-8` before running.

## Architecture Notes

- **Template extraction is always used** (`should_use_template_extraction()` returns `True`) — this is intentional for this specific table format, as regex-based row parsing is more reliable than column detection for closely-spaced rows
- The pipeline falls back to column-based extraction when template extraction yields no results
- Adaptive OCR retry lowers the confidence threshold by 10 (min 5) when fewer than 20 words are detected

## License

See repository for license information.
