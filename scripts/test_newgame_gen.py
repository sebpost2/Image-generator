"""Regression test for the face-variant workflow-patching logic in newgame_gen.py -- the one
piece of that module's logic that's pure (no ComfyUI network call) and therefore testable
without a running ComfyUI instance, same reasoning as this repo's other unittest-only tests."""
import unittest

import newgame_gen


class TestPatchFaceVariantWorkflow(unittest.TestCase):
    def _base_workflow(self):
        return {
            "6": {"inputs": {"text": "old positive"}},
            "7": {"inputs": {"text": "old negative"}},
            "15": {"inputs": {"wildcard": "old wildcard", "seed": 1, "denoise": 0.4}},
            "20": {"inputs": {"image": "old.png"}},
        }

    def test_patches_source_image_filename(self):
        wf = newgame_gen._patch_face_variant_workflow(
            self._base_workflow(), "variant_src_d2.png", "base pos", "base neg",
            "she gasps, eyes wide", seed=42, denoise=0.6)
        self.assertEqual(wf["20"]["inputs"]["image"], "variant_src_d2.png")

    def test_patches_base_positive_and_negative_for_facedetailer_context(self):
        wf = newgame_gen._patch_face_variant_workflow(
            self._base_workflow(), "variant_src_d2.png", "base pos", "base neg",
            "she gasps, eyes wide", seed=42, denoise=0.6)
        self.assertEqual(wf["6"]["inputs"]["text"], "base pos")
        self.assertEqual(wf["7"]["inputs"]["text"], "base neg")

    def test_wraps_wildcard_text_in_concat(self):
        wf = newgame_gen._patch_face_variant_workflow(
            self._base_workflow(), "variant_src_d2.png", "base pos", "base neg",
            "she gasps, eyes wide", seed=42, denoise=0.6)
        self.assertEqual(wf["15"]["inputs"]["wildcard"], "[CONCAT]she gasps, eyes wide")

    def test_patches_seed_and_denoise(self):
        wf = newgame_gen._patch_face_variant_workflow(
            self._base_workflow(), "variant_src_d2.png", "base pos", "base neg",
            "she gasps, eyes wide", seed=42, denoise=0.6)
        self.assertEqual(wf["15"]["inputs"]["seed"], 42)
        self.assertEqual(wf["15"]["inputs"]["denoise"], 0.6)


if __name__ == "__main__":
    unittest.main()
