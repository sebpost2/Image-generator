"""Regression test for the face-variant workflow-patching logic in newgame_gen.py -- the one
piece of that module's logic that's pure (no ComfyUI network call) and therefore testable
without a running ComfyUI instance, same reasoning as this repo's other unittest-only tests."""
import unittest

import newgame_gen


class TestApplyLorasToWorkflow(unittest.TestCase):
    def _base_workflow(self):
        return {
            "4": {"inputs": {"ckpt_name": "oneObsession_v23.safetensors"}},
            "6": {"inputs": {"text": "positive", "clip": ["4", 1]}},
            "3": {"inputs": {"model": ["4", 0], "positive": ["6", 0]}},
        }

    def test_empty_loras_leaves_workflow_untouched(self):
        wf = self._base_workflow()
        result = newgame_gen._apply_loras_to_workflow(wf, [])
        self.assertEqual(result["3"]["inputs"]["model"], ["4", 0])
        self.assertEqual(result["6"]["inputs"]["clip"], ["4", 1])

    def test_single_lora_inserted_and_rewired(self):
        wf = newgame_gen._apply_loras_to_workflow(self._base_workflow(),
                                                   [("dogeza.safetensors", 0.8)])
        self.assertEqual(wf["lora_1"]["inputs"]["lora_name"], "dogeza.safetensors")
        self.assertEqual(wf["lora_1"]["inputs"]["strength_model"], 0.8)
        self.assertEqual(wf["lora_1"]["inputs"]["strength_clip"], 0.8)
        self.assertEqual(wf["lora_1"]["inputs"]["model"], ["4", 0])
        self.assertEqual(wf["lora_1"]["inputs"]["clip"], ["4", 1])
        self.assertEqual(wf["3"]["inputs"]["model"], ["lora_1", 0])
        self.assertEqual(wf["6"]["inputs"]["clip"], ["lora_1", 1])

    def test_multiple_loras_chained_in_order(self):
        wf = newgame_gen._apply_loras_to_workflow(
            self._base_workflow(),
            [("dogeza.safetensors", 0.8), ("cum.safetensors", 1.0)])
        self.assertEqual(wf["lora_1"]["inputs"]["model"], ["4", 0])
        self.assertEqual(wf["lora_2"]["inputs"]["model"], ["lora_1", 0])
        self.assertEqual(wf["lora_2"]["inputs"]["clip"], ["lora_1", 1])
        self.assertEqual(wf["3"]["inputs"]["model"], ["lora_2", 0])
        self.assertEqual(wf["6"]["inputs"]["clip"], ["lora_2", 1])

    def test_lora_nodes_own_inputs_not_rewired_to_themselves(self):
        wf = newgame_gen._apply_loras_to_workflow(
            self._base_workflow(),
            [("dogeza.safetensors", 0.8), ("cum.safetensors", 1.0)])
        # lora_2 must still point at lora_1's outputs, not get swept up in the final rewire pass.
        self.assertEqual(wf["lora_2"]["inputs"]["model"], ["lora_1", 0])


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
