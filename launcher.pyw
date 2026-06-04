"""
Reput8ion Delivery Lab — GUI Launcher

Double-click to open. No terminal window appears.

Generate Coaching Report : participant recording only. Produces the coach
                           dashboard and a coaching .docx for James.

Generate Client Report   : participant recording + coach commentary.
                           Incorporates James's spoken observations into
                           the leave-behind .docx for the client.

Accepted formats: MP3, MP4, WAV, M4A, AAC, MOV (audio and video).
Coach commentary can also be a plain .txt transcript.
"""

# Prevent Python from reading or writing .pyc bytecode caches. OneDrive can
# rewrite .pyc timestamps during sync, making Python run stale bytecode even
# after the source is edited. This one line closes off that failure mode.
import sys
sys.dont_write_bytecode = True

import os
import queue
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Project root is the directory containing this file.
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


# ── Brand constants ────────────────────────────────────────────────────────────
DEEP_TEAL = "#0A5C6B"
CYAN      = "#0CC0DF"
WHITE     = "#FFFFFF"
LIGHT_BG  = "#F5F8F9"
FONT      = "Arial"

AUDIO_VIDEO_TYPES = [
    ("Audio / Video", "*.mp3 *.mp4 *.wav *.m4a *.aac *.mov *.mkv *.webm"),
    ("All files",     "*.*"),
]
COACH_FILE_TYPES = [
    ("Audio / Video / Text / Word", "*.mp3 *.mp4 *.wav *.m4a *.aac *.mov *.txt *.docx"),
    ("All files",                    "*.*"),
]

def _today() -> str:
    now = datetime.now()
    return f"{now.day} {now.strftime('%B %Y')}"


# ── Main application ───────────────────────────────────────────────────────────

class DeliveryLabApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Reput8ion Delivery Lab")
        self.configure(bg=LIGHT_BG)
        self.resizable(False, False)
        self._q: queue.Queue = queue.Queue()
        self._report_path: Path | None = None
        self._build_ui()
        self._poll()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header bar
        hdr = tk.Frame(self, bg=DEEP_TEAL)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr, text="REPUT8ION DELIVERY LAB",
            bg=DEEP_TEAL, fg=WHITE,
            font=(FONT, 16, "bold"), pady=12,
        ).pack()
        tk.Label(
            hdr, text="Telling your story, delivering with confidence",
            bg=DEEP_TEAL, fg=CYAN,
            font=(FONT, 10, "italic"),
        ).pack()
        tk.Label(hdr, bg=DEEP_TEAL, pady=6).pack()

        body = tk.Frame(self, bg=LIGHT_BG, padx=24, pady=16)
        body.pack(fill=tk.BOTH)

        # ── Session details ─────────────────────────────────────────────────
        self._section(body, "SESSION DETAILS")
        details = tk.Frame(body, bg=LIGHT_BG)
        details.pack(fill=tk.X, pady=(0, 4))

        self.candidate_var = tk.StringVar()
        self.session_var   = tk.StringVar(value="Mock interview")
        self.date_var      = tk.StringVar(value=_today())

        for label, var in [
            ("Candidate name", self.candidate_var),
            ("Session type",   self.session_var),
            ("Date",           self.date_var),
        ]:
            row = tk.Frame(details, bg=LIGHT_BG)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=label, bg=LIGHT_BG, font=(FONT, 11),
                     width=17, anchor=tk.W).pack(side=tk.LEFT)
            tk.Entry(row, textvariable=var, font=(FONT, 11),
                     width=34).pack(side=tk.LEFT)

        ttk.Separator(body).pack(fill=tk.X, pady=10)

        # ── File pickers ────────────────────────────────────────────────────
        self._section(body, "FILES")
        files = tk.Frame(body, bg=LIGHT_BG)
        files.pack(fill=tk.X, pady=(0, 4))

        self.participant_var = tk.StringVar()
        self._picker_row(
            files, "Participant recording",
            self.participant_var, AUDIO_VIDEO_TYPES,
        )

        # Coach commentary — always visible, required only for Client Report
        self.coach_var = tk.StringVar()
        self._picker_row(
            files, "Coach commentary",
            self.coach_var, COACH_FILE_TYPES,
            hint="MP3, MP4, WAV, M4A, MOV, TXT or DOCX  —  optional for Client Report",
        )

        ttk.Separator(body).pack(fill=tk.X, pady=10)

        # ── Action buttons ──────────────────────────────────────────────────
        btn_row = tk.Frame(body, bg=LIGHT_BG)
        btn_row.pack(fill=tk.X, pady=(0, 8))

        self.coaching_btn = tk.Button(
            btn_row,
            text="Generate Coaching Report",
            bg=DEEP_TEAL, fg=WHITE,
            font=(FONT, 11, "bold"),
            padx=16, pady=9,
            relief=tk.FLAT, cursor="hand2",
            command=lambda: self._start("coaching"),
        )
        self.coaching_btn.pack(side=tk.LEFT)

        self.client_btn = tk.Button(
            btn_row,
            text="Generate Client Report",
            bg="#0A7A8C", fg=WHITE,
            font=(FONT, 11, "bold"),
            padx=16, pady=9,
            relief=tk.FLAT, cursor="hand2",
            command=lambda: self._start("client"),
        )
        self.client_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.open_btn = tk.Button(
            btn_row,
            text="Open Report",
            bg=CYAN, fg=WHITE,
            font=(FONT, 11, "bold"),
            padx=16, pady=9,
            relief=tk.FLAT, cursor="hand2",
            state=tk.DISABLED,
            command=self._open_report,
        )
        self.open_btn.pack(side=tk.LEFT, padx=(10, 0))

        # ── Progress log ────────────────────────────────────────────────────
        self._section(body, "PROGRESS")
        self.log = scrolledtext.ScrolledText(
            body, height=14, width=72,
            font=("Courier New", 9),
            bg="#1C2B30", fg="#B8E0E8",
            insertbackground=CYAN,
            state=tk.DISABLED,
        )
        self.log.pack(fill=tk.X, pady=(0, 6))

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(
            body, textvariable=self.status_var,
            bg=LIGHT_BG, fg=DEEP_TEAL,
            font=(FONT, 10, "italic"), anchor=tk.W,
        ).pack(fill=tk.X)

    def _section(self, parent, text):
        tk.Label(
            parent, text=text,
            bg=LIGHT_BG, fg=DEEP_TEAL,
            font=(FONT, 9, "bold"), anchor=tk.W,
        ).pack(fill=tk.X, pady=(6, 2))

    def _picker_row(self, parent, label, var, filetypes, hint=""):
        row = tk.Frame(parent, bg=LIGHT_BG)
        row.pack(fill=tk.X, pady=3)
        tk.Label(row, text=label, bg=LIGHT_BG, font=(FONT, 11),
                 width=21, anchor=tk.W).pack(side=tk.LEFT)
        tk.Entry(row, textvariable=var, font=(FONT, 10),
                 width=30).pack(side=tk.LEFT)

        ft = filetypes

        def pick():
            path = filedialog.askopenfilename(filetypes=ft, title=f"Select: {label}")
            if path:
                var.set(path)

        tk.Button(
            row, text="Browse...",
            font=(FONT, 10), padx=6,
            command=pick,
        ).pack(side=tk.LEFT, padx=(6, 0))

        if hint:
            hint_row = tk.Frame(parent, bg=LIGHT_BG)
            hint_row.pack(fill=tk.X)
            tk.Label(
                hint_row, text=f"    {hint}",
                bg=LIGHT_BG, fg="#5A7A82",
                font=(FONT, 9, "italic"), anchor=tk.W,
            ).pack(side=tk.LEFT)

    # ── Progress polling ───────────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                line = self._q.get_nowait()
                self.log.configure(state=tk.NORMAL)
                self.log.insert(tk.END, line)
                self.log.see(tk.END)
                self.log.configure(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _log(self, msg: str):
        self._q.put(msg + "\n")

    # ── Validation and launch ──────────────────────────────────────────────────

    def _start(self, mode: str):
        """mode is 'coaching' or 'client'."""
        candidate = self.candidate_var.get().strip()
        session   = self.session_var.get().strip() or "Session"
        date      = self.date_var.get().strip()
        p_file    = self.participant_var.get().strip()
        c_file    = self.coach_var.get().strip()

        if not candidate:
            messagebox.showerror("Missing field", "Please enter the candidate's name.")
            return
        if not p_file:
            messagebox.showerror("Missing file", "Please select the participant recording.")
            return
        if not Path(p_file).exists():
            messagebox.showerror("File not found", f"Cannot find:\n{p_file}")
            return
        if mode == "client":
            if c_file and not Path(c_file).exists():
                messagebox.showerror("File not found", f"Cannot find:\n{c_file}")
                return
            # Coach commentary is optional — without it the narrative is generated
            # from the interview alone (same quality, no personalisation layer).

        # Reset UI
        for btn in (self.coaching_btn, self.client_btn):
            btn.configure(state=tk.DISABLED)
        self.open_btn.configure(state=tk.DISABLED)
        self._report_path = None
        self.log.configure(state=tk.NORMAL)
        self.log.delete(1.0, tk.END)
        self.log.configure(state=tk.DISABLED)
        label = "Coaching Report" if mode == "coaching" else "Client Report"
        self.status_var.set(f"Generating {label}...")
        self.coaching_btn.configure(text="Running..." if mode == "coaching" else "Generate Coaching Report")
        self.client_btn.configure(text="Running..." if mode == "client" else "Generate Client Report")

        params = dict(
            audio_file=p_file,
            candidate=candidate,
            session=session,
            date=date,
            mode=mode,
            coach_file=c_file if mode == "client" else "",
        )
        threading.Thread(target=self._run, args=(params,), daemon=True).start()

    def _run(self, params: dict):
        try:
            self._pipeline(params)
        except Exception as exc:
            import traceback
            self._log(f"\n[ERROR] {exc}")
            self._log(traceback.format_exc())
            self.after(0, lambda: self._done(False))
        else:
            self.after(0, lambda: self._done(True))

    # ── Pipeline ───────────────────────────────────────────────────────────────

    def _pipeline(self, p: dict):
        """Delegate entirely to src.pipeline.run_session.

        All orchestration logic lives there so that changes reach both this
        GUI path and the cli.py terminal path simultaneously — the root cause
        of a full session of rework before this refactor.
        """
        from src.pipeline import run_session

        result = run_session(
            audio_path=p["audio_file"],
            candidate=p["candidate"],
            session_label=p["session"],
            date=p["date"],
            mode=p["mode"],
            coach_file=p.get("coach_file", ""),
            log=self._log,
            auto_open_dashboard=(p["mode"] == "coaching"),
        )
        self._report_path = result.report_path

    def _done(self, ok: bool):
        if ok:
            if self._report_path:
                self.status_var.set("Done. Client report ready — click Open Report.")
                self.open_btn.configure(state=tk.NORMAL)
            else:
                self.status_var.set("Done. Coach dashboard open in browser.")
        else:
            self.status_var.set("Error — check log above.")
        self.coaching_btn.configure(state=tk.NORMAL, text="Generate Coaching Report")
        self.client_btn.configure(state=tk.NORMAL,   text="Generate Client Report")

    def _open_report(self):
        if self._report_path and self._report_path.exists():
            os.startfile(str(self._report_path))


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = DeliveryLabApp()
    app.mainloop()
