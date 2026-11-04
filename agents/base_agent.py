"""
CAPSTONE CONCEPTS DEMONSTRATED:
  - Hard Stops: max_iterations cap enforced in run_loop() — every agent inherits this
  - Observability: _log() is the single place all agent activity is recorded;
      extend this method to emit spans to LangSmith, OpenTelemetry, or any tracer
  - Agent Configurations: config dataclass carries model + limits per agent
"""
import json
from typing import Any, Callable, Optional
import anthropic
from config.agent_configs import AgentConfig


class BaseAgent:
    """
    All sub-agents inherit this class.

    Two things every agent must have:
    1. A config that specifies its model, token budget, and iteration cap
    2. An agentic loop that enforces those limits and logs every step

    The agentic loop is NOT in __init__ because different agents call it with
    different system prompts and tool sets. Subclasses call run_loop() once per
    phase, passing the appropriate prompt and a tool handler callback.
    """

    def __init__(self, config: AgentConfig, tools: list[dict]):
        self.config = config
        self.tools = tools
        self.client = anthropic.Anthropic()

    def _log(self, event: str, detail: str = "") -> None:
        """
        CAPSTONE: Observability

        Every agent action goes through here: tool calls, token counts, hard stops.
        In production this would emit a span — replace the print with:
            tracer.add_event(agent=self.config.name, event=event, detail=detail)
        For now, structured console output is sufficient for the demo.
        """
        tag = f"[{self.config.name.upper():12}]"
        print(f"{tag} {event}" + (f"  {detail}" if detail else ""))

    def run_loop(
        self,
        system_prompt: str,
        user_message: str,
        on_tool_call: Callable[[str, dict], tuple[dict, Optional[Any]]],
    ) -> Optional[Any]:
        """
        CAPSTONE: Hard Stops + Observability

        Runs the agentic loop until:
        - stop_reason == "end_turn"  (agent finished)
        - max_iterations reached     (HARD STOP — safety cap)

        Args:
            on_tool_call: called when the agent uses a tool.
                          Returns (tool_result_dict, captured_output_or_None).
                          captured_output is what the caller cares about (e.g. the
                          structured data from a save_* tool). If the tool isn't the
                          "result tool", return (result_dict, None).

        Returns:
            The last non-None captured_output from on_tool_call, or None if the
            agent never called a result tool.
        """
        messages = [{"role": "user", "content": user_message}]
        result: Optional[Any] = None

        for iteration in range(1, self.config.max_iterations + 1):
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=system_prompt,
                tools=self.tools,
                messages=messages,
            )

            # CAPSTONE: Observability — token usage logged every call
            self._log(
                f"iter {iteration}/{self.config.max_iterations}",
                f"model={self.config.model}  "
                f"in={response.usage.input_tokens}  "
                f"out={response.usage.output_tokens}  "
                f"stop={response.stop_reason}",
            )

            # Print agent's visible reasoning
            for block in response.content:
                if hasattr(block, "text") and block.text.strip():
                    print(f"\n  [{self.config.name}] {block.text.strip()}\n")

            if response.stop_reason == "end_turn":
                self._log("done")
                break

            if response.stop_reason == "tool_use":
                tool_block = next(b for b in response.content if b.type == "tool_use")
                self._log("tool_call", tool_block.name)

                tool_result, captured = on_tool_call(tool_block.name, tool_block.input)
                if captured is not None:
                    result = captured

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
            # CAPSTONE: Hard Stop — loop exhausted max_iterations without end_turn
            self._log(
                "HARD STOP",
                f"reached max_iterations={self.config.max_iterations} — loop terminated",
            )

        return result
