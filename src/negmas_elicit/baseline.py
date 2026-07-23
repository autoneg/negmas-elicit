"""Elicitation base classes."""

from __future__ import annotations

import time

from negmas.common import MechanismState, Value
from negmas.helpers.prob import ScipyDistribution
from negmas.outcomes import Outcome
from negmas.preferences import IPUtilityFunction

from negmas_elicit.base import BaseElicitor

__all__ = ["DummyElicitor", "FullKnowledgeElicitor"]


class DummyElicitor(BaseElicitor):
    """
    A baseline elicitation algorithm that does not perform any elicitation.

    This elicitor serves as a baseline for comparison with other elicitation
    algorithms. It simply uses the prior utility distributions without any
    updates, allowing researchers to measure the benefit of elicitation.

    This is useful for:
    - Establishing a baseline performance without elicitation
    - Testing negotiation mechanisms independently of elicitation
    - Scenarios where elicitation cost is prohibitively high
    """

    def utility_on_rejection(self, outcome: Outcome, state: MechanismState) -> Value:
        """Estimated utility if `outcome` is rejected, always the reserved
        value since this elicitor does not model the opponent's rejections.

        Args:
            outcome: Outcome to evaluate (unused).
            state: Current mechanism state (unused).

        Returns:
            `self.reserved_value`.
        """
        return self.reserved_value

    def can_elicit(self) -> bool:
        """Always `True` (kept only to satisfy the abstract interface; no
        elicitation is actually performed by this baseline).

        Returns:
            `True`.
        """
        return True

    def elicit_single(self, state: MechanismState):
        """Does nothing since this baseline never elicits.

        Args:
            state: Current mechanism state (unused).

        Returns:
            `False`, indicating no elicitation act was performed.
        """
        return False

    def init_elicitation(
        self, preferences: IPUtilityFunction | ScipyDistribution | None, **kwargs
    ):
        """Initializes elicitation using the given prior `preferences`
        unchanged (no elicitation is done) and marks every outcome as
        immediately offerable.

        Args:
            preferences: The (uncertain) prior utility function to use as is.
            **kwargs: Additional keyword arguments passed to the parent's
                      `init_elicitation`.
        """
        super().init_elicitation(preferences=preferences, **kwargs)
        strt_time = time.perf_counter()
        self.offerable_outcomes = self._nmi.outcomes
        self._elicitation_time += time.perf_counter() - strt_time


class FullKnowledgeElicitor(BaseElicitor):
    """
    A baseline elicitor with full access to the user's true utility function.

    This elicitor represents the ideal case where the negotiator has complete
    knowledge of the user's preferences without any elicitation cost. It serves
    as an upper bound for evaluating elicitation algorithms.

    This is useful for:
    - Establishing an upper bound on negotiation performance
    - Measuring the "price of uncertainty" in preference elicitation
    - Testing negotiation strategies independently of preference uncertainty
    """

    def utility_on_rejection(self, outcome: Outcome, state: MechanismState) -> Value:
        """Estimated utility if `outcome` is rejected, always the reserved
        value since this elicitor does not model the opponent's rejections.

        Args:
            outcome: Outcome to evaluate (unused).
            state: Current mechanism state (unused).

        Returns:
            `self.reserved_value`.
        """
        return self.reserved_value

    def can_elicit(self) -> bool:
        """Always `True` (kept only to satisfy the abstract interface; no
        elicitation is actually performed by this baseline).

        Returns:
            `True`.
        """
        return True

    def elicit_single(self, state: MechanismState):
        """Does nothing since this baseline never elicits.

        Args:
            state: Current mechanism state (unused).

        Returns:
            `False`, indicating no elicitation act was performed.
        """
        return False

    def init_elicitation(
        self, preferences: IPUtilityFunction | ScipyDistribution | None, **kwargs
    ):
        """Initializes elicitation using the user's true `ufun` directly
        (ignoring the `preferences` argument), so no uncertainty ever exists
        and no elicitation is done. Every outcome is marked as immediately
        offerable.

        Args:
            preferences: Ignored; the user's real `ufun` is used instead.
            **kwargs: Ignored.
        """
        super().init_elicitation(preferences=self.user.ufun)
        strt_time = time.perf_counter()
        self.offerable_outcomes = self._nmi.outcomes
        self._elicitation_time += time.perf_counter() - strt_time
