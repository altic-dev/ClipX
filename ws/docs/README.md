# 📚 Documentation

This folder contains documentation for the Voice-to-Text Dictation Cleaner project.

## Files

| File | Description |
|------|-------------|
| [TRAINING_RECIPE.md](TRAINING_RECIPE.md) | **Main experiment log** - tracks all training runs, hyperparameters, and results |
| [DATA_INVENTORY.md](DATA_INVENTORY.md) | Tracks generated bucket data, quality, and usage |
| [PROMPT_WRITING_GUIDE.md](PROMPT_WRITING_GUIDE.md) | How to write generator and verifier prompts for data creation |
| [TRAINING_NOTES.md](TRAINING_NOTES.md) | Original training notes (legacy) |
| [TRAINING_SETUP.md](TRAINING_SETUP.md) | Basic training setup instructions |

## Quick Links

### Training
- Start training: `python train/scripts/train_unsloth.py --help`
- Generate data: `python train/scripts/generate_and_verify.py <bucket> -n 500`
- Create splits: `python train/scripts/create_bucket_split.py`

### Evaluation
- Run eval: `python SLM-Eval/eval/simple_eval.py --model <model> -i <test_file>`
- Compare models: `python SLM-Eval/scripts/compare_evals.py <csv1> <csv2>`

### Data
- Bucket data: `SLM-Eval/data/dictation_mode/buckets/`
- Test files: `SLM-Eval/tests/dictation_mode/`
- Prompts: `SLM-Eval/prompts/dictation_mode/`

## Current Status

- **Best model:** bucket_5_ft (86.6% on 82-test)
- **Next:** bucket_9_ft with 7,303 examples
- **Target:** >90% on 82-test

---

*Last updated: January 4, 2026*


