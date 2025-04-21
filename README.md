# Sharinbai

A tool for automatically generating business-like folder structures and sample files

## Overview

Sharinbai is a tool that automatically generates realistic folder structures and sample files (Word, Excel, PDF) based on specific industries and business roles. It uses Ollama to automatically generate everything from folder structures to file contents.

## Features

- Automatic generation of appropriate folder structures based on industry and business role
- Creation of sample files including Word documents (.docx), Excel spreadsheets (.xlsx), and PDF files (.pdf)
- Realistic content generation using Ollama
- Multi-language support (Japanese, English, etc.)
- Custom output directory specification
- Detailed logging
- Organized output in industry/role subdirectories
- Learning from existing files to create similar documents
- Date-sensitive document generation with recent dates by default
- Support for long-term project simulation with organized date-based folder structures
- Hierarchical organization of reports and documents by year/fiscal year

## Requirements

- Python 3.6 or higher
- [Ollama](https://ollama.ai/) installed and running locally
- A requirements.txt file is included with the project, which lists all the necessary Python dependencies. You can install them automatically using pip:
  ```
  pip install -r requirements.txt
  ```

## Installation

1. Clone or download this repository
2. Install and start Ollama
   ```
   # Installation method varies by OS
   # https://ollama.ai/download
   
   # Start Ollama server
   ollama serve
   ```
3. Download the required model
   ```
   ollama pull gemma3:12b
   ```

## Usage

```bash
python sharinbai.py [--industry INDUSTRY] [--role ROLE] [--output DIR] [--language LANG] [--start-date DATE] [--end-date DATE]
```

### Arguments

- `--industry, -i`: Industry to generate folder structure for (e.g., Construction, IT, Medical) (default: Construction)
- `--role, -r`: Business role to focus on (e.g., Accounting, Sales, HR) (default: Project Manager)
- `--output, -o`: Output directory path (default: ./output)
- `--language, -l`: Language for generated content (default: English)
- `--start-date, -sd`: Start date for date-sensitive documents (format: YYYY-MM-DD, default: 30 days ago)
- `--end-date, -ed`: End date for date-sensitive documents (format: YYYY-MM-DD, default: today)

### Directory Structure

Files are organized in the following hierarchy:
```
output_dir/
  └── Industry/
      └── Role/
          ├── Reports/
          │   ├── FY2023/
          │   │   ├── Monthly Reports/
          │   │   │   └── 2023-01-Report.docx
          │   │   └── Annual_Summary_2023.xlsx
          │   └── FY2024/
          │       └── ...
          ├── Meeting Minutes/
          │   ├── 2023/
          │   │   └── ...
          │   └── 2024/
          │       └── ...
          └── [Other folders and files]
```

For example, with default settings, your files will be created in:
```
./output/Construction/Project Manager/
```

### Examples

```bash
# Generate Construction industry folder structure with Project Manager role (uses defaults)
python sharinbai.py

# Generate Medical industry folder structure with Project Manager role (default)
python sharinbai.py --industry "Healthcare Industry"

# Generate IT industry folder structure with focus on accounting role
python sharinbai.py --industry "IT Industry" --role Accounting

# Generate folder structure for education industry with focus on HR role in Japanese
python sharinbai.py --industry "Education" --role HR --language ja

# Generate documents with dates in a specific range
python sharinbai.py --industry "Construction" --start-date 2023-01-01 --end-date 2023-03-31

# Generate a 6-month project with files organized by month and year
python sharinbai.py --industry "Construction" --start-date 2023-01-01 --end-date 2023-06-30

# Using short form arguments
python sharinbai.py -i "Retail" -r "Marketing" -o ./retail_marketing -l English
```

## Learning from Existing Files

By default, Sharinbai will:

1. Scan the target directory for existing folders and files
2. Extract content from Word, Excel, and PDF files
3. Use the existing content as examples to generate similar new files
4. Create a folder structure that complements the existing one

This is useful for:
- Expanding an existing project structure with consistent file formats
- Creating documents that match your existing style and formatting
- Ensuring new content fits in with your established patterns

If you prefer to generate completely new content without being influenced by existing files, use the `--skip-scan` option.

## Date-Sensitive Document Generation

By default, Sharinbai will generate date-sensitive documents (reports, meeting minutes, etc.) with dates from the last 30 days. This feature:

1. Automatically identifies files that should contain dates (reports, minutes, etc.)
2. Assigns realistic dates within the specified date range
3. Includes these dates in filenames (YYYY-MM-DD format) and document content
4. Makes documents appear as if they were created recently

For long-term projects or simulation of organizational history:

1. Specify both `--start-date` and `--end-date` with a date range spanning multiple months
2. The tool automatically detects when the date range spans multiple months
3. Documents will be organized in date-based folder structures:
   - Reports folder with fiscal year subfolders
   - Meeting minutes organized by year/month
   - Project records organized chronologically
4. All files will be created within the same base folder structure, organized by date
5. This creates a realistic timeline of project or organizational documents

## Notes

- Generated content is fictional and created by AI
- Please review content before using in actual business environments
- Do not include real business data

## License

Apache License