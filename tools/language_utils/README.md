# Language Resources Utilities

This directory contains utilities for managing and fixing language resource files.

## Overview

The project uses JSON-based language resource files located in the `resources/` directory. These files follow the naming pattern `prompts-{lang}.json` where `{lang}` is the language code (e.g., `en`, `fr`, `zh`, etc.).

Each language file contains translations for various strings and prompts used in the application. Some of these strings contain placeholders in the format `{placeholder_name}` which are replaced at runtime with dynamic content.

## Included Scripts

### 1. `fix_language_resources.py`

This script automatically fixes missing placeholders in all language resource files by comparing them to the reference language (default: `en`).

Usage:
```bash
python fix_language_resources.py
```

The script:
1. Loads all language resource files from `resources/`
2. Identifies the reference language (default: `en`)
3. For each non-reference language, it identifies missing placeholders
4. Adds the missing placeholders to the translated strings
5. Saves the fixed files to `resources_fixed/`

### 2. `test_fixed_resources.py`

This script tests if all language resources have the required placeholders.

Usage:
```bash
python test_fixed_resources.py
```

The script:
1. Loads all language resource files from `resources_fixed/`
2. Compares each language against the reference language
3. Reports any missing keys or placeholders

## Placeholder Extraction Logic

The scripts use a special logic to extract only real placeholders from the text strings, while ignoring example JSON patterns that might look like placeholders:

1. The scripts maintain a whitelist of known valid placeholder names (e.g., `industry`, `role`, `date_range`, etc.)
2. When scanning text for placeholders, any pattern matching `{placeholder}` is checked against this whitelist
3. Additionally, simple word-only patterns without JSON syntax characters are considered potential placeholders
4. JSON example patterns with quotes, colons, commas, etc. are automatically excluded

This prevents incorrectly identifying sample JSON syntax in the prompts as actual placeholders, which would cause unnecessary fixes to be applied.

## Workflow for Maintaining Language Resources

When adding new strings or modifying existing ones:

1. Always update the reference language file (`prompts-en.json`) first
2. If adding new placeholders, add them to the `valid_placeholders` list in the scripts
3. Run the built-in test to check for issues:
   ```bash
   python sharinbai.py test-languages
   ```
4. If issues are found, run the fix script:
   ```bash
   python fix_language_resources.py
   ```
5. Verify the fixes:
   ```bash
   python test_fixed_resources.py
   ```
6. Copy the fixed files back to the resources directory:
   ```bash
   cp resources_fixed/prompts-*.json resources/
   ```
7. Run the test again to confirm everything is fixed:
   ```bash
   python sharinbai.py test-languages
   ```

## Placeholder Guidelines

When adding new strings with placeholders:

1. Use the format `{placeholder_name}` for all placeholders
2. Use simple, single-word names for placeholders (e.g., `industry`, `role_text`, `date_range`)
3. Ensure consistent placeholder names across all languages
4. Document the purpose of each placeholder
5. When adding new strings to translation files, ensure all placeholders from the reference language are included
6. If adding a new placeholder name, update the `valid_placeholders` set in both scripts

## Adding New Languages

To add a new language:

1. Create a new file named `prompts-{lang}.json` in the `resources/` directory
2. Copy the structure from the reference language (`prompts-en.json`)
3. Translate all strings, ensuring placeholders are preserved
4. Update `language_mapping.json` to include the new language
5. Run the tests to ensure everything is correct 