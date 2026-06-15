# FTCS - Financial Table Capture System

OCR-powered table extraction utility for accounting-style terminal screenshots. Converts green-on-black terminal images into structured CSV and Excel output using Tesseract OCR with rule-based post-processing.

## Features

- **Direct pytesseract integration** — Uses Python binding for Tesseract instead of subprocess calls
- **Smart amount normalization** — Handles terminal-font OCR confusion (I→1, O→0, T→7, etc.)
- **C/R table code normalization** — Fixes common OCR errors in 4-character table codes
- **Year filtering** — Extract only rows matching a specific year (`--year YYYY`)
- **Batch processing** — Process entire folders of images into a single combined CSV
- **Direct Excel export** — Native `.xlsx` output without intermediate scripts
- **Debug summary** — Per-file extraction statistics in a terminal-friendly table
- **Multi-format support** — PNG, JPG, JPEG, BMP, TIFF, WEBP
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
| `pytesseract` | Python binding for Tesseract OCR |
| `opencv-python` | Image loading and processing |
| `Pillow` | Image preprocessing (binarization, masking, sharpening) |
| `openpyxl` | Excel `.xlsx` file generation |
| `numpy` | Array operations for image processing |
| `scikit-image` | Structural similarity (SSIM) comparison |
| `pyautogui` | GUI automation for screen capture |
| `PyGetWindow` | Window management for automation |

## Usage

### Single Image

```bash
# Basic extraction (outputs to terminal_ocr_output_all_years.csv)
python extract.py image.png

# With year filter
python extract.py image.png --year 2025

# With Excel export
python extract.py image.png --xlsx output.xlsx

# Custom CSV output path
python extract.py image.png --csv my_output.csv
```

### Batch Processing

```bash
# Process folder
python extract.py --batch --folder ./images

# Process with year filter
python extract.py --batch --folder ./images --year 2025

# Process with explicit output
python extract.py --batch --folder ./images combined_output.csv --xlsx output.xlsx

# Use defaults from settings.py
python extract.py --batch

# Recursive folder scan
python extract.py --batch --folder ./images --recursive
```

### CLI Options

| Option | Description |
|--------|-------------|
| `images` | Positional screenshot image paths |
| `--batch` | Batch process all images in folder |
| `--folder PATH` | Folder containing screenshot images |
| `--recursive` | Scan subfolders recursively (with `--batch`) |
| `--year YYYY` | Filter results to specified year. Use `ALL` for all years |
| `--csv PATH` | CSV output path |
| `--xlsx PATH` | Excel `.xlsx` output path |
| `--no-prompt` | Do not ask for year; export all years unless `--year` is supplied |
| `--no-debug` | Turn off per-file terminal debug summary |
| `--debug` | Force per-file terminal debug summary on |

## Output Files

| File | Description |
|------|-------------|
| `terminal_ocr_output_{year}.csv` | CSV output (single or batch mode) |
| `terminal_ocr_output_all_years.csv` | CSV output when no year filter |
| `{name}.xlsx` | Excel output (when `--xlsx` is specified) |

### Output Columns

| Column | Description |
|--------|-------------|
| `source_image` | Source image filename |
| `cr_table` | Cash receipts table identifier |
| `row_no` | Row number within the image |
| `transaction_date` | Transaction date (DD/MM/YYYY) |
| `pfx_document_number` | Document number (e.g., `B674`) |
| `original_amount` | Original transaction amount |
| `accounting_amount` | Accounted amount |
| `raw_ocr_line` | Raw OCR text line for verification |

## Configuration

All settings are centralized in `settings.py`. Key configuration classes:

### `OCRSettings`
- `CONFIDENCE_THRESHOLD` — Minimum OCR confidence (0–100, default: 15)
- `PSM_MODE` — Tesseract page segmentation mode (default: `6`)
- `OCR_ENGINE_MODE` — Tesseract engine mode (default: 3 = auto)
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

### `ErrorCorrectionSettings`
- `AMOUNT_CHAR_TRANSLATION` — Character mapping for amount normalization (I→1, O→0, T→7, etc.)

### `OutputSettings`
- `OUTPUT_COLUMNS` — Column names for CSV/Excel export

### `PathSettings`
- `DEFAULT_INPUT_IMAGE` — Default image for single mode
- `DEFAULT_INPUT_FOLDER` — Default folder for batch mode
- `SUPPORTED_IMAGE_FORMATS` — List of supported image glob patterns

Run `python settings.py` to view all current settings.

## Amount Normalization

The OCR routine includes sophisticated amount normalization for terminal-font screenshots:

| OCR Reading | Normalized | Explanation |
|-------------|------------|-------------|
| `5. 3f=` | `5.37-` | Space removed, f→7, =→- |
| `5.1 +` | `5.1+` | Preserved as-is |
| `1.if=` | `1.17-` | i→1, f→7, =→- |
| `5.t5-` | `5.75-` | t→7 |
| `23.T1-` | `23.71-` | T→7 |

## Troubleshooting

### `tesseract: command not found`
Install Tesseract OCR and ensure it's in your system `PATH`, or set `OCRSettings.TESSERACT_PATH` in `settings.py`.

### `pytesseract` not found
```bash
pip install pytesseract
```

### Low extraction quality
- Adjust `CONFIDENCE_THRESHOLD` (lower to capture more text, higher to reduce noise)
- Check `masked_inspection/` preview images to verify preprocessing
- Review `raw_ocr_line` column in output to see original OCR text

### No rows in output
- Verify input image contains a recognizable table format
- Try without `--year` filter
- Check that dates contain `/` in DD/MM/YYYY format

### UnicodeEncodeError on Windows
The script includes a safe print wrapper for ASCII fallback. If issues persist, set `PYTHONIOENCODING=utf-8` before running.

## Architecture Notes

- Uses `pytesseract` Python binding for direct Tesseract integration
- Image loading via `cv2.imread()` for better format support
- Regex-based row extraction with DATE_RE, DOC_RE, CR_RE patterns
- Amount normalization with character translation table for terminal-font OCR confusion
- Debug summary table for per-file extraction statistics

## License

See repository for license information.
