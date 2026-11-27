// Exact TypeScript representation of the Briefing API contracts (core-007: roles and views).
// Never substitute sample data if a request or contract check fails.
export type ReleaseContext = {
  first_week: string
  latest_week: string
  territory_ids: string[]
  available_weeks: string[]
  product_ids: string[]
  brands: { id: string; name: string; engines: ("scripted" | "agent")[] }[]
  supported_intents: string[]
  engine: "scripted"
}
export type Evidence = {
  id: string
  tool: string
  params: Record<string, unknown>
  query: string | null
  result: unknown
  data_version: string | null
}
export type Claim = { value: string; evidence_id: string }
// brief-005: P1 sends a brief for sign-off, P2 signs it off or returns it; only a signed-off brief reaches P3 and P4.
export type ReviewStatus = "draft" | "sent" | "signed_off" | "returned" | "rejected"
export type ClaimFlag = { claim: number; value: string; evidence_id: string; note: string | null }  // a claim the Insights Manager marked as wrong
export type TrailEntry = { at: string; persona: string; action: string; from?: string; to?: string; comment?: string | null; flags?: ClaimFlag[]; legacy?: boolean }
export type ReturnNote = { at: string; comment: string | null; flags: ClaimFlag[] | null }
export type BriefingResult = {
  brief_id: string
  view: "analyst"
  status: "draft_requires_review"
  review_status: ReviewStatus
  reviewed_at: string | null
  review_reason: string | null
  signed_off_at?: string | null
  review_trail?: TrailEntry[]    // analyst and Insights Manager views only: every send, return and sign-off, with comments and flags
  returned?: ReturnNote | null   // set while the brief is returned: what the analyst reads before rerunning
  engine: "scripted" | "agent"
  system: string
  question: string
  brand_id: string
  territory_id: string
  week_start: string
  week_end?: string | null
  answer: string
  claims: Claim[]
  evidence: Evidence[]
  data_version: string | null
  abstained: boolean
  triage?: TriageRecord | null  // brief-002: who made each triage call (analyst view only)
  flow?: Stage[] | null         // brief-002: the seven stages, run states and actors (analyst view only)
  citations?: { start: number; end: number; claim: number }[] | null  // where each claim sits in the answer
  sections?: MemoSection[] | null  // brief-003: the memo's sections, charts and the data behind them
  definition?: BriefDefinition | null  // brief-010: what the brief was built under; absent on briefs made before it
  events?: RunEvent[] | null  // brief-009: the saved event log (analyst view only); absent on briefs made before it
}
// brief-009 (plan.md): one step of a run. `claims` are indexes into the brief's claims; `args` are analyst view only;
// `summary` is written by code from the tool result. The agent engine and the scripted engine (actor Code) share this shape.
export type RunEvent = {
  seq: number
  t: string
  actor: "Manager" | "Data Forensics" | "Driver Investigator" | "Writer" | "Code" | "Person"
  kind: "agent" | "llm" | "code" | "person"
  step: string
  story: string | null
  tool: string | null
  args: Record<string, unknown> | null
  verdict: "supported" | "ruled out" | "inconclusive" | "abstained" | "done" | null
  summary: string
  claims: number[]
  prompt: string | null  // "<prompt file>@<short hash>", model steps only
}
// brief-003: the memo outline. Every number in `text`, `prose`, a caption or an explanation is a claim of the
// same brief; every plotted point comes from `table`, a governed query recorded as an evidence item.
export type Span = { start: number; end: number; claim: number }
export type DataTable = { evidence_id: string; query: string; columns: string[]; rows: (string | number | boolean | null)[][] }
export type ChartPoint = { week: string; value: number | null; basis?: "observed" | "projected" | "estimated"; restated?: boolean }
export type ChartSpec = {
  kind: "trend" | "story" | "share" | "coverage"
  weeks: string[]
  caption: string
  explanation: string
  series?: { name: string; points: ChartPoint[] }[]
  band?: { low: number; high: number; weeks: string[]; label: string } | null
  panel?: { name: string; unit: string; driver: string; points: ChartPoint[]; table?: DataTable } | null
  rows?: { territory: string; cells: { week: string; basis: "observed" | "projected" | "estimated"; restated: boolean }[] }[]
  table?: DataTable | null  // analyst view only
  explanation_citations?: Span[]  // analyst view only
}
// brief-008: structured blocks beside a section's text. Every value is a string the server already filled from a
// claim token (the UI shows it as given); the *_citations fields are analyst view only and use the Span form.
export type KpiTile = {
  label: string
  value: string
  detail?: string | null
  direction?: "up" | "down" | "flat" | null
  value_citation?: Span[]
}
export type TerritoryBasis = "observed" | "projected" | "estimated" | "withheld"
export type TerritoryRow = {
  cells: string[]
  basis: TerritoryBasis
  cell_citations?: Span[][]    // one list of spans per cell, offsets within that cell's string
}
export type TerritoryTable = { columns: string[], rows: TerritoryRow[], note?: string | null }
export type StoryCardBlock = {
  headline: string
  confidence: "High" | "Medium" | "Low"
  drivers_checked: string[]
  headline_citations?: Span[]
}
export type MemoSection = {
  number: string
  title: string
  text: string
  prose: string
  claims?: number[]            // analyst view only: indexes into the brief's claims
  text_citations?: Span[]      // analyst view only
  prose_citations?: Span[]     // analyst view only
  chart?: ChartSpec | null
  kpis?: KpiTile[] | null                 // brief-008: §1
  territory_table?: TerritoryTable | null // brief-008: §2
  card?: StoryCardBlock | null            // brief-008: each story section
  detail?: string | null                  // brief-008: analyst view only, folded under "Show detail"
  detail_citations?: Span[]               // analyst view only
}
// brief-002 Phase A: the code triage plan P1 reviews, and how a brief was made.
export type StoryCard = {
  id: string
  kind: "territory" | "plan" | "competitor"
  title: string
  rank: number
  proposed: "investigate" | "over_cap"
  territory?: string | null
  manager?: { keep: boolean; position: number | null; why: string | null; hypotheses: string[] }  // agent plans only
  what_moved: string
  decision: string
  population: string
  granularity: string
  time: string
}
export type TriagePlan = {
  promotion_review?: boolean
  plan_id: string
  question: string
  data_version: string
  state: "TRIAGE_REVIEW" | "ROUTINE" | "CALENDAR" | "OUT_OF_SCOPE"
  engine?: "agent"
  model?: string
  scope?: string
  manager_order?: string[]
  manager_note?: string
  flagged?: boolean
  flags?: string[]
  corrections?: string[]
  weeks: string[]
  baseline: string[]
  context: string
  stories: StoryCard[]
  dropped: { territory: string; reason: string; layer: "code" }[]
  claims: Claim[]
  evidence: Evidence[]
  brand_id: string
  territory_id: string
  week_start: string
}
export type TriageDecision = { plan_id: string; stories: string[] }
export type CloudHost = { enabled: boolean; seconds_left: number; starting: boolean; error: string | null; eta_minutes: number | null; cpu: boolean }
export type AgentStatus = { cloud?: CloudHost; builtin?: { model: string } | null; online: boolean; configured: boolean; model: string | null; hosts?: { name: string; model: string | null }[]; queued: number; running: number; last_seen_seconds: number | null }
export type AgentJob = {
  id: string
  kind: "triage" | "brief"
  status: "queued" | "running" | "done" | "failed"
  error: string | null
  host_kind?: "cloud_cpu" | "teammate" | "builtin" | null
  progress?: RunEvent[] | null  // brief-009: the events so far while the job runs
  result?: unknown
}
export type TriageRecord = {
  plan_id: string
  default: boolean
  order: string[]
  calls: { story: string; title: string; outcome: string; layer: "code" | "agent" | "human"; position?: number; why?: string | null }[]
}
export type Stage = {
  stage: number
  name: string
  actors: { kind: "code" | "agent" | "llm" | "human"; name: string }[]
  states: string[]
  note: string
}
// The leadership view: an executive summary cut from the answer by the server. It never
// carries claims, evidence, query text or a trace.
export type LeadershipBrief = {
  brief_id: string
  view: "leadership"
  engine: "scripted" | "agent"
  system: string
  brand_id: string
  territory_id: string
  week_start: string
  week_end?: string | null  // brief-008: set for a multi-week period
  data_version: string | null
  abstained: boolean
  review_status: ReviewStatus
  reviewed_at: string | null
  summary: string
  sections?: MemoSection[] | null  // brief-003 FR-026: §1, §2, §3 without checks, §5; no claims, tables or queries
  definition?: BriefDefinition | null  // brief-010: the same definition as the analyst brief; it holds no SQL and no arguments
  process_summary?: string | null  // brief-009 FR-005: one line on how it was built; leaders never get the events
}
export type PublishedBrief = {
  brief_id: string
  brand_id: string
  week_start: string
  week_end?: string | null
  territory_id: string
  engine: string
  reviewed_at: string | null
  abstained: boolean
}
export type LaneRole = {
  role: string
  persona: string
  label: string
  views: ("analyst" | "leadership")[]
  actions: string[]
  available: boolean
}
export type ViewAs = "analyst" | "insights" | "leadership" | "marketer"
// tester: the test login, which switches between the analyst (P1, CA), Insights Manager (P2), leadership (P3, BM) and Marketer (P4) roles (view_as).
export type Me = { name: string; username?: string;  // username: the sign-in name, shown when /api/me sends it
   auth_mode: "oidc" | "dev"; brand_ids: string[]; lanes: { briefing?: LaneRole; forecast?: LaneRole }; evaluation?: boolean; tester?: boolean; view_as?: ViewAs | null }
// Data classification per tab and view (core-009): labels only, from src/pharmagentics/api/classification.json.
export type ClassLevel = { id: string; label: string; description: string }
export type Classification = { version: string; levels: ClassLevel[]; tabs: Record<string, string>; clearance: Record<string, string> }
export type Comparison =
  | { kind: "previous"; weeks: number }
  | { kind: "last_year" }
  | { kind: "pre_launch" }  // brief-010: the four weeks before Metacora launched; no weeks, start or end
  | { kind: "custom"; start: string; end: string }

// brief-010 FR-000a and FR-000e: the brief definition, JSON names as in plan.md ("The brief definition"). Every field
// except the period is a list of one or more values; the first is the primary and drives the stories, the cards and the
// finding directions, and each extra value adds labelled figures beside it. The server reads a single value as a
// one-item list, and fills every field it is not given with the pre-selected value (like for like, TRx, all five
// grains, the other territories, the house comparison), so a brief with no definition is the brief of today.
export type TerritoriesCounted = "like_for_like" | "all_reportable" | "projected"
export type MeasureChoice = "trx" | "nbrx"  // the old "both" is ["trx", "nbrx"]
export type GrainLevel = "national" | "territory" | "plan" | "channel" | "specialty"
export type RelativeTo = "other_territories" | "national" | "none"
export type BriefDefinition = {
  first_week?: string | null  // ISO Monday; null: the question's weeks, else the latest closed week
  last_week?: string | null
  comparison?: Comparison[] | null  // null: the previous four weeks
  territories: TerritoriesCounted[]
  measure: MeasureChoice[]
  grain: GrainLevel[]
  relative_to: RelativeTo[]
}
// What a question reader may propose: any field as one value or a list (a single value is a one-item list).
type OneOrMany<T> = T | T[]
export type ProposedDefinition = {
  first_week?: string | null
  last_week?: string | null
  comparison?: OneOrMany<Comparison> | null
  territories?: OneOrMany<TerritoriesCounted> | null
  measure?: OneOrMany<MeasureChoice | "both"> | null
  grain?: OneOrMany<GrainLevel> | null
  relative_to?: OneOrMany<RelativeTo> | null
}

export type BriefingQuery = {
  intent: "weekly_brief" | "promotion_review"
  brand_id: string
  territory_id: string
  week_start: string
  week_end?: string | null  // brief-008: the last week of a multi-week period; absent for one week
  comparison?: Comparison | null
  question: string
  definition?: BriefDefinition | null  // brief-010: the six selectors; the server's pre-selected values when absent
}

// brief-008 FR-008: a typed question read into a proposed scope for the form. Nothing runs on it.
export type BriefingScope = {
  question: string
  week_start: string
  week_end: string
  territory_id: string | null  // null: the question names no territory, so the form keeps its choice
  comparison_weeks: number | null  // null: no earlier week fits, so the default comparison applies
  promotion_review: boolean
  notes: string[]
  read_by: "model" | "rules"
  model?: string | null
  definition?: ProposedDefinition | null  // brief-010: the fields the reader proposes; the analyst confirms them
}

export class NotSignedIn extends Error {}

const BASE = (import.meta.env.VITE_PHARMAGENTICS_API_BASE_URL || "").trim().replace(/\/+$/, "")

function expectObject(v: unknown): asserts v is Record<string, unknown> {
  if (v === null || typeof v !== "object" || Array.isArray(v)) throw new Error("Invalid API response object")
}
function stringArray(v: unknown): v is string[] {
  return Array.isArray(v) && v.every(x => typeof x === "string")
}
const REVIEW = new Set(["draft", "sent", "signed_off", "returned", "rejected"])

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  if (!BASE) throw new Error("API URL is not configured. Set VITE_PHARMAGENTICS_API_BASE_URL. No mock fallback is enabled.")
  let response: Response
  try { response = await fetch(`${BASE}${path}`, { cache: "no-store", credentials: "same-origin", ...init }) }
  catch { throw new Error("Cannot reach Briefing API. Check server, HTTPS/CORS settings, and API URL.") }
  if (response.status === 401) throw new NotSignedIn("Sign in first.")
  if (!response.ok) {
    let message = `Briefing API returned HTTP ${response.status}`
    try {
      const payload: unknown = await response.json()
      expectObject(payload)
      if (typeof payload.detail === "string") message = payload.detail
    } catch { /* keep status */ }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return await response.json() as T
}
export const post = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })

export async function getMe(): Promise<Me> {
  const v: unknown = await api("/api/me")
  expectObject(v)
  if (typeof v.name !== "string" || (v.auth_mode !== "oidc" && v.auth_mode !== "dev")) throw new Error("The backend identity contract is incompatible with this frontend.")
  expectObject(v.lanes)
  return v as unknown as Me
}
export async function setViewAs(view: ViewAs): Promise<Me> {
  return await api("/api/me/view-as", post({ view }))
}
export async function getClassification(): Promise<Classification> {
  const v: unknown = await api("/api/classification")
  expectObject(v)
  if (!Array.isArray(v.levels)) throw new Error("The backend classification contract is incompatible with this frontend.")
  expectObject(v.tabs)
  return v as unknown as Classification
}
export async function getContext(): Promise<ReleaseContext> {
  const v: unknown = await api("/api/briefing/context")
  expectObject(v)
  if (!stringArray(v.available_weeks) || !stringArray(v.territory_ids) ||
      !stringArray(v.product_ids) || !stringArray(v.supported_intents) ||
      v.engine !== "scripted" || typeof v.latest_week !== "string" || typeof v.first_week !== "string") {
    throw new Error("The backend context contract is incompatible with this frontend.")
  }
  if (!v.supported_intents.includes("weekly_brief")) throw new Error("The backend does not currently support weekly briefings.")
  const productIds = v.product_ids
  if (!Array.isArray(v.brands) || v.brands.length !== v.product_ids.length || v.brands.some((b: unknown) => {
    if (!b || typeof b !== "object") return true
    const c = b as ReleaseContext["brands"][number]
    return typeof c.id !== "string" || typeof c.name !== "string" || !productIds.includes(c.id) ||
      !Array.isArray(c.engines) || !c.engines.length || c.engines.some(e => e !== "scripted" && e !== "agent")
  })) throw new Error("The backend returned an incompatible brand catalog.")
  if (!v.territory_ids.length || !v.available_weeks.length) {
    throw new Error("The backend returned no supported territories or reporting weeks.")
  }
  return v as unknown as ReleaseContext
}
function checkAnalyst(v: unknown): BriefingResult {
  expectObject(v)
  if (v.view !== "analyst" || typeof v.brief_id !== "string" || v.status !== "draft_requires_review" || (v.engine !== "scripted" && v.engine !== "agent") ||
      !REVIEW.has(v.review_status as string) || typeof v.answer !== "string" ||
      !Array.isArray(v.claims) || !Array.isArray(v.evidence) || typeof v.abstained !== "boolean") {
    throw new Error("Backend returned a response incompatible with the implemented weekly briefing UI.")
  }
  const ids = new Set<string>()
  for (const ev of v.evidence as unknown[]) {
    expectObject(ev)
    if (typeof ev.id !== "string") throw new Error("Evidence identifier missing")
    ids.add(ev.id)
  }
  for (const cl of v.claims as unknown[]) {
    expectObject(cl)
    if (typeof cl.evidence_id !== "string" || typeof cl.value !== "string" || !ids.has(cl.evidence_id)) {
      throw new Error("Backend contains a claim without a resolvable evidence record")
    }
  }
  return v as unknown as BriefingResult
}
function checkLeadership(v: unknown): LeadershipBrief {
  expectObject(v)
  if (v.view !== "leadership" || typeof v.brief_id !== "string" || typeof v.summary !== "string" ||
      "claims" in v || "evidence" in v || "answer" in v) {
    throw new Error("Backend returned a leadership view that is not a plain executive summary.")
  }
  return v as unknown as LeadershipBrief
}
export async function getTriage(q: BriefingQuery): Promise<TriagePlan> {
  return checkPlan(await api("/api/briefing/triage", post(q)))
}
function checkPlan(v: unknown): TriagePlan {
  expectObject(v)
  if (typeof v.plan_id !== "string" || !["TRIAGE_REVIEW", "ROUTINE", "CALENDAR", "OUT_OF_SCOPE"].includes(v.state as string) ||
      !Array.isArray(v.stories) || !Array.isArray(v.dropped) || !Array.isArray(v.claims) || !Array.isArray(v.evidence)) {
    throw new Error("Backend returned a triage plan incompatible with this frontend.")
  }
  const ids = new Set((v.evidence as { id: string }[]).map(e => e.id))
  if ((v.claims as Claim[]).some(c => !ids.has(c.evidence_id))) throw new Error("The triage plan contains a claim without a resolvable evidence record")
  for (const c of v.stories as unknown[]) {
    expectObject(c)
    if (typeof c.id !== "string" || (c.proposed !== "investigate" && c.proposed !== "over_cap") ||
        ["what_moved", "decision", "population", "granularity", "time"].some(k => typeof c[k] !== "string")) {
      throw new Error("A triage card is incompatible with this frontend.")
    }
  }
  return v as unknown as TriagePlan
}
export async function readBriefingScope(req: { question: string; brand_id: string }): Promise<BriefingScope> {
  const v: unknown = await api("/api/briefing/scope", post(req))
  expectObject(v)
  if (typeof v.week_start !== "string" || typeof v.week_end !== "string" || (v.comparison_weeks !== null && typeof v.comparison_weeks !== "number") ||
      typeof v.promotion_review !== "boolean" || (v.read_by !== "model" && v.read_by !== "rules") || !Array.isArray(v.notes)) {
    throw new Error("The question could not be read. Set the scope by hand.")
  }
  return v as unknown as BriefingScope
}
export async function getBriefing(q: BriefingQuery, triage?: TriageDecision): Promise<BriefingResult> {
  return checkAnalyst(await api("/api/briefing/query", post(triage ? { ...q, triage } : q)))
}
export async function openBrief(id: string, view: "analyst"): Promise<BriefingResult>
export async function openBrief(id: string, view: "leadership"): Promise<LeadershipBrief>
export async function openBrief(id: string, view: "analyst" | "leadership"): Promise<BriefingResult | LeadershipBrief> {
  const v: unknown = await api(`/api/briefing/${encodeURIComponent(id)}?view=${view}`)
  return view === "analyst" ? checkAnalyst(v) : checkLeadership(v)
}
export async function listPublished(): Promise<PublishedBrief[]> {
  const v: unknown = await api("/api/briefing/published")
  if (!Array.isArray(v)) throw new Error("The backend published-briefs contract is incompatible with this frontend.")
  return v as PublishedBrief[]
}
// P1: send the brief for sign-off, or reject it (a rejection needs a reason).
export async function reviewBrief(id: string, decision: "sent" | "rejected", reason?: string): Promise<BriefingResult> {
  return checkAnalyst(await api(`/api/briefing/${encodeURIComponent(id)}/review`, post({ decision, reason: reason || null })))
}
// P2: sign a brief off, or return it with a comment (needed) and flags on single claims (by index in the brief's claims).
export async function signoffBrief(id: string, decision: "signed_off" | "returned", comment?: string, flags: { claim: number; note?: string | null }[] = []): Promise<BriefingResult> {
  return checkAnalyst(await api(`/api/briefing/${encodeURIComponent(id)}/signoff`, post({ decision, comment: comment || null, flags })))
}
export type QueueRow = { brief_id: string; brand_id: string; week_start: string; week_end?: string | null; territory_id: string; engine: string; abstained: boolean
  review_status: "sent" | "returned" | "signed_off"; sent_at: string | null; signed_off_at: string | null; returned_at: string | null }
// The sign-off queue: P2 gets the briefs sent, returned and signed off; P1 the ones waiting on P2 and the ones returned to them.
export async function listQueue(): Promise<QueueRow[]> {
  const v: unknown = await api("/api/briefing/queue")
  if (!Array.isArray(v)) throw new Error("The backend sign-off queue contract is incompatible with this frontend.")
  return v as QueueRow[]
}

// Agent jobs (core-007 FR-028/FR-031): run by teammate or cloud CPU hosts; the app only queues and checks them.
export async function getAgentStatus(): Promise<AgentStatus> {
  return await api("/api/agent/status") as AgentStatus
}
export async function submitAgentJob(req: { kind: "triage" | "brief"; query: BriefingQuery; triage_job?: string; decision?: TriageDecision }): Promise<AgentJob> {
  return await api("/api/agent/jobs", post(req)) as AgentJob
}
export async function waitAgentJob(id: string, onUpdate: (j: AgentJob) => void): Promise<AgentJob> {
  const started = Date.now()
  for (;;) {
    const job = await api(`/api/agent/jobs/${encodeURIComponent(id)}`) as AgentJob
    onUpdate(job)
    if (job.status === "done" || job.status === "failed") return job
    if (Date.now() - started > 20 * 60 * 1000) throw new Error("The agent job is taking too long; check the agent host.")
    await new Promise(r => setTimeout(r, 3000))
  }
}
export function agentPlan(job: AgentJob): TriagePlan { return checkPlan(job.result) }
export function agentBrief(job: AgentJob): BriefingResult { return checkAnalyst(job.result) }

// brief-009 FR-006: the agent team for the "How it works" tab (GET /api/briefing/agents). `prompts` is present only for
// roles that hold the analyst view; a leadership role never gets it.
export type AgentPrompt = { id: string; step: string; file: string; hash: string; ref: string; text: string }
export type AgentCard = {
  id: string; name: string; kind: "agent" | "llm"; job: string; lands: string
  tools: { name: string; does: string }[]; tools_note?: string; steps: string[]; prompts?: AgentPrompt[]
}
export type FlowStep = { n: number; actor: string; kind: "agent" | "llm" | "code" | "person"; title: string; note: string }
export type CompareRow = { group: string; label: string; unit: "share" | "count" | "seconds" | "cost"; scripted: number | null; agent: number | null; note?: string }
export type CompareRun = { run_id: string; started: string; cases: number; model: string | null }
export type AgentComparison = { available: boolean; note: string; rows: CompareRow[]; scripted?: CompareRun; agent?: CompareRun }
export type AgentsInfo = {
  model: { spec: string | null; source: "app" | "evaluation" | null }
  limits: { rounds_a_story: number; seconds_a_story: number; seconds_a_run: number } | null
  engines: { scripted: string; agent: string }
  flow: FlowStep[]
  actors: AgentCard[]
  comparison: AgentComparison
  prompts_shown: boolean
}
export async function getAgentsInfo(): Promise<AgentsInfo> {
  const v: unknown = await api("/api/briefing/agents")
  expectObject(v)
  if (!Array.isArray(v.actors) || !Array.isArray(v.flow) || !v.engines || typeof v.engines !== "object" || !v.comparison || typeof v.comparison !== "object") {
    throw new Error("The backend agent description is incompatible with this frontend.")
  }
  return v as unknown as AgentsInfo
}
