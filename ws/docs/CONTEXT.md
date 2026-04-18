# Project Context: Voice-to-Text Dictation Cleaner Fine-Tuning

## Overview

This project fine-tunes **Qwen3-4B-Instruct** to act as a voice-to-text dictation cleaner. The model cleans raw transcribed speech into polished, properly formatted text - removing fillers, adding punctuation, converting numbers, and handling self-corrections.

**End Goal**: MLX 4-bit model for deployment on Apple Silicon (FluidVoice app)

---

## Directory Structure

```
qwen_learn/
├── docs/                          # Documentation
│   ├── CONTEXT.md                 # This file - project overview
│   ├── TRAINING_RECIPE.md         # Experiment log & hyperparameters
│   ├── DATA_INVENTORY.md          # Data bucket status & quality tracking
│   └── PROMPT_WRITING_GUIDE.md    # Tips for writing generator/verifier prompts
│   └── post_ft_benchmark.md       # Post-training evaluation guide
│
├── train/                         # Training code & outputs
│   ├── scripts/
│   │   ├── train_unsloth.py       # Main training script (Unsloth + SFTTrainer)
│   │   ├── generate_and_verify.py # Synthetic data generation + LLM verification
│   │   └── create_bucket_split.py # Creates train/test splits from bucket data
│   └── outputs/                   # Saved model checkpoints
│       ├── bucket_3_ft/           # First FT attempt (3 buckets)
│       ├── bucket_5_ft/           # Best model so far (5 buckets, 86.6% on 82-test)
│       └── bucket_9_ft_v3/        # Latest attempt (9 buckets, 84.1% with temp 0.1)
│
├── SLM-Eval/                      # Evaluation framework
│   ├── eval/
│   │   └── simple_eval.py         # Main evaluation script
│   ├── config/
│   │   └── models.yaml            # Model configs (providers, ports, params)
│   ├── prompts/dictation_mode/
│   │   ├── bucket3_prompt.txt     # Current training/eval system prompt (LONG)
│   │   ├── bucket5_short_prompt.txt # Shorter prompt (818 chars)
│   │   └── system_prompt.txt      # Original long prompt
│   ├── tests/dictation_mode/
│   │   ├── test_cases.json        # 82 gold test cases (primary benchmark)
│   │   ├── bucket_3_train.json    # Bucket 3 train set (eval format)
│   │   ├── bucket_3_test.json     # Bucket 3 test set (eval format)
│   │   ├── bucket_5_train.json    # Bucket 5 train set
│   │   ├── bucket_5_test.json     # Bucket 5 test set
│   │   ├── bucket_9_train.json    # Bucket 9 train set
│   │   └── bucket_9_test.json     # Bucket 9 test set
│   ├── data/dictation_mode/
│   │   ├── buckets/               # Raw generated data by type
│   │   │   ├── prompts/           # Generator & verifier prompts for each bucket
│   │   │   ├── bait_questions_956.jsonl
│   │   │   ├── number_conversion_978.jsonl
│   │   │   ├── punctuation_commands_770.jsonl
│   │   │   ├── self_corrections_1451.jsonl
│   │   │   ├── formatting_commands_1890.jsonl
│   │   │   ├── filler_removal_439.jsonl
│   │   │   ├── abbreviation_expansion_243.jsonl
│   │   │   ├── multi_command_chains_313.jsonl
│   │   │   └── emoji_consistency_263.jsonl
│   │   ├── bucket_3/              # Combined 3-bucket data
│   │   ├── bucket_5/              # Combined 5-bucket data
│   │   └── bucket_9/              # Combined 9-bucket data (latest)
│   │       ├── train.jsonl        # Training data (raw format)
│   │       ├── test.jsonl         # Test data (raw format)
│   │       ├── train_messages.jsonl  # Training data (Unsloth format)
│   │       └── test_messages.jsonl   # Test data (Unsloth format)
│   └── results/                   # Evaluation results
│       ├── leaderboard.csv        # Aggregated scores across all runs
│       ├── bucket3_prompt/        # Results using bucket3_prompt.txt
│       │   ├── vllm_qwen3-4b-instruct-2507/  # Baseline results
│       │   ├── vllm_ft-bucket5-qwen3-4b/     # Bucket 5 FT results
│       │   └── vllm_ft-bucket9-qwen3-4b/     # Bucket 9 FT results
│       └── comparison_*.csv       # Model comparison CSVs
│
└── venv_*/                        # Virtual environments
    ├── venv_qwen3/                # For training (Unsloth, transformers)
    └── venv_vllm/                 # For vLLM serving (isolated due to NumPy conflicts)
```

---

## Key Files Explained

### Training

| File | Purpose |
|------|---------|
| `train/scripts/train_unsloth.py` | Main training script using Unsloth + HuggingFace SFTTrainer. Supports multi-GPU, checkpointing, eval during training. |
| `train/scripts/generate_and_verify.py` | Generates synthetic data using LLM, then verifies quality with LLM-as-Judge. Outputs JSONL + review CSV. |
| `train/scripts/create_bucket_split.py` | Combines bucket JSONL files into train/test splits with stratification. |

### Data Format

**Raw bucket data** (`*.jsonl`):
```json
{"input": "um can you like send the email", "expected_output": "Can you send the email?"}
```

**Training format** (`*_messages.jsonl`):
```json
{"messages": [
  {"role": "system", "content": "You are a voice-to-text..."},
  {"role": "user", "content": "um can you like send the email"},
  {"role": "assistant", "content": "Can you send the email?"}
]}
```

**Eval format** (`*.json`):
```json
{"tests": [
  {"id": "test_001", "name": "filler_removal", "input": "...", "expected_output": "...", "difficulty": "easy"}
]}
```

### Evaluation

| File | Purpose |
|------|---------|
| `SLM-Eval/eval/simple_eval.py` | Runs model on test cases, compares output to expected, saves results. |
| `SLM-Eval/config/models.yaml` | Defines models, providers, API endpoints, and inference params. |
| `SLM-Eval/results/leaderboard.csv` | Aggregated scores from all evaluation runs. |

### Prompts

| File | Purpose |
|------|---------|
| `bucket3_prompt.txt` | **Current** system prompt used for training bucket_9. Long (2364 chars). |
| `bucket5_short_prompt.txt` | Shorter prompt (818 chars). Used for bucket_5 training. |
| `buckets/prompts/*_generator.txt` | Prompts for generating synthetic data for each bucket. |
| `buckets/prompts/*_verifier.txt` | Prompts for LLM-as-Judge verification of generated data. |

---

## Data Buckets

| Bucket | Count | Purpose |
|--------|-------|---------|
| `bait_questions` | 956 | Questions/requests the model should clean, NOT answer |
| `number_conversion` | 978 | "two" → "2", "five thirty" → "5:30", "$12.50" |
| `punctuation_commands` | 770 | "period", "comma", "new line", explicit punctuation |
| `self_corrections` | 1451 | "no wait", "actually", "scratch that" → discard old content |
| `formatting_commands` | 1890 | "bold X", "header Y", "bullet point" |
| `filler_removal` | 439 | Remove "um", "uh", "like", "you know" |
| `abbreviation_expansion` | 243 | "thx" → "thanks", "pls" → "please" |
| `multi_command_chains` | 313 | Multiple commands in sequence |
| `emoji_consistency` | 263 | "smiley face" → 😊, "heart emoji" → ❤️ |

---

## Model Serving (vLLM)

### Start vLLM Server

```bash
# Activate vLLM environment (separate from training!)
source venv_vllm/bin/activate

# Serve fine-tuned model on GPU 7, port 8004
CUDA_VISIBLE_DEVICES=7 vllm serve /path/to/model --port 8004 --max-model-len 2048 --gpu-memory-utilization 0.9
```

### Model Configs in `models.yaml`

```yaml
providers:
  vllm-8004:
    base_url: "http://localhost:8004/v1"
    api_key: "vllm"
    batch_size: 512

models:
  - name: "vllm/ft-bucket9-qwen3-4b"
    provider: "vllm-8004"
    model_id: "/home/nvidia/bsubramaniam/qwen_learn/train/outputs/bucket_9_ft_v3/checkpoint-1600"
    tier: "mid"
    temperature: 0.1  # Lower temp = more deterministic
```

### Currently Running Models

| Port | Model | GPU |
|------|-------|-----|
| 8004 | bucket_9_ft_v3/checkpoint-1600 | 7 |
| 8003 | Qwen3-4B-Instruct-2507 (baseline) | varies |

---

## Common Commands

### Generate Synthetic Data
```bash
python train/scripts/generate_and_verify.py bait_questions -n 1000 -c 64
# Output: buckets/bait_questions_XXX.jsonl + bait_questions_XXX_review.csv
```

### Create Train/Test Split
```bash
python train/scripts/create_bucket_split.py
# Combines buckets → bucket_N/train.jsonl, test.jsonl, train_messages.jsonl
```

### Train Model
```bash
source venv_qwen3/bin/activate
python train/scripts/train_unsloth.py \
  --train-file .../bucket_9/train_messages.jsonl \
  --eval-file .../bucket_9/test_messages.jsonl \
  --gpus 0,1,2,3 \
  --epochs 10 \
  --batch-size 2 \
  --run-name bucket_9_ft
```

### Evaluate Model
```bash
source venv_qwen3/bin/activate
python eval/simple_eval.py \
  --model vllm/ft-bucket9-qwen3-4b \
  -i tests/dictation_mode/test_cases.json \
  -p bucket3_prompt.txt \
  --bs 512
```

---

## Best Results So Far

| Model | 82-Test Score | Notes |
|-------|---------------|-------|
| **bucket_5_ft** | **86.6%** (71/82) | Best overall, short prompt |
| bucket_9_ft_v3 (temp 0.1) | 84.1% (69/82) | More buckets, but longer prompt confused it |
| Qwen3-4B Baseline | 63.4% (52/82) | No fine-tuning |
| Gemini 2.5 Flash Lite | 48.8% (40/82) | With short prompt |

---

## Key Learnings

1. **Prompt at inference MUST match training prompt** - using different prompts hurts performance
2. **Shorter prompts often work better** - bucket_5 (short prompt) > bucket_9 (long prompt)
3. **Lower temperature (0.1) helps** - more deterministic outputs for this task
4. **Fine-tuning beats big models** - 4B FT model crushes Gemini 2.5 Flash on this task
5. **Watch for overfitting** - eval loss increasing = stop training, use earlier checkpoint
6. **Data quality > quantity** - 5 clean buckets beat 9 mixed-quality buckets

---

## Next Steps

- [ ] Export best model (bucket_5_ft) to GGUF
- [ ] Convert to MLX 4-bit for Apple Silicon
- [ ] Test on real FluidVoice transcriptions
- [ ] Consider training bucket_9 data with short prompt


