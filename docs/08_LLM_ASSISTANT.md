# Local LLM Mapper and Assistant

## Model strategy

Start development with a capable local 12B–14B-class model through Ollama.

Once the workflow is reliable, benchmark the same test set against a 7B-class model and choose the smallest model that meets the accuracy and latency requirement.

The exact model is configuration, not application architecture.

## LLM responsibilities

The local model is good for:

- semantic field mapping;
- terminology normalisation;
- identifying package/section relationships;
- interpreting unfamiliar vendor wording;
- transforming extracted document content into canonical JSON;
- explaining why a mapping was made;
- asking focused clarification questions;
- proposing data/knowledge changes.

## LLM non-responsibilities

Do not use the model for tasks that ordinary code can do more reliably:

- arithmetic/totals;
- unit conversions with known rules;
- workbook cell placement;
- filesystem operations;
- validation comparisons;
- database writes;
- final SSD generation;
- audit logging.

## Mapper prompt behaviour

Core requirements:

- use the supplied canonical schema;
- use relevant knowledge documents as guidance;
- preserve source units unless a rule explicitly normalises them;
- do not infer missing values;
- return null when not present;
- group continuation sections/pages correctly;
- include source evidence references;
- flag ambiguity rather than guessing;
- return structured JSON.

## Context construction

Recommended context:

```text
System mapping instructions
+ Canonical schema
+ Global packing-list knowledge
+ Matched vendor/document profile
+ Relevant approved examples
+ Current document/package content
→ Local model
```

Avoid dumping the complete Knowledge folder into every prompt.

## Right-hand assistant

The assistant is job-scoped, not a global chatbot.

It should understand:

- active source document;
- selected case/field;
- current Virtual SSD values;
- source values;
- validation issues;
- relevant knowledge;
- approved project/default data;
- output mapping rules where safe to expose.

## Useful questions

Examples:

- Where did this value come from?
- Why is this case flagged?
- Which cases exceed 1,500 kg?
- What did I change from the source?
- Which fields did not come from the packing list?
- Why did this mapping use gross weight?
- What knowledge rule affected this field?
- Reprocess this case.
- Propose a knowledge update for this term.

For structured filtering/calculation questions, let Python query the canonical data and use the LLM to interpret/present the result.

## Assistant-initiated questions

When processing is genuinely ambiguous, the assistant may ask a user question.

Example:

```text
I found:
Shipping Weight: 1,280 kg
Equipment Weight: 1,095 kg

I believe:
Shipping Weight → Gross Weight
Equipment Weight → Net Weight

Is this correct?

[Yes] [No — edit mapping]
```

The job should retain already-completed processing while waiting for an answer.

## Change proposals

The assistant never silently changes working data or knowledge.

Every material change should use an explicit proposal UI with Apply/Cancel or Approve/Reject.

## Chat persistence

Store chat history per processing job so that later support can understand why a correction was made.

## Local-only requirement

Core operation should not require OpenAI, Anthropic, Azure, or another cloud model/API.

Network access may still exist for normal application administration, but source document content should remain local unless a future deployment explicitly changes that requirement.
