#!/usr/bin/env python3
"""Validate automqbox/CMP playground simulation contract artifacts.

This validator treats packaged playground as a no-cloud semantic simulation
environment. It fails when artifacts only describe a smoke demo or isolated
fixtures instead of a coherent external-dependency contract, domain fixture
graph, and scenario graph.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


REQUIRED_FILES = [
    "playground-external-dependency-contract.yaml",
    "playground-domain-fixture-graph.yaml",
    "playground-scenario-graph.yaml",
]

ALLOWED_EXTERNAL_CATEGORIES = {
    "cloud-api",
    "cloud api",
    "cloud",
    "k8s",
    "k8s-api",
    "k8s api",
    "kubernetes",
    "kubernetes-api",
    "kubernetes api",
    "kafka-instance-api",
    "kafka instance api",
    "kafka-instance",
    "connect-rest-api",
    "connect rest api",
    "connect-rest",
}

FORBIDDEN_PRODUCT_MOCK_TERMS = [
    "frontend",
    "component",
    "page",
    "api client",
    "api_client",
    "controller",
    "dto",
    "request schema",
    "response schema",
    "service",
    "domain logic",
]

FORBIDDEN_PROTECTION_GROUPS = {
    "frontend component": ["frontend", "component", "page"],
    "api client": ["api client", "api_client", "client"],
    "controller": ["controller"],
    "DTO/request/response schema": ["dto", "request", "response", "schema"],
    "service/domain logic": ["service", "domain"],
}

REAL_CODE_GROUPS = {
    "frontend": ["frontend", "page", "component"],
    "api_client": ["api_client", "api client", "client"],
    "controller": ["controller", "controllers"],
    "service_or_domain": ["service", "services", "domain", "services_or_domain"],
}

CONNECT_SIGNAL_RE = re.compile(
    r"\b(ConnectCluster|connect-cluster|connect cluster|Connector|connectors?|ASG|autoscaling|worker|8083)\b",
    re.IGNORECASE,
)

REQUIRED_CONNECT_FIXTURE_TYPES = {
    "provider-resource",
    "kafka-instance",
    "connect-cluster",
    "connector",
    "connector-task",
    "worker",
    "change-progress",
    "event",
    "metrics",
    "logs",
}

REQUIRED_CONNECT_SCENARIO_TERMS = {
    "detail": ["detail", "/{id}", "详情"],
    "progress/change": ["progress", "change", "last-change", "进度", "变更"],
    "event": ["event", "events", "事件"],
    "connector": ["connector", "connectors", "连接器"],
    "tasks/workers": ["tasks", "workers", "任务", "worker"],
    "metrics": ["metrics", "指标"],
    "logs": ["logs", "日志"],
    "update/resize": ["update", "resize", "PUT", "修改", "容量"],
    "delete": ["delete", "DELETE", "删除"],
}

NEGATIVE_REQUIRED_TERMS = {
    "inactive mode fields absent": ["inactive", "absent", "not submitted", "不提交", "不存在", "K8s", "ASG"],
    "no mock-only endpoint": ["mock-only", "mock only", "mock-only endpoint", "无 mock-only", "不得调用 mock"],
    "no real external call": ["real cloud", "real provider", "real runtime", "真实云", "真实依赖", "outside no-cloud"],
}

PLANNING_STATUSES = {"planned", "pending", "not_run", "not_started", "not_applicable"}
EXECUTION_STATUSES = {"passed", "not_applicable"}


def load_yaml(path: Path) -> Any:
    if yaml is None:
        raise RuntimeError("PyYAML is required")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        raise RuntimeError(f"{path}: invalid YAML: {exc}") from exc


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return [value]


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return text(value)


def rows_from(doc: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = doc.get(key)
    if isinstance(raw, dict):
        rows: list[dict[str, Any]] = []
        for item_id, body in raw.items():
            row = as_dict(body).copy()
            row.setdefault("id", item_id)
            rows.append(row)
        return rows
    return [as_dict(item) for item in as_list(raw)]


def row_status(row: dict[str, Any]) -> str:
    return text(row.get("result") or row.get("status")).lower()


def validate_status(prefix: str, row: dict[str, Any], *, mode: str) -> list[str]:
    errors: list[str] = []
    status = row_status(row)
    allowed = PLANNING_STATUSES if mode == "planning" else EXECUTION_STATUSES
    if status not in allowed:
        errors.append(f"{prefix} has invalid {mode} result/status={status or '<missing>'}")
    if status == "not_applicable" and not text(row.get("na_reason") or row.get("decision")):
        errors.append(f"{prefix} is not_applicable but missing na_reason/decision")
    if mode == "execution" and status == "passed":
        if not text(row.get("evidence")) and not as_list(row.get("evidence_refs")):
            errors.append(f"{prefix} passed without evidence/evidence_refs")
    return errors


def value_for_alias(row: dict[str, Any], aliases: list[str]) -> Any:
    normalized = {str(k).lower().replace("-", "_").replace(" ", "_"): k for k in row}
    for alias in aliases:
        key = alias.lower().replace("-", "_").replace(" ", "_")
        if key in normalized:
            return row.get(normalized[key])
    return None


def contains_group(haystack: str, aliases: list[str]) -> bool:
    normalized = haystack.lower().replace("_", " ")
    return any(alias.lower().replace("_", " ") in normalized for alias in aliases)


def validate_forbidden_mocks(prefix: str, raw: Any) -> list[str]:
    errors: list[str] = []
    items = [text(item) for item in as_list(raw) if text(item)]
    body = flatten(items).lower().replace("_", " ")
    if not items:
        return [f"{prefix} missing forbidden mock protection list"]
    for label, aliases in FORBIDDEN_PROTECTION_GROUPS.items():
        if not contains_group(body, aliases):
            errors.append(f"{prefix} forbidden mocks must explicitly protect {label}")
    return errors


def validate_real_code(prefix: str, raw: Any) -> list[str]:
    errors: list[str] = []
    row = as_dict(raw)
    body = flatten(row)
    if not body:
        return [f"{prefix} missing real_code_under_test/real_consumers"]
    for label, aliases in REAL_CODE_GROUPS.items():
        if value_for_alias(row, aliases) is None and not contains_group(body, aliases):
            errors.append(f"{prefix} real code path missing {label}")
    return errors


def validate_external_contracts(
    change_dir: Path,
    external_doc: dict[str, Any],
    *,
    mode: str,
) -> tuple[list[str], set[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    rows = rows_from(external_doc, "external_dependencies")
    ids: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    if not rows:
        return [f"{change_dir}: playground-external-dependency-contract.yaml must define external_dependencies"], ids, by_id
    for row in rows:
        ext_id = text(row.get("external_dependency_id") or row.get("id"))
        prefix = f"{change_dir}: external dependency {ext_id or '<missing>'}"
        if not ext_id:
            errors.append(f"{change_dir}: external dependency row missing external_dependency_id/id")
            continue
        if ext_id in ids:
            errors.append(f"{change_dir}: duplicate external dependency {ext_id}")
        ids.add(ext_id)
        by_id[ext_id] = row
        category = text(row.get("category")).lower()
        if category not in ALLOWED_EXTERNAL_CATEGORIES:
            errors.append(f"{prefix} category must be external, got {category or '<missing>'}")
        for field in ["real_dependency", "contract_source", "allowed_mock_boundary", "request_semantics", "response_semantics", "error_semantics", "status_semantics"]:
            if not text(row.get(field)) and not as_list(row.get(field)):
                errors.append(f"{prefix} missing {field}")
        mocked_by = as_dict(row.get("mocked_by") or row.get("implemented_by") or row.get("simulated_by"))
        if not mocked_by:
            errors.append(f"{prefix} missing mocked_by/implemented_by/simulated_by")
        else:
            if not text(mocked_by.get("adapter")) and not text(mocked_by.get("simulator")):
                errors.append(
                    f"{prefix} mocked_by must name a no-cloud adapter/simulator; product mocks are not a valid playground acceptance boundary"
                )
        mocked_text = flatten(row.get("allowed_mock_boundary")).lower()
        for term in FORBIDDEN_PRODUCT_MOCK_TERMS:
            if term in mocked_text.replace("_", " "):
                errors.append(f"{prefix} allowed mock boundary appears to mock product logic: {term}")
        errors.extend(validate_forbidden_mocks(prefix, row.get("forbidden_mocks")))
        errors.extend(validate_real_code(prefix, row.get("real_consumers")))
        for field in ["fixture_refs", "scenario_refs"]:
            if not as_list(row.get(field)):
                errors.append(f"{prefix} missing {field}")
        if not as_list(row.get("drift_guards")):
            errors.append(f"{prefix} missing drift_guards")
        errors.extend(validate_status(prefix, row, mode=mode))
    return errors, ids, by_id


def validate_fixture_graph(
    change_dir: Path,
    fixture_doc: dict[str, Any],
    external_ids: set[str],
    *,
    mode: str,
) -> tuple[list[str], set[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    rows = rows_from(fixture_doc, "fixtures")
    ids: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    if not rows:
        return [f"{change_dir}: playground-domain-fixture-graph.yaml must define fixtures"], ids, by_id
    for row in rows:
        fixture_id = text(row.get("fixture_id") or row.get("id"))
        prefix = f"{change_dir}: fixture {fixture_id or '<missing>'}"
        if not fixture_id:
            errors.append(f"{change_dir}: fixture row missing fixture_id/id")
            continue
        if fixture_id in ids:
            errors.append(f"{change_dir}: duplicate fixture {fixture_id}")
        ids.add(fixture_id)
        by_id[fixture_id] = row
        for field in ["type", "state", "contract_source", "provides", "api_consumers", "scenario_refs", "case_refs", "backend_matrix_refs", "frontend_action_refs"]:
            if not text(row.get(field)) and not as_list(row.get(field)):
                errors.append(f"{prefix} missing {field}")
        ext_refs = [text(item) for item in as_list(row.get("external_dependency_refs")) if text(item)]
        if not ext_refs:
            errors.append(f"{prefix} missing external_dependency_refs")
        for ref in ext_refs:
            if ref not in external_ids:
                errors.append(f"{prefix} references unknown external dependency {ref}")
        errors.extend(validate_status(prefix, row, mode=mode))
    for row in rows:
        fixture_id = text(row.get("fixture_id") or row.get("id"))
        prefix = f"{change_dir}: fixture {fixture_id or '<missing>'}"
        for field in ["parents", "children"]:
            for ref in [text(item) for item in as_list(row.get(field)) if text(item)]:
                if ref not in ids:
                    errors.append(f"{prefix} {field} references unknown fixture {ref}")
    combined = flatten(fixture_doc)
    if CONNECT_SIGNAL_RE.search(combined):
        types = {text(row.get("type")).lower() for row in rows}
        missing = REQUIRED_CONNECT_FIXTURE_TYPES - types
        for fixture_type in sorted(missing):
            errors.append(f"{change_dir}: Connect runtime fixture graph missing required fixture type {fixture_type}")
    for closure in rows_from(fixture_doc, "required_graph_closure"):
        closure_id = text(closure.get("closure_id") or closure.get("id"))
        prefix = f"{change_dir}: graph closure {closure_id or '<missing>'}"
        if not closure_id:
            errors.append(f"{change_dir}: graph closure row missing closure_id/id")
            continue
        fixture_refs = [text(item) for item in as_list(closure.get("fixture_refs")) if text(item)]
        scenario_refs = [text(item) for item in as_list(closure.get("scenario_refs")) if text(item)]
        if not fixture_refs:
            errors.append(f"{prefix} missing fixture_refs")
        if not scenario_refs:
            errors.append(f"{prefix} missing scenario_refs")
        for ref in fixture_refs:
            if ref not in ids:
                errors.append(f"{prefix} references unknown fixture {ref}")
    return errors, ids, by_id


def validate_scenarios(
    change_dir: Path,
    scenario_doc: dict[str, Any],
    external_ids: set[str],
    fixture_ids: set[str],
    *,
    mode: str,
) -> tuple[list[str], set[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    rows = rows_from(scenario_doc, "scenarios")
    ids: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    if not rows:
        return [f"{change_dir}: playground-scenario-graph.yaml must define scenarios"], ids, by_id
    for row in rows:
        scenario_id = text(row.get("scenario_id") or row.get("id"))
        prefix = f"{change_dir}: scenario {scenario_id or '<missing>'}"
        if not scenario_id:
            errors.append(f"{change_dir}: scenario row missing scenario_id/id")
            continue
        if scenario_id in ids:
            errors.append(f"{change_dir}: duplicate scenario {scenario_id}")
        ids.add(scenario_id)
        by_id[scenario_id] = row
        for field in ["user_goal", "contract_source", "start_state", "end_state", "backend_matrix_refs", "frontend_action_refs", "packaged_case_refs", "ordered_steps", "negative_assertions", "playground_capability_requirements", "expected_result", "proves"]:
            if not text(row.get(field)) and not as_list(row.get(field)):
                errors.append(f"{prefix} missing {field}")
        errors.extend(validate_real_code(prefix, row.get("real_code_under_test")))
        errors.extend(validate_forbidden_mocks(prefix, row.get("forbidden_mocked_layers") or row.get("forbidden_mocks")))
        ext_refs = [text(item) for item in as_list(row.get("mocked_external_dependency_refs") or row.get("external_dependency_refs")) if text(item)]
        if not ext_refs:
            errors.append(f"{prefix} missing mocked_external_dependency_refs")
        for ref in ext_refs:
            if ref not in external_ids:
                errors.append(f"{prefix} references unknown external dependency {ref}")
        fixture_refs = [text(item) for item in as_list(row.get("fixture_refs")) if text(item)]
        if not fixture_refs:
            errors.append(f"{prefix} missing fixture_refs")
        for ref in fixture_refs:
            if ref not in fixture_ids:
                errors.append(f"{prefix} references unknown fixture {ref}")
        step_text = flatten(row.get("ordered_steps"))
        if CONNECT_SIGNAL_RE.search(flatten(row)):
            for label, terms in REQUIRED_CONNECT_SCENARIO_TERMS.items():
                if not any(term.lower() in step_text.lower() for term in terms):
                    errors.append(f"{prefix} Connect scenario missing downstream step for {label}")
        negative_text = flatten(row.get("negative_assertions")).lower()
        for label, terms in NEGATIVE_REQUIRED_TERMS.items():
            if not any(term.lower() in negative_text for term in terms):
                errors.append(f"{prefix} negative assertions missing {label}")
        for step in [as_dict(item) for item in as_list(row.get("ordered_steps"))]:
            step_id = text(step.get("step_id") or step.get("id"))
            sprefix = f"{prefix} step {step_id or '<missing>'}"
            if not step_id:
                errors.append(f"{prefix} ordered step missing step_id/id")
                continue
            for field in ["action", "frontend_route", "api_routes", "fixture_refs", "expected_state"]:
                if not text(step.get(field)) and not as_list(step.get(field)):
                    errors.append(f"{sprefix} missing {field}")
            for ref in [text(item) for item in as_list(step.get("fixture_refs")) if text(item)]:
                if ref not in fixture_ids:
                    errors.append(f"{sprefix} references unknown fixture {ref}")
        if mode == "execution":
            for field in ["command", "command_exit_code", "executed_by", "assertion_refs", "completed_at", "evidence_refs"]:
                if not text(row.get(field)) and not as_list(row.get(field)):
                    errors.append(f"{prefix} execution mode missing {field}")
        else:
            if not text(row.get("command")):
                errors.append(f"{prefix} missing planned command")
        errors.extend(validate_status(prefix, row, mode=mode))
    for backflow in rows_from(scenario_doc, "scenario_backflow_rules"):
        rule_id = text(backflow.get("rule_id") or backflow.get("id"))
        prefix = f"{change_dir}: scenario backflow rule {rule_id or '<missing>'}"
        if not rule_id:
            errors.append(f"{change_dir}: scenario backflow rule missing rule_id/id")
            continue
        for field in ["trigger", "backflow_target", "required_action"]:
            if not text(backflow.get(field)):
                errors.append(f"{prefix} missing {field}")
        if backflow.get("blocks_acceptance") is not True:
            errors.append(f"{prefix} must set blocks_acceptance: true")
    return errors, ids, by_id


def validate_cross_refs(
    change_dir: Path,
    external_by_id: dict[str, dict[str, Any]],
    fixture_by_id: dict[str, dict[str, Any]],
    scenario_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    fixture_ids = set(fixture_by_id)
    scenario_ids = set(scenario_by_id)
    for ext_id, row in external_by_id.items():
        prefix = f"{change_dir}: external dependency {ext_id}"
        for ref in [text(item) for item in as_list(row.get("fixture_refs")) if text(item)]:
            if ref not in fixture_ids:
                errors.append(f"{prefix} references unknown fixture {ref}")
        for ref in [text(item) for item in as_list(row.get("scenario_refs")) if text(item)]:
            if ref not in scenario_ids:
                errors.append(f"{prefix} references unknown scenario {ref}")
    for fixture_id, row in fixture_by_id.items():
        prefix = f"{change_dir}: fixture {fixture_id}"
        for ref in [text(item) for item in as_list(row.get("scenario_refs")) if text(item)]:
            if ref not in scenario_ids:
                errors.append(f"{prefix} references unknown scenario {ref}")
    used_fixtures: set[str] = set()
    for scenario in scenario_by_id.values():
        used_fixtures |= {text(item) for item in as_list(scenario.get("fixture_refs")) if text(item)}
        for step in [as_dict(item) for item in as_list(scenario.get("ordered_steps"))]:
            used_fixtures |= {text(item) for item in as_list(step.get("fixture_refs")) if text(item)}
    for fixture_id in sorted(fixture_ids - used_fixtures):
        errors.append(f"{change_dir}: fixture {fixture_id} is not consumed by any scenario or ordered step")
    return errors


def optional_yaml(change_dir: Path, rel: str) -> dict[str, Any]:
    path = change_dir / rel
    if not path.exists():
        return {}
    return as_dict(load_yaml(path))


def rows_from_any(doc: dict[str, Any], keys: list[str]) -> list[dict[str, Any]]:
    for key in keys:
        rows = rows_from(doc, key)
        if rows:
            return rows
    return []


def validate_mock_matrix_packaged_runtime_refs(
    change_dir: Path,
    external_ids: set[str],
    fixture_ids: set[str],
    scenario_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    referenced_scenarios: set[str] = set()
    docs: list[tuple[str, list[dict[str, Any]]]] = [
        ("mock-backend-matrix.yaml", rows_from_any(optional_yaml(change_dir, "mock-backend-matrix.yaml"), ["backend_rows", "rows", "matrix"])),
        ("mock-frontend-action-matrix.yaml", rows_from_any(optional_yaml(change_dir, "mock-frontend-action-matrix.yaml"), ["actions", "frontend_actions", "rows", "matrix"])),
        ("mock-acceptance-cases.yaml", rows_from_any(optional_yaml(change_dir, "mock-acceptance-cases.yaml"), ["cases", "rows", "matrix"])),
    ]
    for filename, rows in docs:
        for row in rows:
            rid = text(
                row.get("backend_row_id")
                or row.get("frontend_action_id")
                or row.get("case_id")
                or row.get("row_id")
                or row.get("id")
            ) or "<missing>"
            prefix = f"{change_dir}: {filename} row {rid}"
            ext_refs = [text(item) for item in as_list(row.get("playground_external_dependency_refs")) if text(item)]
            fixture_refs = [text(item) for item in as_list(row.get("playground_domain_fixture_refs")) if text(item)]
            scenario_refs = [text(item) for item in as_list(row.get("playground_scenario_refs")) if text(item)]
            if not ext_refs and not fixture_refs and not scenario_refs:
                continue
            referenced_scenarios |= set(scenario_refs)
            if not ext_refs:
                errors.append(f"{prefix} has playground refs but missing playground_external_dependency_refs")
            if not fixture_refs:
                errors.append(f"{prefix} has playground refs but missing playground_domain_fixture_refs")
            if not scenario_refs:
                errors.append(f"{prefix} has playground refs but missing playground_scenario_refs")
            for ref in ext_refs:
                if ref not in external_ids:
                    errors.append(f"{prefix} references unknown runtime external dependency {ref}")
            for ref in fixture_refs:
                if ref not in fixture_ids:
                    errors.append(f"{prefix} references unknown runtime domain fixture {ref}")
            for ref in scenario_refs:
                if ref not in scenario_ids:
                    errors.append(f"{prefix} references unknown runtime scenario {ref}")
    for scenario_id in sorted(scenario_ids - referenced_scenarios):
        errors.append(
            f"{change_dir}: runtime scenario {scenario_id} is not referenced by backend/frontend matrix or packaged case "
            "through playground_scenario_refs"
        )
    return errors


def validate(change_dir: Path, *, mode: str = "planning") -> list[str]:
    errors: list[str] = []
    if mode not in {"planning", "execution"}:
        return [f"{change_dir}: invalid playground simulation validation mode {mode}"]
    for rel in REQUIRED_FILES:
        if not (change_dir / rel).exists():
            errors.append(f"{change_dir}: missing required playground simulation artifact {rel}")
    if errors:
        return errors

    external_doc = as_dict(load_yaml(change_dir / "playground-external-dependency-contract.yaml"))
    fixture_doc = as_dict(load_yaml(change_dir / "playground-domain-fixture-graph.yaml"))
    scenario_doc = as_dict(load_yaml(change_dir / "playground-scenario-graph.yaml"))

    external_errors, external_ids, external_by_id = validate_external_contracts(change_dir, external_doc, mode=mode)
    errors.extend(external_errors)
    fixture_errors, fixture_ids, fixture_by_id = validate_fixture_graph(change_dir, fixture_doc, external_ids, mode=mode)
    errors.extend(fixture_errors)
    scenario_errors, scenario_ids, scenario_by_id = validate_scenarios(change_dir, scenario_doc, external_ids, fixture_ids, mode=mode)
    errors.extend(scenario_errors)
    errors.extend(validate_cross_refs(change_dir, external_by_id, fixture_by_id, scenario_by_id))
    errors.extend(validate_mock_matrix_packaged_runtime_refs(change_dir, external_ids, fixture_ids, scenario_ids))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("change_dir", type=Path)
    parser.add_argument(
        "--mode",
        choices=["planning", "execution"],
        default="planning",
        help="planning allows planned rows; execution requires passed rows and execution evidence.",
    )
    args = parser.parse_args()
    try:
        errors = validate(args.change_dir, mode=args.mode)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("playground simulation contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
