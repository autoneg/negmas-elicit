"""End-to-end elicitation tests.

Ported and modernized from the original ``negmas`` elicitation test-suite
(``disabled_test_elicitors.pp``) so that the full elicitation stack — strategies,
users, queries, every elicitor type and the eliciting mechanism — is exercised
against the current ``negmas`` API.

The numerical assertions on the elicitation strategies (bisection halving the
uncertainty, titration moving the bounds by a fixed step, ...) are the real
correctness guards and are preserved verbatim from the original suite.
"""

from __future__ import annotations

import os

import numpy as np
import pytest
from negmas import MappingUtilityFunction
from negmas.helpers import instantiate
from negmas.inout import load_genius_domain_from_folder
from negmas.preferences import IPUtilityFunction, pareto_frontier
from negmas.sao import AspirationNegotiator, LimitedOutcomesNegotiator, SAOMechanism

import negmas_elicit as elicitation
from negmas_elicit import (
    DummyElicitor,
    EStrategy,
    FullKnowledgeElicitor,
    PandoraElicitor,
    SAOElicitingMechanism,
    User,
    next_query,
    possible_queries,
)

N_OUTCOMES = 5
COST = 0.02
UTILITY = 0.17682

# Every non-abstract elicitor exposed by the package (used to check they all run).
ALL_ELICITOR_TYPES = [
    name
    for name in elicitation.__all__
    if name.endswith("Elicitor")
    and not name.startswith("Base")
    and "VOIOptimal" not in name
]


def _ufun():
    return MappingUtilityFunction(
        dict(zip([(_,) for _ in range(N_OUTCOMES)], [UTILITY] * N_OUTCOMES)),
        reserved_value=0.0,
    )


@pytest.fixture
def neg() -> SAOMechanism:
    return SAOMechanism(outcomes=[(_,) for _ in range(N_OUTCOMES)])


@pytest.fixture
def user() -> User:
    return User(preferences=_ufun(), cost=COST)


@pytest.fixture
def true_utilities():
    return list(np.random.rand(N_OUTCOMES).tolist())


@pytest.fixture
def data_folder():
    import negmas

    return os.path.join(os.path.dirname(negmas.__file__), "tests", "data")


def u0(neg: SAOMechanism, reserved_value=0.0):
    return IPUtilityFunction(outcomes=neg.outcomes, reserved_value=reserved_value)


# --------------------------------------------------------------------------- #
# User + elicitation strategies                                               #
# --------------------------------------------------------------------------- #
class TestUserAndStrategies:
    def test_user_initializable(self, user):
        assert user.total_cost == 0.0

    def test_user_can_read_true_utilities(self, user):
        true_utils = list(user.ufun.mapping.values())
        assert len(true_utils) == N_OUTCOMES
        assert user.total_cost == 0.0
        assert user.ufun((0,)) == UTILITY
        assert user.cost_of_asking() == COST

    def test_elicit_exact(self, neg, user):
        strategy = EStrategy(strategy="exact")
        strategy.on_enter(nmi=neg.shared_nmi)
        u, _ = strategy.apply(user=user, outcome=(0,))
        assert isinstance(u, float)
        assert u == UTILITY

    def test_elicit_bisection(self, neg, user):
        strategy = EStrategy(strategy="bisection", resolution=1e-4)
        strategy.on_enter(neg.shared_nmi)
        elicited, estimated = [], []
        while True:
            e = strategy.utility_estimate((0,))
            u, _ = strategy.apply(user=user, outcome=(0,))
            if isinstance(u, float) or u.scale < COST:
                assert abs(u - UTILITY) < 1e-2
                break
            elicited.append(u)
            estimated.append(e)
        assert elicited[0].loc == 0.0
        assert elicited[0].scale == 0.5
        assert estimated[0].loc == 0.0
        assert estimated[0].scale == 1.0
        # uncertainty halves at every bisection step
        for u, e in zip(elicited, estimated):
            assert u.scale == 0.5 * e.scale
        for i in range(len(elicited) - 1):
            assert elicited[i + 1].scale == 0.5 * elicited[i].scale

    def test_elicit_titration_up(self, neg, user):
        step = 0.05
        strategy = EStrategy(strategy=f"titration+{step}", resolution=1e-4)
        strategy.on_enter(neg.shared_nmi)
        elicited, estimated = [], []
        total_cost = 0.0
        while True:
            e = strategy.utility_estimate((0,))
            assert user.total_cost == total_cost
            u, _ = strategy.apply(user=user, outcome=(0,))
            if isinstance(u, float) or u.scale < COST:
                assert abs(u - UTILITY) < step * 2
                break
            total_cost += COST
            elicited.append(u)
            estimated.append(e)
        assert elicited[0].loc == step
        assert elicited[0].scale == 1.0 - step

    def test_elicit_titration_down(self, neg, user):
        step = -0.05
        strategy = EStrategy(strategy=f"titration{step}", resolution=1e-4)
        strategy.on_enter(neg.shared_nmi)
        elicited = []
        while True:
            u, _ = strategy.apply(user=user, outcome=(0,))
            if isinstance(u, float) or u.scale < COST:
                assert abs(u - UTILITY) < -step * 2
                break
            elicited.append(u)
        step = -step
        assert elicited[0].loc + elicited[0].scale == 1.0 - step
        assert elicited[0].scale == 1.0 - step

    def test_stops_eliciting_at_cost(self, neg, user):
        strategy = EStrategy(strategy="bisection", resolution=1e-4, stop_at_cost=True)
        strategy.on_enter(neg.shared_nmi)
        estimated = []
        while True:
            e = strategy.utility_estimate((0,))
            u, _ = strategy.apply(user=user, outcome=(0,))
            if isinstance(u, float) or u.scale < COST:
                assert abs(u - UTILITY) < COST
                break
            estimated.append(e)
        assert estimated[-1].scale >= COST

    def test_possible_queries(self, neg):
        for s in (
            "exact",
            "bisection",
            "titration+0.05",
            "titration-0.5",
            "dtitration+0.5",
            "dtitration-0.05",
            "pingpong0.5",
            "dpingpong0.5",
        ):
            user = User(preferences=_ufun(), cost=COST)
            strategy = EStrategy(strategy=s)
            strategy.on_enter(neg.shared_nmi)
            q = possible_queries(nmi=neg.shared_nmi, strategy=strategy, user=user)
            assert (len(q) > 0) == (s != "exact")

    def test_next_query(self, neg):
        for s in ("bisection", "titration+0.05", "dtitration-0.05"):
            strategy = EStrategy(strategy=s)
            user = User(preferences=_ufun(), cost=COST)
            strategy.on_enter(neg.shared_nmi)
            q = next_query(strategy=strategy, user=user)
            assert len(q) > 0


# --------------------------------------------------------------------------- #
# Elicitors inside a negotiation                                              #
# --------------------------------------------------------------------------- #
ACCEPTED = [(0,), (2,)]


class TestElicitorsInNegotiation:
    def _opponent(self):
        return LimitedOutcomesNegotiator(
            acceptable_outcomes=ACCEPTED,
            acceptance_probabilities=[1.0] * len(ACCEPTED),
        )

    def test_dummy(self, true_utilities):
        user = User(
            preferences=MappingUtilityFunction(
                dict(zip([(_,) for _ in range(N_OUTCOMES)], true_utilities)),
                reserved_value=0.0,
            ),
            cost=COST,
        )
        neg = SAOMechanism(outcomes=[(_,) for _ in range(N_OUTCOMES)], n_steps=10)
        elicitor = DummyElicitor(user=user)
        neg.add(self._opponent())
        neg.add(elicitor, preferences=u0(neg))
        neg.run()
        assert len(neg.history) > 0
        assert neg.agreement is None or neg.agreement in ACCEPTED
        assert elicitor.elicitation_cost == 0.0

    def test_full_knowledge(self, true_utilities):
        user = User(
            preferences=MappingUtilityFunction(
                dict(zip([(_,) for _ in range(N_OUTCOMES)], true_utilities)),
                reserved_value=0.0,
            ),
            cost=COST,
        )
        neg = SAOMechanism(outcomes=[(_,) for _ in range(N_OUTCOMES)], n_steps=10)
        elicitor = FullKnowledgeElicitor(user=user)
        neg.add(self._opponent())
        neg.add(elicitor, preferences=u0(neg))
        neg.run()
        assert len(neg.history) > 0
        assert neg.agreement is None or neg.agreement in ACCEPTED
        assert elicitor.elicitation_cost == 0.0

    @pytest.mark.parametrize("elicitor_type", ALL_ELICITOR_TYPES)
    def test_every_elicitor_runs(self, elicitor_type, true_utilities):
        neg = SAOMechanism(outcomes=[(_,) for _ in range(N_OUTCOMES)], n_steps=10)
        user = User(
            preferences=MappingUtilityFunction(
                dict(zip([(_,) for _ in range(N_OUTCOMES)], true_utilities)),
                reserved_value=0.0,
            ),
            cost=COST,
        )
        strategy = EStrategy(strategy="titration-0.05")
        strategy.on_enter(nmi=neg.shared_nmi)
        kwargs = {}
        if "VOI" in elicitor_type:
            kwargs["dynamic_query_set"] = True
        elicitor = instantiate(
            f"negmas_elicit.{elicitor_type}", strategy=strategy, user=user, **kwargs
        )
        neg.add(self._opponent())
        neg.add(elicitor, preferences=u0(neg))
        assert elicitor.elicitation_cost == 0.0
        neg.run()
        assert len(neg.history) > 0
        assert neg.agreement is None or neg.agreement in ACCEPTED


# --------------------------------------------------------------------------- #
# Pareto frontier + genius domains                                            #
# --------------------------------------------------------------------------- #
class TestFrontierAndDomains:
    def test_pareto_frontier(self):
        n_outcomes = 10
        reserved_value = 0.1
        outcomes = [(_,) for _ in range(n_outcomes)]
        accepted = [(2,), (3,), (4,), (5,)]
        elicitor_utilities = list(np.random.rand(n_outcomes).tolist())
        opponent_utilities = [
            1.0 if (_,) in accepted else 0.0 for _ in range(n_outcomes)
        ]
        frontier, frontier_locs = pareto_frontier(
            [
                MappingUtilityFunction(
                    dict(zip(outcomes, elicitor_utilities)),
                    reserved_value=reserved_value,
                ),
                MappingUtilityFunction(
                    dict(zip(outcomes, opponent_utilities)),
                    reserved_value=reserved_value,
                ),
            ],
            outcomes=outcomes,
            sort_by_welfare=True,
        )
        assert len(frontier) > 0

    def test_load_genius_domain(self, data_folder):
        d = (
            load_genius_domain_from_folder(os.path.join(data_folder, "Laptop"))
            .normalize()
            .to_single_issue()
        )
        assert len(d.issues) == 1
        assert len(d.ufuns) == 2

    def test_elicitor_runs_on_genius_domain(self, data_folder):
        d = (
            load_genius_domain_from_folder(os.path.join(data_folder, "Laptop"))
            .normalize()
            .to_single_issue()
        )
        domain = d.make_session(AspirationNegotiator, n_steps=100, time_limit=30)
        domain.add(LimitedOutcomesNegotiator(), preferences=d.ufuns[0])
        user = User(preferences=d.ufuns[0], cost=0.2)
        strategy = EStrategy(strategy="titration-0.5")
        strategy.on_enter(nmi=domain.shared_nmi)
        elicitor = PandoraElicitor(strategy=strategy, user=user)
        domain.add(elicitor)
        domain.run()
        assert len(domain.history) > 0


# --------------------------------------------------------------------------- #
# The eliciting mechanism (config generation + full runs)                     #
# --------------------------------------------------------------------------- #
class TestElicitingMechanism:
    def test_no_conflict_full_knowledge(self):
        config = SAOElicitingMechanism.generate_config(
            cost=0.05,
            n_outcomes=50,
            conflict=0.0,
            winwin=1.0,
            n_steps=100,
            own_reserved_value=0.1,
            opponent_type="tough",
            opponent_model_uncertainty=0.0,
            own_utility_uncertainty=0.0,
        )
        neg = SAOElicitingMechanism(**config, elicitor_type="full_knowledge")
        frontier, _ = neg.pareto_frontier(sort_by_welfare=True)
        assert len(frontier) > 0
        neg.run()
        assert len(neg.history) > 0

    @pytest.mark.parametrize(
        "strategy,dynamic", [("pingpong", False), ("bisection", True)]
    )
    def test_alternating_offers(self, strategy, dynamic):
        config = SAOElicitingMechanism.generate_config(
            cost=0.001,
            n_outcomes=10,
            opponent_type="limited_outcomes",
            conflict=1.0,
            n_steps=500,
            time_limit=100000.0,
            own_utility_uncertainty=0.1,
            own_reserved_value=0.1,
        )
        p = SAOElicitingMechanism(
            **config,
            elicitation_strategy=strategy,
            elicitor_type="balanced",
            dynamic_queries=dynamic,
        )
        p.run()
        assert len(p.history) > 0
        assert p.elicitation_state["elicitation_cost"] >= 0.0
        assert (
            p.elicitation_state["elicitor_utility"] >= p.negotiators[1].reserved_value
        )

    @pytest.mark.parametrize("dynamic", [False, True])
    def test_alternating_offers_voi(self, dynamic):
        config = SAOElicitingMechanism.generate_config(
            cost=0.001,
            n_outcomes=10,
            opponent_type="limited_outcomes",
            conflict=1.0,
            n_steps=500,
            time_limit=100000.0,
            own_utility_uncertainty=0.1,
            own_reserved_value=0.1,
        )
        p = SAOElicitingMechanism(
            **config,
            elicitation_strategy=None,
            elicitor_type="voi",
            dynamic_queries=dynamic,
        )
        p.run()
        assert len(p.history) > 0
        assert p.elicitation_state["elicitation_cost"] >= 0.0

    def test_voi_optimal(self):
        config = SAOElicitingMechanism.generate_config(
            cost=0.001,
            n_outcomes=10,
            opponent_type="limited_outcomes",
            conflict=1.0,
            n_steps=500,
            time_limit=100000.0,
            own_utility_uncertainty=0.5,
            own_reserved_value=0.1,
        )
        p = SAOElicitingMechanism(**config, elicitor_type="voi_optimal")
        p.run()
        assert len(p.history) > 0
        assert p.elicitation_state["elicitation_cost"] >= 0.0
        assert p.elicitation_state["total_voi"] is None or (
            p.elicitation_state["total_voi"] >= 0
        )

    def test_full_knowledge_mechanism(self):
        config = SAOElicitingMechanism.generate_config(
            cost=0.001,
            n_outcomes=10,
            opponent_type="limited_outcomes",
            conflict=1.0,
            n_steps=500,
            time_limit=100000.0,
            own_utility_uncertainty=0.1,
            own_reserved_value=0.1,
        )
        p = SAOElicitingMechanism(
            **config, elicitation_strategy="bisection", elicitor_type="full_knowledge"
        )
        p.run()
        assert len(p.history) > 0
        assert p.elicitation_state["elicitation_cost"] == 0.0

    def test_small_session(self):
        config = SAOElicitingMechanism.generate_config(
            cost=0.2, n_outcomes=5, n_steps=10
        )
        p = SAOElicitingMechanism(**config)
        p.run()
        assert len(p.history) > 0
