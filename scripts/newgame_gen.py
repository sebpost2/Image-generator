"""
Generador de imágenes para NewGame — usa el workflow ComfyUI del juego activo
(games.get_active_workflow(); WORKFLOW_MASTER_LUSTIFY.json por defecto, ver NewGame/IMAGES.md).

Uso (una escena):
  python newgame_gen.py <scene_id> <pos.txt> <neg.txt> [--seed N] [--size WxH]

Guarda el resultado en NewGame/assets/img/scenes/<scene_id>.png.

generate_scene() se importa desde writer-generator/scripts/batch.py para la fase 2 (batch).
Este script asume que ComfyUI ya está corriendo en 127.0.0.1:8188 — el batch runner se
encarga de arrancarlo; para uso standalone, arrancá ComfyUI a mano primero.
"""
import json
import sys
import time
import random
import shutil
import urllib.request
from pathlib import Path

import games

COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_PATH = Path("D:/2_MyScripts/PERSONAL/Image-generator/WORKFLOW_MASTER_LUSTIFY.json")
COMFY_OUTPUT_DIR = Path("D:/ComfyUI_windows_portable/ComfyUI/output")
# Kept for reference / backwards compatibility (this is the literal seeded into a fresh
# games.json default entry); the actual output folder is resolved live via games.py at call
# time so switching the active game takes effect without editing this file.
TARGET_OUTPUT_DIR = Path(games.DEFAULT_DIR)
# Throwaway staging for the supervised multi-candidate flow: generate_candidates() drops the
# raw draws here for a human to preview and pick from, and nothing here is authoritative until
# choose_candidate() copies the picked one into the game folder. Same disposable spirit as the
# untracked output/ dir; a scene's subfolder only ever holds the current round's candidates.
CANDIDATES_DIR = WORKFLOW_PATH.parent / "candidates"
# Rolling per-image timing, so the GUI can show a real "~Xs" estimate instead of a guess.
# Updated after every successful generation; read (never blocks) before starting a new one.
TIMING_FILE = WORKFLOW_PATH.parent / "gen_timing.json"

# 1024x704 (2026-07-23 speed pass, down from 1216x832): same ~1.46 aspect ratio, both multiples
# of 64 for valid SDXL latent dims -- ~40% fewer pixels per sampling step, the single biggest
# remaining speed lever short of cutting the Face Detailer. A scene with an explicit `size` in
# manifest.csv overrides this per-scene; this only changes the fallback.
DEFAULT_WIDTH, DEFAULT_HEIGHT = 1024, 704


def load_timing():
    """{'last_seconds': float, 'avg_seconds': float, 'n': int} or {} if none recorded yet."""
    try:
        return json.loads(TIMING_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _record_timing(seconds):
    data = load_timing()
    n = data.get("n", 0) + 1
    prev_avg = data.get("avg_seconds", seconds)
    avg = prev_avg + (seconds - prev_avg) / n  # incremental mean, no need to store every sample
    try:
        TIMING_FILE.write_text(json.dumps({"last_seconds": seconds, "avg_seconds": avg, "n": n}),
                                encoding="utf-8")
    except Exception:
        pass  # best-effort -- a stale/missing estimate is fine, generation itself must not fail


def estimate_seconds(default=150):
    """Best-guess time for ONE image, from real history if we have any, else `default`
    (rough reasoned guess for the current workflow -- gets replaced by real data after run 1)."""
    return load_timing().get("avg_seconds", default)


class GenerationCancelled(Exception):
    """Raised when a cancel_event fires mid-wait -- distinct from TimeoutError/RuntimeError so
    callers (generate_candidates) can treat it as a clean stop, not a real failure to log/retry."""


def post_prompt(workflow):
    data = json.dumps({"prompt": workflow, "client_id": "claude_newgame_gen"}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_history(prompt_id):
    with urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}") as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_interrupt():
    """Ask ComfyUI to abort whatever prompt is currently executing (its own /interrupt route --
    no body needed). Best-effort: if nothing is running, or the call fails, this is a silent
    no-op -- cancellation must never raise on top of an already-cancelled generation."""
    try:
        req = urllib.request.Request(f"{COMFY_URL}/interrupt", data=b"", method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def wait_for_result(prompt_id, timeout=1200, cancel_event=None):
    # ponytail: 600s was too tight for this workflow (base + highres-fix + 3 detailer passes)
    # on an 8GB laptop GPU -- observed a real completion at 687s that the old timeout cut off
    # 87s early even though ComfyUI had already finished. Raise further if it still times out.
    start = time.time()
    while time.time() - start < timeout:
        if cancel_event is not None and cancel_event.is_set():
            post_interrupt()
            raise GenerationCancelled(f"cancelled while waiting for {prompt_id}")
        hist = get_history(prompt_id)
        if prompt_id in hist:
            return hist[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Timeout esperando prompt {prompt_id}")


def extract_image_path(result):
    outputs = result.get("outputs", {})
    for node_id, out in outputs.items():
        if "images" in out:
            for img in out["images"]:
                return COMFY_OUTPUT_DIR / img.get("subfolder", "") / img["filename"]
    return None


def _run_one(scene_id, pos_file, neg_file, seed, width, height, cancel_event=None):
    """
    Build the LUSTIFY workflow for one scene, submit it to ComfyUI, wait for the result, and
    return the raw ComfyUI source image Path -- WITHOUT copying anything into the game repo.

    This is the reusable core shared by generate_scene() (single committed image) and
    generate_candidates() (several staged draws to pick from): both submit + wait identically;
    they differ only in where the resulting file ends up, which stays out of here on purpose.

    Preserves the working node-index logic:
      node 3  = base KSampler seed (deterministic per scene unless overridden)
      node 19 = highres-fix KSampler seed (randomized, same reason as the detailers below --
                a fixed seed here would stamp the same upscale noise pattern on every image)
      nodes 15/16/17 = FaceDetailer / Hand Detailer / Body Detailer seeds (always randomized,
                       else composition repeats)
      node 5  = empty latent size, node 6/7 = positive/negative text, node 9 = filename prefix
    """
    pos_file = Path(pos_file)
    neg_file = Path(neg_file)

    if seed is None or seed < 0:
        seed = random.randint(0, 2**32 - 1)

    positive = pos_file.read_text(encoding="utf-8").strip()
    negative = neg_file.read_text(encoding="utf-8").strip()

    # Resolved live (not WORKFLOW_PATH) so each game's own checkpoint/workflow is used --
    # e.g. oneObsession's WORKFLOW_ANIME_ONEOBSESSION.json shares the same node layout
    # (seed/size/prompt/filename node ids) as LUSTIFY's, so no other logic here needs to change.
    wf = json.loads(games.get_active_workflow().read_text(encoding="utf-8"))
    wf["3"]["inputs"]["seed"] = seed
    wf["19"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)  # Highres-fix KSampler
    wf["15"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)  # FaceDetailer — randomizar o repite composicion
    wf["16"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)  # Hand Detailer
    wf["17"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)  # Body/Limb Detailer
    wf["5"]["inputs"]["width"] = width
    wf["5"]["inputs"]["height"] = height
    wf["6"]["inputs"]["text"] = positive
    wf["7"]["inputs"]["text"] = negative
    wf["9"]["inputs"]["filename_prefix"] = f"newgame_{scene_id}"

    if cancel_event is not None and cancel_event.is_set():
        raise GenerationCancelled(f"{scene_id}: cancelled before submitting")

    print(f"[gen] scene={scene_id} seed={seed} size={width}x{height}")
    resp = post_prompt(wf)
    pid = resp["prompt_id"]
    print(f"[gen] prompt_id={pid}, esperando...")
    t0 = time.time()
    result = wait_for_result(pid, cancel_event=cancel_event)
    elapsed = time.time() - t0
    print(f"[gen] {scene_id}: image done in {elapsed:.0f}s")
    _record_timing(elapsed)
    img_path = extract_image_path(result)
    if not img_path or not img_path.exists():
        raise RuntimeError("no se encontro imagen en el resultado de ComfyUI")
    return img_path


def generate_scene(scene_id, pos_file, neg_file, seed=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT,
                   output_dir=None):
    """
    Generate one scene and copy the result into the game repo as <scene_id>.png. Returns the
    target Path. This is the unattended one-image-per-scene path (batch.phase_generate uses it);
    its signature and behavior are unchanged from before the candidate refactor.

    output_dir: where the PNG lands; when None it is resolved live via games.get_active_dir()
    so the currently-selected game wins. Pass an explicit dir to override (batch.py does this
    per manifest row so mixed-game manifests always land in the right place).
    """
    img_path = _run_one(scene_id, pos_file, neg_file, seed, width, height)

    out_dir = Path(output_dir) if output_dir is not None else games.get_active_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{scene_id}.png"
    shutil.copy2(img_path, target)
    print(f"[gen] OK -> {target}")
    print(f"[gen] src -> {img_path}")
    return target


def generate_candidates(scene_id, pos_file, neg_file, count=3, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT,
                        on_candidate=None, cancel_event=None):
    """
    Supervised path: generate `count` independent draws of one scene (each a fresh random seed,
    never a fixed one -- the whole point is different draws to pick between) and stage them under
    CANDIDATES_DIR/<scene_id>/candidate_1.png .. candidate_N.png WITHOUT committing any to the
    game. Returns the list of staged candidate Paths actually completed (may be fewer than
    `count` if cancelled early).

    on_candidate(i, path): if given, called right after each candidate is staged -- lets a GUI
    show it immediately instead of waiting for the whole batch (all count draws run sequentially
    on one GPU, so an early candidate can otherwise sit unseen for minutes).

    cancel_event: if given and set (e.g. because the human already picked an earlier candidate),
    checked before each new draw starts (queued draws are simply skipped) and during the wait for
    an in-flight draw (which gets a ComfyUI /interrupt so the GPU stops on it immediately rather
    than finishing a draw nobody will use).

    Nothing here is authoritative: the human picks one and choose_candidate() commits it. The
    scene's candidate folder is wiped at the start of each call so it only ever holds the current
    round's draws, never an accumulation across rounds.
    """
    scene_dir = CANDIDATES_DIR / scene_id
    if scene_dir.exists():
        shutil.rmtree(scene_dir)
    scene_dir.mkdir(parents=True, exist_ok=True)

    candidates = []
    for i in range(1, count + 1):
        if cancel_event is not None and cancel_event.is_set():
            print(f"[gen] {scene_id}: cancelled, skipping remaining candidates ({i}/{count})")
            break
        # Per-candidate progress line: a multi-candidate run is 3x one generation and would
        # otherwise sit silent for minutes, which reads as "nothing happened".
        print(f"[gen] {scene_id}: candidate {i}/{count}...")
        try:
            img_path = _run_one(scene_id, pos_file, neg_file, None, width, height,
                                cancel_event=cancel_event)
        except GenerationCancelled as e:
            print(f"[gen] {scene_id}: {e}")
            break
        dest = scene_dir / f"candidate_{i}.png"
        shutil.copy2(img_path, dest)
        print(f"[gen] {scene_id}: candidate {i}/{count} staged -> {dest}")
        candidates.append(dest)
        if on_candidate is not None:
            try:
                on_candidate(i, dest)
            except Exception:
                pass  # a GUI callback failure must not abort generation
    return candidates


def choose_candidate(scene_id, candidate_path, output_dir=None):
    """
    Commit step for the supervised path: copy the human-picked candidate to <scene_id>.png in the
    game folder and return the target Path. output_dir resolves exactly like generate_scene's
    (explicit override, else the active game). Until this runs, no candidate is the game's image.
    """
    candidate_path = Path(candidate_path)
    out_dir = Path(output_dir) if output_dir is not None else games.get_active_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{scene_id}.png"
    shutil.copy2(candidate_path, target)
    print(f"[gen] chosen {candidate_path.name} -> {target}")
    return target


def main():
    if len(sys.argv) < 4:
        print("Uso: python newgame_gen.py <scene_id> <pos.txt> <neg.txt> [--seed N] [--size WxH] "
              "[--out DIR] [--candidates N]")
        sys.exit(1)

    scene_id = sys.argv[1]
    pos_file = Path(sys.argv[2])
    neg_file = Path(sys.argv[3])

    seed = None
    width, height = DEFAULT_WIDTH, DEFAULT_HEIGHT
    output_dir = None
    candidates = None
    i = 4
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--seed" and i + 1 < len(sys.argv):
            seed = int(sys.argv[i + 1]); i += 2
        elif arg == "--size" and i + 1 < len(sys.argv):
            w, h = sys.argv[i + 1].split("x")
            width, height = int(w), int(h); i += 2
        elif arg == "--out" and i + 1 < len(sys.argv):
            output_dir = Path(sys.argv[i + 1]); i += 2
        elif arg == "--candidates" and i + 1 < len(sys.argv):
            candidates = int(sys.argv[i + 1]); i += 2
        else:
            i += 1

    try:
        if candidates is not None:
            # Staging-only mode for standalone testing: generate N draws and print their paths,
            # committing nothing (a human still has to pick, which the CLI doesn't do).
            paths = generate_candidates(scene_id, pos_file, neg_file, count=candidates,
                                        width=width, height=height)
            print("[gen] candidates staged (none committed):")
            for p in paths:
                print(f"[gen]   {p}")
        else:
            generate_scene(scene_id, pos_file, neg_file, seed=seed, width=width, height=height,
                           output_dir=output_dir)
    except RuntimeError as e:
        print(f"[gen] ERROR: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
