# Data still to fill in

The Week 18 case is a placeholder so tools and the UI can run. Replace files in `data/cases/` without changing tool names.

| Field | Current | Needed |
| --- | --- | --- |
| Weekly forecast vs actual TRx | DuckDB `weekly_performance` (synthetic national + 4 regions) | Real or calibrated weekly vintages |
| NRx / NBRx | Columns exist, values null | Fill if briefing needs them |
| Access status / competitor share | Placeholder flags on TRx rows | Plan-level series |
| Payer events | One synthetic formulary downgrade | Plan-level access changes |
| Competitor events | One regional launch | National launches with no clean control |
| Inventory / seasonality | Not injected | Optional Oct 9 extensions |
| Public calibration | Missing | CMS Part D, formulary files, openFDA NDC |
| Segments | `all` | Channel / payer segment |
| Briefing handoff | Simulated `brief_lumina_w18` request in DuckDB | Live request from Michael/Meghna |
| Ground truth | DuckDB `eval_ground_truth` (evaluator-only) | Held-out seeds and negative controls |

Do not put ground-truth files on the Investigator tool path. Evaluator UI can load them separately.
