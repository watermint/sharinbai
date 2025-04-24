# Sharinbai - Automated Directory Structure Generator

![sharinbai](sharinbai_w256.png)

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
   ollama pull gemma3:12b
   ```
   
   Note: The first time you run this command, it will download the model which may take some time depending on your internet connection and the model size.

4. Verify that Ollama is working:
   ```
   ollama run gemma3:4b "Hello, how are you?"
   ```

For more details, visit the [Ollama documentation](https://github.com/ollama/ollama/blob/main/README.md).

### 2. Download the Repository

If you are not familiar with the `git` command, you can download the repository as a ZIP file:

- 1. Go to the GitHub page: https://github.com/watermint/sharinbai
- 2. Click the green **Code** button, then select **Download ZIP**.
- 3. After downloading, unzip the file to your desired location.
- 4. Open a terminal and change directory to the unzipped folder (e.g., `cd sharinbai`).

Alternatively, you can use the following `git` command to clone the repository:

```
git clone https://github.com/watermint/sharinbai.git
cd sharinbai
```

### 3. Setting up Python and Virtual Environment

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

### Edit Specific Files

To selectively regenerate existing files with new role or date parameters:

```
python sharinbai.py edit --role "New Role" --max-files 10
```

This command:
- Randomly selects up to 10 files from the existing structure (uses the default if `--max-files` is not specified)
- Regenerates them with the new role and date range while preserving the folder structure
- Prioritizes files with extensions for better content generation
- Can be used to update specific files without regenerating the entire structure

Example use cases:
- Change the perspective of files (e.g., from manager to quality assurance)
- Update files to reflect a different time period
- Refresh content with consistent new context

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

### Multiple Roles in the Same Structure

You can generate multiple role-specific folders and files within the same folder structure by using the `--role` option:

1. First, create a base structure:
   ```
   python sharinbai.py structure --industry healthcare --role doctor
   ```

2. Then, generate content for additional roles using the same structure:
   ```
   python sharinbai.py file --role nurse
   python sharinbai.py file --role administrator
   ```

The program will use the industry and language settings from `.metadata.json` but temporarily override the role, allowing you to create content for multiple roles within the same structure.

### How Interactive Prompting Works

When required information is missing, Sharinbai will prompt you for input:

1. **Industry** - Required for all new structures
   ```
   Please enter the industry for the folder structure:
   ```

   Please enter your desired industry. You may enter a general industry such as "Construction," or a more specific industry such as "Civil engineering contractor specializing in tunnel construction."


2. **Role** - Optional contextual information
   ```
   Please enter the business role for which the folder structure is intended:
   ```

   Please enter your desired role. You may enter a general roles such as "Sales" or "Legal," or a more specific role such as "Project Manager of Highway tunnel project".

3. **Language** - Will show supported languages and prompt for choice
   ```
   Supported languages:
   1. de
   2. en
   3. en-GB
   4. es
   5. fr
   6. it
   7. ja
   8. ko
   9. pt
   10. vi
   11. zh
   12. zh-TW
   Please select a language (enter language code or number from the list): 
   ```
   
   > **Note:** While Sharinbai supports the languages listed above, the actual content generation depends on the LLM model's language capabilities. Not all models support all languages equally well. For best results with non-English languages, consider using larger models like `gemma3:12b` or models specifically trained for multilingual support.

### Working with Existing Structures

When working with existing folder structures (using the `file` command), Sharinbai automatically reads the `.metadata.json` file to retrieve industry, role, and language information. This means you don't need to specify these parameters again.

If you want to temporarily override the industry or role stored in `.metadata.json`, you can use the `--industry` or `--role` options:

```
python sharinbai.py file --role data_scientist
```

This allows you to generate content for different roles while maintaining the same base folder structure.

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

### Batch Processing

Sharinbai supports batch processing through a YAML configuration file:

```
python sharinbai.py batch --file batch_config.yaml
```

This allows you to define multiple tasks to be executed sequentially. See the example `batch_config.yaml` for details.

### Edit Command Options

The `edit` command provides additional options for more control:

```
python sharinbai.py edit --path ./my_project --role "Quality Inspector" --max-files 15 --date-start 2023-10-01 --date-end 2023-10-31
```

Parameters:
- `--path`: Target directory containing the structure to edit (default: ./out)
- `--role`: New role perspective for the regenerated files (required)
- `--max-files`: Maximum number of files to randomly select and edit (default: 10)
- `--date-start` and `--date-end`: New date range for the regenerated files
- `--model`: AI model to use for content generation
- `--language`: Language override (if not using the language from metadata)

The `edit` command always uses the explicitly provided role and date range parameters, ignoring those in the metadata files. This allows you to selectively refresh content with a new perspective while preserving the overall structure.

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
