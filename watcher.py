"""
Delivery Lab — Session Watcher

Monitors the Sessions folder for new audio files.
When a new file lands, shows a dialog for candidate/session/date,
then runs the full analysis pipeline.

Launch via the desktop shortcut or: python watcher.py
"""

import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

PROJECT_DIR = Path(__file__).parent
SESSIONS_DIR = PROJECT_DIR / "Sessions"
SUPPORTED_EXT = {".mp3", ".mp4", ".wav", ".m4a", ".aac", ".ogg"}
VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv"}
POLL_SECONDS = 5


def get_ffmpeg() -> str:
    """Return the bundled FFmpeg executable path."""
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def convert_to_mp3(src: Path) -> Path:
    """Convert a video file to MP3 alongside the original. Returns the MP3 path."""
    dest = src.with_suffix(".mp3")
    if dest.exists():
        return dest
    ffmpeg = get_ffmpeg()
    print(f"[CONVERT] {src.name} → {dest.name} …")
    result = subprocess.run(
        [ffmpeg, "-y", "-i", str(src), "-vn", "-acodec", "libmp3lame", "-q:a", "2", str(dest)],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed:\n{result.stderr.decode()}")
    mb_before = src.stat().st_size / 1_048_576
    mb_after = dest.stat().st_size / 1_048_576
    print(f"[CONVERT] Done — {mb_before:.0f} MB → {mb_after:.0f} MB")
    return dest


def ask_session_details(audio_path: Path):
    """One-window dialog — candidate name, session label, date."""

    class Dialog(tk.Toplevel):
        def __init__(self, parent):
            super().__init__(parent)
            self.result = None
            self.title("Delivery Lab")
            self.resizable(False, False)
            self.attributes("-topmost", True)

            today = datetime.now()
            date_default = f"{today.day} {today.strftime('%B %Y')}"

            ttk.Label(self, text="New recording detected:", font=("Arial", 9)).grid(
                row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 2)
            )
            ttk.Label(self, text=audio_path.name, font=("Arial", 9, "bold")).grid(
                row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 12)
            )

            ttk.Label(self, text="Candidate name", font=("Arial", 10)).grid(
                row=2, column=0, sticky="w", padx=16, pady=5
            )
            self.candidate = ttk.Entry(self, width=32, font=("Arial", 10))
            self.candidate.grid(row=2, column=1, sticky="ew", padx=(0, 16), pady=5)
            self.candidate.focus()

            ttk.Label(self, text="Session", font=("Arial", 10)).grid(
                row=3, column=0, sticky="w", padx=16, pady=5
            )
            self.session = ttk.Entry(self, width=32, font=("Arial", 10))
            self.session.insert(0, "Mock interview")
            self.session.grid(row=3, column=1, sticky="ew", padx=(0, 16), pady=5)

            ttk.Label(self, text="Date", font=("Arial", 10)).grid(
                row=4, column=0, sticky="w", padx=16, pady=5
            )
            self.date_entry = ttk.Entry(self, width=32, font=("Arial", 10))
            self.date_entry.insert(0, date_default)
            self.date_entry.grid(row=4, column=1, sticky="ew", padx=(0, 16), pady=5)

            btn = ttk.Frame(self)
            btn.grid(row=5, column=0, columnspan=2, sticky="e", padx=16, pady=(12, 16))
            ttk.Button(btn, text="Skip", command=self._skip).pack(side="right", padx=(8, 0))
            ttk.Button(btn, text="Run analysis", command=self._run).pack(side="right")

            self.bind("<Return>", lambda _: self._run())
            self.bind("<Escape>", lambda _: self._skip())
            self.protocol("WM_DELETE_WINDOW", self._skip)

            self.update_idletasks()
            w, h = self.winfo_reqwidth(), self.winfo_reqheight()
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        def _run(self):
            name = self.candidate.get().strip()
            if not name:
                messagebox.showwarning("Missing", "Please enter the candidate name.", parent=self)
                return
            self.result = (
                name,
                self.session.get().strip() or "Media training session",
                self.date_entry.get().strip() or f"{datetime.now().day} {datetime.now().strftime('%B %Y')}",
            )
            self.destroy()

        def _skip(self):
            self.destroy()

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    dlg = Dialog(root)
    root.wait_window(dlg)
    result = dlg.result
    root.destroy()
    return result


def run_pipeline(audio_path: Path, candidate: str, session: str, date: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {candidate} | {session} | {date}")
    print(f"  {audio_path.name}")
    print(f"{'='*60}\n")
    # -B forces Python to ignore and never write .pyc bytecode caches.
    # OneDrive can rewrite .pyc timestamps during sync, which makes Python run
    # stale bytecode even after the source is edited. Running with -B reads the
    # current source every time and closes off that whole class of failure.
    subprocess.run(
        [sys.executable, "-B", "-m", "src.cli", str(audio_path),
         "--candidate", candidate, "--session", session, "--date", date],
        cwd=PROJECT_DIR,
    )


def watch() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Snapshot existing files so we don't reprocess on startup
    seen = {f for f in SESSIONS_DIR.iterdir() if f.suffix.lower() in SUPPORTED_EXT}

    print("=" * 60)
    print("  Reput8ion Delivery Lab — Session Watcher")
    print("=" * 60)
    print(f"\n  Folder:  {SESSIONS_DIR}")
    print(f"  Formats: {', '.join(sorted(SUPPORTED_EXT))}")
    print("\n  Drop an audio file into the Sessions folder.")
    print("  A dialog will appear asking for candidate details.")
    print("  Press Ctrl+C to stop.\n")

    while True:
        time.sleep(POLL_SECONDS)
        try:
            current = {f for f in SESSIONS_DIR.iterdir() if f.suffix.lower() in SUPPORTED_EXT}
        except Exception:
            continue

        new_files = sorted(current - seen)
        seen = current

        for audio_path in new_files:
            print(f"[NEW FILE] {audio_path.name}")
            # Convert video files to MP3 before uploading — much faster pipeline
            if audio_path.suffix.lower() in VIDEO_EXT:
                try:
                    audio_path = convert_to_mp3(audio_path)
                    seen.add(audio_path)  # don't re-trigger on the freshly created MP3
                except Exception as e:
                    print(f"[ERROR] Conversion failed: {e}")
                    continue
            result = ask_session_details(audio_path)
            if result:
                run_pipeline(audio_path, *result)
            else:
                print(f"[SKIPPED]  {audio_path.name}")


if __name__ == "__main__":
    try:
        watch()
    except KeyboardInterrupt:
        print("\n\nWatcher stopped.")
