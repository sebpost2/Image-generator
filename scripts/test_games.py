"""Minimal stdlib-only regression tests for games.py (no pytest dependency), mirroring
writer-generator/scripts/test_manifest_store.py's style.

Covers the per-game workflow (checkpoint) selection added so a second game can use a
different ComfyUI workflow (e.g. WORKFLOW_ANIME_ONEOBSESSION.json) instead of the
LUSTIFY default, without breaking the existing single-string games.json format already
on disk for the nsfwgame install.
"""
import json
import tempfile
import unittest
from pathlib import Path

import games


class GamesConfigTestCase(unittest.TestCase):
    """Points games.CONFIG_PATH at a scratch file so tests never touch the real games.json."""

    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        import os
        os.close(fd)
        self.tmp = Path(path)
        self.tmp.unlink()  # load() should recreate it fresh
        self._orig_config_path = games.CONFIG_PATH
        games.CONFIG_PATH = self.tmp

    def tearDown(self):
        games.CONFIG_PATH = self._orig_config_path
        self.tmp.unlink(missing_ok=True)


class TestDefaultWorkflow(GamesConfigTestCase):
    def test_fresh_config_active_workflow_is_lustify_default(self):
        self.assertEqual(games.get_active_workflow(), Path(games.DEFAULT_WORKFLOW))

    def test_fresh_config_still_returns_active_dir_as_path(self):
        self.assertEqual(games.get_active_dir(), Path(games.DEFAULT_DIR))

    def test_fresh_config_list_games_returns_name_dir_tuples(self):
        # Existing callers (pipeline_app.py, image_app.py) unpack (name, dir) and never
        # look at a third element -- this must keep working unchanged.
        self.assertEqual(games.list_games(), [(games.DEFAULT_GAME, games.DEFAULT_DIR)])


class TestOldStringFormatMigration(GamesConfigTestCase):
    """games.json written before per-game workflows existed stores a plain string per game
    (name -> dir). Loading it must not crash and must default that game to LUSTIFY."""

    def setUp(self):
        super().setUp()
        self.tmp.write_text(json.dumps({
            "active": "nsfwgame",
            "games": {"nsfwgame": "D:/games/nsfw/scenes"},
        }), encoding="utf-8")

    def test_old_string_entry_migrates_to_default_workflow(self):
        self.assertEqual(games.get_active_workflow(), Path(games.DEFAULT_WORKFLOW))

    def test_old_string_entry_keeps_its_dir(self):
        self.assertEqual(games.get_active_dir(), Path("D:/games/nsfw/scenes"))

    def test_old_string_entry_healed_on_disk(self):
        games.load()
        on_disk = json.loads(self.tmp.read_text(encoding="utf-8"))
        self.assertIsInstance(on_disk["games"]["nsfwgame"], dict)
        self.assertEqual(on_disk["games"]["nsfwgame"]["dir"], "D:/games/nsfw/scenes")


class TestAddGameWithWorkflow(GamesConfigTestCase):
    def test_add_game_with_explicit_workflow(self):
        games.add_game("animegame", "D:/games/anime/scenes", workflow="D:/wf/anime.json")
        games.set_active("animegame")
        self.assertEqual(games.get_active_workflow(), Path("D:/wf/anime.json"))
        self.assertEqual(games.get_active_dir(), Path("D:/games/anime/scenes"))

    def test_add_game_without_workflow_defaults_to_lustify(self):
        # Backward compatible: existing 2-arg call sites (add_game(name, path)) must keep working.
        games.add_game("plaingame", "D:/games/plain/scenes")
        games.set_active("plaingame")
        self.assertEqual(games.get_active_workflow(), Path(games.DEFAULT_WORKFLOW))

    def test_list_games_unaffected_by_workflow_field(self):
        games.add_game("animegame", "D:/games/anime/scenes", workflow="D:/wf/anime.json")
        self.assertIn(("animegame", "D:/games/anime/scenes"), games.list_games())


if __name__ == "__main__":
    unittest.main()
