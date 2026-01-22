import xml.etree.ElementTree as ET
import argparse
from pathlib import Path
from datetime import datetime
import os
import sys

class L5XAnalyzer:
    def __init__(self, l5x_file_path):
        self.l5x_file_path = l5x_file_path
        self.tree = None
        self.root = None
        self.ns = {} 
        
        self._load_file()

    def _load_file(self):
        if not os.path.exists(self.l5x_file_path):
            raise FileNotFoundError(f"File not found: {self.l5x_file_path}")
        
        try:
            self.tree = ET.parse(self.l5x_file_path)
            self.root = self.tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"XML Parsing Error: {e}")
        
        if '}' in self.root.tag:
            ns_url = self.root.tag.split('}')[0].strip('{')
            self.ns = {'r': ns_url}
        else:
            self.ns = {}

    def _find(self, path, element=None):
        if element is None: element = self.root
        if self.ns:
            namespaced_path = "/".join([f"r:{tag}" for tag in path.split('/')])
            return element.find(namespaced_path, self.ns)
        return element.find(path)

    def _findall(self, path, element=None):
        if element is None: element = self.root
        if self.ns:
            namespaced_path = "/".join([f"r:{tag}" for tag in path.split('/')])
            return element.findall(namespaced_path, self.ns)
        return element.findall(path)

    def _get_desc(self, element):
        if element is None: return ""
        desc_node = self._find("Description", element)
        if desc_node is not None and desc_node.text:
            return desc_node.text.strip().replace('\n', ' ')
        return ""

    def _get_tag_data(self, tag_element):
        return {
            'Name': tag_element.get('Name', ''),
            'DataType': tag_element.get('DataType', ''),
            'Usage': tag_element.get('Usage', 'Local'),
            'AliasFor': tag_element.get('AliasFor', ''),
            'Description': self._get_desc(tag_element)
        }

    # --- Public Methods ---

    def get_controller_info(self):
        controller = self._find("Controller")
        if controller is not None:
            data = controller.attrib
            data['Description'] = self._get_desc(controller)
            return data
        return {}

    def get_global_tags(self):
        tags = self._findall("Controller/Tags/Tag")
        return [self._get_tag_data(t) for t in tags]

    def get_programs(self):
        programs_list = self._findall("Controller/Programs/Program")
        results = []

        for prog in programs_list:
            prog_name = prog.get('Name')
            prog_desc = self._get_desc(prog)
            
            # Get Local Tags
            local_tags = [self._get_tag_data(t) for t in self._findall("Tags/Tag", prog)]
            
            # Get Routines and Logic
            routines_data = []
            routines = self._findall("Routines/Routine", prog)
            
            for routine in routines:
                r_name = routine.get('Name')
                r_type = routine.get('Type') # RLL, ST, FBD, SFC
                r_desc = self._get_desc(routine)
                logic = []

                # Extract Logic
                if r_type == "RLL":
                    # Ladder Logic: Extract Rungs
                    rungs = self._findall("RLLContent/Rung", routine)
                    for rung in rungs:
                        rung_num = rung.get('Number')
                        rung_comment = ""
                        rung_text = ""
                        
                        comment_node = self._find("Comment", rung)
                        if comment_node is not None and comment_node.text:
                            rung_comment = comment_node.text.strip()
                        
                        text_node = self._find("Text", rung)
                        if text_node is not None and text_node.text:
                            rung_text = text_node.text.strip()

                        logic.append({
                            'Type': 'Rung',
                            'Number': rung_num,
                            'Comment': rung_comment,
                            'Code': rung_text
                        })

                elif r_type == "ST":
                    # Structured Text: Extract Lines
                    lines = self._findall("STContent/Line", routine)
                    st_code = []
                    for line in lines:
                        if line.text:
                            st_code.append(line.text.strip())
                    
                    logic.append({
                        'Type': 'ST_Block',
                        'Code': "\n".join(st_code)
                    })

                # Future
                else:
                    logic.append({'Type': 'Unknown', 'Code': f"Logic parsing for {r_type} not implemented."})

                routines_data.append({
                    'Name': r_name,
                    'Type': r_type,
                    'Description': r_desc,
                    'Logic': logic
                })

            results.append({
                'Name': prog_name,
                'Description': prog_desc,
                'Tags': local_tags,
                'Routines': routines_data
            })
            
        return results


def write_with_timestamp_on_conflict(path_str: Path, text_content: str, encoding: str = "utf-8") -> Path:
    """
    Writes content to a file. If file exists, creates a timestamped version.
    Returns the Path object of the file actually written.
    """
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)

    # 1. Try creating the file
    try:
        with p.open("x", encoding=encoding) as f:
            f.write(text_content)
        return p
    except FileExistsError:
        # 2. If exists, append timestamp
        ts = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        candidate = p.with_name(f"{p.stem}_{ts}{p.suffix}")

        # 3. If timestamped name also exists (fast execution), append counter
        counter = 1
        final_path = candidate
        while final_path.exists():
            final_path = p.with_name(f"{p.stem}_{ts}_{counter}{p.suffix}")
            counter += 1

        with final_path.open("x", encoding=encoding) as f:
            f.write(text_content)

        return final_path
        

def format_tag_line(t):
    """Helper to format a tag line consistently"""
    desc = (t['Description'][:40] + '..') if len(t['Description']) > 40 else t['Description']
    # If it's an Alias, show what it points to
    type_or_alias = f"Alias->{t['AliasFor']}" if t['AliasFor'] else t['DataType']
    
    return f"{t['Name']:<30} | {t['Usage']:<10} | {type_or_alias:<30} | {desc}"


def main():
    parser = argparse.ArgumentParser(description="Rockwell L5X Logic Export Tool")
    parser.add_argument("l5x_path", help="Absolute or relative path to the .L5X file")
    parser.add_argument("out_dir", help="Absolute or relative path to the output directory")
    args = parser.parse_args()

    print(f"Processing file: {args.l5x_path} ...")

    try:
        analyzer = L5XAnalyzer(args.l5x_path)
        out_dir = Path(args.out_dir)

        # 1. Export Controller Info
        # Using list + join is faster than string concatenation +=
        info_lines = []
        info = analyzer.get_controller_info()
        for k, v in info.items():
            info_lines.append(f"{k}: {v}")

        final_path = write_with_timestamp_on_conflict(out_dir / "export_controller_info.txt", "\n".join(info_lines))
        print(f"    > Controller Info exported to {final_path}")

        # 2. Export Global Tags
        tag_lines = []
        g_tags = analyzer.get_global_tags()
        
        # Header
        tag_lines.append(f"{'Name':<30} | {'Usage':<10} | {'Type/Alias':<30} | {'Description'}")
        tag_lines.append(f"{'-'*30} | {'-'*10} | {'-'*30} | {'-'*20}")

        for t in g_tags:
            tag_lines.append(format_tag_line(t))

        final_path = write_with_timestamp_on_conflict(out_dir / "export_tags.txt", "\n".join(tag_lines))
        print(f"    > Global tags exported to {final_path}")

        # 3. Export Programs
        prog_lines = []
        programs = analyzer.get_programs()

        for prog in programs:
            prog_lines.append(f"PROGRAM: {prog['Name']}")
            prog_lines.append(f"Desc:    {prog['Description']}")
            prog_lines.append('='*75)

            # 3.1 Local Tags
            prog_lines.append(f"\n  [LOCAL TAGS] - Found {len(prog['Tags'])}")
            prog_lines.append(f"  {'Name':<30} | {'Usage':<10} | {'Type/Alias':<30} | {'Description'}")
            prog_lines.append(f"  {'-'*30} | {'-'*10} | {'-'*30} | {'-'*20}")
            
            for t in prog['Tags']:
                prog_lines.append("  " + format_tag_line(t))

            # 3.2 Routines & Logic
            prog_lines.append(f"\n  [ROUTINES & LOGIC] - Found {len(prog['Routines'])}")
            
            for routine in prog['Routines']:
                prog_lines.append("\n")
                prog_lines.append(f"    {'='*60}")
                prog_lines.append(f"    ROUTINE: {routine['Name']} ({routine['Type']})")
                if routine['Description']:
                    prog_lines.append(f"    Desc:    {routine['Description']}")
                prog_lines.append(f"    {'='*60}")

                # Print Logic
                for item in routine['Logic']:
                    if item['Type'] == 'Rung':
                        prog_lines.append(f"    [Rung {item['Number']}]")
                        if item['Comment']:
                            prog_lines.append(f"      /* {item['Comment']} */")
                        prog_lines.append(f"      {item['Code']}")
                        prog_lines.append(f"      {'-'*40}")
                    
                    elif item['Type'] == 'ST_Block':
                        prog_lines.append(f"    [Structured Text Code]")
                        prog_lines.append(f"      {'-'*40}")
                        st_lines = item['Code'].split('\n')
                        for line in st_lines:
                            prog_lines.append(f"      {line}")
                    else:
                        prog_lines.append(f"    [Logic] {item['Code']}")
            
            # Separator between programs
            prog_lines.append("\n\n" + "#"*80 + "\n")

        final_path = write_with_timestamp_on_conflict(out_dir / "export_programs.txt", "\n".join(prog_lines))
        print(f"    > Programs exported to {final_path}")

    except FileNotFoundError:
        print(f"Error: The file '{args.l5x_path}' does not exist.")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
