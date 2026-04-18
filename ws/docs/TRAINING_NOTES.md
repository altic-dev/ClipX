# Voice-to-Text Cleaner Training Notes

## Project Goal
Fine-tune Qwen3-4B-Instruct to clean noisy voice dictation into properly formatted text.
Target deployment: MLX 4-bit on Apple Silicon.

---

## Training History

### Run 1: ft_synth_7K_Qwen3-4B-Instruct-2507 (Jan 2, 2026)

**Data:**
- 6,999 train / 999 val / 1,490 test (verified splits)
- Source: `synth_full_19k.json` → LLM-verified → 9,489 approved

**Config:**
- Model: `Qwen/Qwen3-4B-Instruct-2507`
- Full fine-tuning (no LoRA)
- 4 GPUs, 10 epochs, ~1,090 steps
- Batch: 4/GPU × 4 grad_accum = 64 effective
- LR: 2e-5, cosine schedule, 100 warmup

**Results:**

| Test Set | Baseline | Fine-tuned | Change |
|----------|----------|------------|--------|
| Verified test (1,490) | 37.3% | 63.1% | **+25.8%** |
| Original test (82) | 64.6% | 69.5% | +4.9% |

**Issue Found:** Training data had inconsistent number formatting:
- "one third cup" vs "3 cups" (mixed words/numerals)
- "two pm" vs "2 PM"

---

### Run 2: Normalized Data (Pending)

**Fix Applied:** Created `normalize_data.py` to standardize:
- Number words → numerals ("two" → "2")
- Time format ("two pm" → "2 PM")
- Fractions ("one third" → "1/3")
- Ordinals ("third" → "3rd")

**Changes:** 6.1% of training examples modified

**Files:**
- `train_normalized_messages.jsonl` (6,999 examples)
- `val_normalized_messages.jsonl` (999 examples)
- `test_normalized_eval.json` (1,490 examples)

---

## Data Pipeline

### 1. Raw Data
- `synth_full_19k.json` - 19,160 synthetic examples

### 2. Verification (LLM-as-Judge)
- Model: `Qwen3-235B-A22B-Instruct-2507-FP8`
- Script: `train/scripts/verify_data.py`
- Checks: punctuation, fragments, literal commands, context
- Result: 9,489 approved (49.5%), 9,638 corrected

### 3. Splits
- Train: 6,999 (73.7%)
- Val: 999 (10.5%)
- Test: 1,490 (15.7%)
- Stratified by difficulty (easy/medium/hard)

### 4. Normalization
- Script: `train/scripts/normalize_data.py`
- Converts number words to numerals for consistency

### 5. Format Conversion
- Daniel Han's minimal format (no system prompt)
- `{"messages": [{"role": "user", "content": "Correct the raw transcription:\n\"...\""}, {"role": "assistant", "content": "..."}]}`

---

## Training Format

**User message:**
```
Correct the raw transcription:
"hey um meeting at two pm no wait three pm period"
```

**Assistant response:**
```
Meeting at 3 PM.
```

**Why no system prompt:**
- Faster inference (fewer tokens)
- Model learns behavior from examples
- More robust to prompt variations
- Recommended by Daniel Han / Unsloth

---

## Evaluation

### Test Sets

1. **Verified test** (`test_normalized_eval.json`)
   - 1,490 examples from same distribution as training
   - Best for measuring training effectiveness

2. **Original test** (`tests/dictation_mode/test_cases.json`)
   - 82 hand-crafted examples
   - Tests edge cases and specific rules

### Eval Command
```bash
cd SLM-Eval
python eval/simple_eval.py --model vllm/ft-synth-7k-qwen3-4b \
  -i data/dictation_mode/verified_splits/test_normalized_eval.json --bs 128
```

---

## Model Checkpoints

Location: `/home/nvidia/bsubramaniam/qwen_learn/train/outputs/`

### ft_synth_7K_Qwen3-4B-Instruct-2507_20260102_212458/
- `checkpoint-700/` through `checkpoint-1100/`
- `final/` - Final model

---

## vLLM Servers

| Port | Model | Purpose |
|------|-------|---------|
| 8003 | Qwen3-4B-Instruct-2507 (base) | Baseline |
| 8004 | ft_synth_7K (fine-tuned) | Evaluation |

---

## Known Issues

1. **Number inconsistency** - Original data mixed "two" and "2"
   - Fixed with normalization script

2. **Eval strictness** - Exact match can fail on equivalent outputs
   - "8:00" vs "eight" both correct but marked different

3. **System prompt mismatch** - Eval uses detailed prompt, training uses minimal
   - Decision: Keep minimal format, ensure data follows eval rules

---

## Bucket Training Experiments (Jan 3-4, 2026)

### Key Finding: Short Prompt > Big Prompt

Tested two system prompts embedded in training data:

| Prompt | File | Size | Best Score |
|--------|------|------|------------|
| **Short** | `bucket3_prompt.txt` | 2,364 chars | **84.1%** ✅ |
| Big | `system_prompt.txt` | 3,875 chars | 72.0% |

**Why short prompt wins:**
- Concise rules without verbose examples
- Model doesn't learn to mimic instructional format
- Says "Output ONLY the cleaned text" without showing reasoning chains
- Less chance for model to output `<think>` tags or reasoning

### Regularization Experiments

Tested various hyperparameters on `bucket_9_clean` dataset (6,387 train / 710 test):

| Config | LR | Weight Decay | Score | Notes |
|--------|-----|--------------|-------|-------|
| Original | 2e-5 | 0.01 | **85.4%** | checkpoint-400, manual stop |
| **Best** | 2e-5 | 0.01 | **84.1%** | early stopping @ epoch 0.75 |
| Too aggressive | 5e-6 | 0.05 | 25.6% ❌ | Underfitting, outputs garbage |
| Big prompt | 2e-5 | 0.01 | 72.0% | Model outputs reasoning |

### Optimal Training Settings

```python
# Recommended config for Qwen3-4B voice-to-text cleaner
--lr 2e-5                    # Original LR works best
--weight-decay 0.01          # Default, don't increase
--batch-size 4               # Per GPU
--gradient-accumulation 4    # Effective batch = 16
--epochs 3                   # Max epochs
--early-stopping-patience 3  # Stop when eval loss increases
--max-seq-length 1024        # Sufficient for short prompt
```

### Lessons Learned

1. **Don't over-regularize**: LR 5e-6 + WD 0.05 caused severe underfitting
2. **Shorter prompts work better**: Model learns cleaner behavior
3. **Early stopping is essential**: Best checkpoint usually around epoch 0.5-1.0
4. **Eval every 50 steps**: Catches overfitting early
5. **Big prompt pitfall**: Model may learn to output reasoning format instead of clean text

### Best Model

`bucket_9_clean_v3` - 84.1% on 82-case test set
- Trained with short prompt (`bucket3_prompt.txt`)
- LR 2e-5, WD 0.01, early stopped at epoch 0.75
- Location: `train/outputs/bucket_9_clean_v3/final`

---

## Next Steps

1. [x] ~~Retrain on normalized data~~ (bucket experiments done)
2. [x] ~~Evaluate on both test sets~~ 
3. [ ] Convert best model to MLX 4-bit
4. [ ] Test on Mac for inference speed

---

## Files Reference

```
qwen_learn/
├── docs/
│   └── TRAINING_NOTES.md          # This file
├── train/
│   ├── scripts/
│   │   ├── train_unsloth.py       # Main training script
│   │   ├── verify_data.py         # LLM-as-Judge verification
│   │   ├── normalize_data.py      # Number/format normalization
│   │   └── run_training.sh        # Training launcher
│   └── outputs/                   # Model checkpoints
├── SLM-Eval/
│   ├── data/dictation_mode/
│   │   └── verified_splits/       # Train/val/test data
│   ├── eval/
│   │   └── simple_eval.py         # Evaluation script
│   └── config/
│       └── models.yaml            # Model configs
└── verification_expert_full.json  # Verification results
```


