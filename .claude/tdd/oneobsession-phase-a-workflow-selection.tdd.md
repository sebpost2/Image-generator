# TDD Evidence: Per-game ComfyUI workflow (checkpoint) selection

**Source plan**: derived inline during this session (Phase A of a 3-phase plan: oneObsession
anime game, scene→game handoff, unattended multi-hour batch runs). No `*.plan.md` file was
written to disk; the plan was presented and approved in-conversation.

## User journey covered

As the project owner, I want a second game to use a different ComfyUI checkpoint/workflow
(oneObsession/anime instead of LUSTIFY), so that I can reuse this same writer→review→generate
pipeline for a second, visually distinct game.

This slice covers only the config/plumbing layer (which workflow file a game resolves to).
Prompt-style tuning for anime (tag-style vs. descriptive LUSTIFY prompts in
`draft_image_prompts.py`) and the "Add game..." dialog's checkpoint picker are **not** part of
this slice — flagged as follow-up below.

## Task report

| Task | Summary | Validation | Result |
|---|---|---|---|
| 1 | Added `test_games.py` (9 tests) covering fresh-config default, old-string-format migration, and `add_game(..., workflow=...)` | `python -m unittest test_games -v` | RED (5 errors, 1 failure) confirmed for the intended reason (missing `get_active_workflow`, missing `workflow=` kwarg, no migration) before any production edit |
| 2 | `games.py`: added `DEFAULT_WORKFLOW`, `get_active_workflow()`, in-place migration of old string-format game entries, `add_game(name, path, workflow=None)` | `python -m unittest test_games -v` | GREEN (9/9) |
| 3 | `newgame_gen.py`: `_run_one()` now loads the workflow JSON via `games.get_active_workflow()` instead of the hardcoded `WORKFLOW_PATH` constant | `python -m unittest discover -p "test_*.py"` (both repos) + `py_compile` | GREEN, no regressions (Image-generator: 9/9, writer-generator: 21/21) |

## Test specification

| # | What is guaranteed | Test file | Type | Result |
|---|---|---|---|---|
| 1 | A fresh (no `games.json`) config resolves the active workflow to the LUSTIFY default | `test_games.py:test_fresh_config_active_workflow_is_lustify_default` | unit | PASS |
| 2 | `list_games()` still returns `(name, dir)` tuples unchanged (no breakage for existing GUI callers) | `test_games.py:test_fresh_config_list_games_returns_name_dir_tuples` | unit | PASS |
| 3 | A `games.json` written before this change (plain string per game) loads without crashing and defaults to LUSTIFY | `test_games.py:test_old_string_entry_migrates_to_default_workflow` | unit | PASS |
| 4 | That old-format entry is healed to the new dict shape on disk after one `load()` | `test_games.py:test_old_string_entry_healed_on_disk` | unit | PASS |
| 5 | `add_game(name, path, workflow=...)` stores and resolves the given workflow | `test_games.py:test_add_game_with_explicit_workflow` | unit | PASS |
| 6 | `add_game(name, path)` (old 2-arg call sites, e.g. `pipeline_app.py`, `image_app.py`) still works and defaults to LUSTIFY | `test_games.py:test_add_game_without_workflow_defaults_to_lustify` | unit | PASS |

## Coverage and known gaps

- `newgame_gen.py`'s use of `games.get_active_workflow()` is a one-line delegation to
  already-tested `games.py` logic — not independently unit tested, since exercising
  `_run_one()` requires mocking ComfyUI's HTTP API (`post_prompt`/`wait_for_result`), which is
  out of scope for this slice. Verified instead by `py_compile` + full existing suite staying
  green.
- No `oneObsession` game has actually been registered yet (`games.add_game(...)` was only
  exercised in tests) — the real `games.json` on disk still has the old string format and will
  self-heal automatically on next app launch.
- **Not done yet** (flagged in the original plan, not silently dropped):
  - `draft_image_prompts.py` anime/tag-style prompt profile (Phase A step 4)
  - "Add game..." dialog checkpoint/workflow picker in `pipeline_app.py` / `image_app.py`
  - Phase B (scene→game handoff) and Phase C (unattended multi-hour runs)

## Merge evidence

Three checkpoint commits on `Image-generator`'s current branch, not squashed:
- `3f9bba5` test: add reproducer for per-game workflow (checkpoint) selection (RED)
- `13974eb` fix: add per-game workflow (checkpoint) selection to games.py (GREEN)
- `26ccc34` fix: resolve ComfyUI workflow per active game instead of hardcoded LUSTIFY (GREEN, regression-checked)
