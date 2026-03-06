"""Watchdog for the agent runner.

Monitors agent engine execution and automatically restarts it if the engine
crashes while the session is still active.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from codex.agents.engine import AgentEngine
    from codex.db.models import AgentSession

logger = logging.getLogger(__name__)

# Session statuses that are considered "active" (eligible for restart)
_ACTIVE_STATUSES = frozenset({"pending", "running"})


class AgentWatchdog:
    """Monitors agent engine execution and restarts it on crash if the session is still active.

    The watchdog wraps :meth:`AgentEngine.run` with retry logic. If the engine raises
    an unexpected exception *and* the associated session is still in an active state
    (``"pending"`` or ``"running"``), the watchdog retries the execution up to
    ``max_retries`` times, waiting an exponentially increasing delay between attempts.

    If the session is no longer active (e.g. it was cancelled externally) the watchdog
    stops retrying and re-raises the last exception immediately.
    """

    DEFAULT_MAX_RETRIES: int = 3
    DEFAULT_BASE_DELAY: float = 1.0  # seconds

    def __init__(
        self,
        engine: AgentEngine,
        session: AgentSession,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
    ) -> None:
        """Initialise the watchdog.

        Args:
            engine: The :class:`AgentEngine` instance to monitor.
            session: The :class:`AgentSession` being executed. Its ``status``
                attribute is checked before each retry to decide whether the
                session is still active.
            max_retries: Maximum number of restart attempts after the first
                failure (default ``3``).
            base_delay: Base delay in seconds used for exponential back-off
                between retries (default ``1.0``). The actual delay before
                attempt *n* is ``base_delay * 2 ** (n - 1)``.
        """
        self.engine = engine
        self.session = session
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._attempts: int = 0

    @property
    def attempts(self) -> int:
        """Number of execution attempts made so far."""
        return self._attempts

    def _is_session_active(self) -> bool:
        """Return ``True`` if the session is still eligible for a restart."""
        return self.session.status in _ACTIVE_STATUSES

    async def run(
        self,
        user_message: str,
        system_prompt: str | None = None,
        on_action: Callable[[dict[str, Any]], None] | None = None,
    ) -> str:
        """Run the agent engine with watchdog monitoring.

        Delegates to :meth:`AgentEngine.run`. If the engine raises an unexpected
        exception the watchdog checks whether the session is still active and, if
        so, retries the execution after an exponential back-off delay.

        Args:
            user_message: The user's task or question forwarded to the engine.
            system_prompt: Optional override for the engine's system prompt.
            on_action: Optional callback invoked by the engine on each tool call.

        Returns:
            The agent's final text response.

        Raises:
            Exception: The last exception raised by the engine once all retries
                are exhausted or the session is no longer active.
        """
        last_exc: BaseException | None = None

        while self._attempts <= self.max_retries:
            if self._attempts > 0:
                # Before retrying, check that the session is still active.
                if not self._is_session_active():
                    logger.info(
                        "Session %s is no longer active (status=%r); watchdog will not retry.",
                        self.session.id,
                        self.session.status,
                    )
                    break

                delay = self.base_delay * (2 ** (self._attempts - 1))
                logger.warning(
                    "Agent engine crashed (attempt %d/%d); retrying in %.1fs. "
                    "session_id=%s error=%r",
                    self._attempts,
                    self.max_retries + 1,
                    delay,
                    self.session.id,
                    last_exc,
                )
                await asyncio.sleep(delay)

            self._attempts += 1

            try:
                return await self.engine.run(
                    user_message,
                    system_prompt=system_prompt,
                    on_action=on_action,
                )
            except Exception as exc:
                last_exc = exc
                logger.error(
                    "Agent engine raised an exception (attempt %d/%d): %r",
                    self._attempts,
                    self.max_retries + 1,
                    exc,
                    exc_info=True,
                )

        # All retries exhausted or session became inactive — re-raise.
        assert last_exc is not None, "No exception captured despite retry loop exit"
        raise last_exc
