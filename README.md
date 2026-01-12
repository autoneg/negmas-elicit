# negmas-elicit

[![PyPI version](https://badge.fury.io/py/negmas-elicit.svg)](https://badge.fury.io/py/negmas-elicit)
[![Tests](https://github.com/yasserfarouk/negmas-elicit/actions/workflows/test.yml/badge.svg)](https://github.com/yasserfarouk/negmas-elicit/actions/workflows/test.yml)
[![Documentation](https://github.com/yasserfarouk/negmas-elicit/actions/workflows/docs.yml/badge.svg)](https://yasserfarouk.github.io/negmas-elicit/)
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
git clone https://github.com/yasserfarouk/negmas-elicit.git
cd negmas-elicit
pip install -e .
```

## Quick Start

```python
from negmas import MappingUtilityFunction
from negmas.outcomes import make_issue
from negmas_elicit import (
    User,
    PandoraElicitor,
    SAOElicitingMechanism,
)

# Define the negotiation issues
issues = [make_issue(10, "price"), make_issue(5, "quality")]

# Create a user with a known utility function
ufun = MappingUtilityFunction(
    mapping=lambda o: o[0] / 10 + o[1] / 5,
    issues=issues,
)
user = User(ufun=ufun, cost=0.1)

# Create an elicitor
elicitor = PandoraElicitor(user=user)

# Use in a mechanism or standalone elicitation
# ...
```

## Available Elicitors

### Baseline Elicitors
- `DummyElicitor`: No elicitation, uses prior beliefs
- `FullKnowledgeElicitor`: Assumes complete knowledge of user preferences

### Pandora Elicitors
- `PandoraElicitor`: Standard Pandora's box approach
- `OptimalIncrementalElicitor`: Optimal incremental elicitation
- `FastElicitor`: Fast approximation
- `MeanElicitor`, `BalancedElicitor`, `AspiringElicitor`: Different expectation strategies
- `OptimisticElicitor`, `PessimisticElicitor`: Optimistic/pessimistic strategies

### VOI Elicitors
- `VOIElicitor`: Value of Information based elicitation (OQA)
- `VOIFastElicitor`: Fast VOI approximation
- `VOIOptimalElicitor`: Optimal VOI strategy
- `VOINoUncertaintyElicitor`: VOI without uncertainty modeling

## References

The elicitation algorithms implemented in this library are based on the following papers:

| Algorithm | Paper |
|-----------|-------|
| Pandora's Box | Baarslag, T., & Gerding, E. H. (2015). Optimal incremental preference elicitation during negotiation. IJCAI'15. |
| VOI / OQA | Baarslag, T., & Kaisers, M. (2017). The Value of Information in Automated Negotiation. AAMAS'17. |
| FastVOI | Mohammad, Y., & Nakadai, S. (2018). FastVOI: Efficient utility elicitation during negotiations. PRIMA'18. |
| Optimal VOI | Mohammad, Y., & Nakadai, S. (2019). Optimal Value of Information Based Elicitation During Negotiation. AAMAS'19. |

### BibTeX

```bibtex
@inproceedings{baarslag2015optimal,
    title={Optimal incremental preference elicitation during negotiation},
    author={Baarslag, Tim and Gerding, Enrico H},
    booktitle={Proceedings of the 24th International Conference on Artificial Intelligence},
    pages={3--9},
    year={2015},
    organization={AAAI Press}
}

@inproceedings{baarslag2017value,
    title={The value of information in automated negotiation: A decision model for eliciting user preferences},
    author={Baarslag, Tim and Kaisers, Michael},
    booktitle={Proceedings of the 16th Conference on Autonomous Agents and MultiAgent Systems},
    pages={391--400},
    year={2017},
    organization={IFAAMAS}
}

@inproceedings{mohammad2018fastvoi,
    title={FastVOI: Efficient utility elicitation during negotiations},
    author={Mohammad, Yasser and Nakadai, Shinji},
    booktitle={International Conference on Principles and Practice of Multi-Agent Systems},
    pages={560--567},
    year={2018},
    organization={Springer}
}

@inproceedings{mohammad2019optimal,
    title={Optimal value of information based elicitation during negotiation},
    author={Mohammad, Yasser and Nakadai, Shinji},
    booktitle={Proceedings of the 18th International Conference on Autonomous Agents and MultiAgent Systems},
    pages={242--250},
    year={2019},
    organization={IFAAMAS}
}
```

## Documentation

Full documentation is available at [https://yasserfarouk.github.io/negmas-elicit/](https://yasserfarouk.github.io/negmas-elicit/)

## Requirements

- Python 3.12+
- negmas >= 0.10.0

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
  organization={Springer}
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
