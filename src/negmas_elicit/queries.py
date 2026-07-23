"""Preference elicitation."""

from __future__ import annotations

import copy
import operator
import pprint
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from negmas.common import NegotiatorMechanismInterface, Value
from negmas.helpers.prob import UNIFORM, ScipyDistribution
from negmas.outcomes import Outcome
from negmas.preferences.preferences import Preferences

from negmas_elicit.common import _loc, _upper

if TYPE_CHECKING:
    from negmas_elicit.strategy import EStrategy
    from negmas_elicit.user import User

__all__ = [
    "Constraint",
    "MarginalNeutralConstraint",
    "RankConstraint",
    "ComparisonConstraint",
    "RangeConstraint",
    "Answer",
    "Query",
    "QResponse",
    "next_query",
    "possible_queries",
    "CostEvaluator",
]


class Constraint(ABC):
    """Some constraint on allowable utility values for given outcomes."""

    def __init__(
        self,
        full_range: Sequence[tuple[float, float]] | tuple[float, float] = (0.0, 1.0),
        outcomes: list[Outcome] = None,
    ):
        """Creates a constraint.

        Args:
            full_range: The full (prior) range of possible utility values,
                        either a single `(min, max)` tuple applied to every
                        outcome, or a sequence of `(min, max)` tuples (one
                        per outcome) when `outcomes` is given.
            outcomes: [Optional] The list of outcomes this constraint applies
                      to. If given, `full_range` may be a sequence matching
                      it in length.
        """
        super().__init__()
        self.outcomes = outcomes
        self.index = None
        if outcomes is not None:
            self.index = dict(zip(outcomes, range(len(outcomes))))
            if not isinstance(full_range, tuple):
                full_range = [full_range] * len(outcomes)
        self.full_range = full_range

    @abstractmethod
    def is_satisfied(
        self, preferences: Preferences, outcomes: Iterable[Outcome] | None = None
    ) -> bool:
        """
        Whether or not the constraint is satisfied.
        """

    @abstractmethod
    def marginals(self, outcomes: Iterable[Outcome] = None) -> list[ScipyDistribution]:
        """Returns the marginal (uniform) distribution implied by this
        constraint for each of the given outcomes, ignoring any correlations
        between outcomes induced by the constraint.

        Args:
            outcomes: The outcomes to get marginals for. If `None`, uses
                      `self.outcomes`.

        Returns:
            A list of `ScipyDistribution` (one per outcome).
        """
        ...

    @abstractmethod
    def marginal(self, outcome: Outcome) -> ScipyDistribution:
        """Returns the marginal (uniform) distribution implied by this
        constraint for the given outcome alone.

        Args:
            outcome: The outcome to get the marginal distribution for.

        Returns:
            A `ScipyDistribution` describing the allowed utility range for
            `outcome` under this constraint.
        """
        ...

    def __repr__(self):
        """Returns a `dict`-style representation of this constraint's fields."""
        return self.__dict__.__repr__()

    def __str__(self):
        """Returns a pretty-printed representation of this constraint's fields."""
        return pprint.pformat(self.__dict__)


class MarginalNeutralConstraint(Constraint):
    """Constraints that do not affect the marginals of any outcomes. These constraints may only affect the joint
    distribution."""

    def marginals(self, outcomes: Iterable[Outcome] = None) -> list[ScipyDistribution]:
        """Returns the unaffected marginal (uniform over `full_range`)
        distribution for each of the given outcomes since this constraint
        type never restricts individual outcomes' marginals.

        Args:
            outcomes: The outcomes to get marginals for. If `None`, uses
                      `self.outcomes`.

        Returns:
            A list of `ScipyDistribution` (uniform over `full_range`), one
            per outcome.
        """
        if outcomes is None:
            outcomes = self.outcomes
        # this works only for real-valued outcomes.
        return [
            ScipyDistribution(
                type=UNIFORM,
                loc=self.full_range[_][0],
                scale=self.full_range[_][1] - self.full_range[_][0],
            )
            for _ in range(len(outcomes))
        ]

    def marginal(self, outcome: Outcome) -> ScipyDistribution:
        # this works only for real-valued outcomes.
        """Returns the unaffected marginal (uniform over `full_range`)
        distribution for the given outcome since this constraint type never
        restricts individual outcomes' marginals.

        Args:
            outcome: The outcome to get the marginal distribution for.

        Returns:
            A `ScipyDistribution` uniform over `full_range`.
        """
        if self.outcomes is None:
            return ScipyDistribution(
                type=UNIFORM,
                loc=self.full_range[0],
                scale=self.full_range[1] - self.full_range[0],
            )
        indx = self.index[outcome]
        return ScipyDistribution(
            type=UNIFORM,
            loc=self.full_range[indx][0],
            scale=self.full_range[indx][1] - self.full_range[indx][0],
        )


class RankConstraint(MarginalNeutralConstraint):
    """Constraints the utilities of given outcomes to be in ascending order"""

    def __init__(
        self,
        rankings: list[int],
        full_range: Sequence[tuple[float, float]] | tuple[float, float] = (0.0, 1.0),
        outcomes: list[Outcome] = None,
    ):
        """Creates a rank constraint.

        Args:
            rankings: The expected ascending ranking of the outcomes, given
                      as a sorted list of `(utility, index)` pairs (the same
                      format `is_satisfied` builds internally to compare
                      against).
            full_range: The full (prior) range of possible utility values.
            outcomes: [Optional] The list of outcomes this constraint applies
                      to.
        """
        super().__init__(full_range=full_range, outcomes=outcomes)
        self.rankings = rankings

    def is_satisfied(
        self, preferences: Preferences, outcomes: Iterable[Outcome] | None = None
    ) -> bool:
        """Checks whether ranking `outcomes` by `preferences` (ascending
        utility) matches the expected `self.rankings`.

        Args:
            preferences: The utility function to evaluate outcomes with.
            outcomes: The outcomes to rank. If `None`, uses `self.outcomes`.

        Returns:
            `True` if the ascending ranking of `outcomes` by `preferences`
            equals `self.rankings`.
        """
        if outcomes is None:
            outcomes = self.outcomes
        if outcomes is None:
            raise ValueError("No outcomes are  given in construction or to the call")
        u = [(preferences(o), i) for i, o in enumerate(outcomes)]
        ranking = sorted(u, key=lambda x: x[0])
        return ranking == self.rankings


class ComparisonConstraint(MarginalNeutralConstraint):
    """Constraints the utility of given two outcomes (must be exactly two) to satisfy the given operation (e.g. >, <)"""

    def __init__(
        self,
        op: str | Callable[[Value, Value], bool],
        full_range: Sequence[tuple[float, float]] | tuple[float, float] = (0.0, 1.0),
        outcomes: list[Outcome] = None,
    ):
        """Creates a comparison constraint between exactly two outcomes.

        Args:
            op: The comparison operation to check between the utilities of
                the two outcomes. Either a `Callable(u1, u2) -> bool` or one
                of the strings `"less"`/`"l"`/`"<"`, `"greater"`/`"g"`/`">"`,
                `"equal"`/`"="`/`"=="`, `"le"`/`"<="`, `"ge"`/`">="`.
            full_range: The full (prior) range of possible utility values.
            outcomes: [Optional] The two outcomes to compare. Must have
                      length 2 if given.
        """
        super().__init__(full_range=full_range, outcomes=outcomes)
        if outcomes is not None and len(outcomes) != 2:
            raise ValueError(
                f"{len(outcomes)} outcomes were given to {self.__class__.__name__}"
            )
        self.op_name = op
        if isinstance(op, str):
            if op in ("less", "l", "<"):
                op = operator.lt
            elif op in ("greater", "g", ">"):
                op = operator.gt
            elif op in ("equal", "=", "=="):
                op = operator.eq
            elif op in ("le", "<="):
                op = operator.le
            elif op in ("ge", ">="):
                op = operator.ge
            else:
                raise ValueError(f"Unknown operation {op}")
        self.op = op

    def is_satisfied(
        self, preferences: Preferences, outcomes: Iterable[Outcome] | None = None
    ) -> bool:
        """Checks whether `self.op(u(outcomes[0]), u(outcomes[1]))` holds
        for the given `preferences`.

        Args:
            preferences: The utility function to evaluate outcomes with.
            outcomes: The two outcomes to compare. If `None`, uses
                      `self.outcomes`. Must have length 2.

        Returns:
            `True` if the comparison operation is satisfied.
        """
        if outcomes is None:
            outcomes = self.outcomes
        if outcomes is None:
            raise ValueError("No outcomes are  given in construction or to the call")
        if len(outcomes) != 2:
            raise ValueError(
                f"{len(outcomes)} outcomes were given to {self.__class__.__name__}"
            )
        u = [(preferences(o), i) for i, o in enumerate(outcomes)]
        return self.op(u[0], u[1])

    def __str__(self):
        """Returns a human readable `outcome1 op outcome2` representation."""
        return f"{self.outcomes[0]} {self.op_name} {self.outcomes[0]}"

    __repr__ = __str__


class RangeConstraint(Constraint):
    """Constraints the utility of each of the given outcomes to lie within the given range"""

    def __init__(
        self,
        rng: tuple = (None, None),
        full_range: Sequence[tuple[float, float]] | tuple[float, float] = (0.0, 1.0),
        outcomes: list[Outcome] = None,
        eps=1e-5,
    ):
        """Creates a range constraint.

        Args:
            rng: The allowed `(min, max)` utility range (either value may be
                 `None` meaning unbounded on that side, falling back to
                 `full_range`), or a sequence of such tuples (one per
                 outcome) when `outcomes` is given.
            full_range: The full (prior) range of possible utility values,
                        used to fill in `None` bounds in `rng`.
            outcomes: [Optional] The list of outcomes this constraint applies
                      to.
            eps: A small tolerance added when checking whether a utility
                 value lies within the allowed range.
        """
        super().__init__(full_range=full_range, outcomes=outcomes)

        if outcomes is not None:
            self.index = dict(zip(outcomes, range(len(outcomes))))
            if not isinstance(rng, tuple):
                rng = [rng] * len(outcomes)
        self.range = rng
        self.eps = eps
        if outcomes is None:
            self.effective_range = (
                rng[0] if rng[0] is not None else self.full_range[0],
                rng[1] if rng[1] is not None else self.full_range[1],
            )
        else:
            self.effective_range = [
                (r[0] if r[0] is not None else f[0], r[1] if r[1] is not None else f[1])
                for r, f in zip(self.range, self.full_range)
            ]

    def is_satisfied(
        self, preferences: Preferences, outcomes: Iterable[Outcome] | None = None
    ) -> bool:
        """Checks that the utility (from `preferences`) of every one of
        `outcomes` lies within `self.range` (within `eps` tolerance).

        Args:
            preferences: The utility function to evaluate outcomes with.
            outcomes: The outcomes to check. If `None`, uses `self.outcomes`.

        Returns:
            `True` if all outcomes have utility within `[range[0] - eps,
            range[1] + eps]`.
        """
        if outcomes is None:
            outcomes = self.outcomes
        if outcomes is None:
            raise ValueError("No outcomes are  given in construction or to the call")
        us = [preferences(o) for o in outcomes]
        mn, mx = self.range
        if mn is not None:
            for u in us:
                if u < mn - self.eps:
                    return False
        if mx is not None:
            for u in us:
                if u > mx + self.eps:
                    return False
        return True

    def marginals(self, outcomes: Iterable[Outcome] = None) -> list[ScipyDistribution]:
        """Returns the marginal distribution (uniform over `effective_range`,
        i.e. `range` with any `None` bound filled in from `full_range`) for
        each of the given outcomes.

        Args:
            outcomes: The outcomes to get marginals for. If `None`, uses
                      `self.outcomes`.

        Returns:
            A list of `ScipyDistribution`, one per outcome.
        """
        if outcomes is None:
            outcomes = self.outcomes
        # this works only for real-valued outcomes.
        return [
            ScipyDistribution(
                type=UNIFORM,
                loc=self.effective_range[_][0],
                scale=self.effective_range[_][1] - self.effective_range[_][0],
            )
            for _ in range(len(outcomes))
        ]

    def marginal(self, outcome: Outcome) -> ScipyDistribution:
        # this works only for real-valued outcomes.
        """Returns the marginal distribution (uniform over `effective_range`)
        for the given outcome.

        Args:
            outcome: The outcome to get the marginal distribution for.

        Returns:
            A `ScipyDistribution` uniform over the effective range for this
            outcome.
        """
        if self.outcomes is None:
            return ScipyDistribution(
                type=UNIFORM,
                loc=self.effective_range[0],
                scale=self.effective_range[1] - self.effective_range[0],
            )
        indx = self.index[outcome]
        return ScipyDistribution(
            type=UNIFORM,
            loc=self.effective_range[indx][0],
            scale=self.effective_range[indx][1] - self.effective_range[indx][0],
        )

    def __str__(self):
        """Returns a human readable `range` (and `outcomes` if any) representation."""
        result = f"{self.range}"
        if self.outcomes is not None and len(self.outcomes) > 0:
            result += f"{self.outcomes}"
        return result

    __repr__ = __str__


@dataclass
class Answer:
    """One possible answer to a `Query`.

    Attributes:
        outcomes: The outcomes this answer's `constraint` applies to.
        constraint: The `Constraint` that must be satisfied by the user's
                    true utility function for this answer to be the correct
                    (selected) one.
        cost: An additional cost incurred specifically for getting this
              answer (on top of the query's own `cost`).
        name: A human readable name for this answer (e.g. `"yes"`/`"no"`).
    """

    outcomes: list[Outcome]
    constraint: Constraint
    cost: float = 0.0
    name: str = ""

    def __str__(self):
        """Returns a human readable representation of the answer (its name
        or its constraint/cost/outcomes)."""
        if len(self.name) > 0:
            return self.name + f"{self.constraint}"
        else:
            output = f"{self.constraint}"
            if self.cost > 1e-7:
                output += f"(cost:{self.cost})"
            if len(self.outcomes) > 0:
                output += f"(outcomes:{self.outcomes})"
            return output

    __repr__ = __str__


@dataclass
class Query:
    """A question that can be asked to a `User`, with its set of possible
    `Answer`s.

    The user's `ask` method checks each of `answers`'s constraints in order
    against the true utility function and returns the first one satisfied.

    Attributes:
        answers: The list of possible `Answer`s to this query.
        probs: The prior probability of each answer being the correct one
               (same length/order as `answers`), used to estimate the
               expected value of asking this query before it is actually
               asked.
        cost: The cost of asking this query (independent of the answer
              received).
        name: A human readable name for this query.
    """

    answers: list[Answer]
    probs: list[float]
    cost: float = 0.0
    name: str = ""

    def __str__(self):
        """Returns a human readable representation of the query (its name,
        or its answers and cost if not zero)."""
        if len(self.name) > 0:
            return self.name
        else:
            if self.cost < 1e-7:
                return f"answers: {self.answers}"
            else:
                return f"answers: {self.answers} (cost:{self.cost})"

    __repr__ = __str__


@dataclass
class QResponse:
    """The response to a `Query` asked of a `User`.

    Attributes:
        answer: The selected `Answer` (whose constraint was satisfied by the
                true utility function), or `None` if no answer was found to
                be satisfied (the query failed) or the query itself was `None`.
        indx: The index of `answer` within the original query's `answers`
              list (`-1` if `answer` is `None`).
        cost: The total cost incurred for asking the query and getting this
              answer.
    """

    answer: Answer | None
    indx: int
    cost: float


def possible_queries(
    nmi: NegotiatorMechanismInterface,
    strategy: EStrategy,
    user: User,
    outcome: Outcome = None,
) -> list[tuple[Outcome, list[ScipyDistribution], float]]:
    """Simulates applying `strategy` to `outcome` repeatedly (on deep copies of
    `user` and `strategy` so no real elicitation/cost is incurred) until an
    exact utility value is found, and returns every query that would be asked
    along the way together with its (incremental) cost.

    Args:
        nmi: The `NegotiatorMechanismInterface` of the negotiation (used to
             get the outcomes if `outcome` is `None`).
        strategy: The `EStrategy` to simulate (deep-copied before use).
        user: The `User` to simulate asking (deep-copied before use).
        outcome: The single outcome to compute possible queries for. If
                 `None`, computes them for every outcome in `nmi`.

    Returns:
        A list of `(outcome, query, cost)` tuples, one for each query that
        would be asked while narrowing down the outcome's utility to an
        exact value.
    """
    user = copy.deepcopy(user)
    strategy = copy.deepcopy(strategy)

    def _possible_queries(outcome, strategy=strategy, nmi=nmi):
        queries_before = user.elicited_queries()
        utility_before = strategy.utility_estimate(outcome)
        _lower_before, _upper_before = _loc(utility_before), _upper(utility_before)
        n_before = len(queries_before)
        while True:
            u, _ = strategy.apply(user=user, outcome=outcome)
            if isinstance(u, float):
                break
        _qs = user.elicited_queries()[n_before:]

        # update costs
        s = 0.0
        qs = []
        for i, q in enumerate(_qs):
            qs.append((outcome, q.query, q.cost + s - user.cost))
            s += q.cost

        # # add possible other answers
        # for old_indx, _ in enumerate(qs):
        #     if strategy.strategy == 'exact':
        #         qs[old_indx] = (_[0], [_[1]], _[3], _[4], _[5])
        #         continue
        #     others = []
        #     if (_[1] - lower_before) > epsilon:
        #         others.append(ScipyDistribution(type='uniform', loc=lower_before, scale=_[1] - lower_before))
        #     others.append(ScipyDistribution(type='uniform', loc=_[1], scale=_[2]) if _[2] > 0 else _[1])
        #     end = (_[1] + _[2])
        #     if (upper_before - end) > epsilon:
        #         others.append(ScipyDistribution(type='uniform', loc=end, scale=upper_before - end))
        #     qs[old_indx] = (_[0], others, _[3], _[4], _[5])
        return qs

    if outcome is None:
        queries = []
        for outcome in nmi.outcomes:
            queries += _possible_queries(outcome)
    else:
        queries = _possible_queries(outcome)
    return queries


def next_query(
    strategy: EStrategy, user: User, outcome: Outcome = None
) -> list[tuple[Outcome, Query, float]]:
    """Gets the immediate next query (without simulating further ahead) for
    one or all outcomes, together with the cost of asking it.

    Args:
        strategy: The `EStrategy` used to compute the next query for an
                  outcome.
        user: The `User` who would be asked (used only to get the cost of
              asking, no question is actually asked).
        outcome: The single outcome to compute the next query for. If
                 `None`, computes it for every outcome known to `strategy`.

    Returns:
        A list of `(outcome, query, cost)` tuples, one per outcome
        considered.
    """

    def _next_query(outcome, strategy=strategy):
        return outcome, strategy.next_query(outcome), user.cost_of_asking()

    if outcome is None:
        queries = []
        for outcome in strategy.outcomes:
            queries.append(_next_query(outcome))
    else:
        queries = [_next_query(outcome)]
    return queries


class CostEvaluator:
    """Computes the total cost of asking a `Query` and getting a particular
    `Answer`.

    The total cost is the sum of a fixed per-question `cost` (e.g. the
    `User`'s base cost), the query's own `cost`, and the specific answer's
    `cost` (if any).
    """

    def __init__(self, cost: float):
        """Creates a cost evaluator with a fixed per-question cost.

        Args:
            cost: The fixed cost incurred for asking any question (e.g. the
                  `User`'s base cost).
        """
        self.cost = cost

    def __call__(self, query: Query, answer: Answer):
        """Computes `self.cost + query.cost + answer.cost`.

        Args:
            query: The query that was asked.
            answer: The answer that was received.

        Returns:
            The total cost of asking `query` and getting `answer`.
        """
        return self.cost + query.cost + (answer.cost if answer.cost else 0.0)
