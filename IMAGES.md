# Image Generation — NewGame

This project's art is AI-generated. The old "sourced GIFs from Twitter/Discord" plan in
`GAME_OVERVIEW.md` §6 is a legacy draft, superseded by this pipeline.

## Where to look

Read **`AI/Image_Generation_tips/00_INDEX.md`** first — it's the router. Don't read the whole
folder, just the file relevant to what you're generating (checkpoints, settings, lessons learned,
advanced techniques, LoRAs).

## Key facts

- Checkpoint: **LUSTIFY APEX V8** (`lustifySDXLNSFW_apexV8.safetensors`) — no character LoRA,
  generic photorealistic women resolved by prompt.
- Workflow: `AI/md/WORKFLOW_MASTER_LUSTIFY.json`.
- This is a **separate pipeline from GameBase's** (Ilusty checkpoint + `elara_vesper_v3` character
  LoRA) — don't mix the two, NewGame has no fixed protagonist to lock a LoRA to.
- Known open issue: 3-person group scenes systematically collapse to 2 visible men (confirmed
  6/6 checked images, not seed noise). See lesson 13 in
  `AI/Image_Generation_tips/02_lecciones_aprendidas.md`. Don't rely on full 3-person-visible
  group scenes until this is fixed.
- 1-2 person scenes, backgrounds, and bondage poses are validated solid.
