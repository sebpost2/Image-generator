"""
Generador de imágenes para NewGame — usa WORKFLOW_MASTER_LUSTIFY.json
(checkpoint LUSTIFY APEX V8, sin LoRA de personaje, ver NewGame/IMAGES.md).

Uso:
  python newgame_gen.py <scene_id> <pos.txt> <neg.txt> [--seed N] [--size WxH]

Guarda el resultado en NewGame/assets/img/scenes/<scene_id>.png.
"""
import json
import sys
import time
import random
import shutil
import urllib.request
from pathlib import Path

COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_PATH = Path("E:/Proyectos/Games/AI/md/WORKFLOW_MASTER_LUSTIFY.json")
COMFY_OUTPUT_DIR = Path("E:/Proyectos/Games/AI/ComfyUI_windows_portable/ComfyUI/output")
TARGET_OUTPUT_DIR = Path("E:/Proyectos/Games/NewGame/assets/img/scenes")


def post_prompt(workflow):
    data = json.dumps({"prompt": workflow, "client_id": "claude_newgame_gen"}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_history(prompt_id):
    with urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}") as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_result(prompt_id, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
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


def main():
    if len(sys.argv) < 4:
        print("Uso: python newgame_gen.py <scene_id> <pos.txt> <neg.txt> [--seed N] [--size WxH]")
        sys.exit(1)

    scene_id = sys.argv[1]
    pos_file = Path(sys.argv[2])
    neg_file = Path(sys.argv[3])

    seed = None
    width, height = 1216, 832
    i = 4
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--seed" and i + 1 < len(sys.argv):
            seed = int(sys.argv[i + 1]); i += 2
        elif arg == "--size" and i + 1 < len(sys.argv):
            w, h = sys.argv[i + 1].split("x")
            width, height = int(w), int(h); i += 2
        else:
            i += 1

    if seed is None or seed < 0:
        seed = random.randint(0, 2**32 - 1)

    positive = pos_file.read_text(encoding="utf-8").strip()
    negative = neg_file.read_text(encoding="utf-8").strip()

    wf = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    wf["3"]["inputs"]["seed"] = seed
    wf["15"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)  # FaceDetailer — randomizar o repite composicion
    wf["16"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)  # Hand Detailer
    wf["5"]["inputs"]["width"] = width
    wf["5"]["inputs"]["height"] = height
    wf["6"]["inputs"]["text"] = positive
    wf["7"]["inputs"]["text"] = negative
    wf["9"]["inputs"]["filename_prefix"] = f"newgame_{scene_id}"

    print(f"[gen] scene={scene_id} seed={seed} size={width}x{height}")
    resp = post_prompt(wf)
    pid = resp["prompt_id"]
    print(f"[gen] prompt_id={pid}, esperando...")
    result = wait_for_result(pid)
    img_path = extract_image_path(result)
    if not img_path or not img_path.exists():
        print("[gen] ERROR: no se encontro imagen en el resultado")
        sys.exit(2)

    TARGET_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = TARGET_OUTPUT_DIR / f"{scene_id}.png"
    shutil.copy2(img_path, target)
    print(f"[gen] OK -> {target}")
    print(f"[gen] src -> {img_path}")


if __name__ == "__main__":
    main()
