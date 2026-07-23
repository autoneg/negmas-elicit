"""Regression tests for VOI related-query pruning.

These cover ``BaseElicitor._prune_related_queries``, which was previously
inlined (and duplicated) in ``BaseVOIElicitor.elicit_single`` and
``VOIOptimalElicitor.elicit_single`` with two bugs:

* the enumerate index ``i`` was used instead of the actual query index
  ``qind`` to index ``self.queries`` -- invalidating unrelated queries and
  raising ``IndexError`` when ``i >= len(self.queries)``;
* ``self.queries[i].answers = ...`` tried to set an attribute on a tuple,
  raising ``AttributeError`` whenever a query's answer set was pruned
  (``2 <= len(tokeep) < len(answers)``).

The tests build a bare ``VOIElicitor`` (bypassing ``__init__``) and exercise
the helper directly so the behaviour is pinned down regardless of whether the
full negotiation flow happens to trigger the pruning path.
"""

from __future__ import annotations

import pytest
from negmas.helpers.prob import UNIFORM, ScipyDistribution

from negmas_elicit.queries import Answer, Query, RangeConstraint
from negmas_elicit.voi import VOIElicitor


def _answer(lo: float, hi: float) -> Answer:
    return Answer(
        outcomes=[("o",)],
        constraint=RangeConstraint(rng=(lo, hi)),
        name=f"{lo:g}-{hi:g}",
    )


def _query(answers: list[Answer]) -> Query:
    n = len(answers)
    return Query(answers=answers, probs=[1.0 / n] * n, cost=0.0, name="q")


def _uniform(lo: float, hi: float) -> ScipyDistribution:
    return ScipyDistribution(type=UNIFORM, loc=lo, scale=hi - lo)


def _bare_elicitor(queries, queries_of_outcome) -> VOIElicitor:
    el = object.__new__(VOIElicitor)
    el.queries = queries
    el.queries_of_outcome = queries_of_outcome
    return el


@pytest.mark.parametrize("elicitor_type", ["voi", "voi_optimal"])
def test_none_queries_of_outcome_returns_newu_unchanged(elicitor_type):
    from negmas_elicit.voi import VOIOptimalElicitor

    cls = VOIElicitor if elicitor_type == "voi" else VOIOptimalElicitor
    el = object.__new__(cls)
    el.queries = []
    el.queries_of_outcome = None
    newu = _uniform(0.2, 0.5)
    assert el._prune_related_queries(("o",), newu, _uniform(0.0, 1.0)) is newu


def test_prune_reduces_answer_subset_without_overwriting_query():
    # Query with 3 answers; posterior range [0.2, 0.5] overlaps answers 0 and 2
    # but exactly matches answer 1 (which is dropped as "already known").
    outcome = ("o",)
    answers = [_answer(0.0, 0.2), _answer(0.2, 0.5), _answer(0.5, 1.0)]
    q = _query(answers)
    queries = [(outcome, q, 0.0)]
    el = _bare_elicitor(queries, {outcome: [0]})

    el._prune_related_queries(outcome, _uniform(0.2, 0.5), _uniform(0.0, 1.0))

    # The query entry must not have been replaced by the (None, None, None)
    # sentinel -- the old code did `self.queries[i].answers = ...` which raised
    # AttributeError on the tuple; the fix mutates the Query in place.
    assert el.queries[0][1] is q
    assert q.answers == [answers[0], answers[2]]
    assert el.queries_of_outcome[outcome] == [0]


def test_prune_invalidates_query_at_correct_index():
    # Two unrelated queries sit at indices 0 and 1; the target query is at
    # index 2. Neither of its answers overlaps the posterior range, so it must
    # be invalidated. The old code invalidated index `i` (the enumerate
    # position 0), corrupting queries[0] instead of queries[2].
    outcome = ("o",)
    q = _query([_answer(0.0, 0.1), _answer(0.9, 1.0)])
    queries = [(("a",), None, None), (("b",), None, None), (outcome, q, 0.0)]
    el = _bare_elicitor(queries, {outcome: [2]})

    el._prune_related_queries(outcome, _uniform(0.4, 0.6), _uniform(0.0, 1.0))

    assert el.queries[2] == (None, None, None)
    assert el.queries[0][0] == ("a",)
    assert el.queries[1][0] == ("b",)
    assert el.queries_of_outcome[outcome] == []


def test_prune_zero_scale_invalidates_all_related():
    outcome = ("o",)
    q = _query([_answer(0.0, 0.5), _answer(0.5, 1.0)])
    queries = [(outcome, q, 0.0)]
    el = _bare_elicitor(queries, {outcome: [0]})

    # A degenerate (zero-scale) posterior invalidates every related query.
    el._prune_related_queries(outcome, _uniform(0.5, 0.5), _uniform(0.0, 1.0))

    assert el.queries[0] == (None, None, None)
    assert el.queries_of_outcome[outcome] == []


def test_prune_skips_already_invalidated_query():
    outcome = ("o",)
    # Both answers of the live query overlap the posterior range [0.2, 0.5],
    # so it is retained; the sentinel at index 0 is skipped (its query is None).
    q = _query([_answer(0.0, 0.3), _answer(0.3, 0.6)])
    queries = [(outcome, None, None), (outcome, q, 0.0)]
    el = _bare_elicitor(queries, {outcome: [0, 1]})

    el._prune_related_queries(outcome, _uniform(0.2, 0.5), _uniform(0.0, 1.0))

    # Index 0 was already a (None, ...) sentinel and must be skipped; index 1
    # is the live query and should be retained with both answers kept.
    assert el.queries[0] == (outcome, None, None)
    assert el.queries[1][1] is q
    assert len(q.answers) == 2
    assert el.queries_of_outcome[outcome] == [1]
