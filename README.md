# negmas-elicit

[![PyPI version](https://badge.fury.io/py/negmas-elicit.svg)](https://badge.fury.io/py/negmas-elicit)
[![Tests](https://github.com/autoneg/negmas-elicit/actions/workflows/test.yml/badge.svg)](https://github.com/autoneg/negmas-elicit/actions/workflows/test.yml)
[![Documentation](https://github.com/autoneg/negmas-elicit/actions/workflows/docs.yml/badge.svg)](https://autoneg.github.io/negmas-elicit/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

A library for preference elicitation during automated negotiations. This module was extracted from the [negmas](https://github.com/yasserfarouk/negmas) library to provide a focused, standalone package for elicitation capabilities.

## Features

- **Multiple Elicitation Strategies**: Pandora-based elicitors, Value of Information (VOI) elicitors, and baseline implementations
- **Query System**: Flexible query types including range, rank, comparison, and marginal neutrality constraints
- **User Modeling**: Simulate users with different response behaviors and costs
- **Expector Functions**: Various strategies for handling uncertainty (mean, max, min, balanced, aspiring)
- **Mechanism Integration**: `SAOElicitingMechanism` for running negotiations with preference elicitation

## Installation

### From PyPI

```bash
pip install negmas-elicit
```

### From Source

```bash
git clone https://github.com/autoneg/negmas-elicit.git
cd negmas-elicit
pip install -e .
```

## Quick Start

```python
from negmas_elicit import SAOElicitingMechanism

# Generate a random-but-controlled negotiation scenario, then plug in an elicitor.
config = SAOElicitingMechanism.generate_config(
    cost=0.02,  # what the user charges per query
    n_outcomes=10,
    n_steps=100,
    conflict=1.0,
    own_utility_uncertainty=0.2,  # how uncertain the elicitor's prior ufun is
    own_reserved_value=0.1,
    opponent_type="limited_outcomes",
)
mech = SAOElicitingMechanism(
    **config, elicitor_type="voi", elicitation_strategy="bisection"
)
mech.run()

s = mech.elicitation_state
print("agreement:", s["agreement"])
print("elicitor utility:", round(s["elicitor_utility"], 3))
print("elicitation cost:", round(s["elicitation_cost"], 3))
print("queries asked:", s["n_queries"])
```

See the [documentation](https://autoneg.github.io/negmas-elicit/) for a
guided tour, a manual `User` + `EStrategy` + elicitor example, and the full API.

## Command-line evaluations

Installing the package provides a `negmas-elicit` command for reproducing the
paper-style experiments (sweeping elicitors and reporting utility, elicitation
cost, number of queries and Pareto distance):

```bash
negmas-elicit list                                   # available elicitors & strategies
negmas-elicit run --elicitor voi --n-outcomes 10     # a single session
negmas-elicit evaluate --repetitions 20 --out out.csv  # compare all elicitors
```

## Sample results

The table below is the output of a full tournament sweeping every elicitor
over 20 repetitions (240 sessions, no failures). It was produced with:

```bash
negmas-elicit evaluate --repetitions 20 --n-outcomes 10 --n-steps 100 \
    --cost 0.02 --uncertainty 0.2 --conflict 1.0 --opponent limited_outcomes \
    --out out.csv --raw out_raw.csv
```

i.e. 10 outcomes, a per-query cost of 0.02, prior utility uncertainty of 0.2,
full conflict (`conflict=1.0`), and a `limited_outcomes` opponent. `method` is
the elicitor's family: **Pandora's-box** (Baarslag & Gerding 2015, only
`pandora` here), **Practical** (Mohammad & Nakadai 2018 — the practical
elicitation-strategy variants), **VOI** (Value of Information), and `baseline`
(the no-elicitation oracle).

| method | variant | utility (mean±std) | welfare | elic. cost | n_queries | pareto dist | steps | time (s) |
|----------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| baseline | **full_knowledge** | **0.790 ± 0.158** | 1.399 | 0.000 | 0.0 | 0.178 | 2.85 | 0.0002 |
| VOI | voi_optimal | 0.776 ± 0.186 | 1.422 | 0.000 | 0.0 | 0.136 | 2.85 | 0.0003 |
| VOI | voi | 0.738 ± 0.196 | 1.346 | 0.018 | 0.9 | 0.195 | 3.0 | 0.0162 |
| Pandora's-box | pandora | 0.708 ± 0.162 | 1.322 | 0.044 | 2.2 | 0.252 | 2.8 | 0.0004 |
| Practical | fast | 0.708 ± 0.162 | 1.322 | 0.044 | 2.2 | 0.252 | 2.8 | 0.0004 |
| Practical | mean | 0.708 ± 0.162 | 1.322 | 0.044 | 2.2 | 0.252 | 2.8 | 0.0004 |
| Practical | balanced | 0.708 ± 0.162 | 1.322 | 0.044 | 2.2 | 0.252 | 2.8 | 0.0004 |
| Practical | optimistic | 0.708 ± 0.162 | 1.322 | 0.044 | 2.2 | 0.252 | 2.8 | 0.0004 |
| Practical | pessimistic | 0.708 ± 0.162 | 1.322 | 0.044 | 2.2 | 0.252 | 2.8 | 0.0005 |
| VOI | voi_fast | 0.675 ± 0.233 | 1.319 | 0.070 | 3.5 | 0.184 | 2.75 | 0.0154 |
| Practical | random | 0.626 ± 0.205 | 1.202 | 0.081 | 4.1 | 0.270 | 3.0 | 0.0008 |
| Practical | full | 0.463 ± 0.186 | 1.109 | 0.313 | 15.7 | 0.232 | 2.85 | 0.0027 |

A few things to note:

- **`full_knowledge`** is the top performer — as the no-query oracle it should
  be: it knows the true utility and pays no elicitation cost, so it bounds
  everyone from above. (It underperforming elicitors would indicate a
  configuration bug; here it correctly leads.)
- **`voi_optimal`** declines to elicit at `cost=0.02`: its expected value of
  information never clears the cost, so it asks zero queries. **`voi`** asks
  ~0.9 queries on average.
- Only `pandora` is Baarslag & Gerding's Pandora's-box method (IJCAI 2015);
  `fast`, `mean`, `balanced`, `optimistic`, `pessimistic` (and `full`,
  `random`) are Mohammad & Nakadai's practical elicitation strategies (IEEE
  SMC 2018). At 10 outcomes the practical variants coincide with `pandora`
  (same outcome to elicit/offer); they elicit ~2.2 queries but land below the
  no-query baselines here because, with the default `toughness`, the base
  negotiator concedes quickly to early (often dominated) agreements, so
  elicitation mostly adds cost. Raising `toughness` (a slower-conceding base
  negotiator) lets elicitation pay off.
- **`full`** elicits every outcome (15.7 queries, highest cost 0.313), so the
  cost dominates — it ends with the lowest utility (0.463).

### 100-outcome tournament

With a larger outcome space (100 outcomes, same cost 0.02, 100 steps, conflict
not fixed — scenarios use random bilateral utilities; `voi` is omitted because
its dynamic-query construction is impractically slow at this scale), 220
sessions:

| method | variant | utility (mean±std) | welfare | elic. cost | n_queries | pareto dist | steps | time (s) |
|----------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| baseline | full_knowledge | 0.668 ± 0.153 | 1.306 | 0.000 | 0.0 | 0.314 | 2.90 | 0.0017 |
| Pandora's-box | pandora | 0.681 ± 0.155 | 1.179 | 0.046 | 2.3 | 0.375 | 2.75 | 0.0032 |
| Practical | fast | 0.681 ± 0.155 | 1.179 | 0.046 | 2.3 | 0.375 | 2.75 | 0.0035 |
| Practical | mean | 0.681 ± 0.155 | 1.179 | 0.046 | 2.3 | 0.375 | 2.75 | 0.0043 |
| Practical | balanced | 0.681 ± 0.155 | 1.179 | 0.046 | 2.3 | 0.375 | 2.75 | 0.0028 |
| Practical | optimistic | 0.681 ± 0.155 | 1.179 | 0.046 | 2.3 | 0.375 | 2.75 | 0.0021 |
| Practical | pessimistic | 0.681 ± 0.155 | 1.179 | 0.046 | 2.3 | 0.375 | 2.75 | 0.0022 |
| VOI | voi_optimal | 0.680 ± 0.171 | 1.306 | 0.000 | 0.0 | 0.314 | 2.75 | 0.0025 |
| Practical | random | 0.493 ± 0.211 | 1.086 | 0.231 | 11.6 | 0.379 | 2.35 | 0.0047 |
| VOI | voi_fast | 0.190 ± 0.560 | 0.772 | 0.471 | 23.6 | 0.648 | 2.80 | 1.6239 |
| Practical | full | 0.100 ± 0.000 | — | 3.017 | 150.9 | — | 2.00 | 0.0000 |

At this scale the no-query baselines (`full_knowledge`, `voi_optimal`) and the
Pandora's-box / practical family are statistically tied (~0.68; std ≈ 0.16).
`voi_fast` becomes noisy (it asks ~24 queries, sometimes over-eliciting), and
`full` cannot reach agreement: eliciting all 100 outcomes costs ~3.0 (above the
maximum achievable utility of 1.0), so it ends the negotiation immediately and
settles for the reserved value (0.100).

## Available Elicitors

Each elicitor is tagged with its method family and the paper that introduced it:

- **Pandora's-box** — Baarslag & Gerding, [IJCAI 2015](https://www.ijcai.org/Proceedings/15/Papers/008.pdf): the original optimal incremental / Pandora's-box elicitor.
- **Practical elicitation strategies** — Mohammad & Nakadai, [IEEE SMC 2018](https://doi.org/10.1109/SMC.2018.00525): extends the optimal elicitation algorithm to the practical case where queries reduce (not remove) uncertainty, using different expectation strategies.
- **VOI** — Value of Information: Baarslag & Kaisers, [AAMAS 2017](https://ifaamas.org/Proceedings/aamas2017/pdfs/p391.pdf) (OQA); Mohammad & Nakadai, [PRIMA 2018](https://link.springer.com/chapter/10.1007/978-3-030-03098-8_42) (FastVOI) and [AAMAS 2019](https://www.ifaamas.org/Proceedings/aamas2019/pdfs/p242.pdf) (Optimal VOI).

### Baseline Elicitors
- `FullKnowledgeElicitor`: Assumes complete knowledge of user preferences (the
  no-elicitation upper bound used in the tournaments)

### Pandora's-box elicitors — Baarslag & Gerding (IJCAI 2015)
- `PandoraElicitor` — **Pandora's-box**: standard Pandora's box approach
- `OptimalIncrementalElicitor` — **Pandora's-box**: optimal incremental elicitation

### Practical elicitation strategies — Mohammad & Nakadai (IEEE SMC 2018)
- `FastElicitor` — practical: fast approximation (no deep elicitation)
- `MeanElicitor`, `BalancedElicitor`, `AspiringElicitor` — practical: different expectation strategies
- `OptimisticElicitor`, `PessimisticElicitor` — practical: optimistic/pessimistic strategies
- `FullElicitor` — practical baseline: elicits every outcome up front, then offers
- `RandomElicitor` — practical baseline: random index instead of the optimal z-index

### VOI Elicitors — Value-of-Information methods
- `VOIElicitor` — **VOI** (OQA; Baarslag & Kaisers, AAMAS 2017)
- `VOIFastElicitor` — **VOI** (FastVOI; Mohammad & Nakadai, PRIMA 2018)
- `VOIOptimalElicitor` — **VOI** (Optimal VOI; Mohammad & Nakadai, AAMAS 2019)
- `VOINoUncertaintyElicitor` — **VOI**: VOI without uncertainty modeling

## References

The elicitation algorithms implemented in this library are based on the following papers:

| Algorithm | Paper |
|-----------|-------|
| Pandora's Box | Baarslag, T., & Gerding, E. H. (2015). [Optimal incremental preference elicitation during negotiation](https://www.ijcai.org/Proceedings/15/Papers/008.pdf). IJCAI'15. |
| Practical elicitation strategies | Mohammad, Y., & Nakadai, S. (2018). [Utility elicitation during negotiation with practical elicitation strategies](https://doi.org/10.1109/SMC.2018.00525). IEEE SMC'18. |
| VOI / OQA | Baarslag, T., & Kaisers, M. (2017). [The Value of Information in Automated Negotiation](https://ifaamas.org/Proceedings/aamas2017/pdfs/p391.pdf). AAMAS'17. |
| FastVOI | Mohammad, Y., & Nakadai, S. (2018). [FastVOI: Efficient utility elicitation during negotiations](https://link.springer.com/chapter/10.1007/978-3-030-03098-8_42). PRIMA'18. |
| Optimal VOI | Mohammad, Y., & Nakadai, S. (2019). [Optimal Value of Information Based Elicitation During Negotiation](https://www.ifaamas.org/Proceedings/aamas2019/pdfs/p242.pdf). AAMAS'19. |

### BibTeX

```bibtex
@inproceedings{baarslag2015optimal,
    title={Optimal incremental preference elicitation during negotiation},
    author={Baarslag, Tim and Gerding, Enrico H},
    booktitle={Proceedings of the 24th International Conference on Artificial Intelligence},
    pages={3--9},
    year={2015},
    organization={AAAI Press},
    url={https://www.ijcai.org/Proceedings/15/Papers/008.pdf}
}

@inproceedings{mohammad2018practical,
    title={Utility elicitation during negotiation with practical elicitation strategies},
    author={Mohammad, Yasser and Nakadai, Shinji},
    booktitle={2018 IEEE International Conference on Systems, Man, and Cybernetics (SMC)},
    pages={3100--3107},
    year={2018},
    organization={IEEE},
    doi={10.1109/SMC.2018.00525},
    url={https://doi.org/10.1109/SMC.2018.00525}
}

@inproceedings{baarslag2017value,
    title={The value of information in automated negotiation: A decision model for eliciting user preferences},
    author={Baarslag, Tim and Kaisers, Michael},
    booktitle={Proceedings of the 16th Conference on Autonomous Agents and MultiAgent Systems},
    pages={391--400},
    year={2017},
    organization={IFAAMAS},
    url={https://ifaamas.org/Proceedings/aamas2017/pdfs/p391.pdf}
}

@inproceedings{mohammad2018fastvoi,
    title={FastVOI: Efficient utility elicitation during negotiations},
    author={Mohammad, Yasser and Nakadai, Shinji},
    booktitle={International Conference on Principles and Practice of Multi-Agent Systems},
    pages={560--567},
    year={2018},
    organization={Springer},
    doi={10.1007/978-3-030-03098-8_42},
    url={https://link.springer.com/chapter/10.1007/978-3-030-03098-8_42}
}

@inproceedings{mohammad2019optimal,
    title={Optimal value of information based elicitation during negotiation},
    author={Mohammad, Yasser and Nakadai, Shinji},
    booktitle={Proceedings of the 18th International Conference on Autonomous Agents and MultiAgent Systems},
    pages={242--250},
    year={2019},
    organization={IFAAMAS},
    url={https://www.ifaamas.org/Proceedings/aamas2019/pdfs/p242.pdf}
}
```

## Documentation

Full documentation is available at [https://autoneg.github.io/negmas-elicit/](https://autoneg.github.io/negmas-elicit/)

## Requirements

- Python 3.12+
- negmas >= 0.15.2

## License

This project is licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See the [LICENSE](LICENSE) file for details.

## Citation

If you use this library in your research, please cite the negmas library:

```bibtex
@inproceedings{negmas2019,
  title={NegMAS: A Platform for Automated Negotiation},
  author={Mohammad, Yasser and Greenwald, Amy and Nakadai, Shinji},
  booktitle={International Conference on Principles and Practice of Multi-Agent Systems},
  pages={343--351},
  year={2019},
  organization={Springer},
  doi={10.1007/978-3-030-69322-0_23},
  url={https://link.springer.com/chapter/10.1007/978-3-030-69322-0_23}
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
