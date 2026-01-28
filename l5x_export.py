import xml.etree.ElementTree as ET
import argparse
from pathlib import Path
from datetime import datetime
import os
import sys
from typing import Dict, List, Any, Optional, Tuple


class L5XAnalyzer:

    # Expected root element name for L5X files
    ROOT_ELEMENT_NAME = "RSLogix5000Content"

    def __init__(self, l5x_file_path: str) -> None:
        self.l5x_file_path: str = l5x_file_path
        self.tree: Optional[ET.ElementTree] = None
        self.root: Optional[ET.Element] = None
        self.ns: Dict[str, str] = {}

        self._load_file()

    def _load_file(self) -> None:
        if not os.path.exists(self.l5x_file_path):
            raise FileNotFoundError(f"File not found: {self.l5x_file_path}")

        try:
            self.tree = ET.parse(self.l5x_file_path)
            self.root = self.tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"XML Parsing Error: {e}")

        # Handle XML namespaces
        if "}" in self.root.tag:
            ns_url = self.root.tag.split("}")[0].strip("{")
            self.ns = {"r": ns_url}
            root_local_name = self.root.tag.split("}")[1]
        else:
            self.ns = {}
            root_local_name = self.root.tag

        # Validate root element
        if root_local_name != self.ROOT_ELEMENT_NAME:
            raise ValueError(
                f"Invalid L5X file: Root element is '{root_local_name}', "
                f"expected '{self.ROOT_ELEMENT_NAME}'"
            )

    def _find(
        self, path: str, element: Optional[ET.Element] = None
    ) -> Optional[ET.Element]:
        if element is None:
            element = self.root
        if self.ns:
            namespaced_path = "/".join([f"r:{tag}" for tag in path.split("/")])
            return element.find(namespaced_path, self.ns)
        return element.find(path)

    def _findall(
        self, path: str, element: Optional[ET.Element] = None
    ) -> List[ET.Element]:
        if element is None:
            element = self.root
        if self.ns:
            namespaced_path = "/".join([f"r:{tag}" for tag in path.split("/")])
            return element.findall(namespaced_path, self.ns)
        return element.findall(path)

    def _get_desc(self, element: Optional[ET.Element]) -> str:
        if element is None:
            return ""
        desc_node = self._find("Description", element)
        if desc_node is not None and desc_node.text:
            return desc_node.text.strip().replace("\n", " ")
        return ""

    def _get_text_content(self, element: Optional[ET.Element]) -> str:
        if element is None:
            return ""
        return element.text if element.text else ""

    def _get_tag_data(self, tag_element: ET.Element) -> Dict[str, str]:
        return {
            "Name": tag_element.get("Name", ""),
            "DataType": tag_element.get("DataType", ""),
            "Usage": tag_element.get("Usage", "Local"),
            "AliasFor": tag_element.get("AliasFor", ""),
            "Radix": tag_element.get("Radix", ""),
            "Description": self._get_desc(tag_element),
        }

    def _extract_rung_comments(self, rung: ET.Element) -> Dict[str, str]:
        comments: Dict[str, str] = {}
        for comment in self._findall("Comment", rung):
            operand = comment.get("Operand", "")
            text = comment.text.strip() if comment.text else ""
            if text:
                if operand:
                    comments[f"Operand_{operand}"] = text
                else:
                    comments["Main"] = text
        return comments

    def _extract_routine_logic(
        self, routine: ET.Element, r_type: str
    ) -> List[Dict[str, Any]]:
        logic: List[Dict[str, Any]] = []

        if r_type == "RLL":
            # Ladder Logic: Extract Rungs
            rungs = self._findall("RLLContent/Rung", routine)
            for rung in rungs:
                rung_num = rung.get("Number", "")
                rung_type = rung.get("Type", "N")  # N=Normal, E=Empty, etc.

                # Get all comments (main + operand)
                comments = self._extract_rung_comments(rung)
                main_comment = comments.get("Main", "")
                operand_comments = {k: v for k, v in comments.items() if k != "Main"}

                # Get rung logic text
                text_node = self._find("Text", rung)
                rung_text = self._get_text_content(text_node)

                logic.append(
                    {
                        "Type": "Rung",
                        "Number": rung_num,
                        "RungType": rung_type,
                        "Comment": main_comment,
                        "OperandComments": operand_comments,
                        "Code": rung_text,
                    }
                )

        elif r_type == "ST":
            # Structured Text: Handle multiple STContent elements (online edits)
            st_contents = self._findall("STContent", routine)

            if not st_contents:
                # Fallback: check for direct Line elements
                lines = self._findall("STContent/Line", routine)
                if lines:
                    st_code = [self._get_text_content(line) for line in lines]
                    logic.append(
                        {
                            "Type": "ST_Block",
                            "OnlineEditType": "",
                            "Code": "\n".join(st_code),
                        }
                    )
            else:
                for st_content in st_contents:
                    # Track if this is an online edit version
                    online_edit_type = st_content.get("OnlineEditType", "")

                    lines = self._findall("Line", st_content)
                    # Preserve original whitespace - don't strip!
                    st_code = [self._get_text_content(line) for line in lines]

                    logic.append(
                        {
                            "Type": "ST_Block",
                            "OnlineEditType": online_edit_type,
                            "Code": "\n".join(st_code),
                        }
                    )

        elif r_type == "FBD":
            # Function Block Diagram
            sheets = self._findall("FBDContent/Sheet", routine)
            block_count = 0
            wire_count = 0

            for sheet in sheets:
                blocks = self._findall("Block", sheet)
                wires = self._findall("Wire", sheet)
                block_count += len(blocks)
                wire_count += len(wires)

            logic.append(
                {
                    "Type": "FBD",
                    "SheetCount": len(sheets),
                    "BlockCount": block_count,
                    "WireCount": wire_count,
                    "Note": "Function Block Diagram - graphical content summary only",
                }
            )

        elif r_type == "SFC":
            # Sequential Function Chart
            steps = self._findall("SFCContent/Step", routine)
            transitions = self._findall("SFCContent/Transition", routine)
            actions = self._findall("SFCContent/ActionStructure", routine)

            step_names = [step.get("Name", "unnamed") for step in steps]

            logic.append(
                {
                    "Type": "SFC",
                    "StepCount": len(steps),
                    "StepNames": step_names,
                    "TransitionCount": len(transitions),
                    "ActionCount": len(actions),
                    "Note": "Sequential Function Chart - structure summary only",
                }
            )

        else:
            logic.append(
                {
                    "Type": "Unknown",
                    "RoutineType": r_type,
                    "Note": f'Logic parsing for routine type "{r_type}" not implemented',
                }
            )

        return logic

    def _extract_routines(self, parent_element: ET.Element) -> List[Dict[str, Any]]:
        routines_data: List[Dict[str, Any]] = []
        routines = self._findall("Routines/Routine", parent_element)

        for routine in routines:
            r_name = routine.get("Name", "")
            r_type = routine.get("Type", "")
            r_desc = self._get_desc(routine)

            logic = self._extract_routine_logic(routine, r_type)

            routines_data.append(
                {"Name": r_name, "Type": r_type, "Description": r_desc, "Logic": logic}
            )

        return routines_data

    # =========================================================================
    # Public Methods
    # =========================================================================

    def get_controller_info(self) -> Dict[str, Any]:
        controller = self._find("Controller")
        if controller is not None:
            # Create a COPY of attributes to avoid mutating the XML tree
            data = dict(controller.attrib)
            data["Description"] = self._get_desc(controller)
            return data
        return {}

    def get_global_tags(self) -> List[Dict[str, str]]:
        tags = self._findall("Controller/Tags/Tag")
        return [self._get_tag_data(t) for t in tags]

    def get_data_types(self) -> List[Dict[str, Any]]:
        data_types = self._findall("Controller/DataTypes/DataType")
        results: List[Dict[str, Any]] = []

        for dt in data_types:
            dt_name = dt.get("Name", "")
            dt_family = dt.get("Family", "")  # StringFamily, NoFamily
            dt_class = dt.get("Class", "")  # User, Predefined

            # Extract members
            members: List[Dict[str, str]] = []
            for member in self._findall("Members/Member", dt):
                members.append(
                    {
                        "Name": member.get("Name", ""),
                        "DataType": member.get("DataType", ""),
                        "Dimension": member.get("Dimension", ""),
                        "Radix": member.get("Radix", ""),
                        "Hidden": member.get("Hidden", "false"),
                        "Description": self._get_desc(member),
                    }
                )

            results.append(
                {
                    "Name": dt_name,
                    "Family": dt_family,
                    "Class": dt_class,
                    "Description": self._get_desc(dt),
                    "Members": members,
                }
            )

        return results

    def get_aoi_definitions(self) -> List[Dict[str, Any]]:
        aois = self._findall(
            "Controller/AddOnInstructionDefinitions/AddOnInstructionDefinition"
        )
        results: List[Dict[str, Any]] = []

        for aoi in aois:
            aoi_name = aoi.get("Name", "")
            aoi_revision = aoi.get("Revision", "")
            aoi_vendor = aoi.get("Vendor", "")

            # Extract Parameters
            params: List[Dict[str, str]] = []
            for param in self._findall("Parameters/Parameter", aoi):
                params.append(
                    {
                        "Name": param.get("Name", ""),
                        "DataType": param.get("DataType", ""),
                        "Usage": param.get("Usage", ""),  # Input, Output, InOut
                        "Required": param.get("Required", "false"),
                        "Visible": param.get("Visible", "true"),
                        "Description": self._get_desc(param),
                    }
                )

            # Extract Local Tags
            local_tags: List[Dict[str, str]] = []
            for tag in self._findall("LocalTags/LocalTag", aoi):
                local_tags.append(self._get_tag_data(tag))

            # Extract Routines
            routines = self._extract_routines(aoi)

            results.append(
                {
                    "Name": aoi_name,
                    "Revision": aoi_revision,
                    "Vendor": aoi_vendor,
                    "Description": self._get_desc(aoi),
                    "Parameters": params,
                    "LocalTags": local_tags,
                    "Routines": routines,
                }
            )

        return results

    def get_modules(self) -> List[Dict[str, Any]]:
        modules = self._findall("Controller/Modules/Module")
        results: List[Dict[str, Any]] = []

        for module in modules:
            mod_name = module.get("Name", "")
            mod_type = module.get("CatalogNumber", "")
            parent = module.get("ParentModule", "")
            parent_port = module.get("ParentModPortId", "")

            # Get ports
            ports: List[Dict[str, str]] = []
            for port in self._findall("Ports/Port", module):
                ports.append(
                    {
                        "Id": port.get("Id", ""),
                        "Address": port.get("Address", ""),
                        "Type": port.get("Type", ""),
                        "Upstream": port.get("Upstream", "false"),
                    }
                )

            results.append(
                {
                    "Name": mod_name,
                    "CatalogNumber": mod_type,
                    "ParentModule": parent,
                    "ParentModPortId": parent_port,
                    "Description": self._get_desc(module),
                    "Ports": ports,
                }
            )

        return results

    def get_tasks(self) -> List[Dict[str, Any]]:
        tasks = self._findall("Controller/Tasks/Task")
        results: List[Dict[str, Any]] = []

        for task in tasks:
            task_name = task.get("Name", "")
            task_type = task.get("Type", "")  # CONTINUOUS, PERIODIC, EVENT
            task_rate = task.get("Rate", "")
            task_priority = task.get("Priority", "")
            task_watchdog = task.get("Watchdog", "")

            # Get scheduled programs
            programs: List[str] = []
            for prog in self._findall("ScheduledPrograms/ScheduledProgram", task):
                prog_name = prog.get("Name", "")
                if prog_name:
                    programs.append(prog_name)

            results.append(
                {
                    "Name": task_name,
                    "Type": task_type,
                    "Rate": task_rate,
                    "Priority": task_priority,
                    "Watchdog": task_watchdog,
                    "Description": self._get_desc(task),
                    "ScheduledPrograms": programs,
                }
            )

        return results

    def get_programs(self) -> List[Dict[str, Any]]:
        programs_list = self._findall("Controller/Programs/Program")
        results: List[Dict[str, Any]] = []

        for prog in programs_list:
            prog_name = prog.get("Name", "")
            prog_desc = self._get_desc(prog)
            prog_main_routine = prog.get("MainRoutineName", "")
            prog_fault_routine = prog.get("FaultRoutineName", "")
            prog_disabled = prog.get("Disabled", "false")

            # Get Local Tags
            local_tags = [
                self._get_tag_data(t) for t in self._findall("Tags/Tag", prog)
            ]

            # Get Routines and Logic
            routines_data = self._extract_routines(prog)

            results.append(
                {
                    "Name": prog_name,
                    "Description": prog_desc,
                    "MainRoutineName": prog_main_routine,
                    "FaultRoutineName": prog_fault_routine,
                    "Disabled": prog_disabled,
                    "Tags": local_tags,
                    "Routines": routines_data,
                }
            )

        return results


# =============================================================================
# Output Functions
# =============================================================================


def format_tag_line(t: Dict[str, str], indent: str = "") -> str:
    desc = (
        (t["Description"][:40] + "..")
        if len(t["Description"]) > 40
        else t["Description"]
    )
    type_or_alias = f"Alias->{t['AliasFor']}" if t["AliasFor"] else t["DataType"]
    return f"{indent}{t['Name']:<30} | {t['Usage']:<10} | {type_or_alias:<30} | {desc}"


def format_member_line(m: Dict[str, str], indent: str = "  ") -> str:
    desc = (
        (m["Description"][:35] + "..")
        if len(m["Description"]) > 35
        else m["Description"]
    )
    dim_str = f"[{m['Dimension']}]" if m["Dimension"] else ""
    return f"{indent}{m['Name']:<25} | {m['DataType']:<20}{dim_str:<6} | {desc}"


def format_parameter_line(p: Dict[str, str], indent: str = "  ") -> str:
    desc = (
        (p["Description"][:30] + "..")
        if len(p["Description"]) > 30
        else p["Description"]
    )
    req = "*" if p.get("Required", "false") == "true" else " "
    return (
        f"{indent}{req}{p['Name']:<24} | {p['Usage']:<8} | {p['DataType']:<20} | {desc}"
    )


def write_with_timestamp_on_conflict(
    path_str: Path, text_content: str, encoding: str = "utf-8"
) -> Path:
    """
    Args:
        path_str: Target file path
        text_content: Content to write
        encoding: File encoding

    Returns:
        Path object of the file actually written
    """
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)

    try:
        with p.open("x", encoding=encoding) as f:
            f.write(text_content)
        return p
    except FileExistsError:
        ts = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        candidate = p.with_name(f"{p.stem}_{ts}{p.suffix}")
        counter = 1
        final_path = candidate
        while final_path.exists():
            final_path = p.with_name(f"{p.stem}_{ts}_{counter}{p.suffix}")
            counter += 1
        with final_path.open("x", encoding=encoding) as f:
            f.write(text_content)
        return final_path


# =============================================================================
# Export Functions
# =============================================================================


def extract_controller_info(analyzer: L5XAnalyzer, out_dir: Path) -> Path:
    lines: List[str] = []
    info = analyzer.get_controller_info()

    # Prioritize important fields first
    priority_fields = ["Name", "ProcessorType", "Revision", "Description"]
    for field in priority_fields:
        if field in info:
            lines.append(f"{field}: {info[field]}")

    # Add remaining fields
    for k, v in info.items():
        if k not in priority_fields:
            lines.append(f"{k}: {v}")

    return write_with_timestamp_on_conflict(
        out_dir / "extract_controller_info.txt", "\n".join(lines)
    )


def extract_tags(analyzer: L5XAnalyzer, out_dir: Path) -> Path:
    lines: List[str] = []
    g_tags = analyzer.get_global_tags()

    lines.append(f"{'Name':<30} | {'Usage':<10} | {'Type/Alias':<30} | {'Description'}")
    lines.append(f"{'-'*30} | {'-'*10} | {'-'*30} | {'-'*20}")

    for t in g_tags:
        lines.append(format_tag_line(t))

    return write_with_timestamp_on_conflict(
        out_dir / "extract_tags.txt", "\n".join(lines)
    )


def extract_data_types(analyzer: L5XAnalyzer, out_dir: Path) -> Path:
    lines: List[str] = []
    data_types = analyzer.get_data_types()

    # Filter to user-defined types only
    user_types = [dt for dt in data_types if dt.get("Class", "") == "User"]

    lines.append(f"USER DEFINED TYPES (UDTs) - Found {len(user_types)}")
    lines.append("=" * 80)

    for dt in user_types:
        lines.append(f"\nUDT: {dt['Name']}")
        if dt["Description"]:
            lines.append(f"Desc: {dt['Description']}")
        lines.append("-" * 60)

        if dt["Members"]:
            lines.append(f"  {'Member':<25} | {'DataType':<26} | {'Description'}")
            lines.append(f"  {'-'*25} | {'-'*26} | {'-'*20}")
            for m in dt["Members"]:
                if m.get("Hidden", "false") != "true":
                    lines.append(format_member_line(m))
        else:
            lines.append("  (No members)")

        lines.append("")

    return write_with_timestamp_on_conflict(
        out_dir / "extract_data_types.txt", "\n".join(lines)
    )


def extract_aoi_definitions(analyzer: L5XAnalyzer, out_dir: Path) -> Path:
    lines: List[str] = []
    aois = analyzer.get_aoi_definitions()

    lines.append(f"ADD-ON INSTRUCTIONS (AOIs) - Found {len(aois)}")
    lines.append("=" * 80)

    for aoi in aois:
        lines.append(f"\n{'#'*80}")
        lines.append(f"AOI: {aoi['Name']}")
        if aoi["Revision"]:
            lines.append(f"Revision: {aoi['Revision']}")
        if aoi["Vendor"]:
            lines.append(f"Vendor: {aoi['Vendor']}")
        if aoi["Description"]:
            lines.append(f"Desc: {aoi['Description']}")
        lines.append("=" * 70)

        # Parameters
        lines.append(f"\n  [PARAMETERS] - Found {len(aoi['Parameters'])}")
        if aoi["Parameters"]:
            lines.append(
                f"   {'Name':<25} | {'Usage':<8} | {'DataType':<20} | {'Description'}"
            )
            lines.append(f"  {'-'*25} | {'-'*8} | {'-'*20} | {'-'*20}")
            for p in aoi["Parameters"]:
                lines.append(format_parameter_line(p))

        # Local Tags
        lines.append(f"\n  [LOCAL TAGS] - Found {len(aoi['LocalTags'])}")
        if aoi["LocalTags"]:
            lines.append(
                f"  {'Name':<30} | {'Usage':<10} | {'Type':<30} | {'Description'}"
            )
            lines.append(f"  {'-'*30} | {'-'*10} | {'-'*30} | {'-'*20}")
            for t in aoi["LocalTags"]:
                lines.append(format_tag_line(t, indent="  "))

        # Routines
        lines.append(f"\n  [ROUTINES] - Found {len(aoi['Routines'])}")
        for routine in aoi["Routines"]:
            lines.extend(format_routine(routine, indent="    "))

        lines.append("")

    return write_with_timestamp_on_conflict(
        out_dir / "extract_aoi_definitions.txt", "\n".join(lines)
    )


def extract_modules(analyzer: L5XAnalyzer, out_dir: Path) -> Path:
    lines: List[str] = []
    modules = analyzer.get_modules()

    lines.append(f"I/O MODULES - Found {len(modules)}")
    lines.append("=" * 80)
    lines.append(
        f"\n{'Name':<25} | {'Catalog Number':<20} | {'Parent':<20} | {'Description'}"
    )
    lines.append(f"{'-'*25} | {'-'*20} | {'-'*20} | {'-'*30}")

    for mod in modules:
        desc = (
            (mod["Description"][:30] + "..")
            if len(mod["Description"]) > 30
            else mod["Description"]
        )
        parent = (
            f"{mod['ParentModule']}:{mod['ParentModPortId']}"
            if mod["ParentModule"]
            else "-"
        )
        lines.append(
            f"{mod['Name']:<25} | {mod['CatalogNumber']:<20} | {parent:<20} | {desc}"
        )

    return write_with_timestamp_on_conflict(
        out_dir / "extract_modules.txt", "\n".join(lines)
    )


def extract_tasks(analyzer: L5XAnalyzer, out_dir: Path) -> Path:
    lines: List[str] = []
    tasks = analyzer.get_tasks()

    lines.append(f"TASKS - Found {len(tasks)}")
    lines.append("=" * 80)

    for task in tasks:
        lines.append(f"\nTASK: {task['Name']}")
        lines.append(f"  Type: {task['Type']}")
        if task["Rate"]:
            lines.append(f"  Rate: {task['Rate']} ms")
        lines.append(f"  Priority: {task['Priority']}")
        if task["Watchdog"]:
            lines.append(f"  Watchdog: {task['Watchdog']} ms")
        if task["Description"]:
            lines.append(f"  Desc: {task['Description']}")

        if task["ScheduledPrograms"]:
            lines.append(f"  Scheduled Programs:")
            for prog in task["ScheduledPrograms"]:
                lines.append(f"    - {prog}")
        lines.append("")

    return write_with_timestamp_on_conflict(
        out_dir / "extract_tasks.txt", "\n".join(lines)
    )


def format_routine(routine: Dict[str, Any], indent: str = "") -> List[str]:
    lines: List[str] = []

    lines.append(f"\n{indent}{'='*60}")
    lines.append(f"{indent}ROUTINE: {routine['Name']} ({routine['Type']})")
    if routine["Description"]:
        lines.append(f"{indent}Desc: {routine['Description']}")
    lines.append(f"{indent}{'='*60}")

    for item in routine["Logic"]:
        if item["Type"] == "Rung":
            lines.append(f"{indent}[Rung {item['Number']}]")
            if item.get("RungType", "N") != "N":
                lines.append(f"{indent}  (Type: {item['RungType']})")
            if item["Comment"]:
                lines.append(f"{indent}  /* {item['Comment']} */")
            # Show operand comments if any
            for op_name, op_comment in item.get("OperandComments", {}).items():
                lines.append(f"{indent}  /* {op_name}: {op_comment} */")
            if item["Code"]:
                lines.append(f"{indent}  {item['Code']}")
            lines.append(f"{indent}  {'-'*40}")

        elif item["Type"] == "ST_Block":
            if item.get("OnlineEditType"):
                lines.append(
                    f"{indent}[Structured Text - Online Edit: {item['OnlineEditType']}]"
                )
            else:
                lines.append(f"{indent}[Structured Text Code]")
            lines.append(f"{indent}  {'-'*40}")
            # Preserve indentation in ST code
            for line in item["Code"].split("\n"):
                lines.append(f"{indent}  {line}")
            lines.append(f"{indent}  {'-'*40}")

        elif item["Type"] == "FBD":
            lines.append(f"{indent}[Function Block Diagram]")
            lines.append(
                f"{indent}  Sheets: {item['SheetCount']}, Blocks: {item['BlockCount']}, Wires: {item['WireCount']}"
            )
            lines.append(f"{indent}  Note: {item['Note']}")

        elif item["Type"] == "SFC":
            lines.append(f"{indent}[Sequential Function Chart]")
            lines.append(
                f"{indent}  Steps: {item['StepCount']}, Transitions: {item['TransitionCount']}, Actions: {item['ActionCount']}"
            )
            if item.get("StepNames"):
                lines.append(f"{indent}  Step Names: {', '.join(item['StepNames'])}")
            lines.append(f"{indent}  Note: {item['Note']}")

        else:
            lines.append(f"{indent}[{item['Type']}]")
            if "Note" in item:
                lines.append(f"{indent}  {item['Note']}")

    return lines


def extract_programs(analyzer: L5XAnalyzer, out_dir: Path) -> Path:
    lines: List[str] = []
    programs = analyzer.get_programs()

    for prog in programs:
        lines.append(f"PROGRAM: {prog['Name']}")
        if prog["Description"]:
            lines.append(f"Desc: {prog['Description']}")
        if prog["MainRoutineName"]:
            lines.append(f"Main Routine: {prog['MainRoutineName']}")
        if prog["FaultRoutineName"]:
            lines.append(f"Fault Routine: {prog['FaultRoutineName']}")
        if prog["Disabled"] == "true":
            lines.append("*** PROGRAM DISABLED ***")
        lines.append("=" * 75)

        # Local Tags
        lines.append(f"\n  [LOCAL TAGS] - Found {len(prog['Tags'])}")
        if prog["Tags"]:
            lines.append(
                f"  {'Name':<30} | {'Usage':<10} | {'Type/Alias':<30} | {'Description'}"
            )
            lines.append(f"  {'-'*30} | {'-'*10} | {'-'*30} | {'-'*20}")
            for t in prog["Tags"]:
                lines.append(format_tag_line(t, indent="  "))

        # Routines & Logic
        lines.append(f"\n  [ROUTINES & LOGIC] - Found {len(prog['Routines'])}")
        for routine in prog["Routines"]:
            lines.extend(format_routine(routine, indent="    "))

        # Program separator
        lines.append("\n\n" + "#" * 80 + "\n")

    return write_with_timestamp_on_conflict(
        out_dir / "extract_programs.txt", "\n".join(lines)
    )


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rockwell L5X Logic Export Tool - Extract PLC logic to text format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python l5x_export.py MyProject.L5X ./output
  python l5x_export.py "C:\\PLC\\Project.L5X" "C:\\Reports"

Output Files:
  - extract_controller_info.txt  : Project metadata
  - extract_tags.txt             : Global (controller-scope) tags
  - extract_data_types.txt       : User Defined Types (UDTs)
  - extract_aoi_definitions.txt  : Add-On Instructions with logic
  - extract_modules.txt          : I/O module configuration
  - extract_tasks.txt            : Task scheduling configuration
  - extract_programs.txt         : Programs with routines and logic
        """,
    )
    parser.add_argument("l5x_path", help="Path to the .L5X file")
    parser.add_argument("out_dir", help="Output directory for exported files")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    print(f"Processing file: {args.l5x_path}")

    try:
        analyzer = L5XAnalyzer(args.l5x_path)
        out_dir = Path(args.out_dir)

        # Export all components
        exports = [
            ("Controller Info", lambda: extract_controller_info(analyzer, out_dir)),
            ("Global Tags", lambda: extract_tags(analyzer, out_dir)),
            ("Data Types (UDTs)", lambda: extract_data_types(analyzer, out_dir)),
            ("Add-On Instructions", lambda: extract_aoi_definitions(analyzer, out_dir)),
            ("I/O Modules", lambda: extract_modules(analyzer, out_dir)),
            ("Tasks", lambda: extract_tasks(analyzer, out_dir)),
            ("Programs", lambda: extract_programs(analyzer, out_dir)),
        ]

        for name, export_func in exports:
            final_path = export_func()
            print(f"  > {name} exported to {final_path}")

        print("\nExport completed successfully!")

    except FileNotFoundError:
        print(f"Error: The file '{args.l5x_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()