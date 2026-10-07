Offline Chinese OCR models for V1.2 image-role evidence.

The three ONNX model files in this directory are the RapidOCR/PaddleOCR
Chinese PP-OCRv4 detector, recognizer, and mobile text-angle classifier.
They are distributed for offline CPU inference and are not used to replace
images in generated DOCX files. RapidOCR is Apache-2.0; see the upstream
RapidOCR project and PaddleOCR model-card/license notices for model terms.

The app verifies each model's SHA-256 at runtime and persists those digests
with image-role evidence. The selected model bytes are recorded in the
finalization gate report.
