"""Tests to verify all imports work correctly."""

from __future__ import annotations


def test_import_package():
    """Test that the main package can be imported."""
    import negmas_elicit

    assert negmas_elicit.__version__ == "0.1.1"


def test_import_all_exports():
    """Test that all exports from __all__ can be imported."""
    from negmas_elicit import (
        # voi
        BaseElicitor,
        EStrategy,
        Query,
        User,
    )

    # Verify classes are actually classes
    assert isinstance(User, type)
    assert isinstance(BaseElicitor, type)
    assert isinstance(EStrategy, type)
    assert isinstance(Query, type)


def test_import_submodules():
    """Test that all submodules can be imported directly."""
    from negmas_elicit import (
        base,
        baseline,
        common,
        expectors,
        mechanism,
        pandora,
        queries,
        strategy,
        user,
        voi,
    )

    assert base is not None
    assert baseline is not None
    assert common is not None
    assert expectors is not None
    assert mechanism is not None
    assert pandora is not None
    assert queries is not None
    assert strategy is not None
    assert user is not None
    assert voi is not None
