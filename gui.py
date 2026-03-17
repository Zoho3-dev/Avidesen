"""
Interface graphique pour le pipeline Avidsen.
Lance le scraping et la publication vers Zoho Desk.
"""

import sys
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

from main import (
    discover_all_tutorials,
    fetch_tutorials_content,
    save_tutorials,
    publish_tutorials_to_zoho,
)


class TextRedirector:
    """Redirige stdout/stderr vers un widget ScrolledText."""

    def __init__(self, widget: scrolledtext.ScrolledText):
        self.widget = widget

    def write(self, text: str):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, text)
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")

    def flush(self):
        pass


class App(tk.Tk):
    """Fenêtre principale de l'application."""

    def __init__(self):
        super().__init__()
        self.title("Avidsen – Tutoriels → Zoho Desk")
        self.geometry("780x520")
        self.resizable(True, True)
        self.configure(bg="#f0f4f8")
        self._running = False
        self._build_ui()

    # ── Construction de l'interface ──────────────────────────────────────

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#2E86C1", height=56)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Avidsen – Publication des Tutoriels",
            font=("Segoe UI", 14, "bold"),
            fg="white",
            bg="#2E86C1",
            pady=12,
        ).pack()

        # Zone de boutons
        btn_frame = tk.Frame(self, bg="#f0f4f8", pady=10)
        btn_frame.pack(fill="x", padx=16)

        self.btn_start = ttk.Button(
            btn_frame, text="▶  Lancer le traitement", command=self._on_start
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.status_label = tk.Label(
            btn_frame, text="En attente…", fg="#555", bg="#f0f4f8",
            font=("Segoe UI", 10),
        )
        self.status_label.pack(side="left")

        self.progress = ttk.Progressbar(btn_frame, mode="indeterminate", length=160)
        self.progress.pack(side="right")

        # Zone de log
        log_frame = tk.Frame(self, bg="#f0f4f8")
        log_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.log = scrolledtext.ScrolledText(
            log_frame,
            state="disabled",
            wrap="word",
            font=("Consolas", 9),
            bg="#1e1e2e",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat",
            bd=0,
        )
        self.log.pack(fill="both", expand=True)

    # ── Logique ─────────────────────────────────────────────────────────

    def _on_start(self):
        if self._running:
            return
        self._running = True
        self.btn_start.configure(state="disabled")
        self.progress.start(12)
        self.status_label.configure(text="Traitement en cours…", fg="#2E86C1")
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.configure(state="disabled")

        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _run_pipeline(self):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        redirector = TextRedirector(self.log)
        sys.stdout = redirector
        sys.stderr = redirector

        try:
            # 1. Découverte
            tutorials = discover_all_tutorials()
            if not tutorials:
                print("\n[ERROR] Aucun tutoriel trouvé.")
                return

            # 2. Extraction
            full = fetch_tutorials_content(tutorials)
            if not full:
                print("\n[ERROR] Aucun contenu extrait.")
                return

            # 3. Sauvegarde locale
            save_tutorials(full)

            # 4. Publication
            print("\n" + "=" * 60)
            print("PUBLICATION AUTOMATIQUE SUR ZOHO DESK")
            print("=" * 60)
            publish_tutorials_to_zoho(full)

            print("\n" + "=" * 60)
            print("TERMINÉ")
            print("=" * 60)
            self._set_status("Terminé !", "#27ae60")

        except Exception as exc:
            print(f"\n[ERREUR FATALE] {exc}")
            self._set_status("Erreur !", "#e74c3c")

        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            self._finish()

    # ── Helpers thread-safe ─────────────────────────────────────────────

    def _set_status(self, text: str, color: str):
        self.after(0, lambda: self.status_label.configure(text=text, fg=color))

    def _finish(self):
        def _do():
            self.progress.stop()
            self.btn_start.configure(state="normal")
            self._running = False
        self.after(0, _do)


if __name__ == "__main__":
    app = App()
    app.mainloop()
