# Studio 5000 L5X Logic Extractor

A lightweight, zero-dependency Python tool to parse Rockwell Automation Studio 5000 `.L5X` export files and convert them into human-readable text reports.

This tool is designed for Control Engineers and Developers who need to document code, track changes in version control (Git), or perform static analysis on PLC logic without opening the Studio 5000 IDE.

## Features

*   **Zero Dependencies:** Runs entirely on the Python Standard Library. No `pip install` required.
*   **Deep Logic Extraction:**
    *   **Ladder Logic (RLL):** Extracts Rung structure, logic text, and rung comments.
    *   **Structured Text (ST):** Extracts full code blocks.
*   **Tag Analysis:**
    *   Separates **Global (Controller)** and **Local (Program)** scopes.
    *   Identifies **Aliases**, **Base Tags**, and **I/O Usage** (Input/Output/Local).
    *   Preserves full descriptions/comments.
*   **Safe File Handling:** automatically timestamps output files if a file with the same name already exists to prevent data loss.
*   **Namespace Agnostic:** Automatically detects and handles XML namespaces, making it compatible with various L5X schema versions.

## Prerequisites

*   **Python 3.6+**
*   An `.L5X` file exported from Studio 5000 / RSLogix 5000.

## Installation

1.  Clone this repository:
    ```bash
    git clone https://github.com/YOUR_USERNAME/L5X-Logic-Exporter.git
    cd L5X-Logic-Exporter
    ```

2.  Run the script directly (no virtual environment needed).

## Usage

The script accepts two arguments: the path to the input file and the output directory.

```bash
python l5x_export.py <Input_Path.L5X> <Output_Directory>
```
Examples

Process a file in the same folder:

code
Bash
download
content_copy
expand_less
python l5x_export.py MyProject.L5X ./output

Process a file using absolute paths:

code
Bash
download
content_copy
expand_less
python l5x_export.py "C:\PLC_Backups\Line1_V2.L5X" "C:\Reports\Line1"
Output Files

The tool generates three distinct text files in your specified output directory:

1. export_controller_info.txt

Contains high-level metadata about the project.

code
Text
download
content_copy
expand_less
Name: MyFactory_PLC
ProcessorType: 1756-L81E
Revision: 32.11
Description: Main Process Controller for Line 1
2. export_tags.txt

A formatted table of all Controller Scope (Global) tags.

code
Text
download
content_copy
expand_less
Name                           | Usage      | Type/Alias                     | Description
------------------------------ | ---------- | ------------------------------ | --------------------
Sys_Heartbeat                  | Local      | DINT                           | Watchdog timer
Pump_01_Start                  | Output     | Alias->Local:1:O.Data.0        | Main Pump Start Cmd
Recipe_Data                    | Local      | udt_RecipeSystem               | Current Recipe parameters
3. export_programs.txt

The core logic file. It recursively lists every Program, Local Tags, Routines, and the Logic content.

code
Text
download
content_copy
expand_less
PROGRAM: MainProgram
Desc:    Core Sequencing Logic
===========================================================================

  [LOCAL TAGS] - Found 5
  Name                           | Usage      | Type/Alias                     | Description
  ------------------------------ | ---------- | ------------------------------ | --------------------
  Step_Index                     | Local      | DINT                           | Sequencer Step

  [ROUTINES & LOGIC] - Found 2

    ============================================================
    ROUTINE: MainRoutine (RLL)
    Desc:    Main Jump Handler
    ============================================================
    [Rung 0]
      /* Jump to sequence if auto mode is active */
      XIC(Mode_Auto) JSR(Sequence_Routine)
      ----------------------------------------

    ============================================================
    ROUTINE: Sequence_Routine (ST)
    ============================================================
    [Structured Text Code]
      ----------------------------------------
      IF Step_Index = 10 THEN
          Pump_Cmd := 1;
      END_IF;
🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

Fork the project.

Create your feature branch (git checkout -b feature/AmazingFeature).

Commit your changes (git commit -m 'Add some AmazingFeature').

Push to the branch (git push origin feature/AmazingFeature).

Open a Pull Request.

⚠️ Disclaimer

This tool is an independent open-source project and is not affiliated with, endorsed by, or supported by Rockwell Automation.

Read-Only: This tool only reads L5X files; it does not modify them.

Verification: Always verify the actual logic in the Studio 5000 environment before making engineering decisions. The extraction process is intended for documentation and analysis purposes only.

📄 License

Distributed under the MIT License. See LICENSE for more information.

code
Code
download
content_copy
expand_less
---

### Bonus: The `.gitignore` File
Since you are creating a Python repo, you should add a `.gitignore` file to prevent uploading junk files.

**File:** `.gitignore`
```text
# Python cache
__pycache__/
*.py[cod]

# Output directories (don't upload your test exports)
output/
*.txt

# OS specific
.DS_Store
Thumbs.db
