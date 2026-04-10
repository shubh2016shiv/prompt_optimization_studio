"""
Concrete strategy implementations for APOST prompt optimizations.

This directory contains all 13 framework strategy classes that implement
BaseOptimizerStrategy:

1. kernel_optimizer.py - KERNEL
2. xml_structured_optimizer.py - XML Structured Bounding
3. create_optimizer.py - CREATE
4. progressive_disclosure_optimizer.py - Progressive Disclosure
5. reasoning_aware_optimizer.py - Reasoning-Aware
6. cot_ensemble_optimizer.py - CoT Ensemble / Medprompt
7. tcrte_coverage_optimizer.py - TCRTE Coverage-First
8. textgrad_iterative_optimizer.py - TextGrad Iterative
9. overshoot_undershoot_optimizer.py - Overshoot/Undershoot
10. core_attention_optimizer.py - CoRe Attention-Aware
11. ral_writer_optimizer.py - RAL-Writer
12. opro_trajectory_optimizer.py - OPRO trajectory optimization
13. sammo_topological_optimizer.py - SAMMO structure-aware multi-objective optimization
"""