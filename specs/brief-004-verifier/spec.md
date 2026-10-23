# Feature Specification: Verifier (Stage 6)

**Spec ID**: `brief-004-verifier` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-16 | **Updated**: 2026-10-23
**Status**: Draft v2. Not started.
**Replaces**: `008-verifier` (Oct 16)
**Input**: System Architecture §4 (stage 6: shared rules, lane checks); Briefing Architecture §5.6, §10.2; Evaluation Pack EV-1.1, EV-1.2, EV-4.5, EV-5.3, EV-6.1, EV-6.2, EV-9.1, EV-9.2; User stories P1-Q1, P1-Q4, P2-Q5, P3-Q3, P3-Q6, P4-Q1, P4-Q2

Stage 6 shares its rules across lanes (System §4): numbers reconcile by code, citations resolve, no causal overclaim. This spec implements those rules for the Briefing lane and adds the Briefing checks. The Forecast lane's stage 6 (V = Σc + r within tolerance, citations, overclaim) is owned by Alvin and Sienna.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reject any wrong number (Priority: P1)

Before any reviewer sees a brief, the verifier checks every token, every digit and every rendered number against the pinned snapshot. A brief with a planted wrong number is rejected.

**Why this priority**: One mismatched figure forces the analyst to re-audit the whole brief (P1-Q1).

**Independent Test**: Plant a wrong number in a rendered brief; check the verifier names the claim and both values.

**Acceptance Scenarios**:

1. **Given** a token with no tool record, **When** the verifier runs, **Then** it fails with the token named.
2. **Given** a digit not from a token, **When** the verifier runs, **Then** the brief fails.
3. **Given** a rendered number that differs from the pinned snapshot after stated rounding, **When** the verifier runs, **Then** the brief fails with the claim and both values.
4. **Given** the 2026-07-06 brief stating "Great Lakes BXA TRx was 670", **When** the verifier runs, **Then** it fails: the cut is withheld and 670 includes 46 duplicated TRx. (User story P1-Q1.)
5. **Given** an April 2026 brief re-verified today, **When** Mid-Atlantic 2026-04-06 is checked, **Then** it reconciles to 692 on the pinned snapshot; 742 from the newer data fails. (User story P2-Q5.)

---

### User Story 2 - Every claim has evidence that resolves (Priority: P1)

Every story cites at least one tool record. Every link resolves to the record and span that produced the value, on the pinned snapshot.

**Why this priority**: P2 must show the evidence behind a challenged claim (P2-Q5); P1 traces in one click (P1-Q4).

**Independent Test**: Remove a link; check the flag. Follow every link in a good brief.

**Acceptance Scenarios**:

1. **Given** a claim with no evidence ID, **When** the verifier runs, **Then** the claim is flagged.
2. **Given** the claim "BXA NBRx on SYN_MID_ATLANTIC_MEDICARE_PART_D_1 fell 37%", **When** its links are followed, **Then** they open the `get_metric` and `lookup_access_events` records and spans. (User story P1-Q4.)

---

### User Story 3 - Disclosure and coverage checks (Priority: P1)

The verifier fails a brief that uses a restated number without disclosure, or a partial-coverage total without its label.

**Why this priority**: The director quotes these numbers upward (P3-Q6).

**Independent Test**: Remove the restatement disclosure from the 2026-07-13 brief, and the coverage label from the 2026-07-06 brief.

**Acceptance Scenarios**:

1. **Given** a restatement in the health report and no disclosure in the brief, **When** the verifier runs, **Then** it fails (EV-1.2).
2. **Given** a national total built on 7 of 8 territories without the label, **When** the verifier runs, **Then** it fails. (User stories P1-Q1, P3-Q6.)

---

### User Story 4 - Governance and wording checks (Priority: P1)

The verifier fails any line that identifies a rep, any banned term, any reader-jargon term in reader text, "new patients" outside NBRx, causal wording below High, a promotion claim worded as causation, and a generalization from a small cell.

**Why this priority**: The brief goes to sales leadership and marketing. Terminology is a mentor directive. P4 must not be told a campaign "caused" a lift.

**Independent Test**: Plant each violation and check each is caught.

**Acceptance Scenarios**:

1. **Given** a line pointing to one rep, **When** the verifier runs, **Then** it fails.
2. **Given** "statistical surveillance", "surveillance", or "new patients" attached to NRx, **When** the verifier runs, **Then** it fails.
3. **Given** "difference-in-differences" in a reader-facing sentence, **When** the verifier runs, **Then** it fails. (User story P3-Q3.)
4. **Given** "promotion caused a 120 TRx lift", **When** the verifier runs, **Then** it fails; association wording passes. (User story P4-Q1.)
5. **Given** "cash patients respond most to promotion" drawn from a 49-prescription cell, **When** the verifier runs, **Then** it fails. (User story P4-Q2.)
6. **Given** a promotion credit in a story whose promotion verdict is not "supported", **When** the verifier runs, **Then** it fails (EV-4.5).

---

### User Story 5 - Overclaiming judge, used only when trusted (Priority: P2)

A judge checks faithfulness and overclaiming. It scores briefs only after its agreement with human labels is measured and meets the bar; before that it runs in shadow mode.

**Why this priority**: Overclaiming is the costliest error (P2-Q3). An unmeasured judge cannot be trusted.

**Independent Test**: Run the judge on human-labeled briefs; report agreement. Plant a causal claim on a Medium story.

**Acceptance Scenarios**:

1. **Given** a causal claim on a Medium or Low story, **When** checks run, **Then** it is flagged by code (the wording map) and, when trusted, by the judge.
2. **Given** agreement below the bar, **When** scoring is requested, **Then** the judge does not replace human scoring.

---

### User Story 6 - One revision, then visible flags (Priority: P1)

If a brief fails, the writer gets the flags and one revision. If it still fails, it goes to review with its flags visible.

**Why this priority**: The Monday brief is never blocked, and people see what failed.

**Independent Test**: Plant a fixable and an unfixable failure.

**Acceptance Scenarios**:

1. **Given** a first-pass failure, **When** flagged, **Then** exactly one revision loop to stage 5 runs.
2. **Given** a second failure, **When** the loop ends, **Then** the state is VERIFICATION_FLAGGED and the flags appear to the reviewer.

### Edge Cases

- A claim is exact but its rounding rule is missing: fail, do not guess.
- A glossary entry differs from the layer text: fail.
- A story's evidence exists only for a withheld cut: flag as unqualified use.
- The judge is unavailable: code checks still run; the brief notes the judge did not run.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The verifier MUST check that every claim token resolves to a tool record.
- **FR-002**: The verifier MUST fail any digit not from a token.
- **FR-003**: The verifier MUST reconcile every rendered number to the pinned snapshot after stated rounding, and MUST ignore newer data.
- **FR-004**: The verifier MUST check that every story cites at least one tool record, and that every link resolves on the pinned snapshot to the record and span that produced the value.
- **FR-005**: The verifier MUST fail a brief that omits a restatement disclosure present in the health report, or a coverage label on a partial total.
- **FR-006**: The verifier MUST check wording against the semantic layer per metric, and MUST fail banned terms, reader-jargon terms in reader text, and "new patients" outside NBRx.
- **FR-007**: The verifier MUST fail lines that identify an individual rep.
- **FR-008**: The verifier MUST check that causal wording appears only on High stories, and that promotion findings use association wording and appear only where the promotion verdict is supported.
- **FR-009**: The verifier MUST fail any generalization from a cell below the small-cell floor.
- **FR-010**: A judge MAY check faithfulness and overclaiming. It MUST NOT replace human scoring until its agreement with human labels meets the bar. [NEEDS CLARIFICATION: agreement bar (Evaluation Pack open item 2)]
- **FR-011**: On failure, the verifier MUST trigger exactly one revision loop to stage 5, then pass flags to review.
- **FR-012**: The verifier MUST record a verification status per claim in `brief_claim`.
- **FR-013**: All code checks MUST be deterministic.
- **FR-014**: Each flag MUST carry one failure tag from the Briefing list (until S10): data misread, wrong metric, wrong grain, missed event, false alarm, over-attribution, missed interaction, stale context, unsupported claim, numeric mismatch, governance breach, run error.

### Key Entities

Verification result (per claim, per check, flags); flag (check, claim, evidence, failure tag); judge result (label, rationale, agreement).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of briefs with a planted wrong number are rejected (EV-1.1 gate).
- **SC-002**: 100% of numeric claims link to at least one tool record (EV-6.1), and 100% of links resolve (EV-6.2).
- **SC-003**: 100% of missing disclosures and coverage labels are caught (EV-1.2).
- **SC-004**: Zero governance or wording failures reach review unflagged (EV-9.1, EV-9.2).
- **SC-005**: Causal wording appears only where the evidence supports it (EV-5.3); promotion is never credited without a supported verdict (EV-4.5).
- **SC-006**: Judge-human agreement is reported before the judge scores anything.
- **SC-007**: 100% of failing briefs get exactly one revision and then reach review with visible flags.

## Assumptions

- The verifier reads the rendered brief, `brief_claim`, the health report, the pinned snapshot and the semantic layer. It never reads the answer key.
- A false pass is worse than a false fail.
