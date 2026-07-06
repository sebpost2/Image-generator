# NewGame — Image Generation Pipeline

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
| `scripts/newgame_gen.py` | Generator script — calls the ComfyUI API with a scene's prompt files and saves the result into `NewGame/assets/img/scenes/` |
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

`scripts/newgame_gen.py` has absolute Windows paths pointing at `E:/Proyectos/Games/...`.
Update `WORKFLOW_PATH`, `COMFY_OUTPUT_DIR`, and `TARGET_OUTPUT_DIR` at the top of the file to
match wherever you clone this repo + the `nsfwgame` (NewGame) repo on the new machine.

### 5. Run

```powershell
# 0. Start ComfyUI (must be listening on 127.0.0.1:8188)
# 1. Generate a scene:
python scripts/newgame_gen.py <scene_id> prompts/<scene_id>_pos.txt prompts/<scene_id>_neg.txt
```

## Known open issue

3-person group scenes systematically collapse to 2 visible men (confirmed 6/6 checked
images, not seed noise). See lesson 13 in `Image_Generation_tips/02_lecciones_aprendidas.md`.
1-2 person scenes, backgrounds, and bondage poses are validated solid.
