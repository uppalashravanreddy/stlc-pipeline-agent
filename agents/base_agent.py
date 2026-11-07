"""
CAPSTONE CONCEPTS DEMONSTRATED:
  - Hard Stops: max_iterations cap enforced in run_loop()
  - Observability: _log() writes to console AND a structured JSONL log file.
      Every agent event — iterations, token counts, tool calls, hard stops —
      is recorded with a timestamp. Open logs/ after a run to see the full trace.
  - Agent Configurations: config dataclass carries model + limits per agent
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
import anthropic
from config.agent_configs import AgentConfig

LOGS_DIR = Path(__file__).parent.parent / "logs"


class BaseAgent:
    """
    All sub-agents inherit this class.
    Set agent.log_path before calling run_loop() to enable file logging.
    The orchestrator sets this at the start of each pipeline run.
    """

    def __init__(self, config: AgentConfig, tools: list[dict]):
        self.config  = config
        self.tools   = tools
        self.client  = anthropic.Anthropic()
        self.log_path: Optional[Path] = None   # set by orchestrator

    # ── Observability ─────────────────────────────────────────────────────────

    def _log(self, event: str, detail: str = "", **extra) -> None:
        """
        CAPSTONE: Observability

        Writes every agent event to:
          1. Console (immediate visibility during the run)
          2. JSONL log file (persistent audit trail — open after the run)

        Each log entry captures:
          timestamp, agent name, event type, detail, and any extra fields
          (tokens_in, tokens_out, stop_reason, tool_name, iteration)

        In production: replace the file write with a LangSmith span:
            tracer.add_event(name=event, metadata={...})
        """
        tag = f"[{self.config.name.upper():12}]"
        print(f"{tag} {event}" + (f"  {detail}" if detail else ""))

        if self.log_path:
            entry = {
                "ts":     datetime.now(timezone.utc).isoformat(),
                "agent":  self.config.name,
                "event":  event,
                "detail": detail,
                **extra,
            }
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

    # ── Agentic loop ──────────────────────────────────────────────────────────

    def run_loop(
        self,
        system_prompt: str,
        user_message: str,
        on_tool_call: Callable[[str, dict], tuple[dict, Optional[Any]]],
        phase_label: str = "",          # e.g. "Phase 0+1 — Classify + Test Plan"
    ) -> Optional[Any]:
        """
        CAPSTONE: Hard Stops + Observability

        Runs until end_turn, tool_use handled, or max_iterations (HARD STOP).
        Handles max_tokens by nudging the agent to call the tool immediately.

        phase_label: shown in every log line so you know which phase is running,
                     what the token budget is, and what percentage is consumed.
        """
        messages = [{"role": "user", "content": user_message}]
        results: list = []
        budget = self.config.max_tokens

        # CAPSTONE: Prompt Caching
        # The system prompt is static — same text on every iteration and every run.
        # Marking it with cache_control stores it after the first call.
        # Subsequent calls within 5 min use the cached version at ~90% cheaper input tokens.
        # Change: system= string  →  system= list with cache_control block
        cached_system = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        for iteration in range(1, self.config.max_iterations + 1):
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=budget,
                system=cached_system,
                tools=self.tools,
                messages=messages,
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            )

            out_tokens    = response.usage.output_tokens
            in_tokens     = response.usage.input_tokens
            cache_created = getattr(response.usage, "cache_creation_input_tokens", 0)
            cache_read    = getattr(response.usage, "cache_read_input_tokens", 0)
            pct_used      = round(out_tokens / budget * 100, 1)

            # Show cache activity in the log
            cache_note = ""
            if cache_created: cache_note = f" | cache_written={cache_created:,}"
            if cache_read:    cache_note = f" | cache_hit={cache_read:,} (saved)"

            # Log line: agent | phase | iter | model | budget | in | out% | cache | stop
            self._log(
                f"{phase_label} | iter {iteration}/{self.config.max_iterations}",
                f"model={self.config.model} | "
                f"budget={budget:,} | "
                f"in={in_tokens:,} | "
                f"out={out_tokens:,}/{budget:,} ({pct_used}%){cache_note} | "
                f"stop={response.stop_reason}",
                iteration=iteration,
                phase=phase_label,
                tokens_in=in_tokens,
                tokens_out=out_tokens,
                token_budget=budget,
                pct_budget_used=pct_used,
                cache_created=cache_created,
                cache_read=cache_read,
                stop_reason=response.stop_reason,
            )

            for block in response.content:
                if hasattr(block, "text") and block.text.strip():
                    print(f"\n  [{self.config.name}] {block.text.strip()}\n")

            if response.stop_reason == "end_turn":
                self._log("done")
                break

            if response.stop_reason == "max_tokens":
                self._log("max_tokens_hit", "nudging agent to call tool now")
                messages.append({"role": "assistant", "content": response.content})

                # CRITICAL: if the truncated response has a tool_use block,
                # the API requires a tool_result before any new user message.
                # Missing this causes 400 "tool_use without tool_result".
                pending_tool_uses = [
                    b for b in response.content
                    if hasattr(b, "type") and b.type == "tool_use"
                ]
                if pending_tool_uses:
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": b.id,
                                "content": json.dumps({
                                    "status": "interrupted",
                                    "message": "Response was cut off. Call the save tool with data generated so far.",
                                }),
                            }
                            for b in pending_tool_uses
                        ],
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": (
                            "You were cut off at the token limit. "
                            "Call the save tool NOW with whatever you have generated so far. "
                            "Do not re-plan or regenerate — just call the tool immediately."
                        ),
                    })
                continue

            if response.stop_reason == "tool_use":
                tool_block = next(b for b in response.content if b.type == "tool_use")
                self._log("tool_call", tool_block.name, tool=tool_block.name)

                tool_result, captured = on_tool_call(tool_block.name, tool_block.input)
                if captured is not None:
                    results.append(captured)   # keep every result, not just last

                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": json.dumps(tool_result),
                    }],
                })

        else:
            self._log(
                "HARD_STOP",
                f"reached max_iterations={self.config.max_iterations}",
                max_iterations=self.config.max_iterations,
            )

        return results   # list of all captured outputs (may be empty)
