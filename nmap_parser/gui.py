# -*- encoding: utf-8 -*-

'''
@File    :   gui.py
@Time    :   2026/06/15
@Author  :   test233
@Version :   1.0.0
'''

"""
Graphical User Interface for Nmap Parser
Uses CustomTkinter for a modern look
"""

import os
import sys
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    from .core import NmapConverter
except ImportError:
    from core import NmapConverter  # type: ignore


class ConverterApp(ctk.CTk):
    """Main application window"""

    def __init__(self):
        super().__init__()

        self.converter = NmapConverter()
        self.input_path = None
        self.output_path = None
        self.recursive = False

        self.title("Nmap Parser - XML to Excel")
        self.geometry("700x600")
        self.minsize(600, 600)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._create_widgets()

    def _create_widgets(self):
        """Create UI widgets"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)

        title_label = ctk.CTkLabel(
            self,
            text="Nmap Parser - XML to Excel",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(20, 10), padx=20)

        input_label = ctk.CTkLabel(self, text="Input Path:")
        input_label.grid(row=1, column=0, pady=10, padx=(20, 10), sticky="w")

        self.input_entry = ctk.CTkEntry(self, placeholder_text="Select XML file or directory")
        self.input_entry.grid(row=1, column=1, pady=10, padx=(0, 10), sticky="ew")

        input_btn = ctk.CTkButton(self, text="Browse...", command=self._browse_input, width=80)
        input_btn.grid(row=1, column=2, pady=10, padx=(0, 20))

        output_label = ctk.CTkLabel(self, text="Output File:")
        output_label.grid(row=2, column=0, pady=10, padx=(20, 10), sticky="w")

        self.output_entry = ctk.CTkEntry(self, placeholder_text="Select output Excel file path")
        self.output_entry.grid(row=2, column=1, pady=10, padx=(0, 10), sticky="ew")

        output_btn = ctk.CTkButton(self, text="Browse...", command=self._browse_output, width=80)
        output_btn.grid(row=2, column=2, pady=10, padx=(0, 20))

        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=3, column=0, columnspan=3, pady=10, padx=20, sticky="ew")

        self.recursive_checkbox = ctk.CTkCheckBox(
            options_frame, text="Recursively search subdirectories",
            command=self._toggle_recursive
        )
        self.recursive_checkbox.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.convert_btn = ctk.CTkButton(
            self,
            text="Start Conversion",
            command=self._start_conversion,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40
        )
        self.convert_btn.grid(row=4, column=0, columnspan=3, pady=20, padx=20, sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="", wraplength=600, justify="left")
        self.status_label.grid(row=5, column=0, columnspan=3, pady=(0, 20), padx=20, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=6, column=0, columnspan=3, pady=(0, 20), padx=20, sticky="ew")
        self.progress_bar.set(0)

        self.info_text = ctk.CTkTextbox(self, state="disabled", height=150)
        self.info_text.grid(row=7, column=0, columnspan=3, pady=(0, 20), padx=20, sticky="ew")

    def _browse_input(self):
        """Browse for input file or directory"""
        path = filedialog.askopenfilename(
            title="Select Nmap XML file",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if path:
            self.input_path = path
            self.input_entry.delete(0, 'end')
            self.input_entry.insert(0, path)

    def _browse_output(self):
        """Browse for output file"""
        path = filedialog.asksaveasfilename(
            title="Save Excel file",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if path:
            self.output_path = path
            self.output_entry.delete(0, 'end')
            self.output_entry.insert(0, path)

    def _toggle_recursive(self):
        """Toggle recursive option"""
        self.recursive = not self.recursive

    def _log_message(self, message):
        """Add message to log"""
        self.info_text.configure(state="normal")
        self.info_text.insert("end", message + "\n")
        self.info_text.see("end")
        self.info_text.configure(state="disabled")

    def _update_status(self, message):
        """Update status label"""
        self.status_label.configure(text=message)

    def _start_conversion(self):
        """Start conversion in background thread"""
        if not self.input_path:
            messagebox.showerror("Error", "Please select an input XML file or directory")
            return

        if not self.output_path:
            messagebox.showerror("Error", "Please select an output Excel file path")
            return

        self.convert_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.configure(state="disabled")

        thread = threading.Thread(target=self._run_conversion)
        thread.daemon = True
        thread.start()

    def _run_conversion(self):
        """Run conversion process"""
        try:
            self._update_status(f"{self.converter.emoji_scan} Scanning input path...")
            self._log_message(f"Input: {self.input_path}")
            self._log_message(f"Output: {self.output_path}")
            self._log_message(f"Recursive: {'Yes' if self.recursive else 'No'}")
            self._log_message("")

            xml_files = self.converter.get_xml_files(self.input_path, self.recursive)

            if not xml_files:
                self._update_status(f"{self.converter.emoji_error} No XML files found")
                messagebox.showerror("Error", "No XML files found")
                self.convert_btn.configure(state="normal")
                return

            self._log_message(f"Found {len(xml_files)} XML file(s):")
            for f in xml_files:
                self._log_message(f"  - {os.path.basename(f)}")
            self._log_message("")

            self._update_status(f"{self.converter.emoji_scan} Parsing {len(xml_files)} file(s)...")

            all_data = {
                "task_info": [],
                "hosts": [],
                "ports": [],
                "vulns": []
            }

            success_count = 0
            fail_count = 0

            for i, xml_file in enumerate(xml_files):
                try:
                    file_data = self.converter.parse_nmap_xml(xml_file)
                    if file_data["task_info"]:
                        all_data["task_info"].append(file_data["task_info"])
                    all_data["hosts"].extend(file_data["hosts"])
                    all_data["ports"].extend(file_data["ports"])
                    all_data["vulns"].extend(file_data["vulns"])
                    success_count += 1
                    self._log_message(
                        f"{self.converter.emoji_success} {os.path.basename(xml_file)}"
                    )
                except Exception as e:
                    fail_count += 1
                    self._log_message(
                        f"{self.converter.emoji_error} {os.path.basename(xml_file)}: {str(e)}"
                    )

                progress = (i + 1) / len(xml_files)
                self.progress_bar.set(progress)

            self._update_status(f"{self.converter.emoji_excel} Generating Excel file...")
            self._log_message("")

            self.converter.write_to_xlsx(all_data, self.output_path)

            stats = self.converter.get_summary_stats(all_data, len(xml_files))

            self._log_message("=" * 50)
            self._log_message(f"{self.converter.emoji_stats} Summary:")
            self._log_message(f"  Successfully parsed: {success_count} file(s)")
            if fail_count > 0:
                self._log_message(f"  Failed: {fail_count} file(s)")
            self._log_message(f"  Total hosts: {stats['hosts_total']} (up: {stats['hosts_up']})")
            self._log_message(f"  Total ports: {stats['ports_total']} (open: {stats['ports_open']})")
            self._log_message(f"  Scripts/Vulns: {stats['vulns_total']}")
            self._log_message("=" * 50)

            self._update_status(f"{self.converter.emoji_success} Conversion successful!")
            self._log_message(f"\n{self.converter.emoji_success} Output file: {self.output_path}")

            messagebox.showinfo("Success", f"Conversion complete!\n\nOutput: {self.output_path}")

        except Exception as e:
            self._update_status(f"{self.converter.emoji_error} Conversion failed")
            self._log_message(f"{self.converter.emoji_error} Error: {str(e)}")
            messagebox.showerror("Error", f"Conversion failed:\n{str(e)}")

        finally:
            self.convert_btn.configure(state="normal")


def main():
    """Main entry point for GUI"""
    app = ConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
