# -*- encoding: utf-8 -*-

'''
@File    :   core.py
@Time    :   2026/06/15
@Author  :   test233
@Version :   1.0.0
'''

"""
Core conversion logic for Nmap XML to Excel
"""

import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from pathlib import Path

import xlsxwriter


class NmapConverter:
    """Nmap XML to Excel converter"""

    def __init__(self):
        self.emoji_success = "[OK]"
        self.emoji_info = "[*]"
        self.emoji_warning = "[!]"
        self.emoji_error = "[X]"
        self.emoji_scan = "[>]"
        self.emoji_file = "[F]"
        self.emoji_folder = "[D]"
        self.emoji_excel = "[E]"
        self.emoji_stats = "[=]"

    def get_xml_files(self, input_path: str, recursive: bool = False) -> List[str]:
        """Get all XML files under the given path"""
        xml_files = []
        input_path = os.path.abspath(input_path)

        if os.path.isfile(input_path):
            if input_path.endswith('.xml'):
                xml_files.append(input_path)
            return xml_files

        if os.path.isdir(input_path):
            search_pattern = "**/*.xml" if recursive else "*.xml"
            for xml_file in Path(input_path).glob(search_pattern):
                xml_files.append(str(xml_file))

            xml_files.sort()
            return xml_files

        return []

    def parse_nmap_xml(self, xml_path: str) -> Dict[str, Any]:
        """Parse a single Nmap XML file"""
        result = {
            "task_info": {},
            "hosts": [],
            "ports": [],
            "vulns": []
        }

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            filename = os.path.basename(xml_path)

            result["task_info"] = {
                "xml_file": filename,
                "scanner": root.get('scanner', ''),
                "nmap_version": root.get('version', ''),
                "scan_args": root.get('args', ''),
                "start_time": root.get('start', ''),
                "start_time_str": root.get('startstr', ''),
                "xml_output_version": root.get('xmloutputversion', ''),
                "total_hosts": "",
                "up_hosts": "",
                "down_hosts": "",
                "finish_time": "",
                "finish_time_str": "",
                "elapsed_time": "",
                "exit_status": ""
            }

            runstats = root.find('runstats/finished')
            if runstats is not None:
                result["task_info"]["finish_time"] = runstats.get('time', '')
                result["task_info"]["finish_time_str"] = runstats.get('timestr', '')
                result["task_info"]["elapsed_time"] = runstats.get('elapsed', '')
                result["task_info"]["exit_status"] = runstats.get('exit', '')

            hoststats = root.find('runstats/hosts')
            if hoststats is not None:
                result["task_info"]["total_hosts"] = hoststats.get('total', '')
                result["task_info"]["up_hosts"] = hoststats.get('up', '')
                result["task_info"]["down_hosts"] = hoststats.get('down', '')

            for host in root.findall('host'):
                host_info = {
                    "xml_file": filename,
                    "ip_address": "",
                    "hostname": "",
                    "status": "",
                    "status_reason": "",
                    "status_ttl": "",
                    "start_time": host.get('starttime', ''),
                    "end_time": host.get('endtime', '')
                }

                addr = host.find('address')
                if addr is not None:
                    host_info["ip_address"] = addr.get('addr', '')

                hostnames = host.find('hostnames')
                if hostnames is not None:
                    hostname_elem = hostnames.find('hostname')
                    if hostname_elem is not None:
                        host_info["hostname"] = hostname_elem.get('name', '')

                status = host.find('status')
                if status is not None:
                    host_info["status"] = status.get('state', '')
                    host_info["status_reason"] = status.get('reason', '')
                    host_info["status_ttl"] = status.get('reason_ttl', '')

                result["hosts"].append(host_info)

                ports = host.find('ports')
                if ports is not None:
                    for port in ports.findall('port'):
                        port_info = {
                            "xml_file": filename,
                            "ip_address": host_info["ip_address"],
                            "port_id": port.get('portid', ''),
                            "protocol": port.get('protocol', ''),
                            "state": "",
                            "state_reason": "",
                            "state_ttl": "",
                            "service_name": "",
                            "service_product": "",
                            "service_version": "",
                            "service_extrainfo": "",
                            "service_method": "",
                            "service_conf": "",
                            "cpe": ""
                        }

                        state = port.find('state')
                        if state is not None:
                            port_info["state"] = state.get('state', '')
                            port_info["state_reason"] = state.get('reason', '')
                            port_info["state_ttl"] = state.get('reason_ttl', '')

                        service = port.find('service')
                        if service is not None:
                            port_info["service_name"] = service.get('name', '')
                            port_info["service_product"] = service.get('product', '')
                            port_info["service_version"] = service.get('version', '')
                            port_info["service_extrainfo"] = service.get('extrainfo', '')
                            port_info["service_method"] = service.get('method', '')
                            port_info["service_conf"] = service.get('conf', '')

                        cpe = port.find('cpe')
                        if cpe is not None:
                            port_info["cpe"] = cpe.text if cpe.text else ''

                        result["ports"].append(port_info)

                    for port in ports.findall('port'):
                        for script in port.findall('script'):
                            vuln_info = {
                                "xml_file": filename,
                                "ip_address": host_info["ip_address"],
                                "port_id": port.get('portid', ''),
                                "protocol": port.get('protocol', ''),
                                "script_id": script.get('id', ''),
                                "output": script.get('output', ''),
                                "version": script.get('version', ''),
                                "result": "",
                                "severity": "",
                                "description": "",
                                "risk_factor": "",
                                "see_also": "",
                                "solution": "",
                                "cve": "",
                                "bid": "",
                                "cert": "",
                                "msf_module": "",
                                "osvdb": ""
                            }

                            for elem in script:
                                tag = elem.tag.lower()
                                if tag == 'elem':
                                    elem_key = elem.get('key', '').lower()
                                    elem_text = elem.text if elem.text else ''

                                    if elem_key == 'result':
                                        vuln_info["result"] = elem_text
                                    elif elem_key == 'severity':
                                        vuln_info["severity"] = elem_text
                                    elif elem_key == 'description':
                                        vuln_info["description"] = elem_text
                                    elif elem_key == 'risk_factor':
                                        vuln_info["risk_factor"] = elem_text
                                    elif elem_key == 'see_also':
                                        vuln_info["see_also"] = elem_text
                                    elif elem_key == 'solution':
                                        vuln_info["solution"] = elem_text
                                    elif elem_key == 'cve':
                                        vuln_info["cve"] = elem_text
                                    elif elem_key == 'bid':
                                        vuln_info["bid"] = elem_text
                                    elif elem_key == 'cert':
                                        vuln_info["cert"] = elem_text
                                    elif elem_key == 'msf_module':
                                        vuln_info["msf_module"] = elem_text
                                    elif elem_key == 'osvdb':
                                        vuln_info["osvdb"] = elem_text

                            result["vulns"].append(vuln_info)

            for hosthint in root.findall('hosthint'):
                host_info = {
                    "xml_file": filename,
                    "ip_address": "",
                    "hostname": "",
                    "status": "",
                    "status_reason": "",
                    "status_ttl": "",
                    "start_time": "",
                    "end_time": ""
                }

                addr = hosthint.find('address')
                if addr is not None:
                    host_info["ip_address"] = addr.get('addr', '')

                status = hosthint.find('status')
                if status is not None:
                    host_info["status"] = status.get('state', '')
                    host_info["status_reason"] = status.get('reason', '')
                    host_info["status_ttl"] = status.get('reason_ttl', '')

                result["hosts"].append(host_info)

        except ET.ParseError:
            raise
        except Exception:
            raise

        return result

    def write_to_xlsx(self, data: Dict[str, Any], output_file: str) -> None:
        """Write parsed data to XLSX file"""
        workbook = xlsxwriter.Workbook(output_file)

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        # --- Task Info worksheet ---
        task_worksheet = workbook.add_worksheet("Task Info")
        task_fields = [
            "XML File", "Scanner", "Nmap Version", "Scan Args",
            "Start Time", "Start Time Str", "XML Version", "Total Hosts",
            "Up Hosts", "Down Hosts", "Finish Time", "Finish Time Str",
            "Elapsed (s)", "Exit Status"
        ]

        for col, field in enumerate(task_fields):
            task_worksheet.write(0, col, field, header_format)

        task_worksheet.set_column(0, 0, 20)
        task_worksheet.set_column(1, 2, 12)
        task_worksheet.set_column(3, 3, 80)
        task_worksheet.set_column(4, 4, 15)
        task_worksheet.set_column(5, 5, 22)
        task_worksheet.set_column(6, 6, 12)
        task_worksheet.set_column(7, 9, 10)
        task_worksheet.set_column(10, 10, 15)
        task_worksheet.set_column(11, 11, 22)
        task_worksheet.set_column(12, 13, 12)

        for row, task in enumerate(data["task_info"], start=1):
            task_worksheet.write(row, 0, task["xml_file"], cell_format)
            task_worksheet.write(row, 1, task["scanner"], cell_format)
            task_worksheet.write(row, 2, task["nmap_version"], cell_format)
            task_worksheet.write(row, 3, task["scan_args"], cell_format)
            task_worksheet.write(row, 4, task["start_time"], cell_format)
            task_worksheet.write(row, 5, task["start_time_str"], cell_format)
            task_worksheet.write(row, 6, task["xml_output_version"], cell_format)
            task_worksheet.write(row, 7, task["total_hosts"], cell_format)
            task_worksheet.write(row, 8, task["up_hosts"], cell_format)
            task_worksheet.write(row, 9, task["down_hosts"], cell_format)
            task_worksheet.write(row, 10, task["finish_time"], cell_format)
            task_worksheet.write(row, 11, task["finish_time_str"], cell_format)
            task_worksheet.write(row, 12, task["elapsed_time"], cell_format)
            task_worksheet.write(row, 13, task["exit_status"], cell_format)

        # --- Host Status worksheet ---
        host_worksheet = workbook.add_worksheet("Host Status")
        host_fields = [
            "XML File", "IP Address", "Hostname", "Status", "Status Reason",
            "Status TTL", "Start Time", "End Time"
        ]

        for col, field in enumerate(host_fields):
            host_worksheet.write(0, col, field, header_format)

        host_worksheet.set_column(0, 0, 20)
        host_worksheet.set_column(1, 1, 16)
        host_worksheet.set_column(2, 2, 25)
        host_worksheet.set_column(3, 3, 10)
        host_worksheet.set_column(4, 4, 30)
        host_worksheet.set_column(5, 5, 8)
        host_worksheet.set_column(6, 7, 22)

        for row, host in enumerate(data["hosts"], start=1):
            host_worksheet.write(row, 0, host["xml_file"], cell_format)
            host_worksheet.write(row, 1, host["ip_address"], cell_format)
            host_worksheet.write(row, 2, host["hostname"], cell_format)
            host_worksheet.write(row, 3, host["status"], cell_format)
            host_worksheet.write(row, 4, host["status_reason"], cell_format)
            host_worksheet.write(row, 5, host["status_ttl"], cell_format)
            host_worksheet.write(row, 6, host["start_time"], cell_format)
            host_worksheet.write(row, 7, host["end_time"], cell_format)

        # --- Port & Service worksheet ---
        port_worksheet = workbook.add_worksheet("Port & Service")
        port_fields = [
            "XML File", "IP Address", "Port", "Protocol", "State",
            "State Reason", "State TTL", "Service Name", "Service Product",
            "Service Version", "Service Extra", "Method", "Confidence", "CPE"
        ]

        for col, field in enumerate(port_fields):
            port_worksheet.write(0, col, field, header_format)

        port_worksheet.set_column(0, 0, 20)
        port_worksheet.set_column(1, 1, 16)
        port_worksheet.set_column(2, 3, 8)
        port_worksheet.set_column(4, 4, 10)
        port_worksheet.set_column(5, 5, 30)
        port_worksheet.set_column(6, 6, 8)
        port_worksheet.set_column(7, 7, 15)
        port_worksheet.set_column(8, 9, 20)
        port_worksheet.set_column(10, 10, 30)
        port_worksheet.set_column(11, 12, 10)
        port_worksheet.set_column(13, 13, 50)

        for row, port in enumerate(data["ports"], start=1):
            port_worksheet.write(row, 0, port["xml_file"], cell_format)
            port_worksheet.write(row, 1, port["ip_address"], cell_format)
            port_worksheet.write(row, 2, port["port_id"], cell_format)
            port_worksheet.write(row, 3, port["protocol"], cell_format)
            port_worksheet.write(row, 4, port["state"], cell_format)
            port_worksheet.write(row, 5, port["state_reason"], cell_format)
            port_worksheet.write(row, 6, port["state_ttl"], cell_format)
            port_worksheet.write(row, 7, port["service_name"], cell_format)
            port_worksheet.write(row, 8, port["service_product"], cell_format)
            port_worksheet.write(row, 9, port["service_version"], cell_format)
            port_worksheet.write(row, 10, port["service_extrainfo"], cell_format)
            port_worksheet.write(row, 11, port["service_method"], cell_format)
            port_worksheet.write(row, 12, port["service_conf"], cell_format)
            port_worksheet.write(row, 13, port["cpe"], cell_format)

        # --- Vulnerabilities worksheet ---
        vuln_worksheet = workbook.add_worksheet("Vulnerabilities")
        vuln_fields = [
            "XML File", "IP Address", "Port", "Protocol", "Script ID",
            "Output", "Version", "Result", "Severity", "Description",
            "Risk Factor", "See Also", "Solution", "CVE", "BID",
            "CERT", "MSF Module", "OSVDB"
        ]

        for col, field in enumerate(vuln_fields):
            vuln_worksheet.write(0, col, field, header_format)

        vuln_worksheet.set_column(0, 0, 20)
        vuln_worksheet.set_column(1, 1, 16)
        vuln_worksheet.set_column(2, 4, 10)
        vuln_worksheet.set_column(5, 5, 80)
        vuln_worksheet.set_column(6, 6, 12)
        vuln_worksheet.set_column(7, 7, 20)
        vuln_worksheet.set_column(8, 8, 12)
        vuln_worksheet.set_column(9, 9, 60)
        vuln_worksheet.set_column(10, 10, 15)
        vuln_worksheet.set_column(11, 11, 60)
        vuln_worksheet.set_column(12, 12, 40)
        vuln_worksheet.set_column(13, 17, 15)

        for row, vuln in enumerate(data["vulns"], start=1):
            vuln_worksheet.write(row, 0, vuln["xml_file"], cell_format)
            vuln_worksheet.write(row, 1, vuln["ip_address"], cell_format)
            vuln_worksheet.write(row, 2, vuln["port_id"], cell_format)
            vuln_worksheet.write(row, 3, vuln.get("protocol", ""), cell_format)
            vuln_worksheet.write(row, 4, vuln["script_id"], cell_format)
            vuln_worksheet.write(row, 5, vuln.get("output", ""), cell_format)
            vuln_worksheet.write(row, 6, vuln.get("version", ""), cell_format)
            vuln_worksheet.write(row, 7, vuln.get("result", ""), cell_format)
            vuln_worksheet.write(row, 8, vuln.get("severity", ""), cell_format)
            vuln_worksheet.write(row, 9, vuln.get("description", ""), cell_format)
            vuln_worksheet.write(row, 10, vuln.get("risk_factor", ""), cell_format)
            vuln_worksheet.write(row, 11, vuln.get("see_also", ""), cell_format)
            vuln_worksheet.write(row, 12, vuln.get("solution", ""), cell_format)
            vuln_worksheet.write(row, 13, vuln.get("cve", ""), cell_format)
            vuln_worksheet.write(row, 14, vuln.get("bid", ""), cell_format)
            vuln_worksheet.write(row, 15, vuln.get("cert", ""), cell_format)
            vuln_worksheet.write(row, 16, vuln.get("msf_module", ""), cell_format)
            vuln_worksheet.write(row, 17, vuln.get("osvdb", ""), cell_format)

        workbook.close()

    def get_summary_stats(self, all_data: Dict[str, Any], xml_files_count: int) -> Dict[str, Any]:
        """Get summary statistics"""
        stats = {
            "files_count": xml_files_count,
            "hosts_total": len(all_data['hosts']),
            "hosts_up": sum(1 for h in all_data['hosts'] if h['status'] == 'up'),
            "hosts_down": len(all_data['hosts']) - sum(1 for h in all_data['hosts'] if h['status'] == 'up'),
            "ports_total": len(all_data['ports']),
            "ports_open": sum(1 for p in all_data['ports'] if p['state'] == 'open'),
            "ports_closed": len(all_data['ports']) - sum(1 for p in all_data['ports'] if p['state'] == 'open'),
            "vulns_total": len(all_data['vulns']),
            "scripts_count": len(set(v['script_id'] for v in all_data['vulns'])) if all_data['vulns'] else 0,
        }
        return stats
