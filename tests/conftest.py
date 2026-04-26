"""Pytest configuration and fixtures for negmas-elicit tests."""

from __future__ import annotations

import pytest
from negmas import MappingUtilityFunction
from negmas.outcomes import make_issue

from negmas_elicit import User


@pytest.fixture
def simple_issues():
    """Create simple negotiation issues for testing."""
    return [make_issue(5, "price"), make_issue(3, "quality")]


@pytest.fixture
def simple_outcomes(simple_issues):
    """Generate all outcomes from simple issues."""
    from negmas.outcomes import enumerate_issues

    return list(enumerate_issues(simple_issues))


@pytest.fixture
def simple_ufun(simple_issues, simple_outcomes):
    """Create a simple utility function for testing."""

    # Linear utility: higher price and quality are better
    def utility(outcome):
        if outcome is None:
            return 0.0
        return (outcome[0] / 4 + outcome[1] / 2) / 2

    return MappingUtilityFunction(
        mapping={o: utility(o) for o in simple_outcomes},
        issues=simple_issues,
    )


@pytest.fixture
def simple_user(simple_ufun):
    """Create a simple user for testing."""
    return User(ufun=simple_ufun, cost=0.01)
