"""
Multi-game output-target registry for the Image-generator pipeline.

Generated scene PNGs originally landed in one hardcoded folder (nsfwgame). A second game
now also needs generated scene art, so which game's assets folder new images land in has to
be selectable at runtime instead of baked into a module constant. This module owns that
selection so both newgame_gen.py (the generator) and image_app.py (the standalone GUI) can
share it -- it lives here, in Image-generator, because both of those must keep working with
no dependency on the sibling writer-generator repo.

Config lives in Image-generator/games.json (sibling to prompts/). If it doesn't exist it is
auto-created with the original nsfwgame folder as the sole, active entry, so the existing
game keeps working with zero setup.
"""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "games.json"

DEFAULT_GAME = "nsfwgame"
DEFAULT_DIR = "D:/2_MyScripts/PERSONAL/nsfwgame/assets/img/scenes"
# The checkpoint/ComfyUI workflow a game uses if it doesn't set its own -- LUSTIFY is the
# original (and still only, until oneObsession) checkpoint every existing game was built on.
DEFAULT_WORKFLOW = "D:/2_MyScripts/PERSONAL/Image-generator/WORKFLOW_MASTER_LUSTIFY.json"


def _default_data():
    return {"active": DEFAULT_GAME,
            "games": {DEFAULT_GAME: {"dir": DEFAULT_DIR, "workflow": DEFAULT_WORKFLOW}}}


def load():
    if not CONFIG_PATH.exists():
        data = _default_data()
        save(data)
        return data
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not data.get("games"):
        data = _default_data()
        save(data)
    # A stale/hand-edited "active" pointing at a removed game would break get_active_dir;
    # heal it by falling back to the first registered game.
    if data.get("active") not in data["games"]:
        data["active"] = next(iter(data["games"]))
        save(data)
    # games.json written before per-game workflows existed stores a plain dir string per
    # game. Heal each one into {"dir": ..., "workflow": DEFAULT_WORKFLOW} in place so every
    # other function below can assume the dict shape.
    healed = False
    for name, entry in data["games"].items():
        if isinstance(entry, str):
            data["games"][name] = {"dir": entry, "workflow": DEFAULT_WORKFLOW}
            healed = True
    if healed:
        save(data)
    return data


def save(data):
    CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def list_games():
    # (name, dir) only -- existing callers (pipeline_app.py, image_app.py) unpack exactly
    # this shape and never look at the workflow, so it stays out of the tuple.
    data = load()
    return [(name, data["games"][name]["dir"]) for name in data["games"]]


def get_active_name():
    return load()["active"]


def get_active_dir():
    data = load()
    return Path(data["games"][data["active"]]["dir"])


def get_active_workflow():
    data = load()
    return Path(data["games"][data["active"]]["workflow"])


def set_active(name):
    data = load()
    if name not in data["games"]:
        raise ValueError(f"unknown game: {name}")
    data["active"] = name
    save(data)


def add_game(name, path, workflow=None):
    name = (name or "").strip()
    if not name:
        raise ValueError("game name cannot be blank")
    data = load()
    data["games"][name] = {"dir": str(path), "workflow": str(workflow or DEFAULT_WORKFLOW)}
    save(data)


def remove_game(name):
    """Refuse to remove the active game or the last remaining one; return True if removed."""
    data = load()
    if name == data["active"] or len(data["games"]) <= 1:
        return False
    if name not in data["games"]:
        return False
    del data["games"][name]
    save(data)
    return True
