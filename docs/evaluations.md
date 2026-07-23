# Running Evaluations

Installing the package adds a `negmas-elicit` command that drives the same
`SAOElicitingMechanism` used throughout the library. It reproduces the
*experimental methodology* of the accompanying papers: a sweep over elicitors and
negotiation parameters, collecting the utility achieved, the elicitation cost, the
number of queries asked and the distance to the Pareto frontier.

!!! note
    The CLI reproduces the experimental *setup and metrics*. Because each scenario
    is generated randomly (seedable), it does not reproduce the exact table numbers
    printed in the 2018/2019 papers — it reproduces the comparison you run to
    obtain such tables.

## Commands

```text
negmas-elicit list                 # list available elicitors and strategies
negmas-elicit run       [options]  # run one elicitation session
negmas-elicit evaluate  [options]  # sweep elicitors x repetitions and tabulate
```

Run `negmas-elicit <command> --help` for the full option list.

## Listing what is available

```bash
negmas-elicit list
```

## A single session

```bash
negmas-elicit run --elicitor voi --n-outcomes 10 --cost 0.05 --uncertainty 0.3 --seed 0
```

```text
Elicitor           : voi
Agreement          : (7,)
Agreed             : True
Elicitor utility   : 1.0000
Opponent utility   : 0.0180
Welfare            : 1.0180
Elicitation cost   : 0.0000
Queries asked      : 0
Pareto distance    : 0.0
Steps              : 3
Total time (s)     : 0.0007
Total VOI          : 0.0
```

## Comparing elicitors (the sweep)

`evaluate` runs `--repetitions` sessions per elicitor and reports the mean and
standard deviation of each metric. With no `--elicitors` it compares them all.

```bash
negmas-elicit evaluate \
    --elicitors full_knowledge pandora voi voi_optimal \
    --repetitions 20 --n-outcomes 10 --cost 0.02 --uncertainty 0.4 --seed 0
```

```text
Elicitation evaluation (n_outcomes=10, cost=0.02, uncertainty=0.4, conflict=1.0, reps=20)

               elicitor_utility     welfare      elicitation_cost   n_queries    pareto_distance   agreed  steps   total_time
                       mean    std   mean    std       mean   std     mean   std      mean    std    mean   mean         mean
full_knowledge       0.7897 0.1580 1.3991 0.4172      0.000 0.000     0.00  0.00    0.1783 0.2457     1.0   2.85       0.0002
pandora              0.8698 0.0893 1.3845 0.4033      0.072 0.030     3.60  1.50    0.0943 0.2279     1.0   3.45       0.0008
voi                  0.6791 0.2320 1.3288 0.3802      0.045 0.058     2.25  2.90    0.2093 0.2583     1.0   3.05       0.0449
voi_optimal          0.7059 0.2739 1.2835 0.4376      0.047 0.165     2.35  8.26    0.2250 0.2755     1.0   2.90       0.0015
```

Write the results to CSV for plotting/analysis:

```bash
negmas-elicit evaluate --repetitions 50 --out summary.csv --raw sessions.csv
```

- `--out` writes the aggregated (mean/std per elicitor) table.
- `--raw` writes one row per individual session.

## Scenario options

These options are shared by `run` and `evaluate` and define the negotiation
scenario passed to `SAOElicitingMechanism.generate_config`:

| Option | Default | Meaning |
|--------|---------|---------|
| `--cost` | `0.02` | Cost the user charges per query. |
| `--n-outcomes` | `10` | Number of outcomes in the (single-issue) negotiation. |
| `--n-steps` | `100` | Maximum number of negotiation rounds. |
| `--conflict` | `1.0` | Conflict level between the two utility functions in `[0, 1]`. |
| `--winwin` | `0.0` | Win-win level in `[0, 1]`. |
| `--uncertainty` | `0.2` | Uncertainty (scale) of the elicitor's prior utility function. |
| `--reserved-value` | `0.1` | The elicitor's reserved value. |
| `--opponent` | `limited_outcomes` | Opponent negotiator type (`limited_outcomes`, `tough`, `aspiration`, ...). |
| `--strategy` | `bisection` | Deep-elicitation query strategy. |

## Reported metrics

Each session records these into `SAOElicitingMechanism.elicitation_state`:

| Metric | Meaning |
|--------|---------|
| `elicitor_utility` | True utility the elicitor obtained from the agreement (net of elicitation cost). |
| `welfare` | Sum of both negotiators' utilities. |
| `elicitation_cost` | Total cost paid for queries. |
| `n_queries` | Number of queries asked. |
| `pareto_distance` | Distance from the agreement to the Pareto frontier (0 = Pareto optimal). |
| `agreed` | Whether an agreement was reached. |
| `steps` | Number of negotiation rounds used. |
| `total_time` | Wall-clock time for the session. |

## Programmatic use

The same helper is importable:

```python
from negmas_elicit.cli import run_session

result = run_session(
    "voi", n_outcomes=10, cost=0.05, own_utility_uncertainty=0.3, seed=0
)
print(result.elicitor_utility, result.n_queries)
```
