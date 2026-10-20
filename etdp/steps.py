"""The 18 steps of the ETDP (Kundisch et al., 2022), each marked [I], [N] or [S], and the rules R1–R9.

Every step function performs its work and sets ``state.next_step``.
"""

from __future__ import annotations

import logging

from . import goals
from .classify import drop_removed, examine, taxonomy_view
from .conditions import CONDITIONS, objective
from .context import Context
from .llm.base import LLMError, LLMTruncated
from .documents import fit_query, read_chunks, register_objects, retrieve
from .models import (MISFIT, NO_INFO, Cell, ChoiceOut, Concept, ConceptsOut, IterationRecord, JudgeOut, MetaOut,
                     MetaReviewOut, ObjectsOut, OperationLog, OperationsOut, QueryOut, RunState, Work)
from .operations import RULES, apply_operations

logger = logging.getLogger(__name__)

SUBJECTIVE = ("concise", "robust", "comprehensive", "extendible", "explanatory")
SEARCH_AIMS = {
    "objects": "documents that describe concrete, named objects of the domain (overviews, comparisons, lists, case "
               "studies, documentation, white papers)",
    "concepts": "documents that conceptualize the phenomenon: taxonomies, classifications, typologies, frameworks, "
                "dimensions and characteristics",
    "evaluation": "documents that describe concrete, named objects of the domain, other than those already registered",
}


# --------------------------------------------------------------------------- helpers


def open_iteration(st: RunState, kind: str, reason: str) -> IterationRecord:
    rec = IterationRecord(number=len(st.iterations) + 1, kind=kind, reason=reason)
    st.iterations.append(rec)
    st.work = Work()
    logger.info("=== iteration %d (%s): %s ===", rec.number, kind, reason)
    return rec


def issue_ids(st: RunState) -> list[str]:
    """Stable ids of the open issues: I<iteration that raised them>.<n> (TDR 24)."""
    return [f"I{st.issues_from}.{i + 1}" for i in range(len(st.issues))]


def labelled_issues(st: RunState) -> list[str] | str:
    return [f"{k}: {x}" for k, x in zip(issue_ids(st), st.issues)] or "none"


def set_issues(st: RunState, issues: list[str]) -> None:
    """Record the open issues found at an exit point of the current iteration."""
    st.issues, st.issues_from = issues, st.current.number


def taxonomy_with_counts(st: RunState) -> list[dict]:
    """The taxonomy with, under each characteristic, the number of building objects classified in it; per dimension, those without
    information and those fitting no characteristic."""
    view = taxonomy_view(st.taxonomy.dimensions)
    objs = st.building_objects()
    for d, v in zip(st.taxonomy.dimensions, view):
        for c, cv in zip(d.characteristics, v["characteristics"]):
            cv["objects"] = sum(1 for o in objs if o.cells.get(d.id, Cell()).value == c.id)
            cv["origin"] = c.origin
        v["objects_without_information"] = sum(1 for o in objs if o.cells.get(d.id, Cell()).value == NO_INFO)
        v["objects_fitting_no_characteristic"] = sum(1 for o in objs if o.cells.get(d.id, Cell()).value == MISFIT)
    return view


def formulate_query(ctx: Context, aim: str) -> str:
    """[N] A search string of a few broad keywords; [S] fitted to the range and different from the previous ones.
    A search for objects (Steps 7e and 16) looks for objects the run has not registered yet, never for particular
    characteristics; only a search for concepts (Step 7c) addresses the open issues of the taxonomy."""
    st, m = ctx.state, ctx.cfg.method
    if aim == "concepts":
        focus = ("Meta-characteristic: " + (st.meta_characteristic or "none") + "\nOpen issues of the taxonomy "
                 "(search for literature that helps resolve them; \"none\" if empty):\n" + str(st.issues[:20] or "none"))
    else:
        names = [o.name for o in st.objects.values()][:80]
        focus = ("Objects already registered (search for documents that name OTHER objects of the domain, for example "
                 "by addressing a segment or type of the domain that these do not cover; do not search for particular "
                 "properties of objects):\n" + (", ".join(names) or "none"))
    variables = {**ctx.base_vars(), "aim": SEARCH_AIMS[aim], "seed_keywords": st.input.seed_keywords or "none",
                 "previous_queries": st.queries or "none", "focus": focus,
                 "min_words": m.min_query_words, "max_words": m.max_query_words}
    pad = [*st.input.seed_keywords, st.input.phenomenon, st.input.domain_of_objects]
    query = fit_query(ctx.llm.structured("formulate_query", variables, QueryOut).query, m.min_query_words,
                      m.max_query_words, pad)
    if " ".join(query.split()).casefold() in {" ".join(q.split()).casefold() for q in st.queries}:
        variables["previous_queries"] = st.queries + [f"{query}  <-- already used"]
        query = fit_query(ctx.llm.structured("formulate_query", variables, QueryOut).query, m.min_query_words,
                          m.max_query_words, pad)
    st.queries.append(query)
    if st.iterations:
        st.current.queries.append(query)
    return query


def find_objects(ctx: Context, aim: str, role: str, limit: int | None = None) -> list[str]:
    """Search, read the relevant passages and register objects (Step 7e; also Step 16)."""
    rec = ctx.record
    query = formulate_query(ctx, aim)
    docs = retrieve(ctx, query, rec.number)
    rec.documents += docs
    found = []
    for _, chunk in read_chunks(ctx, docs):
        try:
            found += ctx.llm.structured("extract_objects", {**ctx.base_vars(), "text": chunk}, ObjectsOut).objects
        except LLMError as exc:          # one unreadable passage does not stop the run
            logger.warning("passage skipped, no usable answer: %s", exc)
    return register_objects(ctx, found, docs, rec.number, role=role, limit=limit)


def log_violations(violations: list[str], attempt: int, attempts: int, shown: set[str]) -> None:
    """Show which rules a proposal violates, why, and what is done about it."""
    tags = sorted({v.split()[0] for v in violations if v.split()[0] in RULES})
    logger.info("proposal violates %d rule(s) (attempt %d of %d)", len(violations), attempt, attempts)
    for t in tags:
        if t not in shown:
            logger.info("  %s: %s", t, RULES[t])
            shown.add(t)
    for v in violations:
        logger.info("  - %s", v[:400])
    if attempt < attempts:
        logger.info("  correction: the violations are returned to the LLM, which must answer with a corrected "
                    "list of operations")
    else:
        logger.info("  no correction left: the proposal is rejected")


def propose(ctx: Context, stage: str, origin: str, variables: dict) -> None:
    """Procedure Propose: [N] operations; [S] preconditions and invariants checked on a copy; violations returned
    to the LLM at most r times; a proposal that still violates a rule is rejected (R5)."""
    st, cfg, rec = ctx.state, ctx.cfg, ctx.record
    check = cfg.method.verify_operations
    prompts = ctx.llm.prompts
    base = {**ctx.base_vars(), **variables}
    base["stage"] = prompts.render(f"stage_{stage}", base)
    base["operations_rules"] = prompts.render("operations_rules", base)
    base["taxonomy"] = taxonomy_with_counts(st) or "empty: no dimension yet"
    base["violations"] = "none"
    res = None
    shown: set[str] = set()
    attempts = cfg.method.r + 1 if check else 1
    for k in range(1, attempts + 1):
        try:
            out = ctx.llm.structured("propose_operations", base, OperationsOut)
        except LLMTruncated:
            # a runaway answer (a string that never ends) is not repeated verbatim: the LLM is asked for a short one
            res = None
            msg = ("the previous answer was cut because it was far too long; answer again with a complete, short "
                   "JSON: only the operations that the evidence requires, each reason in one sentence, no repetition")
            rec.attempts.append([msg])
            logger.warning("proposal %d of %d: the answer was cut at max_output_tokens; %s", k, attempts,
                           "asking for a short answer" if k < attempts else "the proposal is rejected")
            base["violations"] = [msg]
            continue
        res = apply_operations(st.taxonomy, out.operations, st.input, cfg, rec.number, origin, check)
        rec.attempts.append(res.violations)
        for line in res.skipped:
            logger.info("  skipped: %s", line)
        logger.info("proposal %d of %d: %d operation(s): %s", k, attempts, len(out.operations),
                    "; ".join(f"{o.op} {o.target or o.name}" for o in out.operations) or "none")
        if not res.violations:
            if k > 1:
                logger.info("proposal accepted after %d correction(s)", k - 1)
            break
        log_violations(res.violations, k, attempts, shown)
        base["violations"] = res.violations
    if res is None or res.violations:
        rec.rejected = True
        st.work.proposal, st.work.operations = None, []
        logger.info("proposal rejected after %d attempt(s); the taxonomy is unchanged", attempts)
    else:
        st.work.proposal, st.work.operations = res.taxonomy, res.logs


def choose(ctx: Context, task: str, options: list[str], variables: dict, default: str) -> tuple[str, str]:
    """[N] The LLM chooses among ``options``."""
    out = ctx.llm.structured(task, {**ctx.base_vars(), **variables, "options": options}, ChoiceOut)
    choice = out.choice.strip()
    return (choice if choice in options else default), "chosen by the LLM: " + out.reason


def history(st: RunState) -> list[dict]:
    return [{"iteration": r.number, "kind": r.kind, "operations": len(r.operations), "exit": r.exit,
             "unmet": [k for k, v in r.objective.items() if not v]} for r in st.iterations]


# --------------------------------------------------------------------------- rules R1–R4


def approach_rule(st: RunState) -> tuple[str, str]:
    """[S] R1–R3."""
    built = [r.kind for r in st.iterations if r.kind in ("c", "e")]
    inp = st.input
    if not built:
        if inp.purpose_type == "identification_and_structuring" and inp.purpose_nature == "descriptive":
            return "e", "R1: identification-and-structuring, descriptive purpose (TDR 7, 8)"
        return "c", "R1: structuring or normative purpose (TDR 7, 8)"
    if len(set(built)) == 1:
        other = "c" if built[0] == "e" else "e"
        return other, "R2: at least one iteration of each approach (TDR 9)"
    objs = st.building_objects()
    empty = [c.id for d in st.taxonomy.dimensions for c in d.characteristics if c.origin == "empirical"
             and not c.negation and not any(o.cells.get(d.id, Cell()).value == c.id for o in objs)]
    if empty:
        return "e", f"R3: characteristics of empirical origin without objects: {empty}"
    if needs_evidence(st):
        return "e", f"R3: the last evaluation calls for new evidence: {needs_evidence(st)}"
    other = "c" if built[-1] == "e" else "e"
    return other, "R3: alternation"


def needs_evidence(st: RunState) -> list[str]:
    """Unmet evaluation criteria whose remedy is new evidence (R3)."""
    return [r["measure"] for r in st.evaluation.get("results", []) if not r["met"] and r["remedy"] == "6"]


def mandatory(ctx: Context) -> list[str]:
    """[S] Requirements that no result can waive, checked when the objective conditions hold: the meta-characteristic is
    reviewed after the first iteration (R4, TDR 5) and, with the symbolic approach selection, at least one iteration of
    each approach was performed (R2, TDR 9)."""
    st = ctx.state
    missing = []
    if not st.meta_reviewed:
        missing.append("review of the meta-characteristic (R4)")
    built = {r.kind for r in st.iterations if r.kind in ("c", "e")}
    if ctx.cfg.method.symbolic_approach and built != {"c", "e"}:
        missing.append(f"an iteration of each approach (R2): only {sorted(built)} so far")
    return missing


def route(ctx: Context, exit_point: str, unmet: list[str], forced: tuple[str, str] | None = None) -> None:
    """Exit after Step 12, 14 or 17: [S] the meta-characteristic is reviewed once (R4); then ``forced`` (R2) or, failing
    that, [N] the LLM chooses the re-entry (a new building iteration or a revision); [S] the run ends at the
    iteration limit."""
    st, cfg, rec = ctx.state, ctx.cfg, ctx.record
    rec.exit = exit_point
    if len(st.iterations) >= cfg.limits.max_iterations:
        st.status = "max_iterations_reached"
        st.message = f"limit of {cfg.limits.max_iterations} iterations reached; unmet at Step {exit_point}: {unmet}"
        st.next_step = "18"
        return
    if not st.meta_reviewed:
        entry, why = "4", "R4: review of the meta-characteristic after the first iteration (TDR 5)"
    elif forced:
        entry, why = forced
    else:
        entry, why = choose(ctx, "choose_entry", ["6", "10"], {"exit": exit_point, "unmet": unmet,
                                                               "history": history(st)}, "6")
    rec.entry, rec.entry_reason = entry, why
    logger.info("exit after Step %s; re-entry before Step %s (%s)", exit_point, entry, why)
    if entry == "10":
        open_iteration(st, "r", why)
    st.next_step = entry


# --------------------------------------------------------------------------- Steps 1–6


def step_1_3(ctx: Context) -> None:
    """[I] phenomenon, target users and purpose(s) are given in the input; [S] it has been validated on loading."""
    inp = ctx.state.input
    logger.info("phenomenon: %s; users: %s; purpose: %s (%s, %s); perspectives: %s", inp.phenomenon, inp.users,
                inp.purpose, inp.purpose_type, inp.purpose_nature, inp.perspective_names)
    ctx.state.next_step = "4"


def step_4(ctx: Context) -> None:
    """Determine the meta-characteristic: [N] formulate it if not supplied; on re-entry, [N] review it and [S] accept
    a refinement once (R4, TDR 5)."""
    st = ctx.state
    if not st.iterations:
        st.meta_characteristic = (st.input.meta_characteristic or
                                  ctx.llm.structured("meta_characteristic", ctx.base_vars(), MetaOut).meta_characteristic)
        logger.info("meta-characteristic: %s", st.meta_characteristic)
        st.next_step = "5"
        return
    out = ctx.llm.structured("meta_review", {**ctx.base_vars(), "taxonomy": taxonomy_with_counts(st)}, MetaReviewOut)
    st.meta_reviewed = True
    new = out.meta_characteristic.strip()
    if out.keep or not new:
        st.current.meta_review = f"kept ({out.reason})"
    elif not stays_in_domain(ctx, st.meta_characteristic, new):
        st.current.meta_review = (f"refinement rejected by R4, as it moves away from the domain of objects: {new!r} "
                                  f"({out.reason})")
    else:
        st.current.meta_review = f"refined: {st.meta_characteristic!r} -> {new!r} ({out.reason})"
        st.meta_characteristic = new
    logger.info("meta-characteristic review: %s", st.current.meta_review)
    st.next_step = "6"


def stays_in_domain(ctx: Context, old: str, new: str) -> bool:
    """[S] R4: a refined meta-characteristic is accepted only if it is at least as close ([N] embeddings) to the
    designer's domain of objects as the current one; the domain is fixed input [I]."""
    sims = ctx.embedder.similarity([ctx.state.input.domain_of_objects], [old, new])[0]
    return float(sims[1]) >= float(sims[0])


def step_5(ctx: Context) -> None:
    """[S] Ending conditions (O1–O3, O5–O8, O10) and the five subjective conditions; for each evaluation goal of the input, its
    method, criteria and targets from the registry of Kundisch et al. (2022, Table 4) (TDR 6, 20)."""
    st = ctx.state
    chosen = [g.model_dump() for g in st.input.evaluation_goals]
    unknown = goals.unknown_targets(chosen)
    if unknown:
        raise ValueError(f"unknown evaluation targets in the input: {unknown}")
    known = {c.key for g in goals.GOALS.values() for c in g.criteria}
    if set(ctx.cfg.evaluation.targets) - known:
        raise ValueError("unknown evaluation targets in the configuration: "
                         f"{sorted(set(ctx.cfg.evaluation.targets) - known)}")
    st.evaluation_plan = goals.plan(chosen, ctx.cfg.evaluation.targets)
    st.next_step = "6"


def step_6(ctx: Context) -> None:
    """Building approach: [S] R1–R3 (ablation: [N] the LLM chooses)."""
    st, cfg = ctx.state, ctx.cfg
    if cfg.method.symbolic_approach:
        kind, why = approach_rule(st)
    else:
        kind, why = choose(ctx, "choose_approach", ["c", "e"], {"history": history(st),
                                                                "objects": len(st.building_objects())}, "e")
    open_iteration(st, kind, why)
    st.next_step = "7e" if kind == "e" else "7c"


# --------------------------------------------------------------------------- Steps 7e–9e


def step_7e(ctx: Context) -> None:
    """Identify objects: [N] search string; [S] Retrieve; [N] identify named objects; [S] register them."""
    st = ctx.state
    st.work.new_object_ids = find_objects(ctx, "objects", "building")
    ctx.record.new_objects = list(st.work.new_object_ids)
    st.next_step = "8e"


def step_8e(ctx: Context) -> None:
    """Identify common characteristics and group objects: [N] classify the new objects in the taxonomy and code the
    characteristics it lacks."""
    st = ctx.state
    objs = [st.objects[i] for i in st.work.new_object_ids]
    _, codes = examine(ctx, st.taxonomy, objs, coding=True)
    st.work.codes = codes
    ctx.record.codes = len(codes)
    st.next_step = "9e"


def step_9e(ctx: Context) -> None:
    """Group characteristics into dimensions: [N] operations grouping the codes; [S] verify and correct (R5)."""
    st = ctx.state
    objs = {o.id: o for o in st.building_objects()}
    misfits = [f"{o.id} '{o.name}' in {d.id} '{d.name}'" for o in objs.values() for d in st.taxonomy.dimensions
               if (c := o.cells.get(d.id)) and c.value == MISFIT]
    if st.work.codes or misfits:
        codes = [{"object": c.object_id, "object_name": objs[c.object_id].name, "code": c.label,
                  "definition": c.definition} for c in st.work.codes if c.object_id in objs]
        propose(ctx, "e", "empirical", {"codes": codes or "none", "misfits": misfits or "none",
                                        "issues": labelled_issues(st)})
    st.next_step = "10"


# --------------------------------------------------------------------------- Steps 7c–8c


def step_7c(ctx: Context) -> None:
    """Conceptualize characteristics and dimensions: [N] search string; [S] Retrieve; [N] concepts from the
    literature and existing taxonomies; [N] operations; [S] verify and correct."""
    st, rec = ctx.state, ctx.record
    query = formulate_query(ctx, "concepts")
    docs = retrieve(ctx, query, rec.number)
    rec.documents += docs
    concepts: list[Concept] = []
    for doc_id, chunk in read_chunks(ctx, docs):
        try:
            extracted = ctx.llm.structured("extract_concepts", {**ctx.base_vars(), "text": chunk}, ConceptsOut).concepts
        except LLMError as exc:          # one unreadable passage does not stop the run
            logger.warning("passage skipped, no usable answer: %s", exc)
            continue
        for c in extracted:
            if not c.name.strip():
                continue
            concepts.append(Concept(id=f"K{st.next_concept}", kind=c.kind, name=c.name.strip(),
                                    definition=c.definition, dimension=c.dimension, doc_id=doc_id))
            st.next_concept += 1
    st.work.concepts = concepts
    rec.concepts = len(concepts)
    if concepts:
        propose(ctx, "c", "conceptual", {
            "concepts": [{"id": c.id, "kind": c.kind, "name": c.name, "definition": c.definition,
                          "dimension": c.dimension} for c in concepts],
            "issues": labelled_issues(st)})
    st.next_step = "8c"


def step_8c(ctx: Context) -> None:
    """Examine objects for these characteristics and dimensions: [N] classify all objects in the new or changed
    dimensions. Conceptual elements without objects are flagged by O3."""
    st = ctx.state
    if st.work.proposal is not None:
        examine(ctx, st.work.proposal, st.building_objects())
    st.next_step = "10"


# --------------------------------------------------------------------------- Step 10


def prune_empty(ctx: Context) -> None:
    """[S] R6: a revision adjusts the taxonomy and brings no evidence: a characteristic that it created and that no
    building object was classified in is removed again (a negation characteristic needs no object), and so is a
    dimension that it created and that is left without enough characteristics. Cells of the other characteristics
    stay valid, so nothing is classified again."""
    st, rec = ctx.state, ctx.record
    objs, min_chars = st.building_objects(), ctx.cfg.method.min_characteristics_per_dimension
    removed: list[str] = []
    for d in list(st.taxonomy.dimensions):
        used = {o.cells[d.id].value for o in objs if d.id in o.cells}
        gone = [c for c in d.characteristics if c.iteration == rec.number and not c.negation and c.id not in used]
        if not gone:
            continue
        d.characteristics = [c for c in d.characteristics if c not in gone]
        removed += [c.id for c in gone]
        if d.iteration == rec.number and len(d.characteristics) < min_chars:
            st.taxonomy.dimensions.remove(d)
            removed.append(d.id)
            continue
        for o in objs:
            if d.id in o.cells:
                o.cells[d.id].key, o.cells[d.id].text = d.signature(), d.wording()
    if removed:
        log = OperationLog(iteration=rec.number, op="delete", removed=removed,
                           reason="revision: no classified object has the element, which a revision cannot create")
        rec.operations.append(log)
        st.operations_log.append(log)
        drop_removed(list(st.objects.values()), st.taxonomy)
        logger.info("  removed again, without objects: %s", ", ".join(removed))


def step_10(ctx: Context) -> None:
    """Create / revise taxonomy: on re-entry, [N] operations resolving the open issues and [S] verification; [S] apply
    the verified operations, keeping identifiers, and log them (TDR 24); [N] classify objects in changed dimensions."""
    st, rec = ctx.state, ctx.record
    if rec.kind == "r":
        propose(ctx, "r", "empirical", {"issues": labelled_issues(st)})
    if st.work.proposal is not None:
        st.taxonomy = st.work.proposal
        rec.operations = st.work.operations
        st.operations_log += st.work.operations
    st.work.proposal = None
    drop_removed(list(st.objects.values()), st.taxonomy)
    examine(ctx, st.taxonomy, st.building_objects())
    if rec.kind == "r" and ctx.cfg.method.verify_operations:
        prune_empty(ctx)
    logger.info("taxonomy: %d dimensions; %d operations applied", len(st.taxonomy.dimensions), len(rec.operations))
    for o in rec.operations:
        logger.info("  %s %s: %s", o.op, ", ".join(o.created or o.targets), o.reason[:200])
    st.next_step = "11-12"


# --------------------------------------------------------------------------- Steps 11–17


def step_11_12(ctx: Context) -> None:
    """[S] Objective ending conditions O1–O3, O5–O8 and O10, recorded in every iteration (TDR 17); the required review of
    the meta-characteristic and iteration of each approach (R4, R2) are enforced even if all hold."""
    st, rec = ctx.state, ctx.record
    ok, det, issues = objective(st, ctx.cfg)
    rec.objective, rec.objective_details = ok, det
    set_issues(st, issues)
    unmet = [k for k, v in ok.items() if not v]
    logger.info("objective conditions unmet: %s", unmet or "none")
    for k in unmet:
        logger.info("  %s %s: %s", k, CONDITIONS[k], det[k])
    if unmet:
        route(ctx, "12", unmet)
    elif missing := mandatory(ctx):
        logger.info("objective conditions hold, but required: %s", "; ".join(missing))
        route(ctx, "12", [f"required: {m}" for m in missing],
              ("6", "R2: at least one iteration of each approach (TDR 9)"))
    else:
        st.next_step = "13-14"


def judge_memory(st: RunState) -> str:
    """[S] What the judge decided before and what was changed since: the last subjective verdict and the operations
    of the iterations that followed it (including the current one), so that it does not contradict itself."""
    last = next((r for r in reversed(st.iterations[:-1]) if r.subjective), None)
    if last is None:
        return "none (first assessment)"
    lines = [f"Previous assessment (iteration {last.number}):"]
    for c, r in last.subjective.items():
        lines.append(f"- {c}: {'met' if r['passed'] else 'NOT met'}. {r['justification']}")
    ops = [o for r in st.iterations if r.number > last.number for o in r.operations]
    lines.append("Operations applied since, to resolve the issues you raised:")
    lines += [f"- {o.op} {o.targets} -> {o.created or o.removed or ''}: {o.reason}" for o in ops] or ["- none"]
    return "\n".join(lines)


def step_13_14(ctx: Context) -> None:
    """[N] The judge, acting as taxonomy designer, assesses the subjective conditions; [S] each holds if the judge
    deems it met; unmet conditions and the judge's suggestions become open issues (R8)."""
    st, rec = ctx.state, ctx.record
    out = ctx.llm.structured("judge_subjective", {**ctx.base_vars(), "taxonomy": taxonomy_with_counts(st),
                                                  "objects": len(st.building_objects()),
                                                  "memory": judge_memory(st)}, JudgeOut)
    result, suggestions = {}, []
    for cond in SUBJECTIVE:
        items = [e for e in out.evaluations if e.condition == cond]
        passed = bool(items) and all(e.passed for e in items)
        result[cond] = {"passed": passed, "justification": " ".join(e.justification for e in items)}
        if not passed:
            suggestions += [f"subjective '{cond}': {x}" for e in items for x in e.suggestions]
            if not any(e.suggestions for e in items):
                suggestions.append(f"subjective '{cond}' not met")
    rec.subjective = result
    unmet = [c for c, r in result.items() if not r["passed"]]
    logger.info("subjective conditions met: %s; unmet: %s", [c for c in SUBJECTIVE if c not in unmet] or "none",
                unmet or "none")
    for c in unmet:
        logger.info("  %s: %s", c, result[c]["justification"])
    for x in suggestions:
        logger.info("  suggestion %s", x)
    if unmet:
        set_issues(st, suggestions)
        route(ctx, "14", unmet)
    else:
        st.next_step = "15-16"


def step_15_16(ctx: Context) -> None:
    """Configure (plan of Step 5) and perform the evaluation: [N][S] new objects identified as in Step 7e, not used in
    building (TDR 21); [N] classified twice, independently; [S] the measures of the registry (R9)."""
    st, cfg, rec = ctx.state, ctx.cfg, ctx.record
    new = find_objects(ctx, "evaluation", "evaluation", cfg.evaluation.new_objects)
    objs = [st.objects[i] for i in new]
    first, _ = examine(ctx, st.taxonomy, objs, only_stale=False)
    second, _ = examine(ctx, st.taxonomy, objs, store=False, only_stale=False, variant=rec.number)
    measures = goals.measure(objs, first, second, st.building_objects() + objs,
                             [d.id for d in st.taxonomy.dimensions], cfg.evaluation.dominance_threshold,
                             cfg.evaluation.max_groups)
    measures["new_object_ids"] = new
    rec.evaluation = st.evaluation = measures
    st.next_step = "17"


def step_17(ctx: Context) -> None:
    """[S] Every criterion of the plan compared with its target. New objects of a failed evaluation join the
    building objects; the LLM chooses the re-entry, informed of the remedy that the registry suggests per criterion."""
    st, cfg, rec = ctx.state, ctx.cfg, ctx.record
    results = goals.assess(st.evaluation_plan, st.evaluation, cfg.evaluation.new_objects)
    st.evaluation["results"] = rec.evaluation["results"] = results
    unmet = [f"{r['goal']}: {r['measure']} = {r['value']} (target {r['comparator']} {r['target']}; "
             f"suggested re-entry: {'new evidence' if r['remedy'] == '6' else 'revision'})"
             for r in results if not r["met"]]
    if not unmet:
        st.status = "completed"
        st.next_step = "18"
        return
    for i in st.evaluation.get("new_object_ids", []):
        st.objects[i].role = "building"
    set_issues(st, [f"evaluation: {u}" for u in unmet])
    route(ctx, "17", unmet)


def step_18(ctx: Context) -> None:
    """[S] Report: taxonomy, definitions, evolution and conditions per iteration (TDR 24–26)."""
    from .export import write_outputs

    write_outputs(ctx.state, ctx.run_dir, ctx.cfg)
    ctx.state.next_step = "done"


STEPS = {"1-3": step_1_3, "4": step_4, "5": step_5, "6": step_6, "7e": step_7e, "8e": step_8e, "9e": step_9e,
         "7c": step_7c, "8c": step_8c, "10": step_10, "11-12": step_11_12, "13-14": step_13_14,
         "15-16": step_15_16, "17": step_17, "18": step_18}
