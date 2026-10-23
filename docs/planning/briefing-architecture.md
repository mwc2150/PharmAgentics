<!-- Markdown copy of the Google Doc "Architecture 10/21" (Briefing Agent Architecture SoT), taken 2026-10-23. The Google Doc is the master; update it first. Precedence: below the System Architecture (docs/planning/system-architecture.md) for anything shared; this doc governs the Briefing lane's internals. Diagram: pharmagentics_architecture_10/21.png in Drive. -->

# PharmAgentics — Briefing Agent Architecture (SoT)

Oct 16, 2026 (updated Oct 21) · @Michael

This doc is the single architecture reference for the Weekly Brand-Performance Briefing Agent. It merges the Briefing Agent Roadmap (Michael) and the PharmAgentics Operation Flow (Meghna). Spec Kit's constitution, specs and plans cite it.

## 1. Purpose, precedence and merge rules

**Precedence.**

1. Project SoT: the Proposal, the Briefing Agent Personas and the Evaluation Pack.
2. This doc.
3. The Briefing Agent Roadmap and the Operation Flow, kept as history.

Where this doc departs from the Proposal, the departure is logged in Section 16 and confirmed with Dr. Admasu.

**Merge rules.**

| Case | Rule |
| :-: | :-: |
| Both docs specify it and agree | Kept |
| One doc specifies it; the other is silent | The specifying doc's element is kept |
| Both specify it, differently | Resolved and logged in Section 16 |
| Neither specifies it, but the Personas or Evaluation Pack require it | Added, tagged SoT |
| Still undecided | Marked [NEEDS CLARIFICATION: …] and listed in Section 15 |

**Source tags.** Tables carry a Source column: R = Roadmap, O = Operation Flow, R+O = both, SoT = required by the Personas or Evaluation Pack, New = added in this merge.

**Scope.** Briefing Agent only. The Forecast-Explanation Agent is a separate use case. The two share a data world, not a runtime.

**Terms.**

- **Investigation (Briefing):** testing whether a material weekly change is real and what drives it. It happens inside this agent.
- **Investigation (Forecast):** explaining forecast-versus-actual variance. It belongs to the Forecast-Explanation Agent and is out of scope here.
- **Competitive intelligence:** the name of the change-detection stage, per the mentor. "Statistical surveillance" is not used in this or any project doc.

## 2. Design principles

Twelve principles bind every component. They are the candidate articles for the Spec Kit constitution.

| # | Principle | Source |
| :-: | :-: | :-: |
| 1 | Every number in an output comes from a tool. The LLM never computes and never types a digit. | R+O |
| 2 | The semantic layer is the only source of metric definitions, dimensions and thresholds. | R+O |
| 3 | Deterministic where the answer is knowable, agentic where the path is not, human where the judgment stays uncertain. | R, extended |
| 4 | Every run pins one data version. Every claim reconciles to that version and links to it. | O, SoT |
| 5 | Every step emits a span. Every claim links to the evidence and the span that produced it. | R+O |
| 6 | Stages hand off through typed contracts, not free-form agent conversation. | O |
| 7 | Every agentic loop ends by construction. Caps are the backstop; a capped story closes as "unresolved, investigate next." | R, SoT |
| 8 | The agent proposes; people decide. No brief leaves without analyst review and manager sign-off. | R+O, SoT |
| 9 | No line in a brief identifies an individual rep. | SoT |
| 10 | No patient or proprietary data goes to an external model; all data is synthetic. | R+O |
| 11 | No agent tool can read the answer key. | R |
| 12 | No change merges if the evaluation suite regresses. Eval items live in the Evaluation Pack. | R, SoT |

## 3. System context and scope

One Monday run turns last week's commercial data for one fictional brand into a brief the analyst and the manager have approved.

| Aspect | Definition | Source |
| :-: | :-: | :-: |
| Trigger | Monday run for the latest closed week | R+O |
| History | Two years of weekly data; the window moves forward one week per run (Nov 2024 to Oct 2026 at launch) | R, SoT |
| Unit of work | One brand, one reporting week, one run_id | O |
| Output | A Monday brief with clickable evidence, approved by the analyst and signed off by the manager | R+O, SoT |

**Users.**

| Persona | Role in the run | What the architecture owes them |
| :-: | :-: | :-: |
| P1 Commercial Analyst (Ace) | First reviewer; edits the draft; reviews triage when it is flagged | A draft already reconciled, one-click tracing, data problems surfaced before drafting |
| P2 Insights Manager (Marcus) | Signs off before the brief leaves the team | Artifacts separated from real change, alternatives on record, honest confidence, an audit trail |
| P3 Brand Director (Diana) | Reads the approved brief only | Changes ranked by impact, plain explanations, next steps and who to involve |
| P4 Marketer (Magdalena) | Reads the approved brief only, after P2 signs off | Promotion tested as one driver with a verdict either way, changes located by geography, promotion activity next to performance, no rep-level lines |

Finance, market access and sales operations are named in the brief as functions to involve. They are not users of the agent.

**Boundary with the Forecast-Explanation Agent.**

- **Shared:** the synthetic generator (one brand world), the semantic-layer files and the tracing conventions.
- **Not shared at runtime:** no handoff between the agents in v1. The Roadmap's forecast_watchlist table is parked. [NEEDS CLARIFICATION: revisit with Alvin and Sienna]
- **To agree with the Forecast team:** answer-key format, driver labels, held-out seed swap and failure tags (Evaluation Pack Open items 8 to 12).

**Amendment to the Proposal.** The Proposal describes one Magentic manager over both agents. This doc runs Magentic inside the briefing use case only, with no runtime routing between the agents, because the two use cases have different triggers and stakeholders. [NEEDS CLARIFICATION: confirm with Dr. Admasu]

## 4. Architecture overview

Seven stages run in a fixed order. Only stage 4 holds an agentic loop, and people gate stages 4 and 7. The Operation Flow's run states form the outer spine; the Roadmap's Magentic loop sits inside stage 4.

*(Diagram in the Google Doc: Briefing Agent architecture · 7 stages, 1 agentic loop.)*

Runs with no material change skip stage 4 and go straight to the narrative; every brief still passes verification and two-person review.

| # | Stage | What it does | Mode | Roadmap step | Op Flow step | Main output |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 1 | Load and pin | Loads the week with two years of history; pins data, model, prompt and code versions | Code | 1 | 1 | run_registry row |
| 2 | Validation gate | Checks feeds and cuts before any interpretation | Code | 2 | 2 + "data reliable?" | Health report: pass, warn or fail per cut |
| 3 | Competitive intelligence | Computes governed KPIs and flags material changes | Code | 3 | 3, 4 + "material change?" | candidate_changes |
| 4 | Triage and investigation | Decides what to investigate, then tests whether each story is real and why | Code + LLM + human by exception; Magentic loop | 4 | 5, 6, 7 | stories, hypotheses, investigation_result |
| 5 | Narrative | Writes the brief from the closed evidence | LLM, constrained | 5 | 8 | Draft with claim tokens |
| 6 | Verification | Checks numbers, evidence, wording and governance | Code + LLM judge | 6 | 9 | brief_claims with verification status |
| 7 | Review, publish and feedback | Analyst review, manager sign-off, edit capture | Human | 7 | 10, 11, 12 | analyst_review, published brief, failure tags |

Five controls cut across every stage: the semantic layer, typed handoff contracts, tracing and provenance, held-out evaluation, and human approval.

The two source docs describe stage 4 from opposite sides. The Operation Flow describes its outside: a request goes in, a result comes out. The Roadmap describes its inside: the manager, the specialists and the ledgers. This doc keeps both.

## 5. Stage specifications

Each stage lists its behavior with source tags, its failure path and its run states. Section 12 maps every stage to the persona questions and eval items it answers for.

### 5.1 Load and pin

Each run loads the latest closed week and pins everything it reads.

- Assign a run_id. Record the week, state, timestamps, and data, model, prompt and code versions in run_registry. (O)
- Load two years of history for baselines and same-week-last-year comparisons. (R)
- Store each weekly pull as an immutable snapshot. The run pins one snapshot, and every later claim reconciles to it. (O, SoT)
- Restatement window: 3 weeks. Weeks restated inside the window are flagged, never silently overwritten or double-counted. (R, SoT) This is the proposed answer to Evaluation Pack Open item 18.
- State: LOADED.

### 5.2 Validation gate

Checks run per feed and per cut before any metric is interpreted.

- Checks: schema and types, missing sources, row counts against the trailing average, duplicate keys, panel coverage, freshness and reporting lag, and the restatement diff against the previous pull. (R+O)
- Output: a health report with pass, warn or fail per cut. (R)
- On warn or fail, affected cuts are suppressed or visibly qualified. The brief leads with the cuts that are not reliable and reports the rest. (R+O)
- Restatements found here flow to the narrative, which states the old and new values. (SoT)
- [NEEDS CLARIFICATION: behavior when every cut fails; proposal: publish a data-health notice only]
- States: VALIDATED, VALIDATION_WARNING, VALIDATION_FAILED.

### 5.3 Competitive intelligence

This stage turns validated data into governed KPIs and a ranked list of material changes.

- Compute the governed KPIs: TRx, NRx, NBRx, TRx in 30-day equivalents, market share and NBRx share. (R+O)
- Normalize TRx to 30-day equivalents before detection, so a 30- to 90-day conversion is not read as a drop. (R)
- Compare each metric and cut week over week, against the 4-week average, and against the same week last year. (R+O)
- Score robust z-scores on residuals after removing seasonality with time-series decomposition. (R+O)
- Flag a change only if it clears the semantic layer's absolute, relative and statistical thresholds. (R+O)
- Rank flagged changes by business impact and cap the list at about 15 candidates. (R+O)
- [NEEDS CLARIFICATION: definition of business impact, shared with the answer key; proposal: absolute change in TRx 30-day equivalents]
- [NEEDS CLARIFICATION: multiple-testing control. About 1,800 leaf-level tests a week can raise dozens of chance flags per null week before the filters. Options: hierarchical drill-down or false-discovery-rate control, tuned on dev null weeks.]
- With no candidates, the run enters ROUTINE. The routine brief still passes through stages 5 to 7.
- States: ROUTINE, or on to stage 4.

### 5.4 Triage and investigation

Stage 4 decides which changes deserve investigation, then runs a bounded Magentic loop on each story. Its outside is a typed request and result (O); its inside is the manager and two specialists (R).

**Handoff in (O).** Code builds an investigation_request: candidate IDs, metric and cut, magnitude, baseline, historical context, evidence IDs and the health report. Constraint: whatever component groups candidates into stories must see every candidate of the run together, or compound and masked weeks go unseen (EV-4.4). Proposal: one request per run.

**Triage.** The decision to investigate is a hybrid of code, LLM and human review. No single layer owns it.

| Layer | Decides | Examples | Source |
| :-: | :-: | :-: | :-: |
| Code | Calls a rule can make | Drop candidates on cuts that failed validation; tag calendar weeks; link candidates to stories already resolved in episodic memory; suggest groupings by shared cut and timing | New, built on R and O rules |
| LLM (manager) | Judgment calls | Group candidates into stories; choose which stories to investigate and in what order; set first hypotheses | R |
| Human (P1) | Calls that are flagged or uncertain | Approve or edit the triage plan when code and manager disagree or the manager marks low confidence, through Magentic plan review | User decision, 2026-10-16; R |

Human review here is by exception, so P1 reviews output, not every input. [NEEDS CLARIFICATION: the decision junction: which calls are code, which are LLM, and what flags human review]

**The Magentic loop (R).**

- The manager keeps a task ledger (known facts, facts to look up, hypotheses) and a progress ledger (done, looping, who acts next). Both are logged as spans, so a reviewer can replay the reasoning.
- Each story goes to **Data Forensics** first: is the data wrong for this change? It checks feed metadata, restatements, panel coverage, the holiday calendar and days-supply mix.
- Then to the **Driver Investigator**: what is causing it? It tests access, promotion, competitor, segment or geography mix, and days-supply shift. Promotion gets a verdict either way, so a lift is not credited to the latest campaign when another driver explains it (EV-4.5).
- Each hypothesis gets a verdict: supported, ruled out, or insufficient evidence, with tool outputs attached.
- A contribution decomposition shows how much each segment or region adds to a national change. Contributions sum to the total.
- Each story closes with a label (real change, data artifact or calendar effect), a confidence level, a leading driver or none, the alternatives ruled out, what to investigate next, and which function to involve. (R, SoT)
- Confidence: High means one explanation is supported and the others ruled out. Medium means one is supported and alternatives stay open. Low means the agent abstains and lists the story under "investigate next." (R) This is the proposed answer to Evaluation Pack Open item 3.
- Episodic memory holds recent briefs and resolved anomalies, so a known event is not "discovered" again and continuity can be stated. (R) It is built as a query over prior runs' stories and brief_claims, not a separate store. (New)
- Tools: get_metric, decompose_change, validate_feed, lookup_access_events, lookup_promo, compare_competitors, lookup_calendar, reconcile_numbers. They are typed and bound to semantic-layer metric IDs; an unknown ID returns an error the manager must handle. (R) Rep-level data is aggregated inside the tools before any agent sees it. (SoT)
- Loop guardrails are in Section 10.

**Handoff out (O).** An investigation_result carries driver findings, contributions, confidence, uncertainty and evidence references, plus the story and hypothesis records. Only this closed evidence pack reaches the narrative. (R+O)

States: INVESTIGATION_REQUESTED, TRIAGE_REVIEW, INVESTIGATING, EVIDENCE_RECEIVED.

### 5.5 Narrative

The LLM writes prose around numbers it cannot type.

- Fixed template: KPI table filled by code; what changed, ordered by impact; is it real; likely drivers with confidence; investigate next and who to involve; promotion activity next to performance for stories where promotion was tested (EV-7.5); data-health footnote; restatement disclosure; glossary generated from the semantic layer. (R, SoT)
- The LLM writes claim tokens such as {{c17}}, and a renderer swaps in values from the evidence pack. (R)
- The LLM reads only the closed evidence pack and the definitions of the metrics in play. (R+O)
- Reader-facing text follows ASD-STE100: short sentences, one word with one meaning, paired with business framing for tone. (SoT)
- No line identifies an individual rep. "New patients" is used only for NBRx. (R, SoT)
- [NEEDS CLARIFICATION: the template and length a real brand team uses; Evaluation Pack Open item 4]
- State: DRAFTED.

### 5.6 Verification

Nothing reaches a reviewer without passing these checks or carrying visible flags.

- **Code checks (R+O):** every claim token resolves; any digit not from a token fails the brief; every number reconciles to the pinned snapshot after stated rounding; every story cites at least one evidence item; wording matches the semantic layer.
- **Governance checks (SoT):** no line identifies a rep; banned terms are absent, including "statistical surveillance" and "new patients" for NRx.
- **Judge checks (R+O):** faithfulness and overclaiming; causal words only at High confidence. The judge is used only after its agreement with human labels is measured (Evaluation Pack Open item 2).
- **Failure path (R):** one revision loop back to stage 5. If the brief still fails, it goes to review with its flags visible.
- States: VERIFIED, VERIFICATION_FLAGGED.

### 5.7 Review, publish and feedback

Two people approve every brief, and every correction becomes data.

- P1 reviews the draft with clickable evidence and edits it. (R+O)
- P2 signs off before the brief leaves the team. (SoT) [NEEDS CLARIFICATION: does sign-off sit with P2 or one level higher; Personas to-do]
- Every edit and runtime failure gets one failure tag. Repeated corrections become new eval cases. (R+O)
- [NEEDS CLARIFICATION: the path when P2 returns a brief; proposal: back to stage 5 with comments]
- States: IN_REVIEW, PUBLISHED, RETURNED.

## 6. Run states

A run moves through sixteen states, and each transition is logged against its run_id. The Operation Flow's eight states are kept; the rest come from Roadmap behavior, the Personas or this merge.

| State | Meaning | Next | Source |
| :-: | :-: | :-: | :-: |
| LOADED | Data and versions pinned to the run_id | VALIDATED, VALIDATION_WARNING, VALIDATION_FAILED, RUN_ERROR | O |
| VALIDATED | Required checks passed for the cuts entering detection | ROUTINE, INVESTIGATION_REQUESTED | O |
| VALIDATION_WARNING | Some cuts unreliable; their outputs suppressed or qualified | ROUTINE, INVESTIGATION_REQUESTED | O |
| VALIDATION_FAILED | Every cut failed | DRAFTED as a data-health notice [NEEDS CLARIFICATION] | R |
| ROUTINE | No material change | DRAFTED | O |
| INVESTIGATION_REQUESTED | Material changes packaged into a typed request for stage 4, inside this agent | TRIAGE_REVIEW, INVESTIGATING | O, reworded |
| TRIAGE_REVIEW | Triage flagged or uncertain; waiting for P1 | INVESTIGATING | New (user decision) |
| INVESTIGATING | Magentic loop running under its caps | EVIDENCE_RECEIVED | R |
| EVIDENCE_RECEIVED | investigation_result closed and linked to the run | DRAFTED | O |
| DRAFTED | Narrative written with claim tokens | VERIFIED, VERIFICATION_FLAGGED | New, from R |
| VERIFIED | Claims passed numeric, semantic, governance and evidence checks | IN_REVIEW | O |
| VERIFICATION_FLAGGED | Still failing after one revision; flags visible | IN_REVIEW | R |
| IN_REVIEW | P1 review, then P2 sign-off | PUBLISHED, RETURNED | SoT |
| RETURNED | P2 sent the brief back | DRAFTED [NEEDS CLARIFICATION] | New |
| PUBLISHED | Approved brief released; feedback captured | End | O |
| RUN_ERROR | A tool, data or model failure stopped the run | End; alert and rerun | New |

## 7. Data model

The data has three layers: the semantic layer defines the terms, the commercial tables hold the brand world, and the runtime objects record each run. Field names follow Meghna's data dictionary.

### 7.1 Semantic layer

The semantic layer is a set of versioned YAML files validated by Pydantic. Tools reject any metric ID it does not hold. (R+O)

- **Metrics:** TRx, NRx, NBRx, TRx in 30-day equivalents, market share, NBRx share. Business impact is added once defined.
- **Dimensions:** week; geography (region to territory); payer channel (commercial, Medicare Part D, Medicaid, cash); HCP specialty.
- **Business rules:** materiality thresholds per metric, the market basket with effective dates, the holiday calendar, formulary plan-year resets.
- **Data contracts:** source table, lag, restatement window, owner.
- **Readers:** tools validate every metric ID and dimension; prompts receive only the definitions in play; the verifier checks wording per metric; each brief gets a generated glossary; the Forecast team adds its metrics to the same files.
- Seeded from the course's Week 02 Claims Data Field Guide. Heavier tooling (dbt, MetricFlow) only if needed. (R)

One entry, thresholds illustrative (R):

```yaml
metric: nbrx
label: New-to-brand prescriptions
definition: Rx for patients new to this brand in the lookback window (new to market, switches, add-ons)
not_to_be_confused_with: [nrx]   # NRx also counts new Rx numbers for continuing patients
grain: week × geography × payer_channel × hcp_specialty
source: rx_weekly.nbrx
lineage: generator v1 → calibrated to CMS Part D prescriber mix
refresh: weekly, 1-week lag, restatable for 3 weeks
materiality: {abs_min: 50, rel_min: 0.05, z_min: 2.0}
allowed_phrases: ["new-to-brand", "new patient starts"]
owner: Meghna
```

### 7.2 Commercial and context tables

These are the only tables agent tools can read.

| Table | Grain | Key fields | Feeds | Source |
| :-: | :-: | :-: | :-: | :-: |
| rx_weekly | week × territory × payer_channel × hcp_specialty × product | TRx, NRx, NBRx, TRx 30-day equivalent, days-supply mix | Detection, share, decomposition, competitor comparison | R+O |
| market_basket | product × effective dates | in_basket_flag, effective_start, effective_end | Share denominator; competitor launches | R+O |
| access_status | plan × product × effective date | covered, PA, step edit, not covered; covered lives | Access hypotheses | R |
| promo_activity | week × territory | rep calls, samples, speaker programs, digital, rep vacancy | Promotion hypotheses; aggregated before any agent reads it. Channel spend, reach and consumer campaigns for P4 [NEEDS CLARIFICATION: A16] | R |
| feed_metadata | week × source | load time, row count, panel coverage, schema version, restatement flag | Validation gate, Data Forensics | R+O |
| calendar | week | holiday flag, business days, plan-year reset | Baselines, calendar effects | R+O |
| geography | territory | region | Rollups, concentration; NY metro boroughs if adopted (A17) | New [NEEDS CLARIFICATION] |

### 7.3 Runtime, handoff, evidence and review objects

These objects make each run reproducible and each claim traceable.

| Object | Grain | Key fields | Use | Source |
| :-: | :-: | :-: | :-: | :-: |
| run_registry | run_id | week, current_state, timestamps, data/model/prompt/code versions, pinned snapshot | One reproducible record per run | O |
| candidate_changes | run_id × candidate_id | metric_id, cut, actual, baseline, absolute and relative change, anomaly score, business impact | Stage 3 output | O |
| investigation_request | run_id × request_id | candidate IDs, metric and cut, magnitude, baseline, historical context, evidence IDs, health report | Typed handoff into stage 4 | O |
| story | run_id × story_id | candidate IDs, label, confidence, leading driver, continuity, investigate next, function to involve, closure reason | The unit the brief reports | New, SoT |
| hypothesis | run_id × story_id × hypothesis_id | driver, parameters, verdict, evidence IDs | Alternatives tested and ruled out | New, SoT |
| investigation_result | run_id × request_id | driver findings, contributions, confidence, uncertainty, evidence references | Typed handoff out of stage 4 | O |
| evidence_items | run_id × evidence_id | source tool, parameters, result, source reference, span ID | Claim provenance | O |
| brief_claims | run_id × claim_id | claim token, claim text, evidence IDs, confidence, verification status | Links the narrative to evidence; feeds episodic memory | O, R |
| analyst_review | run_id × reviewer_role | reviewer role (P1 or P2), decision, edits, comments, timestamp, failure tag | Two-gate review and the failure catalog | O, SoT |
| answer_key | event_id | event type, affected cut, start week, magnitude, duration or decay, label | Eval harness only, in a separate store | R+O |

## 8. Synthetic data world

*(Superseded for the shared world by System Architecture §3.1 and open item S3: the repo's data foundation, seed 7, 8 territories in 4 regions, 4 specialties, monthly plan-level access. The text below is the Oct 21 original.)*

A seeded Python generator builds one fictional brand world, injects labeled events into it, and logs them to an answer key the agent cannot read. (R)

- Claude writes the generator code; NumPy seeds produce the data, so every dataset is reproducible from its seed. LLM output is not reproducible from a seed; code is.
- **World:** one brand in a crowded primary-care class with three competitors; two years of weekly history; about 50 territories in 10 regions; four payer channels; three HCP specialties.
- **Injection library:** each event's magnitude, onset lag and decay are drawn from ranges by seed and logged to the answer key. Event categories and examples are in Evaluation Pack Section 4.
- **Calibration:** CMS Medicare Part D Prescribers by Provider and Drug sets regional distribution, specialty mix and scale. The CMS Monthly Part D Formulary files set how often products face PA or step edits. openFDA NDC gives package sizes for the 30- to 90-day conversion. Weekly noise and seasonality are set by judgment, documented, and reviewed with Dr. Admasu.
- **Splits, gold briefs and held-out rules:** Evaluation Pack Section 7.
- [NEEDS CLARIFICATION: the therapeutic class to mimic for calibration]

## 9. Autonomy ledger

The agent does more than a script in four places: grouping stories, choosing and ordering hypotheses, choosing test parameters, and deciding when to stop or abstain. Everything else is code or a person, and the ledger says which. (R, updated for triage)

| Component | Mode | Why | Evidence we show |
| :-: | :-: | :-: | :-: |
| Data pull and validation gate | Deterministic | The checks are knowable rules | Unit tests; injected-artifact catch rate |
| Competitive intelligence | Deterministic | Statistics plus semantic-layer thresholds | Detection precision and recall |
| Triage: what to investigate and how to group it | Hybrid: code, then manager, then P1 by exception | Some calls are rules, some are judgment, and uncertain ones go to a person | Share of calls made by each layer; triage traces against the scripted baseline |
| Choosing and ordering hypotheses | Agentic (manager) | The path differs by case | Tool sequences that vary sensibly by case |
| Hypothesis tests | Code, with LLM-chosen parameters | The math is code; what to test is not | Parameter-extraction accuracy |
| Stop or abstain | Agentic, bounded by caps | Is the evidence sufficient? | Abstention calibration |
| Narrative | LLM, constrained | Prose only; numbers are tokens filled by code | 100% numeric reconciliation |
| Verifier | Code plus LLM judge | Code checks numbers; the judge checks overclaiming | Judge agreement with human labels |
| Flagged actions | LLM proposes, people decide | The agent never acts outside the brief | Human-in-the-loop log |

**Answering "is it really a script?"** Two pieces of evidence carry the answer.

- **Trajectory diversity:** tool sequences vary by case in ways that track the case. Where they diverge from the scripted baseline, the agent scores better on the Explanation and Calibration items (EV-4.x, EV-5.x).
- **Manager ablation:** the scripted baseline uses the same tools, narrative and verifier as the agent and replaces only the manager with a fixed order of checks. That makes it the manager-off ablation. (New; proposed answer to Evaluation Pack Open item 16)

The more triage moves to code or to people, the more the claim rests on the investigation loop itself. That loop has to show its value on its own.

## 10. Guardrails and governance

### 10.1 Loop guardrails

The Magentic loop cannot recurse by construction and cannot iterate without end; the caps are only the backstop. This answers the mentor's concern about runaway recursion.

1. **No recursion by construction.** Two levels only: the manager calls specialists; specialists cannot call the manager, each other, or new agents; tools are plain functions with no LLM inside. Call depth is fixed at two. (New, from R's structure)
2. **Finite search space.** Hypotheses come from a fixed catalog in the semantic layer: driver categories, artifact types and calendar effects. The task ledger refuses to rerun a test with the same parameters, so each story has a finite set of possible tests. (New)
3. **Caps as backstop:** rounds per run; stalls (rounds with no new verdict); tool calls per story; Data Forensics calls per story (the Personas' "data-check loop"); wall-clock time; token budget; brief length. (R, SoT) [NEEDS CLARIFICATION: values; Evaluation Pack Open item 17]
4. **Defined exit.** Hitting any cap closes the story as "unresolved, investigate next" and keeps the evidence gathered so far. The run continues to stage 5, so the Monday brief is never blocked. (R, SoT)
5. **A test that tries to break it.** A stress case built to provoke looping, such as evidence that conflicts across sources. Traces must show the loop exited through rule 2 or 3, not by timeout. (New)

### 10.2 Governance rules

| Rule | Where it is enforced | Source |
| :-: | :-: | :-: |
| No individual identification: rep calls and vacancies aggregated or suppressed [NEEDS CLARIFICATION: minimum aggregation level; Evaluation Pack Open item 5] | Tools (stage 4), verifier (stage 6) | SoT |
| Governed terminology: wording follows the semantic layer; "competitive intelligence," never "statistical surveillance" | Prompts (stage 5), verifier (stage 6), every project doc | SoT |
| Causal wording only at High confidence | Verifier (stage 6) | R |
| Answer-key isolation: no tool can query answer_key; separate store; tool allowlist in the spec | Tool layer, storage | R |
| Data use: synthetic data only; no patient or proprietary data to external models | Data inventory review | R+O |
| The agent proposes; people decide | Stage 4 (triage by exception), stage 7 | R+O, SoT |

### 10.3 IQVIA principles

| Principle | Implementation |
| :-: | :-: |
| Protect the foundation | Versioned semantic layer and data contracts; the generator has its own spec |
| Make data explainable | Glossary in every brief, lineage on every metric, provenance on every claim |
| Govern decisions, not just data | Autonomy ledger; the agent proposes and people decide; causal wording gated by confidence |
| Embed trust into workflows | The analyst's Monday format; evidence one click away; triage review when flagged |
| Scale responsibly | Synthetic data only; prompts and models versioned; eval gate before merge |

## 11. Observability

Every step emits an OpenTelemetry span viewed in Arize Phoenix, and every number in the brief links to the span that computed it.

- Spans on every tool call, agent turn and LLM call. (R+O)
- Span attributes: run_id, seed, week, metric ID, story ID, agent name, ledger snapshot, tokens, cost, latency, handoff state, failures. (R+O)
- Claim provenance: claim token to evidence item to span. Clicking a number in the brief opens its span. (R+O)
- Phoenix experiments compare the manual, scripted, low-code and custom-agent versions on the same cases, so regressions show before merge. (R)
- Run-to-run variance is reported, not hidden. (R, SoT)

## 12. Evaluation linkage

The Evaluation Pack decides what is measured. This section says which stage is accountable when an item fails, so a failure tag points to the right component. Eval items still score the brief as black-box tests.

| Stage | Persona questions | Accountable for |
| :-: | :-: | :-: |
| 1 Load and pin | P1-Q1, P1-Q2, P2-Q5 | EV-2.4, EV-6.2 |
| 2 Validation gate | P1-Q2, P2-Q1 | EV-2.1, EV-2.3, EV-1.2 (detecting the restatement) |
| 3 Competitive intelligence | P1-Q3, P1-Q5, P3-Q1, P3-Q2 | EV-3.1, EV-3.2, EV-3.3, EV-3.4 |
| 4 Triage and investigation | P2-Q1, P2-Q2, P2-Q3, P2-Q4, P3-Q4, P4-Q1, P4-Q2, P4-Q4, P4-Q5 | EV-2.2, EV-4.1 to EV-4.5, EV-5.1, EV-5.2, EV-5.4, EV-7.2, EV-8.5 (rounds) |
| 5 Narrative | P1-Q6, P3-Q3, P3-Q5, P3-Q6, P4-Q3, P4-Q6 | EV-1.1 (tokens), EV-1.2 (disclosure), EV-1.3, EV-7.1, EV-7.3, EV-7.4, EV-7.5, EV-8.5 (length) |
| 6 Verification | P1-Q1, P1-Q4, P2-Q5, P3-Q6 | EV-1.1 (the gate), EV-5.3, EV-6.1, EV-9.1, EV-9.2 |
| 7 Review and feedback | P1-Q6, P2-Q6 | EV-6.3, EV-8.1 |
| Cross-cutting | P1-Q4, P2-Q5, P2-Q6 | EV-8.2, EV-8.3, EV-8.4, EV-9.3, EV-9.4 |

All 24 persona questions and all 37 eval items land on at least one stage.

**The Operation Flow's runtime metrics,** mapped to where they now live:

| Operation Flow metric | Now lives in |
| :-: | :-: |
| Validation catch rate | EV-2.1 |
| Material-event recall | EV-3.1 |
| Null-week false-alarm rate | EV-3.2 |
| Escalation precision | Component spec: competitive intelligence (white-box) |
| Handoff completeness | Component spec: tool interface and handoff contracts (white-box) |
| Narrative reconciliation | EV-1.1 |
| Evidence-grounded claim rate | EV-6.1 |
| Operational efficiency | EV-8.2 |
| Human correction rate | EV-8.1 |
| Run-to-run stability | EV-8.4 |

**White-box tests owed by component specs.** Per the Evaluation Pack's black-box rule, these live in each spec's tasks.md:

- Tool unit tests and schema checks: 100% pass. (R)
- Router: tool choice, parameter extraction (≥ 95% correct parameters, proposed), and convergence: steps to an answer and spread across reruns. (R)
- Escalation precision and handoff completeness. (O)
- Judge agreement with human labels (Evaluation Pack Open item 2). (R)
- Loop guardrails: call depth, the no-repeat rule, and each cap's exit path. (New)
- Validation gate: catches each seeded artifact type on dev seeds. (R)

## 13. Technology stack

The stack comes from the Operation Flow. It belongs in plan.md's Technical Context, not in specs or the constitution.

| Layer | Choice | Source |
| :-: | :-: | :-: |
| Storage and query | Parquet + DuckDB | O |
| Data processing | Python, pandas or Polars, NumPy | O |
| Competitive-intelligence statistics | SciPy, statsmodels; optional change-point library | O |
| Agent reasoning and narrative | Gemini API with function calling | O |
| Agent implementation | Google ADK or custom Python, implementing the Magentic pattern [NEEDS CLARIFICATION: framework; the Proposal cites Microsoft Agent Framework's Magentic orchestration] | O, R |
| Handoff interface | Typed Pydantic/JSON contracts or shared DuckDB tables | O |
| Configuration | YAML + Pydantic semantic layer and data contracts | R+O |
| Observability | OpenTelemetry; Arize Phoenix | R+O |
| User interface | Streamlit | O |
| Testing | pytest + held-out synthetic evaluation harness | O |
| Development workflow | Spec Kit in Antigravity | R |

## 14. Build approach and component specs

Each component gets one Spec Kit spec, and every version of the agent is scored on the same eval suite. (R)

- **Three builds (ADLC):** scripted (stages 1 to 3 plus a fixed order of checks), low-code, then Magentic. Each earlier version stays as a baseline.
- **Spec loop:** specify, clarify, plan, tasks, implement in Antigravity, then verify against the spec's eval cases. When reality disagrees with a spec, update the spec first, then the code.
- **Prototypes:** each component is prototyped cheaply to learn what its spec should say, then rebuilt from the spec. Prototypes stay runnable, since they become baselines.
- **Schedule:** follows the AALS Capstone Roadmap. The Roadmap doc's phases P0 to P4 are a working plan subject to change.

The run-orchestrator spec is new in this merge; it owns the run states in Section 6.

| Spec | Stages | Example acceptance criterion | Eval items cited | Owner |
| :-: | :-: | :-: | :-: | :-: |
| Data generator and injection library | Section 8 | Seed S produces event E at its logged magnitude | Supports all | Data |
| Semantic layer | Cross-cutting | Every field in rx_weekly has an entry; an unknown metric ID raises an error | EV-9.2 | Data |
| Validation gate | 1, 2 | Catches each seeded artifact type on dev seeds | EV-2.1, EV-2.3, EV-2.4 | Data |
| Competitive intelligence | 3 | Flags every material seeded event; at most 1 false flag per null week | EV-3.1 to EV-3.4 | Data |
| Tool interface and handoff contracts | 4 | Typed signatures bound to the semantic layer; requests and results validate against their schemas | EV-9.1, EV-9.3 | Agent |
| Triage, manager and specialists | 4 | Closes every story with a verdict and confidence within the caps | EV-2.2, EV-4.x, EV-5.1, EV-5.2, EV-5.4 | Agent |
| Narrative and renderer | 5 | Zero digits outside claim tokens | EV-1.1, EV-1.2, EV-7.x | Agent |
| Verifier | 6 | Rejects a brief with a planted wrong number | EV-1.1, EV-5.3, EV-6.1, EV-9.1, EV-9.2 | Agent |
| Run orchestrator and review flow | All (Section 6) | Every run ends in PUBLISHED or RUN_ERROR, with each transition logged | EV-6.2, EV-8.5 | Both |
| Eval harness and tracing | Cross-cutting | The full suite runs in one command and logs a Phoenix experiment | All | Both |

[NEEDS CLARIFICATION: who is the Data owner and who is the Agent owner; the Roadmap suggests one of each, reviewing each other's specs]

## 15. Open items

Seventeen architecture decisions remain open; none blocks writing the constitution or the data-layer specs. Items marked Proposed have a suggested answer in the section named.

| # | Open item | Section | Who resolves | Status |
| :-: | :-: | :-: | :-: | :-: |
| A1 | Triage decision junction: which calls are code, which are LLM, and what flags human review | 5.4 | Michael, Meghna | Open |
| A2 | Magentic inside the briefing use case only (amendment to the Proposal) | 3 | Dr. Admasu | Open |
| A3 | Agent framework: Google ADK, custom Python or Microsoft Agent Framework | 13 | Michael, Meghna | Open |
| A4 | Definition of business impact, shared with the answer key | 5.3 | Michael, Meghna; Alvin, Sienna | Proposed |
| A5 | Multiple-testing control in competitive intelligence | 5.3 | Michael, Meghna | Open |
| A6 | Geography dimension table | 7.2 | Data owner | Open |
| A7 | Behavior when every cut fails validation | 5.2, 6 | Michael, Meghna | Proposed |
| A8 | Path when P2 returns a brief | 5.7, 6 | Michael, Meghna | Proposed |
| A9 | Sign-off level: P2 or one level higher | 5.7 | Dr. Admasu | Open |
| A10 | Plan review: on for the demo, by exception in the Monday run | 5.4 | Dr. Admasu | Proposed |
| A11 | Any runtime handoff to the Forecast agent (forecast_watchlist parked) | 3 | Alvin, Sienna | Open |
| A12 | Therapeutic class to mimic for calibration | 8 | Dr. Admasu | Open |
| A13 | Names of the Data owner and the Agent owner | 14 | Michael, Meghna | Open |
| A14 | Replace "surveillance" with "competitive intelligence" in the Proposal and the Operation Flow | 1 | Michael, Meghna | Open |
| A15 | One investigation_request per run | 5.4 | Michael, Meghna | Proposed |
| A16 | Promotion attribution, reach and campaign data (channel spend, consumer campaigns) for P4: in scope for v1 or not | 5.4, 7.2 | Dr. Admasu; Alvin, Sienna | Open |
| A17 | NY metro borough geography: a region inside the national world, or a separate world | 7.2, 8 | Dr. Admasu | Open |

**Evaluation Pack open items this doc answers or feeds.**

| Evaluation Pack item | This doc proposes | Section |
| :-: | :-: | :-: |
| 3 Confidence scale | High, Medium and Low as defined in 5.4 | 5.4 |
| 16 Ablation | The scripted baseline is the manager-off ablation | 9 |
| 17 Limits | The cap list; values still open | 10.1 |
| 18 Refresh window | 3 weeks | 5.1 |

## 16. Decision log

Twenty decisions shaped this doc: the first eighteen on 2026-10-16, the last two on 2026-10-21. Each change to this doc adds a row.

| # | Decision | Source | Reason |
| :-: | :-: | :-: | :-: |
| 1 | Where one doc specifies an element and the other is silent, the specifying doc's element is kept | User | Avoids reopening settled detail |
| 2 | Operation Flow step 6 becomes "Triage and investigation"; "external" and "Forecast Explanation" removed | O, reworded | Briefing and Forecast investigation are different tasks (user ruling, 2026-10-14) |
| 3 | Orchestration is nested: Operation Flow run states as the spine, the Magentic loop inside stage 4 | R+O | The two docs describe the same stage from outside and inside |
| 4 | Triage is a hybrid: code, then manager, then P1 by exception | User | No single layer can own it; review only when flagged keeps P1's load low |
| 5 | Whatever groups candidates into stories sees every candidate of the run | New | Compound and masked weeks (EV-4.4) |
| 6 | Claim tokens are the mechanism; reconciliation stays as the backstop | R+O | EV-1.1 is a hard gate; preventing errors beats catching them |
| 7 | Routine and warning runs still pass through narrative, verification and review | R | Every brief carries a KPI table (EV-1.1) |
| 8 | Time-series decomposition sits in stage 3 (seasonality); contribution decomposition in stage 4 | R+O | Each doc's method kept where it fits |
| 9 | Data Forensics stays an agentic specialist | R | The Roadmap specifies it; the scripted baseline shows whether it earns that |
| 10 | Story and hypothesis entities added | SoT | EV-2.2, EV-4.2, EV-7.2, EV-7.3 |
| 11 | Two review gates: P1 review, P2 sign-off | SoT | Personas |
| 12 | Stage 3 named "competitive intelligence"; the Operation Flow stack row renamed | SoT | Mentor directive recorded in the Personas |
| 13 | Both docs' evaluation sections superseded by the Evaluation Pack; white-box metrics moved to component specs | SoT | The Evaluation Pack's black-box rule |
| 14 | forecast_watchlist parked | User | Use cases stay separate until shown otherwise |
| 15 | Stack taken from the Operation Flow; framework left open | O | The Roadmap is silent on the stack |
| 16 | Loop guardrails: no recursion by construction, finite hypothesis catalog, caps, defined exit | R, New | Mentor concern about runaway recursion |
| 17 | Run-orchestrator spec added | New | The run states need an owner |
| 18 | Episodic memory built as a query over prior runs | New | No second store; serves EV-1.2 and EV-7.2 |
| 19 | P4 Marketer added as a fourth persona; reads the signed-off brief only, like P3 | SoT | Mentor request, recorded in the Personas (2026-10-21) |
| 20 | Promotion stays one tested driver with a verdict either way; no attribution or ROI model in v1 | SoT | Personas scope note; EV-4.5 and EV-7.5; pending A16 |
