"""Preference elicitation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from negmas.common import MechanismState, NegotiatorMechanismInterface, Value
from negmas.negotiators.helpers import PolyAspiration

__all__ = [
    "Expector",
    "StaticExpector",
    "MeanExpector",
    "MaxExpector",
    "MinExpector",
    "BalancedExpector",
    "AspiringExpector",
]


class Expector(ABC):
    """
    Finds an `expectation` of a utility value.

    This is not necessarily the mathematical expected value but it can be any
    reduction method that receives a utility value and return a real number.
    """

    def __init__(self, nmi: NegotiatorMechanismInterface | None = None):
        """Creates an expector.

        Args:
            nmi: [Optional] The `NegotiatorMechanismInterface` of the current
                 negotiation. Used by expectors that need the negotiation
                 state (e.g. relative time) when it is not passed explicitly
                 to `__call__`.
        """
        self.nmi = nmi

    @abstractmethod
    def is_dependent_on_negotiation_info(self) -> bool:
        """Returns `True` if the expected value depends in any way on the negotiation state/settings"""
        ...

    @abstractmethod
    def __call__(self, u: Value, state: MechanismState = None) -> float:
        """Reduces a (possibly probabilistic) utility value to a real number.

        Args:
            u: The utility value to reduce. May be a `float` (returned as
               is) or a `Value` distribution.
            state: [Optional] The current mechanism state, needed by
                   expectors whose result depends on the negotiation's
                   progress (e.g. relative time).

        Returns:
            The reduced real-valued utility estimate.
        """
        ...


class StaticExpector(Expector):
    """An `Expector` whose reduction of a utility distribution to a real
    number does not depend on the negotiation state (e.g. relative time)."""

    def is_dependent_on_negotiation_info(self) -> bool:
        """Always `False` for static expectors.

        Returns:
            `False`.
        """
        return False

    @abstractmethod
    def __call__(self, u: Value, state: MechanismState = None) -> float:
        """Reduces a (possibly probabilistic) utility value to a real number
        independently of the negotiation state.

        Args:
            u: The utility value to reduce.
            state: Ignored (kept for interface compatibility).

        Returns:
            The reduced real-valued utility estimate.
        """
        ...


class MeanExpector(StaticExpector):
    """Reduces a utility value to its mean (expected value)."""

    def __call__(self, u: Value, state: MechanismState = None) -> float:
        """Returns the mean of `u`: `u` itself if it is already a `float`,
        or `float(u)` (the distribution's mean) otherwise.

        Args:
            u: The utility value to reduce.
            state: Ignored.

        Returns:
            The mean utility estimate.
        """
        return u if isinstance(u, float) else float(u)


class MaxExpector(StaticExpector):
    """Reduces a utility value to its maximum (upper bound), representing an
    optimistic estimate."""

    def __call__(self, u: Value, state: MechanismState = None) -> float:
        """Returns the upper bound of `u`: `u` itself if it is already a
        `float`, or `u.loc + u.scale` otherwise.

        Args:
            u: The utility value to reduce.
            state: Ignored.

        Returns:
            The maximum (upper-bound) utility estimate.
        """
        return u if isinstance(u, float) else u.loc + u.scale


class MinExpector(StaticExpector):
    """Reduces a utility value to its minimum (lower bound), representing a
    pessimistic estimate."""

    def __call__(self, u: Value, state: MechanismState = None) -> float:
        """Returns the lower bound of `u`: `u` itself if it is already a
        `float`, or `u.loc` otherwise.

        Args:
            u: The utility value to reduce.
            state: Ignored.

        Returns:
            The minimum (lower-bound) utility estimate.
        """
        return u if isinstance(u, float) else u.loc


class BalancedExpector(Expector):
    """Reduces a utility value by linearly interpolating between its lower
    and upper bounds based on the negotiation's relative time.

    Early in the negotiation (`relative_time` close to 0) it behaves
    optimistically (close to the upper bound); as the negotiation progresses
    towards its end (`relative_time` close to 1) it becomes pessimistic
    (close to the lower bound). This mirrors a negotiator that starts tough
    and concedes over time.
    """

    def is_dependent_on_negotiation_info(self) -> bool:
        """Always `True` since the result depends on relative time.

        Returns:
            `True`.
        """
        return True

    def __call__(self, u: Value, state: MechanismState = None) -> float:
        r"""Computes :math:`t \cdot loc + (1-t) \cdot (loc + scale)` where
        :math:`t` is `state.relative_time` (or `self.nmi.state` if `state`
        is `None`).

        Args:
            u: The utility value to reduce.
            state: [Optional] The current mechanism state. If `None`, uses
                   `self.nmi.state`.

        Returns:
            The time-balanced utility estimate (`u` itself if it is already
            a `float`).
        """
        if state is None:
            state = self.nmi.state
        if isinstance(u, float):
            return u
        else:
            return state.relative_time * u.loc + (1.0 - state.relative_time) * (
                u.loc + u.scale
            )


class AspiringExpector(Expector):
    """Reduces a utility value by interpolating between its lower and upper
    bounds using an aspiration curve (`PolyAspiration`) instead of a plain
    linear interpolation with relative time.

    This allows expressing different concession profiles (e.g. boulware,
    conceder, linear) for how quickly the estimate moves from optimistic
    (upper bound) towards pessimistic (lower bound) as the negotiation
    progresses.
    """

    def __init__(
        self,
        nmi: NegotiatorMechanismInterface | None = None,
        max_aspiration=1.0,
        aspiration_type: (
            Literal["linear"] | Literal["conceder"] | Literal["boulware"] | float
        ) = "linear",
    ):
        """Creates an aspiration-based expector.

        Args:
            nmi: [Optional] The `NegotiatorMechanismInterface` of the current
                 negotiation, used to get the state when it is not passed
                 explicitly to `__call__`.
            max_aspiration: The aspiration level at the start of the
                            negotiation (relative time 0), between 0 and 1.
            aspiration_type: The shape of the aspiration (concession) curve:
                             `"boulware"` (concedes slowly then fast),
                             `"linear"`, `"conceder"` (concedes fast then
                             slowly), or a numeric exponent.
        """
        Expector.__init__(self, nmi=nmi)
        self.__asp = PolyAspiration(max_aspiration, aspiration_type)

    def utility_at(self, x):
        """Returns the aspiration level (in `[0, 1]`) at relative time `x`.

        Args:
            x: The relative time (between 0 and 1) at which to evaluate the
               aspiration curve.

        Returns:
            The aspiration level at `x`.
        """
        return self.__asp.utility_at(x)

    def is_dependent_on_negotiation_info(self) -> bool:
        """Always `True` since the result depends on relative time.

        Returns:
            `True`.
        """
        return True

    def __call__(self, u: Value, state: MechanismState = None) -> float:
        r"""Computes :math:`\alpha \cdot loc + (1-\alpha) \cdot (loc + scale)`
        where :math:`\alpha` is the aspiration level at `state.relative_time`
        (or `self.nmi.state` if `state` is `None`).

        Args:
            u: The utility value to reduce.
            state: [Optional] The current mechanism state. If `None`, uses
                   `self.nmi.state`.

        Returns:
            The aspiration-weighted utility estimate (`u` itself if it is
            already a `float`).
        """
        if state is None:
            state = self.nmi.state
        if isinstance(u, float):
            return u
        else:
            alpha = self.__asp.utility_at(state.relative_time)
            return alpha * u.loc + (1.0 - alpha) * (u.loc + u.scale)
