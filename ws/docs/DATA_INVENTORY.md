# 📊 Data Inventory - Generated Bucket Data

Last updated: January 4, 2026 (bucket_9_clean - DATA QUALITY FIX!)

---

## ⚠️ CRITICAL: Data Quality Issues Fixed!

On Jan 4, 2026, we discovered **206 bad examples** in the new buckets that were causing regressions:

| Bucket | Before | After | Removed | Issue |
|--------|--------|-------|---------|-------|
| filler_removal | 439 | **252** | 187 (43%) | Removed meaningful words (actually, basically, kind of) |
| emoji_consistency | 263 | **249** | 14 (5%) | Wrong emoji placement, lost content |
| multi_command_chains | 313 | **308** | 5 (2%) | "add X" → "- X" bullet, bad phone formatting |

### Additional Fixes:
- **48 examples** had inconsistent number formatting fixed across all buckets
- "three times" → "3 times", "ten minutes" → "10 minutes", etc.

---

## ✅ CLEANED DATA SUMMARY (bucket_9_big_prompt)

| Bucket | File | Count | Quality |
|--------|------|-------|---------|
| bait_questions | `bait_questions_956.jsonl` | 956 | ⭐⭐⭐⭐⭐ |
| number_conversion | `number_conversion_978.jsonl` | 978 | ⭐⭐⭐⭐⭐ |
| punctuation_commands | `punctuation_commands_770.jsonl` | 770 | ⭐⭐⭐⭐⭐ |
| self_corrections | `self_corrections_1451.jsonl` | 1,451 | ⭐⭐⭐⭐⭐ |
| formatting_commands | `formatting_commands_1890.jsonl` | 1,890 | ⭐⭐⭐⭐⭐ |
| filler_removal | `filler_removal_252.jsonl` | **252** | ⭐⭐⭐⭐⭐ CLEANED |
| abbreviation_expansion | `abbreviation_expansion_243.jsonl` | 243 | ⭐⭐⭐⭐⭐ |
| multi_command_chains | `multi_command_chains_308.jsonl` | **308** | ⭐⭐⭐⭐⭐ CLEANED |
| emoji_consistency | `emoji_consistency_249.jsonl` | **249** | ⭐⭐⭐⭐⭐ CLEANED |
| **direct_speech** | `direct_speech.jsonl` | **10** | ⭐⭐⭐⭐⭐ NEW |
| **math_symbols** | `math_symbols.jsonl` | **20** | ⭐⭐⭐⭐⭐ NEW |
| **TOTAL** | | **7,127** | |

### 🆕 New Buckets Added (Jan 4, 2026):

**direct_speech** (10 examples) - Implicit speech quotes:
```
IN:  "he said I am fine"
OUT: He said, "I am fine."

IN:  "she told me dont worry"  
OUT: She told me, "Don't worry."

IN:  "the boss shouted stop right now"
OUT: The boss shouted, "Stop right now!"
```

**math_symbols** (20 examples) - Math operator conversion:
```
IN:  "what is two plus two"
OUT: What is 2 + 2?

IN:  "six times seven"
OUT: 6 × 7.

IN:  "twenty divided by four"
OUT: 20 ÷ 4.

IN:  "three minus one equals two"
OUT: 3 - 1 = 2.
```

These were **missing** from previous training, causing failures on:
- `ultimate-002`: "he said I am ready" (no quotes added)
- `ultimate-003`: "she told me dont worry" (no quotes added)
- Math expressions not converting "plus" → "+"

### Train/Test Split (bucket_9_big_prompt):
- **Train**: 6,414 examples (90%)
- **Test**: 713 examples (10%)
- **Location**: `SLM-Eval/data/dictation_mode/bucket_9_big_prompt/`
- **System Prompt**: `system_prompt.txt` (BIG - 1064 tokens, has math + direct speech rules)

---

## 🔴 BAD DATA FILES (DO NOT USE)

| File | Issue |
|------|-------|
| `filler_removal_439.jsonl` | ❌ Removes meaningful words (actually, basically, kind of) |
| `filler_removal_439_BAD.jsonl` | Backup of bad data |
| `emoji_consistency_263.jsonl` | ❌ Wrong emoji placement |
| `emoji_consistency_263_BAD.jsonl` | Backup of bad data |
| `multi_command_chains_313.jsonl` | ❌ "add X" → "- X" bug |
| `multi_command_chains_313_BAD.jsonl` | Backup of bad data |

---

## 📋 What Was Wrong with filler_removal

The generator prompt was teaching the model to remove **meaningful words**:

### ❌ BAD Examples (removed):
```
IN:  "like I said, I really like jazz music"
OUT: "I said, I really like jazz music."  ← Removed "like I said"!

IN:  "you know, it's actually kind of cold in here"
OUT: "It's cold in here."  ← Removed "actually kind of"!

IN:  "basically we need to finish this by Friday"
OUT: "We need to finish this by Friday."  ← Removed "basically"!
```

### ✅ GOOD Examples (kept):
```
IN:  "um I think we should go"
OUT: "I think we should go."  ← Only removed "um"

IN:  "uh actually I changed my mind"
OUT: "Actually, I changed my mind."  ← Kept "actually"!

IN:  "um it's kind of cold"
OUT: "It's kind of cold."  ← Kept "kind of"!
```

### Words That Should NEVER Be Removed:
- actually, basically, literally, honestly, seriously
- kind of, sort of, kinda, sorta
- like I said, I mean, I think, I guess
- probably, maybe, obviously, clearly

### Words That SHOULD Be Removed (true fillers):
- um, uh, uhh, umm, er, ah, hmm
- like (only when pure filler: "so like I was...")
- you know (at start/end)
- so, well, okay (at very start)

---

## 📈 Training Results Comparison

| Model | Data | Test (82) | Notes |
|-------|------|-----------|-------|
| Baseline | - | 41.5% | No FT |
| bucket_5_ft | 6,045 | **86.6%** | Best so far |
| bucket_9_ft_v3 | 7,303 (dirty) | 84.1% | Regressions from bad data |
| bucket_9_clean_ft | 7,097 (clean) | **TBD** | Expected: >87% |

---

## 🎯 Next Steps

1. ✅ Created `bucket_9_clean` split with cleaned data
2. 🔄 Train `bucket_9_clean_ft` with 3 epochs (safe, before overfitting)
3. 📊 Evaluate on 82 test set
4. 🎯 Target: Beat bucket_5_ft (86.6%)

---

## 📂 File Locations

```
SLM-Eval/data/dictation_mode/
├── buckets/                    # Raw bucket data
│   ├── bait_questions_956.jsonl
│   ├── number_conversion_978.jsonl
│   ├── punctuation_commands_770.jsonl
│   ├── self_corrections_1451.jsonl
│   ├── formatting_commands_1890.jsonl
│   ├── filler_removal_252.jsonl      # ✅ CLEANED
│   ├── abbreviation_expansion_243.jsonl
│   ├── multi_command_chains_308.jsonl # ✅ CLEANED
│   ├── emoji_consistency_249.jsonl    # ✅ CLEANED
│   └── *_BAD.jsonl                    # ❌ Backups of bad data
│
├── bucket_9_clean/             # ⭐ LATEST TRAINING DATA
│   ├── train.jsonl             # 6,387 examples
│   ├── test.jsonl              # 710 examples
│   ├── train_messages.jsonl    # For Unsloth training
│   └── test_messages.jsonl     # For Unsloth eval
```

---

*This document should be updated after each data quality check.*
