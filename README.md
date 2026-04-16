# ftcs

OCR table extraction utility for accounting-style screenshots. The project uses Tesseract OCR plus rule-based post-processing to convert terminal-like image tables into clean CSV output (and optional Excel generation scripts).

## Repository review

Current structure is intentionally minimal:

- `extract.py`: main extraction pipeline (single-image and batch modes)
- `settings.py`: centralized configuration for OCR, preprocessing, cleaning, paths, and output behavior
- `README.md`: project documentation

High-level code review notes:

- The pipeline is feature-rich and configurable, with good separation of settings from extraction logic.
- The script currently favors template-based extraction for this table format (`should_use_template_extraction()` always returns `True`), which is consistent with comments in code.
- `--help` output still references `tesseract_version.py`; in this repo the executable script is `extract.py`.
- In one early-return template path, the script prints that an Excel generator exists but does not call `generate_excel_code()` before returning. CSV output remains correct.

## What this tool does

- Preprocesses image input for OCR (thresholding, inversion, optional sharpening/contrast)
- Runs Tesseract in TSV mode to get text and coordinates
- Extracts and cleans table rows with OCR error correction
- Normalizes key columns into:
  - `C/R Table`
  - `Date`
  - `Doc No.`
  - `Orig Amount`
  - `Acc Amount`
- Supports year-based filtering (`--year YYYY`)
- Supports batch processing over a folder of PNG files

## Requirements

- Python 3.8+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and available in `PATH`
- Optional Python packages:
  - `Pillow` for image preprocessing
  - `openpyxl` for generating formatted `.xlsx` files from generated script

Install optional packages:

```bash
pip install Pillow openpyxl
```

## Usage

### Single image

```bash
python extract.py frame_0004.png
```

With year filter:

```bash
python extract.py frame_0004.png --year 2020
```

If no image is provided, `paths.DEFAULT_INPUT_IMAGE` from `settings.py` is used.

### Batch mode

Use explicit input folder and output file:

```bash
python extract.py --batch ./images combined_output.csv
```

Use defaults from `settings.py`:

```bash
python extract.py --batch
```

Batch with year filter:

```bash
python extract.py --batch --year 2020
```

## Configuration

Tune behavior in `settings.py`:

- OCR confidence/PSM: `OCRSettings`
- Image preprocessing: `PreprocessingSettings`
- Table/header schema and patterns: `TableStructureSettings`
- Cleaning/validation constraints: `CleaningSettings`, `ValidationSettings`
- Default paths and output names: `PathSettings`
- Batch behavior and logging: `BatchSettings`, `LoggingSettings`

## Output files

- Primary output: CSV (default: `extracted_table.csv`)
- Batch output: CSV (default: `combined_output.csv`)
- Optional generated script: `create_excel.py` to build `extracted_table.xlsx`

## Troubleshooting

- `tesseract: command not found`
  - Install Tesseract and confirm it is in your `PATH`.
- Low extraction quality
  - Adjust `CONFIDENCE_THRESHOLD`, `PIL_THRESHOLD`, and contrast/sharpen settings.
- No rows in output
  - Verify input image quality and table format assumptions; try without `--year` filter.

## Notes for contributors

- Keep defaults in `settings.py` authoritative; avoid hardcoded constants in `extract.py` where possible.
- Keep CLI examples synchronized with the real script name (`extract.py`).
