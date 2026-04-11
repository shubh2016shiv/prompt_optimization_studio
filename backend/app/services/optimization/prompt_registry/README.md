# Prompt Registry

This package centralizes optimization prompt templates used by framework optimizers.

Conventions:
- File naming: `<prompt_purpose>.py`
- Static templates export: `TEMPLATE`
- Formatted templates export: `build_<prompt_name>(...) -> str`
- Prompt modules must stay prompt-only (no LLM calls, no optimizer logic, no side effects)

Rule:
- New framework prompts should be added in `prompt_registry` and imported by optimizers.

TODO:
- Migrate `few_shot_corpus.py` prompt-pair data in a follow-up change.