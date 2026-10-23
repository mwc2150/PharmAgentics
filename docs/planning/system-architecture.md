<!-- Markdown copy of the Google Doc "PharmAgentics — System Architecture (SoT)" (Consolidated 10/22 folder), taken 2026-10-23. The Google Doc is the master; update it first. Diagram: PharmAgentics_System_Architecture.png in the same Drive folder. -->

# PharmAgentics — System Architecture (SoT)

Oct 22, 2026 · @Michael

## 1. Purpose, sources and precedence

PharmAgentics is one system: a shared platform and a seven-stage spine that both use cases run, with detection (stage 3) and the Magentic investigation loop (stage 4) doubled, one per use case. This doc is the system-level source of truth. It unifies the sources below without editing any of them.

| Source | Owner | Date | What this doc takes from it |
| :- | :- | :- | :- |
| Briefing Agent Architecture (SoT) and diagram | Michael, Meghna | Oct 21 | The spine, stage specs, loop guardrails, run states; the template for the whole system |
| Forecast-Explanation Agent: Architecture and Spec-Driven Development (AALS.pdf) | Alvin | Oct 2026 | Investigator modes, deterministic tools, the InvestigationRequest and InvestigationReport contract, Spec Kit setup |
| [PharmAgentics repo](https://github.com/mwc2150/PharmAgentics), data foundation (PR #1, merged Oct 21) | Meghna | Oct 21 | The shared data world: 14 tables in DuckDB and the feed-health gate |
| AALS Project Proposal | All four | Oct 6 | Common data layer, shared orchestration layer, Magentic pattern, scope |

**Not touched here.** Personas and evaluation stay separate per use case, even where titles match. The Briefing Agent Personas (P1 to P4) and Evaluation Pack (EV-x.y) belong to Michael and Meghna. The Forecast-Explanation Personas and Evaluation Design (CA, BM, FM; FE-xx; TC-xx) belong to Sienna and Alvin. Section 9 links to them by ID only.

**Precedence.**

1. The Proposal.
2. Each use case's personas and evaluation pack.
3. This doc, for everything shared or cross-agent: data world, semantic layer, tool contract, spine, tracing, eval harness, governance, and the interface between agents.
4. Each agent's own architecture doc, for the internals of its own lane.

**Delineation rules.**

| Case | Rule |
| :- | :- |
| Both use cases agree | Stated once, as shared |
| They differ and both work | Recorded side by side with owners; no winner picked (Sections 6 to 8) |
| They conflict on something shared | Logged as a system open item, S1 to S16 (Section 10) |
| This doc proposes a change inside one lane | Tagged Proposed; that lane's owners decide |

**Source tags.** B = Briefing architecture · F = Forecast architecture (Alvin) · FP = Forecast personas and eval (Sienna) · D = repo data foundation · P = Proposal · New = this doc.

## 3. Shared platform

Both agents stand on seven shared parts. Only the stages inside each lane (Section 4) differ by use case.

### 3.1 Data world (D)

Meghna's data foundation is the one data world for both agents. It replaces the world sketched in Briefing architecture Section 8 and the LUMINA Week 18 fixture in the Forecast prototype (S3).

| Aspect | Value |
| :- | :- |
| Generator | Seed 7, release day1-v1; generator and answer key stored outside the repo |
| Time | 104 Monday-start weeks, 2024-10-14 to 2026-10-05 |
| Geography | 8 territories in 4 regions: Northeast (New England, Mid-Atlantic), Midwest (Great Lakes), South (Southeast, South Central), West (Mountain, Pacific, Northwest) |
| Payers | 64 synthetic plans, 2 per channel per territory, across commercial, Medicare Part D, Medicaid and cash |
| HCP specialty | Primary care, cardiology, internal medicine, endocrinology |
| Products | Fictional cardiometabolic basket: BXA Cardiovela (index brand); BXC Lipidara and BXD Vascriva (competitors); BXE Metacora (competitor launch, 2026-03-02) |
| Seeded content | 6 business events and 3 feed artifacts; event labels live only in the hidden answer key |
| Forecast | 4-week-ahead TRx forecast for BXA by territory plus NATIONAL, keyed by issue week; blind by design to unplanned launch, payer, promotion and inventory shocks |

**Storage.** One DuckDB file (`local/pharmagentics.duckdb`) with three schemas: `raw` holds the 14 typed source tables with duplicates and NULLs kept; `metadata` holds import runs and SHA-256 fingerprints; `reporting` holds key checks, feed health and gated KPI views.

| Table | Grain | Briefing reads | Forecast reads | Note |
| :- | :- | :- | :- | :- |
| rx_weekly | week × territory × plan × specialty × product | Yes | Yes, to localize a miss | Raw feed; validate before use |
| market_share_weekly | week × territory × product | Yes | No | Provisional; use with health checks |
| market_basket | product × effective dates | Yes | Yes, for competitor launch | |
| access_status_monthly | month × plan × product | Yes | Yes | Join on plan, product and month, not channel |
| promo_activity | week × territory × product | Yes | Yes | Rep calls and vacancies arrive aggregated |
| inventory_weekly | week × territory × product | Open (S5) | Yes | Proposal names inventory as a forecast driver |
| calendar | week | Yes | Yes | Holidays, business days, plan-year reset |
| feed_metadata | week × territory | Yes | Yes | Coverage, lag, restatement flag |
| restatement_log | Rx key × revision date | Yes | Yes | Prior and revised values |
| forecast_vs_actual_weekly | issue week × week × territory × product | Open (Section 5) | Yes | actual_is_provisional on bad-feed weeks |
| dim_product, dim_plan, dim_territory, dim_specialty | one row per member | Yes | Yes | dim_territory answers Briefing A6 |

**Feed-health gate.** `reporting.v_feed_health` is the v0 stage 2 for both lanes. A week × territory cut is reportable only with one COMPLETE metadata record, reconciled row counts, no missing or duplicate keys, panel coverage of 0.98 to 1.0, lag within one day of target, and no restatement. A failed cut is withheld from the KPI views, never read as zero demand.

### 3.2 Semantic layer (B, D)

One set of versioned YAML files, validated by Pydantic, defines every metric, dimension and threshold for both agents. The repo's `data_dictionary.json` seeds it. Briefing owns the Rx metrics; Forecast adds `forecast_trx`, `variance_trx`, `variance_pct`, `horizon_weeks` and the locked-version key `forecast_issue_week`. Tools reject any metric ID the layer does not hold.

### 3.3 Tool contract (B, F)

Every tool is plain deterministic code with no LLM inside, and every call returns a record that outputs cite. The two lanes already use nearly the same record:

| Field | Briefing evidence_items (B) | Forecast tool record (F) |
| :- | :- | :- |
| ID | evidence_id, per run_id | tool_id |
| Tool | source tool | name |
| Inputs | parameters | arguments |
| Output | result | payload |
| Trace link | source reference, span ID | Listed in the report's evidence log |

Whether the two shapes become one is open (S9). The rule they share is not: no number reaches an output without a record behind it.

### 3.4 Orchestration (P, B, F)

The Proposal's shared orchestration layer becomes one run orchestrator. It owns run IDs, state, timeouts, failures and logging for both lanes. Each lane keeps its own trigger, run states and Magentic loop, so neither agent waits on the other. This amends the Proposal's single manager over both agents (S2).

### 3.5 Tracing (B, F)

Briefing traces with OpenTelemetry spans in Arize Phoenix, from claim token to evidence item to span. Forecast ships an evidence log of tool records inside each report. The shared floor: any number can be traced to its record on the pinned data version.

### 3.6 Eval harness (B, FP)

One harness is the only component that reads the answer key, which sits in a separate store. It scores each lane against that lane's own pack. Shared conventions: held-out seeded cases, scripted and low-code baselines, repeated runs, and answer-key isolation.

### 3.7 Governance (P, B, F)

- Synthetic data only; no patient or proprietary data goes to an external model.
- No output identifies an individual rep; promotion data arrives aggregated at the source.
- No agent tool can read the answer key.
- The agents explain and propose; people decide. No output leaves without analyst review.

## 4. The spine, lane by lane

Stages 1 and 2 are shared outright, and stage 6 shares its rules. Stages 3 to 7 run once per lane, and stage 4 is the only agentic stage in each.

| Stage | Scope | Briefing lane (B) | Forecast lane (F; 4b Proposed) |
| :- | :- | :- | :- |
| 1 Load and pin | Shared | Monday run for the latest closed week; run_id pins the data snapshot and the model, prompt and code versions | Same run_id discipline; also pins the forecast version (forecast_issue_week) and the actual release |
| 2 Validation gate | Shared | v_feed_health; failed cuts suppressed or qualified; restatements flow to disclosure | Same gate; a provisional actual pauses or qualifies attribution (FE-01 to FE-03) |
| 3 Detection | Per lane | 3a Competitive intelligence: governed KPIs, week over week, 4-week and same week last year; absolute, relative and z thresholds; top ~15 candidates | 3b Variance screen: signed V = A − F against the locked forecast, by territory and NATIONAL; or a manual request; materiality rule open (S7) |
| 4 Investigation | Per lane, Magentic | 4a Triage and investigation: manager, Data Forensics, Driver Investigator | 4b Forecast investigation: manager, Data and Version Forensics, Driver Attributor |
| 5 Drafting | Per lane | Monday brief: fixed template plus LLM prose with claim tokens | InvestigationReport: headline, attribution table with residual, what to check, caveats; brand-facing UI mock with a contribution waterfall |
| 6 Verification | Shared rules, lane checks | Tokens resolve; numbers reconcile to the snapshot; wording and HR checks; LLM judge | V = Σc + r within tolerance, run by code; citations resolve; no causal overclaim |
| 7 Review | Per lane | P1 reviews and edits; P2 signs off; P3 and P4 read | Commercial Analytics Analyst reviews; Brand Manager and Forecasting Manager, with Finance, read |

### 4a. Briefing investigation loop (B, unchanged)

The Briefing loop stays exactly as Briefing architecture Section 5.4 specifies it.

- Triage runs code rules first, then the manager, then P1 only when a call is flagged or uncertain.
- The manager keeps task and progress ledgers and reads episodic memory of prior stories.
- Data Forensics asks whether the data is wrong; the Driver Investigator tests access, promotion, competitor, mix and days-supply.
- Each hypothesis closes as supported, ruled out or insufficient evidence; each story closes with a label, a confidence level and what to investigate next.

### 4b. Forecast investigation loop (Proposed)

The Forecast lane keeps Alvin's tools, contract and modes, and wraps them in the same Magentic pattern. Today's planner becomes the manager. The five-step stub playbook stays as the scripted baseline, which also makes it the manager-off ablation. Alvin and Sienna decide whether to adopt it (S6).

| Part | Role in the loop | Carried over from the prototype (F) |
| :- | :- | :- |
| Manager (Magentic) | Keeps task and progress ledgers; orders hypotheses; decides when to stop, combine drivers or abstain | Investigator planner in Ollama mode; MAX_INVESTIGATOR_STEPS = 8 becomes the round cap |
| Data and Version Forensics | Is the miss real? Completeness, provisional actuals, restatements, forecast and actual version match | validate_and_quantify; feed checks shared with Briefing |
| Driver Attributor | What explains the miss beyond what the forecast expected? Localizes it, lists candidate events, runs exposed-versus-control contrasts, flags weak or contaminated controls | get_region_deltas, list_candidate_events, compare_exposed_control (difference-in-differences) |
| Reconciliation (code, not an agent) | Computes the residual so V = Σc + r; runs after the manager's final answer, never inside the model | reconcile_attribution, forced after final |
| Scripted baseline | Fixed five-step playbook; runs with no model server | Stub mode; Auto mode falls back to it |

When payer and competitor exposures overlap inseparably, the loop reports a combined contribution or abstains (FP attribution contract). Contaminated regions are excluded from each contrast, as the prototype does today.

### 4c. Loop guardrails, both loops (B Section 10.1, extended)

1. **Depth two.** The manager calls specialists; specialists never call an agent; tools hold no LLM.
2. **Finite search.** Each lane's hypothesis catalog lives in the semantic layer, and no test reruns with the same parameters.
3. **Caps as backstop.** Rounds, stalls, tool calls, wall time and tokens. Forecast's cap today is 8 steps; Briefing's values are Evaluation Pack open item 17.
4. **Defined exit.** A capped Briefing story closes as "unresolved, investigate next." A capped Forecast run sets abstained or marks the driver inconclusive. Neither output is ever blocked.
5. **Numbers belong to code.** Briefing fills claim tokens from evidence; Forecast forces reconciliation by tool. The model never types a figure.

## 5. Interface between the use cases

In v1 the two agents share a platform, not a runtime: neither calls the other. The seam is defined so either team can wire a handoff later without a redesign. Whether to wire one, and in which direction, is open (S1).

**Shared today.** The data world, the semantic layer, the tool-record rule, the eval harness and the governance rules (Section 3).

**Candidate handoffs, none committed.**

| Direction | What would cross | Possible trigger | Contract |
| :- | :- | :- | :- |
| Briefing to Forecast | A material weekly change in BXA TRx that matches a material forecast miss | A stage 3a candidate and a stage 3b flag on the same week and territory | forecast.InvestigationRequest with source: "briefing_agent", already in Alvin's schema |
| Forecast to Briefing | A closed forecast explanation for the week being briefed | A Forecast report exists for that brand and week | forecast.InvestigationReport, cited as one evidence item in a Briefing story or held in episodic memory |

If neither is adopted, each agent runs alone and each output stands on its own. The Briefing forecast_watchlist table stays parked; it is one form the first row could take.

**Contract rules, system-wide (F).**

- Renaming a request or report field is a contract version bump; new optional fields are allowed.
- Any payload that crosses carries its run_id, pinned data version and evidence references, so the receiver can trace it.
- Hidden ground truth never crosses.

## 6. Name collisions and vocabulary

Where both lanes use one word for different things, this doc qualifies it by lane instead of renaming either team's work. In shared docs and specs, prefix a colliding name with `briefing.` or `forecast.`.

| Term | Briefing meaning (B) | Forecast meaning (F, FP) | How shared docs write it |
| :- | :- | :- | :- |
| Investigation | Testing whether a material weekly change is real and what drives it | Explaining why actual TRx differed from the locked forecast | Briefing investigation; Forecast investigation |
| investigation_request / InvestigationRequest | Internal stage 4 handoff row (run_id × request_id) inside the Briefing agent | External JSON contract a caller sends to the Forecast agent | briefing.investigation_request; forecast.InvestigationRequest |
| investigation_result / InvestigationReport | Internal stage 4 output: driver findings, contributions, evidence references | The Forecast agent's final output contract | briefing.investigation_result; forecast.InvestigationReport |
| Manager / Investigator | Magentic manager inside stage 4a | Planner that picks tools, in Ollama or stub mode | Briefing manager; Forecast Investigator (its manager, if S6 is adopted) |
| Data Forensics | Agentic specialist | A tool step (validate_and_quantify) | Briefing Data Forensics; Forecast Data and Version Forensics |
| Evidence | evidence_items rows linked to spans | Tool records in the report's evidence log | See Section 3.3 |
| Confidence | High, Medium, Low (Low means abstain) | high, medium, low, inconclusive, plus an abstained flag | Per lane until S10 |
| Driver labels | access, promotion, competitor, segment or geography mix, days-supply | payer, competitor; inventory and seasonality optional | Per lane until S10 (Evaluation Pack open item 9) |
| Residual | Segment contributions sum to the total change | Signed residual r, with V = Σc + r | Per lane |
| Scripted baseline | "Scripted": fixed pipeline, also the manager-off ablation | BL-0 deterministic pipeline; stub mode | Same thing; both names kept |
| Baseline names | Manual, Scripted, Low-code, Custom agent | BL-0, BL-1, BL-2, optional human reference | Per lane |
| Eval and case IDs | EV-x.y; cases C-### | FE-xx; cases TC-## | Per lane; never reused across lanes |
| Failure tags | 12 lowercase tags, from "data misread" to "run error" | 8 uppercase families, from DATA / VERSION to WORKFLOW / GOVERNANCE | Per lane until S10 (Evaluation Pack open item 12) |
| Answer key | One record per injected event, 7 fields | One record per case, with identifiability fields | Per lane until S10 (Evaluation Pack open item 8) |
| Analyst persona | P1 Commercial Analyst | CA Commercial Analytics Analyst | Separate personas; not merged |
| Brand-lead persona | P3 Brand Director | BM Brand Manager | Separate personas; not merged |
| Stage 3 name | Competitive intelligence | Variance screen (New) | As written; "surveillance" retired (S8) |
| Spec 001 | None yet | specs/001-forecast-explanation-v1 | Namespaced per lane in one repo (S12) |

## 7. Stack by lane

Each lane's stack is valid where it runs. The repo fixes only the shared base: Python 3.11 or newer and DuckDB. Lane choices belong in each lane's plan.md, not in a constitution.

| Layer | Shared base (D) | Briefing (B) | Forecast (F) |
| :- | :- | :- | :- |
| Language | Python 3.11 or newer | Python; pandas or Polars, NumPy | Python package feagent |
| Storage and query | DuckDB 1.5.6 local file; raw, metadata, reporting schemas | Parquet + DuckDB | Observable case JSON today; DuckDB once ported (S3) |
| Statistics | None | SciPy, statsmodels; optional change-point library | Difference-in-differences in compare_exposed_control |
| LLM | None | Gemini API with function calling | Local Ollama (gpt-oss:20b on one machine) behind an LLMClient interface; OpenAI-compatible swap planned |
| Agent framework | None | Google ADK, custom Python or Microsoft Agent Framework (Briefing A3) | Custom Python; stub, auto and ollama modes |
| Contracts | None | Typed Pydantic/JSON or shared DuckDB tables | InvestigationRequest and InvestigationReport JSON; CLI python -m feagent.api |
| Configuration | Semantic layer, YAML + Pydantic (Section 3.2) | Same | Adds forecast metrics to it |
| Observability | None | OpenTelemetry, Arize Phoenix | Evidence log of tool records in each report |
| UI | None | Streamlit | Streamlit: KPIs, trend, attribution table, what to check, evaluator toggle |
| Tests and CI | unittest; GitHub Actions on Python 3.11 and 3.12 | pytest planned | pytest; must pass with no model server |
| Dev workflow | Spec Kit | Spec Kit in Antigravity | Spec Kit in Cursor |

Gemini is an external API, so Briefing prompts may carry only synthetic data and metric definitions. Ollama keeps Forecast local. Both meet the data-use rule; the review is S14.

## 8. Constitution and Spec Kit

Four principles already appear in both lanes and could form a shared project constitution; a fifth, abstention, is a Forecast article and a Briefing eval item. Each lane keeps everything else as its own articles. Whether to ratify a shared constitution is open (S11).

| Principle | Briefing candidate (B Section 2) | Forecast Constitution v1.0.0 (F) | Scope |
| :- | :- | :- | :- |
| Every number comes from a tool | #1 | Every number from a tool | Shared |
| Agents propose; people decide | #8 | Explain, never act | Shared |
| No tool can read the answer key | #11 | Hide ground truth | Shared |
| Typed contracts at every handoff | #6 | Stable JSON contract | Shared |
| Abstain when evidence is weak | Not an article; EV-5.2 and Low confidence | Abstain under weak evidence | Shared in practice |
| Synthetic data only; nothing proprietary to external models | #10 | Not an article; Proposal rule | Shared in practice |
| Semantic layer is the only source of definitions | #2 | Not an article | Briefing; shared once Forecast adopts 3.2 |
| Pin one data version per run | #4 | Not an article; FE-02 version alignment | Briefing; Forecast via eval |
| Deterministic, agentic or human by where the answer is knowable | #3 | Not an article | Briefing |
| Every step emits a span | #5 | Not an article | Briefing |
| Every loop ends by construction | #7 | Step budget in code | Both, at different strength |
| No line identifies a rep | #9 | Not an article | Briefing; data is aggregated at source for both |
| No merge if the eval suite regresses | #12 | Not an article | Briefing |
| Stub parity; tests pass with no model server; exact recovery on the reference case | Not an article | Article VI | Forecast; Alvin notes it must loosen for noise cases |

**Spec layout in one repo (Proposed).** Namespace specs by owner so numbers never collide (S12).

- `specs/core-###-*`: data generator and injection library, semantic layer, validation gate, tool interface and handoff contracts, run orchestrator, eval harness and tracing. Owners: both teams. The repo README's "Specs 002 to 004" for governed metrics and validation land here.
- `specs/brief-###-*`: competitive intelligence, triage with manager and specialists, narrative and renderer, verifier. Owners: Michael, Meghna.
- `specs/fcst-###-*`: Alvin's 001-forecast-explanation-v1 becomes fcst-001; later the variance screen, the Magentic loop if adopted, and the UI mock. Owners: Alvin, Sienna.
- `.specify/memory/constitution.md` holds only shared articles; each lane's own articles sit in its spec folder's README or a lane constitution.

## 9. Personas and evaluation, by reference

Each lane is judged by its own users and its own pack. This section only says where each lands in the system; nothing here changes either team's personas or items.

| | Briefing | Forecast |
| :- | :- | :- |
| Source | Briefing Agent Personas; Evaluation Pack (both Oct 21) | Forecast-Explanation Agent Personas and Evaluation Design (Oct 16) |
| Personas | P1 Commercial Analyst, P2 Insights Manager, P3 Brand Director, P4 Marketer | CA Commercial Analytics Analyst, BM Brand Manager, FM Forecasting Manager |
| Questions | 24, P1-Q1 to P4-Q6 | 18, CA-Q1 to FM-Q6 |
| Eval items | 37, EV-1.1 to EV-9.4 | 31, FE-01 to FE-31 |
| Test cases | Taxonomy of 7 categories; IDs C-### | 12 scenarios, TC-01 to TC-12 (TC-10 to TC-12 proposed) |
| Review gates | Two: P1 review, P2 sign-off | One: analyst review before distribution |
| Stage accountability | Briefing architecture Section 12 | Proposed below |

**Forecast stage accountability (Proposed; Sienna and Alvin confirm).** Capability groups are Sienna's traceability matrix.

| FE items | Capability (FP) | Accountable stage |
| :- | :- | :- |
| FE-01 to FE-03 | Input reliability and version validation | 1, 2; 4b Data and Version Forensics |
| FE-04 to FE-06 | Variance computation and localization | 3b; 4b Driver Attributor |
| FE-07 to FE-12 | Driver discovery, competing hypotheses, comparison validity | 4b |
| FE-13 to FE-18 | Attribution, reconciliation, residual, abstention | 4b and 6 |
| FE-19 to FE-21 | Traceability and reproducibility | 1, 6 and tracing |
| FE-22 to FE-25 | Follow-ups, forecast-review restraint, clarity, calibration | 5 and 6 |
| FE-26 to FE-29 | Latency, tool use, stability, adaptive value | Cross-cutting; 4b against the stub baseline |
| FE-30, FE-31 | Answer-key isolation, data governance | Cross-cutting |

**Parallel items, not merged.** Five pairs measure the same property in each lane, so one harness function can score both while each lane reports its own number: EV-2.1 and FE-01 (artifact catch), EV-6.2 and FE-20 (link resolution), EV-8.4 and FE-28 (run-to-run stability), EV-9.3 and FE-30 (answer-key isolation), EV-9.4 and FE-31 (data use).

## 10. System-level open items

Sixteen system decisions remain open; none blocks the data-layer specs or either lane's next build. Lane-internal items stay in each lane's own docs (Briefing A1 to A17; Evaluation Pack items 1 to 19).

| # | Open item | Section | Who resolves | Status |
| :- | :- | :- | :- | :- |
| S1 | Runtime handoff: whether to wire one, and in which direction | 5 | All four | Open |
| S2 | Proposal amendment: one orchestrator and a Magentic loop per lane, not one manager over both; supersedes Briefing A2 | 3.4 | Dr. Admasu | Open |
| S3 | One world: port the LUMINA Week 18 reference case into the repo world; update Briefing architecture Section 8 to 8 territories, 4 regions, 4 specialties and monthly plan-level access | 3.1 | Alvin; Michael | Open |
| S4 | Restatement window: the repo restates week 2026-04-06 on 2026-07-13, 14 weeks later; Briefing proposes 3 weeks (Evaluation Pack item 18) | 3.1 | Meghna, Michael | Open |
| S5 | Inventory as a Briefing driver: inventory_weekly exists, but Briefing's driver list omits it | 3.1 | Michael, Meghna | Open |
| S6 | Adopt the Magentic loop for Forecast | 4b | Alvin, Sienna | Proposed |
| S7 | Stage 3b: what triggers a forecast investigation, and the materiality rule for a miss | 4 | Alvin, Sienna | Open |
| S8 | Retire "surveillance" in the repo README, the data README and the Proposal; extends Briefing A14 | 6 | Meghna, Michael | Open |
| S9 | One record shape for Briefing evidence items and Forecast tool records | 3.3 | Both teams | Open |
| S10 | Shared vocabulary: confidence scale, driver labels, failure tags, answer-key format (Evaluation Pack items 8, 9, 12) | 6 | Both teams | Open |
| S11 | A shared project constitution, or per-lane constitutions only | 8 | Both teams | Open |
| S12 | Spec namespaces core, brief and fcst in one repo | 8 | Both teams | Proposed |
| S13 | The repo still has folders and README text for the payer-access and HCP next-best-action agents the Proposal dropped | 1 | All four | Open |
| S14 | Data-use review per LLM provider: Gemini external, Ollama local | 7 | All four; Dr. Admasu | Open |
| S15 | Test runner and CI: unittest in the repo, pytest in Forecast and in Briefing's plan | 7 | Both teams | Open |
| S16 | Where Forecast code lives: feagent moved into agents/forecast-explanation, or a separate repo | 7 | Alvin, Sienna | Open |

## 11. Decision log

Eight decisions shaped this doc, all on 2026-10-22. Each later change adds a row.

| # | Decision | Source | Reason |
| :- | :- | :- | :- |
| D1 | The Briefing architecture's seven-stage spine is the system template | User | Judged the strongest of the designs on hand |
| D2 | Stages 3 and 4 are doubled, one per lane; the Magentic loop is proposed for Forecast | User | Forecast's open-ended investigation fits the same pattern |
| D3 | Personas and evaluation stay per use case, referenced by ID, never merged or edited | User | Same titles apply differently in each lane |
| D4 | Runtime handoff is left open; the seam and its contract rules are defined | User | No overlap is proven yet |
| D5 | Name collisions are qualified by lane, not renamed | User | Neither team's work is edited |
| D6 | Stacks, constitutions and vocabulary are recorded side by side per lane | User | Each is valid where it runs |
| D7 | The repo's data foundation is the one shared data world | User | It is merged, tested and built for both agents |
| D8 | Stage 3b is named "variance screen" | New | Gives the Forecast lane a detection stage parallel to competitive intelligence |
