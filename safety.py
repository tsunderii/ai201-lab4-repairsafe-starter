from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into one of three safety tiers.

    Returns a dict with:
      - "tier"   : str — one of "safe", "caution", "refuse"
      - "reason" : str — a brief explanation of why this tier was assigned

    The three tiers:
      - "safe"    : routine, low-risk repairs most homeowners can handle safely
      - "caution" : doable with care, but mistakes have real cost or mild risk
      - "refuse"  : high-risk repairs that require a licensed professional —
                    mistakes can cause fire, flooding, injury, or structural damage
    """
    system_message = """You are a safety classifier for a home repair Q&A assistant. Your job is to classify home repair questions into one of three tiers:

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

Your task: Classify the user's question into one of these three tiers. Reason step-by-step, then output your classification in the exact format specified."""

    user_message = f"""Classify this home repair question into safe, caution, or refuse.

Question: {question}

Respond in this exact format:
REASONING: [Your step-by-step reasoning: What is the task? What could go wrong? Could mistakes cause fire, injury, or death?]
TIER: [safe|caution|refuse]
REASON: [One sentence explaining why this tier fits.]"""

    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=512,
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        response_text = response.choices[0].message.content

        # Fallback: If "TIER:" not in response
        if "TIER:" not in response_text:
            return {
                "tier": "caution",
                "reason": "Could not parse LLM classification; defaulting to caution for safety."
            }

        # Extract tier line
        tier_line = [line for line in response_text.split('\n') if 'TIER:' in line]
        if not tier_line:
            return {
                "tier": "caution",
                "reason": "Could not parse LLM classification; defaulting to caution for safety."
            }

        # Parse tier value: extract after "TIER:", strip brackets and whitespace, normalize to lowercase
        tier_str = tier_line[0].split('TIER:')[1].strip()
        tier_str = tier_str.strip('[]').lower()

        # Validate against VALID_TIERS
        if tier_str not in VALID_TIERS:
            return {
                "tier": "caution",
                "reason": "Could not parse LLM classification; defaulting to caution for safety."
            }

        # Extract reason from response
        reason_line = [line for line in response_text.split('\n') if 'REASON:' in line]
        if reason_line:
            reason_str = reason_line[0].split('REASON:')[1].strip()
            reason_str = reason_str.strip('[]')
        else:
            reason_str = "Classification completed."

        return {
            "tier": tier_str,
            "reason": reason_str
        }

    except Exception:
        return {
            "tier": "caution",
            "reason": "Could not parse LLM classification; defaulting to caution for safety."
        }
