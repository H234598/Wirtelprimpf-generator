# Local Image Backend Notes

This host also has a small local CPU-only image generation test backend.

## Installed Local Test Backend

```text
Virtual environment: ~/.local/share/local-imagegen-venv
CLI wrapper:         ~/.local/bin/local-imagegen
Default model:       segmind/tiny-sd
Output folder:       ~/Hintergrundbilder/local-imagegen
Device:              CPU
```

The first test image was generated successfully:

```text
~/Hintergrundbilder/local-imagegen/local_imagegen_2026-05-19_13-40-59.png
512x512 PNG
```

## Usage

```bash
LOCAL_IMAGEGEN_STEPS=6 \
LOCAL_IMAGEGEN_WIDTH=512 \
LOCAL_IMAGEGEN_HEIGHT=512 \
~/.local/bin/local-imagegen 'two cats in a warm old library, painterly'
```

Environment variables:

```text
LOCAL_IMAGEGEN_MODEL    Hugging Face model id, default segmind/tiny-sd
LOCAL_IMAGEGEN_OUTDIR   output directory
LOCAL_IMAGEGEN_STEPS    inference steps, default 8
LOCAL_IMAGEGEN_WIDTH    output width, default 512
LOCAL_IMAGEGEN_HEIGHT   output height, default 512
```

## Practical Notes

The machine has Intel Iris Xe graphics but no NVIDIA/AMD compute GPU. This
backend therefore runs on CPU. It is much slower and lower quality than the
OpenAI Images API path, but it proves that fully local generation works.

Current footprint after installation:

```text
~/.local/share/local-imagegen-venv  about 5.0G
~/.cache/huggingface                about 1.0G
```

The Python environment installed PyTorch 2.12 for Python 3.14. The resolver
pulled CUDA-related wheels even though this host uses CPU mode, so disk usage is
higher than ideal.

## Integration Path

The recommended next step is adding a backend switch to the Wirtelprimpf
generator:

```text
WIRTELPRIMPF_BACKEND=openai
WIRTELPRIMPF_BACKEND=local
```

That would keep the existing output, Git commit, and timer logic while swapping
only the image-generation backend.
