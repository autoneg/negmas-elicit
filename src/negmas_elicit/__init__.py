""" "
The interface to all negotiators capable of eliciting user preferences before
, and during negotiations.

This module was extracted from the negmas library.
"""

from __future__ import annotations

from negmas_elicit.base import BaseElicitor
from negmas_elicit.baseline import DummyElicitor, FullKnowledgeElicitor
from negmas_elicit.common import (
    _loc,
    _locs,
    _scale,
    _upper,
    _uppers,
    argmax,
    argmin,
    argsort,
)
from negmas_elicit.expectors import (
    AspiringExpector,
    BalancedExpector,
    Expector,
    MaxExpector,
    MeanExpector,
    MinExpector,
    StaticExpector,
)
from negmas_elicit.mechanism import SAOElicitingMechanism
from negmas_elicit.pandora import (
    AspiringElicitor,
    BalancedElicitor,
    BasePandoraElicitor,
    FastElicitor,
    FullElicitor,
    MeanElicitor,
    OptimalIncrementalElicitor,
    OptimisticElicitor,
    PandoraElicitor,
    PessimisticElicitor,
    RandomElicitor,
    weitzman_index_uniform,
)
from negmas_elicit.queries import (
    Answer,
    ComparisonConstraint,
    Constraint,
    CostEvaluator,
    MarginalNeutralConstraint,
    QResponse,
    Query,
    RangeConstraint,
    RankConstraint,
    next_query,
    possible_queries,
)
from negmas_elicit.strategy import EStrategy
from negmas_elicit.user import ElicitationRecord, User
from negmas_elicit.voi import (
    OQA,
    BaseVOIElicitor,
    VOIElicitor,
    VOIFastElicitor,
    VOINoUncertaintyElicitor,
    VOIOptimalElicitor,
)

__all__ = (
    # common
    "_loc",
    "_locs",
    "_scale",
    "_upper",
    "_uppers",
    "argmax",
    "argmin",
    "argsort",
    # expectors
    "Expector",
    "StaticExpector",
    "MeanExpector",
    "MaxExpector",
    "MinExpector",
    "BalancedExpector",
    "AspiringExpector",
    # user
    "User",
    "ElicitationRecord",
    # queries
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
    # strategy
    "EStrategy",
    # base
    "BaseElicitor",
    # baseline
    "DummyElicitor",
    "FullKnowledgeElicitor",
    # pandora
    "BasePandoraElicitor",
    "PandoraElicitor",
    "OptimalIncrementalElicitor",
    "FullElicitor",
    "RandomElicitor",
    "weitzman_index_uniform",
    "FastElicitor",
    "MeanElicitor",
    "BalancedElicitor",
    "AspiringElicitor",
    "PessimisticElicitor",
    "OptimisticElicitor",
    # voi
    "BaseVOIElicitor",
    "VOIElicitor",
    "VOIFastElicitor",
    "VOINoUncertaintyElicitor",
    "VOIOptimalElicitor",
    "OQA",
    # mechanism
    "SAOElicitingMechanism",
)

from importlib.metadata import version as _get_version

__version__ = _get_version("negmas-elicit")

import numpy as np

np.seterr(all="raise")  # setting numpy to raise exceptions in case of errors
