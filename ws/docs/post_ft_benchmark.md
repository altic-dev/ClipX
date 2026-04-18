# Post Fine-Tuning Benchmark: bucket_9_ft

## ⚠️ FAILED RUN ANALYSIS (bucket_9_ft)

### What Happened
The first training run with bucket_9 data **catastrophically failed**:

| Metric | bucket_9_ft (FAILED) | bucket_5_ft (WORKED) |
|--------|---------------------|---------------------|
| **Initial Train Loss** | 46.23 🔴 | 3.03 ✅ |
| **Final Train Loss** | 12.76 🔴 | 0.04 ✅ |
| **Initial Grad Norm** | 748 🔴 | ~10 ✅ |
| **Model Output** | "assistant, assistant, assistant..." | Correct cleaning |

### Root Cause: Hyperparameter Changes
The following changes from bucket_5_ft broke training:

| Setting | bucket_5_ft (WORKED) | bucket_9_ft (FAILED) |
|---------|---------------------|---------------------|
| batch-size | **2** | 4 |
| gradient-accumulation | **4** | 8 |
| Effective batch | **8** | 32 |
| lr | **2e-5** (default) | 1e-5 |
| label-smoothing | **0** (default) | 0.1 |
| warmup-steps | **100** (default) | 200 |
| early-stopping | **None** | patience=3 |

### Lesson Learned
**Don't change multiple hyperparameters at once!** The combination of larger batch + lower LR + label smoothing caused gradient explosion and model collapse.

---

## ✅ FIXED RUN: bucket_9_ft_v2

### Training Command (Use This!)

```bash
cd /home/nvidia/bsubramaniam/qwen_learn && source venv_qwen3/bin/activate && python train/scripts/train_unsloth.py --train-file /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval/data/dictation_mode/bucket_9/train_messages.jsonl --eval-file /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval/data/dictation_mode/bucket_9/test_messages.jsonl --max-seq-length 1024 --epochs 10 --batch-size 2 --gradient-accumulation 4 --gpus 0,1,2,3 --run-name bucket_9_ft_v2
```

### Settings (Same as bucket_5_ft)

| Setting | Value |
|---------|-------|
| epochs | 10 |
| batch-size | 2 |
| gradient-accumulation | 4 |
| Effective batch | 8 |
| lr | 2e-5 (default) |
| label-smoothing | 0 (default) |
| warmup-steps | 100 (default) |
| max-seq-length | 1024 |

---

## Model Information

| Field | Value |
|-------|-------|
| **Model Name** | bucket_9_ft_v2 |
| **Base Model** | Qwen/Qwen3-4B-Instruct-2507 |
| **Training Data** | 6,569 examples (9 buckets) |
| **Eval Data** | 734 examples |
| **Model Path** | `/home/nvidia/bsubramaniam/qwen_learn/train/outputs/bucket_9_ft_v2/final` |

## Buckets Trained On

| Bucket | Count | % of Data |
|--------|-------|-----------|
| formatting_commands | 1,701 | 25.9% |
| self_corrections | 1,305 | 19.9% |
| number_conversion | 880 | 13.4% |
| bait_questions | 860 | 13.1% |
| punctuation_commands | 693 | 10.5% |
| filler_removal | 395 | 6.0% |
| multi_command_chains | 281 | 4.3% |
| emoji_consistency | 236 | 3.6% |
| abbreviation_expansion | 218 | 3.3% |

---

## Post-Training Steps

### Step 1: Check Free GPUs

```bash
nvidia-smi --query-gpu=index,memory.used,memory.free --format=csv
```

### Step 2: Kill Old FT Model (if running on port 8004)

```bash
kill $(lsof -t -i :8004) 2>/dev/null || echo "Port 8004 is free"
```

### Step 3: Start vLLM Server with New Model

```bash
CUDA_VISIBLE_DEVICES=7 vllm serve /home/nvidia/bsubramaniam/qwen_learn/train/outputs/bucket_9_ft_v2/final \
  --port 8004 \
  --max-model-len 2048 \
  --gpu-memory-utilization 0.9
```

### Step 4: Verify Server is Running

```bash
curl http://localhost:8004/v1/models
```

### Step 5: Update models.yaml

```yaml
  # Fine-tuned on bucket_9 data v2 (9 buckets, 6,569 examples) - FIXED
  - name: "vllm/ft-bucket9-qwen3-4b"
    provider: "vllm-8004"
    model_id: "/home/nvidia/bsubramaniam/qwen_learn/train/outputs/bucket_9_ft_v2/final"
    tier: "mid"
    temperature: 0.7
    top_p: 0.8
    top_k: 20
```

---

## Step 6: Run Evaluations

### 6a. Baseline Model (Qwen3-4B-Instruct-2507) on 82 Test Set

```bash
cd /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval && \
python eval/simple_eval.py \
  --model vllm/qwen3-4b-instruct-2507 \
  -i tests/dictation_mode/test.json \
  --prompt-file prompts/dictation_mode/bucket3_prompt.txt \
  --bs 512
```

### 6b. Fine-Tuned Model (bucket_9_ft) on 82 Test Set

```bash
cd /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval && \
python eval/simple_eval.py \
  --model vllm/ft-bucket9-qwen3-4b \
  -i tests/dictation_mode/test.json \
  --prompt-file prompts/dictation_mode/bucket3_prompt.txt \
  --bs 512
```

### 6c. Baseline on bucket_9_test

```bash
cd /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval && \
python eval/simple_eval.py \
  --model vllm/qwen3-4b-instruct-2507 \
  -i tests/dictation_mode/bucket_9_test.json \
  --prompt-file prompts/dictation_mode/bucket3_prompt.txt \
  --bs 512
```

### 6d. Fine-Tuned on bucket_9_test

```bash
cd /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval && \
python eval/simple_eval.py \
  --model vllm/ft-bucket9-qwen3-4b \
  -i tests/dictation_mode/bucket_9_test.json \
  --prompt-file prompts/dictation_mode/bucket3_prompt.txt \
  --bs 512
```

---

## Step 7: Compare Results

```bash
cd /home/nvidia/bsubramaniam/qwen_learn/SLM-Eval && \
python scripts/compare_evals.py \
  --baseline <baseline_csv_path> \
  --ft <ft_csv_path> \
  --output results/comparison_bucket9_ft.csv
```

---

## Results

### 82 Test Set (Real-World Examples)

| Model | Passed | Total | Accuracy |
|-------|--------|-------|----------|
| Baseline (Qwen3-4B) | TBD | 82 | TBD% |
| **FT bucket_9** | TBD | 82 | TBD% |
| **Improvement** | | | TBD% |

### bucket_9_test (Held-Out Synthetic)

| Model | Passed | Total | Accuracy |
|-------|--------|-------|----------|
| Baseline (Qwen3-4B) | TBD | 734 | TBD% |
| **FT bucket_9** | TBD | 734 | TBD% |
| **Improvement** | | | TBD% |

---

## Analysis

### Strengths (What FT Improved)
- TBD after eval

### Weaknesses (Still Failing)
- TBD after eval

### Recommendations for Next Training Run
- TBD after eval

---

## Result File Paths

| Eval | Model | Path |
|------|-------|------|
| 82 test | Baseline | TBD |
| 82 test | FT bucket_9 | TBD |
| bucket_9_test | Baseline | TBD |
| bucket_9_test | FT bucket_9 | TBD |
| Comparison | Stacked CSV | TBD |

