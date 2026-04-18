# Qwen3-4B Voice Dictation Fine-tuning

Fine-tune Qwen3-4B-Instruct for voice-to-text cleaning, then convert to MLX 4-bit for fast inference on Apple Silicon.

## Quick Start

```bash
# 1. Prepare your data
cd scripts
python prepare_data.py --min-score 4

# 2. Train the model (on H200)
python train_qwen3.py --epochs 3 --batch-size 8

# 3. Convert to MLX 4-bit (on Mac)
python convert_to_mlx.py --model ../outputs/qwen3-4b-dictation_*/final --output ../mlx_models/dictation-4bit
```

## Training Format

Using Daniel Han's recommended format for minimal inference tokens:

```
User: Correct the raw transcription:
"uh meeting at five pm no wait six thirty pm"


