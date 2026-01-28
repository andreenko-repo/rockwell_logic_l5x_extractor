# Studio 5000 L5X Logic Extractor

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](https://docs.python.org/3/library/index.html)

A lightweight, **zero-dependency** Python tool to parse Rockwell Automation Studio 5000 `.L5X` export files and convert them into **human-readable text reports**.

Designed for **Control Engineers** and **Developers** who need to:
- Document PLC code for review or archival
- Perform static analysis on PLC logic
- Feed PLC logic to **LLMs** (Large Language Models) for AI-assisted analysis
- Compare program versions in a diff-friendly format

---

## Features

- **Zero Dependencies** — Runs entirely on the Python Standard Library. No `pip install` required.
- **Comprehensive Extraction**:
  - **Ladder Logic (RLL)** — Rung structure, logic text, and all comments
  - **Structured Text (ST)** — Full code blocks with preserved formatting
  - **Function Block Diagram (FBD)** — Structure metadata
  - **Sequential Function Chart (SFC)** — Step and transition information
- **Complete Project Analysis**:
  - Controller metadata and configuration
  - Global (Controller-scope) and Local (Program-scope) tags
  - User Defined Types (UDTs) with member details
  - Add-On Instructions (AOIs) with parameters and logic
  - I/O Module configuration
  - Task scheduling and program assignments
- **Safe File Handling** — Automatically timestamps output files to prevent overwrites
- **Namespace Agnostic** — Handles all L5X schema versions automatically

---

## Prerequisites

- **Python 3.6+**
- An `.L5X` file exported from Studio 5000 / RSLogix 5000

---

## Installation

```bash
git clone https://github.com/andreenko-repo/rockwell_logic_l5x_extractor.git
cd rockwell_logic_l5x_extractor
```

No additional setup required — run the script directly.

---

## Usage

```bash
python l5x_export.py <Input_Path.L5X> <Output_Directory>
```

### Examples

Process a file in the current folder:
```bash
python l5x_export.py sample_l5x/BoosterCompressor_20260128.L5X .
```

### Console Output
```
Processing file: sample_l5x/BoosterCompressor_20260128.L5X
  > Controller Info exported to sample_extracts/extract_controller_info.txt
  > Global Tags exported to sample_extracts/extract_tags.txt
  > Data Types (UDTs) exported to sample_extracts/extract_data_types.txt
  > Add-On Instructions exported to sample_extracts/extract_aoi_definitions.txt
  > I/O Modules exported to sample_extracts/extract_modules.txt
  > Tasks exported to sample_extracts/extract_tasks.txt
  > Programs exported to sample_extracts/extract_programs.txt

Export completed successfully!
```

---

## Output Files

The tool generates **seven** distinct text files in your specified output directory:

| File | Description |
|------|-------------|
| `extract_controller_info.txt` | Project metadata (processor type, revision, etc.) |
| `extract_tags.txt` | All Controller-scope (global) tags |
| `extract_data_types.txt` | User Defined Types (UDTs) with members |
| `extract_aoi_definitions.txt` | Add-On Instructions with full logic |
| `extract_modules.txt` | I/O module configuration |
| `extract_tasks.txt` | Task scheduling and program assignments |
| `extract_programs.txt` | Programs with routines and complete logic |

---

## Sample Output

The repository includes a complete sample project — a **Booster Gas Compressor** control program demonstrating real-world industrial logic:

- **Sample L5X**: `sample_l5x/BoosterCompressor_20260128.L5X`
- **Sample Extracts**: `sample_extracts/`

### Controller Info (`extract_controller_info.txt`)
```
Name: booster_compressor
ProcessorType: 1756-L82E
MajorRev: 34
MinorRev: 11
ProjectCreationDate: Tue Jan 27 20:39:03 2026
LastModifiedDate: Wed Jan 28 13:42:40 2026
```

### I/O Modules (`extract_modules.txt`)
```
I/O MODULES - Found 7
================================================================================

Name                      | Catalog Number       | Parent               | Description
------------------------- | -------------------- | -------------------- | --------------
Local                     | 1756-L82E            | Local:1              | 
DI_Slot1                  | 1756-IB16            | Local:1              | 
DI_Slot2                  | 1756-IB16            | Local:1              | 
DO_Slot3                  | 1756-OB16E           | Local:1              | 
AI_Slot4                  | 1756-IF8             | Local:1              | 
AO_Slot5                  | 1756-OF8             | Local:1              | 
AI_Slot6                  | 1756-IF8             | Local:1              | 
```

### Tasks (`extract_tasks.txt`)
```
TASKS - Found 1
================================================================================

TASK: MainTask
  Type: CONTINUOUS
  Priority: 10
  Watchdog: 500 ms
  Scheduled Programs:
    - MainProgram
```

### Global Tags (`extract_tags.txt`) — excerpt
```
Name                           | Usage      | Type/Alias                     | Description
------------------------------ | ---------- | ------------------------------ | --------------------
PT102_PV                       | Local      | Alias->Local:4:I.Ch2Data       | PT-102 Discharge Pressure (barg)
VFD_SpeedCmd                   | Local      | REAL                           | VFD Speed Command (%)
ASC_SurgeMargin                | Local      | REAL                           | Anti Surge Control Surge Margin
TripCode                       | Local      | DINT                           | 1=ESD 2=Fire 3=Vib 4=VFD 5=LO_P...
State                          | Local      | DINT                           | State: 0=Stop 10=Prelube 20=Valves...
```

### Program Logic (`extract_programs.txt`) — excerpt

**Main Routine Structure:**
```
PROGRAM: MainProgram
Main Routine: MainRoutine
===========================================================================

  [ROUTINES & LOGIC] - Found 10

    ============================================================
    ROUTINE: MainRoutine (RLL)
    ============================================================
    [Rung 0]
      /* ========================================================================
BOOSTER GAS COMPRESSOR STATION - PRODUCTION PROGRAM
Controller: 1756-L82E
I/O: Slot1=DI(16pt) Slot2=DI(16pt) Slot3=DO(16pt) Slot4=AI(4ch) Slot5=AO(8ch)
======================================================================== */
      
JSR(R00_AnalogAlarms,0);
      ----------------------------------------
    [Rung 1]
      JSR(R01_Inputs,0);
      ----------------------------------------
```

**Permissives Logic:**
```
    ============================================================
    ROUTINE: R02_Permissives (RLL)
    ============================================================
    [Rung 0]
      /* No Active Trip Latched */
      XIO(TripLatch)OTE(Perm_NoTrip);
      ----------------------------------------
    [Rung 1]
      /* VFD Ready and Not Faulted */
      XIC(VFD_Ready)XIO(VFD_Faulted)XIO(VFD_CommFlt)OTE(Perm_VFD);
      ----------------------------------------
    [Rung 4]
      /* Combine All Permissives */
      XIO(Perm_ESD)XIC(Perm_NoTrip)XIO(Perm_LO_Lvl)XIC(Perm_VFD)XIC(Perm_BDV)XIC(Perm_Instr)OTE(PermOK);
      ----------------------------------------
```

**Trip Processing:**
```
    ============================================================
    ROUTINE: R03_Trips (RLL)
    ============================================================
    [Rung 11]
      /* ===== COMBINE ALL TRIPS ===== */
      [XIO(Trip_ESD) ,XIC(Trip_Fire) ,XIC(Trip_Vib) ,XIC(Trip_VFD) ,XIC(Trip_Comms) ,
       XIC(Trip_LO_P) ,XIC(Trip_DischT) ,XIC(Trip_DischP) ,XIC(Trip_Surge) ]OTE(TripActive);
      ----------------------------------------
    [Rung 12]
      /* Latch Trip */
      XIC(TripActive)OTL(TripLatch);
      ----------------------------------------
```

**Anti-Surge Control:**
```
    ============================================================
    ROUTINE: R06_Control (RLL)
    ============================================================
    [Rung 12]
      /* Surge Margin (%) */
      GRT(ASC_SurgeLimit,0.0)SUB(ASC_Flow,ASC_SurgeLimit,ASC_SurgeMargin)
      DIV(ASC_SurgeMargin,ASC_SurgeLimit,ASC_SurgeMargin)
      MUL(ASC_SurgeMargin,100.0,ASC_SurgeMargin);
      ----------------------------------------
    [Rung 17]
      /* Open Recycle When Margin Low */
      XIC(ASC_Enable)XIC(ASC_Auto)LES(ASC_SurgeMargin,ASC_MarginSP)
      ADD(ASC_RecycleCmd,1.0,ASC_RecycleCmd);
      ----------------------------------------
```

---

## Supported Routine Types

| Type | Support Level | Output |
|------|---------------|--------|
| **RLL** (Ladder Logic) | ✅ Full | Rung numbers, comments, logic text |
| **ST** (Structured Text) | ✅ Full | Complete code with formatting preserved |
| **FBD** (Function Block) | ⚠️ Metadata | Sheet count, block count, wire count |
| **SFC** (Sequential Function Chart) | ⚠️ Metadata | Step names, transition count |

---

## Project Structure

```
rockwell_logic_l5x_extractor/
├── l5x_export.py                    # Main extraction tool
├── README.md                        # This file
├── LICENSE                          # MIT License
│
├── sample_l5x/                      # Sample L5X files
│   └── BoosterCompressor_20260128.L5X
│
└── sample_extracts/                 # Sample output from the tool
    ├── extract_controller_info.txt
    ├── extract_tags.txt
    ├── extract_data_types.txt
    ├── extract_aoi_definitions.txt
    ├── extract_modules.txt
    ├── extract_tasks.txt
    └── extract_programs.txt
```

---

## Use with LLMs

This tool is specifically designed to prepare PLC logic for analysis by Large Language Models. The text output format is ideal for:

- **Code Review** — Ask an LLM to review logic for potential issues
- **Documentation** — Generate descriptions of program functionality  
- **Troubleshooting** — Analyze trip logic or sequence issues
- **Learning** — Explain ladder logic to new engineers

### Example LLM Prompts

Using the sample Booster Compressor program:

```
"Review the R03_Trips routine and identify all conditions that can cause a compressor trip."

"Explain the anti-surge control logic in R06_Control and suggest improvements."

"Document the startup sequence in R04_Sequence as a step-by-step procedure."

"What happens when the State variable equals 95? Trace through all the outputs affected."

"List all the analog instruments and their alarm setpoints from the tags."
```

---

## Limitations

- **Read-Only** — This tool only reads L5X files; it does not modify them
- **L5X Only** — Cannot directly read `.ACD` files (export to L5X from Studio 5000 first)
- **Graphical Logic** — FBD and SFC extract metadata only, not visual layout

---


## Disclaimer

This tool is an **independent open-source project** and is **not affiliated with, endorsed by, or supported by Rockwell Automation**.

- **Verification Required** — Always verify logic in the Studio 5000 environment before making engineering decisions
- **Documentation Only** — The extraction process is intended for documentation and analysis purposes only

---


## Acknowledgments

- Structure and best practices informed by analysis of [Rockwell Automation's official VCS tools](https://github.com/rockwellautomation/ra-logix-designer-vcs-custom-tools)
- L5X format documentation from Rockwell Automation Publication 1756-RM084

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## Changelog

### v2.0.0 (2026-01-28)
- Added extraction for Data Types (UDTs), AOIs, Modules, and Tasks
- Fixed XML attribute mutation bug
- Fixed multiple STContent handling for online edits
- Preserved whitespace in Structured Text code
- Added root element validation for L5X files
- Added type hints throughout codebase
- Included sample L5X project and extracts

### v1.0.0 (Initial Release)
- Basic extraction of controller info, tags, and programs
- Support for RLL and ST routine types