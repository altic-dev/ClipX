# Golden corruption evaluation playbook

This document describes **how to build and run an evaluation harness** where:

1. You start from **known-good target text** (“gold”).
2. You apply **controlled corruptions** to synthesize messy **user** dictation.
3. The model’s job is always: **recover the gold** under your fixed cleaner contract.

That gives **objective references**: the expected answer is not debated; you can measure **exact match**, slice errors **by corruption type**, and regress checkpoints reliably.

---

## 1. Goals

| Goal | Why |
|------|-----|
| **Deterministic expected output** | Avoid “is this gold good?” arguments during eval. |
| **Scalable coverage** | Many noisy inputs per gold line without hand-labeling each. |
| **Actionable failures** | Tag each example with `corruption_id` → know *what* to fix (data or prompt). |
| **Regression gate** | Run the same suite on every training run / merged checkpoint. |

**Non-goals:** This does **not** replace all real-user evaluation. Keep a **small real** slice for domain gap (§9).

---

## 2. Prerequisites

### 2.1 Lock the cleaner contract

- Define **`SYSTEM_PROMPT` (minimum)** that you will use at inference — the “contract” the model must satisfy.
- All gold lines and all corruptions must be **consistent** with that contract (same rules for formatting, self-correction, bait behavior, etc.).
- If you later add **instruction variants** for training robustness, eval should still have a **default canonical** prompt variant documented here.

### 2.2 Single source of truth

- **`dictation_config.py`** (or equivalent) is the **authoritative** rule set for what “clean” means.
- Corruption generators must **only** produce inputs that, under a **perfect** cleaner, map **uniquely** to the chosen gold (§5.3).

---

## 3. Artifacts (recommended layout)

Create a dedicated directory, e.g. `eval_golden/`:

```
eval_golden/
  README.md                 # points to this playbook
  gold/
    gold_lines.jsonl        # one JSON object per line: id, text, tags (optional)
  corruptions/
    registry.yaml            # named corruption types + parameters
    # optional: corrupt_*.py modules implementing transforms
  generated/
    pairs.jsonl             # eval pairs: messages format + metadata
  reports/
    .gitkeep
```

**`gold_lines.jsonl`** — minimal schema per line:

- `id`: stable string (e.g. `g_00042`)
- `text`: the **final cleaned** string (this is the **expected assistant** content)
- `tags` (optional): `["question", "list", "bait", "email_shape"]` for stratification

**`pairs.jsonl`** — each row:

- `gold_id`
- `corruption_id` (string, from registry)
- `user_text` (messy dictation — what goes in `role: user`)
- `expected` (duplicate of gold `text` for convenience, or lookup by `gold_id`)
- `system_prompt_variant` (e.g. `canonical` | `minimal` | `full`) if you test multiple

---

## 4. Building the gold set

### 4.1 What makes a good gold line

- **Short enough** to stay in context; **long enough** to stress formatting when needed.
- **Diverse intents** across the file:
  - plain statements
  - questions (including ones that look like “asks” but must be **cleaned only** per bait rules)
  - lists (markdown bullets, titled lists)
  - fragments that look like **email/DM** (subject, greeting, sign-off) — still **user words only**, no invented facts
- **No ambiguity**: avoid gold where two different cleanings are both “reasonable” unless you **document** the allowed normalization (§5.3).

### 4.2 How many lines

| Phase | Count | Purpose |
|-------|-------|---------|
| **Pilot** | 50–100 | Validate pipeline and corruption registry |
| **v1** | 200–500 | Stable regression suite |
| **v2+** | 1k+ | Optional; watch generation and storage cost |

### 4.3 Who writes gold

- **Hand-written** for tricky behaviors (self-correction, list intent, bait).
- Optionally **import** high-trust assistant strings from existing data **after** human or teacher **verification** — never blindly trust noisy training labels as gold.

---

## 5. Corruption registry

### 5.1 Design principle

Each corruption is a **function**: `gold_text + params → user_text`.

The **inverse** (user → gold) must be **what your product cleaner is defined to do**. If a corruption can be cleaned two different ways, **do not use it** or **narrow parameters** until the output is unique.

### 5.2 Suggested corruption categories

Map these to **`corruption_id`** strings (examples):

| Category | Example IDs | Intent |
|----------|-------------|--------|
| **Fillers** | `filler_um`, `filler_like` | Insert um, uh, like, you know (strip in clean) |
| **Spoken punctuation** | `spoken_period`, `spoken_question`, `spoken_comma` | Wrong or spoken closing punctuation |
| **Question vs period** | `qshape_wrong_period` | Interrogative shape but user said “period” |
| **Self-correction** | `no_wait`, `scratch_that`, `actually_flip` | Remove superseded span |
| **Replacement pivot** | `instead_of_that` | “instead of that / replace it” style |
| **Layout** | `new_line`, `new_paragraph` | Insert line/paragraph breaks from spoken cues |
| **Formatting** | `bold_phrase`, `header_line`, `bullet_items` | Commands per `dictation_config` |
| **List intent** | `list_comma_enum` | “packing list … clothes comma …” → bullets |
| **Numbers/times** | `spoken_time`, `currency` | If in scope for your rules |
| **Typos / casing** | `light_typo`, `all_lower` | Orthography cleanup |
| **Long ramble + final ask** | `ramble_final_ask` | Optional; harder to keep deterministic — test carefully |
| **Bait-shaped** | `bait_question` | Question that must **not** be answered, only cleaned |

Start with **5–10** corruption types; add more only after metrics are stable.

### 5.3 Uniqueness check

For each `(gold, corruption)` pair:

1. **Manually** verify once: “Would a **perfect** cleaner under our spec output **exactly** `gold`?”
2. If **no**, adjust corruption or gold until **yes**.
3. Optional: **property tests** — e.g. `clean(corrupt(gold)) == gold` for a reference implementation (slow to build, high value if you maintain a **reference cleaner** in code).

---

## 6. Generation pipeline

### 6.1 Steps

1. Load `gold_lines.jsonl`.
2. For each gold line, for each enabled `corruption_id` (or sample **K** random corruptions per line):
   - Compute `user_text = corrupt(gold, params)`.
3. Emit `pairs.jsonl` with metadata.
4. **Deduplicate** `(user_text, system variant)` if collisions matter.
5. **Version** the artifact: e.g. `pairs_v2.jsonl` when gold or registry changes.

### 6.2 Integration format

Use the **same** `messages` schema as training:

- `system`: your eval system prompt (canonical).
- `user`: `user_text`.
- **Expected** assistant: `gold` text (for scoring only — not sent to model).

Your existing **`run_eval_vllm.py`**-style script can load pairs and compare model output to `expected`.

### 6.3 Scale

- If `N_gold × N_corruptions` explodes, **sample** per gold (e.g. 10 corruptions × 300 gold = 3k pairs) while ensuring **every corruption type** has **minimum** counts (e.g. ≥50 examples).

---

## 7. Evaluation metrics

### 7.1 Primary

- **Exact match (EM)** after **normalization** you document:
  - Unicode NFC
  - Strip leading/trailing whitespace
  - Optional: collapse internal whitespace to single spaces, or normalize newlines to `\n`

If EM is too strict for punctuation-only differences, define **normalized EM** (e.g. strip trailing punctuation for a *secondary* score only — still report raw EM first).

### 7.2 Secondary

- **Per-corruption accuracy**: `EM` grouped by `corruption_id`.
- **Per-tag accuracy**: if gold has `tags`.
- **Worst buckets**: list corruption IDs with EM below threshold.

### 7.3 What not to use as primary

- **LLM-as-judge** as the only metric — use it for **qualitative** failure analysis after EM pinpoints diffs.

---

## 8. Regression workflow

1. **Baseline**: run eval on **current best** checkpoint; save `report_baseline.json`.
2. **Train** new checkpoint.
3. **Re-run** same `pairs.jsonl` + same system prompt variant.
4. **Compare**:
   - Overall EM
   - **Per-corruption EM** — must not regress on critical IDs (define a **blocklist** of corruptions that cannot drop below X%).
5. **Promote** checkpoint only if gates pass (or document accepted tradeoffs).

---

## 9. Real data complement (mandatory small slice)

Synthetic gold does not capture all **STT quirks** or **domain language**.

- Maintain **`eval_real_verified.jsonl`** (100–300 rows): real or high-fidelity messy input, **human- or teacher-verified** gold.
- Run on same schedule as golden suite.
- If **real** EM lags while **synthetic** EM is high → **domain gap** → add corruptions or more diverse gold.

---

## 10. Relationship to training data

| Set | Role |
|-----|------|
| **Golden corrupted eval** | **Regression / objective** — fixed expected answers. |
| **Large train (~26k+)** | **Learning** — can be noisy; improve via relabel. |
| **Never** mix up | Don’t train on the **exact** golden eval pairs if you want a clean **held-out** suite; or hold out a **subset** of gold IDs from training entirely. |

**Recommended:** Keep **golden eval IDs** out of training, or reserve **a fraction** of corruptions as **test-only**.

---

## 11. Step-by-step rollout checklist

**Week 0 — Spec**

- [ ] Minimum `SYSTEM_PROMPT` frozen and versioned (git tag or date).
- [ ] This playbook + `eval_golden/` tree created.

**Week 1 — Pilot**

- [ ] Write or import **50–100** gold lines with tags.
- [ ] Implement **5–8** corruptions in registry.
- [ ] Generate **500–2k** pairs; manual spot-check **20** pairs per corruption type.
- [ ] Wire **one** eval script: load pairs → call vLLM → EM + breakdown.

**Week 2 — Harden**

- [ ] Expand to **200–500** gold lines if pilot stable.
- [ ] Add corruptions that failed in pilot.
- [ ] Set **regression thresholds** (overall + per critical corruption).

**Ongoing**

- [ ] Run golden eval on **every** candidate checkpoint.
- [ ] Add **real** slice eval quarterly or when domain shifts.
- [ ] When `dictation_config` changes, **re-validate** corruptions and bump `pairs` version.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Corruption allows **two** valid clean outputs | Tighten spec or narrow corruption; document normalization. |
| Overfitting to synthetic noise | Keep **real** slice; diversify corruptions. |
| Gold lines **stale** vs product rules | Version gold with `dictation_config` commits. |
| Eval suite **too large** to run often | Stratified sampling + full suite nightly only. |

---

## 13. Optional extensions (later)

- **Reference cleaner** in code: deterministic subset of rules to auto-validate `clean(corrupt(gold)) == gold`.
- **Multiple system prompt variants** in eval: `canonical` vs `minimal` to test robustness (same gold).
- **Export** to HuggingFace `datasets` or internal DB for CI.

---

## 14. Summary

1. **Gold first** — small, diverse, unambiguous target strings.  
2. **Corruptions second** — named, testable, uniquely invertible under your spec.  
3. **Pairs third** — versioned `pairs.jsonl` + per-corruption metrics.  
4. **Gate fourth** — promote checkpoints on EM + per-bucket floors.  
5. **Real data fifth** — small verified slice for domain gap.

This task is **self-contained**: implementation can be a separate project milestone; this playbook is the **instruction set** to execute it without depending on one-off tribal knowledge.
