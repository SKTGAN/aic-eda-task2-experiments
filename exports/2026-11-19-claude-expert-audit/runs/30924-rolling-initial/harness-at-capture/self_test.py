"""Bounded self-tests before a candidate spends an official evaluation slot.

Three layers run inside the Agent. None of them is a physical evaluation or a score:

1. Static checks always run: Python 3.8 syntax, the official byte limit, the declared experiment
   matches the functions that changed (the manifest), the edit has the intended shape, and no rule
   is keyed to a case or seed identity.
2. Synthetic contract probes run when the Agent runtime can import what they need. The decoder probe
   needs NumPy; the archived formal run shows NumPy importing in the contest Agent container under
   /usr/lib/python3.8. A decoder that calls the frozen reference helper is probed only when a
   supported provider of that helper is configured in HELPER_PROVIDERS (none is, by default);
   otherwise it is reported as skipped. The loss probe needs PyTorch, which no archived run shows
   in the Agent container; without it the probe is skipped. runtime_capabilities() records what
   is available, and the Agent logs it once per run.
3. A planner may ask for a check "on paper" as a declarative spec. Only kinds in ALLOWED_PROBES run,
   with clamped parameters, and their outcome is advisory. Model-written test code never runs.

Probes execute only programs the official validator has already accepted, with the interpreter's
normal builtins, as the evaluator does. A restricted builtins table breaks NumPy: its lazy imports
read __import__ from the calling frame, which is how the archived run rejected a decoder with
"KeyError: '__import__'". A failure of the probe's own environment never blocks a submission.
"""

import ast
import builtins
import importlib
import sys

import ledger as L


MAX_BYTES = 18000            # official program limit in UTF-8 bytes
MAX_NODES = 3000             # official AST node limit (advisory here: the official count is authoritative)
PROBE_GROUPS = 120
PROBE_SEED = 7               # a fixture seed, deliberately not a training seed
PROBE_ITERATIONS = 8
HELPER = "reference_global_two_way"
# (module, attribute) pairs that provide the organizer's own reference helper inside the Agent
# container. Empty until the organizer confirms one; decoders that call the helper are then skipped.
HELPER_PROVIDERS = ()
ALLOWED_PROBES = {
    "decoder_change_vs_parent": {"max_fraction": (0.0, 1.0), "min_fraction": (0.0, 1.0)},
    "decoder_top_area_share": {"tolerance": (0.0, 0.5)},
    "loss_ratio_vs_parent": {"min": (0.01, 100.0), "max": (0.01, 100.0)},
}
FOOTPRINTS = ("structural", "coefficients_only")
# Exceptions that come from the probe's environment rather than from the candidate's own logic.
ENVIRONMENT_ERRORS = (ImportError, NameError, MemoryError, RecursionError)


def finding(check, status, detail=""):
    return {"check": check, "status": status, "detail": detail}


# ----------------------------------------------------------------------------------------------
# Static checks


def _docstring_nodes(tree):
    nodes = set()
    for node in [tree] + [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        body = getattr(node, "body", [])
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            nodes.add(id(body[0].value))
    return nodes


def _mentions(node, name):
    return any(isinstance(child, ast.Name) and child.id == name for child in ast.walk(node))


def identity_rules(source, schedule):
    """Places where the program could branch on a training design or seed identity."""
    tree = ast.parse(source)
    seeds = {int(str(cell["seed"])) for cell in schedule if str(cell["seed"]).isdigit()}
    cases = {cell["case"] for cell in schedule}
    docstrings = _docstring_nodes(tree)
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.IfExp, ast.While)) and _mentions(node.test, "seed"):
            problems.append("line %d branches on seed" % node.lineno)
        elif isinstance(node, ast.Compare) and any(_mentions(part, "seed") for part in [node.left] + node.comparators):
            problems.append("line %d compares seed" % node.lineno)
        elif isinstance(node, ast.Constant) and type(node.value) is int and node.value in seeds:
            problems.append("line %d uses the training seed value %d" % (node.lineno, node.value))
        elif (isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
              and any(case in node.value for case in cases)):
            problems.append("line %d names a training design" % node.lineno)
    return problems


def static_checks(source, parent_source, experiment, schedule):
    """Blocking (fail) and advisory (note) findings; an empty fail list means eligible to submit.

    experiment may declare `component` (the one function that must change), `factors` (the exact
    functions of a splice) and `expect_footprint` (the allowed edit shapes of that function).
    """
    results = []
    try:
        tree = ast.parse(source, feature_version=(3, 8))
    except SyntaxError as error:
        return [finding("python38_syntax", "fail", "line %s: %s" % (error.lineno, error.msg))]
    results.append(finding("python38_syntax", "pass"))
    size = len(source.encode("utf-8"))
    results.append(finding("program_bytes", "fail" if size > MAX_BYTES else "pass", "%d of %d bytes" % (size, MAX_BYTES)))
    nodes = sum(1 for _ in ast.walk(tree))
    results.append(finding("ast_nodes", "note" if nodes > MAX_NODES else "pass", "%d of %d nodes" % (nodes, MAX_NODES)))
    try:
        before, after = L.function_dumps(parent_source), L.function_dumps(source)
    except ValueError as error:
        return results + [finding("manifest", "fail", str(error))]
    changed = sorted(component for component, old, new in zip(L.COMPONENTS, before, after) if old != new)
    declared = [experiment["component"]] if experiment.get("component") else changed
    if changed != declared:
        results.append(finding("manifest", "fail", "the plan declares %s but the program changes %s" % (
            declared or "nothing", changed or "nothing")))
    elif experiment.get("factors") and L.factor_ids(source) != experiment["factors"]:
        results.append(finding("manifest", "fail", "the spliced functions are not the declared measured ones"))
    else:
        results.append(finding("manifest", "pass", "changes %s" % changed))
    expected = experiment.get("expect_footprint")
    if expected and changed == declared and declared:
        shape = L.edit_footprint(parent_source, source)[declared[0]]
        results.append(finding("intervention_shape", "pass" if shape in expected else "fail",
                               "the %s edit is %s; the plan allows %s" % (declared[0], shape, list(expected))))
    problems = identity_rules(source, schedule)
    results.append(finding("identity_rules", "fail" if problems else "pass", "; ".join(problems[:3])))
    return results


# ----------------------------------------------------------------------------------------------
# Runtime and helper resolution


def _module(name):
    try:
        return importlib.import_module(name)
    except Exception:  # absent, or present but unusable in this runtime: the probe is skipped
        return None


def resolve_helper():
    """The organizer's reference helper from a configured provider, or None."""
    for module_name, attribute in HELPER_PROVIDERS:
        module = _module(module_name)
        helper = getattr(module, attribute, None) if module is not None else None
        if callable(helper):
            return helper, "%s.%s" % (module_name, attribute)
    return None, None


def runtime_capabilities():
    """What the probes can use in this process (logged once per run)."""
    numpy, torch = _module("numpy"), _module("torch")
    helper, provider = resolve_helper()
    return {"python": "%d.%d.%d" % sys.version_info[:3],
            "numpy": getattr(numpy, "__version__", None), "torch": getattr(torch, "__version__", None),
            "reference_helper": provider,
            "decoder_probe": "custom decoders" + (" and helper decoders" if helper else "") if numpy else "skipped",
            "loss_probe": "runs" if torch else "skipped"}


def calls_helper(source, index=1):
    """Whether the decoder (index 1) of a program calls the frozen reference helper."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    return any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == HELPER
               for node in ast.walk(functions[index]))


# ----------------------------------------------------------------------------------------------
# Synthetic probes


def _load(source, namespace):
    scope = dict(namespace, __builtins__=builtins)
    exec(compile(source, "<candidate>", "exec"), scope)
    return scope["compute_tp_gnn_loss"], scope["decode_tp_gnn_embeddings"]


def _decoder_fixture(np):
    state = np.random.RandomState(0)
    centers = state.normal(size=(3, 6))
    raw = centers[state.randint(0, 3, PROBE_GROUPS)] + 0.4 * state.normal(size=(PROBE_GROUPS, 6))
    embeddings = raw / np.linalg.norm(raw, axis=1, keepdims=True)
    areas = state.uniform(1.0, 5.0, PROBE_GROUPS)
    areas[:4] = 40.0  # a few large, macro-like groups
    embeddings.setflags(write=False)
    areas.setflags(write=False)
    return embeddings, areas


def _skipped(probe, reason):
    return {"probe": probe, "status": "skipped", "reason": reason}


def decoder_probe(source, parent_source, helper=None):
    """Contract check of the candidate decoder on a fixed fixture; `helper` overrides resolution (tests)."""
    np = _module("numpy")
    if np is None:
        return _skipped("decoder_contract", "NumPy is not importable in the Agent runtime")
    if helper is None:
        helper = resolve_helper()[0]
    if helper is None and calls_helper(source):
        return _skipped("decoder_contract", "the decoder calls %s, which no supported provider offers in the "
                                            "Agent runtime" % HELPER)
    namespace = {"np": np}
    if helper is not None:
        namespace[HELPER] = helper
    embeddings, areas = _decoder_fixture(np)
    try:
        decode = _load(source, namespace)[1]
        first = np.asarray(decode(embeddings, areas, PROBE_SEED, PROBE_ITERATIONS, 0.5))
        second = np.asarray(decode(embeddings, areas, PROBE_SEED, PROBE_ITERATIONS, 0.5))
    except ENVIRONMENT_ERRORS as error:
        return _skipped("decoder_contract", "probe environment: %s: %s" % (type(error).__name__, str(error)[:120]))
    except Exception as error:  # the candidate's own failure on the fixture is the finding
        return {"probe": "decoder_contract", "status": "fail", "reason": "%s: %s" % (type(error).__name__, str(error)[:160])}
    problems = []
    if first.shape != (PROBE_GROUPS,):
        problems.append("returned shape %s instead of (%d,)" % (first.shape, PROBE_GROUPS))
    elif first.dtype.kind not in "iub":
        problems.append("returned %s labels instead of integers" % first.dtype)
    elif not set(np.unique(first).tolist()) <= {0, 1}:
        problems.append("returned labels other than 0 and 1")
    elif first.min() == first.max():
        problems.append("put every group on one die")
    elif not np.array_equal(first, second):
        problems.append("returned different labels for identical inputs")
    if problems:
        return {"probe": "decoder_contract", "status": "fail", "reason": "; ".join(problems)}
    result = {"probe": "decoder_contract", "status": "pass",
              "top_area_share": round(float(areas[first == 1].sum() / areas.sum()), 4)}
    if helper is None and calls_helper(parent_source):
        result["change_vs_parent"] = None
        result["note"] = "the parent decoder calls %s; no comparison" % HELPER
        return result
    try:
        parent = np.asarray(_load(parent_source, namespace)[1](embeddings, areas, PROBE_SEED, PROBE_ITERATIONS, 0.5))
        changed = float((parent != first).mean())
        result["change_vs_parent"] = round(changed, 4)
        result["change_vs_parent_up_to_exchange"] = round(min(changed, 1.0 - changed), 4)
    except Exception as error:  # an advisory comparison only
        result["change_vs_parent"] = None
        result["note"] = "parent decoder did not run on the fixture: %s" % type(error).__name__
    return result


def _loss_inputs(torch, F):
    generator = torch.Generator().manual_seed(0)
    groups, width, positives, negatives, edges, nets = 40, 8, 60, 120, 90, 30
    raw = torch.randn(groups, width, generator=generator, requires_grad=True)
    embeddings = F.normalize(raw, dim=1)
    def pairs(count):
        return (torch.randint(0, groups, (count,), generator=generator),
                torch.randint(0, groups, (count,), generator=generator))
    ps, pt = pairs(positives)
    ns, nt = pairs(negatives)
    gs, gt = pairs(edges)
    features = torch.rand(groups, 10, generator=generator)
    features[:, 0] = features[:, 0] - 0.5  # signed slack
    inputs = {
        "positive_scores": (embeddings[ps] * embeddings[pt]).sum(dim=1),
        "negative_scores": (embeddings[ns] * embeddings[nt]).sum(dim=1),
        "embeddings": embeddings, "positive_sources": ps, "positive_targets": pt,
        "negative_sources": ns, "negative_targets": nt, "source_batch_size": 16, "epoch": 3, "max_epochs": 20,
        "graph_scores": (embeddings[gs] * embeddings[gt]).sum(dim=1), "graph_sources": gs, "graph_targets": gt,
        "graph_net_ids": torch.randint(0, nets, (edges,), generator=generator),
        "graph_weights": torch.rand(edges, generator=generator) + 0.1,
        "net_weights": torch.rand(nets, generator=generator) + 1.0,
        "node_features": features, "node_areas": torch.rand(groups, generator=generator) * 4 + 1,
    }
    return raw, inputs


def loss_probe(source, parent_source):
    torch = _module("torch")
    if torch is None:
        return _skipped("loss_contract", "PyTorch is not importable in the Agent runtime")
    F = importlib.import_module("torch.nn.functional")
    try:
        raw, inputs = _loss_inputs(torch, F)
        snapshot = {name: value.detach().clone() for name, value in inputs.items() if isinstance(value, torch.Tensor)}
        value = _load(source, {"torch": torch, "F": F})[0](**inputs)
    except ENVIRONMENT_ERRORS as error:
        return _skipped("loss_contract", "probe environment: %s: %s" % (type(error).__name__, str(error)[:120]))
    except Exception as error:  # the candidate's own failure on the fixture is the finding
        return {"probe": "loss_contract", "status": "fail", "reason": "%s: %s" % (type(error).__name__, str(error)[:160])}
    problems, notes = [], []
    if not isinstance(value, torch.Tensor) or value.numel() != 1:
        problems.append("did not return one scalar tensor")
    elif not bool(torch.isfinite(value).all()):
        problems.append("returned a non-finite loss")
    elif not value.requires_grad:
        problems.append("returned a loss detached from the embeddings")
    else:
        try:
            value.reshape(()).backward()
        except Exception as error:  # e.g. an in-place operation on a tensor autograd needs
            problems.append("backward failed: %s" % str(error)[:120])
        else:
            if raw.grad is None or not bool(torch.isfinite(raw.grad).all()):
                problems.append("produced non-finite gradients")
            elif float(raw.grad.abs().sum()) == 0.0:
                notes.append("zero gradient on the fixture")
    if not problems and any(not torch.equal(snapshot[name], inputs[name].detach()) for name in snapshot):
        problems.append("changed its inputs")
    if problems:
        return {"probe": "loss_contract", "status": "fail", "reason": "; ".join(problems)}
    result = {"probe": "loss_contract", "status": "pass", "loss": round(float(value.detach()), 6)}
    try:
        _, parent_inputs = _loss_inputs(torch, F)
        parent_value = float(_load(parent_source, {"torch": torch, "F": F})[0](**parent_inputs).detach())
        result["ratio_vs_parent"] = round(result["loss"] / parent_value, 4) if parent_value else None
    except Exception as error:  # an advisory comparison only
        notes.append("parent loss did not run on the fixture: %s" % type(error).__name__)
    if notes:
        result["note"] = "; ".join(notes)
    return result


def accept_spec(spec):
    """A planner's proposed check, reduced to an allowed kind with clamped numeric parameters."""
    if not isinstance(spec, dict) or spec.get("kind") not in ALLOWED_PROBES:
        raise ValueError("unsupported probe kind")
    accepted = {"kind": spec["kind"]}
    for name, (low, high) in ALLOWED_PROBES[spec["kind"]].items():
        value = spec.get(name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            accepted[name] = min(high, max(low, float(value)))
    return accepted


def _expectation(spec, results):
    probe = {row["probe"]: row for row in results}
    decoder, loss = probe.get("decoder_contract", {}), probe.get("loss_contract", {})
    kind = spec["kind"]
    if kind == "decoder_change_vs_parent" and decoder.get("change_vs_parent") is not None:
        value = decoder["change_vs_parent_up_to_exchange"]
        held = spec.get("min_fraction", 0.0) <= value <= spec.get("max_fraction", 1.0)
    elif kind == "decoder_top_area_share" and decoder.get("top_area_share") is not None:
        value = decoder["top_area_share"]
        held = abs(value - 0.5) <= spec.get("tolerance", 0.03)
    elif kind == "loss_ratio_vs_parent" and loss.get("ratio_vs_parent") is not None:
        value = loss["ratio_vs_parent"]
        held = spec.get("min", 0.01) <= value <= spec.get("max", 100.0)
    else:
        return {"probe": "planner_spec", "status": "skipped", "spec": spec, "reason": "the probe it needs did not run"}
    return {"probe": "planner_spec", "status": "note", "spec": spec, "value": value, "expectation_held": held}


def run_probes(source, parent_source, components, spec=None, helper=None):
    """Contract probes for the changed functions, then the planner's accepted spec (advisory)."""
    results = []
    for component, probe in (("decoder", decoder_probe), ("loss", loss_probe)):
        if component not in components:
            continue
        try:
            results.append(probe(source, parent_source, helper) if component == "decoder"
                           else probe(source, parent_source))
        except Exception as error:  # the probe's own environment, not the candidate: never blocks
            results.append(_skipped(component + "_contract", "probe error %s: %s" % (type(error).__name__,
                                                                                    str(error)[:120])))
    if spec is not None:
        try:
            results.append(_expectation(accept_spec(spec), results))
        except ValueError as error:
            results.append(_skipped("planner_spec", str(error)))
    return results
