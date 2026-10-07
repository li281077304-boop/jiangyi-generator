import hashlib
from pathlib import Path
import tempfile
import unittest

from image_role_evidence import (
    LocalOCRError,
    LocalOCRRecognizer,
    MODEL_FILES,
    OCRLine,
    classify_image_role,
    recognize_image_local,
)


class ImageRoleEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.models = self.root / "models"
        self.models.mkdir()
        for name in MODEL_FILES:
            (self.models / name).write_bytes(("fixture:" + name).encode("ascii"))
        self.image = self.root / "source.png"
        self.original_image = b"immutable-image-fixture"
        self.image.write_bytes(self.original_image)

    def tearDown(self):
        self.tmp.cleanup()

    def test_local_ocr_uses_explicit_models_and_keeps_source_bytes(self):
        seen = {}

        def engine_factory(model_paths):
            seen["models"] = tuple(model_paths)

            def engine(image_bytes):
                seen["image"] = image_bytes
                return ([[[0, 0, 1, 1], "知识清单", 0.97]], [0.01, 0.01, 0.01])
            return engine

        result = recognize_image_local(self.image, self.models,
                                       engine_factory=engine_factory)

        self.assertEqual(seen["image"], self.original_image)
        self.assertEqual(self.image.read_bytes(), self.original_image)
        self.assertEqual(result.image_sha256,
                         hashlib.sha256(self.original_image).hexdigest())
        self.assertEqual(set(result.model_sha256), set(MODEL_FILES))
        self.assertEqual(result.lines, (OCRLine("知识清单", 0.97,
                                                [0, 0, 1, 1]),))
        self.assertEqual(result.engine, "rapidocr_onnxruntime-cpu")

    def test_recognizer_loads_models_once_for_many_images(self):
        seen = {"loads": 0, "images": []}

        def factory(model_paths):
            seen["loads"] += 1
            self.assertEqual(set(Path(path).name for path in model_paths), set(MODEL_FILES))
            return lambda image: seen["images"].append(image) or ([], 0.0)

        recognizer = LocalOCRRecognizer(self.models, engine_factory=factory)
        recognizer.recognize(b"one", source_node_id="b1")
        recognizer.recognize(b"two", source_node_id="b2")

        self.assertEqual(seen["loads"], 1)
        self.assertEqual(seen["images"], [b"one", b"two"])

    def test_local_ocr_fails_closed_when_a_model_is_missing(self):
        (self.models / MODEL_FILES[0]).unlink()
        with self.assertRaisesRegex(LocalOCRError, "models missing"):
            recognize_image_local(
                self.image, self.models,
                engine_factory=lambda _paths: self.fail("engine must not start"),
            )
        self.assertEqual(self.image.read_bytes(), self.original_image)

    def test_explicit_metadata_cue_is_auditable_but_not_rewritten(self):
        image_hash = hashlib.sha256(self.original_image).hexdigest()
        raw_text = " 教学目标 / 教学重难点 "
        evidence = classify_image_role(
            image_sha256=image_hash,
            source_node_id="b17.image0",
            lines=(OCRLine(raw_text, 0.99),),
        )
        self.assertEqual(evidence.role, "TEACHING_METADATA")
        self.assertFalse(evidence.actionable)
        self.assertEqual(evidence.source_node_id, "b17.image0")
        self.assertEqual(evidence.evidence_lines[0].text, raw_text)
        self.assertEqual(evidence.matched_cues, ("教学目标", "教学重难点"))

    def test_low_confidence_and_unknown_topic_are_not_promoted(self):
        image_hash = hashlib.sha256(self.original_image).hexdigest()
        low = classify_image_role(
            image_sha256=image_hash,
            source_node_id="b18.image0",
            lines=(OCRLine("知识清单", 0.79),),
        )
        self.assertEqual(low.role, "UNKNOWN")
        self.assertFalse(low.actionable)

        descriptive = classify_image_role(
            image_sha256=image_hash,
            source_node_id="b19.image0",
            lines=(OCRLine("一次函数的实际应用", 0.99),),
        )
        self.assertEqual(descriptive.role, "UNKNOWN")
        self.assertEqual(descriptive.confidence, "NO_EXPLICIT_CUE")

    def test_conflicting_cue_families_fail_closed(self):
        evidence = classify_image_role(
            image_sha256=hashlib.sha256(self.original_image).hexdigest(),
            source_node_id="b20.image0",
            lines=(OCRLine("知识清单", 0.99), OCRLine("题型训练", 0.98)),
        )
        self.assertEqual(evidence.role, "AMBIGUOUS")
        self.assertEqual(evidence.confidence, "CONFLICTING_CUES")
        self.assertFalse(evidence.actionable)

    def test_missing_provenance_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            classify_image_role(image_sha256="bad", source_node_id="b1",
                                lines=())
        with self.assertRaisesRegex(ValueError, "source_node_id"):
            classify_image_role(image_sha256="0" * 64, source_node_id=" ",
                                lines=())


if __name__ == "__main__":
    unittest.main()
