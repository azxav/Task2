# Tested local OCR runtimes

Python 3.12.10. Application and OCR environments are separate from each other.

| Profile | Environment | Models | Device |
|---|---|---|---|
| PP-OCRv5 | `.venv-ocr` | `PP-OCRv5_mobile_det`, `latin_PP-OCRv5_mobile_rec` | CPU |
| Tesseract 5.5.2 | `.venv-ocr`, `.runtime/tesseract` | tessdata_best `uzb+eng` | CPU |
| PaddleOCR-VL-1.6 | `.venv-vl` | `PP-DocLayoutV3`, `PaddleOCR-VL-1.6` | NVIDIA GPU |

PaddleOCR 3.6.0 in both environments; Paddle CPU 3.2.2; GPU 3.2.1 (official CUDA 12.6 wheel). Exact installed packages: `requirements-cpu.txt`, `requirements-gpu.txt`. Model files/hashes: `models-lock.json`. Models reside at the workspace's `.cache/paddlex/official_models/`; the worker passes explicit local directories and rejects external TCP connections. Downloading weights belongs to setup, never document analysis.

Installation on a new Windows machine:

```powershell
uv venv .venv-ocr --python 3.12
uv pip install --python .venv-ocr/Scripts/python.exe -r ocr-runtime/requirements-cpu.txt
uv venv .venv-vl --python 3.12
uv pip install --python .venv-vl/Scripts/python.exe paddlepaddle-gpu==3.2.1 --index-url https://www.paddlepaddle.org.cn/packages/stable/cu126/
uv pip install --python .venv-vl/Scripts/python.exe -r ocr-runtime/requirements-gpu.txt
```

Download the listed model directories from the official Paddle repositories during setup. Preserve their directory names and compare SHA-256 with `models-lock.json`. Tesseract's tested portable conda-forge environment is `.runtime/tesseract`; its executable is `Library/bin/tesseract.exe`. Uzbek/English tessdata_best files reside in workspace `.cache/tessdata/`.

VL scales the longer page side to 1700 pixels, disables orientation/unwarping, uses unmerged layout blocks and a 1536-token recognition limit per block. Table HTML preserves row/column roles; OpenCV borders provide cell boxes when topology agrees. Unknown/merged geometry is explicitly diagnostic. Recognition is followed by text-only Tev1 decisions.

The GPU environment logged compiled cuDNN 9.9 versus installed 9.5. Real GPU recognition completed; retain this measured compatibility caveat when reproducing the environment. The initial CPU VL probe was stopped because it was impractically slow; no CPU VL accuracy or timing is claimed.

Licenses/provenance: [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [VL weights](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6), [Tesseract](https://github.com/tesseract-ocr/tesseract), [language data](https://github.com/tesseract-ocr/tessdata_best). PaddleOCR/VL and Tesseract use Apache-2.0; model hashes identify the tested downloaded artifacts.
