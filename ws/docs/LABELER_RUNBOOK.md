# Labeler Runbook — Teacher Relabeling Pipeline

How to run the teacher relabeler against any OpenAI-compatible endpoint, probe a subset of data,
compare outputs, and swap in a new model. All scripts live in `~/ws/sft/` on the DGX station.

---

## Server Access

```
Host:  global.stg.ga.launchpad.nvidia.com
Port:  11122
User:  bsubramaniam
SSH:   ssh -p 11122 bsubramaniam@global.stg.ga.launchpad.nvidia.com
Alias: ssh dgx-station   (configured in ~/.ssh/config)
```

---

## Currently Running Teacher Model

| | |
|---|---|
| **Endpoint** | `http://10.33.197.85:8000/v1` |
| **Model ID** | `/mnt/storage/MiniMax-M2.7` (served name — actual weights are Qwen/Qwen3.6-35B-A3B) |
| **Real model** | `Qwen/Qwen3.6-35B-A3B` — 35B MoE, 3.6B active params |
| **Context** | 262,144 tokens |
| **Started with** | `vllm serve Qwen/Qwen3.6-35B-A3B --port 8000 --max-model-len 262144 --reasoning-parser qwen3 --language-model-only` |

Check what is running at any time:
```bash
curl -sS http://10.33.197.85:8000/v1/models | python3 -m json.tool
```

---

## Swapping in a Different Teacher Model

To use a different model (local or remote), just change two env vars before running any script:

```bash
# Local vLLM (different model on same server)
export NV_BASE_URL=http://10.33.197.85:8000/v1
export NV_MODEL=<model-id-as-reported-by-/v1/models>
export NVIDIA_API_KEY=dummy

# NVIDIA Inference Microservices (NIM) remote API
export NV_BASE_URL=https://integrate.api.nvidia.com/v1
export NVIDIA_API_KEY=sk-...
export NV_MODEL=meta/llama-3.3-70b-instruct   # or any NIM model slug

# Any other OpenAI-compatible endpoint
export NV_BASE_URL=http://<host>:<port>/v1
export NV_MODEL=<model-id>
export NVIDIA_API_KEY=<key-or-dummy>
```

The model ID must exactly match what the `/v1/models` endpoint returns. Check with:
```bash
curl -sS $NV_BASE_URL/models | python3 -c "import json,sys; [print(x['id']) for x in json.load(sys.stdin)['data']]"
```

---

## Thinking Mode

The teacher model (Qwen3.6-35B-A3B) supports reasoning. Three modes:

| Flag | Behaviour | Speed | Quality |
|---|---|---|---|
| `--thinking` | Forces `enable_thinking=true`, bumps token budget to 16384, sets thinking-optimised sampling | ~17s / 20 rows | Best (65% fix rate on probe) |
| `--disable-thinking` | Forces `enable_thinking=false`, fast, compact output | ~50s / 20 rows | Good (55% fix rate) |
| *(no flag)* | Model decides; uses thinking by default but token budget may not be enough → empty outputs on hard cases | ~100s / 20 rows | Unreliable (60% but 3 empties) |

**Recommended: always use `--thinking` for quality runs.**

---

## Environment Setup

```bash
ssh dgx-station
cd ~/ws/sft
source .venv/bin/activate
```

---

## Run a Probe (subset of rows)

Use this to test a new model or prompt against a known set of examples before committing to a full run.

### 1. Pick your probe input

The standard 500-row probe is already at:
```
~/ws/sft/data_relabel/qwen_probe_500.jsonl
```

To create a custom probe from any input file (e.g. the 20 hardest cases):
```bash
python3 -c "
import json
rows = [json.loads(l) for l in open('data_relabel/qwen_probe_500.jsonl')]
targets = {7, 15, 16, 20, 64, 74, 85, 102, 109, 111, 112, 124, 162, 169, 249, 273, 277, 400, 462, 482}
out = [r for i, r in enumerate(rows) if i in targets]
with open('data_relabel/my_probe.jsonl', 'w') as f:
    [f.write(json.dumps(r) + '\n') for r in out]
print(len(out), 'rows written')
"
```

### 2. Run the relabeler

```bash
cd ~/ws/sft
source .venv/bin/activate

export NV_BASE_URL=http://10.33.197.85:8000/v1
export NV_MODEL=/mnt/storage/MiniMax-M2.7
export NVIDIA_API_KEY=dummy

python relabel_teacher.py \
  -i  data_relabel/my_probe.jsonl \
  -o  data_relabel/my_probe_out.jsonl \
  --compare-out data_relabel/my_probe_compare.jsonl \
  --base-url  $NV_BASE_URL \
  --model     $NV_MODEL \
  --compact-prompt \
  --thinking \
  --concurrency 8 \
  --temperature 1.0 \
  --completion-cap 8192 \
  --no-drop-empty
```

Output files:
- `my_probe_out.jsonl` — relabeled messages JSONL (ready for training)
- `my_probe_compare.jsonl` — side-by-side `{index, old_assistant, new_assistant, error, raw_tail}`

### 3. Analyse results

```bash
python data_relabel/analyze_qwen_probe.py \
  --cmp   data_relabel/my_probe_compare.jsonl \
  --input data_relabel/my_probe.jsonl
```

To compare before vs after a prompt change (reprobe):
```bash
python data_relabel/analyze_qwen_probe.py \
  --cmp     data_relabel/qwen_probe_500_compare.jsonl \
  --input   data_relabel/qwen_probe_500.jsonl \
  --reprobe my_probe   # looks for my_probe_compare.jsonl + my_probe.jsonl
```

### 4. Export results to CSV for review

```bash
python3 - << 'EOF'
import json, csv, difflib

inp   = [json.loads(l) for l in open('data_relabel/my_probe.jsonl')]
cmp   = [json.loads(l) for l in open('data_relabel/my_probe_compare.jsonl')]

with open('data_relabel/my_probe_review.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['#', 'user_input', 'gold', 'new_output', 'error'])
    for i, (row, c) in enumerate(zip(inp, cmp)):
        user = row['messages'][1]['content']
        gold = row['messages'][2]['content']
        w.writerow([i, user, gold, c.get('new_assistant',''), c.get('error','')])
print('wrote my_probe_review.csv')
EOF
```

---

## Run the Full Dataset Relabel

The full 48,608-row relabel is orchestrated by `run_full_relabel.sh`. It shards the input,
relabels each shard (resumable), and merges output.

```bash
cd ~/ws/sft
source .venv/bin/activate

# Override defaults if needed
export MINIMAX_VLLM_URL=http://10.33.197.85:8000/v1
export NVIDIA_API_KEY=dummy

# Optional tuning (these are the defaults)
export RELABEL_SHARDS=5
export RELABEL_CONCURRENCY=20
export RELABEL_BATCH_SIZE=5
export RELABEL_COMPLETION_CAP=4096
export RELABEL_REQUEST_TIMEOUT=45

bash run_full_relabel.sh
```

Note: `run_full_relabel.sh` uses `--disable-thinking` and `--compact-prompt` for speed.
For a quality run, edit the script and swap to `--thinking --completion-cap 16384`.

After completion:
```bash
python build_relabeled_dataset.py
# → writes data_combined_v5_relabeled/train_messages.jsonl  (42,967 rows)
#                                     val_messages.jsonl    (2,328 rows)
#                                     test_messages.jsonl   (2,552 rows)
```

---

## Key Files

| File | Purpose |
|---|---|
| `relabel_teacher.py` | Main relabeler — calls teacher model, parses output, writes JSONL |
| `relabel_all_unique.py` | Deduplicates all source data into one input JSONL |
| `run_full_relabel.sh` | Sharded full-dataset orchestrator (resumable) |
| `build_relabeled_dataset.py` | Splits relabeled output into train/val/test |
| `data_relabel/analyze_qwen_probe.py` | Failure analysis + before/after reprobe comparison |
| `prompts/labeler_instructions_compact.txt` | Compact labeler prompt (used with `--compact-prompt`) |
| `prompts/labeler_instructions.txt` | Full labeler prompt (appended with SYSTEM_PROMPT) |
| `data_relabel/qwen_probe_500.jsonl` | 500-row probe input |
| `data_relabel/qwen_probe_500_compare.jsonl` | 500-row baseline results (Qwen, original prompt) |
| `data_relabel/reprobe_20_review.csv` | 20 hardest cases — thinking vs no-thinking comparison |

---

## Prompt Iteration Workflow

1. Edit `prompts/labeler_instructions_compact.txt`
2. Run `relabel_teacher.py` on `data_relabel/reprobe_20.jsonl` (the 20 hard cases)
3. Run `analyze_qwen_probe.py --reprobe reprobe_20` to score before/after
4. Export CSV for manual review
5. If improvement confirmed, run on `qwen_probe_500.jsonl` for full stats
6. Commit prompt + CSV to repo

---

## Current Probe Results Summary

| Prompt version | Mode | FIXED | SAME | WORSE | Fix rate |
|---|---|---|---|---|---|
| Original prompt | thinking | 9/20 | 8/20 | 3/20 | 45% |
| V2 prompt | thinking | 13/20 | 3/20 | 4/20 | 65% |
| V2 prompt | no-thinking | 11/20 | 4/20 | 5/20 | 55% |
| V2 prompt | default | 12/20 | 3/20 | 5/20 | 60% |
