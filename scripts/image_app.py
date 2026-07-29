"""
Standalone GUI for the Image-generator pipeline -- no command line needed.

Lists every scene that has a prompts/<scene_id>_pos.txt file, shows whether the game
already has a generated image for it, and lets you generate one scene (or all the missing
ones) by reusing generate_scene() from newgame_gen.py. "Generate candidates (pick one)"
instead stages several draws of one scene and pops a thumbnail picker so a human commits the
good one -- for the seed-lottery case where a single prompt yields good and bad draws. Long
work runs on a background thread with a live log; the window never freezes.

This app is deliberately self-contained: it does NOT import anything from writer-generator
and works even if that folder does not exist on the machine. The only thing it needs is
ComfyUI reachable at 127.0.0.1:8188 (start it with ComfyUI's run_nvidia_gpu.bat).

Negative-prompt resolution (kept consistent with batch.py, but without needing the
manifest, which lives in writer-generator):
  * scene-specific prompts/<scene_id>_neg.txt if it exists (always correct); otherwise
  * the shared _explicit_neg.txt or _base_neg.txt, chosen by the "Explicit scenes"
    checkbox. The log states which neg file each scene used.

Launched by Run_Image_App.bat (double-click).
"""
import math
import os
import queue
import sys
import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk, filedialog, scrolledtext

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import newgame_gen  # same folder; reuse generate_scene, do not reimplement
import games        # same folder; the active-game output target lives here

PROMPTS_DIR = REPO_DIR / "prompts"
COMFY_URL = newgame_gen.COMFY_URL
README = REPO_DIR / "README.md"
CANDIDATE_COUNT = 3      # draws produced per "Generate candidates", for the human to pick between
CAND_THUMB_W = 180       # target width per candidate thumbnail in the picker dialog


def active_dir():
    """Live lookup, not a cached constant, so switching the active game takes effect at once."""
    return games.get_active_dir()


def comfy_is_up(timeout=3):
    import urllib.request
    try:
        with urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def list_scenes():
    """Every scene_id that has a *_pos.txt, with whether the active game's image exists."""
    target = active_dir()
    scenes = []
    for pos in sorted(PROMPTS_DIR.glob("*_pos.txt")):
        if pos.name.startswith("_"):
            continue  # shared file, not a scene
        sid = pos.name[:-len("_pos.txt")]
        has_img = (target / f"{sid}.png").exists()
        scenes.append((sid, has_img))
    return scenes


def add_game_dialog(root, on_added):
    """Tiny modal: name entry + folder picker -> games.add_game + make it active."""
    dlg = tk.Toplevel(root)
    dlg.title("Add game")
    dlg.transient(root)
    ttk.Label(dlg, text="Name:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
    name_e = ttk.Entry(dlg, width=30)
    name_e.grid(row=0, column=1, padx=6, pady=6)
    ttk.Label(dlg, text="Scenes folder:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
    path_var = tk.StringVar()
    ttk.Entry(dlg, width=30, textvariable=path_var).grid(row=1, column=1, padx=6, pady=6)
    ttk.Button(dlg, text="Browse...",
               command=lambda: path_var.set(filedialog.askdirectory() or path_var.get()))\
        .grid(row=1, column=2, padx=4)

    def save():
        name, path = name_e.get().strip(), path_var.get().strip()
        if not name or not path:
            messagebox.showwarning("Missing field", "Name and folder are both required.", parent=dlg)
            return
        try:
            games.add_game(name, path)
            games.set_active(name)
        except Exception as e:
            messagebox.showerror("Could not add game", str(e), parent=dlg)
            return
        dlg.destroy()
        on_added()

    ttk.Button(dlg, text="Save", command=save).grid(row=2, column=1, sticky="w", padx=6, pady=8)


def resolve_neg(scene_id, explicit):
    specific = PROMPTS_DIR / f"{scene_id}_neg.txt"
    if specific.exists():
        return specific
    return PROMPTS_DIR / ("_explicit_neg.txt" if explicit else "_base_neg.txt")


class ImageApp:
    def __init__(self, root):
        self.root = root
        root.title("NewGame Image-generator")
        root.geometry("820x680")

        self.q = queue.Queue()
        self.busy = False

        top = ttk.Frame(root)
        top.pack(fill="both", expand=True, padx=8, pady=8)

        gamebar = ttk.Frame(top)
        gamebar.pack(fill="x", pady=(0, 4))
        ttk.Label(gamebar, text="Game:").pack(side="left")
        self.game_combo = ttk.Combobox(gamebar, width=26, state="readonly")
        self.game_combo.pack(side="left", padx=4)
        self.game_combo.bind("<<ComboboxSelected>>", self.on_select_game)
        ttk.Button(gamebar, text="Add game...", command=self.on_add_game).pack(side="left", padx=4)

        ttk.Label(top, text="Scenes with prompts (check = image already generated):")\
            .pack(anchor="w")

        listframe = ttk.Frame(top)
        listframe.pack(fill="both", expand=True, pady=4)
        self.listbox = tk.Listbox(listframe, selectmode="browse", height=14)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(listframe, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=sb.set)

        controls = ttk.Frame(top)
        controls.pack(fill="x", pady=4)
        self.explicit = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Explicit scenes (use explicit negatives when a scene "
                                       "has no _neg file)", variable=self.explicit).pack(side="left")
        self.force = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Re-generate existing (--force)", variable=self.force)\
            .pack(side="left", padx=12)

        btns = ttk.Frame(top)
        btns.pack(fill="x", pady=4)
        self.refresh_btn = ttk.Button(btns, text="Refresh list", command=self.refresh)
        self.refresh_btn.pack(side="left")
        self.gen_sel_btn = ttk.Button(btns, text="Generate selected", command=self.on_generate_selected)
        self.gen_sel_btn.pack(side="left", padx=6)
        self.gen_cand_btn = ttk.Button(btns, text="Generate candidates (pick one)",
                                       command=self.on_generate_candidates)
        self.gen_cand_btn.pack(side="left")
        self.gen_missing_btn = ttk.Button(btns, text="Generate all missing", command=self.on_generate_missing)
        self.gen_missing_btn.pack(side="left", padx=6)
        self.open_btn = ttk.Button(btns, text="Open game scenes folder",
                                   command=lambda: self._open(active_dir()))
        self.open_btn.pack(side="right")

        logframe = ttk.LabelFrame(root, text="Log")
        logframe.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.console = scrolledtext.ScrolledText(logframe, height=12, wrap="word", state="disabled")
        self.console.pack(fill="both", expand=True, padx=4, pady=4)

        self.heavy_btns = [self.gen_sel_btn, self.gen_cand_btn, self.gen_missing_btn]
        self._pump()
        self._refresh_game_combo()
        self.refresh()
        self.log("[app] Ready. Select a scene and Generate, or Generate all missing.")

    # --- game selector -----------------------------------------------------
    def _refresh_game_combo(self):
        names = [n for n, _ in games.list_games()]
        self.game_combo.configure(values=names)
        self.game_combo.set(games.get_active_name())

    def on_select_game(self, event=None):
        games.set_active(self.game_combo.get())
        self.log(f"[game] active game -> {games.get_active_name()} ({active_dir()})")
        self.refresh()

    def on_add_game(self):
        def added():
            self._refresh_game_combo()
            self.refresh()
        add_game_dialog(self.root, added)

    # --- log / thread infra (self-contained) ------------------------------
    def log(self, msg):
        self.q.put(msg if msg.endswith("\n") else msg + "\n")

    def _pump(self):
        try:
            while True:
                s = self.q.get_nowait()
                self.console.configure(state="normal")
                self.console.insert("end", s)
                self.console.see("end")
                self.console.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(80, self._pump)

    def _run(self, target, on_done=None):
        if self.busy:
            self.log("[app] Busy -- wait for the current task to finish.")
            return
        self.busy = True
        for b in self.heavy_btns:
            b.configure(state="disabled")

        class _R:
            def __init__(self, q):
                self.q = q
            def write(self, s):
                if s:
                    self.q.put(s)
            def flush(self):
                pass

        def worker():
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = _R(self.q)
            try:
                target()
            except Exception:
                traceback.print_exc()
            finally:
                sys.stdout, sys.stderr = old_out, old_err
                self.root.after(0, self._finish, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, on_done):
        self.busy = False
        for b in self.heavy_btns:
            b.configure(state="normal")
        # A multi-minute generate can finish with nothing on screen but a log line -- an
        # unmissable beep signals completion without needing a modal popup every time.
        try:
            self.root.bell()
        except Exception:
            pass
        if on_done:
            on_done()

    # --- actions -----------------------------------------------------------
    def _open(self, path):
        Path(path).mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))

    def refresh(self):
        self.scenes = list_scenes()
        self.listbox.delete(0, "end")
        for sid, has_img in self.scenes:
            mark = "[x]" if has_img else "[ ]"
            self.listbox.insert("end", f"{mark} {sid}")
        missing = sum(1 for _, h in self.scenes if not h)
        self.log(f"[app] {len(self.scenes)} scene(s), {missing} without an image.")

    def _check_comfy(self):
        if not comfy_is_up():
            messagebox.showerror(
                "ComfyUI not reachable",
                f"ComfyUI is not answering at {COMFY_URL}.\n\n"
                f"Start it first with ComfyUI's run_nvidia_gpu.bat and wait for it to finish "
                f"loading, then try again.\n\nSee README.md for setup.")
            return False
        return True

    def _generate_batch(self, targets):
        """targets: list of scene_ids. Runs on a background thread."""
        explicit = self.explicit.get()
        force = self.force.get()
        target = active_dir()

        def task():
            done, skipped, failed = [], [], []
            for sid in targets:
                pos = PROMPTS_DIR / f"{sid}_pos.txt"
                neg = resolve_neg(sid, explicit)
                out = target / f"{sid}.png"
                if not pos.exists():
                    print(f"[gen] {sid}: no {pos.name} -> skip")
                    skipped.append(sid); continue
                if not neg.exists():
                    print(f"[gen] {sid}: neg file {neg.name} missing -> FAIL")
                    failed.append(sid); continue
                if out.exists() and not force:
                    print(f"[gen] {sid}: image exists, skip (tick --force to redo)")
                    skipped.append(sid); continue
                print(f"[gen] {sid}: neg={neg.name}")
                try:
                    newgame_gen.generate_scene(sid, pos, neg, seed=None, output_dir=target)
                    done.append(sid)
                except Exception as e:
                    print(f"[gen] {sid}: ERROR {e}")
                    failed.append(sid)
            print(f"\n[gen] === summary ===")
            print(f"[gen]   generated: {len(done)}  {done}")
            print(f"[gen]   skipped:   {len(skipped)}  {skipped}")
            print(f"[gen]   failed:    {len(failed)}  {failed}")

        self._run(task, on_done=self.refresh)

    def on_generate_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("No selection", "Select a scene in the list first.")
            return
        sid = self.scenes[sel[0]][0]
        if not self._check_comfy():
            return
        self.log(f"[app] Generating '{sid}'...")
        self._generate_batch([sid])

    def on_generate_missing(self):
        missing = [sid for sid, has_img in self.scenes if not has_img]
        if not missing:
            messagebox.showinfo("Nothing missing", "Every scene already has an image.")
            return
        if not self._check_comfy():
            return
        self.log(f"[app] Generating {len(missing)} missing scene(s)...")
        self._generate_batch(missing)

    # --- supervised multi-candidate flow (single scene) --------------------
    def on_generate_candidates(self):
        """Stage several draws of the selected scene and let the user pick which one becomes the
        game's image -- for the seed-lottery case where one prompt yields good and bad draws. The
        committed image is only written when a candidate is picked in the follow-up dialog."""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("No selection", "Select a scene in the list first.")
            return
        sid = self.scenes[sel[0]][0]
        pos = PROMPTS_DIR / f"{sid}_pos.txt"
        if not pos.exists():
            messagebox.showinfo("No prompt", f"'{sid}' has no {pos.name} in prompts/.")
            return
        if not self._check_comfy():
            return
        neg = resolve_neg(sid, self.explicit.get())
        holder = {}

        def task():
            print(f"[gen] {sid}: staging {CANDIDATE_COUNT} candidates (neg={neg.name})")
            holder["paths"] = newgame_gen.generate_candidates(sid, pos, neg, count=CANDIDATE_COUNT)

        def done():
            paths = holder.get("paths") or []
            if paths:
                self._open_candidate_picker(sid, paths)
            else:
                self.log(f"[gen] {sid}: no candidates produced (see log).")

        self.log(f"[app] Generating {CANDIDATE_COUNT} candidates for '{sid}' (pick one after)...")
        self._run(task, on_done=done)

    def _open_candidate_picker(self, sid, paths):
        """Modal: show each staged candidate as a thumbnail with a 'Use this one' button. Picking
        commits that draw via newgame_gen.choose_candidate; the rest stay staged (and get wiped on
        the next candidate run for this scene). Stdlib PhotoImage only -- no Pillow."""
        paths = [Path(p) for p in paths if Path(p).exists()]
        if not paths:
            messagebox.showinfo("No candidates", "The candidate files are missing.")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Pick a candidate — {sid}")
        dlg.transient(self.root)
        ttk.Label(dlg, text="None of these is the game's image yet. Click 'Use this one' to commit "
                            "it as " + f"{sid}.png.", wraplength=620, justify="left")\
            .pack(anchor="w", padx=8, pady=(8, 4))
        strip = ttk.Frame(dlg)
        strip.pack(padx=8, pady=4)
        dlg._imgs = []      # keep PhotoImage refs alive for the dialog's lifetime

        def choose(p):
            try:
                target = newgame_gen.choose_candidate(sid, p, output_dir=active_dir())
                self.log(f"[app] '{sid}': committed {p.name} -> {target}")
            except Exception as e:
                messagebox.showerror("Could not commit", str(e), parent=dlg)
                return
            dlg.destroy()
            self.refresh()

        for idx, path in enumerate(paths, start=1):
            col = ttk.Frame(strip)
            col.pack(side="left", padx=6)
            thumb = ttk.Label(col, text=f"candidate {idx}", anchor="center")
            thumb.pack()
            try:
                img = tk.PhotoImage(file=str(path))
                factor = max(1, math.ceil(img.width() / CAND_THUMB_W))
                if factor > 1:
                    img = img.subsample(factor, factor)
                dlg._imgs.append(img)
                thumb.configure(image=img, text="")
            except Exception as e:
                thumb.configure(text=f"candidate {idx}\n(no preview: {e})")
            ttk.Button(col, text="Use this one", command=lambda p=path: choose(p)).pack(pady=(2, 0))

        ttk.Button(dlg, text="Cancel (keep current image)", command=dlg.destroy)\
            .pack(anchor="e", padx=8, pady=8)


def main():
    root = tk.Tk()
    ImageApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
