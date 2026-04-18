# 🧪 Training Recipe & Experiment Log

**Project:** Voice-to-Text Dictation Cleaner  
**Model:** Qwen3-4B-Instruct → Fine-tuned  
**Target:** MLX 4-bit on Apple Silicon  
**Last Updated:** January 4, 2026

---

## 📊 Current Best Configuration

```bash
python train/scripts/train_unsloth.py \
    --train-file /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval/data/dictation_mode/bucket_9_big_prompt/train_messages.jsonl \
    --eval-file /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval/data/dictation_mode/bucket_9_big_prompt/test_messages.jsonl \
    --epochs 3 \
    --batch-size 2 \
    --gradient-accumulation 4 \
    --max-seq-length 2048 \
    --run-name bucket_9_big_prompt_ft
```

**Key changes:**
- Using BIG system prompt (`system_prompt.txt`) with math + direct speech rules
- `max-seq-length: 2048` (big prompt = 1064 tokens, needs headroom)
- Added `direct_speech.jsonl` (10 examples) + `math_symbols.jsonl` (20 examples)

---

## 🏆 Best Results So Far

| Model | Test (82) | Data | Notes |
|-------|-----------|------|-------|
| Baseline (Qwen3-4B) | 41.5% | - | No fine-tuning |
| bucket_3_ft | 68-73% | 2,704 | 3 buckets |
| **bucket_5_ft** | **86.6%** | 6,045 | 5 buckets, BEST |
| bucket_9_ft_v3 | 84.1% | 7,303 (dirty) | Regressions from bad data |
| bucket_9_clean_ft | **TBD** | 7,097 (clean) | Expected: >87% |

---

## 📈 Experiment History

### Experiment 1: Disfl-QA Dataset (Jan 2, 2026)
**Goal:** Test if disfluency correction data helps

| Setting | Value |
|---------|-------|
| Data | Disfl-QA train (3,630 examples) |
| Epochs | 20 |
| Batch | 8 × 4 = 32 |
| LR | 2e-5 |

**Results:**
- Disfl-QA test: 8.8% → 52.4% ✅
- Original 82 test: 64.6% → 55% ❌ (regression!)

**Lesson:** Task-specific data (Disfl-QA) doesn't generalize to our task.

---

### Experiment 2: Synth 7K Verified (Jan 2, 2026)
**Goal:** Use LLM-verified synthetic data

| Setting | Value |
|---------|-------|
| Data | 6,999 train / 999 val (from synth_full_19k) |
| Epochs | 10 |
| Batch | 4 × 4 = 16 |
| LR | 2e-5 |

**Results:**
- Verified test (1,490): 37.3% → 63.1% ✅
- Original 82 test: 64.6% → 69.5% ✅

**Issue:** Inconsistent number formatting in data.

---

### Experiment 3: bucket_3_ft (Jan 3, 2026)
**Goal:** Test targeted bucket approach

| Setting | Value |
|---------|-------|
| Data | 2,704 examples (3 buckets) |
| Buckets | bait_questions, number_conversion, punctuation_commands |
| Prompt | Short system prompt |
| Epochs | 5 |
| Batch | 4 × 4 = 16 |

**Results:**
- Test (82): 68-73% ✅
- HARD tier: 70.6% (vs 20.6% baseline) - **+50%!**

**Lesson:** Targeted buckets work better than generic data!

---

### Experiment 4: bucket_5_ft (Jan 3, 2026) ⭐ BEST
**Goal:** Add more buckets for better coverage

| Setting | Value |
|---------|-------|
| Data | 6,045 examples (5 buckets) |
| Buckets | +self_corrections, +formatting_commands |
| Epochs | 10 |
| Batch | 2 × 4 = 8 |
| LR | 2e-5 |

**Results:**
- Test (82): **86.6%** (71/82) ✅
- Best checkpoint: step 2800 (eval_loss=1.01)

**Overfitting Analysis:**
| Step | Eval Loss | Status |
|------|-----------|--------|
| 200 | 0.6967 | ✅ Best region |
| 1000 | 0.7219 | ✅ Good |
| 1400 | 0.8260 | ⚠️ Rising |
| 2800 | 1.0141 | ❌ Overfitting |

**Lesson:** Stop training around epoch 2-3 (step 1000-1400).

---

### Experiment 5: bucket_9_ft_v3 (Jan 4, 2026) ⚠️ REGRESSIONS
**Goal:** Cover all 82 test cases with 9 buckets

| Setting | Value |
|---------|-------|
| Data | 7,303 examples (9 buckets) |
| New Buckets | +filler_removal, +abbreviation_expansion, +multi_command_chains, +emoji_consistency |
| Epochs | 10 |
| Best checkpoint | step 1600 (eval_loss=0.636) |

**Results:**
- Test (82): 84.1% (with temp 0.1)
- **Worse than bucket_5_ft!** (86.6%)

**Root Cause Analysis:**
The 4 new buckets had **206 bad examples** that taught wrong behaviors:

| Bucket | Bad Examples | Issue |
|--------|--------------|-------|
| filler_removal | 187 | Removed meaningful words (actually, basically, kind of) |
| emoji_consistency | 14 | Wrong emoji placement |
| multi_command_chains | 5 | "add X" → "- X" bug |

**Lesson:** Data quality > Data quantity. Bad examples cause regressions!

---

### Experiment 6: bucket_9_clean_ft (Jan 4, 2026) ⚠️ STILL MISSING DATA
**Goal:** Train with cleaned data

| Setting | Value |
|---------|-------|
| Data | **7,097 examples** (cleaned) |
| Train | 6,387 |
| Test | 710 |
| Epochs | **3** (safe, before overfitting) |
| Batch | 2 × 4 × 4 = 32 |
| LR | 2e-5 |

**Data Fixes Applied:**
1. ✅ Removed 187 bad filler_removal examples
2. ✅ Removed 14 bad emoji_consistency examples
3. ✅ Removed 5 bad multi_command_chains examples
4. ✅ Fixed 48 inconsistent number formats

**Results:**
- Test (82): ~85% (similar to bucket_9_ft_v3)
- Still failing on: direct speech quotes, math symbols

**Issue Found:** Missing training data for:
- `direct_speech.jsonl` (10 examples) - never included!
- `math_symbols.jsonl` - didn't exist!

---

### Experiment 7: bucket_9_big_prompt_ft (Jan 4, 2026) 🔄 NEXT
**Goal:** Fix all remaining issues with BIG prompt + missing data

| Setting | Value |
|---------|-------|
| Data | **7,127 examples** (11 buckets) |
| Train | 6,414 |
| Test | 713 |
| Epochs | **3** |
| Batch | 2 × 4 = 8 |
| LR | 2e-5 |
| **max_seq_length** | **2048** (was 1024) |
| **System Prompt** | `system_prompt.txt` (BIG - 1064 tokens) |

**Key Changes:**
1. ✅ Using BIG system prompt (has math + direct speech rules)
2. ✅ Added `direct_speech.jsonl` (10 examples)
3. ✅ Created `math_symbols.jsonl` (20 examples) - NEW!
4. ✅ Increased max_seq_length to 2048 (big prompt = 1064 tokens)

**New Buckets Added:**
| Bucket | Examples | Purpose |
|--------|----------|---------|
| direct_speech | 10 | "He said, \"Hello.\"" |
| math_symbols | 20 | "2 + 2", "5 × 3", "10 ÷ 2" |

**Expected:** >90% on 82 test (fix direct speech + math failures)

---

## 🔧 Hyperparameter Findings

### Epochs & Overfitting
| Epochs | Eval Loss Trend | Recommendation |
|--------|-----------------|----------------|
| 1-2 | ↓ Decreasing | ✅ Learning |
| 2-3 | → Flat | ✅ Optimal |
| 3-5 | ↑ Increasing | ⚠️ Overfitting |
| 5+ | ↑↑ Rising | ❌ Severe overfitting |

**Recommendation:** Train for **3 epochs max** or use early stopping.

### Learning Rate
| LR | Effect |
|----|--------|
| 5e-5 | Too high, unstable |
| 2e-5 | **Good for most cases** |
| 1e-5 | More stable, slower |
| 5e-6 | Too slow |

### Batch Size
| Effective Batch | Effect |
|-----------------|--------|
| 8 | More noise, may help generalization |
| 16 | Good balance |
| 32 | **Recommended** - stable gradients |

---

## 📦 Data Quality Checklist

Before training, verify:

### ✅ filler_removal bucket
- [ ] Does NOT remove: actually, basically, kind of, honestly, literally
- [ ] Does NOT remove: I think, I mean, like I said
- [ ] ONLY removes: um, uh, like (as filler), you know, so/well at start

### ✅ emoji_consistency bucket
- [ ] Only adds emoji when explicitly requested
- [ ] Uses correct emoji (😊 not 😀)
- [ ] Preserves content (not just emoji output)

### ✅ multi_command_chains bucket
- [ ] "add X" does NOT become "- X" bullet
- [ ] Phone numbers properly formatted
- [ ] Corrections apply to preceding item only

### ✅ Number formatting (all buckets)
- [ ] "three times" → "3 times"
- [ ] "ten minutes" → "10 minutes"
- [ ] "five days" → "5 days"
- [ ] "the blue one" → kept as "one" (pronoun)

---

## ✅ What Works

1. **Targeted bucket data** - Much better than generic synthetic data
2. **LLM-as-Judge verification** - Catches bad examples
3. **Short training (3 epochs)** - Prevents overfitting
4. **Data quality checks** - Bad data causes regressions
5. **Number normalization** - Consistency matters

---

## ❌ What Doesn't Work

1. **Generic disfluency data (Disfl-QA)** - Doesn't transfer
2. **Long training (10+ epochs)** - Overfits
3. **Bad training data** - Model learns wrong patterns
4. **Aggressive filler removal** - Removes meaningful words
5. **More buckets without quality** - Quantity ≠ Quality

---

## 🚀 Training Command (bucket_9_clean)

```bash
cd /home/nvidia/bsubramaniam/qwen_learn
source venv_qwen3/bin/activate

python train/scripts/train_unsloth.py \
  --train-file /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval/data/dictation_mode/bucket_9_clean/train_messages.jsonl \
  --eval-file /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval/data/dictation_mode/bucket_9_clean/test_messages.jsonl \
  --gpus 0,1,2,3 \
  --epochs 3 \
  --batch-size 2 \
  --gradient-accumulation 4 \
  --max-seq-length 1024 \
  --run-name bucket_9_clean_ft
```

---

## 📁 File Locations

```
qwen_learn/
├── docs/
│   ├── TRAINING_RECIPE.md      # This file
│   ├── DATA_INVENTORY.md       # Bucket data tracking
│   ├── CONTEXT.md              # Project overview
│   └── PROMPT_WRITING_GUIDE.md # How to write gen/ver prompts
├── train/
│   ├── scripts/
│   │   ├── train_unsloth.py    # Main training script
│   │   ├── generate_and_verify.py  # Data generation
│   │   └── create_bucket_split.py  # Train/test split
│   └── outputs/                # Model checkpoints
│       ├── bucket_5_ft/        # ⭐ Current best (86.6%)
│       └── bucket_9_clean_ft/  # 🔄 Training...
├── SLM-Eval/
│   ├── data/dictation_mode/
│   │   ├── buckets/            # Raw bucket data
│   │   └── bucket_9_clean/     # ⭐ Latest training data
│   ├── prompts/dictation_mode/ # System prompts
│   └── tests/dictation_mode/   # Test files
```

---

*Updated after each training run*
