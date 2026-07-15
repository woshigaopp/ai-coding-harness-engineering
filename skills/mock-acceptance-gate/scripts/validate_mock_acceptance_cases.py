#!/usr/bin/env python3
"""Validate strict mock acceptance case artifacts.

This gate intentionally treats mock acceptance as a generated test system, not
as a prose smoke summary. It validates that finite dimensions produce concrete
case rows, each case has fixture, browser, network, DOM, API, negative, and
evidence bindings, and the markdown report carries row-level results.
"""

from __future__ import annotations

import argparse
import itertools
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


REQUIRED_FILES = [
    "mock-backend-matrix.yaml",
    "mock-frontend-action-matrix.yaml",
    "mock-test-dimensions.yaml",
    "mock-acceptance-cases.yaml",
    "mock-fixture-graph.yaml",
    "mock-acceptance.md",
]
OPTIONAL_STATEFUL_FILE = "mock-event-state-matrix.yaml"
EXECUTION_LEDGER_FILE = "mock-acceptance-execution.yaml"
PLANNING_STATUSES = {"planned", "pending", "not_run", "not_started", "not_applicable"}
EXECUTION_STATUSES = {"passed", "not_applicable"}
PLAYGROUND_SIMULATION_FILES = [
    "playground-external-dependency-contract.yaml",
    "playground-domain-fixture-graph.yaml",
    "playground-scenario-graph.yaml",
]

REQUIRED_REPORT_SECTIONS = [
    "Mock Acceptance Summary",
    "Acceptance Context Rehydration",
    "Dimension Coverage Matrix",
    "Backend Mock Matrix",
    "Frontend Action Matrix",
    "Case Execution Matrix",
    "Fixture Graph Matrix",
    "Frontend User-Flow Local Audit Report",
    "Backend Flow Local Audit Report",
    "Contract Source Local Audit Report",
    "Real Controller / No-Cloud Guard Report",
    "Runtime Freshness Local Audit Report",
    "Packaged / Runtime Handoff QA",
    "Not Run And Cloud Boundary",
]

PACKAGED_RUNTIME_REPORT_SECTIONS = [
    "CMP Playground Architecture Matrix",
    "Playground Simulation Contract",
    "CMP Playground Coverage Matrix",
]

TARGET_ALIASES = {
    "backend": "backend",
    "backend-matrix": "backend",
    "backend_matrix": "backend",
    "mock-backend-matrix": "backend",
    "mock_backend_matrix": "backend",
    "mock-backend": "backend",
    "mock_backend": "backend",
    "frontend": "frontend",
    "frontend-matrix": "frontend",
    "frontend_matrix": "frontend",
    "frontend-action": "frontend",
    "frontend_action": "frontend",
    "frontend-action-matrix": "frontend",
    "frontend_action_matrix": "frontend",
    "mock-frontend": "frontend",
    "mock_frontend": "frontend",
    "packaged": "packaged",
    "packaged-case": "packaged",
    "packaged-cases": "packaged",
    "packaged_case": "packaged",
    "packaged_cases": "packaged",
    "playground": "packaged",
    "playground-representative": "packaged",
    "playground_representative": "packaged",
    "browser": "packaged",
}

REAL_CODE_KEY_GROUPS = {
    "frontend": ["frontend", "page", "component"],
    "api_client": ["api_client", "api client", "client"],
    "controller": ["controller"],
    "service": ["service"],
}
FORBIDDEN_MOCK_CONCEPTS = {
    "frontend/component": ["frontend", "component", "page"],
    "api client": ["api client", "api_client", "client"],
    "controller": ["controller"],
    "DTO": ["dto", "request", "response", "schema"],
    "service": ["service"],
}
EXTERNAL_MOCK_TERMS = [
    "cloud api",
    "cloud-api",
    "cloud",
    "k8s",
    "k8s api",
    "k8s-api",
    "kubernetes",
    "kafka instance api",
    "kafka-instance-api",
    "kafka-instance",
    "connect rest api",
    "connect-rest-api",
    "connect-rest",
    "no-cloud",
    "external",
]
STRICT_EXTERNAL_CATEGORIES = {
    "cloud-api",
    "cloud api",
    "cloud",
    "k8s-api",
    "k8s api",
    "k8s",
    "kubernetes-api",
    "kubernetes api",
    "kubernetes",
    "kafka-instance-api",
    "kafka instance api",
    "kafka-instance",
    "connect-rest-api",
    "connect rest api",
    "connect-rest",
}

MUTATION_ACTION_RE = re.compile(
    r"(create|check|submit|update|resize|delete|scale|upgrade|bind|import|save|worker.?spec|capacity)",
    re.IGNORECASE,
)
PERSISTENT_MUTATION_ACTION_RE = re.compile(
    r"(create|submit|update|resize|delete|scale(?![-_ ]?events?)|upgrade|bind|import|save|worker.?spec|capacity)",
    re.IGNORECASE,
)
PREFLIGHT_ONLY_RE = re.compile(r"(/check\b|\bcheck[-_ ]?submit\b|\bpreflight\b|\bcheck only\b|只检查)", re.IGNORECASE)
CLICK_RE = re.compile(r"\b(click|submit|select|choose|open|type|confirm|press)\b|点击|提交|选择|展开|输入|确认", re.IGNORECASE)
HTTP_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\b\s+/|/[A-Za-z0-9_{}:$./-]+")
HTTP_MUTATION_RE = re.compile(r"\b(POST|PUT|PATCH|DELETE)\b\s+/|/[A-Za-z0-9_{}:$./-]+")
SMOKE_ONLY_RE = re.compile(r"\b(route smoke|api smoke|browser smoke|page loads?|smoke passed|smoke ok)\b", re.IGNORECASE)
ROUTE_AUDIT_SUPPORT_ONLY_RE = re.compile(
    r"\b(runtime audit|route audit|controller audit|real-controller routing|static|freshness|MIME|bundle|page route|"
    r"console/network blockers|route exposes|route loads?|page loads?)\b",
    re.IGNORECASE,
)
FRESHNESS_RE = re.compile(r"\b(branch|commit|bundle|main-[\w.-]+\.js|jar|package|pid|port|mtime|user\.home|log|restart|fresh)\b", re.IGNORECASE)
COMMAND_RE = re.compile(
    r"(?:\./mvnw|\bmvnw\b|\b(?:mvn|pnpm|npm|yarn|vitest|jest|playwright|pytest|curl|java|node)\b|浏览器|手工|manual)",
    re.IGNORECASE,
)
EXECUTED_BY_RE = re.compile(r"\b(?:[A-Za-z_$][\w$]*Test[#.][A-Za-z_$][\w$]*|test[:/][A-Za-z0-9_.#-]+|manual:[A-Za-z0-9_.#-]+)\b")
COMPLETED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:")
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
MANUAL_COMMAND_RE = re.compile(r"\bmanual\b|手工|浏览器", re.IGNORECASE)
EVIDENCE_REF_RE = re.compile(r"[/\\.]|\.(?:txt|xml|json|log|har|zip|png|jpg|jpeg|webm|mp4|html|md)$", re.IGNORECASE)
SUMMARY_ONLY_EVIDENCE_RE = re.compile(
    r"(^|/)(?:tasks\.md|task-verification-log\.yaml|execution-state\.yaml|workflow-state\.yaml|mock-acceptance\.md|mock-acceptance-execution\.yaml)$",
    re.IGNORECASE,
)
STATEFUL_SIGNAL_RE = re.compile(
    r"\b(lifecycle|progress|event|events|terminal|polling|retry|state\s*graph|state\s*machine|task\s*step|change\s*tracking|step\s*graph)\b|"
    r"生命周期|进度|事件|状态机|状态图|终态|轮询|重试|任务步骤|变更追踪|状态推进",
    re.IGNORECASE,
)
PACKAGED_RUNTIME_PLAYGROUND_SIGNAL_RE = re.compile(
    r"\b(cmp-playground|PlaygroundAcceptanceProperties|REAL_CONTROLLER_PATH|packaged playground)\b|"
    r"\bno-cloud runtime\s+(?:Playground|packaged|controller)\b|"
    r"\bautomqbox\s+playground\b",
    re.IGNORECASE,
)
AUTOMQBOX_REPO_SIGNAL_RE = re.compile(r"\b(automqbox|automqbox/CMP|cmp-app|cmp-frontend-next|cmp-service)\b", re.IGNORECASE)
CONNECT_DOMAIN_SIGNAL_RE = re.compile(
    r"\b("
    r"ConnectCluster|ConnectorController|ConnectorService|ConnectorPlugin|ConnectRestClient|"
    r"connect[-_ ]cluster|connect[-_ ]connector|connector[-_ ]plugin|connector[-_ ]task|connector[-_ ]worker|"
    r"Debezium|Kafka Connect"
    r")\b|"
    r"/connect(?:/|\b)|"
    r"\bfrontend/.+?/connect\b|\bcmp/.+?/connect\b|"
    r"连接器|Connect 集群|Connect集群",
    re.IGNORECASE,
)
PRODUCTION_DOWNGRADE_RE = re.compile(
    r"\b("
    r"ASG_LOCAL[A-Z0-9_]*|K8S_LOCAL[A-Z0-9_]*|LOCAL_CREATE_BRANCH|LOCAL_WORKER_SPEC_UPDATE|"
    r"local[-_ ]only|local[-_ ]flow|local[-_ ]branch|local[-_ ]create|"
    r"no[-_ ]runtime|runtime[-_ ]free|without[-_ ]runtime|acceptance[-_ ]only\s+success|"
    r"simulat(?:ed|or)[-_ ]only\s+success|simulated\s+success|fake\s+success|"
    r"mock[-_ ]only\s+(?:implementation|success|create|update|delete|resize)|"
    r"no[-_ ]cloud\s+(?:implementation|business\s+logic|success)|"
    r"without\s+(?:provider|external\s+adapter|cloud\s+adapter|k8s\s+adapter|runtime|resource\s+adapter)\s+(?:call|mutation)"
    r")\b|"
    r"(?:本地|local).{0,24}(?:完成|成功|分支).{0,24}(?:生产|实现|create|update|delete|resize|ASG|K8s)|"
    r"(?:模拟|fake|simulated|acceptance).{0,24}(?:成功|success).{0,24}(?:生产|实现|runtime|adapter|resource|资源)|"
    r"(?:跳过|不调用|无需调用).{0,24}(?:provider|adapter|operator|NodeGroupOperator|K8s|Kubernetes|runtime|resource|云|外部)",
    re.IGNORECASE,
)
STATE_OWNER_RE = re.compile(
    r"\b(state owner|state_owner|database|db|sqlite|repository|dao|mapper|mybatis|schema|table|row|"
    r"k8s|kubernetes|cloud|asg|launch template|security group|iam|runtime graph|task|change|event|cache|topic)\b|"
    r"状态所有者|状态归属|落库|持久化|读写表|数据库|资源状态",
    re.IGNORECASE,
)
PERSISTENCE_RE = re.compile(
    r"\b(persist|persistence|insert|update|delete|upsert|repository|dao|mapper|mybatis|sqlite|database|db|"
    r"schema|table|row|constraint|migration|state write|resource create|resource update|resource delete)\b|"
    r"落库|持久化|插入|更新|删除|读写表|数据库|约束|迁移",
    re.IGNORECASE,
)
SCHEMA_RESOURCE_COMPAT_RE = re.compile(
    r"\b(schema|resource|constraint|required|not\s+null|nullability|nullable|null|default|derived|"
    r"compatibility|compatible|compat-placeholder|forbidden|retired|old[-_ ]mode|old[-_ ]field|"
    r"old[-_ ]resource|migration|ddl|mapper|column)\b|"
    r"schema|资源|约束|必填|非空|可空|null|默认|派生|兼容|禁止|旧字段|旧资源|旧模式|迁移|列",
    re.IGNORECASE,
)
READBACK_RE = re.compile(
    r"\b(readback|read back|detail|list|get|query|select|fetch|row exists|created id|cluster id|same id|"
    r"response id|read after write|last-change|progress|visible next state)\b|"
    r"读回|回读|查询|详情|列表|创建后的.*id|同一个.*id|写后读",
    re.IGNORECASE,
)
MANAGED_RESOURCE_OWNERSHIP_RE = re.compile(
    r"\b(auto[-_ ]?create|default[-_ ]?created|generated\s+resource|managed\s+resource|select[-_ ]?existing|existing\s+resource)\b|"
    r"自动创建|默认创建|生成资源|托管资源|选择已有|已有资源|现有资源",
    re.IGNORECASE,
)
EXTERNAL_RESOURCE_RE = re.compile(
    r"\b(resource|provider|cloud|k8s|kubernetes|iam|role|profile|security\s*group|sg|bucket|dns|vpc|subnet|asg|"
    r"launch\s*template|node\s*group|operator)\b|资源|云|外部|安全组|角色",
    re.IGNORECASE,
)
OWNERSHIP_RE = re.compile(
    r"\b(owned|existing|generated|derived|provenance|ownership|owner|state owner|persist|readback)\b|"
    r"归属|所有权|来源|状态所有者|持久|读回|已有|现有",
    re.IGNORECASE,
)
CLEANUP_PROTECT_RE = re.compile(
    r"\b(cleanup|delete|protect|detach|residual|partial)\b|清理|删除|保护|解绑|残留|部分",
    re.IGNORECASE,
)
DB_OWNER_RE = re.compile(r"\b(sqlite|database|db|repository|dao|mapper|mybatis|schema|table|row)\b|数据库|落库|读写表", re.IGNORECASE)
STATE_WRITER_RE = re.compile(
    r"\b(manager|task|deploy|operator|workflow|resource writer)\b|"
    r"(?:Manager|Task|Deploy|Operator|Workflow|ResourceWriter)",
    re.IGNORECASE,
)


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


def has_any_key(row: dict[str, Any], aliases: list[str]) -> bool:
    normalized = {str(key).lower().replace("-", "_").replace(" ", "_"): key for key in row}
    for alias in aliases:
        key = alias.lower().replace("-", "_").replace(" ", "_")
        if key in normalized and text(row.get(normalized[key])):
            return True
    return False


def contains_any(haystack: str, needles: list[str]) -> bool:
    normalized = haystack.lower().replace("_", " ")
    return any(needle.lower().replace("_", " ") in normalized for needle in needles)


def normalize_dep(dep: str) -> str:
    return dep.lower().strip().replace("_", "-")


def external_dep_errors(prefix: str, deps: list[str]) -> list[str]:
    errors: list[str] = []
    if not deps:
        errors.append(f"{prefix} missing mocked_external_dependencies")
        return errors
    if not any(any(term in dep for term in EXTERNAL_MOCK_TERMS) for dep in deps):
        errors.append(f"{prefix} mocked_external_dependencies do not look external: {deps}")
    for dep in deps:
        normalized = normalize_dep(dep)
        if any(term in dep for term in ["frontend", "component", "api client", "api_client", "controller", "dto", "service"]):
            errors.append(f"{prefix} mocks product/business layer {dep}")
        if normalized in {"metrics", "logs", "runtime", "provider", "no-cloud-state", "no-cloud state"}:
            errors.append(
                f"{prefix} mocked_external_dependencies uses broad old category {dep}; "
                "use cloud-api/k8s-api/kafka-instance-api/connect-rest-api and model metrics/logs through Connect REST or K8s APIs"
            )
    if not any(normalize_dep(dep) in STRICT_EXTERNAL_CATEGORIES for dep in deps):
        errors.append(
            f"{prefix} must include at least one strict external API category: "
            "cloud-api, k8s-api, kafka-instance-api, or connect-rest-api"
        )
    return errors


def section(markdown: str, name: str) -> str:
    pattern = re.compile(rf"^##+\s+{re.escape(name)}\s*$", re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        return ""
    start = match.end()
    level = re.match(r"^(##+)", match.group(0))
    level_text = level.group(1) if level else "##"
    next_match = re.search(rf"^{re.escape(level_text)}\s+", markdown[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(markdown)
    return markdown[start:end]


def rows_from(value: Any, key: str) -> list[dict[str, Any]]:
    raw = as_dict(value).get(key)
    if isinstance(raw, dict):
        rows: list[dict[str, Any]] = []
        for item_id, body in raw.items():
            row = as_dict(body).copy()
            row.setdefault("id", item_id)
            rows.append(row)
        return rows
    return [as_dict(item) for item in as_list(raw)]


def normalize_target(value: Any) -> str:
    raw = text(value).lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "all": "all",
        "backend": "backend",
        "backend-matrix": "backend",
        "mock-backend": "backend",
        "mock-backend-matrix": "backend",
        "frontend": "frontend",
        "frontend-action": "frontend",
        "frontend-matrix": "frontend",
        "frontend-action-matrix": "frontend",
        "mock-frontend": "frontend",
        "mock-frontend-action": "frontend",
        "packaged": "packaged",
        "packaged-case": "packaged",
        "packaged-cases": "packaged",
        "playground": "packaged",
        "browser": "packaged",
        "event": "event-state",
        "events": "event-state",
        "event-state": "event-state",
        "event-state-matrix": "event-state",
        "stateful": "event-state",
        "stateful-event": "event-state",
    }
    return aliases.get(raw, raw)


def backend_rows(backend_doc: dict[str, Any]) -> list[dict[str, Any]]:
    return rows_from(backend_doc, "backend_rows") or rows_from(backend_doc, "rows") or rows_from(backend_doc, "matrix")


def frontend_rows(frontend_doc: dict[str, Any]) -> list[dict[str, Any]]:
    return (
        rows_from(frontend_doc, "actions")
        or rows_from(frontend_doc, "frontend_actions")
        or rows_from(frontend_doc, "rows")
        or rows_from(frontend_doc, "matrix")
    )


def execution_ledger_rows(ledger_doc: dict[str, Any]) -> list[dict[str, Any]]:
    return (
        rows_from(ledger_doc, "executions")
        or rows_from(ledger_doc, "execution_rows")
        or rows_from(ledger_doc, "results")
        or rows_from(ledger_doc, "rows")
        or rows_from(ledger_doc, "matrix")
    )


def row_coverage_sets(row: dict[str, Any]) -> set[str]:
    return {text(item) for item in as_list(row.get("coverage_sets") or row.get("coverage_set")) if text(item)}


def row_dimensions(row: dict[str, Any]) -> dict[str, str]:
    return {str(k): text(v) for k, v in as_dict(row.get("dimensions") or row.get("dimension_values")).items()}


def coverage_targets(coverage_set: dict[str, Any]) -> set[str]:
    raw = (
        coverage_set.get("targets")
        or coverage_set.get("target")
        or coverage_set.get("coverage_targets")
        or coverage_set.get("coverage_target")
        or coverage_set.get("evidence_layers")
        or coverage_set.get("evidence_layer")
        or coverage_set.get("layer")
    )
    targets: set[str] = set()
    for item in as_list(raw):
        normalized = text(item).lower().replace(" ", "_")
        if not normalized:
            continue
        canonical = TARGET_ALIASES.get(normalized.replace("_", "-")) or TARGET_ALIASES.get(normalized)
        if canonical:
            targets.add(canonical)
    return targets


def dimension_values(dimensions_doc: dict[str, Any]) -> dict[str, list[str]]:
    raw_dimensions = as_dict(dimensions_doc.get("dimensions"))
    values: dict[str, list[str]] = {}
    for name, raw in raw_dimensions.items():
        if isinstance(raw, dict):
            raw_values = raw.get("values")
        else:
            raw_values = raw
        vals = [text(item) for item in as_list(raw_values) if text(item)]
        values[str(name)] = vals
    return values


def partial_match(candidate: dict[str, str], pattern: dict[str, Any]) -> bool:
    for key, raw_value in pattern.items():
        expected = {text(item) for item in as_list(raw_value) if text(item)}
        if expected and text(candidate.get(str(key))) not in expected:
            return False
    return True


def combo_excluded(combo: dict[str, str], excludes: list[Any]) -> bool:
    return any(partial_match(combo, as_dict(item)) for item in excludes)


def selected_values(all_values: dict[str, list[str]], coverage_set: dict[str, Any], dim: str) -> list[str]:
    explicit_values = as_dict(coverage_set.get("values"))
    if dim in explicit_values:
        return [text(item) for item in as_list(explicit_values.get(dim)) if text(item)]
    return all_values.get(dim, [])


def validate_dimensions(change_dir: Path, dimensions_doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    values = dimension_values(dimensions_doc)
    if not values:
        return [f"{change_dir}: mock-test-dimensions.yaml must define dimensions"]
    for name, vals in values.items():
        if not vals:
            errors.append(f"{change_dir}: dimension {name} has no values")
    coverage_sets = rows_from(dimensions_doc, "coverage_sets")
    if not coverage_sets:
        errors.append(f"{change_dir}: mock-test-dimensions.yaml must define coverage_sets; prose matrices are not enough")
    for coverage_set in coverage_sets:
        set_id = text(coverage_set.get("id"))
        dims = [text(item) for item in as_list(coverage_set.get("dimensions")) if text(item)]
        if not set_id:
            errors.append(f"{change_dir}: coverage_set is missing id")
        if not dims:
            errors.append(f"{change_dir}: coverage_set {set_id or '<missing>'} is missing dimensions")
        targets = coverage_targets(coverage_set)
        if not targets:
            errors.append(
                f"{change_dir}: coverage_set {set_id or '<missing>'} missing target; "
                "assign it to backend_matrix, frontend_action_matrix, or packaged_cases"
            )
        for dim in dims:
            if dim not in values:
                errors.append(f"{change_dir}: coverage_set {set_id} references unknown dimension {dim}")
    return errors


def validate_fixture_graph(change_dir: Path, fixture_doc: dict[str, Any]) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    fixtures = rows_from(fixture_doc, "fixtures")
    ids: set[str] = set()
    if not fixtures:
        return [f"{change_dir}: mock-fixture-graph.yaml must define fixtures"], ids
    for fixture in fixtures:
        fixture_id = text(fixture.get("fixture_id") or fixture.get("id"))
        if not fixture_id:
            errors.append(f"{change_dir}: fixture row missing fixture_id/id")
            continue
        if fixture_id in ids:
            errors.append(f"{change_dir}: duplicate fixture id {fixture_id}")
        ids.add(fixture_id)
        for field in ["type", "contract_source", "provides", "consumed_by"]:
            if not text(fixture.get(field)) and not as_list(fixture.get(field)):
                errors.append(f"{change_dir}: fixture {fixture_id} missing {field}")
    return errors, ids


def repo_root_for(change_dir: Path) -> Path:
    for ancestor in [change_dir, *change_dir.parents]:
        if ancestor.name == "specs":
            return ancestor.parent
        if (ancestor / ".git").exists() or (ancestor / "pom.xml").exists() or (ancestor / "package.json").exists():
            return ancestor
    return change_dir


def resolve_evidence_ref(change_dir: Path, ref: str) -> Path | None:
    if URL_RE.search(ref):
        return None
    path = Path(ref)
    if path.is_absolute():
        return path
    repo_root = repo_root_for(change_dir)
    candidates = [change_dir / path, repo_root / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def validate_evidence_refs(change_dir: Path, prefix: str, evidence_refs: list[str]) -> list[str]:
    errors: list[str] = []
    if not evidence_refs:
        errors.append(f"{prefix} missing evidence_refs; execution must link row-level command/log/screenshot/network artifacts")
        return errors
    for ref in evidence_refs:
        if SUMMARY_ONLY_EVIDENCE_RE.search(ref):
            errors.append(f"{prefix} evidence_ref {ref} is only a summary artifact; row-level evidence must point to test logs, traces, HAR, screenshots, or reports")
        if not URL_RE.search(ref) and not EVIDENCE_REF_RE.search(ref):
            errors.append(f"{prefix} evidence_ref is too vague: {ref}")
            continue
        resolved = resolve_evidence_ref(change_dir, ref)
        if resolved is not None and not resolved.exists():
            errors.append(f"{prefix} evidence_ref does not exist: {ref}")
    return errors


def validate_command_execution(row: dict[str, Any], prefix: str, command: str) -> list[str]:
    errors: list[str] = []
    if MANUAL_COMMAND_RE.search(command):
        if not text(row.get("manual_result") or row.get("manual_verdict") or row.get("reviewer")):
            errors.append(f"{prefix} manual/browser command missing manual_result/manual_verdict/reviewer")
        return errors
    exit_code = row.get("command_exit_code", row.get("exit_code"))
    if exit_code is None or text(exit_code) == "":
        errors.append(f"{prefix} missing command_exit_code/exit_code=0; command presence alone does not prove the row was executed")
    elif text(exit_code) != "0":
        errors.append(f"{prefix} command_exit_code must be 0 for passed row, got {text(exit_code)}")
    return errors


def mutation_text(row: dict[str, Any]) -> str:
    return flatten([
        row.get("action"),
        row.get("user_action"),
        row.get("method"),
        row.get("path"),
        row.get("api_method"),
        row.get("api_path"),
        row.get("user_goal"),
        row.get("dimensions"),
        row.get("coverage_sets"),
        row.get("request_shape"),
    ])


def is_persistent_mutation(row: dict[str, Any]) -> bool:
    raw = mutation_text(row)
    if PREFLIGHT_ONLY_RE.search(raw):
        return False
    method = text(row.get("method") or row.get("api_method")).upper()
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        return True
    return bool(PERSISTENT_MUTATION_ACTION_RE.search(raw))


def managed_resource_text(row: dict[str, Any]) -> str:
    return flatten([
        mutation_text(row),
        row.get("dimensions"),
        row.get("coverage_sets"),
        row.get("mocked_external_dependencies"),
        row.get("external_adapters"),
        row.get("no_cloud_adapters"),
        row.get("managed_resource_ownership"),
        row.get("state_assertions"),
        row.get("assertions"),
    ])


def is_managed_resource_ownership(row: dict[str, Any]) -> bool:
    raw = managed_resource_text(row)
    return bool(MANAGED_RESOURCE_OWNERSHIP_RE.search(raw) and EXTERNAL_RESOURCE_RE.search(raw))


def validate_managed_resource_ownership_shape(row: dict[str, Any], prefix: str) -> list[str]:
    if not is_managed_resource_ownership(row):
        return []
    errors: list[str] = []
    ownership = as_dict(row.get("managed_resource_ownership") or row.get("resource_ownership"))
    ownership_text = flatten(ownership)
    combined = flatten([ownership_text, row.get("state_assertions"), row.get("assertions"), row.get("real_code_under_test")])
    if not ownership:
        errors.append(f"{prefix} managed resource row missing managed_resource_ownership section")
        return errors
    for field in ["resource_type", "selection_mode", "provider_writer"]:
        if not text(ownership.get(field)):
            errors.append(f"{prefix} managed_resource_ownership missing {field}")
    if not re.search(r"provider|API|operator|writer|resource|调用|写入|创建", text(ownership.get("provider_writer")), re.IGNORECASE):
        errors.append(f"{prefix} managed_resource_ownership.provider_writer must name production provider/API/operator/resource writer")
    if not OWNERSHIP_RE.search(flatten([ownership.get("provenance_assertions"), ownership.get("provenance_state_owner"), combined])):
        errors.append(f"{prefix} managed resource row must assert owned/existing/generated provenance persistence/readback")
    if not READBACK_RE.search(flatten([ownership.get("resource_identity_assertions"), ownership.get("provenance_assertions"), combined])):
        errors.append(f"{prefix} managed resource row must assert resource identity/provenance readback")
    if not CLEANUP_PROTECT_RE.search(flatten([ownership.get("cleanup_assertions"), ownership.get("delete_cleanup_rule"), combined])):
        errors.append(f"{prefix} managed resource row must assert owned cleanup and existing protect/detach behavior")
    return errors


def validate_backend_mutation_shape(row: dict[str, Any], prefix: str) -> list[str]:
    if not is_persistent_mutation(row):
        return []
    errors: list[str] = []
    real_code = as_dict(row.get("real_code_under_test") or row.get("real_code"))
    real_code_text = flatten(real_code)
    if not STATE_WRITER_RE.search(real_code_text):
        errors.append(f"{prefix} persistent mutation row must name the real manager/task/resource writer, not only controller/service")
    if not re.search(r"\b(repository|dao|mapper|mybatis|sqlite|database|db|schema|migration|table|runtime graph|state owner)\b", real_code_text, re.IGNORECASE):
        errors.append(f"{prefix} persistent mutation row must name the state owner/repository/schema/resource writer in real_code_under_test")

    state_owner = row.get("state_owner") or row.get("state_owners") or row.get("persistence_owner")
    if not flatten(state_owner) or not STATE_OWNER_RE.search(flatten(state_owner)):
        errors.append(f"{prefix} persistent mutation row missing state_owner/persistence_owner")

    persistence_assertions = flatten(row.get("persistence_assertions") or row.get("write_assertions"))
    readback_assertions = flatten(row.get("readback_assertions") or row.get("read_after_write_assertions"))
    state_assertions = flatten(row.get("state_assertions") or row.get("assertions"))
    if not PERSISTENCE_RE.search(flatten([persistence_assertions, state_assertions])):
        errors.append(f"{prefix} persistent mutation row must assert write/persistence/resource-state mutation, not only request shape")
    schema_resource_compatibility = flatten([
        row.get("schema_resource_compatibility"),
        row.get("schema_compatibility"),
        row.get("resource_compatibility"),
        persistence_assertions,
        state_assertions,
        real_code_text,
    ])
    if not SCHEMA_RESOURCE_COMPAT_RE.search(schema_resource_compatibility):
        errors.append(f"{prefix} persistent mutation row must assert schema/resource compatibility for required/null/default/derived/forbidden old-mode constraints")
    if not READBACK_RE.search(flatten([readback_assertions, state_assertions])):
        errors.append(f"{prefix} persistent mutation row must assert readback/detail/list/query of the mutated state")
    return errors


def validate_mutation_execution_proof(
    row: dict[str, Any],
    prefix: str,
    *,
    packaged: bool = False,
    require_state_proof: bool = False,
) -> list[str]:
    if not is_persistent_mutation(row):
        return []
    errors: list[str] = []
    if not (packaged or require_state_proof):
        return errors
    proof_text = flatten([
        row.get("executed_by"),
        row.get("test_ref"),
        row.get("runner"),
        row.get("assertion_refs"),
        row.get("evidence"),
        row.get("evidence_refs"),
        row.get("command"),
        row.get("manual_step"),
    ])
    if packaged:
        if not CLICK_RE.search(proof_text):
            errors.append(f"{prefix} packaged mutation execution must prove real browser click/select/type/submit, not only route/runtime audit")
        if not HTTP_MUTATION_RE.search(proof_text):
            errors.append(f"{prefix} packaged mutation execution must prove mutation HTTP method/path/body")
        if ROUTE_AUDIT_SUPPORT_ONLY_RE.search(proof_text) and not (PERSISTENCE_RE.search(proof_text) and READBACK_RE.search(proof_text)):
            errors.append(f"{prefix} packaged mutation execution uses route/runtime audit as primary proof; submit/write/readback proof is required")
    if not PERSISTENCE_RE.search(proof_text):
        errors.append(f"{prefix} mutation execution evidence must include write/persistence/resource-state proof")
    if not READBACK_RE.search(proof_text):
        errors.append(f"{prefix} mutation execution evidence must include readback/detail/list/query proof")
    return errors


def validate_managed_resource_execution_proof(
    row: dict[str, Any],
    prefix: str,
    *,
    require_state_proof: bool = False,
) -> list[str]:
    if not is_managed_resource_ownership(row) or not require_state_proof:
        return []
    proof_text = flatten([
        row.get("executed_by"),
        row.get("test_ref"),
        row.get("runner"),
        row.get("assertion_refs"),
        row.get("evidence"),
        row.get("evidence_refs"),
        row.get("command"),
        row.get("manual_step"),
    ])
    errors: list[str] = []
    if not re.search(r"provider|API|operator|create|delete|update|call|调用|创建|删除|更新", proof_text, re.IGNORECASE):
        errors.append(f"{prefix} managed resource execution evidence must include provider create/delete/update call proof")
    if not (OWNERSHIP_RE.search(proof_text) and READBACK_RE.search(proof_text)):
        errors.append(f"{prefix} managed resource execution evidence must include ownership/provenance readback proof")
    if not CLEANUP_PROTECT_RE.search(proof_text):
        errors.append(f"{prefix} managed resource execution evidence must include cleanup/protect proof")
    return errors


def validate_execution_fields(
    change_dir: Path,
    row: dict[str, Any],
    prefix: str,
    *,
    packaged: bool = False,
    require_state_proof: bool = False,
) -> list[str]:
    errors: list[str] = []
    executed_by = text(row.get("executed_by") or row.get("test_ref") or row.get("runner"))
    assertion_refs = [text(item) for item in as_list(row.get("assertion_refs") or row.get("assertions_executed")) if text(item)]
    evidence = text(row.get("evidence"))
    evidence_refs = [text(item) for item in as_list(row.get("evidence_refs")) if text(item)]
    completed_at = text(row.get("completed_at") or row.get("executed_at"))
    if not executed_by:
        target = "packaged case must map to browser/API runner" if packaged else "aggregate command coverage is not row-level evidence"
        errors.append(f"{prefix} missing executed_by/test_ref; {target}")
    elif not (EXECUTED_BY_RE.search(executed_by) or len(executed_by) >= 12):
        errors.append(f"{prefix} executed_by is too vague: {executed_by}")
    if not assertion_refs:
        target = "packaged case must map to browser/network/DOM/API assertions" if packaged else "each matrix row must map to concrete assertions"
        errors.append(f"{prefix} missing assertion_refs; {target}")
    if evidence and SMOKE_ONLY_RE.search(evidence):
        target = "packaged case must prove browser/network/DOM/API semantics" if packaged else "row-level assertions must prove the matrix semantics"
        errors.append(f"{prefix} evidence is smoke-only; {target}")
    errors.extend(validate_evidence_refs(change_dir, prefix, evidence_refs))
    if not completed_at:
        errors.append(f"{prefix} missing completed_at")
    elif not COMPLETED_AT_RE.search(completed_at):
        errors.append(f"{prefix} completed_at must be ISO-like timestamp")
    command = text(row.get("command") or row.get("test_command") or row.get("manual_step") or row.get("verification"))
    if not command or not COMMAND_RE.search(command):
        errors.append(f"{prefix} missing executable command/manual_step evidence")
    else:
        errors.extend(validate_command_execution(row, prefix, command))
    errors.extend(validate_mutation_execution_proof(row, prefix, packaged=packaged, require_state_proof=require_state_proof))
    errors.extend(validate_managed_resource_execution_proof(row, prefix, require_state_proof=require_state_proof))
    return errors


def row_id(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = text(row.get(key))
        if value:
            return value
    return text(row.get("id"))


def validate_result_evidence(
    change_dir: Path,
    row: dict[str, Any],
    prefix: str,
    *,
    mode: str,
    require_state_proof: bool = False,
) -> list[str]:
    errors: list[str] = []
    status = text(row.get("result") or row.get("status")).lower()
    blocks = row.get("blocks_acceptance", row.get("blocks_done", True))
    if mode == "planning":
        if status not in PLANNING_STATUSES:
            errors.append(f"{prefix} has invalid planning result={status or '<missing>'}")
        if status == "not_applicable" and not text(row.get("na_reason") or row.get("decision")):
            errors.append(f"{prefix} is not_applicable but missing na_reason/decision")
        if status == "not_applicable":
            return errors
        command = text(row.get("command") or row.get("test_command") or row.get("manual_step") or row.get("verification"))
        if not command or not COMMAND_RE.search(command):
            errors.append(f"{prefix} missing planned executable command/manual_step")
        if not text(row.get("expected_result")):
            errors.append(f"{prefix} missing expected_result")
        if not text(row.get("proves")):
            errors.append(f"{prefix} missing proves")
        return errors
    if status not in EXECUTION_STATUSES:
        errors.append(f"{prefix} has result={status or '<missing>'}; preflight matrices cannot pass with unexecuted rows")
    if status == "not_applicable" and not text(row.get("na_reason") or row.get("decision")):
        errors.append(f"{prefix} is not_applicable but missing na_reason/decision")
    if status == "not_applicable":
        return errors
    if blocks is not False and status != "passed":
        errors.append(f"{prefix} blocks acceptance and is not passed")
    errors.extend(validate_execution_fields(change_dir, row, prefix, require_state_proof=require_state_proof))
    return errors


def validate_backend_matrix(change_dir: Path, backend_doc: dict[str, Any], fixture_ids: set[str], *, mode: str) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    rows = backend_rows(backend_doc)
    ids: set[str] = set()
    if not rows:
        return [f"{change_dir}: mock-backend-matrix.yaml must define backend_rows/rows"], ids
    for row in rows:
        rid = row_id(row, "backend_row_id", "row_id", "id")
        prefix = f"{change_dir}: backend matrix row {rid or '<missing>'}"
        if not rid:
            errors.append(f"{change_dir}: backend matrix row missing backend_row_id/id")
            continue
        if rid in ids:
            errors.append(f"{change_dir}: duplicate backend matrix row {rid}")
        ids.add(rid)
        if mode == "planning" and not row_owner(row):
            errors.append(f"{prefix} missing owner_task/owner_issue; backend matrix rows must have an execution owner")
        if not row_coverage_sets(row):
            errors.append(f"{prefix} missing coverage_sets; backend matrix rows must close finite coverage sets")
        if not row_dimensions(row):
            errors.append(f"{prefix} missing dimensions; backend matrix coverage cannot be implicit")
        for field in ["contract_source", "action", "expected_result", "proves"]:
            if not text(row.get(field)):
                errors.append(f"{prefix} missing {field}")
        method = text(row.get("method") or row.get("api_method"))
        path = text(row.get("path") or row.get("api_path"))
        if not method or method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            errors.append(f"{prefix} missing HTTP method")
        if not path.startswith("/"):
            errors.append(f"{prefix} missing API path")
        real_code = as_dict(row.get("real_code_under_test") or row.get("real_code"))
        for concept in ["controller", "service"]:
            if not has_any_key(real_code, REAL_CODE_KEY_GROUPS[concept]):
                errors.append(f"{prefix} real_code_under_test missing {concept}")
        external_adapters = row.get("external_adapters") or row.get("no_cloud_adapters") or row.get("simulated_external_dependencies")
        has_no_cloud_adapter = bool(flatten(external_adapters))
        if not has_no_cloud_adapter:
            errors.append(
                f"{prefix} missing external_adapters/no_cloud_adapters; "
                "backend rows must prove where external dependency calls are intercepted"
            )
        mocked_deps = [text(item).lower() for item in as_list(row.get("mocked_external_dependencies")) if text(item)]
        errors.extend(external_dep_errors(prefix, mocked_deps))
        fixture_refs = [text(item) for item in as_list(row.get("fixture_refs")) if text(item)]
        if not fixture_refs:
            errors.append(f"{prefix} missing fixture_refs")
        for fixture_ref in fixture_refs:
            if fixture_ref not in fixture_ids:
                errors.append(f"{prefix} references unknown fixture {fixture_ref}")
        if not as_list(row.get("assertions")) and not flatten(row.get("state_assertions")):
            errors.append(f"{prefix} missing assertions/state_assertions")
        errors.extend(validate_backend_mutation_shape(row, prefix))
        errors.extend(validate_managed_resource_ownership_shape(row, prefix))
        errors.extend(validate_result_evidence(change_dir, row, prefix, mode=mode, require_state_proof=True))
    return errors, ids


def validate_frontend_action_matrix(change_dir: Path, frontend_doc: dict[str, Any], fixture_ids: set[str], *, mode: str) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    rows = frontend_rows(frontend_doc)
    ids: set[str] = set()
    if not rows:
        return [f"{change_dir}: mock-frontend-action-matrix.yaml must define actions/rows"], ids
    for row in rows:
        rid = row_id(row, "frontend_action_id", "action_id", "row_id", "id")
        prefix = f"{change_dir}: frontend action matrix row {rid or '<missing>'}"
        if not rid:
            errors.append(f"{change_dir}: frontend action matrix row missing frontend_action_id/id")
            continue
        if rid in ids:
            errors.append(f"{change_dir}: duplicate frontend action matrix row {rid}")
        ids.add(rid)
        if mode == "planning" and not row_owner(row):
            errors.append(f"{prefix} missing owner_task/owner_issue; frontend action rows must have an execution owner")
        if not row_coverage_sets(row):
            errors.append(f"{prefix} missing coverage_sets; frontend action rows must close finite coverage sets")
        if not row_dimensions(row):
            errors.append(f"{prefix} missing dimensions; frontend action coverage cannot be implicit")
        for field in ["route", "component", "user_action", "expected_result", "proves"]:
            if not text(row.get(field)):
                errors.append(f"{prefix} missing {field}")
        api_client = text(row.get("api_client") or row.get("api_client_method"))
        if not api_client:
            errors.append(f"{prefix} missing api_client/api_client_method")
        browser_steps = flatten(row.get("browser_steps") or row.get("user_steps"))
        if MUTATION_ACTION_RE.search(flatten([row.get("action"), row.get("user_action")])) and not CLICK_RE.search(browser_steps):
            errors.append(f"{prefix} mutation row must include real click/select/submit user steps")
        network_text = flatten(row.get("network_assertions"))
        if MUTATION_ACTION_RE.search(flatten([row.get("action"), row.get("user_action")])) and not HTTP_RE.search(network_text):
            errors.append(f"{prefix} mutation row must assert HTTP method/path/body")
        for field in ["dom_assertions", "negative_assertions"]:
            if not as_list(row.get(field)):
                errors.append(f"{prefix} missing {field}")
        if not re.search(r"\b(absent|not submit|no |without|forbid|禁止|不存在|不得|不提交)\b", flatten(row.get("negative_assertions")), re.IGNORECASE):
            errors.append(f"{prefix} negative_assertions must include explicit absence/forbidden assertion")
        fixture_refs = [text(item) for item in as_list(row.get("fixture_refs")) if text(item)]
        if not fixture_refs:
            errors.append(f"{prefix} missing fixture_refs")
        for fixture_ref in fixture_refs:
            if fixture_ref not in fixture_ids:
                errors.append(f"{prefix} references unknown fixture {fixture_ref}")
        errors.extend(validate_result_evidence(change_dir, row, prefix, mode=mode))
    return errors, ids


def validate_case_shape(change_dir: Path, case: dict[str, Any], fixture_ids: set[str], *, mode: str) -> list[str]:
    errors: list[str] = []
    case_id = text(case.get("case_id") or case.get("id"))
    prefix = f"{change_dir}: case {case_id or '<missing>'}"
    if not case_id:
        errors.append(f"{change_dir}: mock acceptance case missing case_id")
    if mode == "planning" and not row_owner(case):
        errors.append(f"{prefix} missing owner_task/owner_issue; packaged cases must have an execution owner")
    dimensions = as_dict(case.get("dimensions") or case.get("dimension_values"))
    if not dimensions:
        errors.append(f"{prefix} missing dimensions")
    if not row_coverage_sets(case):
        errors.append(f"{prefix} missing coverage_sets; packaged representative cases must declare what they prove")
    for field in ["user_goal", "frontend_route", "contract_source"]:
        if not text(case.get(field)):
            errors.append(f"{prefix} missing {field}")
    real_code = as_dict(case.get("real_code_under_test") or case.get("real_code"))
    if not flatten(real_code):
        errors.append(f"{prefix} missing real_code_under_test; tested frontend/controller/service cannot be implicit")
    else:
        for concept, aliases in REAL_CODE_KEY_GROUPS.items():
            if not has_any_key(real_code, aliases):
                errors.append(f"{prefix} real_code_under_test missing {concept}; packaged/browser acceptance must prove real frontend/API/controller/service path")
        if "mock" in flatten(real_code).lower() and not text(case.get("na_reason") or case.get("decision")):
            errors.append(f"{prefix} real_code_under_test appears to include mock-only code; real code path and mock boundary must be separate")
    mock_boundary = as_dict(case.get("mock_boundary"))
    mocked_deps = case.get("mocked_external_dependencies") or mock_boundary.get("mocked_external_dependencies")
    mocked_dep_list = [text(item).lower() for item in as_list(mocked_deps) if text(item)]
    if not mocked_dep_list:
        errors.append(f"{prefix} missing mocked_external_dependencies; only external dependencies may be mocked")
    else:
        errors.extend(external_dep_errors(prefix, mocked_dep_list))
    forbidden_mocks = case.get("forbidden_mocks") or mock_boundary.get("forbidden_mocks")
    forbidden_text = flatten(forbidden_mocks).lower()
    if not as_list(forbidden_mocks):
        errors.append(f"{prefix} missing forbidden_mocks; API/controller/service/frontend must be protected from mock substitution")
    else:
        for concept, aliases in FORBIDDEN_MOCK_CONCEPTS.items():
            if not contains_any(forbidden_text, aliases):
                errors.append(f"{prefix} forbidden_mocks must explicitly protect {concept}")
    fixture_refs = [text(item) for item in as_list(case.get("fixture_refs")) if text(item)]
    if not fixture_refs:
        errors.append(f"{prefix} missing fixture_refs")
    for fixture_ref in fixture_refs:
        if fixture_ref not in fixture_ids:
            errors.append(f"{prefix} references unknown fixture {fixture_ref}")
    for field in ["browser_steps", "network_assertions", "dom_assertions", "api_assertions", "negative_assertions"]:
        if not as_list(case.get(field)):
            errors.append(f"{prefix} missing {field}")
    if not re.search(r"\b(absent|not submit|no |without|forbid|禁止|不存在|不得|不提交)\b", flatten(case.get("negative_assertions")), re.IGNORECASE):
        errors.append(f"{prefix} negative_assertions must contain an explicit absence/forbidden assertion, not only a positive check")
    action_text = flatten([case.get("action"), dimensions.get("action"), case.get("user_goal")])
    browser_text = flatten(case.get("browser_steps"))
    network_text = flatten(case.get("network_assertions"))
    if MUTATION_ACTION_RE.search(action_text):
        if not CLICK_RE.search(browser_text):
            errors.append(f"{prefix} is a mutation/action case but browser_steps do not contain real click/select/submit actions")
        if not HTTP_RE.search(network_text):
            errors.append(f"{prefix} is a mutation/action case but network_assertions do not prove HTTP method/path/body")
    if is_persistent_mutation(case):
        api_text = flatten(case.get("api_assertions"))
        if not READBACK_RE.search(api_text):
            errors.append(f"{prefix} persistent mutation case must assert readback/detail/list/query of the created or changed state")
        if not PERSISTENCE_RE.search(flatten([case.get("state_assertions"), case.get("api_assertions"), case.get("expected_result"), case.get("proves")])):
            errors.append(f"{prefix} persistent mutation case must prove backend write/persistence/resource-state mutation, not only route submit")
    status = text(case.get("result") or case.get("status")).lower()
    blocks = case.get("blocks_acceptance", True)
    if mode == "planning":
        if status not in PLANNING_STATUSES:
            errors.append(f"{prefix} has invalid planning result={status or '<missing>'}")
        if status == "not_applicable" and not text(case.get("na_reason") or case.get("decision")):
            errors.append(f"{prefix} is not_applicable but missing na_reason/decision")
        if status == "not_applicable":
            return errors
        command = text(case.get("command") or case.get("test_command") or case.get("manual_step") or case.get("verification"))
        if not command or not COMMAND_RE.search(command):
            errors.append(f"{prefix} missing planned executable command/manual_step")
        if not text(case.get("expected_result")):
            errors.append(f"{prefix} missing expected_result")
        if not text(case.get("proves")):
            errors.append(f"{prefix} missing proves")
        return errors
    if status not in EXECUTION_STATUSES:
        errors.append(f"{prefix} has result={status or '<missing>'}; mock acceptance cannot pass with unexecuted/blocked cases")
    if status == "not_applicable" and not text(case.get("na_reason") or case.get("decision")):
        errors.append(f"{prefix} is not_applicable but missing na_reason/decision")
    if status == "not_applicable":
        return errors
    if blocks is not False and status != "passed":
        errors.append(f"{prefix} blocks acceptance and is not passed")
    errors.extend(validate_execution_fields(change_dir, case, prefix, packaged=True))
    return errors


def row_owner(row: dict[str, Any]) -> str:
    return text(
        row.get("owner_task")
        or row.get("owner_issue")
        or row.get("task")
        or row.get("task_id")
        or row.get("issue")
    )


def filter_rows_for_owner(rows: list[dict[str, Any]], owner_task: str) -> list[dict[str, Any]]:
    if not owner_task:
        return rows
    owned = [row for row in rows if row_owner(row) == owner_task]
    return owned


def filter_cases_for_owner(cases: list[dict[str, Any]], owner_task: str) -> list[dict[str, Any]]:
    if not owner_task:
        return cases
    owned = [case for case in cases if row_owner(case) == owner_task]
    return owned


def validate_case_matrix_links(
    change_dir: Path,
    cases: list[dict[str, Any]],
    backend_ids: set[str],
    frontend_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    for case in cases:
        case_id = text(case.get("case_id") or case.get("id"))
        prefix = f"{change_dir}: case {case_id or '<missing>'}"
        backend_refs = [text(item) for item in as_list(case.get("backend_matrix_refs") or case.get("backend_refs")) if text(item)]
        frontend_refs = [text(item) for item in as_list(case.get("frontend_action_refs") or case.get("frontend_refs")) if text(item)]
        if not backend_refs:
            errors.append(f"{prefix} missing backend_matrix_refs; packaged case must trace to fast backend matrix coverage")
        if not frontend_refs:
            errors.append(f"{prefix} missing frontend_action_refs; packaged case must trace to fast frontend action matrix coverage")
        for ref in backend_refs:
            if ref not in backend_ids:
                errors.append(f"{prefix} references unknown backend matrix row {ref}")
        for ref in frontend_refs:
            if ref not in frontend_ids:
                errors.append(f"{prefix} references unknown frontend action matrix row {ref}")
    return errors


def event_state_rows(event_doc: dict[str, Any]) -> list[dict[str, Any]]:
    return rows_from(event_doc, "event_state_rows") or rows_from(event_doc, "rows") or rows_from(event_doc, "matrix")


def boolish_false(value: Any) -> bool:
    return value is False or text(value).lower() in {"false", "no", "0"}


def row_blocks_execution(row: dict[str, Any]) -> bool:
    if boolish_false(row.get("blocks_acceptance", row.get("blocks_done", True))):
        return False
    status = text(row.get("result") or row.get("status")).lower()
    if status == "not_applicable" and text(row.get("na_reason") or row.get("decision")):
        return False
    return True


def execution_entry_id(entry: dict[str, Any], target: str) -> str:
    if target == "backend":
        return row_id(entry, "backend_row_id", "row_id", "id")
    if target == "frontend":
        return row_id(entry, "frontend_action_id", "action_id", "row_id", "id")
    if target == "packaged":
        return row_id(entry, "case_id", "row_id", "id")
    if target == "event-state":
        return row_id(entry, "event_state_row_id", "state_row_id", "row_id", "id")
    return row_id(entry, "row_id", "case_id", "id")


def required_execution_specs(
    backend_matrix_rows: list[dict[str, Any]],
    frontend_matrix_rows: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
) -> list[tuple[str, str, str]]:
    required: list[tuple[str, str, str]] = []
    for row in backend_matrix_rows:
        rid = row_id(row, "backend_row_id", "row_id", "id")
        if rid and row_blocks_execution(row):
            required.append(("backend", rid, row_owner(row)))
    for row in frontend_matrix_rows:
        rid = row_id(row, "frontend_action_id", "action_id", "row_id", "id")
        if rid and row_blocks_execution(row):
            required.append(("frontend", rid, row_owner(row)))
    for case in cases:
        cid = row_id(case, "case_id", "id")
        if cid and row_blocks_execution(case):
            required.append(("packaged", cid, row_owner(case)))
    for row in event_rows:
        rid = row_id(row, "event_state_row_id", "row_id", "id")
        if rid and row_blocks_execution(row):
            required.append(("event-state", rid, row_owner(row)))
    return required


def validate_execution_ledger(
    change_dir: Path,
    backend_matrix_rows: list[dict[str, Any]],
    frontend_matrix_rows: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    *,
    target: str,
    owner_task: str,
) -> list[str]:
    errors: list[str] = []
    required = required_execution_specs(backend_matrix_rows, frontend_matrix_rows, cases, event_rows)
    if target != "all":
        allowed_targets = {target, "event-state"}
        required = [
            item
            for item in required
            if item[0] in allowed_targets and (not owner_task or item[2] == owner_task)
        ]
    if not required:
        return errors

    ledger_path = change_dir / EXECUTION_LEDGER_FILE
    if not ledger_path.exists():
        return [
            f"{change_dir}: missing {EXECUTION_LEDGER_FILE}; execution evidence must be written to the mutable ledger, not sealed mock matrix files"
        ]

    ledger_doc = as_dict(load_yaml(ledger_path))
    entries = execution_ledger_rows(ledger_doc)
    if not entries:
        return [f"{ledger_path}: must define executions/execution_rows/results rows"]

    known_ids = {
        "backend": {row_id(row, "backend_row_id", "row_id", "id") for row in backend_matrix_rows},
        "frontend": {row_id(row, "frontend_action_id", "action_id", "row_id", "id") for row in frontend_matrix_rows},
        "packaged": {row_id(case, "case_id", "id") for case in cases},
        "event-state": {row_id(row, "event_state_row_id", "row_id", "id") for row in event_rows},
    }
    known_ids = {key: {item for item in values if item} for key, values in known_ids.items()}
    sealed_rows_by_target = {
        "backend": {row_id(row, "backend_row_id", "row_id", "id"): row for row in backend_matrix_rows},
        "frontend": {row_id(row, "frontend_action_id", "action_id", "row_id", "id"): row for row in frontend_matrix_rows},
        "packaged": {row_id(case, "case_id", "id"): case for case in cases},
        "event-state": {row_id(row, "event_state_row_id", "row_id", "id"): row for row in event_rows},
    }

    terminal_keys: set[tuple[str, str]] = set()
    seen_keys: set[tuple[str, str, str]] = set()
    for entry in entries:
        entry_target = normalize_target(entry.get("target") or entry.get("layer") or entry.get("matrix"))
        entry_owner = row_owner(entry)
        entry_id = execution_entry_id(entry, entry_target)
        prefix = f"{ledger_path}: execution row {entry_target or '<missing>'}/{entry_id or '<missing>'}"

        if target != "all":
            if entry_target not in {target, "event-state"}:
                continue
            if owner_task and entry_owner != owner_task:
                continue

        if entry_target not in {"backend", "frontend", "packaged", "event-state"}:
            errors.append(f"{prefix} invalid target; use backend/frontend/packaged/event-state")
            continue
        if not entry_id:
            errors.append(f"{prefix} missing row_id/case_id")
            continue
        if not entry_owner:
            errors.append(f"{prefix} missing owner_task/owner_issue")
        if known_ids.get(entry_target) and entry_id not in known_ids[entry_target]:
            errors.append(f"{prefix} references unknown sealed matrix/case row")

        dedupe_key = (entry_target, entry_id, entry_owner)
        if dedupe_key in seen_keys:
            errors.append(f"{prefix} duplicate execution entry for owner {entry_owner}")
        seen_keys.add(dedupe_key)

        sealed_row = sealed_rows_by_target.get(entry_target, {}).get(entry_id, {})
        merged_entry = {**sealed_row, **entry} if sealed_row else entry
        entry_requires_state_proof = entry_target in {"backend", "packaged"}
        errors.extend(validate_result_evidence(
            change_dir,
            merged_entry,
            prefix,
            mode="execution",
            require_state_proof=entry_requires_state_proof,
        ))
        status = text(entry.get("result") or entry.get("status")).lower()
        if status in {"passed", "not_applicable"}:
            terminal_keys.add((entry_target, entry_id))

    for required_target, required_id, required_owner in required:
        if (required_target, required_id) not in terminal_keys:
            owner_text = f" owner={required_owner}" if required_owner else ""
            errors.append(
                f"{ledger_path}: missing terminal execution evidence for {required_target} row {required_id}{owner_text}; "
                "matrix/case rows stay sealed planned rows, execution result must be recorded in mock-acceptance-execution.yaml"
            )
    return errors


def event_state_refs(row: dict[str, Any]) -> set[str]:
    return {text(item) for item in as_list(row.get("event_state_refs") or row.get("stateful_behavior_refs")) if text(item)}


def validate_event_state_matrix(
    change_dir: Path,
    event_doc: dict[str, Any],
    fixture_ids: set[str],
    *,
    mode: str,
) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    rows = event_state_rows(event_doc)
    ids: set[str] = set()
    if not rows:
        return [f"{change_dir}: mock-event-state-matrix.yaml must define event_state_rows/rows when progress/event/stateful signals exist"], ids
    required_fields = [
        "source_contract",
        "operation",
        "mode_or_variant",
        "from_state",
        "trigger",
        "event_or_step",
        "status",
        "to_state",
        "terminal",
        "failure_event_or_reason",
        "expected_result",
        "proves",
    ]
    for row in rows:
        rid = row_id(row, "event_state_row_id", "row_id", "id")
        prefix = f"{change_dir}: event state row {rid or '<missing>'}"
        if not rid:
            errors.append(f"{change_dir}: event state row missing event_state_row_id/id")
            continue
        if rid in ids:
            errors.append(f"{change_dir}: duplicate event state row {rid}")
        ids.add(rid)
        if mode == "planning" and not row_owner(row):
            errors.append(f"{prefix} missing owner_task/owner_issue; event-state rows must have an execution owner")
        for field in required_fields:
            if not text(row.get(field)):
                errors.append(f"{prefix} missing {field}")
        if row.get("terminal") not in {True, False, "true", "false", "yes", "no"}:
            errors.append(f"{prefix} terminal must be explicit true/false")
        if not as_list(row.get("fixture_refs")):
            errors.append(f"{prefix} missing fixture_refs")
        for fixture_ref in [text(item) for item in as_list(row.get("fixture_refs")) if text(item)]:
            if fixture_ref not in fixture_ids:
                errors.append(f"{prefix} references unknown fixture {fixture_ref}")
        if not flatten(row.get("frontend_assertions")) and not flatten(row.get("backend_assertions")):
            errors.append(f"{prefix} missing frontend_assertions or backend_assertions")
        errors.extend(validate_result_evidence(change_dir, row, prefix, mode=mode))
    return errors, ids


def validate_event_state_consumption(
    change_dir: Path,
    event_ids: set[str],
    backend_matrix_rows: list[dict[str, Any]],
    frontend_matrix_rows: list[dict[str, Any]],
    cases: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if not event_ids:
        return errors
    consumers = backend_matrix_rows + frontend_matrix_rows + cases
    consumed: set[str] = set()
    for row in consumers:
        consumed |= event_state_refs(row)
    for event_id in sorted(event_ids - consumed):
        errors.append(f"{change_dir}: event state row {event_id} is not consumed by backend/frontend matrix or packaged case")
    for row in consumers:
        rid = row_id(row, "backend_row_id", "frontend_action_id", "case_id", "row_id", "id") or "<missing>"
        for ref in event_state_refs(row):
            if ref not in event_ids:
                errors.append(f"{change_dir}: row/case {rid} references unknown event state row {ref}")
    return errors


def validate_coverage_for_rows(
    change_dir: Path,
    dimensions_doc: dict[str, Any],
    rows: list[dict[str, Any]],
    coverage_set: dict[str, Any],
    target_name: str,
    *,
    mode: str,
) -> list[str]:
    errors: list[str] = []
    values = dimension_values(dimensions_doc)
    set_id = text(coverage_set.get("id"))
    dims = [text(item) for item in as_list(coverage_set.get("dimensions")) if text(item)]
    if not set_id or not dims:
        return errors
    dim_values = [selected_values(values, coverage_set, dim) for dim in dims]
    if any(not vals for vals in dim_values):
        return errors
    max_cases = int(coverage_set.get("max_expected_cases", 2000))
    combinations = list(itertools.product(*dim_values))
    if len(combinations) > max_cases:
        errors.append(
            f"{change_dir}: coverage_set {set_id} expands to {len(combinations)} combinations for {target_name}; "
            "split it into smaller coverage_sets or add explicit excludes/values"
        )
        return errors
    excludes = as_list(coverage_set.get("excludes"))
    for combo_tuple in combinations:
        combo = dict(zip(dims, combo_tuple))
        if combo_excluded(combo, excludes):
            continue
        found = False
        for row in rows:
            if set_id not in row_coverage_sets(row):
                continue
            if all(row_dimensions(row).get(dim) == value for dim, value in combo.items()):
                valid_statuses = {"passed"} if mode != "planning" else {"planned", "pending", "not_run", "not_started"}
                if text(row.get("result") or row.get("status")).lower() in valid_statuses:
                    found = True
                    break
        if not found:
            values_text = ", ".join(f"{k}={v}" for k, v in combo.items())
            errors.append(f"{change_dir}: {target_name} coverage_set {set_id} missing passed row for {values_text}")
    return errors


def validate_coverage(
    change_dir: Path,
    dimensions_doc: dict[str, Any],
    backend_matrix_rows: list[dict[str, Any]],
    frontend_matrix_rows: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    *,
    mode: str,
    target_filter: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    target_rows = {
        "backend": ("backend matrix", backend_matrix_rows),
        "frontend": ("frontend action matrix", frontend_matrix_rows),
        "packaged": ("packaged representative cases", cases),
    }
    for coverage_set in rows_from(dimensions_doc, "coverage_sets"):
        set_id = text(coverage_set.get("id"))
        targets = coverage_targets(coverage_set)
        if not set_id or not targets:
            continue
        for target in sorted(targets):
            if target_filter and target not in target_filter:
                continue
            target_name, rows = target_rows[target]
            errors.extend(validate_coverage_for_rows(change_dir, dimensions_doc, rows, coverage_set, target_name, mode=mode))
    return errors


def validate_report(
    change_dir: Path,
    report: str,
    cases: list[dict[str, Any]],
    backend_matrix_rows: list[dict[str, Any]],
    frontend_matrix_rows: list[dict[str, Any]],
    *,
    mode: str,
    combined_scope_text: str = "",
) -> list[str]:
    errors: list[str] = []
    if not report:
        return [f"{change_dir}: mock-acceptance.md is missing or empty"]
    for heading in REQUIRED_REPORT_SECTIONS:
        if not section(report, heading):
            errors.append(f"{change_dir}: mock-acceptance.md missing section '{heading}'")
    playground_scope = playground_scope_status(combined_scope_text or report)
    if playground_scope["is_connect_playground"]:
        for heading in PACKAGED_RUNTIME_REPORT_SECTIONS:
            if not section(report, heading):
                errors.append(f"{change_dir}: automqbox/CMP Connect playground mock acceptance report missing section '{heading}'")
        guard = section(report, "Real Controller / No-Cloud Guard Report")
        if guard and not re.search(r"REAL_CONTROLLER_PATH|real[- ]controller|PlaygroundAcceptanceProperties|allowlist|no-cloud|NoCloud", guard, re.IGNORECASE):
            errors.append(f"{change_dir}: Real Controller / No-Cloud Guard Report must discuss affected controller allowlist routing and no-cloud adapter evidence")
        freshness = section(report, "Runtime Freshness Local Audit Report")
        if freshness and not FRESHNESS_RE.search(freshness):
            errors.append(f"{change_dir}: Runtime Freshness Local Audit Report lacks branch/commit/bundle/package/PID/port freshness evidence")
        handoff = (
            section(report, "Packaged Playground Handoff QA")
            or section(report, "Playground Handoff QA")
            or section(report, "Packaged / Runtime Handoff QA")
        )
        if handoff and not re.search(r"Instances|Connect Clusters|Connectors|Plugins|Accounts|Access|Support|Settings", handoff, re.IGNORECASE):
            errors.append(f"{change_dir}: automqbox/CMP Connect packaged playground handoff QA must include top-level application smoke areas")
    case_matrix = section(report, "Case Execution Matrix")
    if not case_matrix:
        return errors
    backend_matrix = section(report, "Backend Mock Matrix")
    frontend_matrix = section(report, "Frontend Action Matrix")
    for row in backend_matrix_rows:
        rid = row_id(row, "backend_row_id", "row_id", "id")
        if rid and rid not in backend_matrix:
            errors.append(f"{change_dir}: mock-acceptance.md Backend Mock Matrix missing {rid}")
    for row in frontend_matrix_rows:
        rid = row_id(row, "frontend_action_id", "action_id", "row_id", "id")
        if rid and rid not in frontend_matrix:
            errors.append(f"{change_dir}: mock-acceptance.md Frontend Action Matrix missing {rid}")
    for case in cases:
        case_id = text(case.get("case_id") or case.get("id"))
        if case_id and case_id not in case_matrix:
            errors.append(f"{change_dir}: mock-acceptance.md Case Execution Matrix missing {case_id}")
    if mode != "planning":
        ledger_doc = as_dict(load_yaml(change_dir / EXECUTION_LEDGER_FILE))
        for entry in execution_ledger_rows(ledger_doc):
            entry_target = normalize_target(entry.get("target") or entry.get("layer") or entry.get("matrix"))
            entry_id = execution_entry_id(entry, entry_target)
            if not entry_id:
                continue
            if entry_target == "backend" and entry_id not in backend_matrix:
                errors.append(f"{change_dir}: mock-acceptance.md Backend Mock Matrix missing execution ledger row {entry_id}")
            elif entry_target == "frontend" and entry_id not in frontend_matrix:
                errors.append(f"{change_dir}: mock-acceptance.md Frontend Action Matrix missing execution ledger row {entry_id}")
            elif entry_target in {"packaged", "event-state"} and entry_id not in case_matrix:
                errors.append(f"{change_dir}: mock-acceptance.md Case Execution Matrix missing execution ledger row {entry_id}")
    for raw_line in report.splitlines():
        if mode != "planning" and SMOKE_ONLY_RE.search(raw_line) and not re.search(r"\b(case[_ -]?id|MAC-[A-Za-z0-9_-]+)\b", raw_line, re.IGNORECASE):
            errors.append(
                f"{change_dir}: smoke evidence is not tied to a Case ID: {raw_line.strip()[:160]}"
            )
    for heading in ["CMP Playground Architecture Matrix", "Playground Simulation Contract", "CMP Playground Coverage Matrix", "Fixture Graph Matrix"]:
        body = section(report, heading)
        if body and not re.search(r"\b(case[_ -]?id|MAC-|not_applicable|N/A|decision)\b", body, re.IGNORECASE):
            errors.append(f"{change_dir}: {heading} rows must reference case_id or locked N/A decision")
    return errors


def playground_scope_status(combined_text: str) -> dict[str, bool]:
    return {
        "has_playground_signal": bool(PACKAGED_RUNTIME_PLAYGROUND_SIGNAL_RE.search(combined_text)),
        "has_automqbox_signal": bool(AUTOMQBOX_REPO_SIGNAL_RE.search(combined_text)),
        "has_connect_domain_signal": bool(CONNECT_DOMAIN_SIGNAL_RE.search(combined_text)),
        "is_connect_playground": bool(
            PACKAGED_RUNTIME_PLAYGROUND_SIGNAL_RE.search(combined_text)
            and AUTOMQBOX_REPO_SIGNAL_RE.search(combined_text)
            and CONNECT_DOMAIN_SIGNAL_RE.search(combined_text)
        ),
    }


def markdown_table_rows(markdown: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        if re.fullmatch(r"\|[\s:\-|]+\|", line):
            continue
        rows.append([cell.strip().strip("`") for cell in line.strip("|").split("|")])
    return rows


def validate_frontend_fixture_needs(change_dir: Path, fixture_ids: set[str], cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    matrix_path = change_dir / "frontend-fixture-need-matrix.md"
    if not matrix_path.exists():
        return errors
    rows = markdown_table_rows(matrix_path.read_text(encoding="utf-8"))
    if not rows:
        return [f"{matrix_path}: frontend fixture need matrix has no table rows"]
    header = [cell.lower() for cell in rows[0]]
    try:
        fixture_idx = next(i for i, cell in enumerate(header) if "fixture" in cell)
    except StopIteration:
        return [f"{matrix_path}: missing Fixture needed column"]
    for row in rows[1:]:
        if len(row) <= fixture_idx:
            continue
        fixture_text = row[fixture_idx]
        if not fixture_text or fixture_text.lower() in {"n/a", "none", "todo", "tbd", "unknown"}:
            continue
        tokens = {
            token
            for token in re.split(r"[\s,;，；]+", fixture_text)
            if token and token.lower() not in {"and", "or", "fixture", "fixtures"}
        }
        matched_fixture = any(token in fixture_ids for token in tokens)
        matched_case = any(any(token in {text(item) for item in as_list(case.get("fixture_refs"))} for token in tokens) for case in cases)
        if not matched_fixture:
            errors.append(f"{matrix_path}: fixture need row is not backed by mock-fixture-graph.yaml fixture id: {fixture_text}")
        if not matched_case:
            errors.append(f"{matrix_path}: fixture need row is not consumed by any mock acceptance case fixture_refs: {fixture_text}")
    return errors


def validate_packaged_runtime_simulation_if_needed(change_dir: Path, combined_text: str, *, mode: str) -> list[str]:
    has_files = any((change_dir / rel).exists() for rel in PLAYGROUND_SIMULATION_FILES)
    scope = playground_scope_status(combined_text)
    if not has_files and not scope["has_playground_signal"]:
        return []
    if has_files and not scope["is_connect_playground"]:
        return [
            f"{change_dir}: playground simulation artifacts are automqbox/CMP Connect-only; "
            "remove playground-* files and use generic mock acceptance, or add explicit automqbox/CMP Connect scope evidence"
        ]
    if scope["has_playground_signal"] and not scope["is_connect_playground"]:
        return [
            f"{change_dir}: packaged playground is only enabled for automqbox/CMP Connect features; "
            "non-Connect automqbox/CMP work must use generic mock acceptance and must not read cmp-playground facts"
        ]
    if mode == "planning":
        return []
    script_path = Path(__file__).resolve().parent / "validate_playground_simulation_contract.py"
    try:
        spec = importlib.util.spec_from_file_location("validate_playground_simulation_contract", script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot create import spec for {script_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        validate_packaged_runtime_simulation = module.validate
    except Exception as exc:
        return [f"{change_dir}: cannot load playground simulation validator: {exc}"]
    return validate_packaged_runtime_simulation(change_dir, mode=mode)


def validate_no_production_downgrade_language(change_dir: Path, *, mode: str) -> list[str]:
    candidates = [
        "atomic-issue-packets.yaml",
        "task-dag.yaml",
        "tasks.md",
        "contracts.yaml",
        "verification.yaml",
        "mock-backend-matrix.yaml",
        "mock-frontend-action-matrix.yaml",
        "mock-acceptance-cases.yaml",
        "mock-acceptance.md",
    ]
    errors: list[str] = []
    for rel in candidates:
        path = change_dir / rel
        if not path.exists():
            continue
        body = path.read_text(encoding="utf-8", errors="ignore")
        for match in PRODUCTION_DOWNGRADE_RE.finditer(body):
            snippet = re.sub(r"\s+", " ", body[max(0, match.start() - 80): match.end() + 80]).strip()
            errors.append(
                f"{path}: wording may downgrade production implementation to local/no-cloud acceptance: {snippet}. "
                "Production code must call the real provider/K8s/Connect REST/runtime/resource adapter; no-cloud/playground may only receive that call during acceptance."
            )
            break
    return errors


def validate(change_dir: Path, *, mode: str = "execution", target: str = "all", owner_task: str = "") -> list[str]:
    errors: list[str] = []
    if mode not in {"planning", "execution"}:
        return [f"{change_dir}: invalid mock acceptance validation mode {mode}"]
    target = normalize_target(target)
    if target not in {"all", "backend", "frontend", "packaged"}:
        return [f"{change_dir}: invalid mock acceptance target {target}"]
    for rel in REQUIRED_FILES:
        if not (change_dir / rel).exists():
            errors.append(f"{change_dir}: missing required mock acceptance artifact {rel}")
    if errors:
        return errors
    dimensions_doc = as_dict(load_yaml(change_dir / "mock-test-dimensions.yaml"))
    backend_doc = as_dict(load_yaml(change_dir / "mock-backend-matrix.yaml"))
    frontend_doc = as_dict(load_yaml(change_dir / "mock-frontend-action-matrix.yaml"))
    cases_doc = as_dict(load_yaml(change_dir / "mock-acceptance-cases.yaml"))
    fixture_doc = as_dict(load_yaml(change_dir / "mock-fixture-graph.yaml"))
    report = (change_dir / "mock-acceptance.md").read_text(encoding="utf-8")
    combined_for_stateful = "\n".join(
        flatten(doc)
        for doc in [dimensions_doc, backend_doc, frontend_doc, cases_doc, fixture_doc, report]
    )
    has_stateful = bool(STATEFUL_SIGNAL_RE.search(combined_for_stateful))

    errors.extend(validate_dimensions(change_dir, dimensions_doc))
    fixture_errors, fixture_ids = validate_fixture_graph(change_dir, fixture_doc)
    errors.extend(fixture_errors)
    event_ids: set[str] = set()
    if has_stateful:
        event_path = change_dir / OPTIONAL_STATEFUL_FILE
        if not event_path.exists():
            errors.append(f"{change_dir}: missing required mock acceptance artifact {OPTIONAL_STATEFUL_FILE} for progress/event/status/terminal semantics")
        else:
            event_doc = as_dict(load_yaml(event_path))
            matrix_mode = "planning" if mode == "execution" else mode
            event_errors, event_ids = validate_event_state_matrix(change_dir, event_doc, fixture_ids, mode=matrix_mode)
            errors.extend(event_errors)
    backend_matrix_rows = backend_rows(backend_doc)
    frontend_matrix_rows = frontend_rows(frontend_doc)
    cases = rows_from(cases_doc, "cases")
    event_matrix_rows = event_state_rows(event_doc) if has_stateful and "event_doc" in locals() else []
    if mode == "execution" and target != "all":
        if target == "backend":
            backend_matrix_rows = filter_rows_for_owner(backend_matrix_rows, owner_task)
            frontend_matrix_rows = []
            cases = []
            event_matrix_rows = filter_rows_for_owner(event_matrix_rows, owner_task)
        elif target == "frontend":
            backend_matrix_rows = []
            frontend_matrix_rows = filter_rows_for_owner(frontend_matrix_rows, owner_task)
            cases = []
            event_matrix_rows = filter_rows_for_owner(event_matrix_rows, owner_task)
        elif target == "packaged":
            backend_matrix_rows = []
            frontend_matrix_rows = []
            cases = filter_cases_for_owner(cases, owner_task)
            event_matrix_rows = filter_rows_for_owner(event_matrix_rows, owner_task)

    matrix_mode = "planning" if mode == "execution" else mode

    backend_errors, backend_ids = validate_backend_matrix(
        change_dir,
        {"backend_rows": backend_matrix_rows},
        fixture_ids,
        mode=matrix_mode,
    ) if target in {"all", "backend"} else ([], {row_id(row, "backend_row_id", "row_id", "id") for row in backend_rows(backend_doc)})
    frontend_errors, frontend_ids = validate_frontend_action_matrix(
        change_dir,
        {"actions": frontend_matrix_rows},
        fixture_ids,
        mode=matrix_mode,
    ) if target in {"all", "frontend"} else ([], {row_id(row, "frontend_action_id", "action_id", "row_id", "id") for row in frontend_rows(frontend_doc)})
    errors.extend(backend_errors)
    errors.extend(frontend_errors)
    if target in {"all", "packaged"} and not cases:
        errors.append(f"{change_dir}: mock-acceptance-cases.yaml must define cases")
    if target in {"all", "packaged"}:
        seen: set[str] = set()
        for case in cases:
            case_id = text(case.get("case_id") or case.get("id"))
            if case_id in seen:
                errors.append(f"{change_dir}: duplicate mock acceptance case {case_id}")
            seen.add(case_id)
            errors.extend(validate_case_shape(change_dir, case, fixture_ids, mode=matrix_mode))
        errors.extend(validate_case_matrix_links(change_dir, cases, backend_ids, frontend_ids))
    if has_stateful and target == "all":
        errors.extend(validate_event_state_consumption(change_dir, event_ids, backend_matrix_rows, frontend_matrix_rows, cases))
    coverage_target_filter = None if target == "all" else {target}
    errors.extend(validate_coverage(
        change_dir,
        dimensions_doc,
        backend_matrix_rows,
        frontend_matrix_rows,
        cases,
        mode=matrix_mode,
        target_filter=coverage_target_filter,
    ))
    if mode == "execution":
        errors.extend(validate_execution_ledger(
            change_dir,
            backend_matrix_rows,
            frontend_matrix_rows,
            cases,
            event_matrix_rows,
            target=target,
            owner_task=owner_task,
        ))
    if target == "all":
        errors.extend(validate_no_production_downgrade_language(change_dir, mode=mode))
        errors.extend(validate_report(
            change_dir,
            report,
            cases,
            backend_matrix_rows,
            frontend_matrix_rows,
            mode=mode,
            combined_scope_text=combined_for_stateful,
        ))
        errors.extend(validate_frontend_fixture_needs(change_dir, fixture_ids, cases))
        errors.extend(validate_packaged_runtime_simulation_if_needed(change_dir, combined_for_stateful, mode=mode))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("change_dir", type=Path)
    parser.add_argument(
        "--mode",
        choices=["planning", "execution"],
        default="execution",
        help="planning validates concrete planned case rows; execution requires passed results and evidence.",
    )
    parser.add_argument(
        "--target",
        choices=["all", "backend", "backend-matrix", "mock-backend", "frontend", "frontend-action", "frontend-matrix", "mock-frontend", "packaged", "packaged-case", "packaged-cases", "playground"],
        default="all",
        help="execution target layer. Planning mode still validates the full generated system.",
    )
    parser.add_argument(
        "--owner-task",
        default="",
        help="optional owner task id used in execution mode to select row-owned evidence when matrices carry owner_task/owner_issue fields.",
    )
    args = parser.parse_args()
    try:
        target = "all" if args.mode == "planning" else args.target
        errors = validate(args.change_dir, mode=args.mode, target=target, owner_task=args.owner_task)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Strict mock acceptance case validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
