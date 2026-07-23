"""Tests for the ``negmas-elicit`` command-line interface."""

from __future__ import annotations

import pytest

from negmas_elicit.cli import ELICITOR_TYPES, main, run_session


def test_list_command(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "voi" in out and "bisection" in out


def test_run_command(capsys):
    assert (
        main(
            [
                "run",
                "--elicitor",
                "full_knowledge",
                "--n-outcomes",
                "6",
                "--n-steps",
                "20",
                "--seed",
                "0",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "Elicitor utility" in out and "Agreement" in out


def test_evaluate_command_writes_csv(tmp_path, capsys):
    out = tmp_path / "summary.csv"
    code = main(
        [
            "evaluate",
            "--elicitors",
            "pandora",
            "full_knowledge",
            "voi",
            "--repetitions",
            "2",
            "--n-outcomes",
            "6",
            "--seed",
            "0",
            "--out",
            str(out),
        ]
    )
    assert code == 0
    assert out.exists()
    printed = capsys.readouterr().out
    assert "elicitor_utility" in printed


@pytest.mark.parametrize(
    "elicitor", ["full_knowledge", "pandora", "voi", "voi_optimal"]
)
def test_run_session_returns_metrics(elicitor):
    result = run_session(
        elicitor,
        n_outcomes=6,
        n_steps=20,
        cost=0.05,
        own_utility_uncertainty=0.3,
        seed=1,
    )
    assert result.elicitor == elicitor
    assert result.elicitation_cost >= 0.0
    assert isinstance(result.agreed, bool)
    assert result.steps >= 0


def test_all_elicitor_types_run():
    # smoke: every advertised elicitor type runs end-to-end via the CLI helper
    for elicitor in ELICITOR_TYPES:
        result = run_session(elicitor, n_outcomes=6, n_steps=15, seed=0)
        assert result.elicitor == elicitor
