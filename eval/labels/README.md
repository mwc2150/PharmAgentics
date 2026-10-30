# Human labels

LLM-judge scores count only after their agreement with human labels is measured (Evaluation Pack open item 2). Label a sample of answers here, then compare with the judge's scores for the same traces.

One CSV per labelling round, named `YYYY-MM-DD-<reviewer>.csv`, with these columns:

| Column | Content |
| :- | :- |
| `trace_id` | The MLflow trace of the answer being labelled (from the dashboard) |
| `story` | Persona question, e.g. P2-Q3 |
| `item` | Eval item judged, e.g. EV-1.3, EV-5.3, EV-7.1, FE-24 |
| `label` | Meets, Partly or Misses (scale and anchors: open item 13) |
| `note` | Why, in one line |

Label answers from both controls and from real systems, so the sample holds good and bad answers. The agreement statistic and its bar are still open (item 2).
