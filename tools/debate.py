"""
debate.py — Cross-agent debate via mmx and agy CLIs.

Requires:
  - mmx CLI installed and authenticated
  - agy CLI installed and authenticated
  - Proxy at http://127.0.0.1:65210 (set via HTTPS_PROXY)

Usage:
  from debate import run_debate
  result = run_debate("Evaluate this paper outline...", context="...")
  print(result["consensus"])
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

# ── Configuration ──────────────────────────────────────────────────

PROXY_URL = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:65210")
DEFAULT_MODEL = "claude-sonnet-5-5-low"
MMX_BASE_URL = os.environ.get("MMX_BASE_URL", "https://api.minimax.cn")
MAX_ROUNDS = 2  # debate rounds before consensus extraction

# ── Helpers ────────────────────────────────────────────────────────


def _run_mmx(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Run a single mmx text chat and return the assistant message text."""
    env = {**os.environ, "HTTPS_PROXY": PROXY_URL}
    cmd = [
        "mmx",
        f"--base-url={MMX_BASE_URL}",
        "text", "chat",
        f"--model={model}",
        f"--message={prompt}",
        "--output=json",
        "--non-interactive",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, env=env
        )
    except FileNotFoundError:
        return "[mmx CLI not found]"
    except subprocess.TimeoutExpired:
        return "[mmx timeout]"

    if proc.returncode != 0:
        return f"[mmx error: {proc.stderr.strip()[:200]}]"

    try:
        data = json.loads(proc.stdout)
        content = data.get("content", [])
        for block in content:
            if block.get("type") == "text":
                return block["text"]
        return "[mmx returned no text content]"
    except (json.JSONDecodeError, KeyError):
        return proc.stdout.strip()[:4000]


def _run_agy(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Run a single agy --print and return the text response."""
    env = {**os.environ, "HTTPS_PROXY": PROXY_URL}
    cmd = [
        "agy",
        f"--model={model}",
        "--print",
        prompt,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, env=env
        )
    except FileNotFoundError:
        return "[agy CLI not found]"
    except subprocess.TimeoutExpired:
        return "[agy timeout]"

    if proc.returncode != 0:
        return f"[agy error: {proc.stderr.strip()[:200]}]"

    return proc.stdout.strip()[:4000]


def _call_agent(
    agent: str, prompt: str, model: str = DEFAULT_MODEL
) -> str:
    """Dispatch to the correct CLI."""
    if agent == "mmx":
        return _run_mmx(prompt, model=model)
    elif agent == "agy":
        return _run_agy(prompt, model=model)
    else:
        return f"[unknown agent: {agent}]"


# ── Consensus extraction ───────────────────────────────────────────


def _extract_consensus(
    agent_a: str, response_a: str, agent_b: str, response_b: str
) -> dict[str, Any]:
    """
    Cross-validate two agent responses and extract consensus.
    Calls both agents to analyze each other's responses, then synthesizes.
    """
    synthesis_prompt = (
        "Two reviewers have evaluated the same work. "
        "Your task: (1) identify points of agreement, (2) identify points of disagreement, "
        "(3) provide a synthesized recommendation. "
        "Be concise and evidence-based.\n\n"
        f"=== Reviewer A ({agent_a}) ===\n{response_a[:3000]}\n\n"
        f"=== Reviewer B ({agent_b}) ===\n{response_b[:3000]}\n\n"
        "Respond in JSON format with keys: "
        "agreements (list of strings), disagreements (list of strings), recommendation (string)."
    )

    # Call both agents independently for cross-validation
    validation_a = _call_agent(agent_a, synthesis_prompt)
    validation_b = _call_agent(agent_b, synthesis_prompt)

    # Extract agreements/disagreements from both responses
    # Simple heuristic: look for JSON-like structures or key phrases
    agreements = []
    disagreements = []
    recommendation = ""

    for validation in [validation_a, validation_b]:
        # Try to extract JSON
        try:
            # Find JSON-like content
            import re
            json_match = re.search(r'\{.*\}', validation, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if isinstance(data, dict):
                    agreements.extend(data.get("agreements", []))
                    disagreements.extend(data.get("disagreements", []))
                    recommendation = data.get("recommendation", recommendation)
        except (json.JSONDecodeError, AttributeError):
            # Fallback: extract key phrases
            if "agree" in validation.lower():
                agreements.append("Both agents agree on key points (see raw responses)")
            if "disagree" in validation.lower():
                disagreements.append("Agents have differing perspectives (see raw responses)")

    # Deduplicate
    agreements = list(dict.fromkeys(agreements))[:5]
    disagreements = list(dict.fromkeys(disagreements))[:5]

    if not recommendation:
        recommendation = "Review both agent responses for detailed analysis."

    return {
        "agent_a": agent_a,
        "agent_b": agent_b,
        "response_a": response_a,
        "response_b": response_b,
        "cross_validation": {
            agent_a: validation_a[:2000],
            agent_b: validation_b[:2000],
        },
        "agreements": agreements,
        "disagreements": disagreements,
        "recommendation": recommendation,
        "synthesis": f"Cross-validated by {agent_a} and {agent_b}. "
                     f"Agreements: {len(agreements)}, Disagreements: {len(disagreements)}.",
    }


# ── Public API ─────────────────────────────────────────────────────


def run_debate(
    prompt: str,
    *,
    agent_a: str = "mmx",
    agent_b: str = "agy",
    model: str = DEFAULT_MODEL,
    rounds: int = MAX_ROUNDS,
    context: str = "",
    agent_c: str | None = None,
) -> dict[str, Any]:
    """
    Run a cross-agent debate and return structured results.

    Args:
        prompt: The core question or task for both agents.
        agent_a: First agent CLI name ('mmx' or 'agy').
        agent_b: Second agent CLI name.
        model: Model identifier for both agents.
        rounds: Number of debate rounds (agents see each other's prior responses).
        context: Optional background context prepended to prompt.
        agent_c: Optional third agent for consensus extraction. Defaults to agent_a.

    Returns:
        dict with keys:
          - prompt: original prompt
          - context: optional context
          - rounds: list of per-round results
          - final_consensus: synthesis dict
          - status: 'ok' | 'partial' | 'error'
    """
    full_prompt = f"{context}\n\n{prompt}" if context else prompt

    history_a = ""
    history_b = ""
    rounds_result = []

    for i in range(rounds):
        # Build prompts with prior round context
        if i == 0:
            prompt_a = full_prompt
            prompt_b = full_prompt
        else:
            prompt_a = (
                f"{full_prompt}\n\n"
                f"=== Prior round {i} — {agent_b} said ===\n{history_b}\n\n"
                f"Now respond, addressing any disagreements or building on agreements."
            )
            prompt_b = (
                f"{full_prompt}\n\n"
                f"=== Prior round {i} — {agent_a} said ===\n{history_a}\n\n"
                f"Now respond, addressing any disagreements or building on agreements."
            )

        resp_a = _call_agent(agent_a, prompt_a, model=model)
        resp_b = _call_agent(agent_b, prompt_b, model=model)

        history_a = resp_a
        history_b = resp_b

        rounds_result.append(
            {
                "round": i + 1,
                agent_a: resp_a[:2000],
                agent_b: resp_b[:2000],
            }
        )

    # Consensus extraction
    synthesizer = agent_c or agent_a
    try:
        consensus = _extract_consensus(
            agent_a, history_a, agent_b, history_b
        )
        status = "ok"
    except Exception as exc:
        consensus = {"error": str(exc)}
        status = "partial"

    return {
        "prompt": prompt,
        "context": context,
        "agent_a": agent_a,
        "agent_b": agent_b,
        "rounds": rounds_result,
        "final_consensus": consensus,
        "status": status,
    }


def debate_to_markdown(result: dict[str, Any]) -> str:
    """Format debate result as markdown for writing into files."""
    lines = [
        f"# Debate: {result['prompt'][:80]}",
        "",
        f"**Agents**: {result['agent_a']} vs {result['agent_b']}",
        f"**Status**: {result['status']}",
        "",
        "## Rounds",
        "",
    ]
    for r in result.get("rounds", []):
        lines.append(f"### Round {r['round']}")
        lines.append("")
        lines.append(f"**{result['agent_a']}**:")
        lines.append("")
        lines.append(r.get(result["agent_a"], ""))
        lines.append("")
        lines.append(f"**{result['agent_b']}**:")
        lines.append("")
        lines.append(r.get(result["agent_b"], ""))
        lines.append("")

    consensus = result.get("final_consensus", {})
    if consensus:
        lines.append("## Consensus")
        lines.append("")
        lines.append(consensus.get("synthesis", str(consensus)))
        lines.append("")

    return "\n".join(lines)
