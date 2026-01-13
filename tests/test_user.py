"""Tests for User class and basic elicitation functionality."""

from __future__ import annotations

import pytest
from negmas import MappingUtilityFunction
from negmas.outcomes import enumerate_issues, make_issue

from negmas_elicit import (
    Answer,
    EStrategy,
    Query,
    RangeConstraint,
    User,
)


@pytest.fixture
def outcomes():
    """Create simple outcomes for testing."""
    issues = [make_issue(3, "x"), make_issue(3, "y")]
    return list(enumerate_issues(issues))


@pytest.fixture
def ufun(outcomes):
    """Create a utility function for testing."""
    mapping = {o: (o[0] + o[1]) / 4.0 for o in outcomes}
    return MappingUtilityFunction(mapping=mapping)


@pytest.fixture
def user(ufun):
    """Create a user for testing."""
    return User(preferences=ufun, cost=0.01)


class TestUser:
    """Tests for the User class."""

    def test_user_creation(self, user):
        """Test that a user can be created."""
        assert user is not None
        assert user.cost == 0.01

    def test_user_cost_of_asking(self, user):
        """Test that cost_of_asking returns the cost."""
        assert user.cost_of_asking() == 0.01

    def test_user_total_cost_starts_zero(self, user):
        """Test that total_cost starts at zero."""
        assert user.total_cost == 0.0

    def test_user_ufun_evaluation(self, user, outcomes):
        """Test that the user can evaluate outcomes."""
        for outcome in outcomes:
            utility = user.ufun(outcome)
            assert utility is not None
            assert 0.0 <= utility <= 1.0


class TestQuery:
    """Tests for the Query class."""

    def test_query_creation(self, outcomes):
        """Test that a query can be created."""
        outcome = outcomes[0]
        query = Query(
            answers=[
                Answer([outcome], RangeConstraint((0.0, 0.5)), name="low"),
                Answer([outcome], RangeConstraint((0.5, 1.0)), name="high"),
            ],
            probs=[0.5, 0.5],
            name="test_query",
        )
        assert query is not None
        assert query.name == "test_query"
        assert len(query.answers) == 2

    def test_answer_creation(self, outcomes):
        """Test that an answer can be created."""
        outcome = outcomes[0]
        constraint = RangeConstraint((0.0, 0.5))
        answer = Answer([outcome], constraint, name="test_answer")
        assert answer is not None
        assert answer.name == "test_answer"


class TestRangeConstraint:
    """Tests for the RangeConstraint class."""

    def test_range_constraint_creation(self):
        """Test that a range constraint can be created."""
        constraint = RangeConstraint((0.0, 0.5))
        assert constraint is not None
        assert constraint.range == (0.0, 0.5)

    def test_range_constraint_with_outcomes(self, outcomes):
        """Test range constraint with outcomes (one range per outcome)."""
        # When using outcomes, need to provide a range tuple for each outcome
        ranges = [(0.2, 0.8) for _ in outcomes]
        constraint = RangeConstraint(ranges, outcomes=outcomes)
        assert constraint is not None
        assert len(constraint.range) == len(outcomes)


class TestEStrategy:
    """Tests for the EStrategy class."""

    def test_strategy_creation(self):
        """Test that a strategy can be created."""
        strategy = EStrategy(strategy="bisection", resolution=0.01)
        assert strategy is not None
        assert strategy.strategy == "bisection"
        assert strategy.resolution == 0.01

    def test_supported_strategies(self):
        """Test that supported strategies are returned."""
        strategies = EStrategy.supported_strategies()
        assert "exact" in strategies
        assert "bisection" in strategies
        assert len(strategies) > 0
