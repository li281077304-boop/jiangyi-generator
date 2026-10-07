# Offline OCR third-party notices

## Model files

These ONNX files are bundled unchanged from the RapidAI/RapidOCR PP-OCRv4
model set. The byte hashes below match the published RapidOCR model manifest
for release v3.9.2:

| Bundled file | Published model | Published source | SHA-256 |
| --- | --- | --- | --- |
| ch_PP-OCRv4_det_infer.onnx | ch_PP-OCRv4_det_mobile.onnx | <https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/onnx/PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx> | d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9 |
| ch_PP-OCRv4_rec_infer.onnx | ch_PP-OCRv4_rec_mobile.onnx | <https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/onnx/PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx> | 48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b |
| ch_ppocr_mobile_v2.0_cls_infer.onnx | ch_ppocr_mobile_v2.0_cls_mobile.onnx | <https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/onnx/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx> | e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c |

Source manifest: <https://github.com/RapidAI/RapidOCR/blob/main/python/rapidocr/default_models.yaml>.
The model bytes were independently hashed in the checked-in directory and
matched to that manifest before this notice was written. RapidOCR publishes
its project under Apache-2.0; PaddleOCR, the source OCR model project, also
publishes under Apache-2.0:

- <https://github.com/RapidAI/RapidOCR/blob/main/LICENSE>
- <https://github.com/PaddlePaddle/PaddleOCR/blob/main/LICENSE>
- <https://www.apache.org/licenses/LICENSE-2.0>

The source-image bytes are kept in generated DOCX. OCR is used for local
classification and routing evidence and never substitutes OCR text for the
embedded image.

## OCR runtime packages

The Windows x64 onedir build pins the OCR runtime in
packaging/windows/ocr-requirements.lock. Package versions and declared
licenses observed from the locked wheel metadata:

| Package | Version | Declared license |
| --- | --- | --- |
| rapidocr-onnxruntime | 1.4.4 | Apache-2.0 |
| onnxruntime | 1.30.0 | MIT |
| opencv-python | 5.0.0.93 | Apache-2.0 |
| numpy | 2.4.6 | BSD-3-Clause, 0BSD, MIT, Zlib, CC0-1.0 |
| flatbuffers | 25.12.19 | Apache-2.0 |
| protobuf | 7.36.2 | BSD-3-Clause |
| Pillow | 12.3.0 | MIT-CMU |
| Shapely | 2.1.2 | BSD-3-Clause |
| pyclipper | 1.4.0 | MIT |
| PyYAML | 6.0.3 | MIT |
| tqdm | 4.70.1 | MPL-2.0 / MIT |
| six | 1.17.0 | MIT |
| packaging | 26.2 | Apache-2.0 / BSD-2-Clause |

These identifiers were read from the exact pinned wheel metadata in the
offline Windows runtime probe. This table identifies the OCR-specific runtime
closure; it is not a complete notice for unrelated application dependencies
or every native component's transitive notices.
