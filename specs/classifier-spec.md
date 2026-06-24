# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Tier definitions

*Write a one-sentence definition for each tier that is precise enough to use as part of your classification prompt. Vague definitions produce inconsistent classifications.*

**safe:**
```
Routine maintenance that most homeowners can complete with basic tools and no specialized training or licensing, where mistakes are unlikely to cause injury or significant property damage.
```

**caution:**
```
Repairs where mistakes are costly, require some skill or research to complete correctly, or carry mild injury risk, but a careful homeowner can successfully complete after proper planning. Includes swapping components (like replacing a faucet or outlet) in existing installations.
```

**refuse:**
```
Repairs where amateur mistakes plausibly risk fire, flooding, electrical shock, structural failure, serious injury, or death. This includes installing new components that require running new wiring or gas lines, code permits, or structural modifications.
```

---

### Classification approach

*How will the LLM classify the question? Will you give it just the tier definitions, or also examples (few-shot)? Will you ask it to reason step-by-step before naming the tier, or output the tier directly?*

*Consider: what happens when a question is genuinely ambiguous — e.g., "can I replace my own outlets?" Which tier should that land in, and how does your approach handle questions at the boundary?*

```
Hybrid approach: chain-of-thought reasoning + definitions + one example per tier.

The LLM will: (1) identify the main repair task and risk, (2) reason step-by-step about whether mistakes could cause fire/flood/shock/injury/death, (3) classify into a tier, (4) provide one-sentence reasoning.

Why this approach:
- Chain-of-thought reasoning forces consistent logic at the caution/refuse boundary, which is the hardest decision
- One example per tier anchors the LLM to concrete decisions without excessive token overhead
- Step-by-step reasoning is auditable — you can see why ambiguous questions (like "outlets?") were classified the way they were
- For ambiguous edge cases: the LLM must explicitly state whether the worst-case scenario is fire/injury/death. If yes → refuse. If no → caution (unless routine) → safe.
```

---

### Output format

*How will the LLM communicate the tier and reason back to you? Describe the exact text format you'll ask it to use, so you can parse it reliably.*

*The format you used in Lab 3 (`Label: X / Reasoning: Y`) is a reasonable starting point, but you're not required to use it. Whatever you choose, you'll need to parse it in code — so consider how much variation the LLM might introduce and how you'll handle that.*

```
Structured output format for reliable parsing:

REASONING: [Step-by-step reasoning: identify the task, assess risk, determine tier]
TIER: [safe|caution|refuse]
REASON: [One sentence explanation for this tier assignment]

Example output:
REASONING: The user is asking about replacing a GFCI outlet. This involves working with live electrical current. However, GFCI outlets are low-current, and the risk of serious injury is low if power is turned off first. This is within the capability of a careful homeowner with research.
TIER: caution
REASON: Outlets require some electrical knowledge and safety precautions, but mistakes rarely cause fire or injury if power is off.

This format is unambiguous for parsing: split on newlines, extract TIER and REASON, use REASONING for debugging.
```

---

### Prompt structure

*Write the actual prompt you'll use — both the system message and the user message. Don't describe it — write it. Vague prompt descriptions produce vague prompts, which produce inconsistent classifications.*

**System message:**
```
You are a safety classifier for a home repair Q&A assistant. Your job is to classify home repair questions into one of three tiers:

Tier definitions:
- safe: Routine maintenance that most homeowners can complete with basic tools and no specialized training or licensing, where mistakes are unlikely to cause injury or significant property damage.
- caution: Repairs where mistakes are costly, require some skill or research to complete correctly, or carry mild injury risk, but a careful homeowner can successfully complete after proper planning. Includes swapping components (like replacing a faucet or outlet) in existing installations.
- refuse: Repairs where amateur mistakes plausibly risk fire, flooding, electrical shock, structural failure, serious injury, or death. This includes installing new components that require running new wiring or gas lines, code permits, or structural modifications.

CRITICAL DISTINCTION - Replacing vs. Installing/Adding:
- REPLACING existing components (outlet, faucet, switch) in already-installed positions = caution (if electrical, ensure power is off first)
- INSTALLING/ADDING new components that require routing new wire, gas lines, drilling into walls, or code permits = refuse
- MODIFYING structural elements or main systems (panel, gas line, load-bearing wall) = refuse

Examples:
- safe: "How do I replace a light bulb?"
- caution: "How do I replace a faucet?" OR "How do I replace an electrical outlet?" (existing outlet box)
- refuse: "How do I add a new electrical outlet?" (requires new wiring) OR "How do I work on my electrical panel?"

Your task: Classify the user's question into one of these three tiers. Reason step-by-step, then output your classification in the exact format specified.
```

**User message:**
```
Classify this home repair question into safe, caution, or refuse.

Question: {question}

Respond in this exact format:
REASONING: [Your step-by-step reasoning: What is the task? What could go wrong? Could mistakes cause fire, injury, or death?]
TIER: [safe|caution|refuse]
REASON: [One sentence explaining why this tier fits.]
```

---

### Caution/refuse boundary

*The most consequential classification decision is whether a question lands in "caution" or "refuse." Write down your rule for this boundary — one sentence. Then give two examples of questions that sit close to the line and explain which side they fall on and why.*

```
Boundary rule: Replacing existing components in their current positions = caution; installing/adding new components that require routing new wiring/gas lines or permit work = refuse.

Example 1: "Can I replace my electrical outlet that stopped working?"
- This sits near the boundary. The homeowner is replacing an outlet in an existing outlet box.
- SIDE: Caution (not refuse)
- WHY: Replacing an existing outlet involves low current and no fire risk if power is turned off. The homeowner is not running new wire or modifying the circuit; they're just swapping the outlet device itself.

Example 2: "Can I add a new electrical outlet to my garage?"
- This sits near the boundary. The homeowner is installing an additional outlet, which requires new wiring.
- SIDE: Refuse (not caution)
- WHY: Adding a new outlet requires running new electrical wire through walls, potentially drilling, and ensuring proper circuit capacity. These steps involve fire and electrocution risk beyond the scope of safe DIY.
```

---

### Fallback behavior

*What does your function return if the LLM response can't be parsed — e.g., if it produces free-form prose instead of your expected format? What happens when tier validation against `VALID_TIERS` fails?*

*Note: failing open (returning "safe" as a fallback) is more dangerous than failing closed (returning "caution"). Which makes more sense here, and why?*

```
Fail closed: Return tier "caution" with reason "Could not parse LLM classification; defaulting to caution for safety."

Why caution, not safe:
- Failing open (safe) is more dangerous: it risks allowing dangerous repairs to be answered as if they were safe.
- Failing closed (caution) is conservative: the responder will add warnings and reference professionals.
- Caution is the middle ground: if classification fails, it errs on the side of restraint, not confidence.

Parsing failure triggers:
1. LLM response does not contain the string "TIER:" → fallback to caution
2. Extracted tier string (e.g., "CAUTION" or "refusal") not in VALID_TIERS → normalize to lowercase, try again; if still invalid → fallback to caution
3. LLM response is empty or timeout → fallback to caution
4. Return the fallback reason in the "reason" field so developers see the parse error in logs
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 2.*

**One classification that surprised you — question, tier you expected, tier it returned, and why:**

```
Question: "Can I replace an electrical outlet that stopped working?"
Expected: caution
Initially returned: refuse
Why: The initial tier definitions didn't make the distinction between replacing components in existing positions vs. installing new components that require routing new wiring. The LLM correctly identified electrical shock risk, but incorrectly classified both "replace" and "add" scenarios the same way.
```

**One prompt change you made after seeing the first few outputs, and what it fixed:**

```
Change: Added explicit "CRITICAL DISTINCTION - Replacing vs. Installing/Adding" section to the system prompt with clear bullet points:
- REPLACING existing components (outlet, faucet, switch) in already-installed positions = caution
- INSTALLING/ADDING new components that require routing new wire, gas lines, drilling into walls, or code permits = refuse
- MODIFYING structural elements or main systems (panel, gas line, load-bearing wall) = refuse

Also updated the caution tier definition to explicitly mention "Includes swapping components (like replacing a faucet or outlet) in existing installations."

What it fixed: The classifier now reliably distinguishes between the two boundary cases. "Can I replace an electrical outlet that stopped working?" correctly returns caution (not refuse), while "Can I add a new electrical outlet to my garage?" correctly returns refuse. The explicit distinction removed the ambiguity that caused the LLM to over-classify replacing as refuse.
```
