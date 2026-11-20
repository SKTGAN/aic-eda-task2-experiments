"""Static gate: reject harness or candidate source that Python 3.8 cannot run.

Usage: python3 -I py38_gate.py FILE_OR_DIR [...]
Exit status 1 when any finding is reported.

Two checks run on every .py file:
1. ast.parse(..., feature_version=(3, 8)) rejects syntax newer than 3.8
   (match statements, parenthesized context managers, except*, type params).
2. A name scan flags standard-library attributes and builtins added after 3.8.
   This list is not exhaustive; the replay test in the contest image remains
   the authoritative check.
"""
import ast
import pathlib
import sys

# Methods that exist on built-in or pathlib objects only from a later version.
NEWER_METHODS = {
    "bit_count": "int.bit_count (3.10)",
    "removeprefix": "str.removeprefix (3.9)",
    "removesuffix": "str.removesuffix (3.9)",
    "is_relative_to": "PurePath.is_relative_to (3.9)",
    "with_stem": "PurePath.with_stem (3.9)",
}
# Module attributes, flagged only when written as module.attribute.
NEWER_QUALIFIED = {
    ("math", "lcm"): "math.lcm (3.9)",
    ("math", "nextafter"): "math.nextafter (3.9)",
    ("math", "ulp"): "math.ulp (3.9)",
    ("functools", "cache"): "functools.cache (3.9)",
    ("itertools", "pairwise"): "itertools.pairwise (3.10)",
    ("itertools", "batched"): "itertools.batched (3.12)",
    ("random", "randbytes"): "random.randbytes (3.9)",
    ("asyncio", "to_thread"): "asyncio.to_thread (3.9)",
    ("ast", "unparse"): "ast.unparse (3.9)",
    ("sys", "stdlib_module_names"): "sys.stdlib_module_names (3.10)",
    ("os", "pidfd_open"): "os.pidfd_open (3.9)",
}
NEWER_MODULES = {"zoneinfo": "3.9", "graphlib": "3.9", "tomllib": "3.11"}
NEWER_KEYWORDS = {("zip", "strict"): "zip(strict=) (3.10)",
                  ("dataclass", "slots"): "dataclass(slots=) (3.10)",
                  ("dataclass", "kw_only"): "dataclass(kw_only=) (3.10)"}
BUILTIN_GENERICS = {"list", "dict", "tuple", "set", "frozenset", "type"}


def runtime_annotations_deferred(tree):
    return any(isinstance(node, ast.ImportFrom) and node.module == "__future__"
               and any(alias.name == "annotations" for alias in node.names)
               for node in tree.body)


def scan(path):
    text = path.read_text(encoding="utf-8")
    findings = []
    try:
        ast.parse(text, filename=str(path), feature_version=(3, 8))
    except SyntaxError as error:
        findings.append((error.lineno or 0, "syntax newer than 3.8: %s" % error.msg))
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return findings
    deferred = runtime_annotations_deferred(tree)
    annotation_nodes = set()
    for node in ast.walk(tree):
        for field in ("annotation", "returns"):
            value = getattr(node, field, None)
            if value is not None:
                annotation_nodes.update(id(sub) for sub in ast.walk(value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            label = NEWER_METHODS.get(node.attr)
            if isinstance(node.value, ast.Name):
                label = NEWER_QUALIFIED.get((node.value.id, node.attr), label)
            if label:
                findings.append((node.lineno, label))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in names:
                root = name.split(".")[0]
                if root in NEWER_MODULES:
                    findings.append((node.lineno, "module %s (%s)" % (root, NEWER_MODULES[root])))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("aiter", "anext"):
            findings.append((node.lineno, "builtin %s (3.10)" % node.func.id))
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            for keyword in node.keywords:
                label = NEWER_KEYWORDS.get((name, keyword.arg))
                if label:
                    findings.append((node.lineno, label))
        elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            in_annotation = id(node) in annotation_nodes
            if node.value.id in BUILTIN_GENERICS and not (in_annotation and deferred):
                findings.append((node.lineno, "builtin generic %s[...] evaluated at runtime (3.9)" % node.value.id))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr) and id(node) in annotation_nodes \
                and not deferred:
            findings.append((node.lineno, "X | Y annotation evaluated at runtime (3.10)"))
    return findings


def main(arguments):
    failed = False
    for argument in arguments:
        root = pathlib.Path(argument)
        files = sorted(root.rglob("*.py")) if root.is_dir() else [root]
        for path in files:
            for line, label in scan(path):
                failed = True
                print("%s:%d: %s" % (path, line, label))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
