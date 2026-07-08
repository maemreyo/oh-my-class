# Design Reflection — 2026-07-08

Observations gathered while working two design-interview sessions in this repo
(slide-deck editor design, then real-LLM integration hardening). These are not
bugs I already fixed — they're **patterns** I noticed recurring across the
codebase while fixing the specific bugs, worth a dedicated grill session each.
Each section: what I observed, concrete evidence, and the question worth
grilling.

---

## 0. (Read this one first) Almost none of the "AI teaching-pack generator"'s
##    core pipeline actually calls an LLM in production

This is the single most consequential finding of the whole session — everything
below it (sections 1-8) is about *how LLM calls are made*; this one is about
*whether they're made at all*, in the parts of the pipeline that are supposed
to be the product's actual value proposition.

I audited every sub-agent's real production entry point (traced from
`packages/agents/teaching_pack/nodes.py`, not from the sub-agent's own
directory in isolation — a module can have genuinely real LLM code inside it
and still never run in production if nothing calls that code path). Result:

| Agent | Production reality | Evidence |
|---|---|---|
| **researcher** | ✅ Real — builds a real prompt from real `web_search`/`web_fetch` evidence, calls `AgentRuntime.complete_json_with_retries` | `sub_agents/researcher/nodes.py:29-136`, called from `teaching_pack/nodes.py:385,395` |
| **planner** | ❌ Fake — real LLM branch exists (`nodes.py:50-106`) but is dead code; production hard-codes `"use_staged_planner": True` and routes into pure string templating (`_gagne_plan`, `_verb_for`) | `teaching_pack/nodes.py:327`; templating at `sub_agents/planner/staged_engine.py:192-295` |
| **content_creator** | ❌ Fake for every artifact type — production hard-codes `"use_hierarchical_creator": True`; `_fill_section` is string concatenation (`f"{outline.job}: {fact}"`), no LLM call anywhere in the file. Slide-deck path dispatches to `SlideDeckEngine`, which self-labels its own output `"generation_mode": "slide_deck_engine_deterministic"` | `teaching_pack/nodes.py:486`, `generate_one_artifact.py:49`; `sub_agents/content_creator/hierarchical.py:75-163`; `content_creator/slide_deck_artifact.py:26` |
| **reviewer** | ❌ Fake, and the most dramatic gap — a fully real, tested LLM-as-judge (`AdaptiveJudge`, wired through `AgentRuntime.complete_json`) has **zero non-test callers anywhere**. Production always uses `LiveReviewerQualityGate` instead — a heuristic impostor that checks for `"http://"` substrings and `len(sections) >= 1`, with scores literally computed as `threshold + 1.0` / `threshold - 3.0` | `sub_agents/reviewer/nodes.py:15-77` (orphaned); `teaching_pack/quality_runtime.py:82` always builds `LiveReviewerQualityGate()`; fake scoring at `sub_agents/reviewer/live_quality_gate.py:33-112`; the repo's own `.scratch/agent-upgrades/004-reviewer-revive-and-quality.md` states this outright: *"orphaned — wired only to the dead lead_agent; the live path uses thin deterministic quality"* |
| **diagnostician** | ❌ Fake — same hard-coded-flag-shadowing pattern (`"use_structured_diagnostic": True`) over pure arithmetic/grouping | `teaching_pack/nodes.py:364-370`; `sub_agents/diagnostician/nodes.py:110-127` |
| **unit_planner** / **sequence_critic** | ❌ Fake — no LLM import in either file at all (already flagged by ROADMAP's own audit as `td-006`/`td-021`, confirmed again here) | `sub_agents/unit_planner/nodes.py:31-40` |
| **roadmap_agent** | 🌑 Dark — has a real LLM branch with a real prompt, but **zero non-test callers anywhere in `packages/`** | `sub_agents/roadmap_agent/nodes.py:19-113`; `packages/agents/llm/compiled_chat.py:15` explicitly lists it "not yet migrated" |
| **practice_generator** | ✅ Real code, wired, but its host feature never completes — `run_vocabulary_batch_orchestrator` sets `status="queued"` and stops (ROADMAP's own POTEMKIN verdict) | `sub_agents/practice_generator/semantic_anchor.py:80-125`; `teaching_pack/vocabulary_batch_orchestrator.py:126-147,277` |
| **concept_alignment.py** | 🌑 Dark — genuinely real after this session's fix (routes through `LLMClient`), but still zero production callers | `packages/agents/concept_alignment.py:80-96` |
| **coherence_judge** | 🌑 Dark and non-LLM despite the name — a 9-line re-export of a pure-Python lint, no model call, no caller outside its own test | `sub_agents/coherence_judge/__init__.py` |

**Net effect:** of the five nodes actually wired into the real production
graph, only **researcher** calls an LLM with real data by default. The rest
of the pipeline — planning, content generation for *every* artifact type
including slide decks, and quality review — runs on deterministic
templates and heuristics dressed in agent-shaped names, module structure, and
docstrings that describe LLM behavior the shipped code path never executes.
In most cases this isn't "LLM integration not built yet" — the real,
tested LLM code exists right next to the fake path and is silently shadowed
by one hard-coded boolean at the call site (`use_staged_planner`,
`use_hierarchical_creator`, `use_structured_diagnostic`). This reads like an
interim safety/cost net from earlier development that was never flipped back,
now indistinguishable from "the feature was never finished" without reading
the code.

This is the same "green but hollow" shape ADR-032 already named — but ADR-032
audited runtime *wiring* (does anything call this function). This is one
level deeper: the function IS called, wired into the real graph, has real
tests — and *still* runs the fake branch, because a flag one line above the
call site picked deterministic over real. `scripts/verify_new_component_tests.py`
and the `KNOWN_DARK`/`REQUIRE_WIRED` ledger would not catch this pattern —
both check "is this symbol called," not "is this symbol called with the flag
that actually reaches it."

**Grill this — probably as its own dedicated session, not a quick fix:**
for each of planner/content_creator/reviewer/diagnostician, is the
hard-coded flag a deliberate, currently-correct product decision (e.g. cost
control, latency, an intentional MVP-first sequencing) that should be
formally recorded as such (an ADR: "these stages are deterministic-by-design
until X"), or is it stale leftover from development that should simply be
flipped to the real branch now that `LLMClient` has the governance this
whole session just hardened? The two have very different next actions, and
right now nothing in the repo states which one is true — each existing
`.scratch/agent-upgrades/*.md` issue describes the target upgrade, but not
always accurately (e.g. `003-content-creator-hierarchical-resilient.md`
describes the *current* state as "single-shot-per-artifact" LLM calls, which
doesn't match the fully templated hierarchical dispatcher actually deployed
— the issue spec appears to predate this code and was never reconciled with
it, the same "stale issue vs. reality" pattern as section 3 below applied to
capability specs instead of infrastructure).

---

## 1. No enforced boundary around LLM call governance

`packages/llm_client/client.py`'s `LLMClient` is a well-designed deep module —
circuit breaker, middleware (PII scrub, unsafe-output block, JSON repair),
cost tags, budget tracking. But nothing in the codebase *enforces* that this
is the only way to call an LLM. I found three call sites that quietly built
their own `openai.AsyncOpenAI()` or `litellm.acompletion()` instead:
`packages/agents/teaching_pack/triage.py`, `packages/quality/layer4_judge/judge_transport.py`,
`packages/agents/concept_alignment.py`. All three were fixed this session, but
the *reason* they existed is still true: nothing stops a fourth one from
appearing tomorrow.

The repo already runs `import-linter` in CI (`lint-imports-python` job in
`.github/workflows/ci.yml`) for other boundaries. There's no rule saying
"only `packages/llm_client` may import `openai` or `litellm`."

**Grill this:** should there be an import-linter contract enforcing
"no direct `openai`/`litellm` import outside `packages/llm_client`"? What
about `httpx` calls to `:20228` directly (the smoke-test helper and the
gateway health-probe both do this deliberately — are those legitimate
exceptions, and how does a linter distinguish "legitimate infra probe" from
"someone bypassing governance")?

---

## 2. Config lives in too many independently-evolving places

Found, this session alone:
- Two classes for the same concept with different field names for the same
  setting (`LLMConfig.timeout` vs `LLMClientConfig.timeout_s`) — same env
  prefix, silently reading different env vars.
- Three abandoned router configs (`infra/litellm/`, `services/proxy/`,
  `services/router/`) describing a different port and different model names
  than what's actually running — nobody had reconciled them with reality.
- At least three different env-var *naming conventions* for "where's the LLM
  endpoint": `LLM_BASE_URL`, `LLM_CLIENT_BASE_URL`, `NINEROUTER_BASE_URL`.
- A model name (`"content-fusion"`) hardcoded as a default in
  `AdaptiveJudge.__init__` that only ever existed in one of the now-deleted
  router configs — nothing tied that default to the single source of truth.

This isn't one bug, it's a pattern: **there is no single place that owns
"what LLM config exists and what's the current value," and no mechanism that
detects two things claiming to describe the same setting have drifted apart.**

**Grill this:** should there be one canonical settings module all others
import from (not just for LLM config — `MAX_TOKENS`, `NINEROUTER`, gate
config all currently live as sibling singletons in
`packages/agents/config/models.py`)? Is a config-drift lint feasible (e.g.,
"every env var referenced anywhere in `packages/` must appear in
`.env.example`, and vice versa")?

---

## 3. Superseded architecture doesn't get retired, it accumulates

The entire 9Router-direct-dev + LiteLLM-2-layer-production plan
(`infra/9router/`, `infra/litellm/`, `services/proxy/`, `services/router/`,
root `docker-compose.yml`/`docker-compose.prod.yml`, two `.scratch` issue
docs marked `status: ready`/`deferred`) was superseded by the current
20228/4omc setup — but nothing in the repo said so. The `.scratch` issue for
it was still `status: ready-for-agent`, i.e. actionable-looking, months after
reality moved past it. I only found this by accident, chasing a config-drift
question.

Compare this to how `.scratch/ROADMAP.md`'s audit banner handles superseded
*epics* (a loud, dated, top-of-file correction table) — there's no equivalent
discipline for superseded *infrastructure choices* recorded as ADRs/issues
outside the roadmap's own epic list.

**Grill this:** when an architecture decision is reversed (not iterated —
reversed), what's the retirement ritual? A `status: superseded` convention
already exists informally (I used it for the two issue docs this session) —
should it be a required field, checked by a lint that flags any `.scratch/**/ISSUE.md`
or ADR older than N months with `status: ready`/`deferred` for manual review?

---

## 4. Two methods that look like variants but have different safety guarantees

`LLMClient.chat()` and `LLMClient.stream()` look like "the same call, streamed
or not." They are not: `.stream()` never ran `after_call` (PII scrub,
unsafe-output block, JSON repair) because that transform needs the whole
document, not a token — a legitimate constraint — but the asymmetry was
invisible from the call site. The one production caller
(`packages/agents/llm/chat.py`) used `.stream()` purely to avoid provider
response-size limits, never actually surfaced partial tokens, and got none of
`.chat()`'s safety pipeline as a result. Nothing in the type signature or
method name warned about this.

Similarly, `AdaptiveJudge`'s constructor takes an optional `llm_transport`
override for testability — good dependency-inversion — but its *default*
(when nobody overrides it) was the unsafe, ungoverned path. The safe path
(`reviewer_node`'s injected transport, which routes through `LLMClient`) was
opt-in; the unsafe path was opt-out. "Make illegal states unrepresentable"
was inverted here: the DEFAULT should have been the safe one.

**Grill this:** as a general API-design rule for this codebase — when a
class offers a pluggable seam for testability, should the *default*
implementation always be required to prove it goes through `LLMClient`
(enforced by the same live-path-proof lint that already exists for dark
modules), so "nobody overrode it" never means "nobody validated it"?

---

## 5. Env-var loading has two incompatible conventions in the same codebase

Most config classes use `pydantic-settings`' own `env_file=".env"` (self-
loading per class). Some modules (`packages/agents/healing/circuit_breaker.py`,
`packages/agents/teaching_pack/triage.py` before this session) read
`os.environ.get(...)` directly, which only sees `.env`'s contents if
*something else* already loaded it into the process environment (normally
the gateway's own startup). A bare Python script or a subprocess spawned by
a third-party tool (this session's Promptfoo provider) gets neither — and
silently sees garbage or defaults instead of failing loudly.

This is exactly how the `REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}`
bug surfaced: docker-compose expands `${VAR}` natively; a bare Python process
reading the same file does not, and gets the literal, broken string.

**Grill this:** should every module that reads env vars directly be migrated
onto `pydantic-settings` (one loading mechanism, one place that owns "did
`.env` actually load"), or is the mixed approach intentional for some reason
I'm not seeing? Should `.env`'s `${VAR}`-style entries be banned/linted
against, given they only work under one specific loader?

---

## 6. Detection (audits) is doing the job prevention should be doing

ADR-032 and the 2026-07-01 six-auditor sweep are genuinely excellent — they
caught a systemic false-green pattern. But this session, working on a
completely different area (LLM transport), independently found *more*
instances of the same category of bug that the original audit didn't catch:
`classify_openai_error` (zero callers), `AdaptiveJudge`'s ungoverned default
transport, `Promptfoo` never actually invoked. The dark-module ledger
(`tests/test_no_dark_runtime_modules.py`) is a good *self-maintaining* answer
to this once a symbol is *in* the ledger — but getting a symbol into the
ledger is still manual, driven by whoever happens to read that file next.

**Grill this:** is there a cheap, automatable heuristic for "flag every
function/class defined in `packages/`+`services/` with zero non-test,
non-`__init__.py` callers" as a standing report (not necessarily a hard CI
gate — the ledger already handles known cases), so new dark code surfaces on
its own instead of waiting for the next person who happens to be debugging
something adjacent?

---

## 7. Single-sample non-deterministic LLM output used as a hard pass/fail gate

`tests/security/promptfoo.yaml`'s red-team suite is well-designed content-
wise, but was built with traditional deterministic-test assumptions (assert
X, pass/fail once) applied to inherently probabilistic model output. Live
evidence from this session: across 9 real runs, every one of the 5 scenarios
failed at least once, each time a *different* scenario — including
supposedly-deterministic `not-contains` string checks, because the
*underlying generation* varies run to run, not just LLM-graded `llm-rubric`
assertions. `temperature=0` reduced but did not eliminate this.

This isn't specific to Promptfoo — it's a design question for *any* real-LLM
test in this repo that asserts on generated content rather than on
config/wiring/shape (contrast with `tests/test_harness_llm_routing.py`'s
`smoke_probe`, which only asserts the round-trip works, not what the model
said).

**Grill this:** for tests that must assert on LLM *content* (not just
wiring), should the standard become N-sample majority-vote rather than
single-run pass/fail? Does the existing DeepEval harness
(`tests/quality/test_deepeval_config.py`) have the same single-sample
fragility for its scaffolded-but-not-yet-real assertions once they're wired
up for real?

---

## 8. Half-finished authorization migrations sit fail-closed, silently, indefinitely

(From the slide-deck session.) `services/gateway/auth/ownership.py`'s
`SCHOOL_ADMIN` cross-org path is coded, tested to fail closed, and permanently
unreachable — it depends on an `organization_id` column on `users` that was
never added. The code is safe (fail-closed), but there's no signal anywhere
that this is a *stalled* migration rather than a working, rarely-exercised
path. Someone reading `ownership.py` today has no way to tell those apart
without git-archaeology.

**Grill this:** is there a lightweight convention for "this branch is coded
but blocked on an external migration" — a `# BLOCKED-ON:` marker plus a lint
that lists them, similar to `KNOWN_DARK`'s self-documenting ledger — so
these don't require someone to stumble onto them the way I did?

---

## Cross-cutting theme

Almost every item above is the same shape: **a real, deliberate design
decision (dependency injection, config-per-class, fail-closed defaults,
graceful degradation) that was correct in isolation, but had no mechanism
enforcing that its "safe"/"real" branch stays the one actually taken over
time.** Section 0 is this pattern at its most severe: real, tested,
LLM-calling code sitting one hard-coded flag away from running in
production, silently shadowed instead. The individual fixes this session
were all narrow (sections 1-8); section 0 is not narrow, and is the one
worth grilling first — the higher-leverage fix across everything else is
probably the same one — more of this codebase's already-good self-checking
ledgers (`KNOWN_DARK`/`REQUIRE_WIRED`, `test_no_fake_llm.py`), extended to
catch "called, but behind a flag that never selects the real branch" and not
just "called at all" — and fewer places where "real by convention" is the
only thing standing between today's code and next month's silent drift.
