# NewGame — Image Generation Pipeline

## Just want to use this, not touch code?

1. Start ComfyUI (run `D:\ComfyUI_windows_portable\run_nvidia_gpu.bat`) and wait for it to
   finish loading.
2. Double-click **`Run_Image_App.bat`** in this folder — no command line needed.

The app lists every scene that has a prompt, shows which ones already have an image (`[x]`)
and which don't (`[ ]`), and lets you generate a selected scene or all the missing ones with
a live progress log. If it says ComfyUI isn't reachable, do step 1 first. This app is fully
standalone — it does not need the writer-generator repo at all.

The detailed manual/CLI docs are below, for setup and troubleshooting.

---

ComfyUI workflow + prompts used to generate NSFW/scene art for **NewGame**. This is a
*pipeline* repo — no game code, no model weights (those are too large for git and are
either public downloads or re-generated, see below).

Read `IMAGES.md` first, then `Image_Generation_tips/00_INDEX.md` (router — don't read the
whole folder, just the file relevant to what you're generating).

## What's in here

| Path | What |
|---|---|
| `WORKFLOW_MASTER_LUSTIFY.json` | The ComfyUI workflow (import via ComfyUI's "Load" or drag into the canvas) |
| `Image_Generation_tips/` | Checkpoints, settings, lessons learned, advanced techniques, LoRA notes |
| `prompts/` | Per-scene `_pos.txt` / `_neg.txt` files for NewGame (rent_event, collectors_event, prologue_*, market_search_*, etc.) |
| `scripts/newgame_gen.py` | Generator script — calls the ComfyUI API with a scene's prompt files and saves the result into the active game's scenes folder (see `games.json`) |
| `scripts/games.py` + `games.json` | Registry of games and which one is active — decides where generated PNGs land |
| `IMAGES.md` | Copy of the pointer doc from the NewGame repo |

## Setup on a new machine

### 1. Install ComfyUI (portable)

- `github.com/comfyanonymous/ComfyUI` — get the Windows portable release.

### 2. Install required custom nodes

Easiest: install ComfyUI-Manager first, then use its "Install Missing Custom Nodes" against
`WORKFLOW_MASTER_LUSTIFY.json` to pull the rest automatically. Manual list if needed:

| Node | Repo |
|---|---|
| ComfyUI-Manager | `github.com/ltdrdata/ComfyUI-Manager` |
| Impact Pack | `github.com/ltdrdata/ComfyUI-Impact-Pack` |
| Impact Subpack | `github.com/ltdrdata/ComfyUI-Impact-Subpack` |
| ControlNet Aux preprocessors | `github.com/Fannovel16/comfyui_controlnet_aux` |
| rgthree-comfy | `github.com/rgthree/rgthree-comfy` |
| DZ-FaceDetailer | `github.com/nicofdga/DZ-FaceDetailer` |

### 3. Download models (CivitAI)

| Model | Where | Notes |
|---|---|---|
| **Checkpoint**: `lustifySDXLNSFW_apexV8.safetensors` (LUSTIFY APEX V8) | CivitAI — search "LUSTIFY" (internal title `lustify_apex`, SDXL 1.0 base) | Exact source URL wasn't recorded when this was first downloaded — re-find via your CivitAI library/history or search |
| `MS_Real_XL_Taped_Lite.safetensors` | `civitai.com/models/344309` | Tape gag variety. Last note: download was incomplete/untested — verify it's not anime-styled before trusting it |
| ~~`badhands.safetensors`~~ | `civitai.com/models/128969/badhands-sdxl-negative-lycorislokr` | Installed but **not used by default** — it suppresses hand-genital contact instead of fixing anatomy |

Place checkpoints in `ComfyUI/models/checkpoints/`, LoRAs in `ComfyUI/models/loras/`.

**No character LoRA is used for NewGame** — generic photorealistic women are resolved entirely
by prompt (unlike the GameBase/Elara pipeline, which is a separate, unrelated setup).

### 4. Update the hardcoded paths

`scripts/newgame_gen.py` has absolute Windows paths. Update `WORKFLOW_PATH` and
`COMFY_OUTPUT_DIR` at the top of the file to match wherever you clone this repo on the new
machine. The output folder(s) — where generated PNGs land — are no longer hardcoded here: they
live in `games.json` (auto-created next to `prompts/` on first run, seeded with the `nsfwgame`
folder). Pick the active game from the *Game:* selector in `Run_Image_App.bat`, or add more
games there; `scripts/games.py` is the single source of truth. A scene can also be pinned to a
specific game via the optional `game` column in `../writer-generator/manifest.csv`.

### 5. Run

```powershell
# 0. Start ComfyUI (must be listening on 127.0.0.1:8188)
# 1. Generate a single scene (standalone, one-off):
python scripts/newgame_gen.py <scene_id> prompts/<scene_id>_pos.txt prompts/<scene_id>_neg.txt
```

`newgame_gen.py` still works standalone, but its core is now `generate_scene(scene_id,
pos_file, neg_file, seed=None, width=..., height=...)`, which the batch runner imports so the
seed/size/workflow-node logic lives in exactly one place.

## Batch generation (multi-scene, automatic GPU handoff)

For generating many scenes, drive the pipeline from the sibling **`../writer-generator`** repo
instead of starting ComfyUI by hand. The dev GPU (RTX 5050, 8GB VRAM) can't hold both the
text model and ComfyUI at once, so `writer-generator/scripts/batch.py` owns the handoff:

```powershell
# from ..\writer-generator :
python scripts\batch.py draft      # phase 1: LLM drafts prompts into writer-generator\drafts\
#   --> review drafts, copy approved *_pos.txt / *_neg.txt into this repo's prompts\
python scripts\batch.py generate   # phase 2: starts ComfyUI, generates, copies PNGs into the game repo
```

Phase 2 kills koboldcpp, cold-starts ComfyUI (polling `/system_stats` for readiness), and for
each scene in the manifest uses `prompts/<scene_id>_pos.txt` plus either a scene-specific
`<scene_id>_neg.txt` or the shared `_explicit_neg.txt` / `_base_neg.txt`. It skips scenes whose
image already exists (unless `--force`) and prints a generated/skipped/failed summary. See
`../writer-generator/README.md` for the manifest format and the full two-phase workflow.

## Known open issue

3-person group scenes systematically collapse to 2 visible men (confirmed 6/6 checked
images, not seed noise). See lesson 13 in `Image_Generation_tips/02_lecciones_aprendidas.md`.
1-2 person scenes, backgrounds, and bondage poses are validated solid.
