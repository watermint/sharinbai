"""
Constants for UI strings
"""

# Command line arguments
CLI_ARGS = {
    "date_range": "Date range in YYYY-MM-DD:YYYY-MM-DD format",
    "description": "Generates a directory structure based on industry and role.",
    "file": "Only generate specific file(s) (comma-separated paths)",
    "force": "Force overwrite existing folders",
    "industry": "The industry for which to create the folder structure",
    "language": "Language for content to be generated (default: system language)",
    "max_depth": "Maximum depth of folder hierarchy (default: 3)",
    "min_files": "Minimum number of files per folder (default: 3)",
    "model": "Ollama model to use (default: gemma3:4b)",
    "output": "Output directory (default: name of the industry)",
    "role": "The business role for which the folder structure is intended",
    "scan": "Scan existing structure before generating",
    "scenario": "Business scenario to generate from",
    "structure": "Only create folder structure, don't generate files"
}

# Headers
CONTENT_HEADER = "Content"
CONTEXT_HEADER = "Business Context"
OVERVIEW_HEADER = "Overview"
FILE_INFO_HEADER = "File Information"
FILE_LIST_HEADER = "Files:"

# Labels
DESCRIPTION_LABEL = "Description:"
FILENAME_LABEL = "Filename:"
INDUSTRY_LABEL = "Industry:"
ROLE_LABEL = "Position:"
PERIOD_LABEL = "Period:"

# Footers and templates
DATE_FOOTER = ", Date: {date}"
INDUSTRY_FOOTER = "Industry: {industry}"
ROLE_FOOTER = ", Role: {role_text}"
FOOTER_TEXT = "This file was generated as a sample."
DOC_SAMPLE_TEXT = "This document was generated as a sample."
PDF_SAMPLE_TEXT = "This document was generated as a sample."
SHEET_TITLE = "Overview"
NOT_SPECIFIED = "Not specified"

# Error messages
ERROR_MESSAGES = {
    "fallback_file_error": "Error creating fallback file: {error}",
    "folder_structure_not_found": "No folder structure template found in language template. Using base prompt.",
    "invalid_date_format": "Invalid date format: {error}. Using default (last month).",
    "json_parsing_error": "JSON parsing error: {error}",
    "language_mapping_not_found": "Language mapping file not found: {file}",
    "template_file_not_found": "Template file {file} not found. Using default en-US template.",
    "unknown_extension": "Unknown file extension: {file_path} - Suggestions: {suggestions}",
    "unsupported_extension": "Unsupported file extension: {ext}. Using {new_ext} instead."
}

# Templates
FALLBACK_FILE_TEMPLATE = "# {file_name}\n\n{description}\n\nIndustry: {industry}\nRole: {role}\n"

# CLI role prompt - this was specifically referenced in the code
ROLE_PROMPT_CLI = "Please enter the business role for which the folder structure is intended:"

# Statistics output messages
STATS_HEADER = "----- Generation Statistics -----"
STATS_FOLDER_COUNT = "Total folders created: {count}"
STATS_FILE_COUNT = "Total files created: {count}"
STATS_FILE_TYPES_HEADER = "File types:"
STATS_FILE_TYPE_ITEM = "{type}: {count}"
STATS_PROCESSING_TIMES_HEADER = "Processing times:"
STATS_PROCESSING_TIME_ITEM = "{item}: {time}s"
STATS_TOTAL_EXECUTION_TIME = "Total execution time: {time}s"
STATS_FOOTER = "--------------------------------" 