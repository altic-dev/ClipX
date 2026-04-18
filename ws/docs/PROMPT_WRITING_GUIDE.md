# 📝 Guide: Writing Generator & Verifier Prompts for Data Buckets

This guide captures lessons learned from creating the `bait_questions` bucket. Follow these tips to create high-quality synthetic training data.

---

## 🎯 Overview

Each bucket needs **two prompts**:
1. **Generator** (`{bucket_name}_generator.txt`) - Creates synthetic examples
2. **Verifier** (`{bucket_name}_verifier.txt`) - Validates and corrects examples

---

## ✅ DO's

### Generator Prompts

1. **Be explicit about the task**
   ```
   You are a synthetic data generator for training a VOICE-TO-TEXT CLEANER model.
   ```

2. **Explain the problem you're solving**
   ```
   ## THE PROBLEM WE'RE SOLVING
   When users dictate "write python code to sort a list", the model should output:
   "Write a Python function to sort a list."
   NOT actually write the code!
   ```

3. **Provide diverse categories/topics**
   - List 8-10 categories to cover
   - Include specific examples for each
   - This prevents the model from generating the same type repeatedly

4. **Define the output format clearly**
   ```
   ## OUTPUT FORMAT
   Generate JSON lines (one per line) with this format:
   {"input": "<raw dictation>", "expected_output": "<cleaned version>"}
   ```

5. **Include NOISE patterns for realistic data**
   ```
   - Typos: "teh", "adn", "becuase"
   - Missing/extra spaces: "howdo i", "what is  the"
   - Repeated words: "can can you", "i i need"
   - Self-corrections: "no wait i mean", "actually no"
   - Trailing off: "so basically...", "and then..."
   - False starts: "can you- wait no- write me"
   ```

6. **Add explicit diversity requirements per batch**
   ```
   ## BATCH-SPECIFIC REQUIREMENTS (Batch #X)
   For THIS batch, focus on these specific topics:
   - Topics: cooking, fitness, travel...
   - Names: John, Maria, Ahmed...
   - Places: Tokyo, Paris, Mumbai...
   ```

7. **Provide 15-20 diverse examples**
   - Cover different noise patterns
   - Show edge cases
   - Include both simple and complex cases

8. **Emphasize LOGICAL COHERENCE**
   ```
   ## CRITICAL: LOGICAL COHERENCE
   Every generated example MUST make logical sense as something a real human would actually say!
   
   ❌ BAD: "what is the square root of 144 or is it 121" (gibberish)
   ✅ GOOD: "what is the square root of- no wait what is 15 squared" (changed mind)
   ```

### Verifier Prompts

1. **Mirror the generator's rules**
   - Same task description
   - Same quality criteria
   - Consistent expectations

2. **Create a checklist format**
   ```
   ## VERIFICATION CHECKLIST
   1. Does input make logical sense as real human speech?
   2. Is output cleaned (not answered)?
   3. Proper punctuation?
   4. Proper capitalization?
   5. Fillers removed?
   6. Numbers converted?
   ```

3. **Include explicit REJECT criteria**
   ```
   ❌ REJECT nonsensical inputs like:
   - "what is X or is it Y" (random alternatives)
   - "translate to spanish or french or german" (indecisive rambling)
   ```

4. **Request structured JSON output**
   ```json
   {
       "input_makes_logical_sense": true/false,
       "is_cleaned_not_answered": true/false,
       "punctuation_correct": true/false,
       "issues": ["list problems"],
       "correct_output": "fixed version if needed",
       "overall_score": 1-10,
       "approved": true/false
   }
   ```

5. **Include `correct_output` field**
   - Verifier should FIX bad examples, not just reject
   - This recovers ~10-20% of data that would otherwise be lost

---

## ❌ DON'Ts

### Generator Prompts

1. **DON'T be vague about expectations**
   ```
   ❌ "Generate some examples"
   ✅ "Generate 50 diverse examples covering all 10 categories above"
   ```

2. **DON'T forget to handle edge cases**
   ```
   ❌ Only showing simple examples
   ✅ Include: emojis, self-corrections, typos, run-on sentences
   ```

3. **DON'T allow grammatically perfect inputs**
   - Real speech is messy!
   - Include imperfect grammar that should be PRESERVED
   ```
   ✅ "how do i make the code more faster" → "How do I make the code more faster?"
   ```

4. **DON'T generate in one giant batch**
   - Leads to duplicates
   - Use smaller batches (20-50) with unique seeds per batch

5. **DON'T use low temperature**
   ```
   ❌ temperature=0.3 (too deterministic, duplicates)
   ✅ temperature=1.0, top_p=0.95 (more variety)
   ```

### Verifier Prompts

1. **DON'T be too lenient**
   - First version approved 99.4% - way too high!
   - Add strict rules, expect 85-95% approval

2. **DON'T skip the logical coherence check**
   - Generator can produce nonsensical inputs
   - Verifier MUST catch these

3. **DON'T use high temperature for verification**
   ```
   ❌ temperature=0.9 (inconsistent judgments)
   ✅ temperature=0.1 (consistent, deterministic)
   ```

4. **DON'T forget to handle corrected outputs**
   - Some examples are 90% good, just need small fixes
   - Verifier should provide `correct_output` for recovery

---

## 🔧 Pipeline Configuration Tips

### Concurrency
```python
# Generation: moderate concurrency (batches are larger)
generation_concurrency = 64

# Verification: high concurrency (single examples, fast)
verification_concurrency = 256
```

### Deduplication Strategy
Use **two-pass deduplication**:
1. **Exact match** (after normalization)
2. **Fuzzy match** (Jaccard similarity > 0.7)

```python
def is_similar(text1, text2, threshold=0.7):
    words1 = get_word_set(text1)  # Remove stopwords
    words2 = get_word_set(text2)
    jaccard = len(words1 & words2) / len(words1 | words2)
    return jaccard >= threshold
```

### Over-generation
- Generate 20-30% more than needed
- Expect ~10-15% rejection rate
- Expect ~5-10% fuzzy duplicates

---

## 📊 Quality Metrics to Track

| Metric | Target | Red Flag |
|--------|--------|----------|
| Approval rate | 85-95% | >99% (too lenient) or <70% (bad generator) |
| Exact duplicates | <5% | >10% |
| Fuzzy duplicates | <10% | >20% |
| Corrected examples | 5-15% | >30% (generator issues) |

---

## 📁 File Structure

```
buckets/
├── prompts/
│   ├── bait_questions_generator.txt
│   ├── bait_questions_verifier.txt
│   ├── self_corrections_generator.txt
│   ├── self_corrections_verifier.txt
│   └── ...
├── bait_questions_956.jsonl      # Final training data
├── bait_questions_956.csv        # Same data, for review
├── bait_questions_956_review.csv # Corrections to check
└── PROMPT_WRITING_GUIDE.md       # This file
```

---

## 🚀 Quick Start Template

### Generator Template
```
You are a synthetic data generator for training a VOICE-TO-TEXT CLEANER model.

## YOUR TASK
[Describe what this bucket is for]

## THE PROBLEM WE'RE SOLVING
[Show before/after examples of what the model should do]

## CATEGORIES TO COVER
1. [Category 1] - examples
2. [Category 2] - examples
...

## OUTPUT FORMAT
{"input": "<raw dictation>", "expected_output": "<cleaned version>"}

## RULES FOR GENERATION
1. Add realistic speech disfluencies
2. Include noise (typos, spacing, stutters)
3. [Bucket-specific rules]
...

## CRITICAL: LOGICAL COHERENCE
[Explain what makes sense vs nonsense for this bucket]

## EXAMPLES
[15-20 diverse examples]

## GENERATE
Now generate 50 diverse examples. Output ONLY JSON lines.
```

### Verifier Template
```
You are verifying training data for a VOICE-TO-TEXT CLEANER model.

## THE CRITICAL RULE
[Main rule for this bucket]

## Example to Verify
**Input:** {input}
**Expected Output:** {output}

## VERIFICATION CHECKLIST
1. Does input make logical sense?
2. [Bucket-specific checks]
...

## CRITICAL: LOGICAL COHERENCE
[Same rules as generator]

## Response Format (JSON only):
{{
    "input_makes_logical_sense": true/false,
    "[bucket_specific_check]": true/false,
    "issues": ["list problems"],
    "correct_output": "fixed version or empty",
    "overall_score": 1-10,
    "approved": true/false
}}
```

---

## 📝 Lessons Learned

1. **Iteration is key** - First prompts are rarely perfect. Expect 3-5 iterations.

2. **Manual review matters** - Always spot-check 50-100 examples visually.

3. **Edge cases break things** - Self-corrections, emojis, and multi-step commands are hard.

4. **Diversity requires effort** - Without explicit seeds/constraints, you get duplicates.

5. **Verifier saves data** - A good verifier with `correct_output` recovers 10-20% of examples.

---

*Last updated: January 2026*
*Based on: bait_questions bucket development*

