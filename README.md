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

### 1. Setting up Ollama

Sharinbai requires Ollama to run AI models locally on your machine. Follow these steps to install and set up Ollama:

1. Download and install Ollama from [https://ollama.ai](https://ollama.ai)
   - For Windows: Download the installer from the website
   - For macOS: `brew install ollama`
   - For Linux: Follow the instructions on the Ollama website

2. After installation, start Ollama:
   - On Windows: Ollama runs automatically after installation
   - On macOS: 
     - Ollama app typically runs automatically after installation
     - If installed via Homebrew, run `brew services start ollama` to start it as a service
     - This ensures Ollama runs in the background and starts automatically when you log in
   - On Linux: Run `ollama serve` in a terminal

3. Download the language model you want to use:
   ```
   ollama pull gemma3:4b
   ```
   You can also use other models like:
   ```
   ollama pull llama3
   ollama pull gemma3:12b
   ```
   
   Note: The first time you run this command, it will download the model which may take some time depending on your internet connection and the model size.

4. Verify that Ollama is working:
   ```
   ollama run gemma3:4b "Hello, how are you?"
   ```

For more details, visit the [Ollama documentation](https://github.com/ollama/ollama/blob/main/README.md).

### 2. Setting up Python and Virtual Environment

Virtual environments allow you to isolate Python packages for different projects. This prevents conflicts between package versions.

1. Install Python 3.6+ from [python.org](https://www.python.org/downloads/) if you don't have it already

2. Create a virtual environment:
   - On Windows:
     ```
     python -m venv venv
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     python3 -m venv venv
     source venv/bin/activate
     ```
   
   After activating, your command prompt should show `(venv)` at the beginning, indicating you're now working in the virtual environment.

3. Clone this repository:
   ```
   git clone https://github.com/yourusername/sharinbai.git
   cd sharinbai
   ```

4. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

When you're done using Sharinbai, you can deactivate the virtual environment by typing:
```
deactivate
```

To use Sharinbai again later, you'll need to activate the virtual environment before running any commands.

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
     en
     en-GB
     ja
     ko
     zh
     zh-TW
     de
     es
     fr
     it
     pt
     vi
   Please enter the language for the folder structure (default: en):
   ```
   
   > **Note:** While Sharinbai supports the languages listed above, the actual content generation depends on the LLM model's language capabilities. Not all models support all languages equally well. For best results with non-English languages, consider using larger models like `gemma3:12b` or models specifically trained for multilingual support.

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

## Troubleshooting

### Common Issues with Ollama

1. **Model not found error**: Make sure you've downloaded the model using `ollama pull [model_name]`
2. **Connection refused error**: Ensure Ollama is running with `ollama serve`
3. **Out of memory error**: Try using a smaller model like `gemma3:4b` instead of larger ones

### Common Issues with Python

1. **ModuleNotFoundError**: Make sure you've activated the virtual environment and installed requirements
2. **Permission errors**: On Unix-like systems, you might need to use `sudo` or change file permissions

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

### Bundled Fonts

This project bundles several Noto Fonts in the resources directory. These fonts are licensed under the SIL Open Font License, Version 1.1. See the NOTICE file for details and attributions.
