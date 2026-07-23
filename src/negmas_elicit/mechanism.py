"""Negotiation mechanism implementations."""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Any

import numpy as np
import pandas as pd
from negmas import warnings
from negmas.genius import GeniusNegotiator
from negmas.helpers import create_loggers, instantiate
from negmas.helpers.prob import UNIFORM, ScipyDistribution
from negmas.inout import load_genius_domain_from_folder
from negmas.mechanisms import Mechanism
from negmas.models.acceptance import UncertainOpponentModel
from negmas.outcomes import Outcome
from negmas.preferences import (
    IPUtilityFunction,
    MappingUtilityFunction,
    UtilityFunction,
)
from negmas.sao import (
    AspirationNegotiator,
    LimitedOutcomesAcceptor,
    LimitedOutcomesNegotiator,
    RandomNegotiator,
    SAOMechanism,
    SAOState,
    TopFractionNegotiator,
    ToughNegotiator,
)

from negmas_elicit.base import BaseElicitor
from negmas_elicit.baseline import DummyElicitor, FullKnowledgeElicitor
from negmas_elicit.expectors import (
    BalancedExpector,
    MaxExpector,
    MeanExpector,
    MinExpector,
)
from negmas_elicit.pandora import FullElicitor, RandomElicitor
from negmas_elicit.queries import Answer, Query, RangeConstraint
from negmas_elicit.strategy import EStrategy
from negmas_elicit.user import User
from negmas_elicit.voi import (
    VOIElicitor,
    VOIFastElicitor,
    VOINoUncertaintyElicitor,
    VOIOptimalElicitor,
)

__all__ = ["SAOElicitingMechanism"]


def uniform():
    """Uniform."""
    loc = random.random()
    scale = random.random() * (1.0 - loc)
    return ScipyDistribution(type=UNIFORM, loc=loc, scale=scale)


def current_aspiration(elicitor, outcome: Outcome, negotiation: Mechanism) -> float:
    """Current aspiration.

    Args:
        elicitor: Elicitor.
        outcome: Outcome to evaluate.
        negotiation: Negotiation.

    Returns:
        float: The result.
    """
    return elicitor.utility_at(negotiation.relative_time)


def create_negotiator(
    negotiator_type, preferences, can_propose, outcomes, toughness, **kwargs
):
    """Create negotiator.

    Args:
        negotiator_type: Negotiator type.
        preferences: Preferences.
        can_propose: Can propose.
        outcomes: Outcomes.
        toughness: Toughness.
        **kwargs: Additional keyword arguments.
    """
    if negotiator_type == "limited_outcomes":
        if can_propose:
            negotiator = LimitedOutcomesNegotiator(
                acceptable_outcomes=outcomes,
                acceptance_probabilities=list(preferences.mapping.values()),
                **kwargs,
            )
        else:
            negotiator = LimitedOutcomesAcceptor(
                acceptable_outcomes=outcomes,
                acceptance_probabilities=list(preferences.mapping.values()),
                **kwargs,
            )
    elif negotiator_type == "random":
        negotiator = RandomNegotiator(can_propose=can_propose)
    elif negotiator_type == "tough":
        negotiator = ToughNegotiator(can_propose=can_propose)
    elif negotiator_type in ("only_best", "best_only", "best"):
        negotiator = TopFractionNegotiator(
            min_utility=None,
            top_fraction=1.0 - toughness,
            best_first=False,
            can_propose=can_propose,
        )
    elif negotiator_type.startswith("aspiration"):
        asp_kind = negotiator_type[len("aspiration") :]
        if asp_kind.startswith("_"):
            asp_kind = asp_kind[1:]
        try:
            asp_kind = float(asp_kind)
        except Exception:
            pass
        if asp_kind == "":
            if toughness < 0.5:
                toughness *= 2
                toughness = 9.0 * toughness + 1.0
            elif toughness == 0.5:
                toughness = 1.0
            else:
                toughness = 2 * (toughness - 0.5)
                toughness = 1 - 0.9 * toughness
            asp_kind = toughness
        # AspirationNegotiator no longer accepts ``can_propose``; it always
        # proposes.  Opponents in the elicitation experiments always propose,
        # so dropping the flag matches the intended behaviour.
        negotiator = AspirationNegotiator(aspiration_type=asp_kind, **kwargs)
    elif negotiator_type.startswith("genius"):
        class_name = negotiator_type[len("genius") :]
        if class_name.startswith("_"):
            class_name = class_name[1:]
        if class_name == "auto" or len(class_name) < 1:
            negotiator = GeniusNegotiator.random_negotiator()
        else:
            negotiator = GeniusNegotiator(java_class_name=class_name)
        negotiator.preferences = preferences
    else:
        raise ValueError(f"Unknown opponents type {negotiator_type}")
    return negotiator


def _beg(x):
    if isinstance(x, float):
        return x
    else:
        return x.loc


def _scale(x):
    if isinstance(x, float):
        return 0.0
    else:
        return x.scale


def _end(x):
    if isinstance(x, float):
        return x
    else:
        return x.loc + x.scale


class SAOElicitingMechanism(SAOMechanism):
    """An `SAOMechanism` (alternating-offers negotiation) set up to run a
    single elicitor against a single opponent negotiator.

    This is a convenience wrapper that, given the elicitor's true utility
    function and cost, the opponent's utility function, and the desired
    elicitor type/strategy, builds a `User`, an (optional) `EStrategy` and
    the requested elicitor (baseline, Pandora's box or VOI based), then adds
    both the elicitor and the opponent to the mechanism so the negotiation
    can be `run` (or stepped through with `step`) directly. It also tracks
    elicitation-specific statistics (`elicitation_state`) that are updated at
    the start and end of the negotiation and exposes helper logging methods
    and a `plot` method for visualizing the negotiation/elicitation history.

    Use `generate_config` to build a random or Genius-domain-based
    configuration `dict` that can be passed (as `**kwargs`) to `__init__`.
    """

    def __init__(
        self,
        priors,
        true_utilities,
        elicitor_reserved_value,
        cost,
        opp_utility,
        opponent,
        n_steps,
        time_limit,
        base_agent,
        opponent_model,
        elicitation_strategy="pingpong",
        toughness=0.95,
        elicitor_type="balanced",
        history_file_name: str = None,
        screen_log: bool = False,
        dynamic_queries=True,
        each_outcome_once=False,
        rational_answer_probs=True,
        update_related_queries=True,
        resolution=0.1,
        cost_assuming_titration=False,
        name: str | None = None,
    ):
        """Creates the mechanism, the elicitor (of the requested `elicitor_type`)
        and the `User` wrapping the elicitor's true utility function, then adds
        both the elicitor and `opponent` as negotiators.

        Args:
            priors: The elicitor's initial (uncertain) utility function
                    (an `IPUtilityFunction` giving a distribution per outcome).
            true_utilities: The elicitor's real (hidden) utility values, one
                            per outcome in the same order as `priors`'s outcomes.
            cost: The cost of asking the user (elicitor) a single question.
            elicitor_reserved_value: The elicitor's real reserved value (defaults
                                     to 0.0 if `None`).
            opp_utility: The opponent's utility function.
            opponent: The opponent negotiator to add to the mechanism.
            n_steps: Maximum number of negotiation rounds (steps), or `None`.
            time_limit: Maximum real time for the negotiation, or `None`.
            base_agent: The type of negotiator to use as the elicitor's
                        `base_negotiator` (see `create_negotiator`), e.g.
                        `"aspiration"`.
            opponent_model: The opponent (acceptance) model to use for the
                            elicitor.
            elicitation_strategy: The name of the `EStrategy` to use for deep
                                  elicitation (e.g. `"pingpong"`, `"bisection"`).
                                  Ignored if `elicitor_type` requests a VOI
                                  optimal elicitor (which generates its own
                                  continuous queries).
            toughness: Toughness of the base negotiator used by the elicitor.
            elicitor_type: Which elicitor algorithm to use. Recognized values
                           include `"full"`, `"dummy"`, `"full_knowledge"`,
                           `"random_deep"`, `"random_shallow"`/`"random"`,
                           `"pessimistic"`, `"optimistic"`, `"balanced"`,
                           `"pandora"`, `"fast"`, `"mean"`, and any name
                           containing `"voi"` (optionally combined with
                           `"fast"`, `"optimal"`, `"no_uncertainty"`/
                           `"full_knowledge"`, `"balanced"`, `"optimistic"`/
                           `"max"`, `"pessimistic"`/`"min"`).
            history_file_name: [Optional] File to write negotiation logs to.
            screen_log: If `True`, also logs to the screen (at DEBUG level);
                        otherwise only ERROR-level logs go to the screen.
            dynamic_queries: If `True` and using a VOI elicitor (other than
                             the optimal one), queries are generated on the
                             fly from `elicitation_strategy` instead of being
                             precompiled from a fixed set of thresholds.
            each_outcome_once: If `True`, each outcome may only be offered
                               once by the elicitor.
            rational_answer_probs: If `True` (and using precompiled VOI
                                   queries), answer probabilities are set
                                   proportionally to the query threshold
                                   instead of assumed equal (0.5/0.5).
            update_related_queries: If `True`, queries related to one that
                                    was asked/answered get updated based on
                                    the answer (VOI elicitors only).
            resolution: The smallest uncertainty range/step considered
                        during elicitation. If `None`, it is set to
                        `max(elicitor_reserved_value / 4, 0.025)`.
            cost_assuming_titration: If `True` (and using precompiled VOI
                                     queries), the cost of each precompiled
                                     query is scaled by how far it is from
                                     the ends of the threshold range,
                                     simulating the cost of reaching it via
                                     titration.
            name: [Optional] A name for this mechanism/negotiation.
        """
        self.elicitation_state = {}
        initial_priors = priors
        self.xw_real = priors

        outcomes = list(initial_priors.distributions.keys())

        self.U = true_utilities

        super().__init__(
            issues=None,
            outcomes=outcomes,
            n_steps=n_steps,
            time_limit=time_limit,
            max_n_negotiators=2,
            dynamic_entry=False,
            name=name,
            extra_callbacks=True,
        )
        if elicitor_reserved_value is None:
            elicitor_reserved_value = 0.0
        # Recent negmas builds a ``ContiguousIssue`` outcome-space for integer
        # outcomes while utility functions built from a mapping infer a
        # ``CategoricalIssue``.  The two enumerate the same outcomes but fail
        # the outcome-space containment check performed by ``Mechanism.add``.
        # Align every utility function with the mechanism's own outcome-space.
        for _pref in (initial_priors, opp_utility):
            if _pref is not None:
                _pref.outcome_space = self.outcome_space
        self.logger = create_loggers(
            file_name=history_file_name,
            screen_level=logging.DEBUG if screen_log else logging.ERROR,
        )
        user = User(
            preferences=MappingUtilityFunction(
                dict(zip(self.outcomes, self.U)),
                reserved_value=elicitor_reserved_value,
                outcome_space=self.outcome_space,
            ),
            cost=cost,
            nmi=self.shared_nmi,
        )
        if resolution is None:
            resolution = max(elicitor_reserved_value / 4, 0.025)
        if "voi" in elicitor_type and "optimal" in elicitor_type:
            strategy = None
        else:
            strategy = EStrategy(strategy=elicitation_strategy, resolution=resolution)
            strategy.on_enter(nmi=self.shared_nmi, preferences=initial_priors)

        def create_elicitor(type_, strategy=strategy, opponent_model=opponent_model):
            """Create elicitor.

            Args:
                type_: Type .
                strategy: Strategy.
                opponent_model: Opponent model.
            """
            base_negotiator = create_negotiator(
                negotiator_type=base_agent,
                preferences=None,
                can_propose=True,
                outcomes=outcomes,
                toughness=toughness,
            )
            if type_ == "full":
                return FullElicitor(
                    strategy=strategy, user=user, base_negotiator=base_negotiator
                )

            if type_ == "dummy":
                return DummyElicitor(
                    strategy=strategy, user=user, base_negotiator=base_negotiator
                )

            if type_ == "full_knowledge":
                return FullKnowledgeElicitor(
                    strategy=strategy, user=user, base_negotiator=base_negotiator
                )

            if type_ == "random_deep":
                return RandomElicitor(
                    strategy=strategy,
                    deep_elicitation=True,
                    user=user,
                    base_negotiator=base_negotiator,
                )

            if type_ in ("random_shallow", "random"):
                return RandomElicitor(
                    strategy=strategy,
                    deep_elicitation=False,
                    user=user,
                    base_negotiator=base_negotiator,
                )
            if type_ in (
                "pessimistic",
                "optimistic",
                "balanced",
                "pandora",
                "fast",
                "mean",
            ):
                type_ = type_.title() + "Elicitor"
                return instantiate(
                    f"negmas_elicit.{type_}",
                    strategy=strategy,
                    user=user,
                    base_negotiator=base_negotiator,
                    opponent_model_factory=lambda x: opponent_model,
                    single_elicitation_per_round=False,
                    assume_uniform=True,
                    user_model_in_index=True,
                    precalculated_index=False,
                )
            if "voi" in type_:
                expector_factory = MeanExpector
                if "balanced" in type_:
                    expector_factory = BalancedExpector
                elif "optimistic" in type_ or "max" in type_:
                    expector_factory = MaxExpector
                elif "pessimistic" in type_ or "min" in type_:
                    expector_factory = MinExpector

                if "fast" in type_:
                    factory = VOIFastElicitor
                elif "optimal" in type_:
                    prune = "prune" in type_ or "fast" in type_
                    if "no" in type_:
                        prune = not prune
                    return VOIOptimalElicitor(
                        user=user,
                        resolution=resolution,
                        opponent_model_factory=lambda x: opponent_model,
                        single_elicitation_per_round=False,
                        base_negotiator=base_negotiator,
                        each_outcome_once=each_outcome_once,
                        expector_factory=expector_factory,
                        update_related_queries=update_related_queries,
                        prune=prune,
                    )
                elif "no_uncertainty" in type_ or "full_knowledge" in type_:
                    factory = VOINoUncertaintyElicitor
                else:
                    factory = VOIElicitor

                if not dynamic_queries and "optimal" not in type_:
                    queries = []
                    for outcome in self.outcomes:
                        u = initial_priors(outcome)
                        scale = _scale(u)
                        if scale < resolution:
                            continue
                        bb, ee = _beg(u), _end(u)
                        n_q = int((ee - bb) / resolution)
                        limits = np.linspace(bb, ee, n_q, endpoint=False)[1:]
                        for i, limit in enumerate(limits):
                            if cost_assuming_titration:
                                qcost = cost * min(i, len(limits) - i - 1)
                            else:
                                qcost = cost
                            answers = [
                                Answer(
                                    outcomes=[outcome],
                                    constraint=RangeConstraint(rng=(0.0, limit)),
                                    name="yes",
                                ),
                                Answer(
                                    outcomes=[outcome],
                                    constraint=RangeConstraint(rng=(limit, 1.0)),
                                    name="no",
                                ),
                            ]
                            probs = (
                                [limit, 1.0 - limit]
                                if rational_answer_probs
                                else [0.5, 0.5]
                            )
                            query = Query(
                                answers=answers,
                                cost=qcost,
                                probs=probs,
                                name=f"{outcome}<{limit}",
                            )
                            queries.append((outcome, query, qcost))
                else:
                    queries = None
                return factory(
                    strategy=strategy if dynamic_queries else None,
                    user=user,
                    opponent_model_factory=lambda x: opponent_model,
                    single_elicitation_per_round=False,
                    dynamic_query_set=dynamic_queries,
                    queries=queries,
                    base_negotiator=base_negotiator,
                    each_outcome_once=each_outcome_once,
                    expector_factory=expector_factory,
                    update_related_queries=update_related_queries,
                )

        elicitor = create_elicitor(elicitor_type)

        if isinstance(opponent, GeniusNegotiator):
            if n_steps is not None and time_limit is not None:
                self.shared_nmi.n_steps = None

        self.add(opponent, preferences=opp_utility)
        self.add(elicitor, preferences=initial_priors)
        if len(self.negotiators) != 2:
            raise ValueError(
                f"I could not add the two negotiators {elicitor.__class__.__name__}, {opponent.__class__.__name__}"
            )
        self.total_time = 0.0

    @classmethod
    def generate_config(
        cls,
        cost,
        n_outcomes: int = None,
        rand_preferencess=True,
        conflict: float = None,
        conflict_delta: float = None,
        winwin=None,  # only if rand_preferencess is false
        genius_folder: str = None,
        n_steps=None,
        time_limit=None,
        own_utility_uncertainty=0.5,
        own_uncertainty_variablility=0.0,
        own_reserved_value=0.0,
        own_base_agent="aspiration",
        opponent_model_uncertainty=0.5,
        opponent_model_adaptive=False,
        opponent_proposes=True,
        opponent_type="best_only",
        opponent_toughness=0.9,
        opponent_reserved_value=0.0,
    ) -> dict[str, Any]:
        """Builds a configuration `dict` (suitable to pass as `**kwargs` to
        `__init__`) for a random bilateral negotiation domain, or one loaded
        from a Genius XML domain folder.

        Args:
            cost: The cost of asking the elicitor (user) a single question.
            n_outcomes: Number of outcomes to generate (only used if
                        `genius_folder` is not given).
            rand_preferencess: If `True`, generates fully random bilateral
                               utility functions; otherwise generates them
                               with the given `conflict`/`winwin` levels.
            conflict: [Unused directly here but accepted for API symmetry]
                      target conflict level (see `winwin`/`opponent_toughness`).
            conflict_delta: Allowed deviation from the target conflict level
                            when generating non-random utility functions.
            winwin: Whether to bias generated utility functions towards a
                    win-win outcome (only used if `rand_preferencess` is
                    `False`).
            genius_folder: [Optional] Path to a Genius XML domain folder to
                           load the domain and utility functions from instead
                           of generating them randomly.
            n_steps: Maximum number of negotiation rounds (steps), or `None`.
            time_limit: Maximum real time for the negotiation, or `None`.
            own_utility_uncertainty: The elicitor's uncertainty level (used
                                     to build the `IPUtilityFunction` prior
                                     from the true utility function).
            own_uncertainty_variablility: Variability of the elicitor's
                                          uncertainty across outcomes.
            own_reserved_value: The elicitor's real reserved value.
            own_base_agent: The negotiator type to use as the elicitor's
                            `base_negotiator` (e.g. `"aspiration"`).
            opponent_model_uncertainty: Uncertainty level of the
                                        `UncertainOpponentModel` built for
                                        the elicitor.
            opponent_model_adaptive: If `True`, the opponent model adapts
                                     based on observed opponent behavior.
            opponent_proposes: If `True`, the opponent negotiator can propose
                               (not just accept/reject).
            opponent_type: The type of negotiator to use for the opponent
                           (see `create_negotiator`), e.g. `"best_only"`,
                           `"tough"`, `"random"`, `"aspiration..."`.
            opponent_toughness: Toughness parameter used both for the
                                opponent negotiator and (when generating
                                non-random utilities) as the conflict level.
            opponent_reserved_value: The opponent's real reserved value.

        Returns:
            A `dict` of configuration values (`priors`, `true_utilities`,
            `elicitor_reserved_value`, `cost`, `opp_utility`,
            `opponent_model`, `opponent`, `base_agent`, `n_steps`,
            `time_limit`) ready to be passed to `SAOElicitingMechanism.__init__`.
        """
        config = {}
        if n_steps is None and time_limit is None and "aspiration" in opponent_type:
            raise ValueError(
                "Cannot use aspiration negotiators when no step limit or time limit is given"
            )
        if n_outcomes is None and genius_folder is None:
            raise ValueError(
                "Must specify a folder to run from or a number of outcomes"
            )
        if genius_folder is not None:
            d = load_genius_domain_from_folder(
                genius_folder,
                ignore_reserved=opponent_reserved_value is not None,
                ignore_discount=True,
            ).to_single_issue(numeric=True)
            domain = d.make_session(time_limit=120)

            n_outcomes = domain.shared_nmi.n_outcomes  # type: ignore
            outcomes = domain.outcomes
            elicitor_indx = 0 + int(random.random() <= 0.5)
            opponent_indx = 1 - elicitor_indx
            preferences = d.ufuns[elicitor_indx]
            preferences.reserved_value = own_reserved_value
            opp_utility = d.ufuns[opponent_indx]
            opp_utility.reserved_value = opponent_reserved_value
        else:
            outcomes = [(_,) for _ in range(n_outcomes)]
            if rand_preferencess:
                preferences, opp_utility = UtilityFunction.generate_random_bilateral(
                    outcomes=outcomes
                )
            else:
                preferences, opp_utility = UtilityFunction.generate_bilateral(
                    outcomes=outcomes,
                    conflict_level=opponent_toughness,
                    conflict_delta=conflict_delta,
                    win_win=winwin,
                )
            preferences.reserved_value = own_reserved_value
            domain = SAOMechanism(
                outcomes=outcomes,
                n_steps=n_steps,
                time_limit=time_limit,
                max_n_negotiators=2,
                dynamic_entry=False,
            )

        true_utilities = list(preferences.mapping.values())
        priors = IPUtilityFunction.from_preferences(
            preferences,
            uncertainty=own_utility_uncertainty,
            variability=own_uncertainty_variablility,
        )

        outcomes = domain.shared_nmi.outcomes

        opponent = create_negotiator(
            negotiator_type=opponent_type,
            can_propose=opponent_proposes,
            preferences=opp_utility,
            outcomes=outcomes,
            toughness=opponent_toughness,
        )
        opponent_model = UncertainOpponentModel(
            outcomes=outcomes,
            uncertainty=opponent_model_uncertainty,
            opponents=opponent,
            adaptive=opponent_model_adaptive,
        )
        config["n_steps"], config["time_limit"] = n_steps, time_limit
        config["priors"] = priors
        config["true_utilities"] = true_utilities
        config["elicitor_reserved_value"] = own_reserved_value
        config["cost"] = cost
        config["opp_utility"] = opp_utility
        config["opponent_model"] = opponent_model
        config["opponent"] = opponent
        config["base_agent"] = own_base_agent
        return config

    def loginfo(self, s: str) -> None:
        """logs nmi-level information

        Args:
            s (str): The string to log

        """
        self.logger.info(s.strip())

    def logdebug(self, s) -> None:
        """logs debug-level information

        Args:
            s (str): The string to log

        """
        self.logger.debug(s.strip())

    def logwarning(self, s) -> None:
        """logs warning-level information

        Args:
            s (str): The string to log

        """
        self.logger.warning(s.strip())

    def logerror(self, s) -> None:
        """logs error-level information

        Args:
            s (str): The string to log

        """
        self.logger.error(s.strip())

    def step(self) -> SAOState:
        """Advances the negotiation by one round, timing the call and
        logging the proposer and offer made in this step.

        Returns:
            The `SAOState` after the step (as returned by the parent
            `SAOMechanism.step`).
        """
        start = time.perf_counter()
        _ = super().step()
        self.total_time += time.perf_counter() - start
        state = self.state
        self.loginfo(
            f"[{state.step}] {state.current_proposer} offered {state.current_offer}"
        )
        return _

    def on_negotiation_start(self):
        """On negotiation start."""
        if not super().on_negotiation_start():
            return False
        self.elicitation_state = {}
        self.elicitation_state["steps"] = None
        self.elicitation_state["relative_time"] = None
        self.elicitation_state["broken"] = False
        self.elicitation_state["timedout"] = False
        self.elicitation_state["agreement"] = None
        self.elicitation_state["agreed"] = False
        self.elicitation_state["utils"] = [
            0.0 for a in self.negotiators
        ]  # not even the reserved value
        self.elicitation_state["welfare"] = sum(self.elicitation_state["utils"])
        self.elicitation_state["elicitor"] = self.negotiators[
            1
        ].__class__.__name__.replace("Elicitor", "")
        self.elicitation_state["opponents"] = self.negotiators[
            0
        ].__class__.__name__.replace("Aget", "")
        self.elicitation_state["elicitor_utility"] = self.elicitation_state["utils"][1]
        self.elicitation_state["opponent_utility"] = self.elicitation_state["utils"][0]
        self.elicitation_state["opponent_params"] = str(self.negotiators[0])
        self.elicitation_state["elicitor_params"] = str(self.negotiators[1])
        self.elicitation_state["elicitation_cost"] = None
        self.elicitation_state["total_time"] = None
        self.elicitation_state["pareto"] = None
        self.elicitation_state["pareto_distance"] = None
        self.elicitation_state["_elicitation_time"] = None
        self.elicitation_state["real_asking_time"] = None
        self.elicitation_state["n_queries"] = 0
        return True

    def plot(self, visible_negotiators=(0, 1), consider_costs=False, show: bool = True):
        """Plot.

        Args:
            visible_negotiators: Visible negotiators.
            consider_costs: Consider costs.
            show: Whether to display the figures immediately.

        Returns:
            A tuple of two plotly Figure objects (utility figure, outcome figure).
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            if len(self.negotiators) > 2:
                warnings.warn(
                    "Cannot visualize negotiations with more than 2 negotiators"
                )
                return None, None
            else:
                # has_front = int(len(self.outcomes[0]) <2)
                has_front = True
                n_agents = len(self.negotiators)
                history = pd.DataFrame(data=[_[1] for _ in self.history])
                history["time"] = [_[0].time for _ in self.history]
                history["relative_time"] = [_[0].relative_time for _ in self.history]
                history["step"] = [_[0].step for _ in self.history]
                history = history.loc[~history.offer.isnull(), :]
                # ufuns = self._get_preferencess(consider_costs=consider_costs)
                ufuns = self._get_preferences()
                elicitor_dist = self.negotiators[1].ufun
                outcomes = self.outcomes

                utils = [tuple(f(o) for f in ufuns) for o in outcomes]
                agent_names = [
                    a.__class__.__name__ + ":" + a.name for a in self.negotiators
                ]
                history["offer_index"] = [outcomes.index(_) for _ in history.offer]
                frontier, frontier_outcome = self.pareto_frontier(sort_by_welfare=True)
                frontier_outcome_indices = [outcomes.index(_) for _ in frontier_outcome]

                agent_names_for_legends = [
                    agent_names[a]
                    .split(":")[0]
                    .replace("Negotiator", "")
                    .replace("Elicitor", "")
                    for a in range(n_agents)
                ]
                if agent_names_for_legends[0] == agent_names_for_legends[1]:
                    agent_names_for_legends = [
                        agent_names[a]
                        .split(":")[0]
                        .replace("Negotiator", "")
                        .replace("Elicitor", "")
                        + agent_names[a].split(":")[1]
                        for a in range(n_agents)
                    ]

                # Create utility figure with subplots
                # Column 1: Utility space (spans all rows)
                # Column 2: Individual utility plots per agent
                fig_util = make_subplots(
                    rows=n_agents,
                    cols=2,
                    column_widths=[0.5, 0.5],
                    specs=[
                        [{"rowspan": n_agents}, {}] if i == 0 else [None, {}]
                        for i in range(n_agents)
                    ],
                    subplot_titles=["Utility Space"]
                    + [
                        f"{agent_names_for_legends[a]} Utility" for a in range(n_agents)
                    ],
                )

                # Create outcome figure with subplots
                fig_outcome = make_subplots(
                    rows=n_agents,
                    cols=2,
                    column_widths=[0.5, 0.5],
                    specs=[
                        [{"rowspan": n_agents}, {}] if i == 0 else [None, {}]
                        for i in range(n_agents)
                    ],
                    subplot_titles=["Outcome Space"]
                    + [f"{agent_names_for_legends[a]} Offers" for a in range(n_agents)],
                )

                # Plot utility and outcome over time for each agent (right column)
                for a in range(n_agents):
                    h = history.loc[
                        history.offerer == agent_names[a],
                        ["relative_time", "offer_index", "offer"],
                    ].copy()
                    h["utility"] = h.offer.apply(ufuns[a])

                    # Outcome plot (right column)
                    fig_outcome.add_trace(
                        go.Scatter(
                            x=h["relative_time"],
                            y=h["offer_index"],
                            mode="lines",
                            name=f"{agent_names_for_legends[a]} offers",
                            showlegend=False,
                        ),
                        row=a + 1,
                        col=2,
                    )

                    # Utility plot (right column)
                    fig_util.add_trace(
                        go.Scatter(
                            x=h["relative_time"],
                            y=h["utility"],
                            mode="lines",
                            name=f"{agent_names_for_legends[a]} utility",
                            showlegend=False,
                        ),
                        row=a + 1,
                        col=2,
                    )

                    # Additional elicitor-specific plots
                    h["dist"] = h.offer.apply(elicitor_dist)
                    h["beg"] = h.dist.apply(_beg)
                    h["end"] = h.dist.apply(_end)
                    h["p_acceptance"] = h.offer.apply(
                        self.negotiators[1].opponent_model.probability_of_acceptance
                    )

                    fig_util.add_trace(
                        go.Scatter(
                            x=h["relative_time"],
                            y=h["end"],
                            mode="lines",
                            name="End",
                            line=dict(color="red"),
                            showlegend=False,
                        ),
                        row=a + 1,
                        col=2,
                    )
                    fig_util.add_trace(
                        go.Scatter(
                            x=h["relative_time"],
                            y=h["beg"],
                            mode="lines",
                            name="Beg",
                            line=dict(color="red"),
                            showlegend=False,
                        ),
                        row=a + 1,
                        col=2,
                    )
                    fig_util.add_trace(
                        go.Scatter(
                            x=h["relative_time"],
                            y=h["p_acceptance"],
                            mode="lines",
                            name="P(acceptance)",
                            line=dict(color="green"),
                            showlegend=False,
                        ),
                        row=a + 1,
                        col=2,
                    )

                    fig_util.update_yaxes(
                        range=[-0.1, 1.1], title_text="Utility", row=a + 1, col=2
                    )
                    fig_util.update_xaxes(title_text="Relative Time", row=a + 1, col=2)
                    fig_outcome.update_yaxes(title_text="Offer Index", row=a + 1, col=2)
                    fig_outcome.update_xaxes(
                        title_text="Relative Time", row=a + 1, col=2
                    )

                if has_front:
                    # Diagonal reference line
                    fig_util.add_trace(
                        go.Scatter(
                            x=[0, 1],
                            y=[0, 1],
                            mode="lines",
                            line=dict(color="green", dash="dash"),
                            name="Reference",
                            showlegend=False,
                        ),
                        row=1,
                        col=1,
                    )

                    # All outcomes
                    fig_util.add_trace(
                        go.Scatter(
                            x=[_[0] for _ in utils],
                            y=[_[1] for _ in utils],
                            mode="markers",
                            name="Outcomes",
                            marker=dict(color="yellow", symbol="square", size=8),
                        ),
                        row=1,
                        col=1,
                    )

                    clrs = ["blue", "green"]
                    for a in range(n_agents):
                        h = history.loc[
                            history.offerer == agent_names[a],
                            ["relative_time", "offer_index", "offer"],
                        ].copy()
                        h["u0"] = h.offer.apply(ufuns[0])
                        h["u1"] = h.offer.apply(ufuns[1])

                        fig_util.add_trace(
                            go.Scatter(
                                x=h["u0"],
                                y=h["u1"],
                                mode="markers",
                                name=f"{agent_names_for_legends[a]}",
                                marker=dict(color=clrs[a], size=8),
                            ),
                            row=1,
                            col=1,
                        )

                    steps = sorted(history.step.unique().tolist())
                    aoffers = [[], []]
                    for step in steps[::2]:
                        offrs = []
                        for a in range(n_agents):
                            a_offer = history.loc[
                                (history.offerer == agent_names[a])
                                & ((history.step == step) | (history.step == step + 1)),
                                "offer_index",
                            ]
                            if len(a_offer) > 0:
                                offrs.append(a_offer.values[-1])
                        if len(offrs) == 2:
                            aoffers[0].append(offrs[0])
                            aoffers[1].append(offrs[1])

                    fig_outcome.add_trace(
                        go.Scatter(
                            x=aoffers[0],
                            y=aoffers[1],
                            mode="markers",
                            name="Offers",
                            marker=dict(color=clrs[0], size=8),
                        ),
                        row=1,
                        col=1,
                    )

                    if self.state.agreement is not None:
                        fig_util.add_trace(
                            go.Scatter(
                                x=[ufuns[0](self.state.agreement)],
                                y=[ufuns[1](self.state.agreement)],
                                mode="markers",
                                name="Agreement",
                                marker=dict(color="black", symbol="star", size=14),
                            ),
                            row=1,
                            col=1,
                        )
                        fig_outcome.add_trace(
                            go.Scatter(
                                x=[outcomes.index(self.state.agreement)],
                                y=[outcomes.index(self.state.agreement)],
                                mode="markers",
                                name="Agreement",
                                marker=dict(color="black", symbol="star", size=14),
                            ),
                            row=1,
                            col=1,
                        )

                    # Pareto frontier
                    f1, f2 = [_[0] for _ in frontier], [_[1] for _ in frontier]
                    fig_util.add_trace(
                        go.Scatter(
                            x=f1,
                            y=f2,
                            mode="markers",
                            name="Frontier",
                            marker=dict(color="red", symbol="x", size=10),
                        ),
                        row=1,
                        col=1,
                    )
                    fig_outcome.add_trace(
                        go.Scatter(
                            x=frontier_outcome_indices,
                            y=frontier_outcome_indices,
                            mode="markers",
                            name="Frontier",
                            marker=dict(color="red", symbol="x", size=10),
                        ),
                        row=1,
                        col=1,
                    )

                    fig_util.update_xaxes(
                        title_text=f"{agent_names_for_legends[0]} utility", row=1, col=1
                    )
                    fig_util.update_yaxes(
                        title_text=f"{agent_names_for_legends[1]} utility", row=1, col=1
                    )
                    fig_outcome.update_xaxes(
                        title_text=agent_names_for_legends[0], row=1, col=1
                    )
                    fig_outcome.update_yaxes(
                        title_text=agent_names_for_legends[1], row=1, col=1
                    )

                    if self.agreement is not None:
                        pareto_distance = 1e9
                        cu = (ufuns[0](self.agreement), ufuns[1](self.agreement))
                        for pu in frontier:
                            dist = math.sqrt(
                                (pu[0] - cu[0]) ** 2 + (pu[1] - cu[1]) ** 2
                            )
                            if dist < pareto_distance:
                                pareto_distance = dist
                        fig_util.add_annotation(
                            x=0,
                            y=0.95,
                            xref="x domain",
                            yref="y domain",
                            text=f"Pareto-distance={pareto_distance:5.2f}",
                            showarrow=False,
                            xanchor="left",
                            yanchor="top",
                            row=1,
                            col=1,
                        )

                fig_util.update_layout(
                    title="Elicitation Negotiation - Utility",
                    showlegend=True,
                    height=300 * n_agents,
                )
                fig_outcome.update_layout(
                    title="Elicitation Negotiation - Outcomes",
                    showlegend=True,
                    height=300 * n_agents,
                )

                if show:
                    fig_util.show()
                    fig_outcome.show()
                    return None, None

                return fig_util, fig_outcome
        except Exception:
            return None, None

    def on_negotiation_end(self):
        """On negotiation end."""
        super().on_negotiation_end()
        self.elicitation_state = {}
        self.elicitation_state["steps"] = self._step + 1
        self.elicitation_state["relative_time"] = self.relative_time
        self.elicitation_state["broken"] = self.state.broken
        self.elicitation_state["timedout"] = (
            not self.state.broken and self.state.agreement is None
        )
        self.elicitation_state["agreement"] = self.state.agreement
        self.elicitation_state["agreed"] = (
            self.state.agreement is not None and not self.state.broken
        )

        if self.elicitation_state["agreed"]:
            self.elicitation_state["utils"] = [
                a.user_preferences(self.state.agreement)
                if isinstance(a, BaseElicitor)
                else a.ufun(self.state.agreement)
                for a in self.negotiators
            ]
        else:
            self.elicitation_state["utils"] = [
                a.reserved_value if a.reserved_value is not None else 0.0
                for a in self.negotiators
            ]
        self.elicitation_state["welfare"] = sum(self.elicitation_state["utils"])
        self.elicitation_state["elicitor"] = self.negotiators[
            1
        ].__class__.__name__.replace("Elicitor", "")
        self.elicitation_state["opponents"] = self.negotiators[
            0
        ].__class__.__name__.replace("Aget", "")
        self.elicitation_state["elicitor_utility"] = self.elicitation_state["utils"][1]
        self.elicitation_state["opponent_utility"] = self.elicitation_state["utils"][0]
        self.elicitation_state["opponent_params"] = str(self.negotiators[0])
        self.elicitation_state["elicitor_params"] = str(self.negotiators[1])
        self.elicitation_state["elicitation_cost"] = self.negotiators[
            1
        ].elicitation_cost
        self.elicitation_state["total_time"] = self.total_time
        self.elicitation_state["_elicitation_time"] = self.negotiators[
            1
        ].elicitation_time
        self.elicitation_state["asking_time"] = self.negotiators[1].asking_time
        self.elicitation_state["pareto"], pareto_outcomes = self.pareto_frontier()
        if self.elicitation_state["agreed"]:
            if self.state.agreement in pareto_outcomes:
                min_dist = 0.0
            else:
                min_dist = 1e12
                for p in self.elicitation_state["pareto"]:
                    dist = 0.0
                    for par, real in zip(p, self.elicitation_state["utils"]):
                        dist += (par - real) ** 2
                    dist = math.sqrt(dist)
                    if dist < min_dist:
                        min_dist = dist
            self.elicitation_state["pareto_distance"] = (
                min_dist if min_dist < 1e12 else None
            )
        else:
            self.elicitation_state["pareto_distance"] = None
        try:
            self.elicitation_state["queries"] = [
                str(_) for _ in self.negotiators[1].user.elicited_queries()
            ]
        except Exception:
            self.elicitation_state["queries"] = None
        try:
            self.elicitation_state["n_queries"] = len(
                self.negotiators[1].user.elicited_queries()
            )
        except Exception:
            self.elicitation_state["n_queries"] = None
        if hasattr(self.negotiators[1], "total_voi"):
            self.elicitation_state["total_voi"] = self.negotiators[1].total_voi
        else:
            self.elicitation_state["total_voi"] = None
