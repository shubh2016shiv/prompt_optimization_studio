# OPRO: A Research-Backed Guide to Optimization by Prompting

## Abstract

Optimization by Prompting, or **OPRO**, is a method for improving prompts through measured search rather than intuition alone. A language model proposes new prompt candidates, those candidates are evaluated on examples with known answers, the results are recorded, and the next round of prompt generation uses that history as guidance. Yang et al. define this idea directly: the optimizer receives previously generated solutions together with their values, generates new solutions, and then uses new evaluations to continue the search [1]. In the prompt-setting version of the method, the “solutions” are prompts, and the “values” are task scores.

This document explains OPRO from first principles, with the goal of making the method legible to three very different readers at the same time: a new developer who needs a clean mental model, an experienced prompt engineer who needs research context and trade-offs, and a technical reviewer who needs to understand why this is a serious optimization workflow rather than a prompt-writing trick. The explanation proceeds in the order a real system is built: problem definition, required inputs, optimization loop, architecture, evaluation design, failure modes, and deployment implications.

---

## 1. Introduction

Prompt engineering is often described as a craft. In practice, that means people rewrite instructions repeatedly, inspect outputs, make localized edits, and hope the new wording generalizes beyond the examples they happened to observe. That workflow can produce strong prompts, but it scales badly. It depends on human patience, hidden experience, and a large amount of undocumented trial and error.

OPRO replaces that informal editing loop with a structured search process. The central idea is simple. Instead of asking a person to imagine what the next better prompt might be, ask a language model to generate candidate prompts after showing it the history of earlier attempts and their scores. Then measure the new candidates on a task where success can be evaluated. The next generation step receives a richer performance history, and the loop continues.

The consequence is important. OPRO does not treat prompts as prose artifacts to be polished. It treats them as **searchable objects whose quality can be measured**.

### 1.1 A direct definition

> OPRO is an iterative prompt optimization method in which a language model proposes new prompts from the history of earlier prompts and their evaluation scores, and the system keeps searching until it finds stronger prompts for the target task [1].

### 1.2 Why this matters

This definition is stronger than “automatic prompt rewriting.” It commits to three ideas at once. First, prompt quality must be grounded in evaluation rather than taste. Second, the optimizer must have access to the score history of earlier candidates. Third, the loop must run for multiple rounds so that later proposals are informed by earlier results.

That is what makes OPRO interesting from both a machine learning and software engineering perspective. It turns prompt design into an empirical loop.

---

## 2. The Problem OPRO Solves

The practical problem is not that engineers lack ideas for prompts. The problem is that they often lack a reliable way to decide which idea actually improves performance. A prompt can look more detailed, more structured, or more “professional” while still making the model worse on the task.

This gap between appearance and performance becomes severe in tasks where precision matters. Classification, mathematical reasoning, constrained extraction, moderation rules, and policy-sensitive decision tasks all have one thing in common: outputs can often be judged against a known target. In those settings, prompt-writing is not just a wording problem. It is a search problem over a space of instructions.

Yang et al. position OPRO as a natural-language approach to black-box optimization, where gradients are unavailable and the optimizer instead uses a language model plus evaluated solution histories [1]. That framing is useful because it removes the false assumption that prompt engineering is merely “explaining the task more clearly.” Sometimes clarity helps. Sometimes what matters is a specific wording pattern, order of constraints, or formatting convention that a model happens to follow more reliably.

### 2.1 A simple example

Suppose the task is to classify customer messages. An initial prompt might say:

> Read the message and assign the correct category.

That sounds acceptable, but it leaves major ambiguities unresolved. Does the model choose one category or many? What should it do when a message includes multiple issues? Should it explain its choice? Must the output follow a fixed format?

A better-performing prompt might instead say:

> Read the message carefully. Choose exactly one category from the approved list. If the message contains several issues, assign the category that best matches the customer’s primary request. Return only the category name.

The second prompt is not better because it sounds more formal. It is better only if evaluation shows that it produces more accurate classifications on real examples.

### 2.2 Why manual prompt tuning is not enough

The automatic prompt optimization literature exists because manual tuning is expensive, slow, and inconsistent. Pryzant et al. describe hand-written prompts as dependent on onerous trial-and-error effort and propose an alternative based on textual critiques and search [2]. Wang et al. later argue that strong prompts often encode task-specific knowledge and therefore require more strategic search than simple local edits can provide [3]. A later survey places these methods in a broader optimization framework, organizing them by what they optimize, how they search, and how they define success [4].

OPRO is part of that broader shift. It solves the problem of prompt selection by replacing taste with measured search.

---

## 3. The Minimum Requirements for Running OPRO

Before an engineer thinks about optimizer prompts, temperature settings, or search depth, one question matters more than all others: **Can the task be evaluated well enough to support optimization?**

OPRO requires an evaluation setup that already exists before the optimization loop begins.

The first requirement is a clearly defined task. The system must know what counts as a correct or useful output. A vague goal such as “be more helpful” is not enough.

The second requirement is a collection of examples with known expected behavior. In many cases this means labeled inputs and expected outputs. In other cases it may mean rule-based validators or judge-model criteria. What matters is that the system can compare candidate performance in a repeatable way.

The third requirement is a scoring rule. A score may be exact-match accuracy, structured field correctness, rule satisfaction, pass/fail compliance, or another metric. Without a score, OPRO has no learning signal.

The fourth requirement is an optimizer model. This is the model that receives the task description, some examples, and the history of previous prompt attempts, and then proposes new candidates.

The fifth requirement is an evaluation runtime. The official OPRO repository makes the split between optimization and evaluation explicit through separate entry points for optimization and evaluation scripts, which is a strong operational hint that candidate generation and candidate scoring should be treated as distinct stages [5].

### 3.1 Input dependency map

```text
+----------------------+
| Task definition      |
+----------+-----------+
           |
           v
+----------------------+
| Evaluation examples  |
| and expected outputs |
+----------+-----------+
           |
           v
+----------------------+
| Scoring rule         |
+----------+-----------+
           |
           v
+----------------------+      +----------------------+
| Optimizer model      |----->| Candidate prompts    |
+----------+-----------+      +----------+-----------+
           |                             |
           |                             v
           |                  +----------------------+
           +----------------->| Evaluation runtime   |
                              +----------+-----------+
                                         |
                                         v
                              +----------------------+
                              | Scored prompt history|
                              +----------------------+
```

### 3.2 Why prerequisites matter more than fancy prompting

Most prompt optimization failures are not caused by the optimizer model. They come from weak labels, noisy evaluation, or under-specified tasks. If the evaluation signal is wrong, the optimizer will faithfully improve the wrong thing. That is not a flaw in OPRO. It is a basic property of any optimization system.

---

## 4. OPRO in the Research Landscape

OPRO is easier to understand when placed alongside neighboring methods rather than treated as an isolated invention.

Yang et al. introduce OPRO as a method in which a language model receives earlier solutions and their values and proposes new solutions accordingly [1]. In the prompt optimization instantiation of the method, those solutions are instruction prompts. The paper reports that optimized prompts improved performance over human-designed prompts by up to 8% on GSM8K and by up to 50% on some Big-Bench Hard tasks [1].

Pryzant et al. propose a different automatic prompt optimization strategy. Their method, often discussed under the ProTeGi framing, builds natural-language critiques of the current prompt and uses those critiques to edit the prompt, with beam search and bandit selection guiding the search efficiently [2].

PromptAgent takes another step. Wang et al. frame prompt optimization as a strategic planning problem and use Monte Carlo tree search together with error reflection, arguing that strong prompts often require more than shallow surface edits [3].

The survey literature now treats all of these as instances of a broader optimization view of prompt engineering. Li et al. formally organize prompt optimization methods by optimization variables, objectives, and computational frameworks, making clear that prompt improvement is now a serious research area rather than an ad hoc craft [4].

### 4.1 A comparative sketch

```text
Manual prompt editing
    |
    |  human guesswork and trial-and-error
    v
Critique-based optimization
    |
    |  textual feedback + guided edits
    v
OPRO
    |
    |  prompt history + scores -> new prompt proposals
    v
Planning-based optimization
    |
    |  multi-step search over prompt states
    v
Broader automatic prompt engineering
```

### 4.2 What makes OPRO distinct

The distinctive feature of OPRO is not merely that it automates prompt editing. Its distinctive feature is that the optimizer directly reads the history of previous prompt candidates and their scores. That history acts as the search memory of the system.

---

## 5. The Core Idea of OPRO

At the center of OPRO lies a very simple state object: a history of prompt attempts and their scores. This history is sometimes called a **trajectory**, but that label can sound more mysterious than it is. In plain engineering language, it is a table of prompt candidates and evaluation outcomes.

Each entry answers two questions:

1. What prompt did we try?
2. How well did it perform?

The optimizer model reads that table and tries to infer patterns. If prompts that request verification perform better, the model may propose more precise variants of verification instructions. If prompts that force a strict output format score better, the model may push further in that direction.

The loop is therefore evidence-driven rather than intuitive. The optimizer is not hallucinating from zero. It is responding to observed performance.

### 5.1 The loop in one view

```text
Prompt history
    |
    v
Optimizer model reads task + examples + history
    |
    v
New prompt candidates
    |
    v
Evaluation on labeled examples
    |
    v
Scores appended to history
    |
    v
Next round begins with more evidence
```

### 5.2 Why this works at all

The method is plausible because large language models are already strong at pattern completion and analogy in natural language. When a model sees that certain prompt patterns are associated with higher values, it can often generate new variations that extend those patterns. Yang et al. build the entire OPRO method on this principle: the model uses natural-language solution histories and their values as the basis for the next optimization step [1].

---

## 6. The End-to-End Workflow

A readable technical guide must explain the workflow in the order it actually runs. That sounds obvious, but many documents fail because they explain a middle layer before establishing inputs and outputs.

### 6.1 Baseline evaluation

The process begins with the current prompt. That prompt is evaluated first so the system has a baseline score. Without a baseline, later gains are meaningless.

### 6.2 Build the optimizer input

The optimizer model receives a structured input that usually contains the task description, a subset of evaluation examples, and the current history of prompt candidates and their scores. This matches the central mechanism described in the OPRO paper, where the prompt given to the optimizer contains earlier solutions and their values [1].

### 6.3 Generate candidate prompts

The optimizer produces several new prompt candidates. At this stage they are only hypotheses. They are not improvements until the system measures them.

### 6.4 Evaluate the candidates

Each candidate is run on evaluation examples. The outputs are compared against the scoring rule, and a score is computed.

### 6.5 Update the history

The new prompt candidates and their scores are added to the stored history. This enlarged history becomes the basis of the next optimizer step.

### 6.6 Repeat

The loop repeats until a stopping rule is satisfied. That rule might be a fixed number of rounds, a plateau in gains, or a cost limit.

### 6.7 Select final prompts

At the end of the search, the system selects one or more high-value prompt candidates for later validation or deployment.

### 6.8 Workflow diagram

```text
+------------------+
| Current prompt   |
+---------+--------+
          |
          v
+------------------+
| Baseline scoring |
+---------+--------+
          |
          v
+-----------------------------+
| Prompt history starts here  |
+--------------+--------------+
               |
               v
+-----------------------------+
| Optimizer input: task +     |
| examples + prompt history   |
+--------------+--------------+
               |
               v
+-----------------------------+
| Optimizer model proposes    |
| new prompt candidates       |
+--------------+--------------+
               |
               v
+-----------------------------+
| Evaluation runtime scores   |
| all candidates              |
+--------------+--------------+
               |
               v
+-----------------------------+
| History is updated with     |
| new prompts and scores      |
+--------------+--------------+
               |
               v
         [repeat search]
```

---

## 7. Reference Architecture for an OPRO System

The OPRO paper defines the optimization logic, but engineering teams still need a deployable system shape. The safest way to explain that shape is to separate the **logical architecture** from any particular codebase.

At the logical level, an OPRO system needs a task configuration layer, a prompt history store, an optimizer prompt builder, an optimizer model interface, an evaluation service, and a final selection stage. The official repository reinforces the practical need for separation by providing distinct entry points for optimization and evaluation and by warning explicitly about API costs [5].

### 7.1 Service decomposition

```text
                    +-------------------------+
                    | Task config + examples  |
                    +------------+------------+
                                 |
                                 v
+--------------------+   +---------------------+   +----------------------+
| Prompt history     |<->| Optimizer prompt    |-->| Optimizer model      |
| store              |   | builder             |   | proposes candidates  |
+---------+----------+   +----------+----------+   +-----------+----------+
          ^                         |                          |
          |                         v                          |
          |              +----------------------+             |
          +--------------| Candidate registry   |<------------+
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Evaluation service   |
                         | runs task + scoring  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Selection and export |
                         +----------------------+
```

### 7.2 Why this split is useful

The optimizer and evaluator often have different operational requirements. The optimizer benefits from stronger reasoning and richer prompt synthesis. The evaluator may be called hundreds of times and therefore benefits from lower cost and higher determinism. Separating them improves both clarity and cost control.

The split also improves auditability. If optimization results later need to be defended, a clean architecture makes it possible to answer the key questions: which prompt was tried, on which examples, under which model, with which score, at what time.

---

## 8. Data Structures and Reproducibility

A measured optimization system needs measured state. The minimum durable object is a prompt evaluation record containing the candidate prompt, the resulting score, and enough metadata to reproduce the run.

### 8.1 Example state object

```text
PromptEvaluationRecord
    prompt_text: string
    score: float
    metric_name: string
    evaluator_model: string
    example_set_id: string
    iteration_index: integer
    timestamp: datetime
```

### 8.2 Why this matters

Without explicit records, teams cannot tell whether an improvement came from a prompt change, an evaluator change, a metric change, or a hidden change in the evaluation subset. In prompt optimization, undocumented state is one of the fastest ways to destroy trust in the results.

Reproducibility is especially important because OPRO can be expensive. If a run costs real money and uses many model calls, it must yield an auditable artifact rather than a vague claim that “the optimizer found something better.”

---

## 9. Candidate Selection and Final Prompt Choice

An optimization run may find several useful prompts rather than one universally best prompt. This is not a weakness. It reflects the real trade-off between raw score, readability, and robustness.

A practical selection policy often exposes three kinds of winners:

- a relatively safe early winner,
- a strong candidate from the stable high-performing region,
- the absolute top-scoring candidate.

The logic is straightforward. The earliest strong winner may generalize well because it captures obvious improvements without over-specializing. A robust high-performing prompt may be preferable when consistency matters more than squeezing out the final fraction of score. The top-scoring candidate is important because it tells the team what the search was capable of finding, even if that prompt later requires stronger validation.

### 9.1 Selection picture

```text
Optimization history
    |
    +--> early strong candidate ---------> safe deployment candidate
    |
    +--> stable upper band --------------> balanced candidate
    |
    +--> peak score ---------------------> maximum-performance candidate
```

### 9.2 Why multiple outputs are honest

Returning only one prompt hides uncertainty. Returning a small set of meaningfully different winners makes the trade-off visible. That is especially important when the evaluation subset is small and peak scores may partly reflect local overfitting.

---

## 10. Cost, Latency, and Scaling

Any serious OPRO implementation must discuss cost as early as it discusses quality. The official repository states plainly that optimization and evaluation can incur unexpectedly large API costs and advises beginning with smaller benchmark portions or fewer optimization steps [5]. That caution is not a side note. It is a systems property.

If an optimization run uses `R` rounds, `C` candidates per round, and `E` examples per candidate, then evaluation work grows roughly as `R x C x E`, before accounting for retries, judge-model passes, or logging overhead. This means that small changes in search width or evaluation set size can have major budget consequences.

### 10.1 Cost formula

```text
Total evaluation load
    ≈ rounds
    x candidates per round
    x examples per candidate
    x cost per evaluation
```

### 10.2 A common operating pattern

A strong implementation often uses a more capable model for candidate generation and a cheaper or more deterministic mechanism for evaluation. This is not just budget optimization. It reflects the fact that prompt generation and prompt scoring do different work.

### 10.3 The subset trade-off

Small evaluation subsets make search faster. ProTeGi also leans on minibatch reasoning for efficiency [2]. But small subsets increase the risk that the optimizer learns the quirks of the subset rather than the general task. The correct response is not to avoid subsets completely. The correct response is to use subsets for the search loop and then validate finalists on larger or held-out data.

---

## 11. Failure Modes and Debugging

A reliable guide must explain how the system fails, not only how it succeeds.

A common failure mode is **flat performance**. If scores do not improve over rounds, the likely causes are poor evaluation examples, a metric that cannot distinguish weak from strong prompts, or candidate prompts that are too similar to one another.

Another failure mode is **strange top prompts**. OPRO optimizes for measured score, not for readability. A high-performing prompt may look awkward, repetitive, or overly specific. That is not automatically a problem, but it is a signal to validate carefully on held-out data.

A third failure mode is **noisy ranking**. If prompt quality changes dramatically between repeated evaluations, the scoring process may be unstable. This often happens when the evaluator model is nondeterministic or the task definition is underspecified.

### 11.1 Diagnostic tree

```text
Observed weak or unstable result
          |
          +--> Is the metric reliable?
          |
          +--> Are the labels and examples high quality?
          |
          +--> Is the evaluator deterministic enough?
          |
          +--> Are candidate prompts too similar?
          |
          +--> Is the best candidate overfitting the subset?
```

### 11.2 Why debugging belongs in the main document

Prompt optimization systems are unusually sensitive to hidden assumptions in evaluation. That means debugging guidance should not be treated as an appendix. It belongs near the core architecture because evaluation quality is the main thing that determines whether the loop is trustworthy.

---

## 12. When OPRO Fits and When It Does Not

OPRO works best when the task has a measurable success condition. Classification, reasoning with known answers, structured extraction, moderation with labeled data, and policy-constrained outputs are all strong candidates.

It is much less suitable when the task is deeply subjective. Creative writing, exploratory brainstorming, or loose tone adaptation can still benefit from prompt experiments, but they do not naturally provide the kind of crisp evaluation signal that OPRO depends on.

The broader survey literature supports this distinction by framing prompt optimization methods as objective-driven systems. The choice of optimization method depends partly on what kind of feedback or target signal the task can provide [4].

### 12.1 Decision sketch

```text
Does the task have clear correctness or measurable utility?
        |
      yes ------------------> Do evaluation examples exist?
        |                               |
        |                             yes ------> OPRO is a strong candidate
        |                               |
        |                             no -------> build evaluation first
        |
      no --------------------> OPRO is probably not the first tool to use
```

---

## 13. Practical Reading of the Official OPRO Repository

The official repository does two useful things for practitioners. First, it provides distinct entry points for optimization and evaluation, including `optimize_instructions.py` and `evaluate_instructions.py`, which makes the two-stage workflow explicit [5]. Second, it warns directly about API cost and recommends smaller initial experiments [5].

These repository choices matter because they reflect practical engineering lessons. OPRO is not just a research idea. It is a workload. Running it responsibly requires bounded experiments, reproducible records, and a clear split between candidate generation and scoring.

The repository also demonstrates that the method is general enough to be applied beyond prompt optimization alone, including other optimization tasks such as linear regression and the traveling salesman problem [5]. That broader usage supports the underlying research claim that the method is a language-based optimizer, not merely a prompt-editing utility [1][5].

---

## 14. Conclusion

OPRO turns prompt engineering into an empirical optimization loop. Instead of relying only on human judgment, it lets a language model propose new prompt candidates from the history of earlier candidates and their scores, then uses repeated evaluation to guide the next round of search [1].

This is why OPRO matters. It gives prompt engineering a disciplined workflow: define the task, build an evaluation signal, generate candidates, measure them, store the results, and keep searching. In that sense, OPRO is not fundamentally about writing prettier prompts. It is about discovering prompts that perform better under a measurable objective.

Placed in context, OPRO is one major branch of automatic prompt optimization, alongside critique-based methods such as ProTeGi and planning-based methods such as PromptAgent [2][3]. The broader field now treats prompt optimization as a genuine optimization problem over prompt space rather than a purely manual art [4].

For practitioners, the most important lesson is simple. If the task can be measured, prompt engineering should eventually stop being guesswork. OPRO is one of the clearest ways to make that transition.

---

## References

[1] Chengrun Yang, Xuezhi Wang, Yifeng Lu, Hanxiao Liu, Quoc V. Le, Denny Zhou, and Xinyun Chen. **Large Language Models as Optimizers.** ICLR 2024 / arXiv:2309.03409.

[2] Reid Pryzant, Dan Iter, Jerry Li, Yin Tat Lee, Chenguang Zhu, and Michael Zeng. **Automatic Prompt Optimization with “Gradient Descent” and Beam Search.** EMNLP 2023 / arXiv:2305.03495.

[3] Xinyuan Wang, Chenxi Li, Zhen Wang, Fan Bai, Haotian Luo, Jiayou Zhang, Nebojsa Jojic, Eric P. Xing, and Zhiting Hu. **PromptAgent: Strategic Planning with Language Models Enables Expert-level Prompt Optimization.** ICLR 2024 / arXiv:2310.16427.

[4] Wenwu Li, Xiangfeng Wang, Wenhao Li, and Bo Jin. **A Survey of Automatic Prompt Engineering: An Optimization Perspective.** arXiv:2502.11560, 2025.

[5] Google DeepMind. **google-deepmind/opro official repository README.** Repository for “Large Language Models as Optimizers,” including optimization and evaluation entry points and cost precautions.
