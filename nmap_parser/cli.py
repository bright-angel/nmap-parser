# -*- encoding: utf-8 -*-

'''
@File    :   cli.py
@Time    :   2026/06/15
@Author  :   test233
@Version :   1.0.0
'''

"""
Command Line Interface for Nmap Parser
"""

import sys
import argparse

try:
    from .core import NmapConverter
except ImportError:
    from core import NmapConverter  # type: ignore


def main():
    """Main entry point for CLI"""
    converter = NmapConverter()

    parser = argparse.ArgumentParser(
        description='Nmap XML Parser - Generate Excel Report (nmap-parser)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  1. Parse a single XML file:
     nmap-parser scan.xml report.xlsx

  2. Parse a directory (non-recursive):
     nmap-parser ./nmap_scans report.xlsx

  3. Parse a directory (recursive):
     nmap-parser ./nmap_scans report.xlsx -r

  4. Launch GUI mode:
     nmap-parser-gui
        """
    )

    parser.add_argument('input', help='Input path (single XML file or directory)')
    parser.add_argument('output', help='Output Excel file path (.xlsx)')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Recursively search for XML files in directory')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Quiet mode, suppress log output')
    parser.add_argument('-v', '--version', action='version',
                        version='nmap-parser 1.0.0')

    args = parser.parse_args()

    if not args.output.endswith('.xlsx'):
        args.output += '.xlsx'

    try:
        xml_files = converter.get_xml_files(args.input, args.recursive)
        if not xml_files:
            if not args.quiet:
                print(f"{converter.emoji_error} No XML files found")
            sys.exit(1)

        if not args.quiet:
            print(f"{converter.emoji_scan} Found {len(xml_files)} XML file(s)")
            print(f"{converter.emoji_scan} Parsing...")

        all_data = {
            "task_info": [],
            "hosts": [],
            "ports": [],
            "vulns": []
        }

        for xml_file in xml_files:
            try:
                file_data = converter.parse_nmap_xml(xml_file)
                if file_data["task_info"]:
                    all_data["task_info"].append(file_data["task_info"])
                all_data["hosts"].extend(file_data["hosts"])
                all_data["ports"].extend(file_data["ports"])
                all_data["vulns"].extend(file_data["vulns"])

                if not args.quiet:
                    print(f"  {converter.emoji_success} {xml_file}")
            except Exception as e:
                if not args.quiet:
                    print(f"  {converter.emoji_error} {xml_file}: {str(e)}")

        converter.write_to_xlsx(all_data, args.output)

        if not args.quiet:
            stats = converter.get_summary_stats(all_data, len(xml_files))
            print(f"\n{converter.emoji_stats} Summary:")
            print(f"  Files: {stats['files_count']}")
            print(f"  Hosts: {stats['hosts_total']} (up: {stats['hosts_up']})")
            print(f"  Ports: {stats['ports_total']} (open: {stats['ports_open']})")
            print(f"  Scripts/Vulns: {stats['vulns_total']}")
            print(f"\n{converter.emoji_success} Done! Output: {args.output}")

    except Exception as e:
        if not args.quiet:
            print(f"{converter.emoji_error} Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
