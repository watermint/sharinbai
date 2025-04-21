# Sharinbai - Automated Directory Structure Generator

Sharinbai is a tool for generating industry-specific folder structures and placeholder files using AI.
It utilizes LLM models to create a hierarchical directory structure tailored to specific industries and roles.

## Features

- Generate complete folder structures based on industry and role
- Support for multiple languages
- Generate various file types (text, docx, xlsx, pdf, images)
- Customizable outputs
- Interactive parameter input when not provided

## Requirements

- Python 3.6+
- Ollama

## Installation

1. Clone this repository
```
git clone https://github.com/yourusername/sharinbai.git
cd sharinbai
```

2. Install required dependencies
```
pip install -r requirements.txt
```

## Usage

Sharinbai supports the following commands:

### Generate Complete Structure

To create a complete folder structure with files:

```
python sharinbai.py all
```

### Generate Structure Only

To create only the folder structure without generating any files:

```
python sharinbai.py structure
```

### Generate Files Only

To generate or update files in an existing folder structure:

```
python sharinbai.py file
```

### List Supported Languages

To see all supported languages:

```
python sharinbai.py list-languages
```

## Interactive Parameter Input

Sharinbai is designed to work with or without command-line arguments. If the necessary parameters (industry, role, language) are not provided, the program will interactively prompt you for input.

### Parameter Hierarchy

The program determines parameters in the following order:

1. Command-line arguments (if provided)
2. Values from `.metadata.json` in the target directory (if exists)
3. Interactive user input (when neither of the above is available)

### How Interactive Prompting Works

When required information is missing, Sharinbai will prompt you for input:

1. **Industry** - Required for all new structures
   ```
   Please enter the industry for the folder structure:
   ```

2. **Role** - Optional contextual information
   ```
   Please enter a specific role within the industry (optional, press Enter to skip):
   ```

3. **Language** - Will show supported languages and prompt for choice
   ```
   Supported languages:
   1. en
   2. de
   3. fr
   ...
   Please enter the language for the folder structure (default: en):
   ```

### Working with Existing Structures

When working with existing folder structures (using the `file` command), Sharinbai automatically reads the `.metadata.json` file to retrieve industry, role, and language information. This means you don't need to specify these parameters again.

## Examples

### Basic Usage with Interactive Prompts

```
python sharinbai.py all
```
The program will prompt for industry, role, and language.

### Generate Structure with Some Parameters Specified

```
python sharinbai.py structure --industry healthcare
```
The program will use "healthcare" as the industry and prompt for role and language.

### Update Files in Existing Structure

```
python sharinbai.py file --path ./my_project
```
The program will read parameters from the existing `.metadata.json` file.

## Advanced Options

For advanced users, additional parameters can be specified:

```
python sharinbai.py all --model gemma3:4b --path ./custom_output --log-level DEBUG
```

## Project Structure

```
sharinbai/
├── resources/           # Resources and language files
├── src/                 # Source code
│   ├── config/          # Configuration and settings
│   ├── content/         # Content generation 
│   │   └── generators/  # File generators for different formats
│   ├── foundation/      # Foundation for LLM communication
│   └── structure/       # Folder structure generation
├── tests/               # Unit tests
├── requirements.txt     # Dependencies
├── sharinbai.py         # Main entry point
├── run_tests.py         # Test runner
└── README.md            # This file
```

## License

Apache 2.0
