"""
skills/__init__.py — SkillRegistry
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Central registry for all bot capabilities. Implements the Command/Tool pattern
so new skills can be added by writing one function + one register() call —
zero changes to main.py or the bot core engine.

Usage example (adding a future skill):
    # skills/check_carrier.py
    from skills import SkillRegistry

    async def _check_carrier(carrier_mc: str) -> dict:
        ...

    def register(registry: SkillRegistry) -> None:
        registry.register("check_carrier", _check_carrier)

    # Then in main.py setup_hook():
    from skills.check_carrier import register as register_carrier
    register_carrier(self.skills)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging
from typing import Any, Callable, Coroutine

log = logging.getLogger(__name__)


class SkillRegistry:
    """
    Lightweight async skill registry.

    Each registered skill is an async callable keyed by a short name string.
    Skills are invoked via execute() with keyword arguments.
    """

    def __init__(self) -> None:
        self._skills: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, name: str, func: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        """
        Register an async callable under a name.

        Args:
            name: Short identifier (e.g. "parse_and_draft", "send_email").
            func: An async function (coroutine function) to be called.
        """
        if name in self._skills:
            log.warning("Skill '%s' is being overwritten with %s.", name, func.__qualname__)
        self._skills[name] = func
        log.info("✅ Skill registered: '%s' → %s()", name, func.__qualname__)

    # ── Execution ─────────────────────────────────────────────────────────────

    async def execute(self, name: str, **kwargs: Any) -> Any:
        """
        Execute a registered skill by name with keyword arguments.

        Args:
            name:   The skill name to invoke.
            **kwargs: Arguments forwarded directly to the skill function.

        Returns:
            Whatever the skill function returns.

        Raises:
            KeyError: If the skill name has not been registered.
        """
        if name not in self._skills:
            available = ", ".join(sorted(self._skills)) or "none"
            raise KeyError(
                f"Unknown skill: '{name}'. "
                f"Currently registered: [{available}]"
            )
        log.debug("⚙️  Executing skill '%s' | args: %s", name, list(kwargs.keys()))
        return await self._skills[name](**kwargs)

    # ── Introspection ─────────────────────────────────────────────────────────

    def list_skills(self) -> list[str]:
        """Return a sorted list of all registered skill names."""
        return sorted(self._skills.keys())

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __repr__(self) -> str:
        return f"<SkillRegistry skills={self.list_skills()}>"
