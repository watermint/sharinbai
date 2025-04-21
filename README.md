# Sharinbai - Automated Directory Structure Generator

Sharinbai is a tool for generating industry-specific folder structures and placeholder files using AI. It utilizes OpenAI's models to create a hierarchical directory structure tailored to specific industries and roles.

## Features

- Generate complete folder structures based on industry and role
- Support for multiple languages
- Generate various file types (text, docx, xlsx, pdf, images)
- Customizable outputs

## Requirements

- Python 3.6+
- Ollama with llama3 model (or other compatible model)

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

To create a complete folder structure with files for a specific industry and role:

```
python sharinbai.py all --industry "healthcare" --role "doctor" --language "en"
```

### Generate Files Only

To generate or update files in an existing folder structure:

```
python sharinbai.py file --industry "healthcare" --role "doctor" --language "en"
```

### List Supported Languages

To see all supported languages:

```
python sharinbai.py list-languages
```

### Common Options

All commands support the following options:

- `--industry`, `-i`: Industry for the folder structure (required)
- `--path`, `-p`: Path where to create the folder structure (default: ./out)
- `--language`, `-l`: Language for the folder structure (default: en)
- `--model`, `-m`: Ollama model to use (default: llama3)
- `--role`, `-r`: Specific role within the industry (optional)
- `--ollama-url`: URL for the Ollama API server (default: http://localhost:11434)
- `--log-level`: Logging level (default: INFO)

## Examples

### Healthcare Industry for Doctors

```
python sharinbai.py all --industry healthcare --role doctor
```

### Legal Industry with Japanese Language

```
python sharinbai.py all --industry legal --language ja
```

### Update Files in Education Industry Structure

```
python sharinbai.py file --industry education --role professor
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
├── requirements.txt     # Dependencies
├── sharinbai.py         # Main entry point
└── README.md            # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.