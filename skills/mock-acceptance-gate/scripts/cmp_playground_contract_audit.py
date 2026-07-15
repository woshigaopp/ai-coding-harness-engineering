#!/usr/bin/env python3
"""Static audit for automqbox/CMP playground real-controller routing.

Current packaged playground acceptance runs real product controllers/services/tasks
and replaces only physical external dependency beans through the playground
profile. For every affected product controller, acceptance requires
REAL_CONTROLLER_PATH via PlaygroundAcceptanceProperties.realControllerClasses.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import sys
from collections.abc import Iterable


JAVA_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "new",
    "throw",
    "else",
    "do",
    "try",
    "finally",
    "synchronized",
}


@dataclasses.dataclass(frozen=True)
class JavaMethod:
    name: str
    return_type: str
    params: tuple[str, ...]
    file: pathlib.Path
    line: int


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


def line_number(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def normalize_type(type_name: str) -> str:
    type_name = re.sub(r"@\w+(?:\([^)]*\))?\s*", "", type_name)
    type_name = re.sub(r"\b(final|volatile|transient)\b\s*", "", type_name)
    return re.sub(r"\s+", " ", type_name.strip())


def erase_generics(type_name: str) -> str:
    out: list[str] = []
    depth = 0
    for char in type_name:
        if char == "<":
            depth += 1
            continue
        if char == ">":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            out.append(char)
    return normalize_type("".join(out))


def simple_type(type_name: str) -> str:
    type_name = erase_generics(type_name).replace("...", "[]")
    return type_name.split()[-1].split(".")[-1] if type_name.split() else type_name


def split_params(param_text: str) -> tuple[str, ...]:
    param_text = param_text.strip()
    if not param_text:
        return ()
    params: list[str] = []
    current: list[str] = []
    depth_angle = 0
    depth_paren = 0
    for char in param_text:
        if char == "<":
            depth_angle += 1
        elif char == ">":
            depth_angle = max(0, depth_angle - 1)
        elif char == "(":
            depth_paren += 1
        elif char == ")":
            depth_paren = max(0, depth_paren - 1)
        elif char == "," and depth_angle == 0 and depth_paren == 0:
            params.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if current:
        params.append("".join(current).strip())
    return tuple(parse_param_type(param) for param in params if param)


def parse_param_type(param: str) -> str:
    param = normalize_type(re.sub(r"@\w+(?:\([^)]*\))?\s*", "", param))
    tokens = param.split()
    if len(tokens) <= 1:
        return simple_type(param)
    return simple_type(" ".join(tokens[:-1]))


def parse_methods(java_file: pathlib.Path) -> dict[str, list[JavaMethod]]:
    raw = java_file.read_text(encoding="utf-8", errors="ignore")
    text = strip_comments(raw)
    pattern = re.compile(
        r"(?P<prefix>(?:@\w+(?:\([^)]*\))?\s*)*)"
        r"(?P<mods>\b(?:public|protected|private)\b[\w\s<>,.?&\[\]@]*)\s+"
        r"(?P<ret>[\w$.<>,?&\[\]\s]+?)\s+"
        r"(?P<name>[A-Za-z_]\w*)\s*"
        r"\((?P<params>[^;{}()]*(?:\([^)]*\)[^;{}()]*)*)\)\s*"
        r"(?:throws\s+[\w$.,\s<>]+)?\{",
        flags=re.M,
    )
    methods: dict[str, list[JavaMethod]] = {}
    for match in pattern.finditer(text):
        name = match.group("name")
        if name in JAVA_KEYWORDS:
            continue
        return_type = normalize_type(match.group("ret"))
        if not return_type or return_type in JAVA_KEYWORDS:
            continue
        method = JavaMethod(
            name=name,
            return_type=return_type,
            params=split_params(match.group("params")),
            file=java_file,
            line=line_number(text, match.start("name")),
        )
        methods.setdefault(name, []).append(method)
    return methods


def package_name(java_file: pathlib.Path) -> str | None:
    text = java_file.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^\s*package\s+([\w.]+)\s*;", text, flags=re.M)
    return match.group(1) if match else None


def fqcn(java_file: pathlib.Path) -> str | None:
    pkg = package_name(java_file)
    return f"{pkg}.{java_file.stem}" if pkg else None


def cmp_root(root: pathlib.Path) -> pathlib.Path:
    return root / "cmp" if (root / "cmp" / "cmp-app").exists() else root


def find_controller_files(root: pathlib.Path) -> dict[str, pathlib.Path]:
    files: dict[str, pathlib.Path] = {}
    for path in root.glob("cmp-app/src/main/java/com/automq/cmp/controller/**/*Controller.java"):
        name = fqcn(path)
        if name:
            files[name] = path
    for path in root.glob("cmp-ops-tunnel/src/main/java/**/*Controller.java"):
        name = fqcn(path)
        if name:
            files[name] = path
    return files


def read_real_controller_allowlist(root: pathlib.Path) -> set[str]:
    allowlist: set[str] = set()
    props = (
        root
        / "cmp-playground"
        / "src"
        / "main"
        / "java"
        / "com"
        / "automq"
        / "cmp"
        / "playground"
        / "config"
        / "PlaygroundAcceptanceProperties.java"
    )
    if not props.exists():
        return allowlist
    text = strip_comments(props.read_text(encoding="utf-8", errors="ignore"))
    allowlist.update(re.findall(r'"(com\.automq\.cmp\.[^"]+Controller)"', text))
    return allowlist


def interesting_controller(fq_controller: str, only: set[str]) -> bool:
    if not only:
        return True
    short = fq_controller.rsplit(".", 1)[-1]
    return fq_controller in only or short in only or short.removesuffix("Controller") in only


def markdown_row(cols: Iterable[object]) -> str:
    return "| " + " | ".join(str(col).replace("\n", " ").replace("|", "\\|") for col in cols) + " |"


def find_product_replacements(root: pathlib.Path) -> list[pathlib.Path]:
    packaged_runtime = root / "cmp-playground" / "src" / "main" / "java"
    replacements: list[pathlib.Path] = []
    if not packaged_runtime.exists():
        return replacements
    forbidden_packages = (
        "com.automq.cmp.controller",
        "com.automq.cmp.service",
        "com.automq.cmp.manager",
        "com.automq.cmp.task",
        "com.automq.cmp.model",
    )
    for path in packaged_runtime.glob("**/*.java"):
        pkg = package_name(path) or ""
        if pkg.startswith(forbidden_packages) and ".playground" not in pkg:
            replacements.append(path)
    return replacements


def render_report(root: pathlib.Path, only: set[str]) -> tuple[str, int]:
    source_root = cmp_root(root)
    controllers = find_controller_files(source_root)
    real_controller_allowlist = read_real_controller_allowlist(source_root)
    rows: list[list[object]] = []
    failures = 0
    matched_requested: set[str] = set()

    if not real_controller_allowlist:
        failures += 1
        rows.append([
            "PlaygroundAcceptanceProperties",
            "",
            "",
            "ALLOWLIST_NOT_FOUND",
            "cmp-playground must define realControllerClasses for playground acceptance",
            "yes",
            "cmp-playground/src/main/java/.../PlaygroundAcceptanceProperties.java",
        ])

    for controller, controller_file in sorted(controllers.items()):
        if not interesting_controller(controller, only):
            continue
        short = controller.rsplit(".", 1)[-1]
        matched_requested.update({controller, short, short.removesuffix("Controller")})
        finding = "REAL_CONTROLLER_PATH" if controller in real_controller_allowlist else "NOT_REAL_CONTROLLER_PATH"
        blocks = finding != "REAL_CONTROLLER_PATH"
        if blocks:
            failures += 1
        methods = parse_methods(controller_file)
        if not methods:
            rows.append([
                short,
                "",
                "",
                finding,
                "controller has no parsed public/protected/private methods",
                "yes" if blocks else "no",
                str(controller_file),
            ])
            continue
        for parsed_methods in methods.values():
            for method in parsed_methods:
                rows.append([
                    short,
                    f"{method.name}({', '.join(method.params)})",
                    method.return_type,
                    finding,
                    (
                        "allowlisted in PlaygroundAcceptanceProperties.realControllerClasses"
                        if not blocks
                        else "affected controller must be added to realControllerClasses; do not close through a product mock"
                    ),
                    "yes" if blocks else "no",
                    f"{method.file}:{method.line}",
                ])

    for requested in sorted(only):
        if requested not in matched_requested:
            failures += 1
            rows.append([
                requested,
                "",
                "",
                "CONTROLLER_NOT_FOUND",
                "requested affected controller was not found in app/ops-tunnel sources",
                "yes",
                "check controller name/FQCN or repository root",
            ])

    replacements = find_product_replacements(source_root)
    for path in replacements:
        failures += 1
        rows.append([
            path.stem,
            "",
            "",
            "PRODUCT_CLASS_REPLACEMENT",
            "cmp-playground must not define product controller/service/manager/task/model packages",
            "yes",
            str(path),
        ])

    lines = [
        "# Packaged Runtime Real Controller Routing Audit",
        "",
        markdown_row([
            "Controller",
            "Controller method",
            "Controller return",
            "Finding",
            "Required action",
            "Blocks acceptance",
            "Evidence",
        ]),
        markdown_row(["---", "---", "---", "---", "---", "---:", "---"]),
    ]
    lines.extend(markdown_row(row) for row in rows)
    lines.extend([
        "",
        "## Rule",
        "",
        (
            "Current packaged playground acceptance requires every affected product controller to execute as "
            "`REAL_CONTROLLER_PATH`. `cmp-playground` is packaged into `cmp-app` under the playground "
            "profile and may replace only physical external dependency beans through no-cloud adapters. "
            "If a new feature adds a controller or exposes a new route, add that controller to "
            "`PlaygroundAcceptanceProperties.realControllerClasses`, seed or create the required real "
            "database/no-cloud graph state, and extend the external adapters instead of replacing the "
            "business controller/service path."
        ),
        "",
        f"Summary: {failures} blocking finding(s), {len(rows)} audited row(s).",
    ])
    return "\n".join(lines) + "\n", failures


def run(root: pathlib.Path, only: set[str], fail_on_any_gap: bool, out: pathlib.Path | None) -> int:
    report, failures = render_report(root, only)
    print(report, end="")
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
    if failures and fail_on_any_gap:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Path to automqbox repository root")
    parser.add_argument(
        "--controllers",
        default="",
        help="Comma-separated affected controller names/FQCNs, e.g. ConnectorController,ProviderController",
    )
    parser.add_argument("--out", default="", help="Optional markdown report path")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Print findings but exit 0. Use only for exploratory archaeology, not acceptance.",
    )
    args = parser.parse_args()

    root = pathlib.Path(args.repo).expanduser().resolve()
    only = {item.strip() for item in args.controllers.split(",") if item.strip()}
    if not root.exists():
        print(f"Repository root does not exist: {root}", file=sys.stderr)
        return 2
    out = pathlib.Path(args.out).expanduser().resolve() if args.out else None
    return run(root, only, fail_on_any_gap=not args.warn_only, out=out)


if __name__ == "__main__":
    raise SystemExit(main())
