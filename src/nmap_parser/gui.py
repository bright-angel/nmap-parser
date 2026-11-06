"""Desktop GUI (optional ``[gui]`` extra).

Threading model
---------------
Tk widgets may only be touched from the thread that created them. The 1.x GUI
updated labels, the progress bar and message boxes directly from a worker
thread, which can hang or crash. Here the worker only pushes messages onto a
``queue.Queue``; a periodic ``after()`` callback drains it on the main thread.
"""

from __future__ import annotations

import queue
import sys
import threading
import traceback
from contextlib import suppress
from typing import Any

from .exceptions import NmapParserError
from .models import ConversionOutcome, Progress
from .service import ConversionService

try:
    from tkinter import filedialog, messagebox

    import customtkinter as ctk
except ImportError:  # the CLI must remain usable without the GUI extra
    ctk = None  # type: ignore[assignment]
    filedialog = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]

GUI_AVAILABLE = ctk is not None
_INSTALL_HINT = "Install the GUI extra: pip install 'nmap-xml2xlsx[gui]'"

# Falling back to ``object`` keeps the module importable on headless systems.
_Base = ctk.CTk if ctk is not None else object


class ConverterApp(_Base):  # type: ignore[misc,valid-type]
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Nmap Parser - XML to Excel")
        self.geometry("760x620")
        self.minsize(640, 560)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._worker_thread: threading.Thread | None = None

        self._create_widgets()
        self.after(80, self._drain_queue)

    # ------------------------------------------------------------------ UI
    def _create_widgets(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(7, weight=1)

        ctk.CTkLabel(
            self,
            text="Nmap Parser - XML to Excel",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, pady=(20, 16), padx=20)

        ctk.CTkLabel(self, text="Input path:").grid(
            row=1,
            column=0,
            padx=(20, 10),
            pady=8,
            sticky="w",
        )
        self.input_entry = ctk.CTkEntry(
            self,
            placeholder_text="XML file or a directory containing XML files",
        )
        self.input_entry.grid(row=1, column=1, padx=(0, 8), pady=8, sticky="ew")
        ctk.CTkButton(self, text="File...", width=76, command=self._browse_input_file).grid(
            row=1,
            column=2,
            padx=(0, 6),
            pady=8,
        )
        ctk.CTkButton(self, text="Folder...", width=84, command=self._browse_input_dir).grid(
            row=1,
            column=3,
            padx=(0, 20),
            pady=8,
        )

        ctk.CTkLabel(self, text="Output file:").grid(
            row=2,
            column=0,
            padx=(20, 10),
            pady=8,
            sticky="w",
        )
        self.output_entry = ctk.CTkEntry(
            self,
            placeholder_text="report.xlsx",
        )
        self.output_entry.grid(row=2, column=1, padx=(0, 8), pady=8, sticky="ew")
        ctk.CTkButton(self, text="Browse...", width=88, command=self._browse_output).grid(
            row=2,
            column=2,
            columnspan=2,
            padx=(0, 20),
            pady=8,
            sticky="w",
        )

        options = ctk.CTkFrame(self)
        options.grid(row=3, column=0, columnspan=4, padx=20, pady=12, sticky="ew")
        self.recursive_checkbox = ctk.CTkCheckBox(
            options,
            text="Recursively search subdirectories",
        )
        self.recursive_checkbox.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.convert_btn = ctk.CTkButton(
            self,
            text="Start Conversion",
            command=self._start_conversion,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40,
        )
        self.convert_btn.grid(row=4, column=0, columnspan=4, padx=20, pady=(4, 16), sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="Ready", wraplength=700, justify="left")
        self.status_label.grid(row=5, column=0, columnspan=4, padx=20, pady=(0, 8), sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=6, column=0, columnspan=4, padx=20, pady=(0, 12), sticky="ew")
        self.progress_bar.set(0)

        self.log_text = ctk.CTkTextbox(self, state="disabled")
        self.log_text.grid(row=7, column=0, columnspan=4, padx=20, pady=(0, 20), sticky="nsew")

    # -------------------------------------------------------------- browse
    @staticmethod
    def _set_entry(entry: Any, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    def _browse_input_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select an Nmap XML file",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if path:
            self._set_entry(self.input_entry, path)

    def _browse_input_dir(self) -> None:
        path = filedialog.askdirectory(title="Select a folder of Nmap XML files")
        if path:
            self._set_entry(self.input_entry, path)

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Excel report",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        )
        if path:
            self._set_entry(self.output_entry, path)

    # ------------------------------------------------------------- actions
    def _start_conversion(self) -> None:
        # Always read the entries: typed paths used to be ignored because the
        # 1.x GUI only stored the result of the file dialogs.
        input_path = self.input_entry.get().strip()
        output_path = self.output_entry.get().strip()
        if not input_path:
            messagebox.showerror("Error", "Please choose an XML file or a directory")
            return
        if not output_path:
            messagebox.showerror("Error", "Please choose an output Excel file")
            return
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return

        self.convert_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="Scanning input path...")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        recursive = bool(self.recursive_checkbox.get())
        self._log(f"Input    : {input_path}")
        self._log(f"Output   : {output_path}")
        self._log(f"Recursive: {'Yes' if recursive else 'No'}")
        self._log("-" * 56)

        self._worker_thread = threading.Thread(
            target=self._run_conversion,
            args=(input_path, output_path, recursive),
            daemon=True,
        )
        self._worker_thread.start()

    def _run_conversion(self, input_path: str, output_path: str, recursive: bool) -> None:
        """Worker thread: never touches a Tk widget directly."""

        def on_progress(event: Progress) -> None:
            if event.stage == "discover" and event.total:
                self._queue.put(("log", f"Found {event.total} XML file(s)"))
            elif event.stage == "parse" and event.path is not None:
                is_ok = event.message == "ok"
                detail = event.path.name if is_ok else event.message
                self._queue.put(("log", f"  {'[OK]' if is_ok else '[X]'} {detail}"))
                self._queue.put(("progress", event.fraction))
            elif event.stage == "write":
                self._queue.put(("status", "Generating Excel report..."))
            elif event.stage == "done":
                self._queue.put(("progress", 1.0))

        try:
            outcome = ConversionService(progress=on_progress).convert(
                input_path,
                output_path,
                recursive=recursive,
            )
        except NmapParserError as exc:
            self._queue.put(("error", str(exc)))
        except Exception as exc:  # keep the UI alive on unexpected failures
            self._queue.put(("error", f"Unexpected error: {exc}"))
            traceback.print_exc(file=sys.stderr)
        else:
            self._queue.put(("done", outcome))

    # -------------------------------------------------- main-thread updates
    def _drain_queue(self) -> None:
        """Marshal worker messages onto the Tk main thread."""
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "status":
                    self.status_label.configure(text=payload)
                elif kind == "progress":
                    self.progress_bar.set(float(payload))
                elif kind == "done":
                    self._on_done(payload)
                elif kind == "error":
                    self._on_error(payload)
        except queue.Empty:
            pass
        finally:
            # The window may already be destroyed by the time this fires.
            with suppress(Exception):
                self.after(80, self._drain_queue)

    def _log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _on_done(self, outcome: ConversionOutcome) -> None:
        stats = outcome.stats
        self._log("-" * 56)
        self._log(f"Parsed   : {stats.files_ok} ok, {stats.files_failed} failed")
        self._log(f"Hosts    : {stats.hosts_total} (up {stats.hosts_up})")
        self._log(f"Ports    : {stats.ports_total} (open {stats.ports_open})")
        self._log(f"Findings : {stats.findings_total}")
        self._log(f"Output   : {outcome.output}")
        self.status_label.configure(text="Conversion complete")
        self.convert_btn.configure(state="normal")
        detail = f"Output: {outcome.output}"
        if outcome.failures:
            detail += f"\n\n{len(outcome.failures)} file(s) could not be parsed."
        messagebox.showinfo("Success", f"Conversion complete!\n\n{detail}")

    def _on_error(self, message: str) -> None:
        self._log(f"[X] {message}")
        self.status_label.configure(text="Conversion failed")
        self.convert_btn.configure(state="normal")
        messagebox.showerror("Error", message)


def main() -> int:
    """GUI entry point. Returns 2 when the desktop stack is unavailable."""
    if not GUI_AVAILABLE:
        print(f"nmap-parser GUI is not available.\n{_INSTALL_HINT}", file=sys.stderr)
        return 2
    try:
        app = ConverterApp()
        app.mainloop()
    except Exception as exc:  # e.g. TclError on a machine without a display
        print(f"Cannot start GUI: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
