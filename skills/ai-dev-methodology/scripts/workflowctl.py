#!/usr/bin/env python3
"""Structured validator for AutoMQ AI workflow sidecar files.

Markdown remains the human-readable artifact, but YAML sidecars are the
machine-enforced contract graph. This tool validates graph consistency, task
DAG ordering, supersession/backflow invalidation, and blocking Not Run risks.
"""

from __future__ import annotations

import argparse
import copy
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    yaml = None


WORKFLOW_STATE_MACHINE_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "workflow-state-machine.yaml"
)
SKILLS_ROOT = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills"


def load_workflow_state_machine() -> dict[str, Any]:
    if yaml is None:
        raise ValueError("PyYAML is required for workflow state-machine loading")
    try:
        doc = yaml.safe_load(WORKFLOW_STATE_MACHINE_PATH.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ValueError(f"{WORKFLOW_STATE_MACHINE_PATH}: invalid state-machine YAML: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise ValueError(f"{WORKFLOW_STATE_MACHINE_PATH}: schema_version must be 1")
    return doc


WORKFLOW_STATE_MACHINE = load_workflow_state_machine()


DECISION_ID_PATTERN = (
    r"(?:PDEC|ADEC|DEC(?:-[A-Z][A-Z0-9]*)?|READY-DEC|ARCH-DEC|"
    r"DESIGN-DEC|MIG-DEC|UI-DEC|VER-DEC|TASK-DEC)-\d{3}"
)
DESIGN_DECISION_ID_RE = re.compile(rf"\b{DECISION_ID_PATTERN}\b")
EXTERNAL_DESIGN_OBJECT_ID_RE = re.compile(r"\b(?:MECH|EXTMECH|FACT|EXT|CONSTRAINT|XCON)-\d{3}\b")
MECHANISM_MODEL_ID_RE = re.compile(r"\b(?:MECH|OPSEQ|EXTAPI|EVT|RMM|RLM|FCM|MIM)-\d{3}\b")
MECHANISM_PLACEHOLDER_RE = re.compile(
    r"\b(?:MECH|OPSEQ|EXTAPI|EVT|RMM|RLM|FCM|MIM|FACT|CONSTRAINT|C|VER)-xxx\b|"
    r"\bTxxx\b|\bRMP-MAP-xxx\b|\bPCP-xxx\b|\bxxx\b|<[^>]+>|"
    r"path/File\.java|rg \.\.\.|POST /\.\.\.|"
    r"locked alternative|provider module|consumer module|provider/resource writer module|"
    r"runtime materialization owner module|frontend/API/service/provider/runtime|"
    r"canonical request fields|canonical response/readback fields|typed errors/warnings|"
    r"API/resource/metric name|how the external mechanism actually works|"
    r"parameter name -> meaning -> limits/defaults|create/update/delete/prune semantics|"
    r"ADEC/C/VER consequence",
    re.IGNORECASE,
)
MECHANISM_UNRESOLVED_RE = re.compile(
    r"\b(?:TBD|TODO|unknown|open|待确认|未知|未决|后续决定|task-planning|implementation)\b|(?<![_-])\bblocked\b(?![_-])",
    re.IGNORECASE,
)
OBJECT_RE = re.compile(rf"^(?:SRC|REQ|SCN|C|MIG|VER)-\d{{3}}$|^{DECISION_ID_PATTERN}$|^T\d{{3}}$|^SCP-\d{{3}}(?:-T\d{{3}})?$")
SCP_ID_RE = re.compile(r"^SCP-\d{3}(?:-T\d{3})?$")
TASK_RE = re.compile(r"^T\d{3}$")
CONTRACT_RE = re.compile(r"^C-\d{3}$")
VER_RE = re.compile(r"^VER-\d{3}$")
DECISION_RE = re.compile(rf"^{DECISION_ID_PATTERN}$")
REQ_SCN_RE = re.compile(r"^(?:REQ|SCN)-\d{3}$")
LABEL_ONLY_CARRIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)+$")
GENERIC_PACKET_TEXT_RE = re.compile(
    r"(?:REQ|SCN)-\d{3}\s+针对\s+.+?的执行输入：本任务只处理已锁定的字段、接口、页面或验收行"
    r"|Executable requirement semantics for (?:REQ|SCN)-\d{3} must be preserved by owner tasks"
    r"|(?:FACT|CONSTRAINT|EXT|XCON)-\d{3}\s+constrains provider resources, scaling, reachability, lifecycle, or mock boundary behavior"
    r"|(?:PDEC|ADEC|DEC|MIG-DEC|UI-DEC|TASK-DEC)-\d{3}\s+locks the .+? behavior used by this task; implementation must not reinterpret it"
    r"|Decision\s+(?:PDEC|ADEC|DEC|MIG-DEC|UI-DEC|TASK-DEC)-\d{3}\s+is locked and cannot be reinterpreted during implementation"
    r"|Implement/prove\s+.+?\s+owned behavior here"
    r"|Allowlist owner path for API/service/persistence/runtime proof semantics when this backend contract requires it"
    r"|FACT-\d{3}\s+constrains .+? behavior"
    r"|CONSTRAINT-\d{3}\s+constrains .+? behavior",
    re.IGNORECASE,
)
MOCK_ACCEPTANCE_SIGNAL_RE = re.compile(
    r"\b(mock|repo-specific acceptance runtime|acceptance runtime|MockData|MockControllerAspect|@MockFor|fixture|no-cloud|"
    r"external dependenc(?:y|ies)|provider|orchestrator|runtime|packaged acceptance|packaged playground|repo-specific packaged acceptance|"
    r"mock-acceptance|browser acceptance|Playwright|DOM|HAR|trace)\b|"
    r"模拟|验收|无云|外部依赖|浏览器|点击|提交|前端",
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
TASK_SELF_REQUIREMENT_SOURCE_RE = re.compile(
    r"\b(?:this task|T\d{3})\s+must\b|本任务必须|本任务需要|该任务必须|当前任务必须",
    re.IGNORECASE,
)
QUALITY_GATE_PHRASE_RE = re.compile(
    r"must materialize\s+(?:DS|REQ|SCN|C|VER|DEC)[-\dA-Z]*\s+into behavior"
    r"|只保留 validator 需要|validator 需要|gate phrase|过 validator|为了通过",
    re.IGNORECASE,
)
FRONTEND_CLAIMS_PROVIDER_PROOF_RE = re.compile(
    r"provider mutation proof|ownership readback proof|cleanup/protect proof|云资源.*(?:创建|删除|清理).*证明|后端.*provider.*proof",
    re.IGNORECASE,
)
ALLOWLIST_CEILING_RE = re.compile(
    r"allowlist ceiling|validator feasibility|not an implementation instruction|support only|"
    r"仅.*allowlist|仅.*validator|不是.*实现.*指令|不作为.*实现|校验.*范围|门禁.*范围",
    re.IGNORECASE,
)
TEMPLATE_REVIEW_EVIDENCE_RE = re.compile(
    r"Checked atomic-issues/T\d{3}\.md Source Context against atomic-issue-packets\.yaml and task-dag\.yaml; source excerpts are upstream facts, not task self-requirements\."
    r"|Checked atomic-issues/T\d{3}\.md execution brief, verification and done criteria"
    r"|Checked task-dag\.yaml, contracts\.yaml, verification\.yaml and atomic-task-decomposition\.md owner mapping",
    re.IGNORECASE,
)
BACKEND_CLAIMS_BROWSER_PROOF_RE = re.compile(
    r"\b(?:DOM|browser|screenshot|visual|click|rendered selector|no raw text)\s+proof\b|浏览器.*证明|DOM.*证明|截图.*证明",
    re.IGNORECASE,
)
MOCK_ACCEPTANCE_EXECUTION_STAGES = {"mock-acceptance", "product-acceptance", "acceptance", "all"}
MOCK_ACCEPTANCE_PLANNING_STAGES = {"task-planning", "pre-execution"}
MOCK_ACCEPTANCE_TARGETS = {"backend", "frontend", "packaged"}
MOCK_ACCEPTANCE_LAYER_TARGETS = {
    "mock-backend": "backend",
    "backend-mock": "backend",
    "mock_backend": "backend",
    "mock-frontend": "frontend",
    "frontend-mock": "frontend",
    "mock_frontend": "frontend",
    "packaged-playground": "packaged",
    "packaged": "packaged",
    "playground-acceptance": "packaged",
}
VALID_STAGE_STATUS = set(WORKFLOW_STATE_MACHINE.get("valid_stage_statuses", []))
DECISION_SURFACE_STAGE_ALIASES = {
    "PRD": "prd",
    "AIP": "aip",
    "readiness": "readiness",
    "design": "design",
    "archaeology": "archaeology",
    "migration": "migration",
    "frontend-contract": "frontend-contract",
    "cross-module-contract": "contract",
    "verification": "verification",
    "task-planning": "task-planning",
}
ROUTED_DECISION_SURFACE_RE = re.compile(r"\brouted-to-[a-z-]+\b|\brouted\b|stage-owned", re.IGNORECASE)
DECISION_SURFACE_LOCKED_NA_RE = re.compile(
    r"\blocked\s+N/A\b|locked N/A|locked-na|locked not applicable|not-applicable|not applicable|不适用",
    re.IGNORECASE,
)
DECISION_SURFACE_BLOCKED_BACKFLOW_RE = re.compile(
    r"\bblocked[- ]backflow\b|\bbackflow[- ]blocked\b|\bblocked\s+by\s+backflow\b|阻塞回流|回流阻塞",
    re.IGNORECASE,
)
DECISION_SURFACE_CLOSED_RE = re.compile(
    r"\blocked\s+(?:decision|ADEC|DEC|PDEC|READY-DEC|DESIGN-DEC|ARCH-DEC|UI-DEC|VER-DEC)|"
    r"\bcontract\s+candidate\b|"
    r"\b(?:PDEC|ADEC|DEC(?:-[A-Z][A-Z0-9]*)?|READY-DEC|ARCH-DEC|DESIGN-DEC|MIG-DEC|UI-DEC|VER-DEC|TASK-DEC)-\d{3}\b|"
    r"\bC-\d{3}\b|\bVER-\d{3}\b|\bT\d{3}\b|锁定(?:决策|契约|验证|任务)|锁定为\s*(?:PDEC|ADEC|DEC|READY-DEC|ARCH-DEC|DESIGN-DEC|MIG-DEC|UI-DEC|VER-DEC|TASK-DEC|C|VER|T|N/A|不适用)|契约候选",
    re.IGNORECASE,
)

TERMINAL_TASK_STATUSES = {"passed", "done", "completed", "complete", "完成"}
EXECUTION_MUTABLE_RELATIVE = {
    "workflow-state.yaml",
    "execution-state.yaml",
    "task-verification-log.yaml",
    "task-semantic-review.yaml",
    "mock-acceptance-execution.yaml",
    "workflow-events.yaml",
    "launch-readiness-review.md",
}
EXECUTION_MUTABLE_PREFIXES = ("task-receipts/",)
SYSTEM_NOISE_BASENAMES = {".DS_Store", "Thumbs.db"}
SYSTEM_NOISE_PATH_RE = re.compile(
    r"(^|/)(?:__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.gradle|target|node_modules|dist|build|coverage)(?:/|$)"
    r"|(?:\.pyc|\.pyo|\.class|\.log|\.tmp|\.swp)$",
    re.IGNORECASE,
)

ALL_STAGES = [str(item) for item in WORKFLOW_STATE_MACHINE.get("stage_order", [])] + ["all"]

STAGE_CONSTRUCTION_PROTOCOL = "stage-construction-v1"
STAGE_CONSTRUCTION_CONTRACT_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "stage-construction-contracts.yaml"
)
WORKFLOW_RUNTIME_MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "workflow-runtime-manifest.yaml"
)
WORKFLOW_DEFECT_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "workflow-defects.yaml"
)
WORKFLOW_PROFILES = {"full", "execution-only", "repair", "migration"}
STAGE_CONSTRUCTION_STAGES = {
    str(item) for item in WORKFLOW_STATE_MACHINE.get("construction_stages", [])
}
STAGE_OBLIGATION_STATUSES = {
    "open",
    "in_progress",
    "blocked",
    "pending-rewrite",
    "closed",
    "not_applicable",
}

MULTI_PERSPECTIVE_REVIEW_STAGES = {
    "prd",
    "readiness",
    "aip",
    "design",
    "archaeology",
    "migration",
    "frontend-contract",
    "contract",
    "verification",
    "task-planning",
    "pre-execution",
    "mock-acceptance",
    "product-acceptance",
}
MULTI_PERSPECTIVE_STAGE_ALIASES = {
    "requirement-readiness": "readiness",
    "aip-readiness": "readiness",
    "aip-mechanism-design": "aip",
    "new-feature-design": "design",
    "code-archaeology": "archaeology",
    "migration-diff": "migration",
    "cross-module-contract": "contract",
    "verification-matrix": "verification",
    "atomic-task-planning": "task-planning",
    "retrospective": "convergence-retrospective",
}
MULTI_PERSPECTIVE_ALLOWED_STAGES = set(ALL_STAGES) | {"convergence-retrospective"}
LAUNCH_READINESS_FINDING_TYPES = {
    "implementation_gap",
    "atomic_task_gap",
    "launch_decision_required",
    "acceptance_gap",
    "methodology_gap",
    "allowed_implementation_variance",
}
LAUNCH_READINESS_CLOSURE_DIMENSIONS = {
    "user journey",
    "domain semantic",
    "runtime / external effect",
    "state and failure",
    "compatibility and boundary",
    "acceptance evidence",
}
MULTI_PERSPECTIVE_ALLOWED_STAGES.update(MULTI_PERSPECTIVE_STAGE_ALIASES)
MULTI_PERSPECTIVE_ALLOWED_REVIEWER_TYPES = {"readonly-subagent", "read-only-subagent"}
MULTI_PERSPECTIVE_ALLOWED_DISPOSITIONS = {"accepted", "rejected", "deferred", "backflow-created", "superseded"}
MULTI_PERSPECTIVE_ALLOWED_SEVERITIES = {"blocker", "major", "minor", "question"}

STAGE_PREREQUISITES = {
    str(stage): [str(item) for item in values]
    for stage, values in dict(WORKFLOW_STATE_MACHINE.get("prerequisites", {})).items()
}
RUNTIME_PREREQUISITES = {
    str(item) for item in WORKFLOW_STATE_MACHINE.get("runtime_prerequisites", [])
}

TASK_PLANNING_UPSTREAM_RECEIPT_STAGES = [
    "source-intake",
    "prd",
    "aip",
    "readiness",
    "design",
    "archaeology",
    # Optional consumed upstream: included when a migration receipt exists for the change.
    "migration",
    "frontend-contract",
    "contract",
    "verification",
]

WORKDIR_IDENTITY_ARTIFACT = "workflow-workdir.md"
PLAN_SNAPSHOT_STAGES = {
    str(item) for item in WORKFLOW_STATE_MACHINE.get("plan_snapshot_stages", [])
}
STAGE_OWNER_SKILL_PATHS = {
    "source-intake": "automq-ai-dev-workflow-contextpack/SKILL.md",
    "prd": "product-requirement-design/SKILL.md",
    "aip": "aip-template/SKILL.md + aip-readiness-review/SKILL.md",
    "readiness": "requirement-readiness-review/SKILL.md",
    "design": "new-feature-design/SKILL.md",
    "archaeology": "code-archaeology-sdd/SKILL.md",
    "migration": "migration-diff-analysis/SKILL.md",
    "frontend-contract": "frontend-contract-design/SKILL.md",
    "contract": "cross-module-contract-sdd/SKILL.md",
    "verification": "verification-matrix/SKILL.md",
    "task-planning": "atomic-task-planning/SKILL.md",
    "mock-acceptance": "mock-acceptance-gate/SKILL.md",
    "product-acceptance": "product-acceptance-review/SKILL.md",
}
STAGE_COMPLETENESS_HEADINGS = {
    "source-intake": "Stage 0: Source Intake",
    "prd": "Stage 1: Product Requirement / PRD",
    "aip": "Stage 2: AIP / Engineering Design",
    "readiness": "Stage 2: AIP / Engineering Design",
    "archaeology": "Stage 3: Code Archaeology",
    "design": "Stage 4: New Feature Design",
    "migration": "Stage 5: Migration Diff",
    "frontend-contract": "Stage 6: Frontend Contract",
    "contract": "Stage 7: Cross-Module Contract",
    "verification": "Stage 8: Verification Matrix",
    "task-planning": "Stage 9: Atomic Task Planning",
}

STAGE_RECEIPT_REQUIRED_ARTIFACTS = {
    str(stage): [str(item) for item in values]
    for stage, values in dict(WORKFLOW_STATE_MACHINE.get("receipt_artifacts", {})).items()
}

HUMAN_DECISION_REQUIRED_STAGES = {
    "prd",
    "aip",
    "readiness",
    "design",
    "archaeology",
    "migration",
    "frontend-contract",
    "contract",
    "verification",
    "task-planning",
    "mock-acceptance",
    "product-acceptance",
}
HUMAN_DECISION_DEFAULT_PREFIXES = {
    "prd": ("PDEC-",),
    "aip": ("ADEC-",),
    "readiness": ("ADEC-",),
}
HUMAN_DECISION_STATUS_RE = re.compile(r"\b(?:locked|open|superseded)\b", re.IGNORECASE)
HUMAN_DECISION_RESPONSE_RE = re.compile(
    r"confirmed|needs-change|no-response|ai-authorized|user-confirmed|用户|确认|授权|暂不|重写|保持",
    re.IGNORECASE,
)
HUMAN_DECISION_PROMPT_RE = re.compile(r"\b(?:HDP-\d{3}|Human Decision Prompt|Prompt ID|prompt summary|决策提示|逐条)\b", re.IGNORECASE)
HUMAN_DECISION_TIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}|decided at|confirmed at|更新时间|确认时间", re.IGNORECASE)

OPTIONAL_RECEIPT_ARTIFACTS = {
    "source-intake": ["external-capability-research.md"],
    "prd": ["decision-surface-discovery.md"],
    "aip": ["decision-surface-discovery.md", "external-capability-research.md", "mechanism-design-model.md"],
    "readiness": ["decision-surface-discovery.md", "external-capability-research.md", "mechanism-design-model.md"],
    "design": ["decision-surface-discovery.md", "external-capability-research.md", "mechanism-design-model.md"],
    "archaeology": [
        "decision-surface-discovery.md",
        "external-capability-research.md",
        "mechanism-design-model.md",
        "existing-object-action-consumer-graph.md",
        "variant-impact-matrix.md",
        "runtime-materialization-parity.md",
        "runtime-test-topology-matrix.md",
    ],
    "migration": ["decision-surface-discovery.md", "external-capability-research.md", "mechanism-design-model.md"],
    "frontend-contract": ["decision-surface-discovery.md", "external-capability-research.md", "mechanism-design-model.md"],
    "contract": [
        "decision-surface-discovery.md",
        "external-capability-research.md",
        "mechanism-design-model.md",
        "stateful-behavior-matrix.yaml",
        "stateful-behavior-matrix.md",
        "existing-object-action-consumer-graph.md",
        "variant-impact-matrix.md",
        "runtime-materialization-parity.md",
        "progress-change-producer-chain-matrix.md",
        "external-side-effect-contract-matrix.md",
        "runtime-test-topology-matrix.md",
    ],
    "verification": [
        "decision-surface-discovery.md",
        "external-capability-research.md",
        "mechanism-design-model.md",
        "stateful-behavior-matrix.yaml",
        "stateful-behavior-matrix.md",
        "existing-object-action-consumer-graph.md",
        "variant-impact-matrix.md",
        "runtime-materialization-parity.md",
        "progress-change-producer-chain-matrix.md",
        "external-side-effect-contract-matrix.md",
        "runtime-test-topology-matrix.md",
    ],
    "task-planning": [
        "decision-surface-discovery.md",
        "external-capability-research.md",
        "mechanism-design-model.md",
        "stateful-behavior-matrix.yaml",
        "stateful-behavior-matrix.md",
        "existing-object-action-consumer-graph.md",
        "variant-impact-matrix.md",
        "runtime-materialization-parity.md",
        "progress-change-producer-chain-matrix.md",
        "external-side-effect-contract-matrix.md",
        "runtime-test-topology-matrix.md",
    ],
    "pre-execution": [
        "decision-surface-discovery.md",
        "external-capability-research.md",
        "mechanism-design-model.md",
        "stateful-behavior-matrix.yaml",
        "stateful-behavior-matrix.md",
        "existing-object-action-consumer-graph.md",
        "variant-impact-matrix.md",
        "runtime-materialization-parity.md",
        "progress-change-producer-chain-matrix.md",
        "external-side-effect-contract-matrix.md",
        "runtime-test-topology-matrix.md",
    ],
    "mock-acceptance": ["mock-event-state-matrix.yaml"],
}

REQUIRED_FRONTEND_CONTRACT_FILES = {
    "frontend-page-inventory.md": ["Page/route", "Purpose", "Reference", "Layout pattern"],
    "frontend-action-inventory.md": [
        "Action",
        "User intent",
        "Reachable from",
        "Side effect/API called",
        "Success behavior",
        "Failure behavior",
        "Owner issue",
    ],
    "frontend-route-component-matrix.md": [
        "Action ID",
        "Visible action",
        "Source component",
        "Permission/visibility guard",
        "Click handler",
        "Final route/API",
        "Router definition",
        "Landing component/file",
        "Mode branch required",
        "Forbidden inherited UI/API",
        "Verification",
        "Owner issue",
    ],
    "frontend-mode-field-display-matrix.md": [
        "Surface",
        "Mode/state",
        "Data source",
        "Must show",
        "Must hide",
        "Fixture ref",
        "Assertion",
    ],
    "frontend-form-state-matrix.md": [
        "Form/step",
        "Active fields",
        "Inactive/hidden fields",
        "Validation trigger",
        "Submit participation",
    ],
    "frontend-mode-leakage-negative-matrix.md": [
        "Surface/action",
        "Forbidden DOM/text",
        "Forbidden payload fields",
        "Assertion method",
    ],
    "frontend-api-payload-contract-matrix.md": [
        "Action ID",
        "Mode/state",
        "Method/path",
        "Request body canonical path",
        "Allowed keys",
        "Forbidden keys / semantic aliases",
        "Required/nullable/default/derived rule",
        "Legacy compatibility rule",
        "Network exact-key assertion",
        "Owner issue",
    ],
    "frontend-fixture-need-matrix.md": [
        "Page/action",
        "Fixture needed",
        "State variant",
        "Browser assertion",
    ],
    "frontend-browser-verification-matrix.md": [
        "User task ID",
        "Action ID",
        "Browser steps",
        "Network assertions",
        "DOM assertions",
        "Screenshot/trace",
    ],
}
REFERENCE_FRONTEND_CONTRACT_FILES = {
    "frontend-reference-pattern-matrix.md": [
        "Reference ID",
        "Target surface/action",
        "Reference source",
        "Reference file/component",
        "Must reuse/adapt",
        "Must not inherit",
        "Visual/layout obligation",
        "Interaction/state obligation",
        "Browser/visual proof",
        "Owner issue",
    ],
}
REQUIRED_CONTRACT_MATRIX_FILES = {
    "contract-semantic-type-matrix.md": [
        "Interaction / Contract",
        "From -> To",
        "Primary semantic type",
        "Canonical provider fact",
        "Canonical consumer assumption",
        "Required granularity checklist",
        "Verification / exact proof",
        "Status",
    ],
    "api-wire-shape-matrix.md": [
        "Contract",
        "Operation",
        "Method/path",
        "Request canonical body/query",
        "Allowed keys",
        "Forbidden keys / semantic aliases",
        "Required/nullable/default/derived rule",
        "Legacy compatibility rule",
        "Response/readback keys",
        "Exact-key verification",
        "Owner issue",
    ],
}
CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS = [
    "Contract",
    "Sub-obligation ID",
    "Edge",
    "Edge type",
    "Sub-obligation type",
    "Semantic type",
    "Operation / surface",
    "Canonical owner",
    "Fields/resource/state",
    "Provider guarantee",
    "Consumer assumption",
    "Failure / timing detail",
    "State/resource owner",
    "Owner module",
    "Verification proof",
    "Split hint",
]
LEGACY_CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS = [
    column if column != "Owner module" else "Suggested owner module"
    for column in CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS
]
CONTRACT_OBLIGATION_OPERATION_TERMS = [
    "create",
    "check",
    "resize",
    "update",
    "worker_spec",
    "worker spec",
    "detail",
    "readback",
    "delete",
    "progress",
    "last-change",
    "change-detail",
    "scaling",
    "autoscaling",
    "reachability",
    "metrics",
    "logs",
    "workers",
    "connectors",
]
CONTRACT_OBLIGATION_RESOURCE_TERMS = [
    "asg",
    "auto scaling group",
    "launch template",
    "lt",
    "security group",
    "sg",
    "iam",
    "role",
    "profile",
    "instance profile",
    "vpc",
    "subnet",
    "k8s",
    "kubernetes",
    "hpa",
    "serviceaccount",
]
CONTRACT_OBLIGATION_CONSUMER_MODULE_TERMS = [
    "frontend",
    "ui",
    "service",
    "runtime",
    "domain",
    "persistence",
    "provider",
    "api",
    "observability",
    "event",
    "mock",
    "acceptance",
]
CONTRACT_OBLIGATION_LIST_SEPARATOR_RE = re.compile(
    r"(?:[,，;；]|\band\b|\bor\b|以及|和|与|、|/)",
    re.IGNORECASE,
)
CONTRACT_OBLIGATION_CONSUMER_SEPARATOR_RE = re.compile(
    r"(?:[,，;；]|\band\b|\bor\b|以及|和|与|、)",
    re.IGNORECASE,
)
CONTRACT_OBLIGATION_GENERIC_SPLIT_HINT_RE = re.compile(
    r"(?:split\s+by\s+provider\s+guarantee\s*,?\s+consumer\s+assumption\s*,?\s+failure/?timing\s*,?\s+and\s+verification\s+owner"
    r"|按\s*provider.*consumer.*failure.*verification\s*拆"
    r"|same\s+contract|same\s+module|related|视情况拆|后续拆分|由\s*task[- ]planning\s*决定)",
    re.IGNORECASE,
)
COARSE_CONTRACT_ID_RE = re.compile(r"^C-\d{3}$")
CONTRACT_SEMANTIC_TYPE_ALLOWLIST = {
    "wire/api shape",
    "frontend-backend",
    "state machine",
    "error/warning",
    "resource ownership",
    "managed resource ownership",
    "external side effect",
    "readback/observability",
    "progress/change producer",
    "ui action closure",
    "permission",
    "compatibility/migration",
    "acceptance/mock",
    "runtime materialization",
    "runtime-mode materialization parity",
    "observability",
    "db/migration",
}
CONTRACT_SEMANTIC_TYPE_DENY_RE = re.compile(
    r"\b(?:backend|frontend|service|module|implementation|impl|handler|controller|manager|task|domain|repository|dao|dto|vo|"
    r"mode[- ]?specific|misc|other|general|generic|相关|模块|实现|服务|前端|后端)\b",
    re.IGNORECASE,
)
REQUIRED_ATOMIC_DECOMPOSITION_SECTIONS = {
    "Contract Granularity Admission Matrix": [
        "Txxx",
        "Contract / matrix row",
        "Semantic type",
        "Required details copied into packet",
        "Missing detail",
        "Backflow target",
        "Admission",
    ],
    "Contract Edge Decomposition Matrix": [
        "Edge ID",
        "Source contract / row",
        "Sub-obligation",
        "From -> To",
        "Operation / surface",
        "Semantic type",
        "Canonical owner",
        "Owner module",
        "Consumer module(s)",
        "Provider guarantee to create/preserve",
        "Consumer assumption to use",
        "Failure / timing detail",
        "State/resource owner",
        "Verification proof",
        "Candidate task owner",
    ],
    "Provider Consumer Task Decision Matrix": [
        "Edge row",
        "Provider task needed?",
        "Provider task / existing task",
        "Consumer task needed?",
        "Consumer task / proof-only",
        "Reason",
        "Regression / acceptance proof",
    ],
    "Owner Legitimacy Matrix": [
        "Edge row",
        "Row kind",
        "Edge type",
        "Canonical owner",
        "Owner module",
        "Proposed provider task",
        "Proposed task primary module",
        "Owner legitimacy",
        "If not provider: carrier/proof edge",
        "Backflow if invalid",
    ],
    "Task Merge Split Decision Matrix": [
        "Candidate rows",
        "Proposed Txxx",
        "Owner legitimacy passed for all rows?",
        "Same primary module?",
        "Same semantic type?",
        "Same operation/surface?",
        "Same short verification?",
        "Decision",
        "Reason / backflow",
    ],
    "Provider Ownership Propagation Check": [
        "Txxx",
        "Task DAG provides/provides_obligations",
        "Packet provided_contract_obligations",
        "Compiled issue provider claims",
        "Carrier/proof refs moved to consumed/precondition/proof sections",
        "Result / backflow",
    ],
    "Proof Owner Allowlist Matrix": [
        "Verification row",
        "Owner Txxx",
        "Proof file/path",
        "Fixture/support file/path",
        "Source topology row",
        "Added to packet files_to_change?",
        "Added to task-dag files?",
        "Required freshness/build step",
        "Backflow if missing",
    ],
    "Semantic Load Split Matrix": [
        "Candidate Txxx",
        "Primary module count",
        "Touched layers",
        "Provider side-effect owners",
        "State/event/progress producers",
        "Readback/consumer owners",
        "Verification loops",
        "Cross-module build/test?",
        "Split required?",
        "Merge rationale / backflow",
    ],
}
REQUIRED_OBJECT_ACTION_CONSUMER_FILES = {
    "existing-object-action-consumer-graph.md": [
        "Graph ID",
        "Object/entity",
        "Action / mutation",
        "Entry point API/page/controller",
        "Existing variant/discriminator",
        "Producer chain",
        "State owner / storage",
        "Readback API / VO",
        "Consumer surface",
        "Hidden old-variant assumption",
        "Evidence",
    ],
    "variant-impact-matrix.md": [
        "Variant row",
        "New variant candidate",
        "Object/entity",
        "Existing action / mutation",
        "Existing variant(s)",
        "Shared entry/API/page",
        "Shared state/readback",
        "Detection evidence",
        "Variant decision",
    ],
}
PROGRESS_CHANGE_PRODUCER_COLUMNS = [
    "Chain ID",
    "Object/action",
    "Variant",
    "Mutation API / entrypoint",
    "Canonical change writer",
    "State owner / table",
    "Task/event producer",
    "Correlation key",
    "Write timing",
    "Last-change readback",
    "Change detail readback",
    "Frontend/mock consumer",
    "Terminal / polling rule",
    "Failure behavior",
    "Verification",
    "Owner issue",
]
EXTERNAL_SIDE_EFFECT_COLUMNS = [
    "Effect ID",
    "Source",
    "Operation/action",
    "External system",
    "Production side-effect owner",
    "Required production call/resource mutation",
    "Physical dependency allowed?",
    "No-cloud/playground substitute boundary",
    "Minimum acceptable proof",
    "Failure/partial failure semantics",
    "State/readback consumer",
    "Contract ID",
    "Verification ID",
    "Owner issue",
]
RUNTIME_TEST_TOPOLOGY_COLUMNS = [
    "Topology ID",
    "Behavior/contract",
    "Production path",
    "Proof module/package",
    "Proof file/path",
    "Fixture/support files",
    "Required build/install/freshness step",
    "Why this proof owner is necessary",
    "Staleness risk if skipped",
    "Verification command",
    "Expected result",
    "Owner issue",
]
RUNTIME_MATERIALIZATION_CLASSIFICATION_COLUMNS = [
    "Decision ID",
    "Source",
    "Existing mode(s)",
    "New / changed mode",
    "Classification",
    "Evidence",
    "Locked decision",
    "Owner stage",
]
RUNTIME_CAPABILITY_PARITY_COLUMNS = [
    "Capability ID",
    "Product capability",
    "Existing mode baseline",
    "New / changed mode obligation",
    "Supported?",
    "If not supported, product/API/UI expression",
    "Contract ID",
    "Verification ID",
    "Owner issue",
]
RUNTIME_MATERIALIZATION_MAPPING_COLUMNS = [
    "Mapping ID",
    "Mode",
    "Capability input",
    "Existing mode materialization evidence",
    "New / changed mode materialization design",
    "Production owner",
    "Required files/modules",
    "Failure semantics",
    "Verification",
    "Owner issue",
]
PROOF_OWNER_FILE_COLUMNS = [
    "Verification ID",
    "Owner issue",
    "Proof file/path",
    "Must be in task-dag files?",
    "Must be in packet files_to_change?",
    "Fixture/support file",
    "Reason",
    "Status",
]
PROGRESS_CHANGE_SIGNAL_RE = re.compile(
    r"\b(?:progress|last-change|last\s+change|change\s*tracking|changes/\{?changeId\}?|change\s+detail|task\s*step|"
    r"event\s*step|terminal\s*polling|polling\s*stop|InstanceChange|task_table|changeId)\b|"
    r"进度|变更追踪|任务步骤|事件步骤|终态轮询|轮询停止",
    re.IGNORECASE,
)
EXTERNAL_SIDE_EFFECT_SIGNAL_RE = re.compile(
    r"\b(?:external side effect|provider side effect|cloud-runtime|provider-managed|provider API|operator|"
    r"resource mutation|runtime scheduler|autoscaling policy|setCapacity|createOrUpdateAutoScalingPolicy|"
    r"AWS|ASG|K8s|Kubernetes|Terraform|Helm|IAM|RBAC|SDK|third-party|no-cloud|playground)\b|"
    r"外部副作用|云资源|真实.*(?:provider|operator|API|资源)|无云|验收替代|运行时调度|自动扩缩|物理依赖",
    re.IGNORECASE,
)
RUNTIME_TEST_TOPOLOGY_SIGNAL_RE = re.compile(
    r"\b(?:proof owner|runtime proof|build/install|freshness|SNAPSHOT|reactor|Maven|Gradle|module dependency|"
    r"cross[- ]module test|packaged playground|packaged playground image)\b|"
    r"证明文件|验证落点|构建拓扑|模块依赖|新鲜度|安装.*SNAPSHOT|跨模块测试",
    re.IGNORECASE,
)
RUNTIME_MATERIALIZATION_SIGNAL_RE = re.compile(
    r"\b(?:runtime[- ]mode[- ]materialization[- ]parity|runtime materialization|materialization parity|"
    r"deployment\s+mode|runtime\s+mode|execution environment|runner|provider backend|runtime substrate|"
    r"VM|AMI|container|orchestrator|bootstrap|entrypoint|userdata|systemd|init container|sidecar|"
    r"plugins?|extensions?|drivers?|secrets?|truststore|keystore|security config|product config|worker config|"
    r"runtime artifact)\b|"
    r"运行时.*(?:物化|模式|基线|等价|插件|配置|密钥|启动)|部署模式|执行环境|启动入口|产品配置|安全配置|能力基线|能力等价",
    re.IGNORECASE,
)
VARIANT_DECISION_SURFACE_RE = re.compile(
    r"\b(?:mode-consumer|runtime-lifecycle|post-create-consumer)\b|"
    r"\|\s*DS-\d{3}\s*\|[^|\n]*\|\s*(?:mode-consumer|runtime-lifecycle|post-create-consumer)\s*\|",
    re.IGNORECASE,
)
WEAK_PRODUCER_VALUE_RE = re.compile(
    r"\b(?:fixture|mock|frontend|ui|label|labels?|i18n|display|render|DOM|browser|mode-specific|"
    r"fixture-only|mock-only|frontend-only|event-only|log-only|DB-only|internal log|same as above)\b|"
    r"仅.*(?:fixture|mock|前端|文案|展示|日志)|只.*(?:fixture|mock|前端|文案|展示|日志)",
    re.IGNORECASE,
)
STRONG_PRODUCTION_VALUE_RE = re.compile(
    r"\b(?:writer|manager|service|repository|DAO|mapper|table|DB|database|task|factory|executor|"
    r"InstanceChange|task_table|instance_table|EventManager|changeId|clusterId|/last-change|/changes|"
    r"controller|API|readback|persist|state owner)\b|"
    r"写入|持久化|状态所有者|读回|表|任务|服务|仓储|同一",
    re.IGNORECASE,
)
PRODUCTION_FIELD_STRONG_RE = {
    "Canonical change writer": re.compile(
        r"\b(?:writer|manager|service|repository|DAO|mapper|InstanceChange|EventManager|controller|API|task|factory|executor)\b|"
        r"写入|服务|仓储|控制器|任务",
        re.IGNORECASE,
    ),
    "State owner / table": re.compile(
        r"\b(?:tables?|DB|database|repository|DAO|mapper|task_table|instance_table|state owner|storage)\b|"
        r"表|数据库|持久化|状态所有者|存储",
        re.IGNORECASE,
    ),
    "Task/event producer": re.compile(
        r"\b(?:task|factory|executor|InstanceChange|task_table|EventManager|event writer|step writer|manager|service)\b|"
        r"任务|事件|步骤|服务",
        re.IGNORECASE,
    ),
    "Correlation key": re.compile(
        r"\b(?:clusterId|objectId|changeId|same created id|same object id|id\s*->\s*id|->)\b|"
        r"同一.*id|关联键",
        re.IGNORECASE,
    ),
    "Last-change readback": re.compile(
        r"\b(?:/last-change|last-change|readback|controller|API|changeId|clusterId)\b|读回|同一.*id",
        re.IGNORECASE,
    ),
    "Change detail readback": re.compile(
        r"\b(?:/changes|change detail|changes/\{?changeId\}?|readback|controller|API|changeId)\b|变更详情|读回",
        re.IGNORECASE,
    ),
    "Verification": re.compile(
        r"\b(?:assert|verify|proof|test|api|integration|readback|same created id|same object id|clusterId|changeId|/last-change|/changes)\b|"
        r"验证|断言|同一.*id|读回",
        re.IGNORECASE,
    ),
    "Owner issue": re.compile(r"\bT\d{3}\b|owner|issue|任务", re.IGNORECASE),
}
SAME_ID_CHAIN_RE = re.compile(
    r"(?:clusterId|objectId|created id|same created id|same object id|同一(?:对象|集群|创建).*id).{0,120}"
    r"(?:changeId|last-change|/last-change|/changes|change detail|变更详情)"
    r"|(?:POST|PUT|PATCH|DELETE|create|update|delete|mutation|创建|更新|删除).{0,120}"
    r"(?:/last-change|last-change).{0,120}(?:/changes|changeId|change detail|变更详情)",
    re.IGNORECASE,
)
FRONTEND_TASK_RE = re.compile(
    r"\b(frontend|ui|browser|dom|page|component|form|wizard)\b|前端|页面|表单|组件|浏览器",
    re.IGNORECASE,
)
FRONTEND_REFERENCE_SIGNAL_RE = re.compile(
    r"\b(?:(?:reference|refer(?:red)? to) (?:UI|page|component|pattern|experience|implementation)|follow(?:ing)? existing|existing pattern|same (?:experience|layout|ui)|"
    r"like .*?(?:page|component|wizard|form|selector|table|card|experience)|visual parity|layout parity|component parity)\b"
    r"|参考|参照|借鉴|对齐.*(?:体验|页面|组件|布局)|一致.*(?:体验|页面|组件|布局)|像.*(?:页面|组件|体验)|创建体验",
    re.IGNORECASE,
)
FRONTEND_FILE_RE = re.compile(
    r"(^|/)(?:frontend|web|ui|src/)?(?:pages?|components?|routes|app)/|\.tsx?$|\.jsx?$",
    re.IGNORECASE,
)
FRONTEND_COMPONENT_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./:-])((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:tsx|jsx|ts|js))\b",
    re.IGNORECASE,
)
STRONG_FRONTEND_PROOF_RE = re.compile(
    r"\b(browser|playwright|DOM|click|submit|network|request|response|route|API|screenshot|trace|HAR)\b"
    r"|浏览器|点击|提交|网络|请求|响应|截图|路由|接口",
    re.IGNORECASE,
)
WEAK_FRONTEND_PROOF_RE = re.compile(r"\b(build|lint|typecheck|tsc|payload|compile)\b", re.IGNORECASE)
NOT_RUN_RE = re.compile(r"\bnot[_ -]?run|未运行|未执行|defer(?:red)?|后置|跳过\b", re.IGNORECASE)
BACKEND_FILE_RE = re.compile(
    r"(^|/)(?:backend|server|service|api|common|repository|runtime|src/main/java|src/test/java)/"
    r"|\.java\b|\.kt\b|\.scala\b|\.sql\b",
    re.IGNORECASE,
)
BACKEND_BROWSER_PROOF_RE = re.compile(
    r"\b(browser|playwright|DOM|click|screenshot|trace|HAR|render(?:ed)? selector|route/component)\b"
    r"|浏览器|点击|截图|渲染证明|页面证明",
    re.IGNORECASE,
)
BACKEND_TEST_PROOF_RE = re.compile(
    r"\b(?:surefire|failsafe|junit|mockito|assert|assertion|integration|IT|verify|expected|HTTP\s*[245]\d\d)\b"
    r"|(?:^|\s)-Dtest=|\btest\s*$|\bmvn\s+.*\btest\b"
    r"|单测|测试|断言|验证.*状态|验证.*错误|验证.*事件",
    re.IGNORECASE,
)
BACKEND_COMPILE_ONLY_RE = re.compile(
    r"\b(?:compile|build|mvn\s+.*(?:compile|package).*skipTests|skipTests|typecheck)\b",
    re.IGNORECASE,
)
BACKEND_BEHAVIOR_SIGNAL_RE = re.compile(
    r"\b(API|DTO|VO|DO|entity|service|manager|controller|repository|persistence|compatib|validation|"
    r"error|exception|warning|state|event|progress|lifecycle|runtime|task|executor|selector|capacity|workerSpec|autoscaling)\b"
    r"|接口|实体|持久化|兼容|校验|错误|告警|状态|事件|进度|生命周期|运行时|任务|选择器|容量|扩缩容",
    re.IGNORECASE,
)

AIP_TEMPLATE_HEADINGS: list[tuple[str, str]] = [
    ("AIP title", r"AIP（AutoMQ Improvement Proposal）模板|AIP\s*\(AutoMQ Improvement Proposal\)"),
    ("AIP 元信息", r"AIP 元信息"),
    ("评审记录", r"评审记录"),
    ("AIP 正文结构", r"AIP 正文结构"),
    ("1. 背景", r"1[.．、]\s*背景"),
    ("2. 问题定义", r"2[.．、]\s*问题定义"),
    ("3. 调研论证", r"3[.．、]\s*调研论证"),
    ("4. 解决方案", r"4[.．、]\s*解决方案"),
    ("5. 原型设计", r"5[.．、]\s*原型设计"),
    ("6. 接口设计", r"6[.．、]\s*接口设计"),
    ("7. 依赖选型", r"7[.．、]\s*依赖选型"),
    ("8. 方案详情", r"8[.．、]\s*方案详情"),
    ("9. 兼容性问题", r"9[.．、]\s*兼容性问题"),
    ("10. 被拒绝的其他方案", r"10[.．、]\s*被拒绝的其他方案"),
    ("11. 落地计划", r"11[.．、]\s*落地计划"),
    ("AIP 验收", r"AIP 验收"),
    ("发布验收", r"发布验收"),
    ("上线验收", r"上线验收"),
]


DENSE_RULES: list[dict[str, Any]] = [
    {
        "name": "asg-infra-selector",
        "description": "ASG infrastructure selector/default/auto-create/no-raw-text semantics",
        "required_groups": [
            ("VPC", [r"\bVPC\b"]),
            ("Subnet", [r"\bSubnet\b", r"\bsubnet\b"]),
            ("SecurityGroup", [r"\bSecurity\s*Group\b", r"\bSecurityGroup\b", r"\bSG\b"]),
            ("IAM", [r"\bIAM\b", r"\bRole\b", r"\bInstance\s*Profile\b"]),
            ("InstanceType", [r"\bInstance\s*Type\b", r"\bInstanceType\b"]),
            ("selector UI", [r"\bselector\b", r"\bselect\b", r"选择器", r"选择框"]),
            ("default/auto-create/existing/derived", [r"default", r"auto[- ]?create", r"existing", r"derived", r"默认", r"自动创建", r"已有", r"现有", r"派生"]),
            ("no raw text main path", [r"raw\s*(?:text|AWS|ID)", r"text\s*box", r"no\s+raw", r"forbid.*raw", r"禁止.*(?:文本|原始)", r"文本框"]),
        ],
        "verification_groups": [
            ("rendered selector proof", [r"\bbrowser\b", r"\bDOM\b", r"\brender", r"\bcomponent\b", r"\bpage\b", r"浏览器", r"渲染"]),
            ("selector behavior proof", [r"\bselector\b", r"\bselect\b", r"选择器", r"选择框"]),
            ("no raw text proof", [r"raw\s*(?:text|AWS|ID)", r"text\s*box", r"no\s+raw", r"禁止.*(?:文本|原始)", r"文本框"]),
        ],
    },
    {
        "name": "generic-selector",
        "description": "selector/default/auto-create/no-raw-text semantics",
        "required_groups": [
            ("selector UI", [r"\bselector\b", r"\bselect\b", r"选择器", r"选择框"]),
            ("default/auto-create/existing/derived", [r"default", r"auto[- ]?create", r"existing", r"derived", r"默认", r"自动创建", r"已有", r"现有", r"派生"]),
            ("options/state/error/reset", [r"option", r"empty", r"error", r"loading", r"reset", r"warning", r"候选", r"空", r"错误", r"加载", r"重置", r"告警"]),
        ],
        "verification_groups": [
            ("selector behavior proof", [r"\bselector\b", r"\bselect\b", r"选择器", r"选择框"]),
        ],
    },
    {
        "name": "managed-resource-ownership",
        "description": "managed/generated/auto-created/select-existing external resource ownership lifecycle semantics",
        "required_groups": [
            ("selection mode", [r"auto[- ]?create", r"default[- ]?created", r"generated", r"managed", r"select[- ]?existing", r"existing", r"自动创建", r"默认创建", r"生成", r"托管", r"选择已有", r"已有", r"现有"]),
            ("provider writer/create timing", [r"provider", r"API", r"operator", r"writer", r"create timing", r"创建时机", r"写入", r"调用"]),
            ("resource identity", [r"\bID\b", r"name", r"ARN", r"UID", r"tag", r"identity", r"标识", r"名称", r"标签"]),
            ("ownership provenance", [r"owned", r"existing", r"generated", r"derived", r"provenance", r"ownership", r"owner", r"归属", r"所有权", r"来源", r"已有", r"现有"]),
            ("persistence/readback consumer", [r"persist", r"state owner", r"readback", r"consumer", r"detail", r"list", r"runtime", r"持久", r"状态所有者", r"读回", r"消费者", r"详情", r"列表"]),
            ("cleanup/protect", [r"cleanup", r"delete", r"protect", r"detach", r"residual", r"清理", r"删除", r"保护", r"解绑", r"残留"]),
            ("idempotency/failure", [r"idempot", r"retry", r"failure", r"permission", r"quota", r"partial", r"幂等", r"重试", r"失败", r"权限", r"配额", r"部分"]),
        ],
        "verification_groups": [
            ("provider mutation proof", [r"provider", r"API", r"operator", r"create", r"delete", r"update", r"call", r"调用", r"创建", r"删除", r"更新"]),
            ("ownership readback proof", [r"owned", r"existing", r"provenance", r"readback", r"persist", r"query", r"归属", r"读回", r"持久", r"查询"]),
            ("cleanup/protect proof", [r"cleanup", r"protect", r"delete", r"detach", r"清理", r"保护", r"删除", r"解绑"]),
        ],
    },
    {
        "name": "explicit-failure-vs-unknown",
        "description": "explicit failure vs unknown/warning semantics",
        "required_groups": [
            ("explicit failure", [r"explicit", r"unreachable", r"明确", r"不可达"]),
            ("unknown/warning", [r"unknown", r"warning", r"未知", r"告警", r"警告"]),
            ("blocking distinction", [r"block", r"allow", r"non[- ]?blocking", r"阻断", r"允许", r"不阻断"]),
        ],
        "verification_groups": [
            ("failure branch proof", [r"explicit", r"unknown", r"warning", r"unreachable", r"不可达", r"未知", r"告警"]),
        ],
    },
    {
        "name": "frontend-action-flow",
        "description": "user action to route/API/feedback semantics",
        "required_groups": [
            ("user action", [r"\baction\b", r"\bsubmit\b", r"\bclick\b", r"操作", r"提交", r"点击"]),
            ("route/API", [r"\broute\b", r"\brouter\b", r"\bAPI\b", r"路由", r"接口"]),
            ("feedback/next state", [r"feedback", r"next state", r"toast", r"progress", r"error", r"跳转", r"反馈", r"下一状态", r"错误"]),
        ],
        "verification_groups": [
            ("action-flow proof", [r"\bbrowser\b", r"\bDOM\b", r"\bclick\b", r"\bsubmit\b", r"\broute\b", r"\bAPI\b", r"浏览器", r"点击", r"提交", r"路由", r"接口"]),
        ],
    },
    {
        "name": "stateful-behavior",
        "description": "lifecycle/progress/event/status/terminal/polling/retry state-machine semantics",
        "required_groups": [
            ("operation", [r"\boperation\b", r"\bcreate\b", r"\bupdate\b", r"\bdelete\b", r"\bresize\b", r"\bscale\b", r"操作", r"创建", r"更新", r"删除", r"扩缩"]),
            ("from/to state", [r"from state", r"to state", r"\bfrom\b.*\bto\b", r"状态", r"迁移", r"转换"]),
            ("event/step", [r"\bevent\b", r"\bstep\b", r"事件", r"步骤"]),
            ("status", [r"\bstatus\b", r"状态"]),
            ("terminal", [r"\bterminal\b", r"polling", r"stop", r"终态", r"轮询", r"停止"]),
            ("failure/reason", [r"\bfailure\b", r"\bfailed\b", r"\breason\b", r"失败", r"原因"]),
            ("producer/consumer", [r"producer", r"consumer", r"frontend", r"mock", r"API", r"生产", r"消费", r"前端"]),
            ("fixture/verification", [r"fixture", r"\bVER-\d{3}\b", r"verification", r"验证"]),
        ],
        "verification_groups": [
            ("state transition proof", [r"operation", r"transition", r"event", r"status", r"terminal", r"状态", r"事件", r"终态"]),
            ("terminal/failure proof", [r"terminal", r"polling", r"failure", r"reason", r"终态", r"轮询", r"失败", r"原因"]),
        ],
    },
]

DENSE_RULE_BY_NAME = {rule["name"]: rule for rule in DENSE_RULES}


def load_yaml(path: Path, required: bool = False) -> Any:
    if not path.exists():
        if required:
            raise ValueError(f"{path}: missing required YAML sidecar")
        return {}
    if yaml is None:
        raise ValueError("PyYAML is required for workflowctl structured validation")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc
    return data or {}


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def meaningful_list(value: Any, min_chars: int = 4) -> list[str]:
    items = [text(item) for item in as_list(value)]
    return [item for item in items if len(item) >= min_chars and not item.startswith("<")]


def nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {"todo", "tbd", "unknown", "待确认", "未知"}
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_component_actual_hash(root: Path, component: dict[str, Any]) -> str:
    paths_file = text(component.get("paths_file"))
    if paths_file:
        index_path = (root / paths_file).resolve()
        index = as_dict(load_yaml(index_path, required=True))
        resources = [text(item) for item in as_list(index.get("resources")) if text(item)]
        if not resources:
            raise ValueError(f"runtime resource index has no resources: {index_path}")
        payload: dict[str, str] = {}
        for rel in resources:
            resource = (root / rel).resolve()
            if not resource.is_file():
                raise ValueError(f"runtime resource is missing: {rel}")
            payload[rel] = sha256_file(resource)
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    rel = text(component.get("path"))
    path = root / rel
    if not rel or not path.is_file():
        raise ValueError(f"runtime component is missing: {rel or '<empty>'}")
    return sha256_file(path)


def stage_required_artifact_rels(change_dir: Path, stage: str) -> list[str]:
    rels = list(STAGE_RECEIPT_REQUIRED_ARTIFACTS.get(stage, []))
    defect_path = change_dir / "workflow-defects.yaml"
    if defect_path.is_file():
        defect_doc = as_dict(load_yaml(defect_path))
        caught_stages = [
            text(as_dict(raw).get("should_have_caught_stage"))
            for raw in as_dict(defect_doc.get("defects")).values()
            if text(as_dict(raw).get("should_have_caught_stage")) in ALL_STAGES
        ]
        earliest = min(caught_stages, key=ALL_STAGES.index, default="")
        if not earliest or (stage in ALL_STAGES and ALL_STAGES.index(stage) >= ALL_STAGES.index(earliest)):
            rels.append("workflow-defects.yaml")
    if stage in PLAN_SNAPSHOT_STAGES:
        rels.append(f"stage-snapshots/{stage}-plan.md")
    workflow_doc = as_dict(load_yaml(change_dir / "workflow-state.yaml"))
    if stage in STAGE_CONSTRUCTION_STAGES and stage_construction_enabled_doc(workflow_doc):
        rels.extend(
            [
                f"stage-construction/{stage}-obligations.yaml",
                f"stage-construction/{stage}-execution-pack.md",
            ]
        )
    return list(dict.fromkeys(rels))


def stage_artifact_paths(change_dir: Path, stage: str) -> list[Path]:
    paths: list[Path] = []
    rels = stage_required_artifact_rels(change_dir, stage) + list(OPTIONAL_RECEIPT_ARTIFACTS.get(stage, []))
    for rel in rels:
        path = change_dir / rel
        if path.exists():
            paths.append(path)
    return paths


def artifact_digest_map(change_dir: Path, stage: str) -> dict[str, str]:
    digests: dict[str, str] = {}
    for path in stage_artifact_paths(change_dir, stage):
        try:
            rel = path.relative_to(change_dir).as_posix()
        except ValueError:
            rel = path.as_posix()
        digests[rel] = (
            workflow_defects_stage_digest(path, stage)
            if rel == "workflow-defects.yaml"
            else artifact_receipt_digest(path, rel)
        )
    return digests


def workflow_defects_stage_digest(path: Path, stage: str) -> str:
    doc = as_dict(load_yaml(path))
    if stage not in ALL_STAGES:
        return sha256_file(path)
    stage_index = ALL_STAGES.index(stage)
    scoped = {
        defect_id: raw
        for defect_id, raw in as_dict(doc.get("defects")).items()
        if text(as_dict(raw).get("should_have_caught_stage")) in ALL_STAGES
        and ALL_STAGES.index(text(as_dict(raw).get("should_have_caught_stage"))) <= stage_index
    }
    payload = {"schema_version": doc.get("schema_version"), "defects": scoped}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def artifact_receipt_digest(path: Path, rel: str) -> str:
    if rel == WORKDIR_IDENTITY_ARTIFACT:
        body = path.read_text(encoding="utf-8", errors="replace")
        identity = re.split(r"^##+\s+Resume Verification\b", body, maxsplit=1, flags=re.MULTILINE)[0]
        return hashlib.sha256((identity.rstrip() + "\n").encode("utf-8")).hexdigest()
    return sha256_file(path)


def write_stage_plan_snapshot(change_dir: Path, stage: str) -> None:
    if stage not in PLAN_SNAPSHOT_STAGES:
        return
    plan_path = change_dir / "plan.md"
    if not plan_path.is_file():
        raise ValueError(f"{stage}: plan.md is required before pass-stage can freeze the stage plan snapshot")
    body = plan_path.read_text(encoding="utf-8", errors="replace")
    snapshot = (
        f"# {stage} Plan Snapshot\n\n"
        f"> Generated by `workflowctl.py pass-stage {stage}`. Immutable downstream input; "
        "reopen and re-pass the stage to replace it.\n\n"
        f"Source plan SHA-256: `{sha256_file(plan_path)}`\n\n"
        "---\n\n"
        f"{body}"
    )
    atomic_write_text(change_dir / "stage-snapshots" / f"{stage}-plan.md", snapshot)


def plan_append_only_errors(change_dir: Path, workflow_doc: dict[str, Any], stage: str) -> list[str]:
    if stage not in PLAN_SNAPSHOT_STAGES:
        return []
    statuses = as_dict(workflow_doc.get("stage_status"))
    prerequisites = set(effective_stage_prerequisites(workflow_doc, stage))
    upstream_stage = next(
        (
            candidate
            for candidate in reversed([text(item) for item in WORKFLOW_STATE_MACHINE.get("stage_order", [])])
            if candidate in prerequisites
            and candidate in PLAN_SNAPSHOT_STAGES
            and statuses.get(candidate) == "passed"
            and (change_dir / "stage-snapshots" / f"{candidate}-plan.md").is_file()
        ),
        "",
    )
    if not upstream_stage:
        return []
    plan_path = change_dir / "plan.md"
    if not plan_path.is_file():
        return [f"{stage}: plan.md is missing; start from the accepted {upstream_stage} plan snapshot"]
    snapshot_body = (change_dir / "stage-snapshots" / f"{upstream_stage}-plan.md").read_text(
        encoding="utf-8", errors="replace"
    )
    parts = re.split(r"^---\s*$", snapshot_body, maxsplit=1, flags=re.MULTILINE)
    accepted_plan = parts[1].lstrip("\n") if len(parts) == 2 else ""
    current_plan = plan_path.read_text(encoding="utf-8", errors="replace")
    if accepted_plan and not current_plan.startswith(accepted_plan):
        return [
            f"{stage}: plan.md rewrites accepted {upstream_stage} semantics; "
            f"restore stage-snapshots/{upstream_stage}-plan.md as the prefix or backflow/reopen {upstream_stage}"
        ]
    return []


def stable_json_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_receipt_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in receipt.items() if key != "receipt_hash"}


def canonical_receipt_hash(receipt: dict[str, Any]) -> str:
    return stable_json_digest(canonical_receipt_payload(receipt))


def canonical_audit_hash(audit: dict[str, Any]) -> str:
    return stable_json_digest({key: value for key, value in audit.items() if key != "audit_hash"})


def canonical_defect_promotion_hash(defect: dict[str, Any]) -> str:
    return stable_json_digest({key: value for key, value in defect.items() if key != "promotion_receipt_hash"})


def load_workflow_runtime_manifest() -> dict[str, Any]:
    manifest = as_dict(load_yaml(WORKFLOW_RUNTIME_MANIFEST_PATH, required=True))
    if manifest.get("schema_version") != 1:
        raise ValueError(f"{WORKFLOW_RUNTIME_MANIFEST_PATH}: schema_version must be 1")
    if text(manifest.get("protocol")) != STAGE_CONSTRUCTION_PROTOCOL:
        raise ValueError(f"{WORKFLOW_RUNTIME_MANIFEST_PATH}: protocol mismatch")
    return manifest


def workflow_profile(workflow_doc: dict[str, Any]) -> str:
    return text(as_dict(workflow_doc.get("workflow")).get("profile")) or "full"


def workflow_profile_policy(workflow_doc: dict[str, Any]) -> dict[str, Any]:
    try:
        manifest = load_workflow_runtime_manifest()
    except ValueError:
        return {}
    return as_dict(as_dict(manifest.get("profiles")).get(workflow_profile(workflow_doc)))


def runtime_component_hashes(manifest: dict[str, Any]) -> dict[str, str]:
    return {
        str(name): text(as_dict(component).get("sha256"))
        for name, component in as_dict(manifest.get("components")).items()
        if text(as_dict(component).get("sha256"))
    }


def effective_stage_prerequisites(workflow_doc: dict[str, Any], stage: str) -> list[str]:
    prerequisites = list(STAGE_PREREQUISITES.get(stage, []))
    if not stage_construction_enabled_doc(workflow_doc):
        return prerequisites
    required = {
        text(item)
        for item in as_list(workflow_profile_policy(workflow_doc).get("required_receipt_stages"))
        if text(item)
    }
    return [name for name in prerequisites if name in required or name in RUNTIME_PREREQUISITES]


def validate_workflow_runtime(workflow_doc: dict[str, Any]) -> list[str]:
    if not stage_construction_enabled_doc(workflow_doc):
        return []
    errors: list[str] = []
    try:
        manifest = load_workflow_runtime_manifest()
    except ValueError as exc:
        return [str(exc)]
    profile = workflow_profile(workflow_doc)
    if profile not in WORKFLOW_PROFILES or profile not in as_dict(manifest.get("profiles")):
        errors.append(f"workflow.profile={profile or '<empty>'} is unsupported")
    runtime = as_dict(as_dict(workflow_doc.get("workflow")).get("runtime"))
    current_manifest_hash = sha256_file(WORKFLOW_RUNTIME_MANIFEST_PATH)
    if text(runtime.get("version")) != text(manifest.get("runtime_version")):
        errors.append(
            "workflow.runtime.version does not match the installed runtime; run migrate-workflow-runtime explicitly"
        )
    if text(runtime.get("manifest_sha256")) != current_manifest_hash:
        errors.append(
            "workflow.runtime.manifest_sha256 does not match the installed runtime; run migrate-workflow-runtime explicitly"
        )
    if as_dict(runtime.get("component_hashes")) != runtime_component_hashes(manifest):
        errors.append(
            "workflow.runtime.component_hashes do not match the installed runtime; run migrate-workflow-runtime explicitly"
        )
    schema = workflow_doc.get("schema_version")
    compatibility = as_dict(manifest.get("compatibility"))
    if not isinstance(schema, int) or not (
        int(compatibility.get("workflow_schema_min", 0))
        <= schema
        <= int(compatibility.get("workflow_schema_max", 0))
    ):
        errors.append(f"workflow schema_version={schema!r} is outside runtime compatibility range")
    root = WORKFLOW_RUNTIME_MANIFEST_PATH.parent.parent
    for name, raw_component in as_dict(manifest.get("components")).items():
        component = as_dict(raw_component)
        try:
            actual_hash = runtime_component_actual_hash(root, component)
        except ValueError as exc:
            errors.append(f"runtime component {name}: {exc}")
            continue
        if text(component.get("sha256")) != actual_hash:
            errors.append(f"runtime component {name} digest mismatch; publish a new runtime manifest")
    return errors


def migrate_workflow_runtime(
    change_dir: Path,
    profile: str | None = None,
    from_stage: str | None = None,
) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl migrate-workflow-runtime", file=sys.stderr)
        return 2
    workflow_path = change_dir / "workflow-state.yaml"
    workflow_doc = as_dict(load_yaml(workflow_path, required=True))
    workflow_meta = as_dict(workflow_doc.get("workflow"))
    previous_profile = workflow_profile(workflow_doc)
    previous_runtime = as_dict(workflow_meta.get("runtime"))
    previous_components = as_dict(previous_runtime.get("component_hashes"))
    selected_profile = profile or workflow_profile(workflow_doc)
    manifest = load_workflow_runtime_manifest()
    if selected_profile not in as_dict(manifest.get("profiles")):
        print(f"ERROR: unsupported workflow profile {selected_profile}", file=sys.stderr)
        return 1
    workflow_doc["schema_version"] = 2
    workflow_meta["skill"] = "automq-ai-dev-workflow-contextpack"
    workflow_meta["profile"] = selected_profile
    workflow_meta["stage_construction_protocol"] = STAGE_CONSTRUCTION_PROTOCOL
    current_components = runtime_component_hashes(manifest)
    workflow_meta["runtime"] = {
        "version": text(manifest.get("runtime_version")),
        "manifest_sha256": sha256_file(WORKFLOW_RUNTIME_MANIFEST_PATH),
        "component_hashes": current_components,
    }
    workflow_doc["workflow"] = workflow_meta
    statuses = as_dict(workflow_doc.get("stage_status"))
    full_invalidation = not previous_components or previous_profile != selected_profile
    changed_components = sorted(
        set(previous_components) | set(current_components)
        if full_invalidation
        else {
            name
            for name in set(previous_components) | set(current_components)
            if text(previous_components.get(name)) != text(current_components.get(name))
        }
    )
    scoped_stage = text(from_stage)
    if scoped_stage:
        if full_invalidation or scoped_stage not in STAGE_CONSTRUCTION_STAGES:
            print("ERROR: --from-stage requires an existing component-pinned workflow and a construction stage", file=sys.stderr)
            return 1
        components = as_dict(manifest.get("components"))
        behavior_changes = [
            name
            for name in changed_components
            if as_dict(components.get(name)).get("behavior_affecting") is not False
        ]
        if set(behavior_changes) - {"stage_construction_contract"}:
            print(
                "ERROR: --from-stage is limited to a stage-construction-contract-only runtime change; "
                "changed behavior components: " + ", ".join(behavior_changes),
                file=sys.stderr,
            )
            return 1
        defect_path = change_dir / "workflow-defects.yaml"
        defect_doc = as_dict(load_yaml(defect_path)) if defect_path.exists() else {}
        relevant_defect_stages = [
            text(as_dict(raw).get("should_have_caught_stage"))
            for raw in as_dict(defect_doc.get("defects")).values()
            if text(as_dict(raw).get("status")).lower() == "open"
            and text(as_dict(raw).get("runtime_version_introduced")) == text(previous_runtime.get("version"))
            and text(as_dict(raw).get("should_have_caught_stage")) in STAGE_CONSTRUCTION_STAGES
        ]
        earliest_defect_stage = min(
            relevant_defect_stages,
            key=lambda item: ALL_STAGES.index(item),
            default="",
        )
        if scoped_stage != earliest_defect_stage:
            print(
                "ERROR: --from-stage must equal the earliest open late-defect should_have_caught_stage "
                f"introduced by the pinned runtime; expected={earliest_defect_stage or '<none>'}",
                file=sys.stderr,
            )
            return 1
        if behavior_changes != ["stage_construction_contract"]:
            print("ERROR: defect-scoped migration requires an actual stage_construction_contract hash change", file=sys.stderr)
            return 1
    invalidated: set[str] = set()
    if full_invalidation:
        invalidated.update(STAGE_CONSTRUCTION_STAGES | {"execution"})
    else:
        components = as_dict(manifest.get("components"))
        for name in changed_components:
            component = as_dict(components.get(name))
            if component.get("behavior_affecting") is False:
                continue
            if scoped_stage and name == "stage_construction_contract":
                invalidated.update(downstream_stage_closure(workflow_doc, scoped_stage))
                continue
            affected = [text(item) for item in as_list(component.get("affected_stages")) if text(item)]
            if not affected:
                invalidated.update(STAGE_CONSTRUCTION_STAGES | {"execution"})
                break
            for affected_stage in affected:
                invalidated.update(downstream_stage_closure(workflow_doc, affected_stage))

    stage_receipts = as_dict(workflow_doc.get("stage_receipts"))
    na_receipts = as_dict(workflow_doc.get("stage_na_receipts"))
    for stage_name in invalidated:
        if stage_name == "execution":
            statuses[stage_name] = "not_started"
        elif statuses.get(stage_name) not in {None, "", "not_started"}:
            statuses[stage_name] = "pending-rewrite"
        stage_receipts.pop(stage_name, None)
        na_receipts.pop(stage_name, None)
    workflow_doc["stage_status"] = statuses
    workflow_doc["stage_receipts"] = stage_receipts
    workflow_doc["stage_na_receipts"] = na_receipts
    if "execution" in invalidated:
        workflow_doc.pop("execution_receipt", None)
        workflow_doc["task_receipts"] = {}
    migrations = as_list(workflow_doc.get("runtime_migrations"))
    migration = {
        "from_version": text(previous_runtime.get("version")) or "legacy",
        "to_version": text(manifest.get("runtime_version")),
        "previous_manifest_hash": text(previous_runtime.get("manifest_sha256")),
        "current_manifest_hash": sha256_file(WORKFLOW_RUNTIME_MANIFEST_PATH),
        "profile": selected_profile,
        "changed_components": changed_components,
        "previous_component_hashes": {
            name: text(previous_components.get(name)) for name in changed_components
        },
        "current_component_hashes": {
            name: text(current_components.get(name)) for name in changed_components
        },
        "invalidated_stages": [stage for stage in ALL_STAGES if stage in invalidated],
        "full_invalidation": full_invalidation,
        "scoped_from_stage": scoped_stage,
        "migrated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    migration["audit_hash"] = canonical_audit_hash(migration)
    migrations.append(migration)
    workflow_doc["runtime_migrations"] = migrations
    write_yaml(workflow_path, workflow_doc)
    append_workflow_event(change_dir, "runtime_migrated", migration)
    print(
        f"Workflow migrated to {manifest.get('runtime_version')} profile={selected_profile}; "
        f"invalidated={', '.join(migration['invalidated_stages']) or '-'}"
    )
    return 0


def downstream_stage_closure(workflow_doc: dict[str, Any], stage: str) -> list[str]:
    invalidated = {stage}
    changed = True
    while changed:
        changed = False
        for candidate in STAGE_CONSTRUCTION_STAGES | {"execution"}:
            if candidate in invalidated:
                continue
            if invalidated.intersection(effective_stage_prerequisites(workflow_doc, candidate)):
                invalidated.add(candidate)
                changed = True
    return [name for name in ALL_STAGES if name in invalidated]


def reopen_stage(change_dir: Path, stage: str, backflow_id: str, reason: str) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl reopen-stage", file=sys.stderr)
        return 2
    if len(reason.strip()) < 12:
        print("ERROR: reopen-stage --reason must be concrete (at least 12 characters)", file=sys.stderr)
        return 1
    model = WorkflowModel(change_dir)
    trigger = as_dict(model.backflow_triggers.get(backflow_id))
    if not trigger:
        print(f"ERROR: {backflow_id}: missing backflow trigger; record it in backflow.yaml first", file=sys.stderr)
        return 1
    invalidates = as_dict(trigger.get("invalidates"))
    if not any(as_list(invalidates.get(key)) for key in ["artifacts", "decisions", "contracts", "verifications", "tasks"]):
        print(
            f"ERROR: {backflow_id}: backflow trigger has no declared invalidation; run backflow after recording concrete affected artifacts/objects",
            file=sys.stderr,
        )
        return 1
    runtime_errors = validate_workflow_runtime(model.workflow)
    if runtime_errors:
        for error in runtime_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    workflow_doc = model.workflow
    statuses = as_dict(workflow_doc.get("stage_status"))
    if stage not in STAGE_CONSTRUCTION_STAGES:
        print(f"ERROR: {stage}: stage cannot be reopened", file=sys.stderr)
        return 1
    if statuses.get(stage) not in {"passed", "not_applicable"}:
        print(
            f"ERROR: {stage}: reopen-stage requires passed/not_applicable status; actual={statuses.get(stage, 'missing')}",
            file=sys.stderr,
        )
        return 1
    invalidated = downstream_stage_closure(workflow_doc, stage)
    stage_receipts = as_dict(workflow_doc.get("stage_receipts"))
    na_receipts = as_dict(workflow_doc.get("stage_na_receipts"))
    removed_receipts: list[str] = []
    for name in invalidated:
        if name == stage or statuses.get(name) not in {None, "", "not_started"}:
            statuses[name] = "pending-rewrite"
        if name in stage_receipts or name in na_receipts:
            removed_receipts.append(name)
        stage_receipts.pop(name, None)
        na_receipts.pop(name, None)

    execution_reset = "execution" in invalidated and bool(
        statuses.get("execution") not in {None, "", "not_started"}
        or as_dict(workflow_doc.get("execution_receipt"))
        or as_dict(workflow_doc.get("task_receipts"))
    )
    if execution_reset:
        statuses["execution"] = "not_started"
        workflow_doc.pop("execution_receipt", None)
        workflow_doc["task_receipts"] = {}

    audit = {
        "stage": stage,
        "backflow_id": backflow_id,
        "reason": reason.strip(),
        "invalidated_stages": invalidated,
        "removed_receipts": sorted(set(removed_receipts)),
        "execution_reset": execution_reset,
        "reopened_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "command": f"python3 {Path(__file__).as_posix()} reopen-stage {stage} {change_dir.as_posix()} --backflow-id {backflow_id}",
    }
    audit["audit_hash"] = canonical_audit_hash(audit)
    reopens = as_list(workflow_doc.get("stage_reopens"))
    reopens.append(audit)
    workflow_doc["stage_reopens"] = reopens
    workflow_doc["stage_status"] = statuses
    workflow_doc["stage_receipts"] = stage_receipts
    workflow_doc["stage_na_receipts"] = na_receipts
    write_yaml(change_dir / "workflow-state.yaml", workflow_doc)
    append_workflow_event(change_dir, "stage_reopened", audit)
    print(f"Stage {stage} reopened; invalidated: {', '.join(invalidated)}")
    return 0


def validate_stage_reopens(model: WorkflowModel) -> list[str]:
    errors: list[str] = []
    for index, raw in enumerate(as_list(model.workflow.get("stage_reopens"))):
        audit = as_dict(raw)
        label = f"stage_reopens[{index}]"
        for field in [
            "stage", "backflow_id", "reason", "invalidated_stages", "removed_receipts",
            "execution_reset", "reopened_at", "command", "audit_hash",
        ]:
            if field == "execution_reset":
                if not isinstance(audit.get(field), bool):
                    errors.append(f"{label}.{field} must be boolean")
            elif field == "removed_receipts":
                if not isinstance(audit.get(field), list):
                    errors.append(f"{label}.{field} must be a list")
            elif not nonempty(audit.get(field)):
                errors.append(f"{label}.{field} is required")
        stage = text(audit.get("stage"))
        backflow_id = text(audit.get("backflow_id"))
        if stage not in STAGE_CONSTRUCTION_STAGES:
            errors.append(f"{label}.stage is invalid: {stage or '<empty>'}")
        if backflow_id not in model.backflow_triggers:
            errors.append(f"{label}.backflow_id does not reference backflow.yaml: {backflow_id or '<empty>'}")
        if "reopen-stage" not in text(audit.get("command")):
            errors.append(f"{label}.command must record workflowctl reopen-stage")
        if text(audit.get("audit_hash")) != canonical_audit_hash(audit):
            errors.append(f"{label}.audit_hash is forged or stale")
    return errors


def upstream_receipt_hashes_for_task_planning(workflow_doc: dict[str, Any]) -> dict[str, str]:
    return stage_upstream_receipt_hashes(workflow_doc, "task-planning")


def task_planning_reseal_or_regeneration_evidence(change_dir: Path) -> str:
    context = read_optional(change_dir / "atomic-planning-context-pack.md")
    if not context:
        return ""
    if re.search(r"^##+\s+Task Planning (?:Impact Proof|Regeneration Evidence)\b", context, re.MULTILINE):
        return "atomic-planning-context-pack.md"
    return ""


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    return text(value)


def read_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def markdown_table_values(markdown: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        key = cells[0]
        value = cells[1]
        if key and key.lower() not in {"item", "check"}:
            values[key.lower()] = value
    return values


def canonical_resolve(path_text: str) -> str:
    if not path_text:
        return ""
    try:
        return Path(path_text).expanduser().resolve().as_posix()
    except OSError:
        return Path(path_text).expanduser().absolute().as_posix()


def validate_workdir_identity(model: WorkflowModel) -> list[str]:
    errors: list[str] = []
    path = model.change_dir / WORKDIR_IDENTITY_ARTIFACT
    if not path.exists():
        errors.append(
            f"{WORKDIR_IDENTITY_ARTIFACT}: missing workdir identity anchor; "
            "create it before purpose.md/source-intake and do not resume from an unanchored cwd"
        )
        return errors

    body = read_optional(path)
    identity_body = re.split(r"^##+\s+Resume Verification\b", body, maxsplit=1, flags=re.MULTILINE)[0]
    values = markdown_table_values(identity_body)
    required = ["worktree path", "change dir absolute path", "change id", "branch name", "base commit", "git top level"]
    for key in required:
        if not text(values.get(key)):
            errors.append(f"{WORKDIR_IDENTITY_ARTIFACT}: Canonical Workdir missing {key}")

    actual_change_dir = canonical_resolve(model.change_dir.as_posix())
    recorded_change_dir = canonical_resolve(text(values.get("change dir absolute path")))
    if recorded_change_dir and recorded_change_dir != actual_change_dir:
        errors.append(
            f"{WORKDIR_IDENTITY_ARTIFACT}: change dir mismatch; expected {recorded_change_dir}, actual {actual_change_dir}. "
            "This is a resume/worktree identity error; do not create a new change-id"
        )

    actual_change_id = model.change_dir.name
    recorded_change_id = text(values.get("change id"))
    if recorded_change_id and recorded_change_id != actual_change_id:
        errors.append(f"{WORKDIR_IDENTITY_ARTIFACT}: change id mismatch; expected {recorded_change_id}, actual {actual_change_id}")

    repo_root = git_root_for(model.change_dir)
    actual_repo_root = canonical_resolve(repo_root.as_posix()) if repo_root else ""
    recorded_worktree = canonical_resolve(text(values.get("worktree path")))
    recorded_git_top = canonical_resolve(text(values.get("git top level")))
    for label, recorded in [("worktree path", recorded_worktree), ("git top level", recorded_git_top)]:
        if recorded and actual_repo_root and recorded != actual_repo_root:
            errors.append(f"{WORKDIR_IDENTITY_ARTIFACT}: {label} mismatch; expected {recorded}, actual {actual_repo_root}")

    actual_branch = command_output(["git", "-C", str(repo_root), "branch", "--show-current"]) if repo_root else ""
    recorded_branch = text(values.get("branch name"))
    if recorded_branch and actual_branch and recorded_branch != actual_branch:
        errors.append(f"{WORKDIR_IDENTITY_ARTIFACT}: branch mismatch; expected {recorded_branch}, actual {actual_branch}")

    recorded_base = text(values.get("base commit"))
    if repo_root and recorded_base:
        base_exists = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "-e", f"{recorded_base}^{{commit}}"],
            text=True,
            capture_output=True,
            check=False,
        )
        if base_exists.returncode != 0:
            errors.append(f"{WORKDIR_IDENTITY_ARTIFACT}: base commit does not exist in current worktree: {recorded_base}")
        else:
            ancestor = subprocess.run(
                ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", recorded_base, "HEAD"],
                text=True,
                capture_output=True,
                check=False,
            )
            if ancestor.returncode != 0:
                errors.append(
                    f"{WORKDIR_IDENTITY_ARTIFACT}: current HEAD does not descend from or equal base commit {recorded_base}"
                )

    workflow = as_dict(model.workflow.get("workflow"))
    for state_key, identity_key in [
        ("change_id", "change id"),
        ("change_dir_abs", "change dir absolute path"),
        ("worktree_path", "worktree path"),
        ("branch_name", "branch name"),
        ("base_commit", "base commit"),
    ]:
        state_value = text(workflow.get(state_key))
        identity_value = text(values.get(identity_key))
        if state_value and identity_value and state_key in {"change_dir_abs", "worktree_path"}:
            if canonical_resolve(state_value) != canonical_resolve(identity_value):
                errors.append(f"workflow-state.yaml workflow.{state_key} does not match {WORKDIR_IDENTITY_ARTIFACT} {identity_key}")
        elif state_value and identity_value and state_value != identity_value:
            errors.append(f"workflow-state.yaml workflow.{state_key} does not match {WORKDIR_IDENTITY_ARTIFACT} {identity_key}")

    resume_section_present = re.search(r"^##+\s+Resume Verification\b", body, re.MULTILINE)
    if not resume_section_present:
        errors.append(f"{WORKDIR_IDENTITY_ARTIFACT}: missing Resume Verification section")
    return errors


def validate_subagent_execution_proof(container: dict[str, Any], context: str, change_dir: Path) -> list[str]:
    errors: list[str] = []
    proof = as_dict(container.get("subagent_execution"))
    if not proof:
        return [
            f"{context}: missing subagent_execution; reviewer_type=readonly-subagent is only a schema label, "
            "record actual spawn_agent/wait_agent/final output evidence"
        ]

    required_text_fields = [
        "agent_id",
        "agent_type",
        "spawn_agent_evidence",
        "wait_agent_evidence",
        "final_message_digest",
        "reviewer_output_source",
    ]
    for field in required_text_fields:
        if not text(proof.get(field)):
            errors.append(f"{context}: subagent_execution.{field} is required")

    output_source = Path(text(proof.get("reviewer_output_source"))).expanduser()
    if not output_source.is_absolute():
        output_source = change_dir / output_source
    try:
        output_source.resolve().relative_to(change_dir.resolve())
    except ValueError:
        errors.append(f"{context}: reviewer_output_source must stay inside the active change directory")
    else:
        if not output_source.is_file():
            errors.append(f"{context}: reviewer_output_source does not exist: {output_source}")
        else:
            recorded_digest = text(proof.get("final_message_digest"))
            if not re.fullmatch(r"[0-9a-f]{64}", recorded_digest):
                errors.append(f"{context}: final_message_digest must be a lowercase SHA-256")
            elif recorded_digest != sha256_file(output_source):
                errors.append(f"{context}: final_message_digest does not match reviewer_output_source")

    final_status = text(proof.get("final_status")).lower()
    if final_status != "completed":
        errors.append(f"{context}: subagent_execution.final_status must be completed, got {proof.get('final_status')!r}")

    spawn_text = flatten_text(proof.get("spawn_agent_evidence"))
    wait_text = flatten_text(proof.get("wait_agent_evidence"))
    if not re.search(r"\bspawn_agent\b|已生成\s*\d+\s*个智能体|agent id|agent_id", spawn_text, re.IGNORECASE):
        errors.append(f"{context}: subagent_execution.spawn_agent_evidence must cite actual spawn_agent result")
    if not re.search(r"\bwait_agent\b|final status|completed|完成|final message", wait_text, re.IGNORECASE):
        errors.append(f"{context}: subagent_execution.wait_agent_evidence must cite actual wait_agent completion/final message")

    close_text = text(proof.get("close_agent_evidence"))
    if not close_text:
        errors.append(f"{context}: subagent_execution.close_agent_evidence is required; close completed reviewers or record explicit reused-live reason")
    elif not re.search(r"\bclose_agent\b|closed|关闭|reused-live|kept-live|复用", close_text, re.IGNORECASE):
        errors.append(f"{context}: subagent_execution.close_agent_evidence must cite close_agent result or explicit reused-live reason")

    forbidden = flatten_text(proof)
    if re.search(r"not actually started|未实际启动|schema only|只.*schema|main-local|主线程自审|deterministic|validator-only", forbidden, re.IGNORECASE):
        errors.append(f"{context}: subagent_execution admits no real readonly subagent review; gate must remain blocked")
    return errors


def scrub_carriers(value: dict[str, Any]) -> dict[str, Any]:
    scrubbed = dict(value)
    scrubbed.pop("semantic_carriers", None)
    return scrubbed


def matches_any(value: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, value, re.IGNORECASE) for pattern in patterns)


def design_object_ids(value: str) -> set[str]:
    decision_ids = {item for item in DESIGN_DECISION_ID_RE.findall(value) if not item.startswith("PDEC-")}
    return decision_ids | set(EXTERNAL_DESIGN_OBJECT_ID_RE.findall(value))


AIP_SECTION_PATTERNS: list[tuple[str, str]] = [
    ("1. 背景", r"1[.．、]\s*背景"),
    ("2. 问题定义", r"2[.．、]\s*问题定义"),
    ("3. 调研论证", r"3[.．、]\s*调研论证"),
    ("4. 解决方案", r"4[.．、]\s*解决方案"),
    ("5. 原型设计", r"5[.．、]\s*原型设计"),
    ("6. 接口设计", r"6[.．、]\s*接口设计"),
    ("7. 依赖选型", r"7[.．、]\s*依赖选型"),
    ("8. 方案详情", r"8[.．、]\s*方案详情"),
    ("9. 兼容性问题", r"9[.．、]\s*兼容性问题"),
    ("10. 被拒绝的其他方案", r"10[.．、]\s*被拒绝的其他方案"),
    ("11. 落地计划", r"11[.．、]\s*落地计划"),
]


def section_by_heading_pattern(markdown: str, heading_pattern: str) -> str:
    pattern = re.compile(rf"^(##+)\s*{heading_pattern}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        return ""
    start = match.end()
    level = match.group(1)
    next_match = re.search(rf"^{re.escape(level)}\s+", markdown[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(markdown)
    return markdown[start:end]


def aip_sections_for_reference(markdown: str, section_ref: str) -> str:
    if not section_ref.strip():
        return ""
    chunks: list[str] = []
    for label, pattern in AIP_SECTION_PATTERNS:
        label_number = label.split(".", 1)[0]
        label_name = label.split(" ", 1)[1]
        if label in section_ref or label_name in section_ref or re.search(rf"\b{re.escape(label_number)}\b", section_ref):
            found = section_by_heading_pattern(markdown, pattern)
            if found:
                chunks.append(found)
    return "\n".join(chunks)


def current_architecture_evidence_values(markdown: str) -> list[str]:
    evidence: list[str] = []
    for row in markdown_table_dicts(markdown):
        raw = table_get(row, "Evidence path / command", "Evidence", "Evidence path", "command")
        if not raw:
            continue
        if not re.search(r"(?:/|\\|\.java|\.ts|\.tsx|\.go|\.py|\.yaml|\.yml|\.tf|rg |grep |mvn |pnpm |npm |curl )", raw):
            continue
        evidence.append(raw.strip().strip("`"))
    return evidence


def materialization_contains_evidence(text_value: str, evidence: str) -> bool:
    if evidence in text_value:
        return True
    tokens = [
        token.strip("` ,;")
        for token in re.split(r"\s+", evidence)
        if re.search(r"(?:/|\\|\.java|\.ts|\.tsx|\.go|\.py|\.yaml|\.yml|\.tf)", token)
    ]
    return any(token and token in text_value for token in tokens)


def validate_ordered_heading_patterns(markdown: str, required: list[tuple[str, str]], artifact: str) -> list[str]:
    errors: list[str] = []
    cursor = -1
    for label, pattern in required:
        match = re.search(rf"^#+\s*{pattern}\s*$", markdown, re.IGNORECASE | re.MULTILINE)
        if not match:
            errors.append(f"{artifact}: missing AutoMQ AIP template heading: {label}")
            continue
        if match.start() < cursor:
            errors.append(f"{artifact}: AutoMQ AIP template heading out of order: {label}")
        cursor = max(cursor, match.start())
    return errors


def missing_dense_groups(value: str, groups: list[tuple[str, list[str]]]) -> list[str]:
    return [label for label, patterns in groups if not matches_any(value, patterns)]


def infer_dense_rules(value: Any) -> list[dict[str, Any]]:
    payload = flatten_text(value)
    if not payload:
        return []
    inferred: list[dict[str, Any]] = []
    asg_signal = matches_any(payload, [r"\bASG\b", r"\bAuto\s*Scaling\s*Group\b", r"\bEC2\b"])
    infra_signal = matches_any(
        payload,
        [
            r"infrastructure",
            r"\binfra\b",
            r"\bAWS\b",
            r"\bVPC\b",
            r"\bSubnet\b",
            r"\bSecurity\s*Group\b",
            r"\bSecurityGroup\b",
            r"\bSG\b",
            r"\bIAM\b",
            r"\bInstance\s*Type\b",
            r"\bInstanceType\b",
            r"基础设施",
            r"云资源",
        ],
    )
    selector_signal = matches_any(
        payload,
        [
            r"\bselector\b",
            r"\bselect\b",
            r"auto[- ]?create",
            r"existing",
            r"derived",
            r"default",
            r"raw\s*(?:text|AWS|ID)",
            r"text\s*box",
            r"选择器",
            r"选择框",
            r"自动创建",
            r"文本框",
        ],
    )
    managed_resource_signal = matches_any(
        payload,
        [
            r"auto[- ]?create",
            r"default[- ]?created",
            r"generated\s+resource",
            r"managed\s+resource",
            r"select[- ]?existing",
            r"existing\s+resource",
            r"自动创建",
            r"默认创建",
            r"生成资源",
            r"托管资源",
            r"选择已有",
            r"已有资源",
            r"现有资源",
        ],
    ) and matches_any(
        payload,
        [
            r"resource",
            r"provider",
            r"cloud",
            r"\bK8s\b",
            r"Kubernetes",
            r"\bIAM\b",
            r"\bRole\b",
            r"\bProfile\b",
            r"\bSecurity\s*Group\b",
            r"\bSG\b",
            r"\bBucket\b",
            r"\bDNS\b",
            r"\bVPC\b",
            r"\bSubnet\b",
            r"资源",
            r"云",
            r"外部",
            r"安全组",
            r"角色",
        ],
    ) and matches_any(
        payload,
        [
            r"provider[_ -]?writer",
            r"create[_ -]?timing",
            r"provenance",
            r"ownership",
            r"state owner",
            r"persist",
            r"readback",
            r"cleanup",
            r"protect",
            r"detach",
            r"idempot",
            r"writer",
            r"operator",
            r"owned\s+(?:resource|resources)",
            r"existing\s+(?:resource|resources)",
            r"写入",
            r"创建时机",
            r"归属",
            r"所有权",
            r"状态所有者",
            r"持久",
            r"读回",
            r"清理",
            r"保护",
            r"解绑",
            r"幂等",
        ],
    )
    if asg_signal and infra_signal and selector_signal:
        inferred.append(DENSE_RULE_BY_NAME["asg-infra-selector"])
    elif matches_any(payload, [r"\bselector\b", r"\bselect\b", r"选择器", r"选择框"]) and matches_any(
        payload,
        [
            r"auto[- ]?create",
            r"existing",
            r"derived",
            r"default",
            r"raw\s*(?:text|AWS|ID)",
            r"text\s*box",
            r"\boptions?\b",
            r"\bempty\b",
            r"\berror\b",
            r"\bloading\b",
            r"\breset\b",
            r"自动创建",
            r"已有",
            r"现有",
            r"派生",
            r"默认",
            r"文本框",
            r"候选",
            r"空",
            r"错误",
            r"加载",
            r"重置",
        ],
    ):
        inferred.append(DENSE_RULE_BY_NAME["generic-selector"])
    if managed_resource_signal:
        inferred.append(DENSE_RULE_BY_NAME["managed-resource-ownership"])

    if matches_any(payload, [r"explicit.*unknown", r"unknown.*explicit", r"unreachable.*unknown", r"unknown.*unreachable", r"明确.*未知", r"不可达.*未知"]):
        inferred.append(DENSE_RULE_BY_NAME["explicit-failure-vs-unknown"])
    if matches_any(payload, [r"\baction\b.*\b(route|API)\b", r"\b(route|API)\b.*\baction\b", r"操作.*(?:路由|接口)", r"(?:路由|接口).*操作"]):
        inferred.append(DENSE_RULE_BY_NAME["frontend-action-flow"])
    if matches_any(
        payload,
        [
            r"\b(lifecycle|progress|event|events|terminal|polling|retry|state\s*graph|state\s*machine|task\s*step|change\s*tracking|step\s*graph)\b",
            r"生命周期|进度|事件|状态机|状态图|终态|轮询|重试|任务步骤|变更追踪|状态推进",
        ],
    ):
        inferred.append(DENSE_RULE_BY_NAME["stateful-behavior"])
    return inferred


def dense_carrier_payload(value: Any) -> str:
    parts: list[Any] = []
    for item in as_list(value):
        if isinstance(item, dict):
            row = as_dict(item)
            parts.append(row.get("carrier"))
            parts.append(row.get("must_preserve"))
            parts.append(row.get("omission_failure"))
        else:
            parts.append(item)
    return flatten_text(parts)


def salient_terms(value: str) -> list[str]:
    raw_terms = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u3400-\u9fff]{2,}", value)
    stop = {
        "must",
        "should",
        "with",
        "without",
        "normal",
        "path",
        "field",
        "fields",
        "display",
        "create",
        "page",
        "mode",
    }
    terms: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        lower = term.lower()
        if lower in stop or lower in seen:
            continue
        seen.add(lower)
        terms.append(term)
    return terms


def semantic_payload_copied(payload: str, target_text: str) -> bool:
    if payload in target_text:
        return True
    terms = salient_terms(payload)
    if not terms:
        return False
    hits = sum(1 for term in terms if re.search(re.escape(term), target_text, re.IGNORECASE))
    required = min(len(terms), max(4, int(len(terms) * 0.65)))
    return hits >= required


def semantic_carrier_texts(value: Any) -> list[str]:
    texts: list[str] = []
    for item in as_list(value):
        if isinstance(item, dict):
            row = as_dict(item)
            row_texts: list[str] = []
            for candidate in as_list(row.get("must_preserve")):
                candidate_text = text(candidate)
                if candidate_text:
                    row_texts.append(candidate_text)
            if not row_texts:
                carrier_text = text(row.get("carrier"))
                if carrier_text:
                    row_texts.append(carrier_text)
            texts.extend(row_texts)
        else:
            item_text = text(item)
            if item_text:
                texts.append(item_text)
    return texts


def validate_task_semantic_carriers(task_id: str, task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for idx, carrier in enumerate(as_list(task.get("semantic_carriers")), start=1):
        if isinstance(carrier, str) and SCP_ID_RE.fullmatch(carrier.strip()):
            continue
        errors.extend(validate_sidecar_semantic_carriers(task_id, {"semantic_carriers": [carrier]}))
    return errors


def carrier_row_source(row: dict[str, Any]) -> str:
    return text(row.get("source") or row.get("global_source") or row.get("source_id"))


def carrier_row_projection_id(row: dict[str, Any]) -> str:
    return text(row.get("projection_id") or row.get("slice_id") or row.get("carrier_projection_id"))


def semantic_projection_rows_for_source(model: "WorkflowModel", source_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in as_list(model.semantic_carrier_projections.get(source_id)):
        row = as_dict(raw)
        if row:
            row.setdefault("source", source_id)
            rows.append(row)
    source_obj = as_dict(model.requirements.get(source_id)) or as_dict(model.scenarios.get(source_id))
    for raw in as_list(source_obj.get("semantic_carrier_projections")):
        row = as_dict(raw)
        if row:
            row.setdefault("source", source_id)
            rows.append(row)
    return rows


def projection_owner_tasks(row: dict[str, Any]) -> set[str]:
    owners: set[str] = set()
    for key in ["owner_task", "owner_tasks", "task", "tasks", "candidate_txxx", "target_task"]:
        for item in as_list(row.get(key)):
            value = text(item)
            if TASK_RE.match(value):
                owners.add(value)
    return owners


def projection_owner_module(row: dict[str, Any]) -> str:
    return text(row.get("owner_module") or row.get("canonical_owner_module") or row.get("module_owner"))


def projection_payload_text(row: dict[str, Any]) -> str:
    payload_parts = [
        row.get("carrier"),
        row.get("slice"),
        row.get("owner_semantics"),
        row.get("execution_obligation"),
        row.get("must_preserve"),
        row.get("required_details"),
        row.get("verification"),
    ]
    return flatten_text(payload_parts)


def projection_payload_texts(row: dict[str, Any]) -> list[str]:
    items = [text(item) for item in as_list(row.get("must_preserve")) if text(item)]
    if items:
        return items
    payload = projection_payload_text(row)
    return [payload] if payload else []


def projection_applies_to_task(row: dict[str, Any], task_id: str, task: dict[str, Any]) -> bool:
    owners = projection_owner_tasks(row)
    if owners:
        return task_id in owners
    owner_module = projection_owner_module(row)
    task_module = text(task.get("primary_module"))
    return bool(owner_module and task_module and owner_modules_compatible(owner_module, task_module))


def source_has_dense_or_required_carriers(source_obj: dict[str, Any]) -> bool:
    return bool(infer_dense_rules(scrub_carriers(source_obj)) or as_list(source_obj.get("semantic_carriers")))


def validate_semantic_carrier_projections(model: "WorkflowModel", stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"task-planning", "pre-execution", "acceptance", "all"}:
        return errors
    for source_id, source_obj_raw in {**model.requirements, **model.scenarios}.items():
        source_obj = as_dict(source_obj_raw)
        if not source_has_dense_or_required_carriers(source_obj):
            continue
        projections = semantic_projection_rows_for_source(model, source_id)
        if not projections:
            errors.append(
                f"{source_id}: dense REQ/SCN semantics require semantic_carrier_projections before task packets; "
                "do not force every task that references the source to copy the full global carrier"
            )
            continue
        source_consumed_tasks = {item for item in map(str, as_list(source_obj.get("consumed_by"))) if TASK_RE.match(item)}
        projection_owner_modules = {projection_owner_module(as_dict(row)) for row in projections if projection_owner_module(as_dict(row))}
        multi_owner_source = len(projection_owner_modules) > 1 or len(source_consumed_tasks) > 1
        projected_tasks: set[str] = set()
        for idx, row in enumerate(projections, start=1):
            projection_id = carrier_row_projection_id(row) or text(row.get("projection_id"))
            if not projection_id:
                errors.append(f"{source_id}: semantic_carrier_projections[{idx}] missing projection_id")
            elif not SCP_ID_RE.match(projection_id):
                errors.append(
                    f"{source_id}: semantic_carrier_projections[{idx}] projection_id must look like SCP-001 or SCP-001-T002, got {projection_id!r}"
                )
            if carrier_row_source(row) and carrier_row_source(row) != source_id:
                errors.append(f"{source_id}: semantic_carrier_projections[{idx}] source mismatch: {carrier_row_source(row)}")
            owner_module = projection_owner_module(row)
            if not owner_module:
                errors.append(f"{source_id}: semantic_carrier_projections[{idx}] missing owner_module")
            owners = projection_owner_tasks(row)
            if not owners:
                errors.append(f"{source_id}: semantic_carrier_projections[{idx}] missing owner_task")
            for owner in sorted(owners):
                projected_tasks.add(owner)
                if owner not in model.tasks:
                    errors.append(f"{source_id}: semantic_carrier_projections[{idx}] owner_task {owner} is missing from task-dag.yaml")
                    continue
                task_module = task_primary_module(model, owner)
                if owner_module and task_module and not owner_modules_compatible(owner_module, task_module):
                    errors.append(
                        f"{source_id}: semantic_carrier_projections[{idx}] owner_task {owner} primary_module {task_module} "
                        f"does not match owner_module {owner_module}"
                    )
            for field in ["operation_surface", "semantic_type"]:
                if not nonempty(row.get(field)):
                    errors.append(f"{source_id}: semantic_carrier_projections[{idx}] missing {field}")
            payloads = projection_payload_texts(row)
            if not payloads:
                errors.append(f"{source_id}: semantic_carrier_projections[{idx}] missing concrete must_preserve/owner_semantics")
            for payload in payloads:
                if len(payload) < 24 or is_label_only_carrier(payload):
                    errors.append(
                        f"{source_id}: semantic_carrier_projections[{idx}] payload is too thin; "
                        "write the owner-specific fields/resources/states/errors/proof, not a label"
                    )
                if is_generic_packet_text(payload):
                    errors.append(
                        f"{source_id}: semantic_carrier_projections[{idx}] payload is generic placeholder text"
                    )
            excluded = flatten_text(row.get("excluded_owner_semantics") or row.get("does_not_carry") or row.get("not_owner_semantics"))
            if multi_owner_source and not excluded:
                errors.append(
                    f"{source_id}: semantic_carrier_projections[{idx}] must declare excluded_owner_semantics/does_not_carry "
                    "so non-owner semantics are not pushed into this task packet"
                )
        missing_projected = source_consumed_tasks - projected_tasks
        if missing_projected:
            errors.append(
                f"{source_id}: consumed_by tasks {', '.join(sorted(missing_projected))} lack owner-specific semantic_carrier_projection rows"
            )
    return errors


def is_label_only_carrier(value: str) -> bool:
    value = value.strip()
    if not value:
        return True
    if LABEL_ONLY_CARRIER_RE.fullmatch(value):
        return True
    if len(value) < 24 and not re.search(r"\s|[\u3400-\u9fff]|[,.;:，。；：/()（）]", value):
        return True
    return False


def is_generic_packet_text(value: Any) -> bool:
    return bool(GENERIC_PACKET_TEXT_RE.search(text(value)))


def locked_na(value: str) -> bool:
    return bool(re.fullmatch(r"(?:N/A|not applicable|不适用|locked N/A|locked-na|locked not applicable)", text(value), re.IGNORECASE))


def contract_ids_from_text(markdown: str) -> set[str]:
    return set(re.findall(r"\bC-\d{3}\b", markdown))


def executable_obligation_row_too_thin(row: dict[str, str]) -> bool:
    joined = flatten_text(row)
    if not joined or is_generic_packet_text(joined):
        return True
    payload_fields = [
        table_get(row, "Edge"),
        table_get(row, "Sub-obligation type"),
        table_get(row, "Semantic type"),
        table_get(row, "Operation / surface"),
        table_get(row, "Canonical owner"),
        table_get(row, "Fields/resource/state"),
        table_get(row, "Provider guarantee"),
        table_get(row, "Consumer assumption"),
        table_get(row, "Failure / timing detail"),
        table_get(row, "State/resource owner"),
        table_get(row, "Suggested owner module"),
        table_get(row, "Verification proof"),
        table_get(row, "Split hint"),
    ]
    concrete = [
        field for field in payload_fields
        if field and not locked_na(field) and not re.fullmatch(r"(?:none|no|无|same as above|同上|-)", field.strip(), re.IGNORECASE)
    ]
    if len(concrete) < 5:
        return True
    if len(re.findall(r"[\u3400-\u9fff]", joined)) < 20 and len(re.findall(r"[A-Za-z][A-Za-z0-9_.:/-]{3,}", joined)) < 10:
        return True
    return False


def obligation_term_hits(value: str, terms: list[str]) -> list[str]:
    normalized = value.lower()
    hits: list[str] = []
    for term in terms:
        pattern = r"(?<![a-z0-9])" + re.escape(term.lower()).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
        if re.search(pattern, normalized):
            hits.append(term)
    return hits


def obligation_field_has_unresolved_list(value: str, terms: list[str]) -> bool:
    if not value or locked_na(value):
        return False
    hits = obligation_term_hits(value, terms)
    if len(set(hits)) < 2:
        return False
    return bool(CONTRACT_OBLIGATION_LIST_SEPARATOR_RE.search(value))


def split_explicit_list_parts(value: str, separator: re.Pattern[str] = CONTRACT_OBLIGATION_LIST_SEPARATOR_RE) -> list[str]:
    return [
        part.strip()
        for part in separator.split(value or "")
        if part.strip()
    ]


def field_has_multiple_explicit_terms(
    value: str,
    terms: list[str],
    separator: re.Pattern[str] = CONTRACT_OBLIGATION_LIST_SEPARATOR_RE,
) -> bool:
    if not value or locked_na(value):
        return False
    parts = split_explicit_list_parts(value, separator)
    if len(parts) < 2:
        return False
    matched_parts = 0
    for part in parts:
        if obligation_term_hits(part, terms):
            matched_parts += 1
    return matched_parts >= 2


def contract_semantic_type_errors(value: str) -> list[str]:
    value = text(value).strip()
    if not value or locked_na(value):
        return ["Semantic type must be explicit; use a known contract semantic type or custom:<name>"]
    parts = split_explicit_list_parts(value)
    if not parts:
        parts = [value]
    errors: list[str] = []
    for part in parts:
        normalized = re.sub(r"\s+", " ", part.strip().lower())
        if normalized.startswith("custom:"):
            custom_name = normalized.split(":", 1)[1].strip()
            if len(custom_name) < 3 or CONTRACT_SEMANTIC_TYPE_DENY_RE.search(custom_name):
                errors.append(f"custom semantic type '{part}' must name a real semantic shape, not a layer/module/implementation")
            continue
        if normalized in CONTRACT_SEMANTIC_TYPE_ALLOWLIST:
            continue
        if CONTRACT_SEMANTIC_TYPE_DENY_RE.search(normalized):
            errors.append(f"semantic type '{part}' is a layer/module/implementation label, not a contract semantic type")
        else:
            errors.append(f"semantic type '{part}' is not in the known set; use custom:<name> for a new locked type")
    return errors


def specialized_contract_row_ids(change_dir: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    matrix_specs = [
        ("external-side-effect-contract-matrix.md", "External Side Effect Contract Matrix", "Effect ID"),
        ("progress-change-producer-chain-matrix.md", "Progress / Change Producer Chain Matrix", "Chain ID"),
    ]
    for rel, section_name, id_column in matrix_specs:
        body = read_optional(change_dir / rel)
        if not body.strip():
            continue
        for row in markdown_table_dicts(section(body, section_name)):
            if obligation_row_locked_na(row):
                continue
            row_id = table_get(row, id_column)
            if row_id:
                rows.append((rel, row_id))
    return rows


def validate_specialized_rows_in_contract_obligations(change_dir: Path, executable_text: str) -> list[str]:
    errors: list[str] = []
    for rel, row_id in specialized_contract_row_ids(change_dir):
        if not re.search(rf"\b{re.escape(row_id)}\b", executable_text):
            errors.append(
                f"contract: Contract Executable Obligation Matrix must consume {rel} row {row_id}"
            )
    return errors


def obligation_row_locked_na(row: dict[str, str]) -> bool:
    if locked_na(flatten_text(row)):
        return True
    for label in [
        "Status",
        "Admission",
        "Decision",
        "Disposition",
        "Owner issue",
        "Owner task",
        "Owner issue / proof-only",
        "Split hint",
    ]:
        value = table_get(row, label)
        if value and re.fullmatch(r"(?:N/A|not applicable|不适用|locked N/A|locked-na|locked not applicable)", value.strip(), re.IGNORECASE):
            return True
    return False


HIGH_RISK_OBLIGATION_RE = re.compile(
    r"\b(?:external|side[- ]?effect|runtime|materialization|parity|managed|ownership|cleanup|protect|"
    r"hpa|autoscaling|auto[- ]?scaling|scaling policy|policy|progress|change|event|failure|residual|partial)\b"
    r"|外部|副作用|运行时|物化|等价|托管|资源所有权|清理|保护|自动扩缩|伸缩策略|进度|事件|失败|残留|部分失败",
    re.IGNORECASE,
)
PROVIDER_OWNED_EDGE_TYPE_RE = re.compile(r"^semantic[_ -]?contract[_ -]?edge$", re.IGNORECASE)
CARRIER_EDGE_TYPE_RE = re.compile(
    r"^(?:carrier[_ -]?order[_ -]?edge|verification[_ -]?prerequisite[_ -]?edge|proof[_ -]?only[_ -]?edge)$",
    re.IGNORECASE,
)
CONTRACT_EDGE_TYPE_CANONICAL_VALUES = {
    "semantic_contract_edge",
    "carrier_order_edge",
    "verification_prerequisite_edge",
    "proof_only_edge",
}
CONTRACT_PROVIDER_MODULE_MULTI_OWNER_RE = re.compile(
    r"(?:\s*/\s*|[,，;；、]|\s+\+\s+|\s*&\s*|\band\b|\bor\b|以及|和|与|及|或)",
    re.IGNORECASE,
)
PROVIDER_ROW_KIND_RE = re.compile(r"provider\s+guarantee|提供方|provider", re.IGNORECASE)
NON_PROVIDER_ROW_KIND_RE = re.compile(
    r"consumer\s+assumption|verification\s+proof|carrier[- ]?only|proof[- ]?only|locked\s+N/A|failure/timing|消费方|证明",
    re.IGNORECASE,
)
OWNER_VALID_RE = re.compile(r"\b(?:valid-owner|valid|passed|yes|true|是|合法|owner-valid)\b", re.IGNORECASE)
OWNER_NON_PROVIDER_RE = re.compile(r"\b(?:carrier-only|proof-only|locked N/A|locked-na|not applicable|N/A|不适用)\b", re.IGNORECASE)
OWNER_INVALID_RE = re.compile(r"\b(?:invalid|invalid-backflow|backflow|blocked|mismatch|不合法|回流|阻塞)\b", re.IGNORECASE)
CONTRACT_PROVIDER_EDGE_ALIAS_RE = re.compile(
    r"^(?:provides[-_ ]?contract|producer[-_ ]?consumer|runtime[-_ ]?materialization[-_ ]?provider[-_ ]?consumer)$",
    re.IGNORECASE,
)
CARRIER_ORDER_LANGUAGE_RE = re.compile(
    r"\b(?:carrier|request\s+carrier|DTO|wire|shape|schema|API\s+shape|payload|route|handler|prerequisite|fixture|harness|freshness|"
    r"acceptance[-_ ]prerequisite|packaged[-_ ]browser[-_ ]prerequisite|selector\s+request)\b|"
    r"载体|前提|请求体|接口形状|验证前提|验收前提",
    re.IGNORECASE,
)
OBLIGATION_ROW_ID_RE = re.compile(
    r"\b(?:C-\d{3}-OBL-\d{3}|ESE-\d{3}|PCP?-\d{3}|RMM-\d{3}|RMP-\d{3}|VIM-\d{3}|UI-ACT-\d{3})\b"
)
CONTRACT_OR_OBLIGATION_ID_RE = re.compile(r"\bC-\d{3}(?:-OBL-\d{3})?\b")
CONTRACT_OBLIGATION_ID_RE = re.compile(r"^C-\d{3}-OBL-\d{3}$")
PROVIDER_CLAIM_LANGUAGE_RE = re.compile(
    r"\b(?:owns?|owned|owner|provides?|provided|provider\s+task|provider\s+owner|guarantees?|guaranteed|"
    r"implements?|implemented|preserves?|primary\s+closure|provided\s+contracts?|"
    r"provided\s+contract\s+closure|must\s+guarantee|obligations?\s+are\s+implemented)\b"
    r"|拥有|归属|提供|保证|实现|闭包|契约义务",
    re.IGNORECASE,
)
NON_PROVIDER_CLAIM_LANGUAGE_RE = re.compile(
    r"\b(?:consumes?|consumed|consumer|assumes?|may\s+assume|precondition|carrier|"
    r"proof[-_ ]?only|proof|prerequisite|not\s+provide|does\s+not\s+provide|"
    r"do\s+not\s+provide|cannot\s+provide|not\s+owned|not\s+owner|remains?|"
    r"belongs\s+to|downstream|upstream|external\s+consumed|N/A)\b"
    r"|消费|前提|载体|证明|不提供|不拥有|不是|不得|不能|归属.*T\d{3}",
    re.IGNORECASE,
)


def obligation_ids_from_cell(value: str) -> list[str]:
    found = OBLIGATION_ROW_ID_RE.findall(value)
    if found:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in found:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered
    cleaned = str(value or "").strip()
    if cleaned and not locked_na(cleaned):
        return [cleaned]
    return []


def canonical_provider_ref(value: str) -> bool:
    raw = text(value)
    if not raw or locked_na(raw):
        return False
    return bool(CONTRACT_RE.fullmatch(raw) or OBLIGATION_ROW_ID_RE.fullmatch(raw))


def contract_base_id(value: str) -> str:
    raw = text(value)
    if CONTRACT_RE.fullmatch(raw):
        return raw
    match = re.match(r"^(C-\d{3})-OBL-\d{3}$", raw)
    return match.group(1) if match else ""


def contract_or_obligation_refs(value: Any) -> set[str]:
    return set(CONTRACT_OR_OBLIGATION_ID_RE.findall(flatten_text(value)))


def provider_claim_refs(value: Any) -> set[str]:
    claims: set[str] = set()
    raw = flatten_text(value)
    for chunk in re.split(r"(?:\n|<br\s*/?>|[.;。；])", raw, flags=re.IGNORECASE):
        if not CONTRACT_OR_OBLIGATION_ID_RE.search(chunk):
            continue
        if PROVIDER_CLAIM_LANGUAGE_RE.search(chunk) and not NON_PROVIDER_CLAIM_LANGUAGE_RE.search(chunk):
            claims.update(CONTRACT_OR_OBLIGATION_ID_RE.findall(chunk))
    return claims


def provider_ref_allowed(ref: str, allowed_refs: set[str]) -> bool:
    return ref in allowed_refs


def normalize_contract_edge_type(value: str) -> str:
    return re.sub(r"[\s-]+", "_", text(value).strip().lower())


def is_contract_edge_type_value(value: str) -> bool:
    return normalize_contract_edge_type(value) in CONTRACT_EDGE_TYPE_CANONICAL_VALUES


def contract_provider_module_is_multi_owner(value: str) -> bool:
    cleaned = text(value)
    if not cleaned or locked_na(cleaned):
        return False
    return bool(CONTRACT_PROVIDER_MODULE_MULTI_OWNER_RE.search(cleaned))


def executable_obligation_column_drift_errors(row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    sub_id = table_get(row, "Sub-obligation ID") or table_get(row, "Contract") or "<row>"
    for label in [
        "Sub-obligation type",
        "Semantic type",
        "Operation / surface",
        "Canonical owner",
        "Owner module",
        "Suggested owner module",
    ]:
        value = table_get(row, label)
        if value and is_contract_edge_type_value(value):
            errors.append(
                f"{sub_id}: {label} contains edge_type value {value}; "
                "the Contract Executable Obligation Matrix row is column-shifted or copied into the wrong field"
            )
    return errors


MODULE_ID_RE = re.compile(r"^MOD-[A-Z0-9][A-Z0-9_-]*$")


def contract_row_owner_module(row: dict[str, str]) -> str:
    return (
        table_get(row, "Owner module")
        or table_get(row, "Suggested owner module")
        or table_get(row, "owner_module")
        or table_get(row, "canonical_owner_module")
    )


def owner_module_format_errors(row: dict[str, str]) -> list[str]:
    owner_module = contract_row_owner_module(row)
    if not owner_module or locked_na(owner_module):
        return []
    if MODULE_ID_RE.fullmatch(owner_module):
        return []
    sub_id = table_get(row, "Sub-obligation ID") or table_get(row, "Contract") or "<row>"
    return [
        f"{sub_id}: Owner module must be a concrete MOD-* module, got {owner_module}; "
        "do not put VER-*, Txxx, verification names, or semantic owner roles in the module field"
    ]


def obligation_id_is_coarse_contract(value: str) -> bool:
    return bool(COARSE_CONTRACT_ID_RE.fullmatch(text(value)))


def normalize_contract_obligation_row(contract_id: str, row: dict[str, Any]) -> dict[str, str]:
    obligation_id = text(
        row.get("obligation_id")
        or row.get("sub_obligation_id")
        or row.get("Sub-obligation ID")
        or row.get("id")
    )
    normalized = {
        "Contract": contract_id,
        "Sub-obligation ID": obligation_id,
        "Edge": text(row.get("edge") or row.get("Edge")),
        "Sub-obligation type": text(row.get("row_kind") or row.get("sub_obligation_type") or row.get("Sub-obligation type")),
        "Semantic type": text(row.get("semantic_type") or row.get("Semantic type")),
        "Operation / surface": text(row.get("operation_surface") or row.get("operation") or row.get("Operation / surface")),
        "Canonical owner": text(row.get("canonical_owner") or row.get("Canonical owner")),
        "Fields/resource/state": text(row.get("fields_resource_state") or row.get("fields") or row.get("Fields/resource/state")),
        "Provider guarantee": text(row.get("provider_guarantee") or row.get("Provider guarantee")),
        "Consumer assumption": text(row.get("consumer_assumption") or row.get("Consumer assumption")),
        "Failure / timing detail": text(row.get("failure_timing_detail") or row.get("failure_timing") or row.get("Failure / timing detail")),
        "State/resource owner": text(row.get("state_resource_owner") or row.get("state_owner") or row.get("State/resource owner")),
        "Owner module": text(
            row.get("owner_module")
            or row.get("Owner module")
            or row.get("suggested_owner_module")
            or row.get("Suggested owner module")
            or row.get("canonical_owner_module")
        ),
        "Suggested owner module": text(row.get("suggested_owner_module") or row.get("Suggested owner module")),
        "Verification proof": flatten_text(row.get("verification") or row.get("verification_proof") or row.get("Verification proof")),
        "Split hint": text(row.get("split_hint") or row.get("Split hint")),
        "Edge type": text(row.get("edge_type") or row.get("Edge type")),
    }
    normalized["_obligation_id"] = obligation_id
    normalized["_obligation_group_id"] = obligation_id
    normalized["_row_id_aliases"] = obligation_id
    normalized["_row_text"] = flatten_text(row)
    return normalized


def contract_obligation_rows_from_model(model: "WorkflowModel") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for contract_id, raw_contract in model.contracts.items():
        contract = as_dict(raw_contract)
        for raw_row in as_list(contract.get("executable_obligations") or contract.get("obligations")):
            row = normalize_contract_obligation_row(str(contract_id), as_dict(raw_row))
            if not text(row.get("Sub-obligation ID")) or obligation_row_locked_na(row):
                continue
            rows.append(row)
    return rows


def active_contract_obligation_rows(model: "WorkflowModel") -> list[dict[str, str]]:
    change_dir = model.change_dir
    rows: list[dict[str, str]] = contract_obligation_rows_from_model(model)
    plan = read_optional(change_dir / "plan.md")
    executable = first_markdown_section(
        plan,
        "Contract Executable Obligation Matrix",
        "Contract Executable Obligations",
        "契约可执行子义务矩阵",
    )
    for row in markdown_table_dicts(executable):
        joined = flatten_text(row)
        if not joined or obligation_row_locked_na(row):
            continue
        obligation_ids = obligation_ids_from_cell(table_get(row, "Sub-obligation ID"))
        obligation_ids = [oid for oid in obligation_ids if not obligation_id_is_coarse_contract(oid)]
        if not obligation_ids:
            continue
        group_id = obligation_ids[0]
        for obligation_id in obligation_ids:
            copied = dict(row)
            copied["_obligation_id"] = obligation_id
            copied["_obligation_group_id"] = group_id
            copied["_row_text"] = joined
            copied["_row_id_aliases"] = " ".join(obligation_ids)
            rows.append(copied)
    for rel, row_id in specialized_contract_row_ids(change_dir):
        if any(re.search(rf"\b{re.escape(row_id)}\b", flatten_text(row)) for row in rows):
            continue
        rows.append({
            "_obligation_id": row_id,
            "_obligation_group_id": row_id,
            "_row_text": f"{rel} {row_id}",
            "Contract": rel,
            "Sub-obligation ID": row_id,
            "Semantic type": "specialized matrix obligation",
            "Split hint": "must map to owner task, proof-only, locked N/A, or backflow",
        })
    return rows


def obligation_row_id(row: dict[str, str]) -> str:
    return table_get(row, "_obligation_id") or table_get(row, "Sub-obligation ID") or table_get(row, "Contract")


def obligation_group_id(row: dict[str, str]) -> str:
    return table_get(row, "_obligation_group_id") or obligation_row_id(row)


def obligation_aliases(row: dict[str, str]) -> list[str]:
    aliases = obligation_ids_from_cell(table_get(row, "_row_id_aliases"))
    if aliases:
        return aliases
    oid = obligation_row_id(row)
    return [oid] if oid else []


def text_mentions_obligation_group(target: str, row: dict[str, str]) -> bool:
    return any(text_has_row_id(target, alias) for alias in obligation_aliases(row))


def obligation_is_high_risk(row: dict[str, str]) -> bool:
    return bool(HIGH_RISK_OBLIGATION_RE.search(flatten_text(row)))


def text_has_row_id(target: str, row_id: str) -> bool:
    return bool(row_id and re.search(rf"\b{re.escape(row_id)}\b", target))


def task_ids_from_row(row: dict[str, str]) -> set[str]:
    return set(re.findall(r"\bT\d{3}\b", flatten_text(row)))


def obligation_payload_materialized(row: dict[str, str], target_text: str) -> bool:
    payloads = [
        table_get(row, "Operation / surface"),
        table_get(row, "Fields/resource/state"),
        table_get(row, "Provider guarantee"),
        table_get(row, "Consumer assumption"),
        table_get(row, "Failure / timing detail"),
        table_get(row, "State/resource owner"),
        table_get(row, "Verification proof"),
    ]
    meaningful = [
        text(value)
        for value in payloads
        if text(value) and not locked_na(text(value)) and len(text(value)) >= 8
    ]
    if not meaningful:
        return True
    hits = sum(1 for value in meaningful if semantic_payload_copied(value, target_text))
    return hits >= min(len(meaningful), 3)


def normalized_owner_tokens(value: str) -> set[str]:
    raw = text(value)
    if not raw or locked_na(raw):
        return set()
    tokens = re.findall(r"[A-Za-z0-9]+", raw.upper())
    return {token for token in tokens if token and token not in {"MOD", "MODULE", "OWNER", "PRIMARY", "TASK"}}


def owner_modules_compatible(expected: str, actual: str) -> bool:
    expected_tokens = normalized_owner_tokens(expected)
    actual_tokens = normalized_owner_tokens(actual)
    if not expected_tokens or not actual_tokens:
        return False
    if expected_tokens <= actual_tokens or actual_tokens <= expected_tokens:
        return True
    expected_text = text(expected).upper()
    actual_text = text(actual).upper()
    return bool(expected_tokens & actual_tokens) and (expected_text in actual_text or actual_text in expected_text)


def task_primary_module(model: "WorkflowModel", task_id: str) -> str:
    return text(as_dict(model.tasks.get(task_id)).get("primary_module"))


def obligation_ids_in_text(value: str) -> set[str]:
    return set(OBLIGATION_ROW_ID_RE.findall(value or ""))


def row_is_semantic_provider(row: dict[str, str]) -> bool:
    row_kind = table_get(row, "Sub-obligation type") or table_get(row, "Row kind")
    edge_type = table_get(row, "Edge type")
    legitimacy = table_get(row, "Owner legitimacy")
    if CARRIER_EDGE_TYPE_RE.search(edge_type) or OWNER_NON_PROVIDER_RE.search(legitimacy):
        return False
    if (
        PROVIDER_OWNED_EDGE_TYPE_RE.search(edge_type)
        and PROVIDER_ROW_KIND_RE.search(row_kind)
        and not NON_PROVIDER_ROW_KIND_RE.search(row_kind)
    ):
        return True
    return False


def semantic_provider_obligation_ids_by_contract(rows_by_id: dict[str, dict[str, str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for row_id, row in rows_by_id.items():
        if row_is_semantic_provider(row):
            contract_id = obligation_contract_id(row) or contract_base_id(row_id)
            if contract_id:
                result[contract_id].add(row_id)
    return result


def semantic_provider_owner_modules_for_contract(rows_by_id: dict[str, dict[str, str]], contract_id: str) -> set[str]:
    modules: set[str] = set()
    for obligation_id in semantic_provider_obligation_ids_by_contract(rows_by_id).get(contract_id, set()):
        owner_module = contract_row_owner_module(rows_by_id.get(obligation_id, {}))
        if owner_module:
            modules.add(owner_module)
    return modules


def contract_semantic_provider_is_owner_single(rows_by_id: dict[str, dict[str, str]], contract_id: str) -> bool:
    return len(semantic_provider_owner_modules_for_contract(rows_by_id, contract_id)) <= 1


def contract_has_semantic_provider(rows: list[dict[str, str]]) -> bool:
    return any(row_is_semantic_provider(row) for row in rows)


def contract_is_composition_index(rows: list[dict[str, str]]) -> bool:
    owner_modules = {
        contract_row_owner_module(row)
        for row in rows
        if row_is_semantic_provider(row) and contract_row_owner_module(row)
    }
    return len(owner_modules) > 1


def contract_requires_coarse_provider_identity(rows: list[dict[str, str]]) -> bool:
    return contract_has_semantic_provider(rows) and not contract_is_composition_index(rows)


def module_and_contract_pack_context_errors(model: "WorkflowModel", context_text: str) -> list[str]:
    errors: list[str] = []
    if not context_text.strip():
        return errors
    module_pack = section(context_text, "Module And Contract Pack")
    if not module_pack:
        return errors
    for row in markdown_table_dicts(module_pack):
        module = table_get(row, "Module")
        provided = table_get(row, "Provided contracts")
        if not module or not provided or locked_na(provided):
            continue
        for contract_id in sorted(set(re.findall(r"\bC-\d{3}\b", provided))):
            contract = as_dict(model.contracts.get(contract_id))
            if not contract:
                continue
            provider_module = text(contract.get("provider_module"))
            if provider_module and not owner_modules_compatible(provider_module, module):
                errors.append(
                    f"task-planning: atomic-planning-context-pack.md Module And Contract Pack lists {module} "
                    f"as providing {contract_id}, but contracts.yaml provider_module is {provider_module}; "
                    "record API/DTO/wire/frontend/acceptance participation as carrier/consumer/proof, not Provided contracts"
                )
    return errors


def obligation_contract_id(row: dict[str, str]) -> str:
    return text(table_get(row, "Contract") or contract_base_id(table_get(row, "Sub-obligation ID")))


def validate_contract_executable_obligations(model: "WorkflowModel", stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"task-planning", "pre-execution", "acceptance", "all"}:
        return errors
    rows = active_contract_obligation_rows(model)
    rows_by_contract: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        contract_id = obligation_contract_id(row)
        if contract_id:
            rows_by_contract[contract_id].append(row)

    for cid, raw_contract in model.contracts.items():
        contract = as_dict(raw_contract)
        if contract.get("external_provider") is True or contract.get("status") in {"superseded", "not_applicable", "locked-na"}:
            continue
        cid_rows = rows_by_contract.get(str(cid), [])
        if not cid_rows:
            errors.append(
                f"{cid}: executable_obligations are required before task-planning; "
                "do not send a coarse C-xxx directly into task DAG"
            )
            continue
        provider_module = text(contract.get("provider_module"))
        if contract_provider_module_is_multi_owner(provider_module):
            errors.append(
                f"{cid}: provider_module must be owner-single, got {provider_module}; "
                "split semantic provider obligations or keep the coarse C-xxx as a composition index without multi-owner provider_module"
            )
        owner_modules = {
            contract_row_owner_module(row)
            for row in cid_rows
            if row_is_semantic_provider(row) and contract_row_owner_module(row)
        }
        if provider_module and len(owner_modules) > 1:
            errors.append(
                f"{cid}: provider_module cannot summarize multiple executable owner modules "
                f"({', '.join(sorted(owner_modules))}); keep C-xxx as a composition index and put provider ownership on C-xxx-OBL-yyy rows"
            )
        provider_rows = 0
        for row in cid_rows:
            obligation_id = table_get(row, "Sub-obligation ID")
            if obligation_id_is_coarse_contract(obligation_id):
                errors.append(f"{cid}: executable obligation must use C-xxx-OBL-yyy or specialized row ID, not coarse {obligation_id}")
            errors.extend(f"{cid}: {detail}" for detail in executable_obligation_column_drift_errors(row))
            errors.extend(f"{cid}: {detail}" for detail in owner_module_format_errors(row))
            if executable_obligation_row_too_thin(row):
                errors.append(f"{cid}: executable obligation row {obligation_id or '<missing>'} is too thin/generic")
            errors.extend(f"{cid}: {detail}" for detail in executable_obligation_row_granularity_errors(row))
            if not table_get(row, "Edge"):
                errors.append(
                    f"{cid}: executable obligation {obligation_id or '<missing>'} missing edge; "
                    "contracts.yaml executable_obligations[].edge and Markdown Edge must both be explicit"
                )
            edge_type = table_get(row, "Edge type")
            row_kind = table_get(row, "Sub-obligation type") or table_get(row, "Row kind")
            owner_module = contract_row_owner_module(row)
            if not edge_type:
                errors.append(f"{cid}: executable obligation {obligation_id or '<missing>'} missing edge_type")
            elif not (PROVIDER_OWNED_EDGE_TYPE_RE.search(edge_type) or CARRIER_EDGE_TYPE_RE.search(edge_type)):
                errors.append(
                    f"{cid}: executable obligation {obligation_id or '<missing>'} has invalid edge_type {edge_type}; "
                    "use semantic_contract_edge, carrier_order_edge, verification_prerequisite_edge, or proof_only_edge"
                )
            if PROVIDER_OWNED_EDGE_TYPE_RE.search(edge_type) and not row_is_semantic_provider(row):
                errors.append(
                    f"{cid}: non-provider obligation {obligation_id or '<missing>'} uses semantic_contract_edge with row_kind {row_kind or '<missing>'}; "
                    "consumer/proof/carrier rows must use carrier_order_edge, verification_prerequisite_edge, or proof_only_edge"
                )
            is_provider = row_is_semantic_provider(row)
            if is_provider:
                provider_rows += 1
                if not owner_module:
                    errors.append(f"{cid}: provider obligation {obligation_id or '<missing>'} requires owner_module")
                elif provider_module and len(owner_modules) <= 1 and not owner_modules_compatible(provider_module, owner_module):
                    errors.append(
                        f"{cid}: provider obligation {obligation_id or '<missing>'} owner_module {owner_module} "
                        f"does not match owner-single contract provider_module {provider_module}"
                    )
            elif PROVIDER_ROW_KIND_RE.search(row_kind) and CARRIER_EDGE_TYPE_RE.search(edge_type):
                errors.append(
                    f"{cid}: provider guarantee {obligation_id or '<missing>'} cannot use non-provider edge_type {edge_type}; "
                    "split carrier/proof into a separate row"
                )
        if provider_module and provider_rows == 0:
            errors.append(
                f"{cid}: no semantic_contract_edge provider obligation row exists for provider_module {provider_module}; "
                "carrier/proof rows cannot close the contract provider"
            )
    return errors


def executable_obligation_row_granularity_errors(row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    edge = table_get(row, "Edge")
    semantic_type = table_get(row, "Semantic type")
    operation = table_get(row, "Operation / surface")
    canonical_owner = table_get(row, "Canonical owner")
    fields_resource_state = table_get(row, "Fields/resource/state")
    provider = table_get(row, "Provider guarantee")
    consumer = table_get(row, "Consumer assumption")
    proof = table_get(row, "Verification proof")
    split_hint = table_get(row, "Split hint")
    sub_id = table_get(row, "Sub-obligation ID") or table_get(row, "Contract") or "<row>"

    for label, value in [
        ("Edge", edge),
        ("Canonical owner", canonical_owner),
        ("Fields/resource/state", fields_resource_state),
    ]:
        if not value or locked_na(value) or is_generic_packet_text(value) or re.fullmatch(
            r"(?:same as above|同上|same module|related|mode-specific|具体字段|字段资源状态|-)",
            value.strip(),
            re.IGNORECASE,
        ):
            errors.append(f"{sub_id}: {label} must be explicit and concrete; do not hide it in Provider guarantee text")
    for detail in contract_semantic_type_errors(semantic_type):
        errors.append(f"{sub_id}: {detail}")

    if obligation_field_has_unresolved_list(operation, CONTRACT_OBLIGATION_OPERATION_TERMS):
        errors.append(
            f"{sub_id}: Operation / surface combines multiple operation/surface terms; split into one row per operation or surface"
        )
    if obligation_field_has_unresolved_list(fields_resource_state, CONTRACT_OBLIGATION_RESOURCE_TERMS):
        errors.append(
            f"{sub_id}: Fields/resource/state combines multiple resource terms; split into one row per resource/state owner"
        )
    for label, value in [
        ("Operation / surface", operation),
        ("Fields/resource/state", fields_resource_state),
        ("Provider guarantee", provider),
        ("Consumer assumption", consumer),
    ]:
        if obligation_field_has_unresolved_list(value, CONTRACT_OBLIGATION_RESOURCE_TERMS):
            errors.append(
                f"{sub_id}: {label} combines multiple resource terms; split resource lifecycle/state ownership into separate rows"
            )
    if field_has_multiple_explicit_terms(consumer, CONTRACT_OBLIGATION_CONSUMER_MODULE_TERMS, CONTRACT_OBLIGATION_CONSUMER_SEPARATOR_RE):
        errors.append(
            f"{sub_id}: Consumer assumption combines multiple consumer modules; split provider guarantee from each consumer implementation/proof row"
        )
    if obligation_field_has_unresolved_list(proof, ["VER-001", "VER-002", "VER-003", "VER-004", "VER-005", "VER-006", "VER-007", "VER-008", "VER-009", "VER-010", "VER-011", "VER-012", "VER-013", "VER-014", "VER-015", "VER-016", "VER-017", "VER-018", "VER-019", "VER-020", "VER-021", "VER-022", "unit", "integration", "browser", "dom", "api", "mock", "packaged"]):
        errors.append(
            f"{sub_id}: Verification proof combines multiple proof loops; split or justify one short verification closure per row"
        )
    if split_hint and not locked_na(split_hint):
        if CONTRACT_OBLIGATION_GENERIC_SPLIT_HINT_RE.search(split_hint):
            errors.append(
                f"{sub_id}: Split hint is generic; it must name provider task, consumer task, proof-only row, locked N/A, or an explicit merge/split owner"
            )
        elif not re.search(r"\b(?:provider task|consumer task|proof-only|locked N/A|locked-na|merge into|split into|T\d{3}|owner module|独立|证明行|消费方|提供方|合并|拆)\b", split_hint, re.IGNORECASE):
            errors.append(
                f"{sub_id}: Split hint does not give an actionable task-planning decision"
            )
    return errors


def validate_sidecar_semantic_carriers(object_id: str, value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for idx, carrier in enumerate(as_list(value.get("semantic_carriers")), start=1):
        if not nonempty(carrier):
            errors.append(f"{object_id}: semantic_carriers[{idx}] is empty")
            continue
        if isinstance(carrier, dict):
            row = as_dict(carrier)
            payloads = [text(item) for item in as_list(row.get("must_preserve")) if text(item)]
            if not payloads:
                errors.append(f"{object_id}: semantic_carriers[{idx}] dict must include concrete must_preserve items")
                payloads = [text(row.get("carrier"))]
            for payload in payloads:
                if len(payload) < 24 or is_label_only_carrier(payload):
                    errors.append(
                        f"{object_id}: semantic_carriers[{idx}] is label-only or too thin; "
                        "copy concrete field/state/error/default/forbidden semantics"
                    )
                if is_generic_packet_text(payload):
                    errors.append(
                        f"{object_id}: semantic_carriers[{idx}] is generic placeholder text; "
                        "copy the concrete field/state/error/resource/action semantics"
                    )
        else:
            payload = text(carrier)
            if len(payload) < 40 or is_label_only_carrier(payload):
                errors.append(
                    f"{object_id}: semantic_carriers[{idx}] is label-only or too thin; "
                    "use a concrete sentence or dict.must_preserve, not a tag"
                )
            if is_generic_packet_text(payload):
                errors.append(
                    f"{object_id}: semantic_carriers[{idx}] is generic placeholder text; "
                    "copy the concrete field/state/error/resource/action semantics"
                )
    return errors


def validate_dense_carrier_object(object_id: str, value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rules = infer_dense_rules(scrub_carriers(value))
    if not rules:
        return errors
    carriers = as_list(value.get("semantic_carriers"))
    carrier_text = dense_carrier_payload(carriers)
    if not carriers:
        rule_names = ", ".join(rule["name"] for rule in rules)
        errors.append(f"{object_id}: dense semantics inferred ({rule_names}) but semantic_carriers is missing")
        return errors
    for rule in rules:
        missing = missing_dense_groups(carrier_text, rule["required_groups"])
        if missing:
            errors.append(
                f"{object_id}: semantic_carriers do not preserve inferred dense semantics {rule['name']}; missing {', '.join(missing)}"
            )
    return errors


class WorkflowModel:
    def __init__(self, change_dir: Path) -> None:
        self.change_dir = change_dir
        self.workflow = as_dict(load_yaml(change_dir / "workflow-state.yaml"))
        self.semantic = as_dict(load_yaml(change_dir / "semantic-objects.yaml"))
        self.contracts_doc = as_dict(load_yaml(change_dir / "contracts.yaml"))
        self.verification_doc = as_dict(load_yaml(change_dir / "verification.yaml"))
        self.dag_doc = as_dict(load_yaml(change_dir / "task-dag.yaml"))
        self.backflow_doc = as_dict(load_yaml(change_dir / "backflow.yaml"))
        self.packet_doc = as_dict(load_yaml(change_dir / "atomic-issue-packets.yaml"))

        self.sources = as_dict(self.semantic.get("sources"))
        self.requirements = as_dict(self.semantic.get("requirements"))
        self.scenarios = as_dict(self.semantic.get("scenarios"))
        self.semantic_carrier_projections = as_dict(self.semantic.get("semantic_carrier_projections"))
        self.decisions = as_dict(self.semantic.get("decisions"))
        self.migrations = as_dict(self.semantic.get("migrations"))
        self.contracts = as_dict(self.contracts_doc.get("contracts"))
        self.verifications = as_dict(self.verification_doc.get("verifications"))
        self.tasks = as_dict(self.dag_doc.get("tasks"))
        self.edges = as_list(self.dag_doc.get("edges"))
        self.parallel_groups = as_list(self.dag_doc.get("parallel_groups"))
        self.backflow_triggers = as_dict(self.backflow_doc.get("triggers"))
        self.supersession = as_dict(self.backflow_doc.get("supersession"))
        self.packets = as_dict(self.packet_doc.get("packets"))

    def has_structured_sidecars(self) -> bool:
        return any((self.change_dir / name).exists() for name in [
            "workflow-state.yaml",
            "semantic-objects.yaml",
            "contracts.yaml",
            "verification.yaml",
            "task-dag.yaml",
            "backflow.yaml",
        ])


def stage_construction_paths(change_dir: Path, stage: str) -> tuple[Path, Path]:
    root = change_dir / "stage-construction"
    return root / f"{stage}-obligations.yaml", root / f"{stage}-execution-pack.md"


def stage_construction_enabled_doc(workflow_doc: dict[str, Any]) -> bool:
    workflow = as_dict(workflow_doc.get("workflow"))
    marker = text(workflow.get("stage_construction_protocol"))
    schema_version = workflow_doc.get("schema_version")
    try:
        schema_number = int(schema_version or 0)
    except (TypeError, ValueError):
        schema_number = 0
    return marker == STAGE_CONSTRUCTION_PROTOCOL or (
        schema_number >= 2
        and text(workflow.get("skill")) == "automq-ai-dev-workflow-contextpack"
    )


def stage_construction_enabled(model: WorkflowModel) -> bool:
    return stage_construction_enabled_doc(model.workflow)


def legacy_contextpack_doc(workflow_doc: dict[str, Any]) -> bool:
    workflow = as_dict(workflow_doc.get("workflow"))
    try:
        schema = int(workflow_doc.get("schema_version") or 0)
    except (TypeError, ValueError):
        schema = 0
    return (
        schema < 2
        and text(workflow.get("skill")) == "automq-ai-dev-workflow-contextpack"
        and not text(workflow.get("stage_construction_protocol"))
    )


def load_stage_construction_contract() -> dict[str, Any]:
    contract = as_dict(load_yaml(STAGE_CONSTRUCTION_CONTRACT_PATH, required=True))
    if text(contract.get("protocol")) != STAGE_CONSTRUCTION_PROTOCOL:
        raise ValueError(
            f"{STAGE_CONSTRUCTION_CONTRACT_PATH}: expected protocol {STAGE_CONSTRUCTION_PROTOCOL}"
        )
    if not as_dict(contract.get("rules")) or not as_dict(contract.get("stages")):
        raise ValueError(f"{STAGE_CONSTRUCTION_CONTRACT_PATH}: rules/stages must be non-empty")
    return contract


def stage_upstream_receipt_hashes(workflow_doc: dict[str, Any], stage: str) -> dict[str, str]:
    receipts = as_dict(workflow_doc.get("stage_receipts"))
    na_receipts = as_dict(workflow_doc.get("stage_na_receipts"))
    result: dict[str, str] = {}
    for prerequisite in effective_stage_prerequisites(workflow_doc, stage):
        if prerequisite == "execution":
            execution_hash = text(as_dict(workflow_doc.get("execution_receipt")).get("receipt_hash"))
            if execution_hash:
                result[prerequisite] = execution_hash
            continue
        source = na_receipts if as_dict(workflow_doc.get("stage_status")).get(prerequisite) == "not_applicable" else receipts
        receipt_hash = text(as_dict(source.get(prerequisite)).get("receipt_hash"))
        if receipt_hash:
            result[prerequisite] = receipt_hash
    return result


def stage_rule_required_closure(
    contract: dict[str, Any],
    stage: str,
    rule_spec: dict[str, Any],
) -> list[str]:
    defaults = as_dict(contract.get("defaults"))
    required = [
        text(item)
        for item in as_list(rule_spec.get("required_closure") or defaults.get("required_closure"))
        if text(item)
    ]
    available = {
        text(item)
        for item in as_list(
            as_dict(defaults.get("closure_fields_available_by_stage")).get(stage)
        )
        if text(item)
    }
    if not available:
        return required
    return [field for field in required if field in available]


def stage_context_requirement_errors(
    change_dir: Path,
    stage: str,
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    workflow_doc = as_dict(load_yaml(change_dir / "workflow-state.yaml"))
    upstream_receipts = stage_upstream_receipt_hashes(workflow_doc, stage)

    def structured_context_errors(rel: str, body: str) -> list[str]:
        context_errors: list[str] = []
        source_matches = re.findall(
            r"^\|\s*([^|]+?)\s*\|\s*([0-9a-f]{64})\s*\|\s*$",
            body,
            re.MULTILINE | re.IGNORECASE,
        )
        valid_source = False
        for raw_path, recorded_hash in source_matches:
            source_rel = raw_path.strip().strip("`")
            source_path = stage_artifact_reference_path(change_dir, source_rel)
            if source_path and source_path.is_file() and sha256_file(source_path) == recorded_hash.lower():
                valid_source = True
                break
        if not valid_source:
            context_errors.append("missing current source artifact path/hash row")
        for upstream_stage, receipt_hash in upstream_receipts.items():
            if upstream_stage not in body or receipt_hash not in body:
                context_errors.append(f"missing upstream receipt {upstream_stage}:{receipt_hash}")
        if not re.search(
            r"\b(?:SRC|REQ|SCN|DEC(?:-[A-Z][A-Z0-9]*)?|PDEC|ADEC|READY-DEC|ARCH-DEC|DESIGN-DEC|MIG-DEC|UI-DEC|VER-DEC|TASK-DEC|C|VER|MIG|MOD|MECH|OPSEQ|EXTAPI|EVT|MRO|OPM|RMM|RLM|FCM|MIM|UI-ACT|ESE|PCP)-\d{3}\b",
            body,
        ):
            context_errors.append("missing consumed semantic object IDs")
        excerpt_match = re.search(
            r"^##+\s+Copied Semantic Excerpt\s*$\n(.*?)(?=^##+\s+|\Z)",
            body,
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        digest_match = re.search(r"^Semantic digest:\s*([0-9a-f]{64})\s*$", body, re.MULTILINE | re.IGNORECASE)
        excerpt = excerpt_match.group(1).strip() if excerpt_match else ""
        excerpt = re.sub(r"^Semantic digest:.*$", "", excerpt, flags=re.MULTILINE | re.IGNORECASE).strip()
        expected_digest = hashlib.sha256(excerpt.encode("utf-8")).hexdigest() if excerpt else ""
        if len(excerpt) < 40 or not digest_match or digest_match.group(1).lower() != expected_digest:
            context_errors.append("copied semantic excerpt/digest is missing or inconsistent")
        downstream_match = re.search(
            r"^##+\s+Downstream Coverage Targets\s*$\n(.*?)(?=^##+\s+|\Z)",
            body,
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        downstream = downstream_match.group(1).strip() if downstream_match else ""
        if len(downstream) < 12 or re.fullmatch(r"(?:none|n/?a|later|后续)[.!。]?", downstream, re.IGNORECASE):
            context_errors.append("missing downstream coverage targets")
        unresolved_match = re.search(
            r"^##+\s+Unresolved Required Rows\s*$\n(.*?)(?=^##+\s+|\Z)",
            body,
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        unresolved = unresolved_match.group(1).strip() if unresolved_match else ""
        if not unresolved_match or not re.fullmatch(r"(?:none|无|无未决项)[.!。]?", unresolved, re.IGNORECASE):
            context_errors.append("unresolved required rows must be explicitly empty")
        return [f"{rel}:{item}" for item in context_errors]

    stage_spec = as_dict(as_dict(contract.get("stages")).get(stage))
    for raw_requirement in as_list(stage_spec.get("context_requirements")):
        requirement = as_dict(raw_requirement)
        requirement_id = text(requirement.get("id")) or f"CTX-{stage}"
        description = text(requirement.get("description")) or "required context rehydration input"
        matched = False
        observed: list[str] = []
        for raw_alternative in as_list(requirement.get("any_of")):
            alternative = as_dict(raw_alternative)
            rel = text(alternative.get("path"))
            if not rel:
                continue
            path = change_dir / rel
            if not path.exists() or not path.is_file():
                observed.append(f"{rel}:missing")
                continue
            body = read_optional(path)
            heading = text(alternative.get("heading"))
            if heading and not re.search(
                rf"^##+\s+{re.escape(heading)}\s*$",
                body,
                re.MULTILINE | re.IGNORECASE,
            ):
                observed.append(f"{rel}:missing-heading:{heading}")
                continue
            structure_errors = structured_context_errors(rel, body)
            if structure_errors:
                observed.extend(structure_errors)
                continue
            matched = True
            break
        if not matched:
            detail = ", ".join(observed) or "no alternatives declared"
            errors.append(
                f"RULE {requirement_id} [earliest={stage} detected={stage}] "
                f"context preflight failed ({detail}); rationale={description}; "
                f"repair_stage={stage}; forbidden_shortcut=do not create downstream canonical artifacts before rehydration"
            )
    return errors


def stage_construction_scan(
    change_dir: Path,
    stage: str,
    contract: dict[str, Any],
) -> tuple[list[str], dict[str, list[dict[str, str]]], list[dict[str, str]]]:
    rules_by_stage: list[str] = []
    stage_spec = as_dict(as_dict(contract.get("stages")).get(stage))
    for rule_id in as_list(stage_spec.get("always")):
        value = text(rule_id)
        if value and value not in rules_by_stage:
            rules_by_stage.append(value)

    scan_documents: list[tuple[str, str]] = []
    for rel in stage_scan_source_rels(contract, stage):
        path = change_dir / rel
        if path.exists() and path.is_file():
            scan_documents.append((rel, scan_source_body(path)))

    trigger_evidence: dict[str, list[dict[str, str]]] = {}
    scan_evidence: list[dict[str, str]] = []
    for trigger_name, trigger_value in as_dict(contract.get("triggers")).items():
        trigger = as_dict(trigger_value)
        stage_rules = [text(item) for item in as_list(as_dict(trigger.get("rules_by_stage")).get(stage)) if text(item)]
        if not stage_rules:
            continue
        evidence_rows: list[dict[str, str]] = []
        ignore_patterns = [
            text(item)
            for item in as_list(trigger.get("ignore_if_excerpt_matches"))
            if text(item)
        ]
        for pattern_value in as_list(trigger.get("patterns")):
            pattern = text(pattern_value)
            if not pattern:
                continue
            for rel, body in scan_documents:
                if re.search(r"[A-Za-z0-9_]", pattern):
                    match = re.search(
                        rf"(?<![A-Za-z0-9_]){re.escape(pattern)}(?![A-Za-z0-9_])",
                        body,
                        re.IGNORECASE,
                    )
                else:
                    match = re.search(re.escape(pattern), body)
                if match is None:
                    continue
                start = max(0, match.start() - 60)
                end = min(len(body), match.end() + 100)
                excerpt = re.sub(r"\s+", " ", body[start:end]).strip()
                match_sentence = re.split(
                    r"[。！？.!?;\n]",
                    body[max(0, match.start() - 120):match.end()],
                )[-1]
                if any(re.search(ignore, match_sentence) for ignore in ignore_patterns):
                    continue
                evidence = {"path": rel, "pattern": pattern, "excerpt": excerpt}
                evidence_rows.append(evidence)
                scan_evidence.append({"trigger": trigger_name, **evidence})
                if len(evidence_rows) >= 3:
                    break
            if len(evidence_rows) >= 3:
                break
        if evidence_rows:
            trigger_evidence[trigger_name] = evidence_rows
            for rule_id in stage_rules:
                if rule_id not in rules_by_stage:
                    rules_by_stage.append(rule_id)

    return rules_by_stage, trigger_evidence, scan_evidence


def stage_construction_input_fingerprint(
    stage: str,
    upstream_receipts: dict[str, str],
    trigger_evidence: dict[str, list[dict[str, str]]],
) -> str:
    trigger_profile = {
        trigger: sorted(
            {
                stable_json_digest(
                    {
                        "path": text(item.get("path")),
                        "pattern": text(item.get("pattern")),
                        "excerpt": text(item.get("excerpt")),
                    }
                )
                for item in evidence
                if text(item.get("path"))
            }
        )
        for trigger, evidence in sorted(trigger_evidence.items())
    }
    return stable_json_digest(
        {
            "stage": stage,
            "upstream_stage_receipt_hashes": upstream_receipts,
            "trigger_profile": trigger_profile,
        }
    )


def stage_scan_source_rels(contract: dict[str, Any], stage: str) -> list[str]:
    per_stage = as_dict(contract.get("scan_sources_by_stage"))
    configured = as_list(per_stage.get(stage)) if stage else []
    source = configured or as_list(contract.get("scan_sources"))
    return [text(item) for item in source if text(item)]


def scan_source_body(path: Path) -> str:
    if path.suffix.lower() in {".yaml", ".yml"} and path.exists():
        try:
            parsed = load_yaml(path)
        except ValueError:
            parsed = {}
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True)
    return read_optional(path)


def markdown_heading_bodies(body: str, requested: list[str]) -> str:
    if not requested:
        return body
    matches = list(re.finditer(r"^(#{1,6})\s+(.+?)\s*$", body, re.MULTILINE))
    selected: list[str] = []
    wanted = {item.strip().lower() for item in requested if item.strip()}
    for index, match in enumerate(matches):
        title = match.group(2).strip().lower()
        if title not in wanted:
            continue
        level = len(match.group(1))
        end = len(body)
        for next_match in matches[index + 1:]:
            if len(next_match.group(1)) <= level:
                end = next_match.start()
                break
        selected.append(body[match.start():end])
    return "\n".join(selected)


def yaml_path_values(value: Any, path: str) -> list[Any]:
    parts = [part for part in path.split(".") if part]
    current = [value]
    for part in parts:
        next_values: list[Any] = []
        for item in current:
            if part == "*":
                if isinstance(item, dict):
                    next_values.extend(item.values())
                elif isinstance(item, list):
                    next_values.extend(item)
            elif isinstance(item, dict) and part in item:
                next_values.append(item[part])
        current = next_values
    return current


def stage_rule_object_ids(
    change_dir: Path,
    rule_id: str,
    contract: dict[str, Any],
    stage: str = "",
) -> list[str]:
    spec = as_dict(as_dict(contract.get("rules")).get(rule_id))
    decomposition = as_dict(spec.get("decompose_by"))
    patterns = [text(item).replace("\\\\", "\\") for item in as_list(decomposition.get("object_patterns")) if text(item)]
    if not patterns:
        return []
    effective_stage = stage or text(spec.get("earliest_stage"))
    requested_headings = [text(item) for item in as_list(decomposition.get("headings")) if text(item)]
    yaml_paths = [text(item) for item in as_list(decomposition.get("yaml_paths")) if text(item)]
    source_bodies: list[str] = []
    for rel in stage_scan_source_rels(contract, effective_stage):
        path = change_dir / rel
        if path.suffix.lower() in {".yaml", ".yml"} and path.exists():
            try:
                parsed = load_yaml(path)
            except ValueError:
                parsed = {}
            if yaml_paths:
                values = [value for yaml_path in yaml_paths for value in yaml_path_values(parsed, yaml_path)]
                source_bodies.append(json.dumps(values, ensure_ascii=False, sort_keys=True))
            else:
                source_bodies.append(json.dumps(parsed, ensure_ascii=False, sort_keys=True))
        else:
            source_bodies.append(markdown_heading_bodies(read_optional(path), requested_headings))
    combined = "\n".join(source_bodies)
    found: set[str] = set()
    for pattern in patterns:
        try:
            found.update(re.findall(rf"\b(?:{pattern})\b", combined))
        except re.error:
            continue
    return sorted(found)


def stage_obligation_id(stage: str, rule_id: str, object_id: str = "") -> str:
    base = f"{stage.upper().replace('-', '_')}-{rule_id}"
    return f"{base}-{object_id}" if object_id else base


def stage_rule_trigger(
    stage: str,
    rule_id: str,
    contract: dict[str, Any],
    trigger_evidence: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    stage_always = {
        text(item)
        for item in as_list(as_dict(as_dict(contract.get("stages")).get(stage)).get("always"))
    }
    matching: list[dict[str, str]] = []
    trigger_names: list[str] = []
    for trigger_name, evidence in trigger_evidence.items():
        stage_rules = {
            text(item)
            for item in as_list(
                as_dict(as_dict(as_dict(contract.get("triggers")).get(trigger_name)).get("rules_by_stage")).get(stage)
            )
        }
        if rule_id in stage_rules:
            trigger_names.append(trigger_name)
            matching.extend(evidence)
    kind = "always" if rule_id in stage_always else "signal"
    return {
        "kind": kind,
        "signals": trigger_names,
        "evidence": matching,
    }


def expected_stage_obligation(
    stage: str,
    rule_id: str,
    contract: dict[str, Any],
    trigger_evidence: dict[str, list[dict[str, str]]],
    object_id: str = "",
) -> dict[str, Any]:
    spec = as_dict(as_dict(contract.get("rules")).get(rule_id))
    trigger = stage_rule_trigger(stage, rule_id, contract, trigger_evidence)
    trigger["digest"] = stage_trigger_digest(trigger)
    return {
        "obligation_id": stage_obligation_id(stage, rule_id, object_id),
        "rule_id": rule_id,
        "object_id": object_id,
        "title": text(spec.get("title")),
        "earliest_stage": text(spec.get("earliest_stage")),
        "phase": text(spec.get("phase")),
        "rationale": text(spec.get("rationale")),
        "repair_stage": text(spec.get("repair_stage")),
        "allow_not_applicable": spec.get("allow_not_applicable") is True,
        "required_closure": stage_rule_required_closure(contract, stage, spec),
        "not_applicable_required": [
            text(item)
            for item in as_list(as_dict(contract.get("defaults")).get("not_applicable_required"))
            if text(item)
        ],
        "trigger": trigger,
    }


def stage_obligation_metadata_errors(
    stage: str,
    row: dict[str, Any],
    expected: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    for field in [
        "obligation_id",
        "rule_id",
        "object_id",
        "title",
        "earliest_stage",
        "phase",
        "rationale",
        "repair_stage",
        "allow_not_applicable",
        "required_closure",
        "not_applicable_required",
        "trigger",
    ]:
        if row.get(field) != expected.get(field):
            errors.append(
                stage_rule_diagnostic(
                    stage,
                    expected,
                    f"generated ledger metadata {field} differs from machine contract; rerun prepare-stage",
                )
            )
    return errors


def stage_trigger_digest(trigger: dict[str, Any]) -> str:
    normalized = {
        "kind": text(trigger.get("kind")),
        "signals": sorted(text(item) for item in as_list(trigger.get("signals")) if text(item)),
        "evidence": sorted(
            stable_json_digest(
                {
                    "path": text(as_dict(item).get("path")),
                    "pattern": text(as_dict(item).get("pattern")),
                    "excerpt": text(as_dict(item).get("excerpt")),
                }
            )
            for item in as_list(trigger.get("evidence"))
            if text(as_dict(item).get("path"))
        ),
    }
    return stable_json_digest(normalized)


def default_stage_closure() -> dict[str, Any]:
    return {
        "canonical_artifacts": [],
        "evidence": [],
        "semantic_objects": [],
        "decisions": [],
        "contracts": [],
        "verifications": [],
        "negative_assertions": [],
        "downstream_consumers": [],
        "reason": "",
        "product_semantics": "",
        "verification": "",
    }


def render_stage_execution_pack(ledger: dict[str, Any]) -> str:
    stage = text(ledger.get("stage"))
    completeness_path = Path(__file__).resolve().parent.parent / "references" / "artifact-completeness-spec.md"
    completeness_body = read_optional(completeness_path)
    completeness_heading = STAGE_COMPLETENESS_HEADINGS.get(stage, "")
    completeness_excerpt = markdown_heading_bodies(completeness_body, [completeness_heading]) if completeness_heading else ""
    required_artifacts = [
        rel for rel in stage_required_artifact_rels(Path("."), stage)
        if not rel.startswith("stage-construction/") and not rel.startswith("stage-snapshots/")
    ]
    lines = [
        f"# {stage} Stage Execution Pack",
        "",
        "> 本文件由 `workflowctl.py prepare-stage` 生成。它是当前阶段的适用规则索引，不替代 canonical artifact。",
        "",
        "## Construction Order",
        "",
        "1. 一次只处理一个 obligation。",
        "2. 在 canonical artifact 中闭合语义，再把路径、ID、断言和 downstream consumer 回写 ledger。",
        "3. 运行 `validate-obligation` 写入行级 receipt 后再处理下一个 obligation。",
        "4. 全部关闭后运行 `validate-stage-construction`、阶段 validator、readonly review 和 `pass-stage`。",
        "",
        "## Stage Construction Inputs",
        "",
        f"- Owner skill: `{STAGE_OWNER_SKILL_PATHS.get(stage, 'automq-ai-dev-workflow-contextpack/SKILL.md')}`",
        f"- Required receipt artifacts: {', '.join(f'`{item}`' for item in required_artifacts) or 'defined by the owner skill'}",
        f"- Completeness source: `ai-dev-methodology/references/artifact-completeness-spec.md#{completeness_heading}`" if completeness_heading else "- Completeness source: owner skill and applicable obligation details below",
        "- Read the owner skill and this embedded stage excerpt before editing canonical artifacts; the obligation table alone is not an artifact schema.",
        "",
    ]
    if completeness_excerpt:
        lines.extend(["### Embedded Completeness Excerpt", "", completeness_excerpt.strip(), ""])
    lines.extend([
        "## Applicable Obligations",
        "",
        "| Obligation | Rule | Phase | Repair stage | Trigger |",
        "|---|---|---|---|---|",
    ])
    for value in as_list(ledger.get("obligations")):
        row = as_dict(value)
        trigger = as_dict(row.get("trigger"))
        trigger_text = ", ".join(text(item) for item in as_list(trigger.get("signals")) if text(item)) or text(trigger.get("kind"))
        lines.append(
            f"| {text(row.get('obligation_id'))} | {text(row.get('rule_id'))} | "
            f"{text(row.get('phase'))} | {text(row.get('repair_stage'))} | {trigger_text} |"
        )
    lines.extend(["", "## Obligation Details", ""])
    for value in as_list(ledger.get("obligations")):
        row = as_dict(value)
        trigger = as_dict(row.get("trigger"))
        trigger_evidence = [
            f"{text(as_dict(item).get('path'))}: {text(as_dict(item).get('excerpt'))}"
            for item in as_list(trigger.get("evidence"))
            if text(as_dict(item).get("path"))
        ]
        lines.extend(
            [
                f"### {text(row.get('obligation_id'))}: {text(row.get('title'))}",
                "",
                f"- Rule: `{text(row.get('rule_id'))}`",
                f"- Rationale: {text(row.get('rationale'))}",
                f"- Repair stage: `{text(row.get('repair_stage'))}`",
                f"- Required closure: {', '.join(text(item) for item in as_list(row.get('required_closure')) if text(item))}",
                f"- N/A allowed: {'yes' if row.get('allow_not_applicable') is True else 'no'}",
                f"- Trigger evidence: {'; '.join(trigger_evidence) if trigger_evidence else text(trigger.get('kind'))}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def prepare_stage(change_dir: Path, stage: str) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl prepare-stage", file=sys.stderr)
        return 2
    if stage not in STAGE_CONSTRUCTION_STAGES:
        print(f"ERROR: {stage}: stage construction is not supported", file=sys.stderr)
        return 2
    try:
        contract = load_stage_construction_contract()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    model = WorkflowModel(change_dir)
    if legacy_contextpack_doc(model.workflow):
        print(
            "ERROR: legacy contextpack schema v1 is frozen; run migrate-workflow-runtime explicitly before prepare-stage",
            file=sys.stderr,
        )
        return 1
    workflow_doc = model.workflow
    workflow_meta = as_dict(workflow_doc.get("workflow"))
    existing_marker = text(workflow_meta.get("stage_construction_protocol"))
    if existing_marker and existing_marker != STAGE_CONSTRUCTION_PROTOCOL:
        print(
            f"ERROR: workflow.stage_construction_protocol={existing_marker} is incompatible with {STAGE_CONSTRUCTION_PROTOCOL}",
            file=sys.stderr,
        )
        return 1
    errors = validate_workflow_runtime(model.workflow)
    errors.extend(validate_workdir_identity(model))
    stage_status = as_dict(model.workflow.get("stage_status"))
    if stage_status.get(stage) == "passed":
        passed_errors = validate_stage_receipts(model, stage)
        passed_errors.extend(validate_stage_construction(model, stage))
        if not passed_errors:
            print(f"Stage {stage} is already passed with a fresh construction receipt; prepare-stage is a no-op")
            return 0
        for error in passed_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"ERROR: {stage}: refusing to rewrite a passed stage; record/apply backflow, then run "
            f"workflowctl.py reopen-stage {stage} {change_dir} --backflow-id <BF-ID> --reason <reason>",
            file=sys.stderr,
        )
        return 1
    for prerequisite in effective_stage_prerequisites(model.workflow, stage):
        if prerequisite == "execution":
            errors.extend(execution_completion_errors(model))
        elif stage_status.get(prerequisite) not in {"passed", "not_applicable"}:
            errors.append(
                f"{stage}: prerequisite {prerequisite} must be passed/not_applicable before prepare-stage; "
                f"actual={stage_status.get(prerequisite)}"
            )
    receipt_errors = validate_stage_receipts(model, stage)
    errors.extend(receipt_errors)
    errors.extend(plan_append_only_errors(change_dir, model.workflow, stage))
    errors.extend(stage_context_requirement_errors(change_dir, stage, contract))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    rule_ids, trigger_evidence, scan_evidence = stage_construction_scan(change_dir, stage, contract)
    rules = as_dict(contract.get("rules"))
    unknown_rules = [rule_id for rule_id in rule_ids if rule_id not in rules]
    if unknown_rules:
        for rule_id in unknown_rules:
            print(f"ERROR: {stage}: machine contract references unknown rule {rule_id}", file=sys.stderr)
        return 1

    ledger_path, pack_path = stage_construction_paths(change_dir, stage)
    old_ledger = as_dict(load_yaml(ledger_path))
    old_rows = {
        text(as_dict(item).get("obligation_id")): as_dict(item)
        for item in as_list(old_ledger.get("obligations"))
        if text(as_dict(item).get("obligation_id"))
    }
    upstream_receipts = stage_upstream_receipt_hashes(model.workflow, stage)
    input_fingerprint = stage_construction_input_fingerprint(stage, upstream_receipts, trigger_evidence)
    contract_hash = sha256_file(STAGE_CONSTRUCTION_CONTRACT_PATH)
    old_upstream = as_dict(old_ledger.get("upstream_stage_receipt_hashes"))
    old_contract_hash = text(old_ledger.get("contract_hash"))

    obligations: list[dict[str, Any]] = []
    for rule_id in rule_ids:
        spec = as_dict(rules.get(rule_id))
        object_ids = stage_rule_object_ids(change_dir, rule_id, contract, stage)
        decomposition = as_dict(spec.get("decompose_by"))
        required_from = text(decomposition.get("typed_required_from_stage"))
        # Current-stage typed IDs do not exist before the first prepare-stage.
        # A coarse bootstrap row is legal here; the final construction gate
        # requires another prepare-stage after canonical artifacts create IDs.
        for object_id in object_ids or [""]:
            expected = expected_stage_obligation(stage, rule_id, contract, trigger_evidence, object_id)
            trigger = as_dict(expected.get("trigger"))
            trigger_digest = text(trigger.get("digest"))
            old = old_rows.get(text(expected.get("obligation_id")), {})
            old_trigger_digest = text(as_dict(old.get("trigger")).get("digest"))
            context_unchanged = (
                old_contract_hash == contract_hash
                and old_upstream == upstream_receipts
                and old_trigger_digest == trigger_digest
            )
            status = text(old.get("status")) if context_unchanged else ("pending-rewrite" if old else "open")
            if status not in STAGE_OBLIGATION_STATUSES:
                status = "open"
            closure = as_dict(old.get("closure")) if old else default_stage_closure()
            validation = as_dict(old.get("validation")) if context_unchanged else {}
            if context_unchanged and status in {"closed", "not_applicable"}:
                stale_probe = {**expected, "status": status, "closure": closure, "validation": validation}
                if stage_obligation_row_errors(change_dir, stage, stale_probe, True, expected):
                    status = "pending-rewrite"
                    validation = {}
            obligations.append({**expected, "status": status, "closure": closure, "validation": validation})

    ledger = {
        "schema_version": 1,
        "protocol": STAGE_CONSTRUCTION_PROTOCOL,
        "stage": stage,
        "prepared_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "contract_source": STAGE_CONSTRUCTION_CONTRACT_PATH.as_posix(),
        "contract_hash": contract_hash,
        "input_fingerprint": input_fingerprint,
        "upstream_stage_receipt_hashes": upstream_receipts,
        "scan_evidence": scan_evidence,
        "obligations": obligations,
    }
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    write_yaml(ledger_path, ledger)
    atomic_write_text(pack_path, render_stage_execution_pack(ledger))

    workflow_meta["stage_construction_protocol"] = STAGE_CONSTRUCTION_PROTOCOL
    workflow_doc["workflow"] = workflow_meta
    if stage_status.get(stage) in {None, "", "not_started"}:
        stage_status[stage] = "in_progress"
        workflow_doc["stage_status"] = stage_status
        write_yaml(change_dir / "workflow-state.yaml", workflow_doc)
    append_workflow_event(
        change_dir,
        "stage_prepared",
        {"stage": stage, "obligation_count": len(obligations), "input_fingerprint": input_fingerprint},
    )
    print(f"Prepared {len(obligations)} construction obligations for stage {stage}")
    print(f"  ledger: {ledger_path}")
    print(f"  execution pack: {pack_path}")
    return 0


def stage_rule_diagnostic(stage: str, row: dict[str, Any], detail: str) -> str:
    rule_id = text(row.get("rule_id")) or "unknown-rule"
    earliest = text(row.get("earliest_stage")) or "unknown"
    repair = text(row.get("repair_stage")) or earliest
    rationale = text(row.get("rationale")) or "machine contract obligation is not closed"
    trigger = as_dict(row.get("trigger"))
    evidence_paths = sorted(
        {
            text(as_dict(item).get("path"))
            for item in as_list(trigger.get("evidence"))
            if text(as_dict(item).get("path"))
        }
    )
    trigger_text = ",".join(evidence_paths) or text(trigger.get("kind")) or "unknown"
    return (
        f"RULE {rule_id} [earliest={earliest} detected={stage}] trigger={trigger_text}; "
        f"{detail}; rationale={rationale}; repair_stage={repair}; "
        "forbidden_shortcut=do not add keywords or edit only the obligation ledger"
    )


def stage_artifact_reference_path(change_dir: Path, reference: str) -> Path | None:
    rel = reference.split("#", 1)[0].strip()
    if not rel or rel.startswith("/") or ".." in Path(rel).parts:
        return None
    return change_dir / rel


def stage_obligation_row_errors(
    change_dir: Path,
    stage: str,
    row: dict[str, Any],
    require_validation: bool,
    expected: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    rule = expected or row
    status = text(row.get("status"))
    if status not in STAGE_OBLIGATION_STATUSES:
        errors.append(stage_rule_diagnostic(stage, row, f"invalid status={status or '<empty>'}"))
        return errors
    closure = as_dict(row.get("closure"))
    if status == "not_applicable":
        if rule.get("allow_not_applicable") is not True:
            errors.append(stage_rule_diagnostic(stage, rule, "not_applicable is forbidden for this rule"))
        for field in as_list(rule.get("not_applicable_required")):
            field = text(field)
            if len(text(closure.get(field))) < 8:
                errors.append(stage_rule_diagnostic(stage, rule, f"not_applicable closure missing concrete {field}"))
    elif status != "closed":
        errors.append(stage_rule_diagnostic(stage, rule, f"obligation status must be closed/not_applicable, actual={status}"))

    generic_value_re = re.compile(
        r"^(?:covered|handled|later|planned|see\s+\w+|n/?a|tbd|todo|已覆盖|已处理|后续|见\w+)$",
        re.IGNORECASE,
    )
    for field in as_list(rule.get("required_closure")):
        field_name = text(field)
        values = meaningful_list(closure.get(field_name), min_chars=4)
        if not values:
            errors.append(stage_rule_diagnostic(stage, rule, f"required closure field {field_name} is empty"))
            continue
        for value in values:
            if generic_value_re.fullmatch(value):
                errors.append(stage_rule_diagnostic(stage, rule, f"closure field {field_name} contains generic value: {value}"))
        joined = " ".join(values)
        if field_name == "contracts" and not re.search(r"\bC-\d{3}(?:-OBL-\d{3})?\b", joined):
            errors.append(stage_rule_diagnostic(stage, rule, "contracts closure must reference concrete C-xxx/C-xxx-OBL-xxx IDs"))
        if field_name == "verifications" and not re.search(r"\bVER-\d{3}\b", joined):
            errors.append(stage_rule_diagnostic(stage, rule, "verifications closure must reference concrete VER-xxx IDs"))
        if field_name == "decisions" and not re.search(rf"\b(?:{DECISION_ID_PATTERN}|AUTH-\d{{3}})\b", joined):
            errors.append(stage_rule_diagnostic(stage, rule, "decisions closure must reference a concrete decision/AUTH ID"))
        if field_name == "semantic_objects" and not re.search(
            r"\b(?:SRC|REQ|SCN|MIG|SCP|MOD|MECH|OPSEQ|EXTAPI|EVT|MRO|OPM|RMM|RLM|FCM|MIM|UI-ACT|ESE|PCP)-\d{3}\b",
            joined,
        ):
            errors.append(stage_rule_diagnostic(stage, rule, "semantic_objects closure must reference a concrete semantic object ID"))
        if field_name == "negative_assertions" and not re.search(
            r"\b(?:not|no|without|absent|forbid|forbidden|must not|does not)\b|不得|不能|禁止|不出现|不存在|不会",
            joined,
            re.IGNORECASE,
        ):
            errors.append(stage_rule_diagnostic(stage, rule, "negative_assertions must contain a concrete negative condition"))

    artifact_hashes: dict[str, str] = {}
    artifact_bodies: list[str] = []
    for reference in meaningful_list(closure.get("canonical_artifacts"), min_chars=4):
        path = stage_artifact_reference_path(change_dir, reference)
        if path is None:
            errors.append(stage_rule_diagnostic(stage, rule, f"canonical artifact reference is not a safe relative path: {reference}"))
            continue
        if not path.exists() or not path.is_file():
            errors.append(stage_rule_diagnostic(stage, rule, f"canonical artifact does not exist: {reference}"))
            continue
        artifact_hashes[reference.split("#", 1)[0].strip()] = sha256_file(path)
        artifact_bodies.append(read_optional(path))

    canonical_text = "\n".join(artifact_bodies)
    id_patterns = {
        "semantic_objects": r"\b(?:SRC|REQ|SCN|MIG|SCP|MOD|MECH|OPSEQ|EXTAPI|EVT|MRO|OPM|RMM|RLM|FCM|MIM|UI-ACT|ESE|PCP)-\d{3}(?:-OBL-[A-Z0-9-]+)?\b",
        "decisions": rf"\b(?:{DECISION_ID_PATTERN}|AUTH-\d{{3}})\b",
        "contracts": r"\bC-\d{3}(?:-OBL-\d{3})?\b",
        "verifications": r"\bVER-\d{3}\b",
    }
    for field_name, pattern in id_patterns.items():
        referenced = set(re.findall(pattern, " ".join(meaningful_list(closure.get(field_name), 1))))
        missing = sorted(item for item in referenced if item not in canonical_text)
        if missing:
            errors.append(
                stage_rule_diagnostic(
                    stage,
                    rule,
                    f"closure {field_name} references IDs absent from canonical artifacts: {', '.join(missing)}",
                )
            )

    if require_validation and status in {"closed", "not_applicable"}:
        validation = as_dict(row.get("validation"))
        closure_hash = stable_json_digest(closure)
        if text(validation.get("rule_id")) != text(rule.get("rule_id")):
            errors.append(stage_rule_diagnostic(stage, rule, "row-level validation receipt is missing or has wrong rule_id"))
        if text(validation.get("closure_hash")) != closure_hash:
            errors.append(stage_rule_diagnostic(stage, rule, "row-level validation receipt is stale after closure edit"))
        if as_dict(validation.get("artifact_hashes")) != artifact_hashes:
            errors.append(stage_rule_diagnostic(stage, rule, "row-level validation receipt is stale after canonical artifact edit"))
        if text(validation.get("trigger_digest")) != text(as_dict(rule.get("trigger")).get("digest")):
            errors.append(stage_rule_diagnostic(stage, rule, "row-level validation receipt is stale after trigger change"))
        if text(validation.get("metadata_hash")) != stable_json_digest(rule):
            errors.append(stage_rule_diagnostic(stage, rule, "row-level validation receipt is stale after machine rule metadata change"))
    return errors


def stage_construction_context(
    model: WorkflowModel,
    stage: str,
) -> tuple[list[str], dict[str, Any], dict[str, dict[str, Any]]]:
    if stage not in STAGE_CONSTRUCTION_STAGES or not stage_construction_enabled(model):
        return [], {}, {}
    errors: list[str] = []
    ledger_path, pack_path = stage_construction_paths(model.change_dir, stage)
    if not ledger_path.exists():
        return [f"{stage}: stage construction ledger is missing; run workflowctl.py prepare-stage {stage} {model.change_dir} before canonical artifact work"], {}, {}
    if not pack_path.exists():
        errors.append(f"{stage}: stage execution pack is missing; rerun prepare-stage")
    try:
        contract = load_stage_construction_contract()
    except ValueError as exc:
        return [str(exc)], {}, {}
    ledger = as_dict(load_yaml(ledger_path))
    errors.extend(stage_context_requirement_errors(model.change_dir, stage, contract))
    if ledger.get("schema_version") != 1:
        errors.append(f"{stage}: obligation ledger schema_version must be 1")
    if text(ledger.get("protocol")) != STAGE_CONSTRUCTION_PROTOCOL:
        errors.append(f"{stage}: obligation ledger protocol mismatch")
    if text(ledger.get("stage")) != stage:
        errors.append(f"{stage}: obligation ledger stage mismatch: {ledger.get('stage')}")
    if text(ledger.get("contract_source")) != STAGE_CONSTRUCTION_CONTRACT_PATH.as_posix():
        errors.append(f"{stage}: obligation ledger contract_source does not match machine contract")
    contract_hash = sha256_file(STAGE_CONSTRUCTION_CONTRACT_PATH)
    if text(ledger.get("contract_hash")) != contract_hash:
        errors.append(f"{stage}: machine contract hash changed; rerun prepare-stage before validation")
    upstream_receipts = stage_upstream_receipt_hashes(model.workflow, stage)
    if as_dict(ledger.get("upstream_stage_receipt_hashes")) != upstream_receipts:
        errors.append(f"{stage}: upstream stage receipt hashes changed; rerun prepare-stage")

    rule_ids, trigger_evidence, scan_evidence = stage_construction_scan(model.change_dir, stage, contract)
    current_fingerprint = stage_construction_input_fingerprint(stage, upstream_receipts, trigger_evidence)
    if text(ledger.get("input_fingerprint")) != current_fingerprint:
        errors.append(
            f"{stage}: applicability trigger profile changed; rerun prepare-stage so new/removed obligations are explicit"
        )
    rows = [as_dict(item) for item in as_list(ledger.get("obligations"))]
    row_rules = [text(row.get("rule_id")) for row in rows]
    row_ids = [text(row.get("obligation_id")) for row in rows]
    duplicate_ids = sorted({item for item in row_ids if row_ids.count(item) > 1})
    if duplicate_ids:
        errors.append(f"{stage}: duplicate obligation IDs in ledger: {', '.join(duplicate_ids)}")
    missing_rules = sorted(set(rule_ids) - set(row_rules))
    extra_rules = sorted(set(row_rules) - set(rule_ids))
    if missing_rules:
        errors.append(f"{stage}: applicable machine rules missing from ledger: {', '.join(missing_rules)}")
    if extra_rules:
        errors.append(f"{stage}: stale machine rules remain in ledger: {', '.join(extra_rules)}")
    if as_list(ledger.get("scan_evidence")) != scan_evidence:
        errors.append(f"{stage}: scan_evidence differs from current trigger scan; rerun prepare-stage")
    expected_by_id: dict[str, dict[str, Any]] = {}
    for rule_id in rule_ids:
        spec = as_dict(as_dict(contract.get("rules")).get(rule_id))
        decomposition = as_dict(spec.get("decompose_by"))
        object_ids = stage_rule_object_ids(model.change_dir, rule_id, contract, stage)
        required_from = text(decomposition.get("typed_required_from_stage"))
        if decomposition and not object_ids and required_from and ALL_STAGES.index(stage) >= ALL_STAGES.index(required_from):
            errors.append(
                f"{stage}: {rule_id} has only a bootstrap obligation; create typed semantic object IDs in canonical artifacts, "
                "then rerun prepare-stage before closing the stage"
            )
        for object_id in object_ids or [""]:
            expected = expected_stage_obligation(stage, rule_id, contract, trigger_evidence, object_id)
            expected_by_id[text(expected.get("obligation_id"))] = expected
    missing_ids = sorted(set(expected_by_id) - set(row_ids))
    extra_ids = sorted(set(row_ids) - set(expected_by_id))
    if missing_ids:
        errors.append(f"{stage}: typed obligations missing from ledger: {', '.join(missing_ids)}")
    if extra_ids:
        errors.append(f"{stage}: stale/fake obligation IDs remain in ledger: {', '.join(extra_ids)}")
    for row in rows:
        expected = expected_by_id.get(text(row.get("obligation_id")))
        if expected is not None:
            errors.extend(stage_obligation_metadata_errors(stage, row, expected))
    if pack_path.exists() and read_optional(pack_path) != render_stage_execution_pack(ledger):
        errors.append(f"{stage}: execution pack differs from deterministic ledger rendering; rerun prepare-stage")
    return errors, ledger, expected_by_id


def validate_obligation(change_dir: Path, stage: str, obligation_id: str, not_applicable: bool = False) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl validate-obligation", file=sys.stderr)
        return 2
    model = WorkflowModel(change_dir)
    if as_dict(model.workflow.get("stage_status")).get(stage) == "passed":
        print(f"ERROR: {stage}: cannot close obligations after pass-stage; create/apply backflow first", file=sys.stderr)
        return 1
    context_errors, ledger, expected_by_id = stage_construction_context(model, stage)
    if context_errors:
        for error in context_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    target = next(
        (
            as_dict(row)
            for row in as_list(ledger.get("obligations"))
            if text(as_dict(row).get("obligation_id")) == obligation_id
        ),
        None,
    )
    expected = expected_by_id.get(obligation_id)
    if target is None or expected is None:
        print(f"ERROR: {stage}: obligation {obligation_id} is not present; rerun prepare-stage", file=sys.stderr)
        return 1
    target["status"] = "not_applicable" if not_applicable else "closed"
    errors = stage_obligation_row_errors(
        change_dir,
        stage,
        target,
        require_validation=False,
        expected=expected,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    closure = as_dict(target.get("closure"))
    artifact_hashes: dict[str, str] = {}
    for reference in meaningful_list(closure.get("canonical_artifacts"), min_chars=4):
        path = stage_artifact_reference_path(change_dir, reference)
        if path is not None and path.exists() and path.is_file():
            artifact_hashes[reference.split("#", 1)[0].strip()] = sha256_file(path)
    target["validation"] = {
        "rule_id": text(expected.get("rule_id")),
        "stage": stage,
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "closure_hash": stable_json_digest(closure),
        "artifact_hashes": artifact_hashes,
        "trigger_digest": text(as_dict(expected.get("trigger")).get("digest")),
        "metadata_hash": stable_json_digest(expected),
        "contract_hash": text(ledger.get("contract_hash")),
        "input_fingerprint": text(ledger.get("input_fingerprint")),
    }
    ledger_path, _ = stage_construction_paths(change_dir, stage)
    write_yaml(ledger_path, ledger)
    append_workflow_event(
        change_dir,
        "obligation_validated",
        {"stage": stage, "obligation_id": obligation_id, "status": target["status"]},
    )
    print(f"Obligation {obligation_id} validated and closed for stage {stage}")
    return 0


def validate_stage_construction(model: WorkflowModel, stage: str) -> list[str]:
    errors, ledger, expected_by_id = stage_construction_context(model, stage)
    if not ledger:
        return errors
    for row_value in as_list(ledger.get("obligations")):
        row = as_dict(row_value)
        expected = expected_by_id.get(text(row.get("obligation_id")))
        if expected is not None:
            errors.extend(
                stage_obligation_row_errors(
                    model.change_dir,
                    stage,
                    row,
                    require_validation=True,
                    expected=expected,
                )
            )
    return errors


def git_root_for(path: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    root = result.stdout.strip()
    return Path(root) if root else None


def git_changed_paths(repo_root: Path) -> set[str]:
    changed: set[str] = set()
    commands = [
        ["git", "-C", str(repo_root), "diff", "--name-only"],
        ["git", "-C", str(repo_root), "diff", "--cached", "--name-only"],
        ["git", "-C", str(repo_root), "ls-files", "--others", "--exclude-standard"],
    ]
    for command in commands:
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            continue
        for raw in result.stdout.splitlines():
            path = raw.strip()
            if path and not is_workflow_noise_path(repo_root, path):
                changed.add(path)
    return changed


def is_git_ignored(repo_root: Path, rel: str) -> bool:
    if not rel:
        return False
    result = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", "--", rel],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def is_workflow_noise_path(repo_root: Path | None, rel: str) -> bool:
    normalized = rel.strip().strip("/")
    if not normalized:
        return False
    if Path(normalized).name in SYSTEM_NOISE_BASENAMES:
        return True
    if SYSTEM_NOISE_PATH_RE.search(normalized):
        return True
    if repo_root is not None and is_git_ignored(repo_root, normalized):
        return True
    return False


def command_output(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def repo_relative(change_dir: Path, path: Path) -> str | None:
    repo_root = git_root_for(change_dir)
    if repo_root is None:
        return None
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None


def change_relative(change_dir: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(change_dir.resolve()).as_posix()
    except ValueError:
        return None


def changed_paths_relative_to_change(change_dir: Path) -> set[str]:
    repo_root = git_root_for(change_dir)
    if repo_root is None:
        return set()
    try:
        change_rel = change_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return set()
    prefix = f"{change_rel}/"
    relative: set[str] = set()
    for path in git_changed_paths(repo_root):
        if path == change_rel:
            continue
        if path.startswith(prefix):
            relative.add(path[len(prefix):])
    return relative


def changed_paths_outside_change(change_dir: Path) -> list[str]:
    repo_root = git_root_for(change_dir)
    if repo_root is None:
        return []
    try:
        change_rel = change_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return []
    return sorted(
        path
        for path in git_changed_paths(repo_root)
        if path != change_rel and not path.startswith(f"{change_rel}/")
    )


def current_git_state(change_dir: Path) -> dict[str, Any]:
    repo_root = git_root_for(change_dir)
    if repo_root is None:
        return {}
    return {
        "repo_root": repo_root.as_posix(),
        "head": command_output(["git", "-C", str(repo_root), "rev-parse", "HEAD"]),
        "branch": command_output(["git", "-C", str(repo_root), "branch", "--show-current"]),
        "changed_paths": sorted(git_changed_paths(repo_root)),
    }


def mutable_execution_path(rel: str) -> bool:
    return rel in EXECUTION_MUTABLE_RELATIVE or any(rel.startswith(prefix) for prefix in EXECUTION_MUTABLE_PREFIXES)


def sealed_artifact_digest_map(change_dir: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    if not change_dir.exists():
        return digests
    repo_root = git_root_for(change_dir)
    try:
        change_rel = change_dir.resolve().relative_to(repo_root.resolve()).as_posix() if repo_root else ""
    except ValueError:
        change_rel = ""
    for path in sorted(change_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(change_dir).as_posix()
        repo_rel = f"{change_rel}/{rel}" if change_rel else rel
        if is_workflow_noise_path(repo_root, repo_rel):
            continue
        if mutable_execution_path(rel):
            continue
        digests[rel] = artifact_receipt_digest(path, rel)
    return digests


def planning_paths_changed_after_execution_start(change_dir: Path) -> list[str]:
    changed = changed_paths_relative_to_change(change_dir)
    return sorted(rel for rel in changed if not mutable_execution_path(rel))


def task_files(task: dict[str, Any]) -> list[str]:
    return [str(item).strip() for item in as_list(task.get("files")) if str(item).strip()]


def path_matches_allowlist(path: str, allowlist: list[str]) -> bool:
    normalized = path.strip("/")
    for raw in allowlist:
        pattern = raw.strip().strip("/")
        if not pattern:
            continue
        if pattern.endswith("/"):
            if normalized.startswith(pattern):
                return True
        elif pattern.endswith("/**"):
            if normalized.startswith(pattern[:-3].rstrip("/") + "/"):
                return True
        elif any(ch in pattern for ch in "*?[]"):
            if fnmatch.fnmatch(normalized, pattern):
                return True
        elif normalized == pattern or normalized.startswith(pattern.rstrip("/") + "/"):
            return True
    return False


def changed_path_digest(repo_root: Path, rel: str) -> str:
    path = repo_root / rel
    if not path.exists():
        return "__missing__"
    if path.is_dir():
        return "__dir__"
    return sha256_file(path)


def changed_path_digest_map(repo_root: Path, paths: set[str] | list[str]) -> dict[str, str]:
    return {path: changed_path_digest(repo_root, path) for path in sorted(paths)}


def passed_task_changed_hashes(model: WorkflowModel) -> dict[str, set[str]]:
    hashes: dict[str, set[str]] = defaultdict(set)
    for receipt in as_dict(model.workflow.get("task_receipts")).values():
        receipt_dict = as_dict(receipt)
        if receipt_dict.get("status") != "passed":
            continue
        for path, digest in as_dict(receipt_dict.get("passed_changed_path_hashes")).items():
            hashes[str(path)].add(str(digest))
    return hashes


def passed_task_output_freshness_errors(model: WorkflowModel) -> list[str]:
    latest: dict[str, tuple[str, str, str]] = {}
    for task_id, raw_receipt in as_dict(model.workflow.get("task_receipts")).items():
        receipt = as_dict(raw_receipt)
        if receipt.get("status") != "passed":
            continue
        passed_at = text(receipt.get("passed_at"))
        output_hashes = {
            **as_dict(receipt.get("passed_declared_output_hashes")),
            **as_dict(receipt.get("passed_changed_path_hashes")),
        }
        for path, digest in output_hashes.items():
            key = str(path)
            candidate = (passed_at, str(task_id), str(digest))
            if key not in latest or candidate[:2] >= latest[key][:2]:
                latest[key] = candidate
    if not latest:
        return []
    repo_root = git_root_for(model.change_dir)
    if repo_root is None:
        return ["cannot verify passed task output freshness outside a git worktree"]
    errors: list[str] = []
    for path, (_, task_id, expected) in sorted(latest.items()):
        actual = changed_path_digest(repo_root, path)
        if actual != expected:
            errors.append(
                f"{task_id}: passed output {path} changed after pass-task; "
                "record execution backflow, reseal/re-admit the owner task, and rerun acceptance"
            )
    return errors


def task_has_backflow_reseal(model: WorkflowModel, task_id: str | None) -> bool:
    if not task_id:
        return False
    for reseal in as_list(model.workflow.get("backflow_reseals")):
        if task_id in set(map(str, as_list(as_dict(reseal).get("invalidated_tasks")))):
            return True
    return False


def pre_admit_baseline_errors(model: WorkflowModel, task_id: str | None = None) -> list[str]:
    repo_root = git_root_for(model.change_dir)
    if repo_root is None:
        return []
    try:
        change_rel = model.change_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        change_rel = ""
    mutable_workflow_prefix = f"{change_rel}/" if change_rel else ""
    sealed = as_dict(as_dict(model.workflow.get("execution_receipt")).get("sealed_artifact_hashes"))
    passed_hashes = passed_task_changed_hashes(model)
    resealed_task_allowlist = task_files(as_dict(model.tasks.get(str(task_id)))) if task_has_backflow_reseal(model, task_id) else []
    offenders: list[str] = []
    for path in sorted(git_changed_paths(repo_root)):
        if mutable_workflow_prefix and path.startswith(mutable_workflow_prefix):
            rel = path[len(mutable_workflow_prefix):]
            if mutable_execution_path(rel):
                continue
            current_path = model.change_dir / rel
            if current_path.exists() and sealed.get(rel) == artifact_receipt_digest(current_path, rel):
                continue
            offenders.append(path)
            continue
        digest = changed_path_digest(repo_root, path)
        if digest in passed_hashes.get(path, set()):
            continue
        if resealed_task_allowlist and path_matches_allowlist(path, resealed_task_allowlist):
            continue
        offenders.append(path)
    if not offenders:
        return []
    preview = ", ".join(offenders[:12])
    suffix = "" if len(offenders) <= 12 else f", ... (+{len(offenders) - 12} more)"
    return [
        "admit-task baseline contains changes that are not sealed workflow files or unchanged output from passed tasks: "
        f"{preview}{suffix}. Do not let illegal pre-admission edits become the next task baseline."
    ]


def execution_receipt_errors(model: WorkflowModel) -> list[str]:
    errors: list[str] = []
    receipt = as_dict(model.workflow.get("execution_receipt"))
    if not receipt:
        return ["execution_receipt is missing; run workflowctl.py begin-execution before editing business files"]
    if receipt.get("status") != "started":
        errors.append("execution_receipt.status must be started")
    if stage_construction_enabled(model) and text(receipt.get("receipt_hash")) != canonical_receipt_hash(receipt):
        errors.append("execution_receipt.receipt_hash is forged or stale")
    recorded = as_dict(receipt.get("artifact_hashes"))
    expected = artifact_digest_map(model.change_dir, "pre-execution")
    if not recorded:
        errors.append("execution_receipt.artifact_hashes is missing")
    for rel, digest in expected.items():
        if recorded.get(rel) != digest:
            errors.append(f"execution_receipt artifact hash mismatch for {rel}; rerun pre-execution and begin-execution")
    sealed_recorded = as_dict(receipt.get("sealed_artifact_hashes"))
    sealed_expected = sealed_artifact_digest_map(model.change_dir)
    if not sealed_recorded:
        errors.append("execution_receipt.sealed_artifact_hashes is missing")
    for rel, digest in sealed_expected.items():
        if sealed_recorded.get(rel) != digest:
            errors.append(
                f"execution_receipt sealed artifact hash mismatch for {rel}; "
                "planning artifacts changed after begin-execution and require backflow/reseal"
            )
    for rel in sorted(set(sealed_recorded) - set(sealed_expected)):
        if not mutable_execution_path(rel):
            errors.append(f"execution_receipt sealed artifact {rel} no longer exists")
    expected_stage_receipts = stage_upstream_receipt_hashes(model.workflow, "pre-execution")
    if stage_construction_enabled(model) and as_dict(receipt.get("stage_receipt_hashes")) != expected_stage_receipts:
        errors.append("execution_receipt.stage_receipt_hashes is stale")
    if expected_stage_receipts and not as_dict(receipt.get("stage_receipt_hashes")):
        errors.append("execution_receipt.stage_receipt_hashes is missing")
    return errors


def task_receipts(model: WorkflowModel) -> dict[str, Any]:
    return as_dict(model.workflow.get("task_receipts"))


def task_receipt_for(model: WorkflowModel, task_id: str) -> dict[str, Any]:
    return as_dict(task_receipts(model).get(task_id))


def task_is_passed(model: WorkflowModel, task_id: str) -> bool:
    receipt = task_receipt_for(model, task_id)
    required_fields = [
        "task", "passed_at", "validator", "command", "verification_log",
        "verification_log_hash",
        "semantic_review_log", "semantic_review_hash", "semantic_review_verdict",
        "git_state", "passed_git_commit", "passed_changed_path_hashes", "passed_declared_output_hashes", "receipt_hash",
    ]
    strict = stage_construction_enabled(model)
    semantic_entry = latest_semantic_review_entry(model.change_dir, task_id) if strict else {}
    semantic_evidence_valid = (
        bool(semantic_entry)
        and stable_json_digest(semantic_entry) == text(receipt.get("semantic_review_hash"))
        and text(semantic_entry.get("verdict")).lower().replace("_", "-")
        in {"pass", "passed", "no-findings", "no-blocking-findings"}
    ) if strict else True
    verification_entries = verification_entries_for_task(verification_log_payload(model.change_dir), task_id) if strict else []
    verification_evidence_valid = (
        bool(verification_entries)
        and verification_entry_passed(verification_entries[-1])
        and stable_json_digest(verification_entries) == text(receipt.get("verification_log_hash"))
    ) if strict else True
    passed_commit = text(receipt.get("passed_git_commit"))
    commit_evidence_valid = True
    if strict and passed_commit:
        repo_root = git_root_for(model.change_dir)
        commit_evidence_valid = bool(
            repo_root
            and subprocess.run(
                ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", passed_commit, "HEAD"],
                text=True,
                capture_output=True,
                check=False,
            ).returncode == 0
        )
    return (
        receipt.get("status") == "passed"
        and receipt.get("task") == task_id
        and receipt.get("validator") == "workflowctl.py"
        and "pass-task" in text(receipt.get("command"))
        and receipt.get("diff_validated") is True
        and all(field in receipt and receipt.get(field) is not None for field in required_fields)
        and (not strict or bool(text(as_dict(receipt.get("git_state")).get("head"))))
        and (not strict or verification_log_has_task(model.change_dir, task_id))
        and verification_evidence_valid
        and semantic_evidence_valid
        and commit_evidence_valid
        and (
            not strict
            or bool(as_dict(receipt.get("passed_changed_path_hashes")))
            or bool(as_dict(receipt.get("passed_declared_output_hashes")))
            or bool(passed_commit)
        )
        and (
            not strict
            or text(receipt.get("receipt_hash")) == canonical_receipt_hash(receipt)
        )
    )


def execution_completion_errors(model: WorkflowModel) -> list[str]:
    errors = execution_receipt_errors(model)
    state = as_dict(model.workflow.get("stage_status"))
    if text(state.get("execution")) not in {"in_progress", "passed"}:
        errors.append(
            f"execution prerequisite requires in_progress/passed with a valid receipt; actual={state.get('execution', 'missing')}"
        )
    missing = sorted(task_id for task_id in model.tasks if not task_is_passed(model, task_id))
    if missing:
        preview = ", ".join(missing[:12])
        suffix = "" if len(missing) <= 12 else f", ... (+{len(missing) - 12} more)"
        errors.append(f"execution prerequisite requires pass-task receipts for all Atomic Issues; missing {preview}{suffix}")
    errors.extend(passed_task_output_freshness_errors(model))
    return errors


def predecessor_tasks(model: WorkflowModel, task_id: str) -> set[str]:
    predecessors: set[str] = set()
    for edge in model.edges:
        e = as_dict(edge)
        if str(e.get("to")) == task_id and str(e.get("from")) in model.tasks:
            predecessors.add(str(e.get("from")))
    return predecessors


def validate_task_receipt_chain(model: WorkflowModel, task_id: str) -> list[str]:
    errors: list[str] = []
    for predecessor in sorted(predecessor_tasks(model, task_id)):
        if not task_is_passed(model, predecessor):
            errors.append(f"{task_id}: predecessor task {predecessor} has no valid pass-task receipt")
    return errors


def admitted_task_receipt_errors(model: WorkflowModel, task_id: str) -> list[str]:
    receipt = task_receipt_for(model, task_id)
    if not receipt or receipt.get("status") not in {"admitted", "passed"}:
        return [f"{task_id}: task is not admitted; run workflowctl.py admit-task {task_id} before editing"]
    if stage_construction_enabled(model) and text(receipt.get("receipt_hash")) != canonical_receipt_hash(receipt):
        return [f"{task_id}: task receipt hash is forged or stale; re-admit or reseal the task"]
    allowlist = [str(item) for item in as_list(receipt.get("file_allowlist")) if str(item).strip()]
    if not allowlist:
        return [f"{task_id}: admitted receipt has empty file_allowlist"]
    recorded_issue_hash = receipt.get("issue_hash")
    issue_path = model.change_dir / str(as_dict(model.tasks.get(task_id)).get("issue", ""))
    if issue_path.exists() and recorded_issue_hash and recorded_issue_hash != sha256_file(issue_path):
        return [f"{task_id}: admitted issue hash is stale; recompile/re-admit task before editing"]
    recorded_packet_hash = receipt.get("packet_hash")
    packet_path = model.change_dir / "atomic-issue-packets.yaml"
    if packet_path.exists() and recorded_packet_hash and recorded_packet_hash != sha256_file(packet_path):
        return [f"{task_id}: admitted packet hash is stale; re-run task planning and admit-task"]
    return []


def validate_task_diff(change_dir: Path, task_id: str) -> list[str]:
    model = WorkflowModel(change_dir)
    errors: list[str] = []
    if task_id not in model.tasks:
        return [f"{task_id}: unknown task"]
    errors.extend(execution_receipt_errors(model))
    errors.extend(admitted_task_receipt_errors(model, task_id))
    if errors:
        return errors

    repo_root = git_root_for(change_dir)
    if repo_root is None:
        return errors
    receipt = task_receipt_for(model, task_id)
    allowlist = [str(item) for item in as_list(receipt.get("file_allowlist")) if str(item).strip()]
    baseline_hashes = {
        str(path): str(digest)
        for path, digest in as_dict(receipt.get("baseline_changed_path_hashes")).items()
    }
    changed = sorted(git_changed_paths(repo_root))
    try:
        change_rel = change_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        change_rel = ""

    mutable_workflow_prefix = f"{change_rel}/" if change_rel else ""
    offenders: list[str] = []
    for path in changed:
        if mutable_workflow_prefix and path.startswith(mutable_workflow_prefix):
            rel = path[len(mutable_workflow_prefix):]
            if mutable_execution_path(rel):
                continue
            sealed = as_dict(as_dict(model.workflow.get("execution_receipt")).get("sealed_artifact_hashes"))
            current_path = change_dir / rel
            if current_path.exists() and sealed.get(rel) == artifact_receipt_digest(current_path, rel):
                continue
            offenders.append(path)
            continue
        if not path_matches_allowlist(path, allowlist):
            if baseline_hashes.get(path) == changed_path_digest(repo_root, path):
                continue
            offenders.append(path)
    if offenders:
        preview = ", ".join(offenders[:12])
        suffix = "" if len(offenders) <= 12 else f", ... (+{len(offenders) - 12} more)"
        errors.append(
            f"{task_id}: diff contains files outside admitted allowlist or mutates sealed planning artifacts: {preview}{suffix}. "
            "Scope expansion requires backflow/reseal and a fresh admit-task receipt."
        )
    return errors


def validate_pre_execution_admission(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage != "pre-execution":
        return errors

    state = as_dict(model.workflow.get("stage_status"))
    execution_status = text(state.get("execution"))
    if execution_status and execution_status != "not_started":
        errors.append(
            "pre-execution admission: stage_status.execution must be not_started; "
            f"got {execution_status}. Gate failure must backflow before execution starts."
        )

    repo_root = git_root_for(model.change_dir)
    if repo_root is None:
        return errors
    try:
        change_rel = model.change_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return errors

    outside_changes = sorted(
        path
        for path in git_changed_paths(repo_root)
        if path != change_rel and not path.startswith(f"{change_rel}/")
    )
    if outside_changes:
        preview = ", ".join(outside_changes[:12])
        suffix = "" if len(outside_changes) <= 12 else f", ... (+{len(outside_changes) - 12} more)"
        errors.append(
            "pre-execution admission: code/worktree changes exist before the gate passed; "
            f"only files under {change_rel}/ may change before execution. Offending paths: {preview}{suffix}"
        )
    return errors


def validate_execution_state(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    state = as_dict(model.workflow.get("stage_status"))
    execution_status = text(state.get("execution"))
    outside_changes = changed_paths_outside_change(model.change_dir)
    if stage in {"execution", "acceptance", "mock-acceptance", "product-acceptance", "all"} or execution_status != "not_started":
        errors.extend(execution_receipt_errors(model))
    if outside_changes and not as_dict(model.workflow.get("execution_receipt")):
        preview = ", ".join(outside_changes[:12])
        suffix = "" if len(outside_changes) <= 12 else f", ... (+{len(outside_changes) - 12} more)"
        errors.append(
            "business/worktree changes exist without execution_receipt; "
            f"run begin-execution before editing. Offending paths: {preview}{suffix}"
        )
    if execution_status == "not_started" and as_dict(model.workflow.get("execution_receipt")):
        errors.append("workflow-state has execution_receipt but stage_status.execution is not_started")
    if execution_status in {"in_progress", "passed"}:
        sealed = as_dict(as_dict(model.workflow.get("execution_receipt")).get("sealed_artifact_hashes"))
        changed_planning = []
        for rel in planning_paths_changed_after_execution_start(model.change_dir):
            path = model.change_dir / rel
            if path.exists() and sealed.get(rel) == artifact_receipt_digest(path, rel):
                continue
            changed_planning.append(rel)
        if changed_planning:
            preview = ", ".join(changed_planning[:12])
            suffix = "" if len(changed_planning) <= 12 else f", ... (+{len(changed_planning) - 12} more)"
            errors.append(
                "sealed planning artifacts changed after execution started; "
                f"only execution-state.yaml, task-verification-log.yaml, task-semantic-review.yaml, mock-acceptance-execution.yaml, task-receipts/* and workflow-state.yaml are mutable. Changed: {preview}{suffix}"
            )
    return errors


def validate_task_status_receipts(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"pre-execution", "execution", "acceptance", "mock-acceptance", "product-acceptance", "all"}:
        return errors
    receipts = task_receipts(model)
    for tid, raw in model.tasks.items():
        task = as_dict(raw)
        status = str(task.get("status", "")).strip().lower()
        if status in TERMINAL_TASK_STATUSES:
            receipt = as_dict(receipts.get(tid))
            if receipt.get("status") != "passed":
                errors.append(
                    f"{tid}: task-dag/tasks status is terminal ({task.get('status')}) without pass-task receipt; "
                    "task completion must be derived from task_receipts, not hand-edited"
                )
    for tid, raw_receipt in receipts.items():
        if tid not in model.tasks:
            errors.append(f"task_receipts.{tid}: receipt exists for unknown task")
            continue
        receipt = as_dict(raw_receipt)
        if receipt.get("status") not in {"admitted", "passed"}:
            errors.append(f"task_receipts.{tid}.status must be admitted or passed")
        if receipt.get("status") == "passed":
            for predecessor in sorted(predecessor_tasks(model, str(tid))):
                if not task_is_passed(model, predecessor):
                    errors.append(f"task_receipts.{tid}: predecessor {predecessor} lacks pass-task receipt")
    return errors


def validate_stage_receipts(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    state = as_dict(model.workflow.get("stage_status"))
    receipts = as_dict(model.workflow.get("stage_receipts"))
    na_receipts = as_dict(model.workflow.get("stage_na_receipts"))
    if not state:
        return errors
    strict_receipts = stage_construction_enabled(model)

    stages_to_check: set[str] = {
        name for name in effective_stage_prerequisites(model.workflow, stage) if state.get(name) in {"passed", "not_applicable"}
    }
    if stage == "all":
        for stage_name, status in state.items():
            if status in {"passed", "not_applicable"}:
                stages_to_check.add(str(stage_name))
    if stage in state and state.get(stage) in {"passed", "not_applicable"}:
        stages_to_check.add(stage)
    if stage == "pre-execution":
        stages_to_check.update(
            name for name in effective_stage_prerequisites(model.workflow, "pre-execution")
            if state.get(name) in {"passed", "not_applicable"}
        )

    for stage_name in sorted(stages_to_check):
        if stage_name in {"execution", "acceptance", "all"}:
            continue
        if state.get(stage_name) == "not_applicable":
            if not strict_receipts:
                continue
            receipt = as_dict(na_receipts.get(stage_name))
            if not receipt:
                errors.append(
                    f"stage_status.{stage_name}=not_applicable but stage_na_receipts.{stage_name} is missing; "
                    "run workflowctl.py mark-stage-na"
                )
                continue
            policy = workflow_profile_policy(model.workflow)
            allowed = {text(item) for item in as_list(policy.get("whole_stage_na_allowed"))}
            if stage_name not in allowed:
                errors.append(f"stage_na_receipts.{stage_name}: whole-stage N/A is forbidden for profile {workflow_profile(model.workflow)}")
            for field in ["stage", "status", "issued_at", "validator", "command", "decision_id", "reason", "product_semantics", "verification", "receipt_hash"]:
                if not nonempty(receipt.get(field)):
                    errors.append(f"stage_na_receipts.{stage_name}.{field} is required")
            if receipt.get("stage") != stage_name or receipt.get("status") != "not_applicable":
                errors.append(f"stage_na_receipts.{stage_name}: stage/status mismatch")
            if "mark-stage-na" not in text(receipt.get("command")):
                errors.append(f"stage_na_receipts.{stage_name}.command must record workflowctl mark-stage-na")
            if text(receipt.get("receipt_hash")) != canonical_receipt_hash(receipt):
                errors.append(f"stage_na_receipts.{stage_name}.receipt_hash is forged or stale")
            expected_upstream = stage_upstream_receipt_hashes(model.workflow, stage_name)
            if as_dict(receipt.get("upstream_stage_receipt_hashes")) != expected_upstream:
                errors.append(f"stage_na_receipts.{stage_name}.upstream_stage_receipt_hashes is stale")
            continue
        receipt = as_dict(receipts.get(stage_name))
        if not receipt:
            errors.append(
                f"stage_status.{stage_name}=passed but stage_receipts.{stage_name} is missing; "
                "run workflowctl.py pass-stage after the stage validator/rubric passes"
            )
            continue
        if receipt.get("status") != "passed":
            errors.append(f"stage_receipts.{stage_name}.status must be passed")
        for field in ["stage", "status", "issued_at", "validator", "command", "artifact_hashes", "receipt_hash"]:
            if not nonempty(receipt.get(field)):
                errors.append(f"stage_receipts.{stage_name}.{field} is required")
        if receipt.get("stage") != stage_name:
            errors.append(f"stage_receipts.{stage_name}.stage mismatch: {receipt.get('stage')}")
        if receipt.get("validator") != "workflowctl.py":
            errors.append(f"stage_receipts.{stage_name}.validator must be workflowctl.py")
        command = text(receipt.get("command"))
        if f"validate {stage_name}" not in command:
            errors.append(f"stage_receipts.{stage_name}.command must record workflowctl validate {stage_name}")
        if strict_receipts and text(receipt.get("receipt_hash")) != canonical_receipt_hash(receipt):
            errors.append(f"stage_receipts.{stage_name}.receipt_hash is forged or stale")
        if strict_receipts:
            expected_stage_upstream = stage_upstream_receipt_hashes(model.workflow, stage_name)
            if as_dict(receipt.get("upstream_stage_receipt_hashes")) != expected_stage_upstream:
                errors.append(f"stage_receipts.{stage_name}.upstream_stage_receipt_hashes is stale")
        recorded = as_dict(receipt.get("artifact_hashes"))
        expected = artifact_digest_map(model.change_dir, stage_name)
        for rel in stage_required_artifact_rels(model.change_dir, stage_name):
            path = model.change_dir / rel
            if not path.exists():
                errors.append(f"stage_receipts.{stage_name}: required artifact {rel} is missing")
        if not recorded:
            errors.append(f"stage_receipts.{stage_name}.artifact_hashes is missing")
            continue
        for rel, digest in expected.items():
            if recorded.get(rel) != digest:
                errors.append(
                    f"stage_receipts.{stage_name}: artifact hash mismatch for {rel}; "
                    "stage must be rerun and re-receipted after artifact edits"
                )
        extra_recorded = sorted(set(recorded) - set(expected))
        for rel in extra_recorded:
            if not (model.change_dir / rel).exists():
                errors.append(f"stage_receipts.{stage_name}: recorded artifact {rel} no longer exists")
        if stage_name == "task-planning":
            recorded_upstream = as_dict(receipt.get("upstream_stage_receipt_hashes"))
            expected_upstream = upstream_receipt_hashes_for_task_planning(model.workflow)
            if expected_upstream and not recorded_upstream:
                errors.append(
                    "stage_receipts.task-planning.upstream_stage_receipt_hashes is missing; "
                    "rerun workflowctl.py pass-stage task-planning so Atomic Issues are sealed against upstream receipts"
                )
            elif recorded_upstream != expected_upstream:
                errors.append(
                    "stage_receipts.task-planning upstream receipt hashes are stale; "
                    "upstream semantic artifacts changed after task-planning, regenerate task-planning by default or provide Task Planning Impact Proof before local reseal"
                )
    return errors


def validate_stage_status(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    workflow = as_dict(model.workflow.get("workflow"))
    if workflow:
        if workflow.get("context_pack_required") is True:
            state = as_dict(model.workflow.get("stage_status"))
            for stage_name, status in state.items():
                if status not in VALID_STAGE_STATUS:
                    errors.append(
                        f"stage_status.{stage_name}: invalid status {status}; "
                        "use passed only after the stage validator/rubric passed. completed/done are not valid gate states"
                    )
            for prereq in effective_stage_prerequisites(model.workflow, stage):
                if prereq == "execution":
                    errors.extend(execution_completion_errors(model))
                elif state.get(prereq) not in {"passed", "not_applicable"}:
                    errors.append(f"stage {stage}: prerequisite {prereq} status is {state.get(prereq, 'missing')}, expected passed/not_applicable")

    isolation = as_dict(model.workflow.get("repo_isolation"))
    if workflow.get("repo_isolation_required") is True:
        required = ["target_repo", "base_branch", "base_commit", "uid", "worktree_path", "branch_name", "forbidden_sources", "allowed_sources"]
        for key in required:
            if not nonempty(isolation.get(key)):
                errors.append(f"workflow-state.yaml: repo_isolation.{key} is required")
        branch = str(isolation.get("branch_name", ""))
        uid = str(isolation.get("uid", ""))
        if branch and not branch.startswith("codex/"):
            errors.append("workflow-state.yaml: repo isolation branch_name must start with codex/")
        if branch and uid and uid not in branch:
            errors.append("workflow-state.yaml: repo isolation branch_name must include uid")
        worktree_path = str(isolation.get("worktree_path", ""))
        if worktree_path and uid and uid not in worktree_path:
            errors.append("workflow-state.yaml: repo isolation worktree_path must include uid")
    return errors


def validate_aip_artifacts(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"aip", "design", "archaeology", "contract", "verification", "task-planning", "pre-execution", "acceptance", "all"}:
        return errors

    workflow = as_dict(model.workflow.get("workflow"))
    if stage_construction_enabled(model) and workflow_profile(model.workflow) in {"execution-only", "repair"}:
        return errors
    state = as_dict(model.workflow.get("stage_status"))
    aip_status = state.get("aip")

    combined = flatten_text(
        [
            model.workflow,
            model.semantic,
            model.contracts_doc,
            model.verification_doc,
            model.dag_doc,
            model.packet_doc,
        ]
    )
    has_engineering_signal = bool(
        workflow.get("context_pack_required") is True
        or model.tasks
        or model.contracts
        or re.search(r"\bASG\b|\bK8s\b|Terraform|OpenAPI|Architecture|Engineering|架构|工程|接口|部署|云资源", combined, re.IGNORECASE)
    )
    if not has_engineering_signal:
        return errors
    if aip_status == "not_applicable":
        errors.append("AIP Creation Hard Gate: aip stage cannot be not_applicable when engineering/architecture/task-planning signals exist")

    aip_decisions_path = model.change_dir / "decision-reviews" / "aip-decisions.md"
    aip_path = model.change_dir / "aip.md"
    if not aip_path.exists() or not aip_path.read_text(encoding="utf-8").strip():
        errors.append("AIP Creation Hard Gate: missing specs/changes/<change-id>/aip.md")
    else:
        aip_text = aip_path.read_text(encoding="utf-8")
        errors.extend(validate_ordered_heading_patterns(aip_text, AIP_TEMPLATE_HEADINGS, "aip.md"))
        required_sections = [
            ("background/problem", [r"Background", r"背景", r"Problem", r"问题"]),
            ("goals/non-goals", [r"Goals?", r"目标", r"Non[- ]?goals?", r"非目标"]),
            ("selected architecture", [r"Selected architecture", r"Architecture", r"架构", r"方案"]),
            ("rejected alternatives", [r"Rejected alternatives", r"Alternatives", r"被拒绝", r"反选", r"替代方案"]),
            ("interfaces", [r"Interfaces?", r"OpenAPI", r"Terraform", r"接口"]),
            ("data/state/task model", [r"Data", r"State", r"Task", r"数据", r"状态", r"任务"]),
            ("deployment/cloud/IAM", [r"Deployment", r"cloud", r"IAM", r"K8s", r"ASG", r"EC2", r"部署", r"云资源"]),
            ("observability", [r"Observability", r"metrics", r"logs", r"events", r"观测", r"可观测"]),
            ("compatibility/rollback", [r"Compatibility", r"rollback", r"兼容", r"回滚"]),
            ("verification strategy", [r"Verification", r"验证"]),
        ]
        for label, patterns in required_sections:
            if not matches_any(aip_text, patterns):
                errors.append(f"aip.md: missing required AIP section/content: {label}")
        if re.search(r"^#+\s*(?:Background / problem|Goals / non-goals|Selected architecture|Rejected alternatives|Interfaces|Data/state/task model|Deployment/cloud/IAM|Observability|Compatibility/rollback|Verification strategy)\s*$", aip_text, re.IGNORECASE | re.MULTILINE):
            errors.append("aip.md: engineering-completeness outline must not replace AutoMQ AIP template headings; put these as subsections/tables under the standard template")
        errors.extend(validate_mechanism_design_closure(aip_text, "aip.md"))
        design_sources = "\n".join(
            [
                read_optional(model.change_dir / "plan.md"),
                read_optional(aip_decisions_path),
                read_optional(model.change_dir / "external-capability-research.md"),
            ]
        )
        errors.extend(validate_aip_narrative_materialization(aip_text, design_sources, "aip.md"))

    if not aip_decisions_path.exists() or not aip_decisions_path.read_text(encoding="utf-8").strip():
        errors.append("AIP Creation Hard Gate: missing decision-reviews/aip-decisions.md")
    return errors


def validate_decision_surface_routed_closure(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {
        "prd",
        "aip",
        "readiness",
        "design",
        "archaeology",
        "migration",
        "frontend-contract",
        "contract",
        "verification",
        "task-planning",
        "pre-execution",
        "acceptance",
        "all",
    }:
        return errors

    surface_text = read_optional(model.change_dir / "decision-surface-discovery.md")
    if not surface_text.strip():
        return errors

    inventory = section(surface_text, "Decision Surface Inventory")
    owner_gate = section(surface_text, "Owner Assignment Gate")
    if not inventory or not owner_gate:
        return errors

    stage_status = as_dict(model.workflow.get("stage_status"))
    owner_stage_by_surface: dict[str, str] = {}
    inventory_text_by_surface: dict[str, str] = {}
    gate_text_by_surface: dict[str, str] = {}

    def is_decision_surface_closed(text: str) -> bool:
        return bool(
            DECISION_SURFACE_LOCKED_NA_RE.search(text)
            or DECISION_SURFACE_BLOCKED_BACKFLOW_RE.search(text)
            or DECISION_SURFACE_CLOSED_RE.search(text)
        )

    for row in markdown_table_dicts(inventory):
        surface_id = table_get(row, "Surface ID")
        if not re.fullmatch(r"DS-\d{3}", surface_id):
            continue
        owner_stage_by_surface[surface_id] = table_get(row, "Decision owner stage")
        inventory_text_by_surface[surface_id] = " | ".join(row.values())

    for row in markdown_table_dicts(owner_gate):
        surface_id = table_get(row, "Surface ID")
        if not re.fullmatch(r"DS-\d{3}", surface_id):
            continue
        gate_text_by_surface[surface_id] = " | ".join(row.values())

    for surface_id, owner_stage in sorted(owner_stage_by_surface.items()):
        workflow_stage = DECISION_SURFACE_STAGE_ALIASES.get(owner_stage)
        if not workflow_stage:
            continue
        owner_stage_is_due = stage_status.get(workflow_stage) == "passed" or stage == workflow_stage
        if not owner_stage_is_due:
            continue
        combined = f"{inventory_text_by_surface.get(surface_id, '')} | {gate_text_by_surface.get(surface_id, '')}"
        if DECISION_SURFACE_LOCKED_NA_RE.search(combined):
            continue
        if ROUTED_DECISION_SURFACE_RE.search(combined) or not is_decision_surface_closed(combined):
            stage_reason = "is being signed off" if stage == workflow_stage else "is already passed"
            errors.append(
                f"decision-surface-discovery.md: {surface_id} owner stage {owner_stage} {stage_reason}, "
                "but the surface is still routed/stage-owned instead of closed as locked decision/contract/verification/Txxx, locked N/A, or blocked backflow"
            )
    return errors


def validate_id_shapes(model: WorkflowModel) -> list[str]:
    errors: list[str] = []
    collections = {
        "sources": model.sources,
        "requirements": model.requirements,
        "scenarios": model.scenarios,
        "decisions": model.decisions,
        "migrations": model.migrations,
        "contracts": model.contracts,
        "verifications": model.verifications,
        "tasks": model.tasks,
    }
    for name, values in collections.items():
        for object_id in values:
            if not OBJECT_RE.match(str(object_id)):
                errors.append(f"{name}: invalid object id {object_id}")
    return errors


def validate_semantic_graph(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []

    known = set(model.sources) | set(model.requirements) | set(model.scenarios) | set(model.decisions) | set(model.migrations)
    known |= set(model.contracts) | set(model.verifications) | set(model.tasks)

    for req_id, req in {**model.requirements, **model.scenarios}.items():
        errors.extend(validate_dense_carrier_object(req_id, as_dict(req)))
        errors.extend(validate_sidecar_semantic_carriers(req_id, as_dict(req)))
        if as_dict(req).get("status") not in {"locked", "accepted", "not_applicable"}:
            errors.append(f"{req_id}: status must be locked/accepted/not_applicable")
        if not nonempty(as_dict(req).get("semantics")):
            errors.append(f"{req_id}: semantics is required")
        consumed_by = set(map(str, as_list(as_dict(req).get("consumed_by"))))
        if stage in {"contract", "verification", "task-planning", "pre-execution", "acceptance", "all"} and not consumed_by:
            errors.append(f"{req_id}: consumed_by is required")
        if stage in {"verification", "task-planning", "pre-execution", "acceptance", "all"} and not any(item in model.verifications for item in consumed_by):
            errors.append(f"{req_id}: must be consumed by at least one VER")
        if stage in {"task-planning", "pre-execution", "acceptance", "all"} and not any(item in model.tasks for item in consumed_by):
            errors.append(f"{req_id}: must be consumed by at least one task")
        for item in consumed_by:
            if item not in known:
                errors.append(f"{req_id}: consumed_by references unknown object {item}")

    decision_keys: dict[str, list[str]] = defaultdict(list)
    for dec_id, dec_raw in model.decisions.items():
        dec = as_dict(dec_raw)
        errors.extend(validate_dense_carrier_object(dec_id, dec))
        errors.extend(validate_sidecar_semantic_carriers(dec_id, dec))
        status = dec.get("status")
        if status == "locked":
            key = str(dec.get("decision_key", "")).strip()
            if not key:
                errors.append(f"{dec_id}: locked decision missing decision_key")
            else:
                decision_keys[key].append(dec_id)
            if not nonempty(dec.get("decision")):
                errors.append(f"{dec_id}: locked decision missing decision text")
        if status == "superseded" and not nonempty(dec.get("superseded_by")):
            errors.append(f"{dec_id}: superseded decision missing superseded_by")
    for key, ids_for_key in decision_keys.items():
        if len(ids_for_key) > 1:
            errors.append(f"decision key {key}: multiple active locked decisions {', '.join(ids_for_key)}")

    return errors


def validate_contracts(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    rows = active_contract_obligation_rows(model)
    rows_by_contract: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        contract_id = obligation_contract_id(row)
        if contract_id:
            rows_by_contract[contract_id].append(row)
    for cid, raw in model.contracts.items():
        contract = as_dict(raw)
        errors.extend(validate_dense_carrier_object(cid, contract))
        errors.extend(validate_sidecar_semantic_carriers(cid, contract))
        if contract.get("status") != "locked":
            errors.append(f"{cid}: contract status must be locked")
        cid_rows = rows_by_contract.get(str(cid), [])
        requires_provider_identity = contract_requires_coarse_provider_identity(cid_rows)
        for field in ["trigger", "normal_path", "failure_path", "consistency", "timing"]:
            if not nonempty(contract.get(field)):
                errors.append(f"{cid}: missing {field}")
        if requires_provider_identity and not nonempty(contract.get("provider_module")):
            errors.append(f"{cid}: missing provider_module")
        if not as_list(contract.get("consumer_modules")):
            errors.append(f"{cid}: consumer_modules is required")
        provider_issue = contract.get("provider_issue")
        if stage in {"task-planning", "pre-execution", "acceptance", "all"}:
            if provider_issue and provider_issue not in model.tasks:
                errors.append(f"{cid}: provider_issue {provider_issue} is unknown")
            if provider_issue and provider_issue in model.tasks:
                provider_module = text(contract.get("provider_module"))
                provider_task_module = task_primary_module(model, str(provider_issue))
                if provider_module and provider_task_module and not owner_modules_compatible(provider_module, provider_task_module):
                    errors.append(
                        f"{cid}: provider_issue {provider_issue} primary_module {provider_task_module} "
                        f"does not match provider_module {provider_module}; carrier/order/proof tasks cannot own semantic provider contracts"
                    )
            if requires_provider_identity and not provider_issue and contract.get("external_provider") is not True:
                errors.append(f"{cid}: provider_issue is required unless external_provider=true")
            for task_id in as_list(contract.get("consumer_issues")):
                if task_id not in model.tasks:
                    errors.append(f"{cid}: consumer issue {task_id} is unknown")
        if stage in {"verification", "task-planning", "pre-execution", "acceptance", "all"} and not as_list(contract.get("verification")):
            errors.append(f"{cid}: verification is required")
        if stage in {"verification", "task-planning", "pre-execution", "acceptance", "all"}:
            for ver_id in as_list(contract.get("verification")):
                if ver_id not in model.verifications:
                    errors.append(f"{cid}: verification {ver_id} is unknown")
        if stage in {"task-planning", "pre-execution", "acceptance", "all"}:
            materialized = set(map(str, as_list(contract.get("materialized_in"))))
            required_materialization = {str(provider_issue)} | set(map(str, as_list(contract.get("consumer_issues"))))
            required_materialization.discard("")
            missing = required_materialization - materialized
            if missing:
                errors.append(f"{cid}: materialized_in missing tasks {', '.join(sorted(missing))}")
    errors.extend(validate_contract_executable_obligations(model, stage))
    return errors


def validate_verifications(model: WorkflowModel) -> list[str]:
    errors: list[str] = []
    for vid, raw in model.verifications.items():
        ver = as_dict(raw)
        if not nonempty(ver.get("expected_result")):
            errors.append(f"{vid}: expected_result is required")
        if not nonempty(ver.get("proves")):
            errors.append(f"{vid}: proves is required")
        if ver.get("required") is True and ver.get("status") in {"not_run", "blocked"} and ver.get("blocks_done") is not True:
            errors.append(f"{vid}: required unavailable verification must block done")
        for source_id in as_list(ver.get("source")):
            if source_id not in model.requirements and source_id not in model.scenarios and source_id not in model.contracts and source_id not in model.decisions and source_id not in model.migrations:
                errors.append(f"{vid}: source {source_id} is unknown")
    for nr_id, raw in as_dict(model.workflow.get("not_run")).items():
        nr = as_dict(raw)
        if nr.get("blocks_done") is True and not nonempty(nr.get("risk_accepted_by")):
            errors.append(f"{nr_id}: blocks_done Not Run risk lacks risk_accepted_by")
    return errors


def validate_stateful_behavior_artifacts(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"archaeology", "contract", "verification", "task-planning", "pre-execution", "acceptance", "mock-acceptance", "product-acceptance", "all"}:
        return errors
    combined = flatten_text(
        [
            model.semantic,
            model.contracts_doc,
            model.verification_doc,
            model.dag_doc,
            model.packet_doc,
            (model.change_dir / "plan.md").read_text(encoding="utf-8") if (model.change_dir / "plan.md").exists() else "",
            (model.change_dir / "tasks.md").read_text(encoding="utf-8") if (model.change_dir / "tasks.md").exists() else "",
        ]
    )
    if not matches_any(
        combined,
        [
            r"\b(lifecycle|progress|event|events|terminal|polling|retry|state\s*graph|state\s*machine|task\s*step|change\s*tracking|step\s*graph)\b",
            r"生命周期|进度|事件|状态机|状态图|终态|轮询|重试|任务步骤|变更追踪|状态推进",
        ],
    ):
        return errors

    matrix_yaml = model.change_dir / "stateful-behavior-matrix.yaml"
    matrix_md = model.change_dir / "stateful-behavior-matrix.md"
    if not matrix_yaml.exists() and not matrix_md.exists():
        errors.append(f"stateful-behavior: lifecycle/progress/event/status signal exists but stateful-behavior-matrix.yaml/md is missing")
        return errors

    if matrix_yaml.exists():
        raw = load_yaml(matrix_yaml)
        behaviors = as_list(as_dict(raw).get("stateful_behaviors"))
        if not behaviors:
            errors.append("stateful-behavior-matrix.yaml: stateful_behaviors is required")
        for behavior in behaviors:
            b = as_dict(behavior)
            rows = as_list(b.get("rows"))
            if not rows:
                errors.append(f"stateful-behavior-matrix.yaml: behavior {b.get('behavior_id') or '<missing>'} has no transition rows")
            for row_raw in rows:
                row = as_dict(row_raw)
                for field in [
                    "row_id",
                    "operation",
                    "mode_or_variant",
                    "from_state",
                    "trigger",
                    "event_or_step",
                    "status",
                    "to_state",
                    "terminal",
                    "failure_event_or_reason",
                    "verification",
                ]:
                    if not nonempty(row.get(field)):
                        errors.append(f"stateful-behavior-matrix.yaml: row {row.get('row_id') or '<missing>'} missing {field}")
                if row.get("terminal") not in {True, False, "true", "false", "yes", "no"}:
                    errors.append(f"stateful-behavior-matrix.yaml: row {row.get('row_id') or '<missing>'} terminal must be explicit true/false")
                if not as_list(row.get("consumers")) and not as_list(b.get("consumers")):
                    errors.append(f"stateful-behavior-matrix.yaml: row {row.get('row_id') or '<missing>'} missing consumers")
                if not any(
                    nonempty(row.get(field))
                    for field in [
                        "frontend_assertion",
                        "frontend_assertions",
                        "backend_assertion",
                        "backend_assertions",
                        "assertion",
                        "assertions",
                        "mock_fixture_ref",
                        "fixture_ref",
                        "fixture_refs",
                        "test_data_ref",
                    ]
                ):
                    errors.append(
                        f"stateful-behavior-matrix.yaml: row {row.get('row_id') or '<missing>'} "
                        "missing row-level assertion or fixture/test data reference"
                    )
        if not as_list(as_dict(raw).get("stateful_transition_coverage")):
            errors.append("stateful-behavior-matrix.yaml: stateful_transition_coverage is required")
        if not as_list(as_dict(raw).get("stateful_consumer_matrix")):
            errors.append("stateful-behavior-matrix.yaml: stateful_consumer_matrix is required")
    return errors


def validate_tasks(model: WorkflowModel) -> list[str]:
    errors: list[str] = []
    provider_contract_owners: dict[str, set[str]] = defaultdict(set)
    provider_obligation_owners: dict[str, set[str]] = defaultdict(set)
    active_obligation_rows = active_contract_obligation_rows(model)
    obligation_rows_by_id = {
        obligation_row_id(row): row
        for row in active_obligation_rows
        if obligation_row_id(row) and not obligation_id_is_coarse_contract(obligation_row_id(row))
    }
    semantic_provider_obligations_by_contract = semantic_provider_obligation_ids_by_contract(obligation_rows_by_id)
    for tid, raw in model.tasks.items():
        task = as_dict(raw)
        task_module = text(task.get("primary_module"))
        task_provides_obligations = set(map(str, as_list(task.get("provides_obligations"))))
        errors.extend(validate_dense_carrier_object(tid, task))
        errors.extend(validate_task_semantic_carriers(tid, task))
        if not TASK_RE.match(tid):
            errors.append(f"{tid}: invalid task id")
        for field in ["primary_module", "status", "issue"]:
            if not nonempty(task.get(field)):
                errors.append(f"{tid}: missing {field}")
        issue_path = model.change_dir / str(task.get("issue", ""))
        if task.get("issue") and not issue_path.exists():
            errors.append(f"{tid}: issue file does not exist: {task.get('issue')}")
        if not as_list(task.get("sources")):
            errors.append(f"{tid}: sources is required")
        if not as_list(task.get("verification")):
            errors.append(f"{tid}: verification is required")
        projection_ids_by_task = {
            carrier_row_projection_id(row)
            for source_id in map(str, as_list(task.get("sources")))
            for row in semantic_projection_rows_for_source(model, source_id)
            if projection_applies_to_task(row, tid, task) and carrier_row_projection_id(row)
        }
        for carrier in as_list(task.get("semantic_carriers")):
            carrier_text = text(carrier)
            if not SCP_ID_RE.fullmatch(carrier_text):
                continue
            if carrier_text not in projection_ids_by_task:
                errors.append(
                    f"{tid}: semantic_carriers references {carrier_text}, but no matching semantic_carrier_projection "
                    "for this task/source exists in semantic-objects.yaml"
                )
        for cid in as_list(task.get("consumes")):
            if cid not in model.contracts:
                errors.append(f"{tid}: consumes unknown contract {cid}")
        for cid in as_list(task.get("provides")):
            if cid not in model.contracts:
                errors.append(f"{tid}: provides unknown contract {cid}")
                continue
            cid_text = str(cid)
            provider_contract_owners[cid_text].add(str(tid))
            contract = as_dict(model.contracts.get(cid_text))
            semantic_ids = semantic_provider_obligations_by_contract.get(cid_text, set())
            if not semantic_ids:
                errors.append(
                    f"{tid}: lists provides {cid_text}, but {cid_text} has no semantic_contract_edge executable obligation; "
                    "proof-only/carrier-only/composition contracts cannot be semantic task provides"
                )
            elif not contract_semantic_provider_is_owner_single(obligation_rows_by_id, cid_text):
                owner_modules = ", ".join(sorted(semantic_provider_owner_modules_for_contract(obligation_rows_by_id, cid_text)))
                errors.append(
                    f"{tid}: lists provides {cid_text}, but semantic provider obligations under {cid_text} have multiple owner modules "
                    f"({owner_modules}); keep coarse C-xxx as a composition index and list only owner-single provides_obligations"
                )
            elif not semantic_ids <= task_provides_obligations:
                missing = ", ".join(sorted(semantic_ids - task_provides_obligations))
                errors.append(
                    f"{tid}: lists coarse provides {cid_text} without explicitly providing all owner semantic obligations "
                    f"({missing}); keep coarse C-xxx as a composition index or list owner-single provides_obligations"
                )
            elif task_module:
                mismatched = sorted(
                    obligation_id
                    for obligation_id in semantic_ids
                    if contract_row_owner_module(obligation_rows_by_id.get(obligation_id, {}))
                    and not owner_modules_compatible(contract_row_owner_module(obligation_rows_by_id.get(obligation_id, {})), task_module)
                )
                if mismatched:
                    errors.append(
                        f"{tid}: lists provides {cid_text}, but task primary_module {task_module} does not own "
                        f"semantic provider obligations {', '.join(mismatched)}"
                    )
        for obligation_id in map(str, as_list(task.get("provides_obligations"))):
            if not obligation_id:
                continue
            if obligation_id_is_coarse_contract(obligation_id):
                errors.append(
                    f"{tid}: provides_obligations must use C-xxx-OBL-yyy owner rows, not coarse {obligation_id}; "
                    "coarse contracts belong only in provides when all semantic provider obligations are owner-single and listed"
                )
                continue
            if not canonical_provider_ref(obligation_id):
                errors.append(
                    f"{tid}: provides_obligations contains non-contract/non-canonical provider ref {obligation_id}; "
                    "API wire carriers, DTO payload rows, proof files, fixtures and harness prerequisites must be modeled "
                    "as semantic_carriers plus carrier_order_edge/verification_prerequisite_edge/proof_only_edge, not as provides_obligations"
                )
                continue
            obligation_row = obligation_rows_by_id.get(obligation_id)
            if not obligation_row:
                errors.append(
                    f"{tid}: provides_obligations lists {obligation_id}, but no active Contract Executable Obligation Matrix row exists"
                )
                continue
            edge_type = table_get(obligation_row, "Edge type")
            if not row_is_semantic_provider(obligation_row):
                errors.append(
                    f"{tid}: provides_obligations lists {obligation_id}, but its edge_type is {edge_type or '<missing>'}; "
                    "only semantic_contract_edge provider guarantee obligations can be provided"
                )
            owner_module = contract_row_owner_module(obligation_row)
            if owner_module and task_module and not owner_modules_compatible(owner_module, task_module):
                errors.append(
                    f"{tid}: provides_obligations lists {obligation_id}, but suggested owner module is {owner_module} "
                    f"and task primary_module is {task_module}"
                )
            provider_obligation_owners[obligation_id].add(str(tid))
        for vid in as_list(task.get("verification")):
            if vid not in model.verifications:
                errors.append(f"{tid}: verification {vid} is unknown")
        for source_id in as_list(task.get("sources")):
            if source_id not in model.requirements and source_id not in model.scenarios and source_id not in model.decisions and source_id not in model.migrations:
                errors.append(f"{tid}: source {source_id} is unknown")
    for contract_id, owners in sorted(provider_contract_owners.items()):
        if len(owners) > 1:
            errors.append(
                f"{contract_id}: multiple task-dag semantic provider owners {', '.join(sorted(owners))}; "
                "keep exactly one provider_issue/provider task and model all other tasks as consumers, carriers, prerequisites, or proof-only"
            )
    for obligation_id, owners in sorted(provider_obligation_owners.items()):
        if len(owners) > 1:
            errors.append(
                f"{obligation_id}: multiple task-dag semantic provider owners {', '.join(sorted(owners))}; "
                "split distinct obligation rows or keep exactly one provider and model others as carrier/consumer/proof edges"
            )
    for obligation_id in sorted(obligation_rows_by_id):
        row = obligation_rows_by_id[obligation_id]
        if not row_is_semantic_provider(row):
            continue
        owners = provider_obligation_owners.get(obligation_id, set())
        if len(owners) != 1:
            errors.append(
                f"{obligation_id}: semantic_contract_edge obligation must have exactly one task-dag provides_obligations owner, "
                f"got {', '.join(sorted(owners)) or 'none'}"
            )
    return errors


def validate_dag(model: WorkflowModel) -> list[str]:
    errors: list[str] = []
    graph: dict[str, set[str]] = {tid: set() for tid in model.tasks}
    indegree: dict[str, int] = {tid: 0 for tid in model.tasks}

    for edge in model.edges:
        e = as_dict(edge)
        src = e.get("from")
        dst = e.get("to")
        if src not in model.tasks:
            errors.append(f"edge: from task {src} is unknown")
            continue
        if dst not in model.tasks:
            errors.append(f"edge: to task {dst} is unknown")
            continue
        if not nonempty(e.get("type")) or not nonempty(e.get("reason")):
            errors.append(f"edge {src}->{dst}: type and reason are required")
        if not nonempty(e.get("failure_propagation")):
            errors.append(f"edge {src}->{dst}: failure_propagation is required")
        if dst not in graph[src]:
            graph[src].add(dst)
            indegree[dst] += 1

    # Provider/consumer edges must exist.
    provider_by_contract: dict[str, str] = {}
    for tid, raw in model.tasks.items():
        for cid in as_list(as_dict(raw).get("provides")):
            provider_by_contract[str(cid)] = tid
    explicit_edges = {(as_dict(e).get("from"), as_dict(e).get("to")) for e in model.edges}
    for tid, raw in model.tasks.items():
        for cid in as_list(as_dict(raw).get("consumes")):
            provider = provider_by_contract.get(str(cid))
            if provider and provider != tid and (provider, tid) not in explicit_edges:
                errors.append(f"{tid}: consumes {cid} from {provider} but DAG edge {provider}->{tid} is missing")

    queue = deque([tid for tid, deg in indegree.items() if deg == 0])
    seen: list[str] = []
    while queue:
        tid = queue.popleft()
        seen.append(tid)
        for nxt in graph[tid]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if len(seen) != len(model.tasks):
        cycle_nodes = sorted(tid for tid, deg in indegree.items() if deg > 0)
        errors.append(f"task DAG has a cycle or unresolved dependency involving {', '.join(cycle_nodes)}")

    for group_raw in model.parallel_groups:
        group = as_dict(group_raw)
        if group.get("disjoint_files") is False:
            errors.append(f"parallel group {group.get('group')}: disjoint_files is false")
        if group.get("disjoint_contracts") is False:
            errors.append(f"parallel group {group.get('group')}: disjoint_contracts is false")
        if group.get("shared_verification") is True:
            errors.append(f"parallel group {group.get('group')}: shared_verification is true")
        for tid in as_list(group.get("tasks")):
            if tid not in model.tasks:
                errors.append(f"parallel group {group.get('group')}: task {tid} is unknown")

    return errors


def validate_backflow(model: WorkflowModel) -> list[str]:
    errors: list[str] = []
    superseded: set[str] = set(model.supersession)
    for obj_id, raw in model.decisions.items():
        if as_dict(raw).get("status") == "superseded":
            superseded.add(obj_id)
    for obj_id, raw in model.contracts.items():
        if as_dict(raw).get("status") == "superseded":
            superseded.add(obj_id)
    for obj_id, raw in model.verifications.items():
        if as_dict(raw).get("status") == "superseded":
            superseded.add(obj_id)
    for obj_id, raw in model.tasks.items():
        if as_dict(raw).get("status") in {"superseded", "pending-rewrite"}:
            superseded.add(obj_id)

    active_task_text: dict[str, set[str]] = {}
    for tid, raw in model.tasks.items():
        task = as_dict(raw)
        if task.get("status") in {"superseded", "pending-rewrite", "blocked"}:
            continue
        refs = set(map(str, as_list(task.get("sources"))))
        refs |= set(map(str, as_list(task.get("decisions"))))
        refs |= set(map(str, as_list(task.get("consumes"))))
        refs |= set(map(str, as_list(task.get("provides"))))
        refs |= set(map(str, as_list(task.get("verification"))))
        active_task_text[tid] = refs

    for tid, refs in active_task_text.items():
        for obj in sorted(refs & superseded):
            errors.append(f"{tid}: active task references superseded object {obj}")

    for bf_id, raw in model.backflow_triggers.items():
        trigger = as_dict(raw)
        invalidates = as_dict(trigger.get("invalidates"))
        if trigger.get("status") in {"open", "blocked"}:
            for task_id in as_list(invalidates.get("tasks")):
                task_status = as_dict(model.tasks.get(str(task_id))).get("status")
                if task_status not in {"blocked", "pending-rewrite", "pending-rerun"}:
                    errors.append(f"{bf_id}: invalidated task {task_id} must be blocked/pending-rewrite/pending-rerun, got {task_status}")
            for ver_id in as_list(invalidates.get("verifications")):
                ver_status = as_dict(model.verifications.get(str(ver_id))).get("status")
                if ver_status not in {"planned", "blocked", "pending-rerun", "not_run"}:
                    errors.append(f"{bf_id}: invalidated verification {ver_id} must be pending rerun/not_run/blocked, got {ver_status}")
            for dec_id in as_list(invalidates.get("decisions")):
                dec_status = as_dict(model.decisions.get(str(dec_id))).get("status")
                if dec_status not in {"superseded", "pending-rewrite", "blocked"}:
                    errors.append(f"{bf_id}: invalidated decision {dec_id} must be superseded/pending-rewrite/blocked, got {dec_status}")
            for contract_id in as_list(invalidates.get("contracts")):
                contract_status = as_dict(model.contracts.get(str(contract_id))).get("status")
                if contract_status not in {"superseded", "pending-rewrite", "blocked"}:
                    errors.append(f"{bf_id}: invalidated contract {contract_id} must be superseded/pending-rewrite/blocked, got {contract_status}")
    return errors


def validate_markdown_alignment(model: WorkflowModel) -> list[str]:
    errors: list[str] = []
    for tid, raw in model.tasks.items():
        task = as_dict(raw)
        issue = model.change_dir / str(task.get("issue", ""))
        if not issue.exists():
            continue
        text = issue.read_text(encoding="utf-8")
        for ref in set(map(str, as_list(task.get("sources")) + as_list(task.get("decisions")) + as_list(task.get("consumes")) + as_list(task.get("provides")) + as_list(task.get("verification")))):
            if ref and ref not in text:
                errors.append(f"{tid}: issue markdown missing structured reference {ref}")
        for file_path in as_list(task.get("files")):
            if file_path and str(file_path) not in text:
                errors.append(f"{tid}: issue markdown missing structured file path {file_path}")
    return errors


def packet_rows(packet: dict[str, Any], section: str, field: str) -> set[str]:
    return set(str(as_dict(row).get(field)) for row in as_list(packet.get(section)) if as_dict(row).get(field))


def validate_atomic_issue_packets(model: WorkflowModel) -> list[str]:
    errors: list[str] = []
    if not model.packets:
        return [f"{model.change_dir}: missing atomic-issue-packets.yaml packets; compile per-task context packets before atomic execution"]

    compiler = Path(__file__).with_name("atomic_issue_compile.py")
    result = subprocess.run(
        [sys.executable, str(compiler), str(model.change_dir), "--check"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        for line in output.splitlines():
            if line.strip():
                errors.append(f"atomic_issue_compile: {line.strip()}")

    allowed_provider_refs_by_task: dict[str, set[str]] = {}
    for task_id, raw_task in model.tasks.items():
        task = as_dict(raw_task)
        allowed = set(map(str, as_list(task.get("provides"))))
        for obligation_id in map(str, as_list(task.get("provides_obligations"))):
            if canonical_provider_ref(obligation_id):
                allowed.add(obligation_id)
        allowed_provider_refs_by_task[str(task_id)] = allowed

    for tid, raw_task in model.tasks.items():
        task = as_dict(raw_task)
        packet = as_dict(model.packets.get(tid))
        if not packet:
            errors.append(f"{tid}: missing packet in atomic-issue-packets.yaml")
            continue
        if str(packet.get("issue_path", "")) != str(task.get("issue", "")):
            errors.append(f"{tid}: packet issue_path must match task-dag issue")
        if str(packet.get("primary_module", "")) != str(task.get("primary_module", "")):
            errors.append(f"{tid}: packet primary_module must match task-dag primary_module")

        source_ids = packet_rows(packet, "sources", "id")
        expected_sources = set(map(str, as_list(task.get("sources"))))
        if not expected_sources <= source_ids:
            errors.append(f"{tid}: packet sources missing task sources {', '.join(sorted(expected_sources - source_ids))}")

        decision_ids = packet_rows(packet, "decisions", "id")
        expected_decisions = set(map(str, as_list(task.get("decisions"))))
        if not expected_decisions <= decision_ids:
            errors.append(f"{tid}: packet decisions missing task decisions {', '.join(sorted(expected_decisions - decision_ids))}")

        excerpt_contracts = packet_rows(packet, "contract_excerpts", "id")
        consumed_contracts = packet_rows(packet, "consumed_contract_snapshots", "contract")
        provided_contracts = packet_rows(packet, "provided_contract_obligations", "contract")
        expected_consumes = set(map(str, as_list(task.get("consumes"))))
        expected_provides = set(map(str, as_list(task.get("provides"))))
        expected_provider_refs = allowed_provider_refs_by_task.get(str(tid), set())
        missing_contract_excerpts = (expected_consumes | expected_provides) - excerpt_contracts
        if missing_contract_excerpts:
            errors.append(f"{tid}: packet contract_excerpts missing {', '.join(sorted(missing_contract_excerpts))}")
        if not expected_consumes <= consumed_contracts:
            errors.append(f"{tid}: packet consumed_contract_snapshots missing {', '.join(sorted(expected_consumes - consumed_contracts))}")
        if not expected_provides <= provided_contracts:
            errors.append(f"{tid}: packet provided_contract_obligations missing {', '.join(sorted(expected_provides - provided_contracts))}")

        provided_rows = [as_dict(row) for row in as_list(packet.get("provided_contract_obligations"))]
        provided_row_refs: set[str] = set()
        for row in provided_rows:
            contract_ref = text(row.get("contract"))
            if contract_ref:
                provided_row_refs.add(contract_ref)
                if not canonical_provider_ref(contract_ref):
                    errors.append(
                        f"{tid}: packet provided_contract_obligations uses non-canonical provider ref {contract_ref}; "
                        "wire carriers, fixture/proof rows and synthetic API carrier IDs must not be listed as provided obligations"
                    )
                elif not provider_ref_allowed(contract_ref, expected_provider_refs):
                    errors.append(
                        f"{tid}: packet provided_contract_obligations claims {contract_ref}, "
                        "but task-dag.yaml does not list it in provides/provides_obligations; "
                        "move it to consumed/precondition/carrier/proof sections or move provider ownership to the canonical owner task"
                    )
            for claimed_ref in provider_claim_refs(row):
                if not provider_ref_allowed(claimed_ref, expected_provider_refs):
                    errors.append(
                        f"{tid}: packet provided_contract_obligations text claims provider ownership of {claimed_ref}, "
                        "but task-dag.yaml does not list it in provides/provides_obligations"
                    )
        for claimed_ref in provider_claim_refs(as_dict(packet.get("atomicity_review"))):
            if not provider_ref_allowed(claimed_ref, expected_provider_refs):
                errors.append(
                    f"{tid}: packet atomicity_review claims provider ownership of {claimed_ref}, "
                    "but task-dag.yaml does not list it in provides/provides_obligations"
                )
        for claimed_ref in provider_claim_refs(
            [
                packet.get("title"),
                packet.get("module_responsibility"),
                packet.get("owned_state_data_resources"),
                packet.get("scope"),
            ]
        ):
            if not provider_ref_allowed(claimed_ref, expected_provider_refs):
                errors.append(
                    f"{tid}: packet module/scope text claims provider ownership of {claimed_ref}, "
                    "but task-dag.yaml does not list it in provides/provides_obligations"
                )

        verification_ids = packet_rows(packet, "verification", "id")
        expected_verification = set(map(str, as_list(task.get("verification"))))
        if not expected_verification <= verification_ids:
            errors.append(f"{tid}: packet verification missing {', '.join(sorted(expected_verification - verification_ids))}")

        packet_files = packet_rows(packet, "files_to_change", "path")
        expected_files = set(map(str, as_list(task.get("files"))))
        if not expected_files <= packet_files:
            errors.append(f"{tid}: packet files_to_change missing {', '.join(sorted(expected_files - packet_files))}")

        packet_text = flatten_text(packet)
        packet_carriers = [as_dict(row) for row in as_list(packet.get("semantic_carriers"))]
        packet_carrier_text = dense_carrier_payload(packet_carriers)
        for expected_carrier in as_list(task.get("semantic_carriers")):
            expected_text = text(expected_carrier)
            if re.fullmatch(r"SCP-\d{3}", expected_text):
                if not any(carrier_row_projection_id(row) == expected_text for row in packet_carriers):
                    errors.append(f"{tid}: packet semantic_carriers missing projection_id {expected_text}")
                continue
            if expected_text and expected_text not in packet_text:
                errors.append(f"{tid}: packet missing task semantic carrier: {expected_text}")

        direct_source_ids = set(map(str, as_list(task.get("sources"))))
        direct_decision_ids = set(map(str, as_list(task.get("decisions"))))
        direct_semantic_ids = direct_source_ids | direct_decision_ids
        upstream_ids = direct_semantic_ids | set(map(str, as_list(task.get("consumes")))) | set(map(str, as_list(task.get("provides"))))
        required_carriers: list[tuple[str, str]] = []
        for source_id in direct_source_ids:
            source_obj = as_dict(model.requirements.get(source_id)) or as_dict(model.scenarios.get(source_id))
            if not source_obj:
                continue
            projection_rows = [
                row
                for row in semantic_projection_rows_for_source(model, source_id)
                if projection_applies_to_task(row, tid, task)
            ]
            if source_has_dense_or_required_carriers(source_obj) and not projection_rows:
                errors.append(
                    f"{tid}: source {source_id} has dense semantics but no owner-specific semantic_carrier_projection for this task; "
                    "do not copy the full global REQ/SCN carrier into the packet"
                )
            for row in projection_rows:
                projection_id = carrier_row_projection_id(row)
                payloads = projection_payload_texts(row)
                for payload in payloads:
                    if payload:
                        required_carriers.append((projection_id or source_id, payload))
                if projection_id:
                    projection_present = any(
                        carrier_row_projection_id(packet_row) == projection_id
                        or (
                            carrier_row_source(packet_row) in {projection_id, source_id}
                            and semantic_payload_copied(projection_payload_text(row), flatten_text(packet_row))
                        )
                        for packet_row in packet_carriers
                    )
                    if not projection_present:
                        errors.append(
                            f"{tid}: packet semantic_carriers must carry projection {projection_id} from {source_id}; "
                            "full source excerpts or unrelated owner slices do not count"
                        )
            continue

        for source_id in upstream_ids - direct_source_ids:
            source_obj = (
                as_dict(model.requirements.get(source_id))
                or as_dict(model.scenarios.get(source_id))
                or as_dict(model.decisions.get(source_id))
                or as_dict(model.contracts.get(source_id))
                or as_dict(model.migrations.get(source_id))
            )
            if source_id in direct_decision_ids:
                for rule in infer_dense_rules(scrub_carriers(source_obj)):
                    missing = missing_dense_groups(packet_carrier_text, rule["required_groups"])
                    if missing:
                        errors.append(
                            f"{tid}: source {source_id} has inferred dense semantics {rule['name']} but packet semantic_carriers miss {', '.join(missing)}"
                        )
                    verification_ids_for_packet = set(map(str, as_list(task.get("verification"))))
                    verification_text = flatten_text([as_dict(model.verifications.get(vid)) for vid in verification_ids_for_packet])
                    if verification_text:
                        verification_missing = missing_dense_groups(verification_text, rule.get("verification_groups", []))
                        if verification_missing:
                            errors.append(
                                f"{tid}: verification for dense semantics {rule['name']} from {source_id} is too weak; missing {', '.join(verification_missing)}"
                            )
            for carrier_text in semantic_carrier_texts(source_obj.get("semantic_carriers")):
                if carrier_text:
                    required_carriers.append((source_id, carrier_text))
        for source_id, carrier_text in required_carriers:
            carrier_present = any(
                (carrier_row_source(row) == source_id or carrier_row_projection_id(row) == source_id)
                and semantic_payload_copied(carrier_text, flatten_text(row))
                for row in packet_carriers
            )
            copied_present = semantic_payload_copied(carrier_text, packet_text)
            if not carrier_present or not copied_present:
                errors.append(f"{tid}: packet missing semantic carrier from {source_id}: {carrier_text}")

        issue_rel = str(task.get("issue", ""))
        issue_path = model.change_dir / issue_rel
        if issue_rel and issue_path.exists():
            issue_text = issue_path.read_text(encoding="utf-8")
            provider_sections = "\n".join(
                [
                    section(issue_text, "范围"),
                    section(issue_text, "Atomicity Review"),
                    section(issue_text, "模块契约闭包"),
                    section(issue_text, "Provided Contract Obligation"),
                    section(issue_text, "完成标准"),
                ]
            )
            for claimed_ref in provider_claim_refs(provider_sections):
                if not provider_ref_allowed(claimed_ref, expected_provider_refs):
                    errors.append(
                        f"{tid}: compiled issue {issue_rel} claims provider ownership of {claimed_ref}, "
                        "but task-dag.yaml does not list it in provides/provides_obligations"
                    )
            provided_section = section(issue_text, "Provided Contract Obligation")
            for row in markdown_table_dicts(provided_section):
                for claimed_ref in provider_claim_refs(row):
                    if not provider_ref_allowed(claimed_ref, expected_provider_refs):
                        errors.append(
                            f"{tid}: compiled issue Provided Contract Obligation row claims {claimed_ref}, "
                            "but task-dag.yaml does not list it in provides/provides_obligations"
                        )

    for tid in model.packets:
        if tid not in model.tasks:
            errors.append(f"{tid}: packet exists but task is missing from task-dag.yaml")

    return errors


def validate_mock_acceptance(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    planning_mode = stage in MOCK_ACCEPTANCE_PLANNING_STAGES
    execution_mode = stage in MOCK_ACCEPTANCE_EXECUTION_STAGES
    if not planning_mode and not execution_mode:
        return errors
    combined = "\n".join(
        [
            read_optional(model.change_dir / "proposal.md"),
            read_optional(model.change_dir / "spec.md"),
            read_optional(model.change_dir / "plan.md"),
            read_optional(model.change_dir / "tasks.md"),
            read_optional(model.change_dir / "atomic-planning-context-pack.md"),
            read_optional(model.change_dir / "verification.yaml"),
            read_optional(model.change_dir / "contracts.yaml"),
            read_optional(model.change_dir / "atomic-issue-packets.yaml"),
        ]
    )
    required_by_signal = bool(MOCK_ACCEPTANCE_SIGNAL_RE.search(combined))
    if planning_mode and not required_by_signal:
        return errors
    validator = SKILLS_ROOT / "mock-acceptance-gate" / "scripts" / "validate_mock_acceptance_cases.py"
    if not validator.exists():
        errors.append(f"mock-acceptance validator is missing: {validator}")
        return errors
    mode = "planning" if planning_mode else "execution"
    result = subprocess.run(
        [sys.executable, str(validator), str(model.change_dir), "--mode", mode],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        for line in output.splitlines():
            if line.strip():
                errors.append(f"mock-acceptance: {line.strip()}")
    return errors


def validate_no_production_downgrade_language(model: WorkflowModel, stage: str) -> list[str]:
    if stage not in {"contract", "verification", "task-planning", "pre-execution", "mock-acceptance", "product-acceptance", "all"}:
        return []
    candidates = [
        "plan.md",
        "tasks.md",
        "contracts.yaml",
        "verification.yaml",
        "task-dag.yaml",
        "atomic-issue-packets.yaml",
        "mock-backend-matrix.yaml",
        "mock-frontend-action-matrix.yaml",
        "mock-acceptance-cases.yaml",
        "mock-acceptance.md",
    ]
    errors: list[str] = []
    for rel in candidates:
        path = model.change_dir / rel
        body = read_optional(path)
        if not body:
            continue
        match = PRODUCTION_DOWNGRADE_RE.search(body)
        if match:
            snippet = re.sub(r"\s+", " ", body[max(0, match.start() - 80): match.end() + 80]).strip()
            errors.append(
                f"{path}: wording may downgrade production implementation to local/no-cloud acceptance: {snippet}. "
                "Production implementation must call real provider/K8s/Connect REST/runtime/resource adapters; playground/no-cloud may only replace the physical external endpoint during acceptance."
            )
    return errors


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


def section(markdown: str, name: str) -> str:
    pattern = re.compile(rf"^##+\s+{re.escape(name)}\s*$", re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        return ""
    start = match.end()
    level = re.match(r"^(##+)", match.group(0)).group(1)
    next_match = re.search(rf"^{re.escape(level)}\s+", markdown[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(markdown)
    return markdown[start:end]


def first_markdown_section(markdown: str, *names: str) -> str:
    for name in names:
        found = section(markdown, name)
        if found:
            return found
    return ""


def markdown_table_dicts(markdown: str) -> list[dict[str, str]]:
    rows = markdown_table_rows(markdown)
    if not rows:
        return []
    header_index = 0
    for idx, row in enumerate(rows):
        joined = " ".join(cell.lower() for cell in row)
        if (
            "action id" in joined
            or "surface" in joined
            or "user task id" in joined
            or "form/step" in joined
            or "contract" in joined
            or "edge id" in joined
            or "txxx" in joined
            or "candidate rows" in joined
        ):
            header_index = idx
            break
    headers = [cell.strip() for cell in rows[header_index]]
    data: list[dict[str, str]] = []
    for row in rows[header_index + 1:]:
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))
        mapped = {headers[idx]: row[idx].strip() for idx in range(len(headers))}
        if any(value for value in mapped.values()):
            data.append(mapped)
    return data


def markdown_table_column_count_errors(markdown: str, columns: list[str], artifact: str) -> list[str]:
    rows = markdown_table_rows(markdown)
    if not rows:
        return []
    normalized_columns = {re.sub(r"[^a-z0-9]+", "", column.lower()) for column in columns}
    header_index: int | None = None
    for idx, row in enumerate(rows):
        normalized_row = {re.sub(r"[^a-z0-9]+", "", cell.lower()) for cell in row}
        if normalized_columns <= normalized_row:
            header_index = idx
            break
    if header_index is None:
        return []
    expected = len(rows[header_index])
    errors: list[str] = []
    for row_number, row in enumerate(rows[header_index + 1:], start=1):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != expected:
            snippet = " | ".join(row[: min(len(row), 6)])
            errors.append(
                f"{artifact}: table row {row_number} has {len(row)} cells but header has {expected}; "
                f"this usually means a Contract Executable Obligation Matrix column shifted: {snippet}"
            )
    return errors


def table_get(row: dict[str, str], *names: str) -> str:
    normalized = {re.sub(r"[^a-z0-9]+", "", key.lower()): value for key, value in row.items()}
    for name in names:
        key = re.sub(r"[^a-z0-9]+", "", name.lower())
        if key in normalized:
            return normalized[key]
    return ""


def human_decision_participation_enabled(value: str) -> bool:
    return bool(
        re.search(
            r"human-decision-participation|我参与决策|每个决策让我确认|不要自动决策|后续决策都问我|我来拍板",
            value,
            re.IGNORECASE,
        )
    )


def authority_scope_matches(prefix: str, scope: str) -> bool:
    if prefix == "PDEC-":
        return bool(re.search(r"\b(?:product|prd|pdec)\b|产品", scope, re.IGNORECASE))
    if prefix == "ADEC-":
        return bool(re.search(r"\b(?:architecture|engineering|aip|readiness|adec)\b|架构|工程", scope, re.IGNORECASE))
    return False


def authority_value_is_ai_authorized(value: str) -> bool:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    if not normalized:
        return False
    if "/" in normalized or "|" in normalized or "," in normalized:
        return False
    return normalized in {"ai-authorized", "ai authorized", "ai-authorized-by-scope", "ai authorized by scope"}


def authority_evidence_is_specific(value: str) -> bool:
    evidence = text(value)
    if len(evidence) < 8:
        return False
    if re.search(r"\b(?:TBD|TODO|unknown|not-authorized|not authorized)\b|待确认|未授权", evidence, re.IGNORECASE):
        return False
    if re.search(r"\buser message\s*/\s*doc\s*/\s*meeting note\b|用户消息\s*/\s*文档\s*/\s*会议", evidence, re.IGNORECASE):
        return False
    if evidence.lower() in {"user message", "doc", "meeting note", "user message / doc / meeting note"}:
        return False
    return True


def authority_table_authorizes_ai(prefix: str, value: str) -> bool:
    for section_text in [first_markdown_section(value, "Decision Authority", "决策权限"), value]:
        for row in markdown_table_dicts(section_text):
            scope = table_get(row, "Scope")
            authority = table_get(row, "Authority")
            evidence = table_get(row, "Evidence")
            if (
                authority_scope_matches(prefix, scope)
                and authority_value_is_ai_authorized(authority)
                and authority_evidence_is_specific(evidence)
            ):
                return True
    return False


def explicit_user_authorization_text(prefix: str, value: str) -> bool:
    if prefix == "PDEC-":
        patterns = [
            r"用户.{0,40}(?:同意|授权).{0,40}(?:AI\s*推荐决策|AI\s*按推荐方案|产品决策.*AI)",
            r"(?:user|human).{0,60}(?:approve|approved|authorize|authorized).{0,60}(?:AI|recommended decision|product decision)",
            r"同意\s*AI\s*推荐决策",
            r"授权\s*AI\s*按推荐方案(?:锁定)?",
            r"指定范围内的产品决策由\s*AI\s*按推荐方案锁定",
        ]
    elif prefix == "ADEC-":
        patterns = [
            r"用户.{0,40}(?:同意|授权).{0,40}(?:AI.*工程决策|工程决策.*AI|AIP.*推荐|当前推荐方案)",
            r"(?:user|human).{0,60}(?:approve|approved|authorize|authorized).{0,60}(?:AI|engineering decision|AIP recommendation)",
            r"明确授权\s*AI\s*做工程决策",
            r"授权\s*AI\s*做工程决策",
            r"同意当前(?:AIP|工程)?推荐方案",
        ]
    else:
        return False
    return any(re.search(pattern, value, re.IGNORECASE) for pattern in patterns)


def ai_decision_authorized_for(prefix: str, value: str) -> bool:
    return authority_table_authorizes_ai(prefix, value) or explicit_user_authorization_text(prefix, value)


def decision_doc_for_stage(change_dir: Path, stage: str) -> Path:
    stage_to_file = {
        "prd": "prd-decisions.md",
        "aip": "aip-decisions.md",
        "readiness": "aip-decisions.md",
        "design": "design-decisions.md",
        "archaeology": "archaeology-decisions.md",
        "migration": "migration-decisions.md",
        "frontend-contract": "frontend-decisions.md",
        "contract": "contract-decisions.md",
        "verification": "verification-decisions.md",
        "task-planning": "task-planning-decisions.md",
        "mock-acceptance": "mock-acceptance-decisions.md",
        "product-acceptance": "product-acceptance-decisions.md",
    }
    return change_dir / "decision-reviews" / stage_to_file.get(stage, f"{stage}-decisions.md")


def decision_ids_for_stage(stage: str, value: str) -> set[str]:
    found = set(DESIGN_DECISION_ID_RE.findall(value))
    if stage == "prd":
        return {item for item in found if item.startswith("PDEC-")}
    if stage in {"aip", "readiness"}:
        return {item for item in found if item.startswith("ADEC-")}
    return {
        item
        for item in found
        if not item.startswith("PDEC-") and not item.startswith("ADEC-")
    }


def has_human_decision_record(decision_id: str, decision_doc: str, interaction: str) -> bool:
    row_texts: list[str] = []
    for row in markdown_table_dicts(interaction):
        if decision_id in " ".join(row.values()):
            row_texts.append(" | ".join(row.values()))
    for row in markdown_table_dicts(decision_doc):
        if decision_id in " ".join(row.values()):
            row_texts.append(" | ".join(row.values()))
    detail_match = re.search(
        rf"^###\s+{re.escape(decision_id)}\b(?P<body>.*?)(?=^###\s+{DECISION_ID_PATTERN}\b|\Z)",
        decision_doc,
        re.MULTILINE | re.DOTALL,
    )
    if detail_match:
        row_texts.append(detail_match.group("body"))
    combined = "\n".join(row_texts)
    if not combined:
        return False
    return bool(
        HUMAN_DECISION_PROMPT_RE.search(combined)
        and HUMAN_DECISION_RESPONSE_RE.search(combined)
        and HUMAN_DECISION_STATUS_RE.search(combined)
        and HUMAN_DECISION_TIME_RE.search(combined)
    )


def validate_human_decision_records(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in HUMAN_DECISION_REQUIRED_STAGES and stage != "all":
        return errors
    combined = "\n".join(
        [
            read_optional(model.change_dir / "proposal.md"),
            read_optional(model.change_dir / "spec.md"),
            read_optional(model.change_dir / "plan.md"),
            read_optional(model.change_dir / "tasks.md"),
            read_optional(model.change_dir / "source-intake-ledger.md"),
        ]
    )
    interaction = first_markdown_section(combined, "User Decision Interaction", "用户决策交互")
    human_mode = human_decision_participation_enabled(combined + "\n" + flatten_text(model.workflow))
    if human_mode and not interaction:
        errors.append("human-decision-participation is enabled but User Decision Interaction ledger is missing")
    if interaction:
        required_columns = [
            "Stage",
            "Decision ID",
            "Decision key",
            "Prompt ID",
            "Prompt summary",
            "Recommended option",
            "Alternatives",
            "User response",
            "Final status",
            "Decided at",
        ]
        for col in required_columns:
            if col.lower() not in interaction.lower():
                errors.append(f"User Decision Interaction must include column {col}")
        if re.search(r"batch|批量|以上.*都|all agreed|all approved|一并确认", interaction, re.IGNORECASE):
            errors.append("User Decision Interaction must not close multiple decisions with a batched confirmation")
    stages = sorted(HUMAN_DECISION_REQUIRED_STAGES) if stage == "all" else [stage]
    stage_status = as_dict(model.workflow.get("stage_status"))
    for stage_name in stages:
        decision_doc_path = decision_doc_for_stage(model.change_dir, stage_name)
        decision_doc = read_optional(decision_doc_path)
        stage_text = "\n".join(
            [
                combined,
                decision_doc,
                read_optional(model.change_dir / "decision-reviews" / "decision-registry.md"),
                read_optional(model.change_dir / "decision-registry.md"),
            ]
        )
        prefixes = HUMAN_DECISION_DEFAULT_PREFIXES.get(stage_name, ())
        requires_human = human_mode or any(
            prefix and re.search(rf"\b{re.escape(prefix)}\d{{3}}\b", stage_text) and not ai_decision_authorized_for(prefix, stage_text)
            for prefix in prefixes
        )
        if not requires_human:
            continue
        decision_ids = decision_ids_for_stage(stage_name, stage_text)
        if not decision_ids:
            continue
        if stage_status.get(stage_name) in {"not_started", "not_applicable"} and stage != stage_name:
            continue
        if not interaction:
            errors.append(f"{stage_name}: requires human decision records but User Decision Interaction ledger is missing")
        if not decision_doc.strip():
            errors.append(f"{stage_name}: requires human decision records but {decision_doc_path.relative_to(model.change_dir)} is missing or empty")
            continue
        for decision_id in sorted(decision_ids):
            if prefixes and not any(decision_id.startswith(prefix) for prefix in prefixes) and not human_mode:
                continue
            if not has_human_decision_record(decision_id, decision_doc, interaction):
                errors.append(
                    f"{decision_id}: requires one-by-one Human Decision Prompt record with prompt, user response, final status, and decided-at timestamp"
                )
    return errors


def component_paths(value: Any) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for match in FRONTEND_COMPONENT_PATH_RE.finditer(flatten_text(value)):
        path = match.group(1).strip().strip("`").strip(",.;")
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def file_in_allowlist(path: str, allowlist: list[str]) -> bool:
    normalized = path.strip().strip("/")
    for raw in allowlist:
        pattern = str(raw).strip().strip("/")
        if not pattern:
            continue
        if pattern.endswith("/**") and normalized.startswith(pattern[:-3].rstrip("/") + "/"):
            return True
        if pattern.endswith("/") and normalized.startswith(pattern):
            return True
        if normalized == pattern or normalized.startswith(pattern.rstrip("/") + "/"):
            return True
    return False


def packet_file_allowlist(packet: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for row in as_list(packet.get("files_to_change")):
        row_dict = as_dict(row)
        path = text(row_dict.get("path") if row_dict else row)
        if path:
            paths.append(path)
    return paths


def frontend_task_ids(model: WorkflowModel) -> set[str]:
    ids: set[str] = set()
    for tid, raw_task in model.tasks.items():
        task = as_dict(raw_task)
        packet = as_dict(model.packets.get(tid))
        layer = text(task.get("layer")).lower().replace("_", "-")
        if layer in {"backend", "backend-service", "backend-domain", "backend-api", "backend-data", "backend-adapter", "backend-runtime", "backend-observability"}:
            continue
        if layer in MOCK_ACCEPTANCE_LAYER_TARGETS and MOCK_ACCEPTANCE_LAYER_TARGETS[layer] != "frontend":
            continue
        if layer == "frontend" or MOCK_ACCEPTANCE_LAYER_TARGETS.get(layer) == "frontend":
            ids.add(str(tid))
            continue
        text_payload = flatten_text([
            task.get("title"),
            task.get("primary_module"),
            task.get("files"),
            packet.get("title"),
            packet.get("primary_module"),
            packet.get("files_to_change"),
        ])
        if FRONTEND_TASK_RE.search(text_payload) or FRONTEND_FILE_RE.search(text_payload):
            ids.add(str(tid))
    return ids


def backend_task_ids(model: WorkflowModel) -> set[str]:
    ids: set[str] = set()
    frontend_ids = frontend_task_ids(model)
    for tid, raw_task in model.tasks.items():
        if str(tid) in frontend_ids:
            continue
        task = as_dict(raw_task)
        packet = as_dict(model.packets.get(tid))
        layer = text(task.get("layer")).lower().replace("_", "-")
        if layer in {"backend", "backend-service", "backend-domain", "backend-api", "backend-data", "backend-adapter", "backend-runtime", "backend-observability"}:
            ids.add(str(tid))
            continue
        if layer in MOCK_ACCEPTANCE_LAYER_TARGETS:
            if MOCK_ACCEPTANCE_LAYER_TARGETS[layer] == "backend":
                ids.add(str(tid))
            continue
        text_payload = flatten_text([
            task.get("title"),
            task.get("primary_module"),
            task.get("files"),
            packet.get("title"),
            packet.get("primary_module"),
            packet.get("module_responsibility"),
            packet.get("files_to_change"),
        ])
        if BACKEND_FILE_RE.search(text_payload) or re.search(
            r"\bbackend|后端|service|manager|controller|runtime|provider\b",
            text_payload,
            re.IGNORECASE,
        ):
            ids.add(str(tid))
    return ids


def mock_acceptance_task_target(model: WorkflowModel, task_id: str) -> str:
    """Return the mock acceptance layer owned by a task, if any.

    This is intentionally ownership-based. Ordinary backend tasks may mention
    runtime, provider, no-cloud, fixture, or repo-specific acceptance runtime semantics as downstream
    context; those words must not trigger the full mock acceptance execution
    ledger during pass-task. Only explicit mock acceptance owner tasks should.
    """
    task = as_dict(model.tasks.get(task_id))
    packet = as_dict(model.packets.get(task_id))
    explicit = text(
        task.get("mock_acceptance_target")
        or task.get("acceptance_target")
        or packet.get("mock_acceptance_target")
        or packet.get("acceptance_target")
    ).lower().replace("_", "-")
    if explicit in MOCK_ACCEPTANCE_TARGETS:
        return explicit
    if explicit in MOCK_ACCEPTANCE_LAYER_TARGETS:
        return MOCK_ACCEPTANCE_LAYER_TARGETS[explicit]
    layer = text(task.get("layer")).lower().replace("_", "-")
    if layer in MOCK_ACCEPTANCE_LAYER_TARGETS:
        return MOCK_ACCEPTANCE_LAYER_TARGETS[layer]
    title_payload = flatten_text([task.get("title"), task.get("primary_module"), packet.get("title"), packet.get("primary_module")]).lower()
    if re.search(r"\bbackend\s+(?:mock\s+)?matrix\b|\bmock[-_\s]?backend\b", title_payload):
        return "backend"
    if re.search(r"\bfrontend\s+action\s+(?:mock\s+)?matrix\b|\bmock[-_\s]?frontend\b", title_payload):
        return "frontend"
    if re.search(r"\brepresentative\s+acceptance\b|\bpackaged\s+cases?\b|\bpackaged\s+playground\b", title_payload):
        return "packaged"
    return ""


def issue_markdown_text(model: WorkflowModel, task_id: str) -> str:
    packet = as_dict(model.packets.get(task_id))
    issue_path = text(packet.get("issue_path")) or f"atomic-issues/{task_id}.md"
    return read_optional(model.change_dir / issue_path)


def packet_is_frontend(packet: dict[str, Any]) -> bool:
    payload = flatten_text(
        [
            packet.get("title"),
            packet.get("primary_module"),
            packet.get("files_to_change"),
            packet.get("frontend_user_task"),
            packet.get("action_route_component"),
        ]
    )
    return bool(FRONTEND_TASK_RE.search(payload) or FRONTEND_FILE_RE.search(payload))


def packet_is_backend(packet: dict[str, Any]) -> bool:
    if packet_is_frontend(packet):
        return False
    payload = flatten_text(
        [
            packet.get("title"),
            packet.get("primary_module"),
            packet.get("module_responsibility"),
            packet.get("files_to_change"),
        ]
    )
    return bool(BACKEND_FILE_RE.search(payload) or re.search(r"\bbackend|后端|service|manager|controller|runtime|provider\b", payload, re.IGNORECASE))


def markdown_has_columns(markdown: str, columns: list[str]) -> bool:
    normalized = markdown.lower()
    return all(column.lower() in normalized for column in columns)


def markdown_has_meaningful_rows(markdown: str) -> bool:
    placeholders = re.compile(r"^(?:|n/a|none|tbd|todo|unknown|<.*>|\s+)$", re.IGNORECASE)
    for row in markdown_table_rows(markdown):
        if not row:
            continue
        first = row[0].strip().lower()
        if first in {
            "page/route",
            "action",
            "action id",
            "form/step",
            "surface/action",
            "page/action",
            "user task id",
            "contract",
            "interaction / contract",
            "edge id",
            "txxx",
            "candidate rows",
        }:
            continue
        meaningful = [cell for cell in row if not placeholders.fullmatch(cell.strip())]
        if len(meaningful) >= 2:
            return True
    return False


def validate_mechanism_design_closure(markdown: str, artifact: str) -> list[str]:
    errors: list[str] = []
    body = first_markdown_section(markdown, "Mechanism-Level Design Closure Matrix", "机制级设计闭合矩阵")
    if not body:
        errors.append(f"{artifact}: missing Mechanism-Level Design Closure Matrix")
        return errors
    columns = [
        "Design question",
        "Selected mechanism",
        "Rejected alternatives",
        "Current code evidence",
        "External fact",
        "Interface impact",
        "State/runtime impact",
        "Failure behavior",
        "Verification",
        "Downstream C/VER",
    ]
    if not markdown_has_columns(body, columns):
        errors.append(f"{artifact}: Mechanism-Level Design Closure Matrix must include columns {', '.join(columns)}")
    rows = markdown_table_dicts(body)
    if not rows:
        errors.append(f"{artifact}: Mechanism-Level Design Closure Matrix must include concrete rows")
        return errors
    weak_question_re = re.compile(r"^(?:support|支持|实现|enable|ability|capability|能力|方案|design)\b|^(?:ASG|K8s|HPA|autoscaling|runtime)$", re.IGNORECASE)
    blocked_re = re.compile(r"\b(?:TBD|TODO|unknown-blocking|open|blocked|后续|待定|待确认|再决定|task-planning)\b", re.IGNORECASE)
    operation_re = re.compile(
        r"\b(create|update|delete|readback|validate|render|submit|scale|autoscaling|policy|metrics?|logs?|runtime|"
        r"materiali[sz]e|provision|cleanup|protect|migrate|rollback|compatib|failure|permission|event|progress)\b"
        r"|创建|更新|删除|读回|校验|提交|扩缩|策略|指标|日志|运行时|物化|清理|保护|迁移|回滚|兼容|失败|权限|事件|进度",
        re.IGNORECASE,
    )
    for row in rows:
        joined = " | ".join(row.values())
        if blocked_re.search(joined):
            errors.append(f"{artifact}: Mechanism-Level Design Closure Matrix contains unresolved row: {joined}")
        question = table_get(row, "Design question")
        if len(question) < 12 or weak_question_re.search(question) or not operation_re.search(question):
            errors.append(f"{artifact}: design question is not operation/surface-level: {question or '<missing>'}")
        required_values = [
            ("Selected mechanism", 16),
            ("Rejected alternatives", 12),
            ("Current code evidence", 8),
            ("Interface impact", 8),
            ("State/runtime impact", 8),
            ("Failure behavior", 8),
            ("Verification", 5),
            ("Downstream C/VER", 3),
        ]
        for column, min_len in required_values:
            if len(table_get(row, column)) < min_len:
                errors.append(f"{artifact}: Mechanism-Level Design Closure row lacks {column}: {joined}")
        evidence = table_get(row, "Current code evidence")
        if evidence and not re.search(r"(?:/|\\|\.java|\.ts|\.tsx|\.go|\.py|\.yaml|\.yml|\.tf|rg |grep |mvn |pnpm |npm |curl )", evidence):
            errors.append(f"{artifact}: Current code evidence must include path or command: {joined}")
        if re.search(
            r"\b(?:cloud|AWS|ASG|K8s|Kubernetes|HPA|IAM|storage|SDK|provider|mock|no-cloud|external|third[- ]party|"
            r"autoscaling policy|CloudWatch|Prometheus|S3|EBS|EC2|VPC|Subnet|Security\s*Group)\b",
            joined,
            re.IGNORECASE,
        ):
            ext = table_get(row, "External fact / constraint", "External fact", "constraint")
            if not EXTERNAL_DESIGN_OBJECT_ID_RE.search(ext) and not re.search(r"\blocked\s+N/A\b|不适用|无外部|not applicable|N/A", ext, re.IGNORECASE):
                errors.append(f"{artifact}: external mechanism row must reference MECH/FACT/CONSTRAINT ID: {joined}")
        if not re.search(r"\b(?:C|VER)-\d{3}\b", table_get(row, "Downstream C/VER")):
            errors.append(f"{artifact}: Mechanism-Level Design Closure row must map to downstream C/VER: {joined}")
    return errors


def validate_aip_narrative_materialization(markdown: str, design_sources: str, artifact: str) -> list[str]:
    errors: list[str] = []
    body = first_markdown_section(markdown, "AIP Narrative Materialization Gate", "AIP 正文物化门禁")
    if not body:
        errors.append(f"{artifact}: missing AIP Narrative Materialization Gate")
        return errors
    columns = ["Source design object", "Must appear in AIP section", "Narrative requirement", "Status"]
    if not markdown_has_columns(body, columns):
        errors.append(f"{artifact}: AIP Narrative Materialization Gate must include columns {', '.join(columns)}")
    rows = markdown_table_dicts(body)
    if not rows:
        errors.append(f"{artifact}: AIP Narrative Materialization Gate must include concrete rows")
        return errors
    aip_text_without_gate = markdown.replace(body, "")
    for row in rows:
        joined = " | ".join(row.values())
        row_ids = design_object_ids(table_get(row, "Source design object") or joined)
        status = table_get(row, "Status").lower()
        if not re.search(r"\b(?:materialized|locked n/a|n/a|not applicable|不适用|blocked)\b", status, re.IGNORECASE):
            errors.append(f"{artifact}: AIP Narrative Materialization Gate row has invalid status: {joined}")
        if re.search(r"\bblocked\b|阻塞", status, re.IGNORECASE):
            errors.append(f"{artifact}: AIP Narrative Materialization Gate contains blocked row: {joined}")
        if len(table_get(row, "Must appear in AIP section")) < 4:
            errors.append(f"{artifact}: narrative materialization row lacks AIP section: {joined}")
        if len(table_get(row, "Narrative requirement")) < 16:
            errors.append(f"{artifact}: narrative materialization row lacks concrete narrative requirement: {joined}")
        if re.search(r"\bmaterialized\b", status, re.IGNORECASE):
            target_section = aip_sections_for_reference(markdown, table_get(row, "Must appear in AIP section"))
            search_scope = target_section or aip_text_without_gate
            for object_id in sorted(row_ids):
                if object_id not in search_scope:
                    errors.append(
                        f"{artifact}: design object {object_id} is marked materialized but is absent from the referenced AIP section body"
                    )
    required_ids = design_object_ids(design_sources)
    for object_id in sorted(required_ids):
        if object_id not in aip_text_without_gate:
            errors.append(f"{artifact}: design object {object_id} from AIP/design artifacts is not materialized in AIP section body")
    for evidence in current_architecture_evidence_values(design_sources):
        if not materialization_contains_evidence(aip_text_without_gate, evidence):
            errors.append(f"{artifact}: Current Architecture evidence is not materialized in AIP section body: {evidence}")
    return errors


def implementation_affecting_mechanism_ids(markdown: str) -> set[str]:
    ids_found = set(MECHANISM_MODEL_ID_RE.findall(markdown))
    locked_na_rows: set[str] = set()
    for row in markdown_table_dicts(markdown):
        joined = " | ".join(row.values())
        row_id = primary_mechanism_model_row_id(row)
        if row_id and re.search(r"\blocked\s+N/A\b|locked N/A|not applicable|不适用", joined, re.IGNORECASE):
            locked_na_rows.add(row_id)
    return ids_found - locked_na_rows


def primary_mechanism_model_row_id(row: dict[str, str]) -> str:
    for label in [
        "Sequence row",
        "Parameter row",
        "Event row",
        "Runtime row",
        "Resource row",
        "Failure row",
        "Interface row",
        "Mechanism row",
    ]:
        value = table_get(row, label)
        match = MECHANISM_MODEL_ID_RE.search(value)
        if match:
            return match.group(0)
    return ""


def validate_mechanism_design_model(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"aip", "readiness", "design", "archaeology", "contract", "frontend-contract", "verification", "task-planning", "pre-execution", "acceptance", "all"}:
        return errors
    body = read_optional(model.change_dir / "mechanism-design-model.md")
    research = read_optional(model.change_dir / "external-capability-research.md")
    proposal = read_optional(model.change_dir / "proposal.md")
    spec = read_optional(model.change_dir / "spec.md")
    plan = read_optional(model.change_dir / "plan.md")
    tasks_md = read_optional(model.change_dir / "tasks.md")
    combined = "\n".join(
        [
            proposal,
            spec,
            plan,
            tasks_md,
            read_optional(model.change_dir / "aip.md"),
            read_optional(model.change_dir / "external-capability-research.md"),
            read_optional(model.change_dir / "decision-surface-discovery.md"),
        ]
    )
    has_trigger = bool(
        EXTERNAL_SIDE_EFFECT_SIGNAL_RE.search(combined)
        or RUNTIME_MATERIALIZATION_SIGNAL_RE.search(combined)
        or re.search(
            r"\b(?:ASG|HPA|autoscaling|auto[- ]?scaling|metrics source|progress|change|event|resource lifecycle|failure consistency)\b"
            r"|自动扩缩|指标来源|进度|变更|事件|资源生命周期|失败一致性",
            combined,
            re.IGNORECASE,
        )
    )
    path = model.change_dir / "mechanism-design-model.md"
    if has_trigger and not body.strip():
        errors.append("mechanism-design: mechanism-level implementation signal exists but mechanism-design-model.md is missing or empty")
        return errors
    if has_trigger and research.strip():
        explanation = first_markdown_section(research, "External Mechanism Explanation Matrix")
        if not explanation:
            errors.append("external-research: missing External Mechanism Explanation Matrix for mechanism-level external capability")
        elif not markdown_has_columns(
            explanation,
            [
                "Mechanism ID",
                "Mechanism principle",
                "Key API/resource/metric",
                "Key parameters and meanings",
                "Lifecycle create/update/delete/prune behavior",
                "Failure/permission/metric semantics",
                "Required mechanism-design row",
            ],
        ):
            errors.append("external-research: External Mechanism Explanation Matrix must include mechanism principle, API/resource/metric, parameter meanings, lifecycle behavior, failure semantics, and required mechanism-design row")
        else:
            for row in markdown_table_dicts(explanation):
                mechanism_id = table_get(row, "Mechanism ID")
                joined = " | ".join(row.values())
                if MECHANISM_UNRESOLVED_RE.search(joined):
                    errors.append(f"external-research: External Mechanism Explanation Matrix contains unresolved row: {joined}")
                if MECHANISM_PLACEHOLDER_RE.search(joined):
                    errors.append(f"external-research: External Mechanism Explanation Matrix contains template placeholder/generic mechanism text: {joined}")
                for label, min_len in [
                    ("Mechanism principle", 24),
                    ("Key API/resource/metric", 8),
                    ("Key parameters and meanings", 20),
                    ("Lifecycle create/update/delete/prune behavior", 16),
                    ("Failure/permission/metric semantics", 16),
                    ("Required mechanism-design row", 8),
                ]:
                    if len(table_get(row, label)) < min_len:
                        errors.append(f"external-research: mechanism explanation {mechanism_id or '<missing>'} {label} is too thin")
                if not MECHANISM_MODEL_ID_RE.search(table_get(row, "Required mechanism-design row")):
                    errors.append(f"external-research: mechanism explanation {mechanism_id or '<missing>'} must map to mechanism-design-model.md row")
    if not body.strip():
        return errors

    required_sections = {
        "Mechanism Row Inventory": [
            "Mechanism row",
            "Operation / surface",
            "Selected production mechanism",
            "Canonical owner",
            "Interface fields",
            "State/resource mutation",
            "Failure/consistency/idempotency",
            "Verification",
            "Downstream C/VER",
        ],
        "Operation Sequence Model": [
            "Sequence row",
            "Mechanism row",
            "Operation",
            "Ordered production steps",
            "External calls/resources",
            "State writes",
            "Events/progress emitted",
            "Failure branches",
            "Verification",
        ],
        "External API Parameter Map": [
            "Parameter row",
            "External system/API/resource",
            "Parameter / option",
            "AutoMQ source field",
            "Non-equivalent semantic",
            "Permission/metric/failure behavior",
            "Verification",
        ],
        "Event State Model": [
            "Event row",
            "Operation",
            "Event / step",
            "Producer",
            "State owner",
            "Terminal?",
            "Fields",
            "Consumer surfaces",
            "Failure reason / status",
            "Verification",
        ],
        "Runtime Materialization Model": [
            "Runtime row",
            "Mode / runtime",
            "Existing mode baseline",
            "New mode materialization design",
            "Artifact/config/plugin/secret/bootstrap carrier",
            "Production owner",
            "Readiness/readback",
            "Failure behavior",
            "Verification",
        ],
        "Resource Lifecycle Model": [
            "Resource row",
            "Resource",
            "Selection/provenance",
            "Create timing",
            "Update rule",
            "Delete cleanup/protect rule",
            "Identity/readback owner",
            "Partial failure residual state",
            "Verification",
        ],
        "Failure Consistency Model": [
            "Failure row",
            "Operation",
            "Failure point",
            "DB/state before external side effect",
            "External side effect state",
            "User-visible state/event",
            "Retry/rollback/cleanup rule",
            "Consistency invariant",
            "Verification",
        ],
        "Module Interface Model": [
            "Interface row",
            "Producer module",
            "Consumer module",
            "Method/API/event/resource surface",
            "Request fields",
            "Response/readback fields",
            "Error/warning fields",
            "Timing/ordering",
            "Verification",
        ],
    }
    for section_name, columns in required_sections.items():
        section_body = first_markdown_section(body, section_name)
        if not section_body:
            errors.append(f"mechanism-design: missing {section_name}")
            continue
        if not markdown_has_columns(section_body, columns):
            errors.append(f"mechanism-design: {section_name} must include columns {', '.join(columns)}")
        rows = markdown_table_dicts(section_body)
        if not rows:
            errors.append(f"mechanism-design: {section_name} must include concrete rows or locked N/A rows")
            continue
        for row in rows:
            joined = " | ".join(row.values())
            if MECHANISM_UNRESOLVED_RE.search(joined):
                errors.append(f"mechanism-design: {section_name} contains unresolved implementation decision: {joined}")
            if MECHANISM_PLACEHOLDER_RE.search(joined):
                errors.append(f"mechanism-design: {section_name} contains template placeholder/generic mechanism text: {joined}")

    mechanism_ids = set(re.findall(r"\bMECH-\d{3}\b", body))
    for mech_id in sorted(mechanism_ids):
        if len(re.findall(rf"\b{re.escape(mech_id)}\b", body)) < 3:
            errors.append(f"mechanism-design: {mech_id} is not propagated into design model detail rows")

    weak_re = re.compile(
        r"^\s*(?:support|支持|实现|enable|reuse|复用|use existing|same as existing|create resource|record event|provider call|mode-specific|能力|资源创建|记录事件|调用provider)\s*$",
        re.IGNORECASE,
    )
    for row in markdown_table_dicts(first_markdown_section(body, "Mechanism Row Inventory")):
        row_id = table_get(row, "Mechanism row")
        joined = " | ".join(row.values())
        if not re.search(r"\bMECH-\d{3}\b", row_id):
            errors.append(f"mechanism-design: Mechanism Row Inventory row must use MECH-xxx id: {joined}")
        operation = table_get(row, "Operation / surface")
        if not re.search(r"\b(create|update|delete|readback|validate|submit|scale|autoscaling|policy|metrics?|logs?|runtime|materiali[sz]e|cleanup|protect|failure|event|progress)\b|创建|更新|删除|读回|校验|提交|扩缩|策略|指标|日志|运行时|物化|清理|保护|失败|事件|进度", operation, re.IGNORECASE):
            errors.append(f"mechanism-design: {row_id or '<missing>'} operation/surface is not concrete: {operation or '<missing>'}")
        for column in [
            "Selected production mechanism",
            "Current code evidence",
            "Canonical owner",
            "Interface fields",
            "State/resource mutation",
            "Failure/consistency/idempotency",
            "Verification",
            "Downstream C/VER",
        ]:
            value = table_get(row, column)
            if len(value) < 8 or weak_re.fullmatch(value.strip()):
                errors.append(f"mechanism-design: {row_id or '<missing>'} has weak {column}: {value or '<empty>'}")
        evidence = table_get(row, "Current code evidence")
        if evidence and not re.search(r"(?:/|\\|\.java|\.ts|\.tsx|\.go|\.py|\.yaml|\.yml|\.tf|rg |grep |mvn |pnpm |npm |curl )", evidence):
            errors.append(f"mechanism-design: {row_id or '<missing>'} Current code evidence must include path or command: {evidence}")
        if not re.search(r"\b(?:C|VER)-\d{3}\b", table_get(row, "Downstream C/VER")):
            errors.append(f"mechanism-design: {row_id or '<missing>'} must map to downstream C/VER")

    if stage in {"contract", "verification", "task-planning", "pre-execution", "acceptance", "all"}:
        downstream = "\n".join(
            [
                plan,
                tasks_md,
                flatten_text(model.contracts_doc),
                flatten_text(model.verification_doc),
                read_optional(model.change_dir / "atomic-task-decomposition.md"),
                read_optional(model.change_dir / "atomic-issue-packets.yaml"),
            ]
        )
        for model_id in sorted(implementation_affecting_mechanism_ids(body)):
            if not re.search(rf"\b{re.escape(model_id)}\b", downstream):
                errors.append(f"mechanism-design: row {model_id} is not consumed by contract/verification/task artifacts")
    if stage in {"task-planning", "pre-execution", "acceptance", "all"}:
        decomposition = read_optional(model.change_dir / "atomic-task-decomposition.md")
        if "Mechanism Row To Task Map" not in decomposition:
            errors.append("mechanism-design: atomic-task-decomposition.md missing Mechanism Row To Task Map")
        packets = read_optional(model.change_dir / "atomic-issue-packets.yaml")
        for required in ["MECH-", "OPSEQ-", "EXTAPI-", "EVT-", "RMM-", "RLM-", "FCM-", "MIM-"]:
            if required in body and required not in packets:
                errors.append(f"mechanism-design: atomic-issue-packets.yaml must carry {required.rstrip('-')} semantics")
    return errors


def validate_frontend_task_consumption(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"task-planning", "pre-execution", "all"}:
        return errors
    if not model.packets:
        return errors

    route_rows = markdown_table_dicts(read_optional(model.change_dir / "frontend-route-component-matrix.md"))
    field_rows = markdown_table_dicts(read_optional(model.change_dir / "frontend-mode-field-display-matrix.md"))
    form_rows = markdown_table_dicts(read_optional(model.change_dir / "frontend-form-state-matrix.md"))
    negative_rows = markdown_table_dicts(read_optional(model.change_dir / "frontend-mode-leakage-negative-matrix.md"))
    payload_rows = markdown_table_dicts(read_optional(model.change_dir / "frontend-api-payload-contract-matrix.md"))
    browser_rows = markdown_table_dicts(read_optional(model.change_dir / "frontend-browser-verification-matrix.md"))
    reference_rows = markdown_table_dicts(read_optional(model.change_dir / "frontend-reference-pattern-matrix.md"))

    action_to_browser = {
        table_get(row, "Action ID"): row
        for row in browser_rows
        if table_get(row, "Action ID")
    }
    frontend_ids = frontend_task_ids(model)

    for row in reference_rows:
        reference_id = table_get(row, "Reference ID")
        if not reference_id:
            continue
        owner = table_get(row, "Owner issue", "Owning issue")
        if not re.match(r"T\d{3}", owner):
            errors.append(f"frontend-contract: reference pattern {reference_id} lacks concrete Owner issue")
            continue
        if owner not in model.tasks:
            errors.append(f"frontend-contract: reference pattern {reference_id} owner {owner} is missing from task-dag.yaml")
            continue
        if owner not in frontend_ids:
            errors.append(f"frontend-contract: reference pattern {reference_id} owner {owner} is not a frontend packet/task")
        packet = as_dict(model.packets.get(owner))
        reference_section_text = flatten_text(packet.get("reference_ui_patterns"))
        for required in [
            reference_id,
            table_get(row, "Target surface/action"),
            table_get(row, "Reference file/component"),
            table_get(row, "Must reuse/adapt"),
            table_get(row, "Visual/layout obligation"),
            table_get(row, "Interaction/state obligation"),
            table_get(row, "Browser/visual proof"),
        ]:
            required_text = text(required)
            if required_text and not semantic_payload_copied(required_text, reference_section_text):
                errors.append(
                    f"frontend-contract: reference pattern {reference_id} not copied into owner packet "
                    f"{owner}.reference_ui_patterns: {required_text}. Source Context or semantic_carriers alone do not count"
                )
        ref_paths = component_paths(table_get(row, "Reference file/component"))
        if not ref_paths:
            errors.append(f"frontend-contract: reference pattern {reference_id} must name concrete reference page/component file")
        visual_text = flatten_text([table_get(row, "Must reuse/adapt"), table_get(row, "Visual/layout obligation")])
        if not re.search(r"layout|section|order|group|spacing|component|control|review|summary|table|tab|布局|分组|顺序|组件|控件|预览|摘要|表格", visual_text, re.IGNORECASE):
            errors.append(f"frontend-contract: reference pattern {reference_id} must specify visual/layout/component obligations, not only data fields")
        if not STRONG_FRONTEND_PROOF_RE.search(table_get(row, "Browser/visual proof")):
            errors.append(f"frontend-contract: reference pattern {reference_id} lacks browser/screenshot/DOM/trace visual proof")

    for row in route_rows:
        action_id = table_get(row, "Action ID")
        if not re.match(r"UI-ACT-\d+", action_id):
            continue
        owner = table_get(row, "Owner issue", "Owning issue")
        if not re.match(r"T\d{3}", owner):
            errors.append(f"frontend-contract: {action_id} lacks concrete Owner issue in frontend-route-component-matrix.md")
            continue
        if owner not in model.tasks:
            errors.append(f"frontend-contract: {action_id} owner {owner} is missing from task-dag.yaml")
            continue
        if owner not in frontend_ids:
            errors.append(f"frontend-contract: {action_id} owner {owner} is not a frontend packet/task")
        packet = as_dict(model.packets.get(owner))
        action_section_text = flatten_text(packet.get("action_route_component"))
        if action_id not in action_section_text:
            errors.append(
                f"frontend-contract: {action_id} is not copied into owner packet {owner}.action_route_component; "
                "Source Context or semantic_carriers alone do not count as matrix consumption"
            )
        declared_files = task_files(as_dict(model.tasks.get(owner))) + packet_file_allowlist(packet)
        for label, value in [
            ("source component", table_get(row, "Source component")),
            ("landing component/file", table_get(row, "Landing component/file")),
            ("router definition", table_get(row, "Router definition")),
            ("click handler / route builder", table_get(row, "Click handler / route builder", "Click handler")),
        ]:
            paths = component_paths(value)
            if label in {"source component", "landing component/file"} and not paths:
                errors.append(f"frontend-contract: {action_id} {label} must name concrete file path")
            if label == "router definition" and not paths and not re.search(
                r"file[- ]?based router|landing component owns route|Next pages router|Next app router|文件路由",
                value,
                re.IGNORECASE,
            ):
                errors.append(f"frontend-contract: {action_id} router definition must name file or explicit file-based route ownership")
            for path in paths:
                if not file_in_allowlist(path, declared_files):
                    errors.append(
                        f"frontend-contract: {action_id} {label} {path} is not in owner {owner} task files/files_to_change"
                    )
        browser = action_to_browser.get(action_id)
        if not browser:
            errors.append(f"frontend-contract: {action_id} lacks row-level browser verification in frontend-browser-verification-matrix.md")
        else:
            browser_text = flatten_text(browser)
            if NOT_RUN_RE.search(browser_text):
                errors.append(f"frontend-contract: {action_id} browser verification is marked not-run/deferred in planning matrix")
            if not STRONG_FRONTEND_PROOF_RE.search(browser_text):
                errors.append(f"frontend-contract: {action_id} browser verification must include click/network/DOM/screenshot-or-trace proof")

    for row in field_rows:
        surface = table_get(row, "Surface")
        owner = table_get(row, "Owner issue", "Owning issue")
        if not surface:
            continue
        if not re.match(r"T\d{3}", owner):
            errors.append(f"frontend-contract: field display surface {surface} lacks Owner issue")
            continue
        packet = as_dict(model.packets.get(owner))
        field_section_text = flatten_text(packet.get("mode_field_display_matrix") or packet.get("field_display_matrix"))
        for required in [surface, table_get(row, "Must show"), table_get(row, "Must hide"), table_get(row, "Assertion")]:
            required_text = text(required)
            if required_text and not semantic_payload_copied(required_text, field_section_text):
                errors.append(
                    f"frontend-contract: field display surface {surface} not fully copied into owner packet "
                    f"{owner}.mode_field_display_matrix: {required_text}. Source Context or semantic_carriers alone do not count"
                )

    for row in form_rows:
        form = table_get(row, "Form/step")
        if not form:
            continue
        owners = {
            table_get(field_row, "Owner issue")
            for field_row in field_rows
            if table_get(field_row, "Owner issue")
            and (
                table_get(row, "Mode/state") in table_get(field_row, "Mode/state")
                or table_get(field_row, "Surface").split("/")[0].strip().lower() in form.lower()
            )
        }
        if not owners:
            owners = frontend_ids
        matched = False
        for owner in owners:
            packet = as_dict(model.packets.get(owner))
            form_section_text = flatten_text(packet.get("form_state_matrix"))
            required_values = [
                form,
                table_get(row, "Active fields"),
                table_get(row, "Inactive/hidden fields"),
                table_get(row, "Validation trigger"),
                table_get(row, "Submit participation"),
            ]
            if all(
                not text(value) or semantic_payload_copied(text(value), form_section_text)
                for value in required_values
            ):
                matched = True
                break
        if not matched:
            errors.append(
                f"frontend-contract: form state row {form} is not copied into any frontend owner packet.form_state_matrix; "
                "Source Context or semantic_carriers alone do not count"
            )

    for row in negative_rows:
        surface = table_get(row, "Surface/action")
        if not surface:
            continue
        owner = table_get(row, "Owner issue", "Owning issue")
        if not re.match(r"T\d{3}", owner):
            errors.append(f"frontend-contract: negative leakage row {surface} lacks Owner issue")
            continue
        packet = as_dict(model.packets.get(owner))
        negative_section_text = flatten_text(
            [packet.get("mode_negative_assertions"), as_dict(packet.get("browser_verification")).get("negative_assertions")]
        )
        for required in [
            surface,
            table_get(row, "Mode/state"),
            table_get(row, "Forbidden DOM/text"),
            table_get(row, "Forbidden payload fields"),
            table_get(row, "Forbidden route/API"),
            table_get(row, "Assertion method"),
        ]:
            required_text = text(required)
            if required_text and not semantic_payload_copied(required_text, negative_section_text):
                errors.append(
                    f"frontend-contract: negative leakage row {surface} not copied into owner packet "
                    f"{owner}.mode_negative_assertions/browser_verification.negative_assertions: {required_text}. "
                    "Source Context or semantic_carriers alone do not count"
                )

    for row in payload_rows:
        action_id = table_get(row, "Action ID")
        if not action_id or re.fullmatch(r"(?:N/A|not applicable|不适用)", action_id.strip(), re.IGNORECASE):
            continue
        owner = table_get(row, "Owner issue", "Owning issue")
        if not re.match(r"T\d{3}", owner):
            errors.append(f"frontend-contract: API payload row {action_id} lacks concrete Owner issue")
            continue
        if owner not in model.tasks:
            errors.append(f"frontend-contract: API payload row {action_id} owner {owner} is missing from task-dag.yaml")
            continue
        packet = as_dict(model.packets.get(owner))
        payload_section_text = flatten_text(
            [
                packet.get("api_payload_contract_matrix"),
                as_dict(packet.get("browser_verification")).get("network_assertions"),
                packet.get("verification"),
            ]
        )
        for required in [
            action_id,
            table_get(row, "Method/path"),
            table_get(row, "Request body canonical path"),
            table_get(row, "Allowed keys"),
            table_get(row, "Forbidden keys / semantic aliases"),
            table_get(row, "Required/nullable/default/derived rule"),
            table_get(row, "Legacy compatibility rule"),
            table_get(row, "Network exact-key assertion"),
        ]:
            required_text = text(required)
            if required_text and not semantic_payload_copied(required_text, payload_section_text):
                errors.append(
                    f"frontend-contract: API payload row {action_id} not copied into owner packet "
                    f"{owner}.api_payload_contract_matrix/browser_verification.network_assertions: {required_text}. "
                    "mode leakage assertions alone do not count as exact wire-shape consumption"
                )
        if not re.search(r"\bObject\.keys|exact|keys?\(|schema|snapshot|request|network|body|字段|精确|键\b", table_get(row, "Network exact-key assertion"), re.IGNORECASE):
            errors.append(f"frontend-contract: API payload row {action_id} lacks executable exact-key assertion")

    for row in browser_rows:
        action_id = table_get(row, "Action ID")
        if not re.match(r"UI-ACT-\d+", action_id):
            continue
        owner = ""
        for route_row in route_rows:
            if table_get(route_row, "Action ID") == action_id:
                owner = table_get(route_row, "Owner issue", "Owning issue")
                break
        if not re.match(r"T\d{3}", owner):
            errors.append(f"frontend-contract: browser verification row {action_id} has no owner from frontend-route-component-matrix.md")
            continue
        packet = as_dict(model.packets.get(owner))
        browser_section_text = flatten_text(packet.get("browser_verification"))
        for required in [
            action_id,
            table_get(row, "User task ID"),
            table_get(row, "Browser steps"),
            table_get(row, "Network assertions"),
            table_get(row, "DOM assertions"),
            table_get(row, "Screenshot/trace"),
        ]:
            required_text = text(required)
            if required_text and not semantic_payload_copied(required_text, browser_section_text):
                errors.append(
                    f"frontend-contract: browser verification row {action_id} not copied into owner packet "
                    f"{owner}.browser_verification: {required_text}. Source Context or semantic_carriers alone do not count"
                )
    return errors


def validate_contract_matrix_artifacts(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"contract", "verification", "task-planning", "pre-execution", "all"}:
        return errors
    combined = flatten_text([model.contracts_doc, model.contracts, model.dag_doc, model.packet_doc])
    has_contract_signal = bool(model.contracts or re.search(r"\bC-\d{3}\b|Module Contract Graph|Provider/Consumer|跨模块|契约", combined, re.IGNORECASE))
    if not has_contract_signal:
        return errors
    for rel, columns in REQUIRED_CONTRACT_MATRIX_FILES.items():
        path = model.change_dir / rel
        body = read_optional(path)
        if not body.strip():
            errors.append(f"contract: required artifact {rel} is missing or empty")
            continue
        if not markdown_has_columns(body, columns):
            errors.append(f"contract: {rel} must include columns {', '.join(columns)}")
        if not markdown_has_meaningful_rows(body):
            errors.append(f"contract: {rel} must include at least one meaningful data row or locked N/A row")
        if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
            errors.append(f"contract: {rel} contains unresolved TBD/TODO/unknown value")

    plan = read_optional(model.change_dir / "plan.md")
    executable = first_markdown_section(
        plan,
        "Contract Executable Obligation Matrix",
        "Contract Executable Obligations",
        "契约可执行子义务矩阵",
    )
    if not executable:
        errors.append("contract: plan.md missing Contract Executable Obligation Matrix")
    else:
        if not (
            markdown_has_columns(executable, CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS)
            or markdown_has_columns(executable, LEGACY_CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS)
        ):
            errors.append(
                "contract: Contract Executable Obligation Matrix must include columns "
                + ", ".join(CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS)
            )
        errors.extend(
            markdown_table_column_count_errors(
                executable,
                CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS,
                "contract: plan.md Contract Executable Obligation Matrix",
            )
        )
        if re.search(r"\b(TBD|TODO|unknown|待确认|未知|blocked)\b", executable, re.IGNORECASE):
            errors.append("contract: Contract Executable Obligation Matrix contains unresolved TBD/TODO/unknown/blocked value")
        obligation_rows = markdown_table_dicts(executable)
        active_contract_ids = {
            cid for cid, raw_contract in model.contracts.items()
            if as_dict(raw_contract).get("status") not in {"superseded", "not_applicable", "locked-na"}
        }
        source_contract_ids = active_contract_ids or contract_ids_from_text(
            read_optional(model.change_dir / "contracts.yaml")
            + "\n"
            + first_markdown_section(plan, "Module Contract Graph", "模块契约图")
            + "\n"
            + first_markdown_section(
                plan,
                "Contract Materialization Source Matrix",
                "Contract Materialization Matrix",
                "契约物化来源矩阵",
            )
        )
        if source_contract_ids and not obligation_rows:
            errors.append("contract: Contract Executable Obligation Matrix has no data rows")
        for cid in sorted(source_contract_ids):
            cid_rows = [row for row in obligation_rows if cid in flatten_text(row)]
            if not cid_rows:
                errors.append(f"contract: {cid} missing executable sub-obligation rows")
                continue
            for row in cid_rows:
                for detail in executable_obligation_column_drift_errors(row):
                    errors.append(f"contract: {cid} executable obligation row has column drift: {detail}")
                if executable_obligation_row_too_thin(row):
                    errors.append(f"contract: {cid} executable obligation row is too thin/generic: {flatten_text(row)}")
                for detail in executable_obligation_row_granularity_errors(row):
                    errors.append(f"contract: {cid} executable obligation row is too coarse: {detail}")
            for label in [
                "Provider guarantee",
                "Consumer assumption",
                "Failure / timing detail",
                "State/resource owner",
                "Verification proof",
            ]:
                if not any(table_get(row, label) and not locked_na(table_get(row, label)) for row in cid_rows):
                    errors.append(f"contract: {cid} executable obligations missing {label}")
        if is_generic_packet_text(flatten_text(obligation_rows)):
            errors.append("contract: Contract Executable Obligation Matrix contains generic placeholder text")
        errors.extend(validate_specialized_rows_in_contract_obligations(model.change_dir, flatten_text(obligation_rows)))

    for cid, raw_contract in model.contracts.items():
        contract = as_dict(raw_contract)
        if contract.get("external_provider") is True or contract.get("status") in {"superseded", "not_applicable", "locked-na"}:
            continue
        provider_module = text(contract.get("provider_module"))
        if contract_provider_module_is_multi_owner(provider_module):
            errors.append(
                f"contract: {cid} provider_module must be owner-single, got {provider_module}; "
                "split semantic provider obligations or keep the coarse C-xxx as a composition index without multi-owner provider_module"
            )
        for raw_row in as_list(contract.get("executable_obligations") or contract.get("obligations")):
            row = normalize_contract_obligation_row(str(cid), as_dict(raw_row))
            if obligation_row_locked_na(row):
                continue
            obligation_id = table_get(row, "Sub-obligation ID")
            if not table_get(row, "Edge"):
                errors.append(
                    f"contract: {cid} executable_obligations[{obligation_id or '<missing>'}] missing edge; "
                    "contracts.yaml must be isomorphic with Markdown Contract Executable Obligation Matrix"
                )

    if stage not in {"task-planning", "pre-execution", "all"}:
        return errors

    packet_text = flatten_text(model.packet_doc)
    context_text = read_optional(model.change_dir / "atomic-planning-context-pack.md")
    for rel in REQUIRED_CONTRACT_MATRIX_FILES:
        if rel not in context_text:
            errors.append(f"contract: atomic-planning-context-pack.md must consume {rel}")
    if "Contract Executable Obligation Matrix" not in context_text and "contract executable" not in context_text.lower():
        errors.append("contract: atomic-planning-context-pack.md must consume Contract Executable Obligation Matrix")

    wire_rows = markdown_table_dicts(read_optional(model.change_dir / "api-wire-shape-matrix.md"))
    for row in wire_rows:
        contract = table_get(row, "Contract")
        if not contract or re.fullmatch(r"(?:N/A|not applicable|不适用)", contract.strip(), re.IGNORECASE):
            continue
        owner = table_get(row, "Owner issue", "Owning issue")
        if owner and not re.match(r"T\d{3}", owner):
            errors.append(f"contract: API wire shape row {contract} has invalid Owner issue {owner}")
        for required in [
            table_get(row, "Method/path"),
            table_get(row, "Request canonical body/query"),
            table_get(row, "Allowed keys"),
            table_get(row, "Forbidden keys / semantic aliases"),
            table_get(row, "Required/nullable/default/derived rule"),
            table_get(row, "Legacy compatibility rule"),
            table_get(row, "Exact-key verification"),
        ]:
            required_text = text(required)
            if required_text and required_text.lower() not in {"n/a", "not applicable"} and not semantic_payload_copied(required_text, packet_text):
                errors.append(
                    f"contract: API wire shape row {contract} detail is not copied into atomic-issue-packets.yaml execution payload: {required_text}"
                )
    return errors


def validate_atomic_task_decomposition(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"task-planning", "pre-execution", "all"}:
        return errors
    if not model.tasks and not model.packets:
        return errors
    path = model.change_dir / "atomic-task-decomposition.md"
    body = read_optional(path)
    if not body.strip():
        return [f"task-planning: required artifact atomic-task-decomposition.md is missing or empty"]
    if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
        errors.append("task-planning: atomic-task-decomposition.md contains unresolved TBD/TODO/unknown value")
    for section_name, columns in REQUIRED_ATOMIC_DECOMPOSITION_SECTIONS.items():
        if section_name not in body:
            errors.append(f"task-planning: atomic-task-decomposition.md missing section {section_name}")
            continue
        if not markdown_has_columns(body, columns):
            errors.append(f"task-planning: {section_name} must include columns {', '.join(columns)}")
    for row in markdown_table_dicts(body):
        joined = flatten_text(row)
        if re.search(r"\b(?:blocked-backflow|blocked|unknown)\b|待确认|未知|阻塞", joined, re.IGNORECASE) and not re.search(
            r"\blocked\s+N/A\b|locked N/A|not applicable|不适用", joined, re.IGNORECASE
        ):
            errors.append(f"task-planning: atomic-task-decomposition.md contains blocking row: {joined}")
    for task_id in model.tasks:
        if task_id not in body:
            errors.append(f"task-planning: task {task_id} missing from atomic-task-decomposition.md")
    edge_section = section(body, "Contract Edge Decomposition Matrix")
    edge_rows = markdown_table_dicts(edge_section)
    edge_text = flatten_text(edge_rows)
    context_text = read_optional(model.change_dir / "atomic-planning-context-pack.md")
    errors.extend(module_and_contract_pack_context_errors(model, context_text))
    packets = flatten_text(model.packet_doc)
    dag = flatten_text(model.dag_doc) + "\n" + read_optional(model.change_dir / "tasks.md")
    obligation_rows = active_contract_obligation_rows(model)
    obligation_groups: dict[str, dict[str, str]] = {}
    for obligation in obligation_rows:
        gid = obligation_group_id(obligation)
        if gid and gid not in obligation_groups:
            obligation_groups[gid] = obligation
    merge_rows = markdown_table_dicts(section(body, "Task Merge Split Decision Matrix"))
    pc_rows = markdown_table_dicts(section(body, "Provider Consumer Task Decision Matrix"))
    owner_rows = markdown_table_dicts(section(body, "Owner Legitimacy Matrix"))

    owner_rows_by_ref: dict[str, list[dict[str, str]]] = defaultdict(list)
    semantic_provider_by_ref: dict[str, set[str]] = defaultdict(set)
    non_provider_by_ref: dict[str, set[str]] = defaultdict(set)
    for row in owner_rows:
        joined = flatten_text(row)
        edge_ref = table_get(row, "Edge row")
        refs = set()
        if edge_ref:
            refs.add(edge_ref)
        refs |= obligation_ids_in_text(joined)
        if not refs and joined:
            refs.add(joined)
        for ref in refs:
            owner_rows_by_ref[ref].append(row)
        edge_type = table_get(row, "Edge type")
        row_kind = table_get(row, "Row kind")
        legitimacy = table_get(row, "Owner legitimacy")
        proposed_tasks = task_ids_from_row({"task": table_get(row, "Proposed provider task")})
        if not edge_type:
            errors.append(f"task-planning: Owner Legitimacy Matrix row missing Edge type: {joined}")
        elif not (PROVIDER_OWNED_EDGE_TYPE_RE.search(edge_type) or CARRIER_EDGE_TYPE_RE.search(edge_type)):
            errors.append(
                f"task-planning: Owner Legitimacy Matrix row has unknown Edge type {edge_type}; "
                "use semantic_contract_edge, carrier_order_edge, verification_prerequisite_edge, or proof_only_edge"
            )
        if OWNER_INVALID_RE.search(legitimacy):
            errors.append(f"task-planning: Owner Legitimacy Matrix contains invalid owner row that must backflow before merge/split: {joined}")
        if PROVIDER_ROW_KIND_RE.search(row_kind) and CARRIER_EDGE_TYPE_RE.search(edge_type):
            errors.append(
                f"task-planning: provider guarantee row cannot be downgraded to {edge_type}; "
                f"split a carrier/proof row instead: {joined}"
            )
        if row_is_semantic_provider(row):
            if not OWNER_VALID_RE.search(legitimacy):
                errors.append(f"task-planning: semantic provider owner row must mark Owner legitimacy valid-owner/passed: {joined}")
            if not proposed_tasks:
                errors.append(f"task-planning: semantic provider owner row must name Proposed provider task Txxx: {joined}")
            canonical_owner = table_get(row, "Owner module", "Canonical owner module")
            proposed_module_cell = table_get(row, "Proposed task primary module")
            for task_id in sorted(proposed_tasks):
                actual_module = task_primary_module(model, task_id)
                if not actual_module:
                    errors.append(f"task-planning: Owner Legitimacy Matrix references unknown task {task_id}: {joined}")
                    continue
                if proposed_module_cell and not owner_modules_compatible(proposed_module_cell, actual_module):
                    errors.append(
                        f"task-planning: Owner Legitimacy Matrix row says {task_id} primary module is {proposed_module_cell}, "
                        f"but task-dag.yaml says {actual_module}: {joined}"
                    )
                if canonical_owner and not owner_modules_compatible(canonical_owner, actual_module):
                    errors.append(
                        f"task-planning: Owner Legitimacy Matrix maps semantic provider row to {task_id} "
                        f"primary_module {actual_module}, but canonical owner is {canonical_owner}: {joined}"
                    )
                for ref in refs:
                    semantic_provider_by_ref[ref].add(task_id)
        else:
            if CARRIER_EDGE_TYPE_RE.search(edge_type) and not (
                table_get(row, "If not provider: carrier/proof edge") or OWNER_NON_PROVIDER_RE.search(legitimacy)
            ):
                errors.append(f"task-planning: non-provider owner row must record carrier/proof edge handoff: {joined}")
            for task_id in sorted(proposed_tasks):
                for ref in refs:
                    non_provider_by_ref[ref].add(task_id)

    for edge_row in edge_rows:
        joined = flatten_text(edge_row)
        edge_id = table_get(edge_row, "Edge ID")
        refs = ({edge_id} if edge_id else set()) | obligation_ids_in_text(joined)
        if not refs:
            continue
        if owner_rows and not any(ref in owner_rows_by_ref for ref in refs):
            errors.append(f"task-planning: edge row {edge_id or joined[:80]} has no Owner Legitimacy Matrix row")
        candidate_tasks = task_ids_from_row({"task": table_get(edge_row, "Candidate task owner")})
        canonical_owner = table_get(edge_row, "Owner module", "Canonical owner module")
        provider_like = bool(
            table_get(edge_row, "Provider guarantee to create/preserve")
            and not re.search(r"\b(?:locked N/A|not applicable|proof-only|carrier-only)\b", joined, re.IGNORECASE)
        )
        for task_id in sorted(candidate_tasks):
            actual_module = task_primary_module(model, task_id)
            if provider_like and canonical_owner and actual_module and not owner_modules_compatible(canonical_owner, actual_module):
                allowed_non_provider = any(task_id in non_provider_by_ref.get(ref, set()) for ref in refs)
                if not allowed_non_provider:
                    errors.append(
                        f"task-planning: edge row {edge_id or ','.join(sorted(refs))} candidate task {task_id} "
                        f"primary_module {actual_module} cannot own canonical provider module {canonical_owner}; "
                        "use carrier_order_edge/proof_only_edge or move provider obligation to the canonical owner task"
                    )

    provider_obligation_owners: dict[str, set[str]] = defaultdict(set)
    obligation_rows_by_id = {
        gid: row
        for gid, row in obligation_groups.items()
        if gid and not obligation_id_is_coarse_contract(gid)
    }
    semantic_provider_obligations_by_contract = semantic_provider_obligation_ids_by_contract(obligation_rows_by_id)
    for task_id, raw_task in model.tasks.items():
        task = as_dict(raw_task)
        task_module = text(task.get("primary_module"))
        task_provides_obligations = set(map(str, as_list(task.get("provides_obligations"))))
        for contract_id in map(str, as_list(task.get("provides"))):
            semantic_ids = semantic_provider_obligations_by_contract.get(contract_id, set())
            if not semantic_ids:
                errors.append(
                    f"task-planning: {task_id} lists provides {contract_id}, but {contract_id} has no semantic_contract_edge "
                    "executable obligation; proof/carrier/composition rows cannot be semantic provides"
                )
            elif not contract_semantic_provider_is_owner_single(obligation_rows_by_id, contract_id):
                owner_modules = ", ".join(sorted(semantic_provider_owner_modules_for_contract(obligation_rows_by_id, contract_id)))
                errors.append(
                    f"task-planning: {task_id} lists provides {contract_id}, but semantic provider obligations under "
                    f"{contract_id} have multiple owner modules ({owner_modules}); keep coarse C-xxx as a composition "
                    "index and list only owner-single provides_obligations"
                )
            elif not semantic_ids <= task_provides_obligations:
                missing = ", ".join(sorted(semantic_ids - task_provides_obligations))
                errors.append(
                    f"task-planning: {task_id} lists coarse provides {contract_id} without explicitly providing all owner "
                    f"semantic obligations ({missing}); keep coarse C-xxx as a composition index or list owner-single provides_obligations"
                )
            elif task_module:
                mismatched = sorted(
                    obligation_id
                    for obligation_id in semantic_ids
                    if contract_row_owner_module(obligation_rows_by_id.get(obligation_id, {}))
                    and not owner_modules_compatible(contract_row_owner_module(obligation_rows_by_id.get(obligation_id, {})), task_module)
                )
                if mismatched:
                    errors.append(
                        f"task-planning: {task_id} primary_module {task_module} lists provides {contract_id}, "
                        f"but it does not own semantic provider obligations {', '.join(mismatched)}"
                    )
        for obligation_id in map(str, as_list(task.get("provides_obligations"))):
            if not obligation_id:
                continue
            provider_obligation_owners[obligation_id].add(str(task_id))
            obligation_row = obligation_rows_by_id.get(obligation_id)
            edge_type = table_get(obligation_row or {}, "Edge type")
            if obligation_row and not row_is_semantic_provider(obligation_row):
                errors.append(
                    f"task-planning: {task_id} provides_obligations lists {obligation_id}, "
                    f"but its edge_type is {edge_type or '<missing>'}; only semantic_contract_edge provider guarantee obligations can be provided"
                )
            owner_module = contract_row_owner_module(obligation_row or {})
            if owner_module and task_module and not owner_modules_compatible(owner_module, task_module):
                errors.append(
                    f"task-planning: {task_id} primary_module {task_module} lists provides_obligation {obligation_id}, "
                    f"but obligation owner_module is {owner_module}; use carrier_order_edge/proof_only_edge or move it to the canonical owner"
                )
    for obligation_id, owners in sorted(provider_obligation_owners.items()):
        if len(owners) > 1:
            errors.append(
                f"task-planning: provider obligation {obligation_id} has multiple semantic provider task owners "
                f"{', '.join(sorted(owners))}; split distinct owner rows or keep exactly one provider and model others as carrier/consumer/proof edges"
            )

    for edge in model.edges:
        edge = as_dict(edge)
        edge_type = text(edge.get("type"))
        edge_text = flatten_text(edge)
        if CONTRACT_PROVIDER_EDGE_ALIAS_RE.search(edge_type) and CARRIER_ORDER_LANGUAGE_RE.search(edge_text):
            errors.append(
                f"task-planning: DAG edge {edge.get('from')}->{edge.get('to')} is typed {edge_type} "
                "but its reason is carrier/prerequisite language; use carrier_order_edge, verification_prerequisite_edge, or proof_only_edge"
            )
        if edge_type and not (
            PROVIDER_OWNED_EDGE_TYPE_RE.search(edge_type)
            or CARRIER_EDGE_TYPE_RE.search(edge_type)
            or CONTRACT_PROVIDER_EDGE_ALIAS_RE.search(edge_type)
            or re.search(r"acceptance[-_ ]prerequisite|packaged[-_ ]browser[-_ ]prerequisite", edge_type, re.IGNORECASE)
        ):
            errors.append(
                f"task-planning: DAG edge {edge.get('from')}->{edge.get('to')} uses non-canonical type {edge_type}; "
                "use semantic_contract_edge, carrier_order_edge, verification_prerequisite_edge, or proof_only_edge"
            )

    row_to_tasks: dict[str, set[str]] = {}
    for gid, obligation in obligation_groups.items():
        if not gid:
            continue
        missing_targets: list[str] = []
        for label, target in [
            ("atomic-planning-context-pack.md", context_text),
            ("atomic-task-decomposition.md", body),
            ("task-dag.yaml/tasks.md", dag),
            ("atomic-issue-packets.yaml", packets),
        ]:
            if not text_mentions_obligation_group(target, obligation):
                missing_targets.append(label)
        if missing_targets:
            errors.append(
                f"task-planning: contract executable obligation {gid} is not mapped through "
                + ", ".join(missing_targets)
                + "; coarse C-xxx consumption is insufficient"
            )
        mapped_tasks: set[str] = set()
        for candidate in edge_rows + pc_rows + merge_rows:
            if text_mentions_obligation_group(flatten_text(candidate), obligation):
                mapped_tasks.update(task_ids_from_row(candidate))
        if not mapped_tasks:
            mapped_tasks.update(set(re.findall(r"\bT\d{3}\b", dag if text_mentions_obligation_group(dag, obligation) else "")))
        row_to_tasks[gid] = mapped_tasks
        if not mapped_tasks and not re.search(r"\b(?:proof-only|locked N/A|locked-na|not applicable|backflow|N/A|不适用|回流)\b", flatten_text(obligation), re.IGNORECASE):
            errors.append(f"task-planning: contract executable obligation {gid} has no Txxx/proof-only/locked N/A/backflow owner mapping")
        for task_id in sorted(mapped_tasks):
            packet = as_dict(model.packets.get(task_id))
            packet_text = flatten_text(packet)
            if not text_mentions_obligation_group(packet_text, obligation):
                errors.append(
                    f"task-planning: contract executable obligation {gid} maps to {task_id} "
                    "but is not copied into that owner packet"
                )
            elif not obligation_payload_materialized(obligation, packet_text):
                errors.append(
                    f"task-planning: contract executable obligation {gid} maps to {task_id} "
                    "but its operation/fields/provider/failure/verification payload is not materialized in the owner packet"
                )

    high_risk_by_task: dict[str, list[str]] = {}
    for gid, obligation in obligation_groups.items():
        if not gid or not obligation_is_high_risk(obligation):
            continue
        for task_id in row_to_tasks.get(gid, set()):
            high_risk_by_task.setdefault(task_id, []).append(gid)
    for task_id, row_ids in sorted(high_risk_by_task.items()):
        unique_ids = sorted(set(row_ids))
        if len(unique_ids) <= 1:
            continue
        supporting_rows = [
            row for row in merge_rows
            if task_id in flatten_text(row) and all(text_has_row_id(flatten_text(row), oid) for oid in unique_ids)
        ]
        if not supporting_rows:
            errors.append(
                f"task-planning: {task_id} merges multiple high-risk obligation rows {', '.join(unique_ids)} "
                "without one Task Merge Split Decision Matrix row listing every row ID"
            )
            continue
        for merge_row in supporting_rows:
            joined = flatten_text(merge_row)
            same_checks = [
                table_get(merge_row, "Same primary module?"),
                table_get(merge_row, "Same semantic type?"),
                table_get(merge_row, "Same operation/surface?"),
                table_get(merge_row, "Same short verification?"),
            ]
            if not all(re.search(r"\b(?:yes|true|是|same)\b", value, re.IGNORECASE) for value in same_checks):
                errors.append(
                    f"task-planning: {task_id} high-risk merge must prove same module/type/operation/verification for {', '.join(unique_ids)}: {joined}"
                )
            if re.search(r"\b(?:same module|same page|related work|task count|方便|相关|owner closure|同一模块|同页|相关工作|减少任务)\b", joined, re.IGNORECASE) and not all(
                text_has_row_id(joined, oid) for oid in unique_ids
            ):
                errors.append(f"task-planning: {task_id} high-risk merge rationale is too weak: {joined}")
    for cid, raw_contract in model.contracts.items():
        contract = as_dict(raw_contract)
        if as_dict(contract).get("status") in {"superseded", "not_applicable", "locked-na"}:
            continue
        provider = text(contract.get("provider_module"))
        consumers = flatten_text(contract.get("consumer_modules"))
        trigger = text(contract.get("trigger"))
        normal_path = text(contract.get("normal_path"))
        failure_path = text(contract.get("failure_path"))
        timing = text(contract.get("timing"))
        semantic_type = text(contract.get("type"))
        cid_rows = [
            row for row in edge_rows
            if cid in flatten_text(row)
        ]
        if not cid_rows:
            errors.append(
                f"task-planning: contract {cid} has no Contract Edge Decomposition Matrix row; "
                "do not map one contract directly to one task without decomposing executable provider/consumer obligations"
            )
            continue
        cid_text = flatten_text(cid_rows)
        required_payloads = [
            ("provider module", provider),
            ("consumer module", consumers),
            ("trigger/operation", trigger),
            ("provider guarantee", normal_path),
            ("failure path", failure_path),
            ("timing", timing),
        ]
        for label, payload in required_payloads:
            payload_text = text(payload)
            if payload_text and payload_text.lower() not in {"n/a", "not applicable"} and not semantic_payload_copied(payload_text, cid_text):
                errors.append(
                    f"task-planning: contract {cid} {label} is not decomposed into Contract Edge Decomposition Matrix: {payload_text}"
                )
        if re.search(r"resource|ownership|external|side-effect|state-machine|progress|change|readback|wire|frontend|UI|acceptance", semantic_type, re.IGNORECASE):
            if len(cid_rows) == 1:
                row_text = flatten_text(cid_rows[0])
                if re.search(r"\b(one contract|same contract|single contract|same module|related|直接|同一契约|同一模块|相关)\b", row_text, re.IGNORECASE):
                    errors.append(
                        f"task-planning: contract {cid} appears admitted as one coarse edge; split provider guarantee, consumer assumption, failure, timing, and verification obligations"
                    )
    proof_section = section(body, "Proof Owner Allowlist Matrix")
    for row in markdown_table_dicts(proof_section):
        proof_file = table_get(row, "Proof file/path").strip("`")
        if not proof_file:
            continue
        if re.search(r"\b(?:yes|true|是|required|must)\b", table_get(row, "Added to packet files_to_change?"), re.IGNORECASE) and proof_file not in packets:
            errors.append(f"task-planning: proof file {proof_file} is marked packet-required but missing from atomic-issue-packets.yaml")
        if re.search(r"\b(?:yes|true|是|required|must)\b", table_get(row, "Added to task-dag files?"), re.IGNORECASE) and proof_file not in dag:
            errors.append(f"task-planning: proof file {proof_file} is marked task-dag-required but missing from task-dag files")
    load_section = section(body, "Semantic Load Split Matrix")
    for row in markdown_table_dicts(load_section):
        joined = flatten_text(row)
        split_required = table_get(row, "Split required?")
        rationale = table_get(row, "Merge rationale / backflow")
        if re.search(r"\b(?:yes|true|是|required|must)\b", split_required, re.IGNORECASE) and not re.search(
            r"\b(?:backflow|split|拆|回流|T\d{3}|locked N/A|not applicable)\b",
            rationale,
            re.IGNORECASE,
        ):
            errors.append(f"task-planning: semantic load row requires split but lacks split/backflow rationale: {joined}")
        if re.search(r"\b(?:same module|same page|related work|task count|方便|相关)\b", rationale, re.IGNORECASE):
            errors.append(f"task-planning: semantic load merge rationale is too weak: {joined}")
    return errors


def validate_atomic_issue_quality_review(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"task-planning", "pre-execution", "all"}:
        return errors
    if not model.tasks and not model.packets:
        return errors
    review_path = model.change_dir / "atomic-issue-quality-review.yaml"
    review_doc = as_dict(load_yaml(review_path))
    if not review_doc:
        return [f"task-planning: required artifact atomic-issue-quality-review.yaml is missing or empty"]
    scope = as_dict(review_doc.get("review_scope"))
    reviewer_type = text(scope.get("reviewer_type")).lower().replace("_", "-")
    if reviewer_type not in {"readonly-subagent", "read-only-subagent"}:
        errors.append("atomic-issue-quality-review: review_scope.reviewer_type must be readonly-subagent or read-only-subagent; main-local fallback is not allowed")
    errors.extend(validate_subagent_execution_proof(scope, "atomic-issue-quality-review review_scope", model.change_dir))
    reviewed_outputs = flatten_text(scope.get("validator_outputs_reviewed"))
    for required in ["atomic_issue_compile", "validate_artifacts", "workflowctl"]:
        if required not in reviewed_outputs:
            errors.append(f"atomic-issue-quality-review: review_scope.validator_outputs_reviewed must include {required}")
    boundary_definition = as_dict(scope.get("atomic_boundary_definition"))
    boundary_definition_text = flatten_text(boundary_definition)
    for pattern in [
        r"zero|零决策",
        r"single|单层",
        r"self|自包含",
        r"short|短.*验证|验证.*短",
        r"error|错误.*传播|不传播",
    ]:
        if not re.search(pattern, boundary_definition_text, re.IGNORECASE):
            errors.append(
                "atomic-issue-quality-review: review_scope.atomic_boundary_definition must include the methodology "
                "Atomic Boundary conditions: zero decision, single-layer change, self-contained context, short verification loop, and no error propagation"
            )
            break
    if not re.search(r"primary[_ -]?closure|action[- ]?flow|stateful|provided contract|verification loop|用户动作|状态机|提供.*契约|验证闭环|拆分.*证据", boundary_definition_text, re.IGNORECASE):
        errors.append(
            "atomic-issue-quality-review: review_scope.atomic_boundary_definition must state that primary_closure/action-flow/stateful operation/provided contract/verification loop are split evidence, not the Atomic Boundary definition"
        )
    rows = [as_dict(row) for row in as_list(review_doc.get("reviews"))]
    rows_by_task = {text(row.get("task")): row for row in rows if text(row.get("task"))}
    for task_id in sorted(set(model.tasks) | set(model.packets)):
        row = rows_by_task.get(task_id)
        if not row:
            errors.append(f"atomic-issue-quality-review: missing review row for {task_id}")
            continue
        if text(row.get("verdict")).lower() != "pass":
            errors.append(f"atomic-issue-quality-review: {task_id} verdict must be pass before pre-execution")
        for field in [
            "source_context_quality",
            "no_validator_gaming",
            "owner_boundary",
            "atomicity",
            "brief_overflow_handling",
            "frontend_backend_proof_boundary",
            "compiler_failure_triage",
        ]:
            value = text(row.get(field)).lower().replace("_", "-")
            if value not in {"pass", "not-applicable", "not applicable", "n/a"}:
                errors.append(f"atomic-issue-quality-review: {task_id}.{field} must be pass or not_applicable, got {row.get(field)!r}")
        boundary_check = as_dict(row.get("atomic_boundary_check"))
        for field in [
            "zero_decision",
            "single_layer_change",
            "self_contained_context",
            "short_verification_loop",
            "no_error_propagation",
        ]:
            value = text(boundary_check.get(field)).lower().replace("_", "-")
            if value != "pass":
                errors.append(f"atomic-issue-quality-review: {task_id}.atomic_boundary_check.{field} must be pass")
        split_note = flatten_text(boundary_check.get("split_evidence_used"))
        if not re.search(r"primary[_ -]?closure|action[- ]?flow|stateful|provided contract|verification loop|用户动作|状态机|提供.*契约|验证闭环|拆分.*证据", split_note, re.IGNORECASE):
            errors.append(
                f"atomic-issue-quality-review: {task_id}.atomic_boundary_check.split_evidence_used must mention split evidence and must not replace the five Atomic Boundary checks"
            )
        if as_list(row.get("blocking_findings")):
            errors.append(f"atomic-issue-quality-review: {task_id} has blocking_findings")
        evidence = flatten_text(row.get("evidence"))
        if len(evidence) < 80:
            errors.append(f"atomic-issue-quality-review: {task_id} evidence is too thin")
        if not re.search(r"atomic-issues/T\d{3}\.md|atomic-issue-packets\.yaml|task-dag\.yaml|contracts\.yaml|verification\.yaml|atomic-task-decomposition\.md", evidence):
            errors.append(f"atomic-issue-quality-review: {task_id} evidence must cite artifact path or section")
        if TEMPLATE_REVIEW_EVIDENCE_RE.search(evidence):
            errors.append(f"atomic-issue-quality-review: {task_id} evidence is template-like; cite concrete section names, fields, owners, or rows reviewed")

    for task_id, packet_raw in model.packets.items():
        packet = as_dict(packet_raw)
        issue_text = issue_markdown_text(model, str(task_id))
        source_text = flatten_text(packet.get("sources")) + "\n" + section(issue_text, "Source Context")
        execution_text = flatten_text(
            [
                packet.get("behavior_details"),
                packet.get("implementation_steps"),
                packet.get("verification"),
                packet.get("done_criteria"),
                issue_text,
            ]
        )
        if TASK_SELF_REQUIREMENT_SOURCE_RE.search(source_text):
            errors.append(
                f"atomic-issue-quality-review: {task_id} Source Context appears to contain task self-requirements; "
                "source excerpts must quote upstream facts, not current-task obligations"
            )
        if QUALITY_GATE_PHRASE_RE.search(execution_text + "\n" + source_text):
            errors.append(f"atomic-issue-quality-review: {task_id} contains validator/gate phrase instead of executable semantics")
        if ALLOWLIST_CEILING_RE.search(flatten_text(packet.get("files_to_change"))):
            errors.append(f"atomic-issue-quality-review: {task_id} files_to_change contains allowlist-ceiling/validator-feasibility wording")
        if packet_is_frontend(packet) and FRONTEND_CLAIMS_PROVIDER_PROOF_RE.search(execution_text):
            errors.append(
                f"atomic-issue-quality-review: {task_id} frontend packet claims provider/ownership cleanup proof; "
                "move provider mutation/readback/cleanup proof to the backend owner task or mark consumer handoff explicitly"
            )
        if packet_is_frontend(packet) and as_list(packet.get("managed_resource_ownership")):
            errors.append(
                f"atomic-issue-quality-review: {task_id} frontend packet owns managed_resource_ownership rows; "
                "move ownership lifecycle to backend owner task"
            )
        if packet_is_backend(packet) and BACKEND_CLAIMS_BROWSER_PROOF_RE.search(execution_text):
            errors.append(
                f"atomic-issue-quality-review: {task_id} backend packet claims browser/DOM proof; "
                "move browser proof to the frontend owner task"
            )
    return errors


def normalize_multi_perspective_stage(value: str) -> str:
    normalized = text(value).lower().replace("_", "-")
    return MULTI_PERSPECTIVE_STAGE_ALIASES.get(normalized, normalized)


def validate_multi_perspective_review(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in MULTI_PERSPECTIVE_REVIEW_STAGES and stage != "all":
        return errors

    if stage == "all":
        stages_to_validate = sorted(
            s
            for s in MULTI_PERSPECTIVE_REVIEW_STAGES
            if (model.change_dir / "multi-perspective-reviews" / f"{s}.yaml").exists()
            or as_dict(model.workflow.get("stage_status")).get(s) == "passed"
        )
        all_errors: list[str] = []
        for stage_name in stages_to_validate:
            all_errors.extend(validate_multi_perspective_review(model, stage_name))
        return all_errors

    review_path = model.change_dir / "multi-perspective-reviews" / f"{stage}.yaml"
    review_doc = as_dict(load_yaml(review_path))
    if not review_doc:
        return [f"{stage}: required artifact multi-perspective-reviews/{stage}.yaml is missing or empty"]

    scope = as_dict(review_doc.get("review_scope"))
    scope_stage_raw = text(scope.get("stage_under_review"))
    scope_stage = normalize_multi_perspective_stage(scope_stage_raw)
    if scope_stage_raw and scope_stage_raw.lower().replace("_", "-") not in MULTI_PERSPECTIVE_ALLOWED_STAGES:
        errors.append(f"multi-perspective-review: unknown review_scope.stage_under_review {scope_stage_raw!r}")
    if stage != "all" and scope_stage and scope_stage != stage:
        errors.append(
            f"multi-perspective-review: review_scope.stage_under_review {scope_stage_raw!r} resolves to {scope_stage!r}, expected {stage!r}"
        )
    if not scope_stage_raw:
        errors.append("multi-perspective-review: review_scope.stage_under_review is required")
    if not text(scope.get("gate_name")):
        errors.append("multi-perspective-review: review_scope.gate_name is required")
    if not text(scope.get("main_agent_owner")):
        errors.append("multi-perspective-review: review_scope.main_agent_owner is required")

    try:
        required_count = int(scope.get("required_reviewer_count"))
    except Exception:
        required_count = -1
    if required_count <= 0:
        errors.append("multi-perspective-review: review_scope.required_reviewer_count must be greater than 0")
    if stage == "task-planning" and required_count > 2:
        errors.append("multi-perspective-review: task-planning stage-level review must not exceed 2 reviewers")
    if required_count > 5:
        errors.append("multi-perspective-review: stage-level review must not exceed 5 reviewers")

    packet = as_dict(review_doc.get("frozen_input_packet"))
    if not isinstance(packet.get("frozen_artifacts"), list) or not packet.get("frozen_artifacts"):
        errors.append("multi-perspective-review: frozen_input_packet.frozen_artifacts must list reviewed canonical artifacts")
    if not text(packet.get("stage_objective")):
        errors.append("multi-perspective-review: frozen_input_packet.stage_objective is required")
    if not text(packet.get("review_objective")):
        errors.append("multi-perspective-review: frozen_input_packet.review_objective is required")
    if not isinstance(packet.get("reviewable_scope"), list) or not packet.get("reviewable_scope"):
        errors.append("multi-perspective-review: frozen_input_packet.reviewable_scope is required")
    if not isinstance(packet.get("non_reviewable_scope"), list) or not packet.get("non_reviewable_scope"):
        errors.append("multi-perspective-review: frozen_input_packet.non_reviewable_scope is required")

    if scope_stage in {"prd", "readiness", "aip", "design", "contract", "verification", "task-planning", "pre-execution"}:
        ds_inputs = as_dict(packet.get("decision_surface_inputs"))
        if ds_inputs.get("required_when_applicable") is not False:
            if not text(ds_inputs.get("decision_surface_discovery_path")):
                errors.append("multi-perspective-review: decision_surface_inputs.decision_surface_discovery_path is required for decision-bearing stages")
            for field in [
                "generative_stress_tests_reviewed",
                "surface_obligation_projection_reviewed",
                "semantic_consumption_matrix_reviewed",
            ]:
                if ds_inputs.get(field) is not True:
                    errors.append(f"multi-perspective-review: decision_surface_inputs.{field} must be true or required_when_applicable=false")

    reviewers_raw = review_doc.get("reviewers")
    reviewers = reviewers_raw if isinstance(reviewers_raw, list) else []
    if not reviewers:
        errors.append("multi-perspective-review: reviewers must include completed reviewer rows")
    if required_count > 0 and len(reviewers) < required_count:
        errors.append(f"multi-perspective-review: reviewers count {len(reviewers)} is less than required_reviewer_count {required_count}")
    completed_count = 0
    reviewer_ids: set[str] = set()
    perspectives: set[str] = set()
    for idx, row_any in enumerate(reviewers, 1):
        row = as_dict(row_any)
        rid = text(row.get("reviewer_id"))
        if not rid:
            errors.append(f"multi-perspective-review: reviewer row {idx} missing reviewer_id")
        elif rid in reviewer_ids:
            errors.append(f"multi-perspective-review: duplicate reviewer_id {rid}")
        else:
            reviewer_ids.add(rid)
        reviewer_type = text(row.get("reviewer_type")).lower().replace("_", "-")
        if reviewer_type not in MULTI_PERSPECTIVE_ALLOWED_REVIEWER_TYPES:
            errors.append(f"multi-perspective-review: reviewer {rid or idx} has invalid reviewer_type {row.get('reviewer_type')!r}")
        errors.extend(validate_subagent_execution_proof(row, f"multi-perspective-review reviewer {rid or idx}", model.change_dir))
        perspective = text(row.get("perspective"))
        if not perspective:
            errors.append(f"multi-perspective-review: reviewer {rid or idx} missing perspective")
        else:
            perspectives.add(perspective)
        if not text(row.get("assigned_objective")):
            errors.append(f"multi-perspective-review: reviewer {rid or idx} missing assigned_objective")
        if not isinstance(row.get("frozen_input_refs"), list) or not row.get("frozen_input_refs"):
            errors.append(f"multi-perspective-review: reviewer {rid or idx} must cite frozen_input_refs")
        if not isinstance(row.get("forbidden_scope"), list) or not row.get("forbidden_scope"):
            errors.append(f"multi-perspective-review: reviewer {rid or idx} must list forbidden_scope")
        status = text(row.get("status")).lower()
        if status == "completed":
            completed_count += 1
        elif status:
            errors.append(f"multi-perspective-review: reviewer {rid or idx} status must be completed before gate pass, got {status!r}")
        else:
            errors.append(f"multi-perspective-review: reviewer {rid or idx} missing status")
    if required_count > 0 and completed_count < required_count:
        errors.append(f"multi-perspective-review: completed reviewer count {completed_count} is less than required_reviewer_count {required_count}")
    if required_count >= 2 and len(perspectives) < 2:
        errors.append("multi-perspective-review: stage-level review needs at least two distinct reviewer perspectives")

    findings_raw = review_doc.get("findings")
    findings = findings_raw if isinstance(findings_raw, list) else []
    finding_ids: set[str] = set()
    blocker_ids: set[str] = set()
    for idx, row_any in enumerate(findings, 1):
        row = as_dict(row_any)
        fid = text(row.get("finding_id"))
        if not fid:
            errors.append(f"multi-perspective-review: finding row {idx} missing finding_id")
        elif fid in finding_ids:
            errors.append(f"multi-perspective-review: duplicate finding_id {fid}")
        else:
            finding_ids.add(fid)
        rid = text(row.get("reviewer_id"))
        if rid and reviewer_ids and rid not in reviewer_ids:
            errors.append(f"multi-perspective-review: finding {fid or idx} references unknown reviewer_id {rid}")
        severity = text(row.get("severity")).lower()
        if severity not in MULTI_PERSPECTIVE_ALLOWED_SEVERITIES:
            errors.append(f"multi-perspective-review: finding {fid or idx} has invalid severity {row.get('severity')!r}")
        if severity == "blocker" and fid:
            blocker_ids.add(fid)
        if not isinstance(row.get("evidence_paths"), list) or not row.get("evidence_paths"):
            errors.append(f"multi-perspective-review: finding {fid or idx} must cite evidence_paths")
        for field in ["violated_rule", "why_current_artifact_is_insufficient", "suggested_backflow_stage"]:
            if not text(row.get(field)):
                errors.append(f"multi-perspective-review: finding {fid or idx} missing {field}")

    dispositions_raw = review_doc.get("main_agent_dispositions")
    dispositions = dispositions_raw if isinstance(dispositions_raw, list) else []
    disposition_by_finding: dict[str, dict[str, Any]] = {}
    for idx, row_any in enumerate(dispositions, 1):
        row = as_dict(row_any)
        fid = text(row.get("finding_id"))
        if not fid:
            errors.append(f"multi-perspective-review: disposition row {idx} missing finding_id")
            continue
        if fid in disposition_by_finding:
            errors.append(f"multi-perspective-review: duplicate disposition for {fid}")
        disposition_by_finding[fid] = row
        if finding_ids and fid not in finding_ids:
            errors.append(f"multi-perspective-review: disposition references unknown finding_id {fid}")
        disposition = text(row.get("disposition")).lower()
        if disposition not in MULTI_PERSPECTIVE_ALLOWED_DISPOSITIONS:
            errors.append(f"multi-perspective-review: disposition for {fid} has invalid disposition {row.get('disposition')!r}")
        if not text(row.get("disposition_reason")):
            errors.append(f"multi-perspective-review: disposition for {fid} missing disposition_reason")
        if disposition == "rejected" and (not isinstance(row.get("counter_evidence_paths"), list) or not row.get("counter_evidence_paths")):
            errors.append(f"multi-perspective-review: rejected finding {fid} requires counter_evidence_paths")
        if disposition == "backflow-created" and not text(row.get("backflow_id")):
            errors.append(f"multi-perspective-review: backflow-created finding {fid} requires backflow_id")
        if disposition in {"accepted", "backflow-created"} and row.get("canonical_updates_completed") is not True:
            errors.append(f"multi-perspective-review: {disposition} finding {fid} requires canonical_updates_completed=true")
        if row.get("human_decision_prompt_required") is True and not text(row.get("human_decision_prompt_id")):
            errors.append(f"multi-perspective-review: finding {fid} requires human_decision_prompt_id")
    for fid in sorted(finding_ids):
        if fid not in disposition_by_finding:
            errors.append(f"multi-perspective-review: finding {fid} lacks main_agent_disposition")

    gate = as_dict(review_doc.get("gate_result"))
    verdict = text(gate.get("verdict")).lower()
    if verdict not in {"blocked", "pass"}:
        errors.append("multi-perspective-review: gate_result.verdict must be blocked or pass")
    open_blockers = gate.get("blocking_findings_open")
    if not isinstance(open_blockers, list):
        errors.append("multi-perspective-review: gate_result.blocking_findings_open must be a list")
        open_blockers = []
    if verdict == "pass":
        if open_blockers:
            errors.append("multi-perspective-review: gate_result.verdict=pass but blocking_findings_open is not empty")
        unresolved_blockers = [
            fid
            for fid in blocker_ids
            if text(disposition_by_finding.get(fid, {}).get("disposition")).lower() not in {"rejected", "backflow-created", "superseded"}
        ]
        if unresolved_blockers:
            errors.append(f"multi-perspective-review: blocker findings lack closing disposition: {', '.join(sorted(unresolved_blockers))}")
        if gate.get("ready_for_next_stage") is not True:
            errors.append("multi-perspective-review: gate_result.verdict=pass requires ready_for_next_stage=true")
        if not isinstance(gate.get("validators_rerun"), list) or not gate.get("validators_rerun"):
            errors.append("multi-perspective-review: gate_result.verdict=pass requires validators_rerun evidence")
    if verdict == "blocked" and gate.get("ready_for_next_stage") is True:
        errors.append("multi-perspective-review: blocked gate cannot set ready_for_next_stage=true")
    return errors


def validate_compiler_failure_triage(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"task-planning", "pre-execution", "all"}:
        return errors
    if not model.packets:
        return errors
    triage_path = model.change_dir / "compiler-failure-triage.yaml"
    doc = as_dict(load_yaml(triage_path))
    if not doc:
        return ["task-planning: required artifact compiler-failure-triage.yaml is missing or empty"]
    scope = as_dict(doc.get("triage_scope"))
    if text(scope.get("no_packet_edits_before_triage")).lower() not in {"true", "yes", "是"}:
        errors.append("compiler-failure-triage: triage_scope.no_packet_edits_before_triage must be true")
    rows = [as_dict(row) for row in as_list(doc.get("rows"))]
    allowed = {"current-task-owner", "move-to-existing-owner", "split-new-task", "upstream-backflow", "validator-gap-blocked"}
    for idx, row in enumerate(rows, start=1):
        rid = text(row.get("id")) or f"row-{idx}"
        task = text(row.get("task"))
        if not TASK_RE.match(task):
            errors.append(f"compiler-failure-triage: {rid}.task must be a Txxx id")
        if not text(row.get("compiler_error")):
            errors.append(f"compiler-failure-triage: {rid}.compiler_error is required")
        owner_decision = text(row.get("owner_decision"))
        if owner_decision not in allowed:
            errors.append(f"compiler-failure-triage: {rid}.owner_decision must be one of {sorted(allowed)}, got {owner_decision!r}")
        reason = flatten_text(row.get("true_owner_reason"))
        if owner_decision == "current-task-owner" and not re.search(
            r"atomic-task-decomposition\.md|contracts\.yaml|decision-surface-discovery\.md|task-dag\.yaml|C-\d{3}|DS-\d{3}",
            reason,
            re.IGNORECASE,
        ):
            errors.append(f"compiler-failure-triage: {rid}.true_owner_reason must cite owner assignment evidence")
        move = as_dict(row.get("task_split_or_move"))
        if owner_decision in {"move-to-existing-owner", "split-new-task", "upstream-backflow"} and not flatten_text(move):
            errors.append(f"compiler-failure-triage: {rid}.task_split_or_move is required for {owner_decision}")
        delta = as_dict(row.get("files_to_change_delta"))
        if flatten_text(delta.get("added")) and owner_decision != "current-task-owner":
            errors.append(f"compiler-failure-triage: {rid} adds files_to_change but owner_decision is {owner_decision}")
        if ALLOWLIST_CEILING_RE.search(flatten_text(row)):
            errors.append(f"compiler-failure-triage: {rid} contains allowlist-ceiling/validator-feasibility wording")
    summary = as_dict(doc.get("summary"))
    if not rows and sum(int(summary.get(key, 0) or 0) for key in ["current_task_owner_fixes", "moved_to_existing_owner", "split_new_task", "upstream_backflow", "validator_gap_blocked"]) == 0:
        errors.append("compiler-failure-triage: rows or summary counts must record compiler failure triage decisions")
    return errors


def validate_task_planning_repair_ledger(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"task-planning", "pre-execution", "all"}:
        return errors
    if not model.packets:
        return errors
    ledger_path = model.change_dir / "task-planning-repair-ledger.yaml"
    doc = as_dict(load_yaml(ledger_path))
    if not doc:
        return ["task-planning: required artifact task-planning-repair-ledger.yaml is missing or empty"]
    if text(doc.get("stage")) not in {"task-planning", "atomic-task-planning"}:
        errors.append("task-planning-repair-ledger: stage must be task-planning")
    scope = as_dict(doc.get("ledger_scope"))
    if not text(scope.get("generator_entrypoint")):
        errors.append("task-planning-repair-ledger: ledger_scope.generator_entrypoint is required")
    rule = flatten_text(scope.get("rule"))
    for required in ["regression", "fixed", "generator"]:
        if required not in rule.lower():
            errors.append(f"task-planning-repair-ledger: ledger_scope.rule must mention {required}")
    active_signatures: dict[str, str] = {}
    allowed_status = {"open", "fixed", "superseded", "example"}
    allowed_classes = {
        "owner-boundary-leakage",
        "stale-regeneration",
        "keyword-misclassification",
        "task-split-gap",
        "carrier-projection-gap",
        "review-evidence-gap",
        "generator-invariant-failure",
    }
    rows = [as_dict(row) for row in as_list(doc.get("repair_iterations"))]
    real_rows = [row for row in rows if text(row.get("failure_signature")) and not text(row.get("failure_signature")).startswith("<")]
    for idx, row in enumerate(real_rows, start=1):
        rid = text(row.get("iteration_id")) or f"row-{idx}"
        signature = text(row.get("failure_signature"))
        status = text(row.get("status"))
        if status not in allowed_status:
            errors.append(f"task-planning-repair-ledger: {rid}.status must be one of {sorted(allowed_status)}")
        if status in {"open", "fixed"}:
            previous = active_signatures.get(signature)
            if previous:
                errors.append(
                    f"task-planning-repair-ledger: duplicate active/fixed failure_signature {signature} in {previous} and {rid}; "
                    "reappearing fixed signatures must be recorded as generator-invariant-failure, not another local repair"
                )
            active_signatures[signature] = rid
        if not text(row.get("root_cause")):
            errors.append(f"task-planning-repair-ledger: {rid}.root_cause is required")
        if not text(row.get("owner_invariant")):
            errors.append(f"task-planning-repair-ledger: {rid}.owner_invariant is required")
        failure_class = text(row.get("failure_class"))
        if failure_class not in allowed_classes:
            errors.append(f"task-planning-repair-ledger: {rid}.failure_class must be one of {sorted(allowed_classes)}")
        affected_tasks = [text(item) for item in as_list(row.get("affected_tasks")) if text(item)]
        if not affected_tasks:
            errors.append(f"task-planning-repair-ledger: {rid}.affected_tasks is required")
        for task_id in affected_tasks:
            if not TASK_RE.match(task_id):
                errors.append(f"task-planning-repair-ledger: {rid}.affected_tasks contains non-Txxx id {task_id!r}")
        if not meaningful_list(row.get("forbidden_regression"), min_chars=8):
            errors.append(f"task-planning-repair-ledger: {rid}.forbidden_regression is required")
        if not meaningful_list(row.get("generator_rules_changed"), min_chars=6):
            errors.append(f"task-planning-repair-ledger: {rid}.generator_rules_changed is required")
        checks = [as_dict(item) for item in as_list(row.get("regression_checks"))]
        if not checks:
            errors.append(f"task-planning-repair-ledger: {rid}.regression_checks is required")
        for cidx, check in enumerate(checks, start=1):
            cid = text(check.get("check_id")) or f"check-{cidx}"
            command = text(check.get("command"))
            expected = text(check.get("expected_result"))
            last_result = text(check.get("last_result"))
            if not command or command.startswith("<"):
                errors.append(f"task-planning-repair-ledger: {rid}.{cid}.command is required")
            if not expected or expected.startswith("<"):
                errors.append(f"task-planning-repair-ledger: {rid}.{cid}.expected_result is required")
            if status == "fixed" and (not last_result or last_result.startswith("<")):
                errors.append(f"task-planning-repair-ledger: {rid}.{cid}.last_result is required for fixed rows")
    known = [as_dict(row) for row in as_list(doc.get("known_regressions"))]
    for idx, row in enumerate(known, start=1):
        signature = text(row.get("signature"))
        if not signature or signature.startswith("<"):
            continue
        if not text(row.get("owner_invariant")):
            errors.append(f"task-planning-repair-ledger: known_regressions[{idx}].owner_invariant is required")
        if not meaningful_list(row.get("must_not_reappear_in"), min_chars=4):
            errors.append(f"task-planning-repair-ledger: known_regressions[{idx}].must_not_reappear_in is required")
        if not text(row.get("regression_check_command")):
            errors.append(f"task-planning-repair-ledger: known_regressions[{idx}].regression_check_command is required")
    return errors


def validate_variant_impact_artifacts(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"archaeology", "contract", "verification", "task-planning", "pre-execution", "all"}:
        return errors
    combined = flatten_text(
        [
            model.semantic,
            model.contracts_doc,
            model.verification_doc,
            model.dag_doc,
            model.packet_doc,
            read_optional(model.change_dir / "proposal.md"),
            read_optional(model.change_dir / "spec.md"),
            read_optional(model.change_dir / "plan.md"),
            read_optional(model.change_dir / "tasks.md"),
            read_optional(model.change_dir / "decision-surface-discovery.md"),
        ]
    )
    decision_surface = read_optional(model.change_dir / "decision-surface-discovery.md")
    has_decision_surface_variant = bool(VARIANT_DECISION_SURFACE_RE.search(decision_surface)) and bool(
        re.search(r"\b(?:same|shared|existing|old|consumer|readback|post[- ]?create|runtime|mode|variant|deployment|provider)\b|同一|共享|旧|消费者|读回|创建后|运行时|模式|变体", decision_surface, re.IGNORECASE)
    )
    has_structural_variant_evidence = bool(
        re.search(r"Existing Object-Action-Consumer Graph|Variant Impact Matrix|Mode Semantic Inheritance Audit|same object|same action|shared entry|old consumer assumption|同一.*(?:对象|操作|入口)|旧.*(?:假设|消费者)", combined, re.IGNORECASE)
    )
    has_variant_signal = has_decision_surface_variant or has_structural_variant_evidence
    has_variant_artifact = any((model.change_dir / rel).exists() for rel in REQUIRED_OBJECT_ACTION_CONSUMER_FILES)
    if not has_variant_signal and not has_variant_artifact:
        return errors

    for rel, columns in REQUIRED_OBJECT_ACTION_CONSUMER_FILES.items():
        body = read_optional(model.change_dir / rel)
        if not body.strip():
            errors.append(f"variant-impact: required artifact {rel} is missing or empty")
            continue
        if not markdown_has_columns(body, columns):
            errors.append(f"variant-impact: {rel} must include columns {', '.join(columns)}")
        if not markdown_has_meaningful_rows(body):
            errors.append(f"variant-impact: {rel} must include concrete code-derived rows")
        if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
            errors.append(f"variant-impact: {rel} contains unresolved TBD/TODO/unknown value")

    variant_body = read_optional(model.change_dir / "variant-impact-matrix.md")
    variant_detection = section(variant_body, "Variant Detection Matrix")
    for row in markdown_table_dicts(variant_detection):
        joined = flatten_text(row)
        if re.search(r"\b(?:yes|supported|must|需要|支持)\b", joined, re.IGNORECASE):
            for label in ["New variant candidate", "Object/entity", "Existing action / mutation", "Shared entry/API/page", "Shared state/readback", "Detection evidence"]:
                if not table_get(row, label):
                    errors.append(f"variant-impact: supported row missing {label}: {joined}")
            if not re.search(r"\b(C-\d{3}|VER-\d{3}|T\d{3}|locked|决策|contract|verification)\b", joined, re.IGNORECASE):
                errors.append(f"variant-impact: supported row lacks contract/verification/task mapping: {joined}")

    parity_section = section(variant_body, "Old Consumer Parity Matrix")
    if variant_body.strip() and not parity_section:
        errors.append("variant-impact: variant-impact-matrix.md missing Old Consumer Parity Matrix")
    for row in markdown_table_dicts(parity_section):
        joined = flatten_text(row)
        must_satisfy = table_get(row, "Must new variant satisfy?")
        if re.search(r"\b(?:yes|true|must|required|需要|支持|是)\b", must_satisfy, re.IGNORECASE):
            for label in ["New variant", "Object/action", "Existing consumer surface", "Old variant assumption", "New producer/behavior", "Contract candidate", "Verification"]:
                value = table_get(row, label)
                if not value or re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", value, re.IGNORECASE):
                    errors.append(f"variant-impact: parity row missing {label}: {joined}")
            if re.search(r"progress|change|last-change|event|task step|进度|变更|事件|任务步骤", joined, re.IGNORECASE):
                if not read_optional(model.change_dir / "progress-change-producer-chain-matrix.md").strip():
                    errors.append(
                        f"variant-impact: progress/change parity row requires progress-change-producer-chain-matrix.md: {joined}"
                    )

    if stage in {"task-planning", "pre-execution", "all"}:
        context = read_optional(model.change_dir / "atomic-planning-context-pack.md")
        packets = flatten_text(model.packet_doc)
        decomposition = read_optional(model.change_dir / "atomic-task-decomposition.md")
        for rel in REQUIRED_OBJECT_ACTION_CONSUMER_FILES:
            if (model.change_dir / rel).exists() and rel not in context:
                errors.append(f"variant-impact: atomic-planning-context-pack.md must consume {rel}")
        if (model.change_dir / "variant-impact-matrix.md").exists() and "variant-impact-matrix.md" not in decomposition:
            errors.append("variant-impact: atomic-task-decomposition.md must map variant-impact-matrix.md rows to decomposed task edges")
        if (model.change_dir / "variant-impact-matrix.md").exists() and not re.search(
            r"variant|变体|Existing Object|Object-Action|old consumer|旧.*consumer|consumer assumption",
            packets,
            re.IGNORECASE,
        ):
            errors.append("variant-impact: atomic-issue-packets.yaml must carry variant/object-action consumer semantics into owner packets")
    return errors


def validate_progress_change_producer_chain(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"contract", "verification", "task-planning", "pre-execution", "mock-acceptance", "product-acceptance", "all"}:
        return errors
    combined = flatten_text(
        [
            model.semantic,
            model.contracts_doc,
            model.verification_doc,
            model.dag_doc,
            model.packet_doc,
            read_optional(model.change_dir / "proposal.md"),
            read_optional(model.change_dir / "spec.md"),
            read_optional(model.change_dir / "plan.md"),
            read_optional(model.change_dir / "tasks.md"),
            read_optional(model.change_dir / "existing-object-action-consumer-graph.md"),
            read_optional(model.change_dir / "variant-impact-matrix.md"),
            read_optional(model.change_dir / "stateful-behavior-matrix.md"),
        ]
    )
    path = model.change_dir / "progress-change-producer-chain-matrix.md"
    body = read_optional(path)
    if not PROGRESS_CHANGE_SIGNAL_RE.search(combined) and not body.strip():
        return errors
    if not body.strip():
        errors.append("progress-change-producer: progress/change/last-change signal exists but progress-change-producer-chain-matrix.md is missing or empty")
        return errors
    if not markdown_has_columns(body, PROGRESS_CHANGE_PRODUCER_COLUMNS):
        errors.append(f"progress-change-producer: progress-change-producer-chain-matrix.md must include columns {', '.join(PROGRESS_CHANGE_PRODUCER_COLUMNS)}")
    if not markdown_has_meaningful_rows(body):
        errors.append("progress-change-producer: progress-change-producer-chain-matrix.md must include concrete producer chain rows")
    if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
        errors.append("progress-change-producer: progress-change-producer-chain-matrix.md contains unresolved TBD/TODO/unknown value")

    chain_section = section(body, "Progress / Change Producer Chain Matrix")
    for row in markdown_table_dicts(chain_section):
        chain_id = table_get(row, "Chain ID") or "<missing>"
        joined = flatten_text(row)
        if re.search(r"\b(?:N/A|not applicable|不适用|locked N/A)\b", joined, re.IGNORECASE):
            continue
        for label in PROGRESS_CHANGE_PRODUCER_COLUMNS:
            if not table_get(row, label):
                errors.append(f"progress-change-producer: chain {chain_id} missing {label}")
        for label in ["Canonical change writer", "State owner / table", "Task/event producer", "Correlation key", "Last-change readback", "Change detail readback", "Verification", "Owner issue"]:
            value = table_get(row, label)
            strong_re = PRODUCTION_FIELD_STRONG_RE[label]
            if not value or WEAK_PRODUCER_VALUE_RE.search(value) or not strong_re.search(value):
                errors.append(f"progress-change-producer: chain {chain_id} has weak or missing production {label}: {value or '<empty>'}")
        correlation_text = " ".join(
            [
                table_get(row, "Correlation key"),
                table_get(row, "Last-change readback"),
                table_get(row, "Change detail readback"),
                table_get(row, "Verification"),
            ]
        )
        if not SAME_ID_CHAIN_RE.search(correlation_text):
            errors.append(f"progress-change-producer: chain {chain_id} lacks same-id owner/verification/correlation proof")

    if stage in {"task-planning", "pre-execution", "all"}:
        context = read_optional(model.change_dir / "atomic-planning-context-pack.md")
        packets = flatten_text(model.packet_doc)
        decomposition = read_optional(model.change_dir / "atomic-task-decomposition.md")
        dag = flatten_text(model.dag_doc) + "\n" + read_optional(model.change_dir / "tasks.md")
        if "progress-change-producer-chain-matrix.md" not in context:
            errors.append("progress-change-producer: atomic-planning-context-pack.md must consume progress-change-producer-chain-matrix.md")
        if "progress-change-producer-chain-matrix.md" not in decomposition:
            errors.append("progress-change-producer: atomic-task-decomposition.md must decompose producer chain rows")
        for required in ["change writer", "last-change", "change detail", "correlation", "progress/change producer"]:
            if not re.search(re.escape(required), packets, re.IGNORECASE):
                errors.append(f"progress-change-producer: atomic-issue-packets.yaml must carry {required} semantics")
        if not re.search(r"progress|change|last-change|producer|event|state-machine|前端.*进度|变更", dag, re.IGNORECASE):
            errors.append("progress-change-producer: task DAG must include edge from runtime/change producer to progress/change consumer")
    return errors


def validate_external_side_effect_contract(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"contract", "verification", "task-planning", "pre-execution", "mock-acceptance", "product-acceptance", "all"}:
        return errors
    combined = flatten_text(
        [
            model.contracts_doc,
            model.verification_doc,
            model.packet_doc,
            read_optional(model.change_dir / "proposal.md"),
            read_optional(model.change_dir / "spec.md"),
            read_optional(model.change_dir / "plan.md"),
            read_optional(model.change_dir / "tasks.md"),
            read_optional(model.change_dir / "external-capability-research.md"),
            read_optional(model.change_dir / "mock-acceptance-cases.yaml"),
        ]
    )
    path = model.change_dir / "external-side-effect-contract-matrix.md"
    body = read_optional(path)
    if not EXTERNAL_SIDE_EFFECT_SIGNAL_RE.search(combined) and not body.strip():
        return errors
    if not body.strip():
        errors.append("external-side-effect: external side-effect signal exists but external-side-effect-contract-matrix.md is missing or empty")
        return errors
    if not markdown_has_columns(body, EXTERNAL_SIDE_EFFECT_COLUMNS):
        errors.append(f"external-side-effect: external-side-effect-contract-matrix.md must include columns {', '.join(EXTERNAL_SIDE_EFFECT_COLUMNS)}")
    if not markdown_has_meaningful_rows(body):
        errors.append("external-side-effect: external-side-effect-contract-matrix.md must include concrete rows")
    if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
        errors.append("external-side-effect: external-side-effect-contract-matrix.md contains unresolved TBD/TODO/unknown value")
    section_text = section(body, "External Side Effect Contract Matrix")
    for row in markdown_table_dicts(section_text):
        joined = flatten_text(row)
        if re.search(r"\b(?:N/A|not applicable|不适用|locked N/A)\b", joined, re.IGNORECASE):
            continue
        effect_id = table_get(row, "Effect ID") or "<missing>"
        for label in EXTERNAL_SIDE_EFFECT_COLUMNS:
            if not table_get(row, label):
                errors.append(f"external-side-effect: effect {effect_id} missing {label}")
        for label in [
            "Production side-effect owner",
            "Required production call/resource mutation",
            "No-cloud/playground substitute boundary",
            "Minimum acceptable proof",
            "Failure/partial failure semantics",
            "State/readback consumer",
            "Contract ID",
            "Verification ID",
            "Owner issue",
        ]:
            value = table_get(row, label)
            if not value or re.search(r"\b(?:mock-only|fixture-only|frontend-only|log-only|DB-only|same as above)\b|只.*(?:mock|fixture|前端|日志|DB)|仅.*(?:mock|fixture|前端|日志|DB)", value, re.IGNORECASE):
                errors.append(f"external-side-effect: effect {effect_id} has weak or missing {label}: {value or '<empty>'}")
        proof_text = " ".join(
            [
                table_get(row, "Required production call/resource mutation"),
                table_get(row, "Minimum acceptable proof"),
                table_get(row, "State/readback consumer"),
            ]
        )
        if not re.search(r"\b(?:provider|operator|API|SDK|resource|scheduler|runtime|setCapacity|create|update|delete|readback|event|integration|mock-composition|cloud-runtime)\b|生产|调用|资源|读回|事件|运行时", proof_text, re.IGNORECASE):
            errors.append(f"external-side-effect: effect {effect_id} lacks concrete production call/readback proof")
    if stage in {"task-planning", "pre-execution", "all"}:
        context = read_optional(model.change_dir / "atomic-planning-context-pack.md")
        packets = flatten_text(model.packet_doc)
        decomposition = read_optional(model.change_dir / "atomic-task-decomposition.md")
        if "external-side-effect-contract-matrix.md" not in context:
            errors.append("external-side-effect: atomic-planning-context-pack.md must consume external-side-effect-contract-matrix.md")
        if "external-side-effect-contract-matrix.md" not in decomposition:
            errors.append("external-side-effect: atomic-task-decomposition.md must decompose external side-effect rows")
        for required in ["external_side_effects", "production side effect", "minimum acceptable proof", "substitute boundary"]:
            if not re.search(re.escape(required), packets, re.IGNORECASE):
                errors.append(f"external-side-effect: atomic-issue-packets.yaml must carry {required} semantics")
    return errors


def validate_runtime_test_topology(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"archaeology", "verification", "task-planning", "pre-execution", "all"}:
        return errors
    combined = flatten_text(
        [
            model.verification_doc,
            model.packet_doc,
            model.dag_doc,
            read_optional(model.change_dir / "proposal.md"),
            read_optional(model.change_dir / "spec.md"),
            read_optional(model.change_dir / "plan.md"),
            read_optional(model.change_dir / "tasks.md"),
            read_optional(model.change_dir / "external-side-effect-contract-matrix.md"),
            read_optional(model.change_dir / "progress-change-producer-chain-matrix.md"),
        ]
    )
    path = model.change_dir / "runtime-test-topology-matrix.md"
    body = read_optional(path)
    has_signal = bool(RUNTIME_TEST_TOPOLOGY_SIGNAL_RE.search(combined)) or bool(read_optional(model.change_dir / "external-side-effect-contract-matrix.md").strip())
    if not has_signal and not body.strip():
        return errors
    if not body.strip():
        errors.append("runtime-test-topology: runtime/proof topology signal exists but runtime-test-topology-matrix.md is missing or empty")
        return errors
    if not markdown_has_columns(body, RUNTIME_TEST_TOPOLOGY_COLUMNS):
        errors.append(f"runtime-test-topology: runtime-test-topology-matrix.md must include columns {', '.join(RUNTIME_TEST_TOPOLOGY_COLUMNS)}")
    if not markdown_has_meaningful_rows(body):
        errors.append("runtime-test-topology: runtime-test-topology-matrix.md must include concrete rows")
    if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
        errors.append("runtime-test-topology: runtime-test-topology-matrix.md contains unresolved TBD/TODO/unknown value")
    topology_section = section(body, "Runtime Test Topology Matrix")
    for row in markdown_table_dicts(topology_section):
        joined = flatten_text(row)
        if re.search(r"\b(?:N/A|not applicable|不适用|locked N/A)\b", joined, re.IGNORECASE):
            continue
        topology_id = table_get(row, "Topology ID") or "<missing>"
        for label in RUNTIME_TEST_TOPOLOGY_COLUMNS:
            if not table_get(row, label):
                errors.append(f"runtime-test-topology: topology {topology_id} missing {label}")
        proof_file = table_get(row, "Proof file/path")
        if proof_file and not re.search(r"\.(?:java|kt|scala|py|ts|tsx|js|jsx|yaml|yml|feature|sh)\b", proof_file):
            errors.append(f"runtime-test-topology: topology {topology_id} proof file/path must be concrete: {proof_file}")
        if not re.search(r"\b(?:mvn|gradle|npm|pnpm|yarn|pytest|go test|cargo|playwright|browser|curl|install|package|test)\b|测试|安装|构建", table_get(row, "Verification command"), re.IGNORECASE):
            errors.append(f"runtime-test-topology: topology {topology_id} verification command is not executable enough")
    proof_section = section(body, "Proof Owner File Matrix")
    if body.strip() and not proof_section:
        errors.append("runtime-test-topology: runtime-test-topology-matrix.md missing Proof Owner File Matrix")
    packets = flatten_text(model.packet_doc)
    dag = flatten_text(model.dag_doc) + "\n" + read_optional(model.change_dir / "tasks.md")
    for row in markdown_table_dicts(proof_section):
        joined = flatten_text(row)
        if re.search(r"\b(?:N/A|not applicable|不适用|locked N/A)\b", joined, re.IGNORECASE):
            continue
        verification_id = table_get(row, "Verification ID") or "<missing>"
        owner_issue = table_get(row, "Owner issue")
        proof_file = table_get(row, "Proof file/path").strip("`")
        must_task = table_get(row, "Must be in task-dag files?")
        must_packet = table_get(row, "Must be in packet files_to_change?")
        for label in PROOF_OWNER_FILE_COLUMNS:
            if not table_get(row, label):
                errors.append(f"runtime-test-topology: proof owner row {verification_id} missing {label}")
        if proof_file and re.search(r"\b(?:yes|true|是|required|must)\b", must_packet, re.IGNORECASE) and proof_file not in packets:
            errors.append(f"runtime-test-topology: proof file {proof_file} from {verification_id} must be in owner packet files_to_change")
        if proof_file and re.search(r"\b(?:yes|true|是|required|must)\b", must_task, re.IGNORECASE) and proof_file not in dag:
            errors.append(f"runtime-test-topology: proof file {proof_file} from {verification_id} must be in task files allowlist")
        if owner_issue and owner_issue not in packets + "\n" + dag:
            errors.append(f"runtime-test-topology: owner issue {owner_issue} for proof {verification_id} missing from packet/task DAG")
    if stage in {"task-planning", "pre-execution", "all"}:
        context = read_optional(model.change_dir / "atomic-planning-context-pack.md")
        decomposition = read_optional(model.change_dir / "atomic-task-decomposition.md")
        if "runtime-test-topology-matrix.md" not in context:
            errors.append("runtime-test-topology: atomic-planning-context-pack.md must consume runtime-test-topology-matrix.md")
        if "Proof Owner File" not in decomposition and "runtime-test-topology-matrix.md" not in decomposition:
            errors.append("runtime-test-topology: atomic-task-decomposition.md must map proof owner files into task allowlists")
    return errors


def validate_runtime_materialization_parity(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"design", "contract", "verification", "task-planning", "pre-execution", "mock-acceptance", "product-acceptance", "all"}:
        return errors
    combined = flatten_text(
        [
            model.contracts_doc,
            model.verification_doc,
            model.packet_doc,
            model.dag_doc,
            read_optional(model.change_dir / "proposal.md"),
            read_optional(model.change_dir / "spec.md"),
            read_optional(model.change_dir / "plan.md"),
            read_optional(model.change_dir / "tasks.md"),
            read_optional(model.change_dir / "decision-surface-discovery.md"),
            read_optional(model.change_dir / "external-capability-research.md"),
        ]
    )
    path = model.change_dir / "runtime-materialization-parity.md"
    body = read_optional(path)
    has_surface = "runtime-mode-materialization-parity" in read_optional(model.change_dir / "decision-surface-discovery.md")
    has_signal = has_surface or bool(RUNTIME_MATERIALIZATION_SIGNAL_RE.search(combined))
    if not has_signal and not body.strip():
        return errors
    if not body.strip():
        errors.append("runtime-materialization-parity: signal exists but runtime-materialization-parity.md is missing or empty")
        return errors

    required_sections = {
        "Runtime Mode Change Classification": RUNTIME_MATERIALIZATION_CLASSIFICATION_COLUMNS,
        "Product Capability Parity Matrix": RUNTIME_CAPABILITY_PARITY_COLUMNS,
        "Runtime Materialization Mapping": RUNTIME_MATERIALIZATION_MAPPING_COLUMNS,
    }
    for section_name, columns in required_sections.items():
        section_text = section(body, section_name)
        if not section_text:
            errors.append(f"runtime-materialization-parity: missing {section_name}")
            continue
        if not markdown_has_columns(section_text, columns):
            errors.append(f"runtime-materialization-parity: {section_name} must include columns {', '.join(columns)}")
        if not markdown_has_meaningful_rows(section_text):
            errors.append(f"runtime-materialization-parity: {section_name} must include concrete rows")
    if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
        errors.append("runtime-materialization-parity: contains unresolved TBD/TODO/unknown value")

    classification_section = section(body, "Runtime Mode Change Classification")
    for row in markdown_table_dicts(classification_section):
        joined = flatten_text(row)
        classification = table_get(row, "Classification")
        if not re.search(
            r"Additive coexisting mode|Replacement / retirement|Internal substrate refactor|Capability reduction / scoped mode|新增并存|替换|退役|内部.*重构|能力.*(?:降级|收缩)",
            classification,
            re.IGNORECASE,
        ):
            errors.append(f"runtime-materialization-parity: invalid or weak Classification: {joined}")
        if not re.search(r"\b(?:PDEC|ADEC|DEC|DESIGN-DEC|MIG-DEC|C-|VER-|T)\d{0,3}|locked|决策|契约|验证|任务", joined, re.IGNORECASE):
            errors.append(f"runtime-materialization-parity: classification row lacks locked trace: {joined}")

    capability_section = section(body, "Product Capability Parity Matrix")
    for row in markdown_table_dicts(capability_section):
        joined = flatten_text(row)
        supported = table_get(row, "Supported?")
        unsupported_expr = table_get(row, "If not supported, product/API/UI expression")
        if re.search(r"\b(?:no|false|unsupported|不支持|否)\b", supported, re.IGNORECASE):
            if not re.search(r"\b(?:hidden|disabled|rejected|unavailable|not supported|隐藏|禁用|拒绝|不可用|不支持)\b", unsupported_expr, re.IGNORECASE):
                errors.append(f"runtime-materialization-parity: unsupported capability lacks product/API/UI expression: {joined}")
        else:
            for label in ["Existing mode baseline", "New / changed mode obligation", "Contract ID", "Verification ID", "Owner issue"]:
                if not table_get(row, label):
                    errors.append(f"runtime-materialization-parity: supported capability row missing {label}: {joined}")

    mapping_section = section(body, "Runtime Materialization Mapping")
    required_inputs = [
        "Runtime artifact",
        "Product config",
        "Plugins/extensions",
        "Secrets/security config",
        "Dependency endpoints",
        "Bootstrap/entrypoint",
        "Lifecycle operations",
        "Readback/observability",
    ]
    mapping_text = mapping_section + "\n" + body
    for capability_input in required_inputs:
        if not re.search(re.escape(capability_input), mapping_text, re.IGNORECASE):
            errors.append(f"runtime-materialization-parity: mapping must consider capability input {capability_input}")
    for row in markdown_table_dicts(mapping_section):
        joined = flatten_text(row)
        if re.search(r"\b(?:N/A|not applicable|不适用|locked N/A)\b", joined, re.IGNORECASE):
            continue
        mapping_id = table_get(row, "Mapping ID") or "<missing>"
        for label in RUNTIME_MATERIALIZATION_MAPPING_COLUMNS:
            if not table_get(row, label):
                errors.append(f"runtime-materialization-parity: mapping {mapping_id} missing {label}")
        for label in ["New / changed mode materialization design", "Production owner", "Failure semantics", "Verification", "Owner issue"]:
            value = table_get(row, label)
            if not value or re.search(r"\b(?:resource exists|ASG exists|pod exists|process starts|DB state|final status|mock-only|fixture-only|same as old|same as above)\b|只.*(?:资源|状态|mock|fixture)|仅.*(?:资源|状态|mock|fixture)", value, re.IGNORECASE):
                errors.append(f"runtime-materialization-parity: mapping {mapping_id} has weak or missing {label}: {value or '<empty>'}")
    negative_section = section(body, "Runtime Parity Negative Assertions")
    if not negative_section:
        errors.append("runtime-materialization-parity: missing Runtime Parity Negative Assertions")
    elif not re.search(r"Resource created|resource exists|ASG exists|pod exists|process starts|image/AMI/container|plugins|config|secrets|资源|插件|配置|密钥", negative_section, re.IGNORECASE):
        errors.append("runtime-materialization-parity: negative assertions must reject resource-exists/image-assumption shortcuts")

    if stage in {"task-planning", "pre-execution", "all"}:
        context = read_optional(model.change_dir / "atomic-planning-context-pack.md")
        packets = flatten_text(model.packet_doc)
        decomposition = read_optional(model.change_dir / "atomic-task-decomposition.md")
        dag = flatten_text(model.dag_doc) + "\n" + read_optional(model.change_dir / "tasks.md")
        if "runtime-materialization-parity.md" not in context:
            errors.append("runtime-materialization-parity: atomic-planning-context-pack.md must consume runtime-materialization-parity.md")
        if "runtime-materialization-parity.md" not in decomposition and "runtime materialization" not in decomposition.lower():
            errors.append("runtime-materialization-parity: atomic-task-decomposition.md must decompose runtime materialization parity rows")
        for required in ["runtime materialization", "Runtime artifact", "Product config", "Plugins/extensions", "Secrets/security config", "Bootstrap/entrypoint", "Readback/observability"]:
            if not re.search(re.escape(required), packets, re.IGNORECASE):
                errors.append(f"runtime-materialization-parity: atomic-issue-packets.yaml must carry {required} semantics")
        if not re.search(r"runtime materialization|runtime-materialization|RMP-|物化", dag, re.IGNORECASE):
            errors.append("runtime-materialization-parity: task DAG must include runtime materialization owner task or provider/consumer edge")
    return errors


def validate_frontend_contract_artifacts(model: WorkflowModel, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"frontend-contract", "contract", "verification", "task-planning", "pre-execution", "all"}:
        return errors
    combined = "\n".join(
        (model.change_dir / rel).read_text(encoding="utf-8")
        for rel in [
            "plan.md",
            "proposal.md",
            "spec.md",
            "aip.md",
            "tasks.md",
            "atomic-planning-context-pack.md",
            *REQUIRED_FRONTEND_CONTRACT_FILES.keys(),
            *REFERENCE_FRONTEND_CONTRACT_FILES.keys(),
        ]
        if (model.change_dir / rel).exists()
    )
    if not re.search(
        r"frontend|UI|browser|DOM|page|route|component|form|wizard|submit|click|前端|页面|表单|浏览器|路由|组件",
        combined,
        re.IGNORECASE,
    ):
        return errors
    for rel, columns in REQUIRED_FRONTEND_CONTRACT_FILES.items():
        path = model.change_dir / rel
        body = path.read_text(encoding="utf-8") if path.exists() else ""
        if not body.strip():
            errors.append(f"frontend-contract: required artifact {rel} is missing or empty")
            continue
        if not markdown_has_columns(body, columns):
            errors.append(f"frontend-contract: {rel} must include columns {', '.join(columns)}")
        if not markdown_has_meaningful_rows(body):
            errors.append(f"frontend-contract: {rel} must include at least one meaningful data row")
        if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
            errors.append(f"frontend-contract: {rel} contains unresolved TBD/TODO/unknown value")

    reference_signal = bool(FRONTEND_REFERENCE_SIGNAL_RE.search(combined))
    if reference_signal:
        for rel, columns in REFERENCE_FRONTEND_CONTRACT_FILES.items():
            path = model.change_dir / rel
            body = path.read_text(encoding="utf-8") if path.exists() else ""
            if not body.strip():
                errors.append(
                    f"frontend-contract: reference UI signal found, but {rel} is missing or empty. "
                    "Reference UI cannot be reduced to field/selector semantics."
                )
                continue
            if not markdown_has_columns(body, columns):
                errors.append(f"frontend-contract: {rel} must include columns {', '.join(columns)}")
            if not markdown_has_meaningful_rows(body):
                errors.append(f"frontend-contract: {rel} must include at least one meaningful data row")
            if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
                errors.append(f"frontend-contract: {rel} contains unresolved TBD/TODO/unknown value")

    route_path = model.change_dir / "frontend-route-component-matrix.md"
    route_matrix = route_path.read_text(encoding="utf-8") if route_path.exists() else ""
    for row in markdown_table_rows(route_matrix):
        joined = " | ".join(row)
        if row and row[0].strip().lower() == "action id":
            continue
        if re.search(r"\b(action|click|submit|create|update|delete|save|resize|scale|wizard|创建|更新|删除|保存|扩缩|提交)\b", joined, re.IGNORECASE):
            for label, pattern in [
                ("source component", r"[/\\].+\.(?:tsx|jsx|ts|js)\b"),
                ("route/API", r"(?:/|GET|POST|PUT|PATCH|DELETE|api|route|router|接口|路由)"),
                ("landing component/file", r"[/\\].+\.(?:tsx|jsx|ts|js)\b"),
                ("mode branch", r"mode|deployment|capacity|provider|模式|部署|容量"),
                ("forbidden inherited UI/API", r"absent|hide|hidden|not\s+(?:show|render|submit|route)|no\s+|without|forbid|forbidden|禁止|隐藏|不得|不显示|不提交|不存在"),
                ("verification", r"browser|DOM|click|submit|network|route|API|screenshot|trace|浏览器|点击|提交|网络|路由|接口|截图"),
            ]:
                if not re.search(pattern, joined, re.IGNORECASE):
                    errors.append(f"frontend-contract: route/component action row lacks {label} proof: {joined}")

    field_path = model.change_dir / "frontend-mode-field-display-matrix.md"
    field_matrix = field_path.read_text(encoding="utf-8") if field_path.exists() else ""
    for row in markdown_table_rows(field_matrix):
        joined = " | ".join(row)
        if row and row[0].strip().lower() == "surface":
            continue
        for label, pattern in [
            ("must hide/absence assertion", r"absent|hide|hidden|not\s+(?:show|render|submit)|no\s+|without|forbid|forbidden|禁止|隐藏|不得|不显示|不渲染|不存在"),
            ("fixture/assertion", r"fixture|DOM|browser|visible|absent|selector|assert|截图|浏览器|断言|可见"),
        ]:
            if not re.search(pattern, joined, re.IGNORECASE):
                errors.append(f"frontend-contract: frontend-mode-field-display-matrix.md row lacks {label}: {joined}")

    browser_path = model.change_dir / "frontend-browser-verification-matrix.md"
    browser_matrix = browser_path.read_text(encoding="utf-8") if browser_path.exists() else ""
    for label, pattern in [
        ("browser/click steps", r"browser|playwright|click|submit|浏览器|点击|提交"),
        ("network/API assertions", r"network|request|response|API|GET|POST|PUT|PATCH|DELETE|接口|网络"),
        ("DOM assertions", r"\bDOM\b|visible|text|selector|disabled|enabled|文案|可见|选择器|禁用"),
        ("screenshot/trace evidence", r"screenshot|trace|HAR|video|截图|轨迹|录屏"),
    ]:
        if browser_matrix and not re.search(pattern, browser_matrix, re.IGNORECASE):
            errors.append(f"frontend-contract: frontend-browser-verification-matrix.md missing {label}")

    context_path = model.change_dir / "atomic-planning-context-pack.md"
    packet_path = model.change_dir / "atomic-issue-packets.yaml"
    context = context_path.read_text(encoding="utf-8") if context_path.exists() else ""
    packet_text = packet_path.read_text(encoding="utf-8") if packet_path.exists() else ""
    if stage in {"task-planning", "pre-execution", "all"} and (context or packet_text):
        frontend_contract_files = dict(REQUIRED_FRONTEND_CONTRACT_FILES)
        if reference_signal:
            frontend_contract_files.update(REFERENCE_FRONTEND_CONTRACT_FILES)
        for rel in frontend_contract_files:
            if rel not in context:
                errors.append(f"frontend-contract: atomic-planning-context-pack.md must consume {rel}")
        for term in [
            "frontend_user_task",
            "action_route_component",
            "mode_field_display_matrix",
            "form_state_matrix",
            "mode_negative_assertions",
            "fixture_needs",
            "browser_verification",
            "experience_rubric",
        ]:
            if term not in packet_text:
                errors.append(f"frontend-contract: atomic-issue-packets.yaml must include {term} for frontend packets")
        if reference_signal and "reference_ui_patterns" not in packet_text:
            errors.append(
                "frontend-contract: atomic-issue-packets.yaml must include reference_ui_patterns when source/frontend contract references existing UI"
            )
        errors.extend(validate_frontend_task_consumption(model, stage))
    return errors


def validate(change_dir: Path, stage: str) -> list[str]:
    model = WorkflowModel(change_dir)
    errors: list[str] = []
    execution_only_planning = (
        stage_construction_enabled(model)
        and workflow_profile(model.workflow) == "execution-only"
        and stage in {"task-planning", "pre-execution", "all"}
    )
    if not model.has_structured_sidecars():
        return [f"{change_dir}: missing structured YAML sidecars; copy templates from ai-dev-methodology/templates/*.yaml"]
    if legacy_contextpack_doc(model.workflow):
        return [
            "legacy contextpack schema v1 is frozen under its historical runtime; "
            "run workflowctl.py migrate-workflow-runtime <change-dir> --profile <profile> before using current validators"
        ]
    errors.extend(validate_workflow_runtime(model.workflow))
    errors.extend(validate_workflow_defects(change_dir))
    errors.extend(validate_stage_reopens(model))
    errors.extend(validate_workdir_identity(model))
    errors.extend(validate_stage_status(model, stage))
    errors.extend(validate_stage_receipts(model, stage))
    if stage == "all":
        stage_status = as_dict(model.workflow.get("stage_status"))
        for construction_stage in sorted(STAGE_CONSTRUCTION_STAGES):
            if stage_status.get(construction_stage) not in {None, "", "not_started", "not_applicable"}:
                errors.extend(validate_stage_construction(model, construction_stage))
    else:
        errors.extend(validate_stage_construction(model, stage))
    errors.extend(validate_pre_execution_admission(model, stage))
    errors.extend(validate_execution_state(model, stage))
    errors.extend(validate_task_status_receipts(model, stage))
    if not execution_only_planning:
        errors.extend(validate_aip_artifacts(model, stage))
        errors.extend(validate_mechanism_design_model(model, stage))
        errors.extend(validate_human_decision_records(model, stage))
        errors.extend(validate_decision_surface_routed_closure(model, stage))
    errors.extend(validate_id_shapes(model))
    errors.extend(validate_semantic_graph(model, stage))
    errors.extend(validate_semantic_carrier_projections(model, stage))

    if stage in {"contract", "verification", "task-planning", "pre-execution", "acceptance", "all"}:
        errors.extend(validate_contracts(model, stage))
    if stage in {"verification", "task-planning", "pre-execution", "acceptance", "all"}:
        errors.extend(validate_verifications(model))
    if not execution_only_planning:
        errors.extend(validate_stateful_behavior_artifacts(model, stage))
    if stage in {"task-planning", "pre-execution", "acceptance", "all"}:
        errors.extend(validate_tasks(model))
        errors.extend(validate_dag(model))
        errors.extend(validate_atomic_issue_packets(model))
        errors.extend(validate_markdown_alignment(model))
    if stage in {"pre-execution", "acceptance", "mock-acceptance", "product-acceptance", "all"}:
        errors.extend(validate_backflow(model))
    if not execution_only_planning:
        errors.extend(validate_frontend_contract_artifacts(model, stage))
    errors.extend(validate_contract_matrix_artifacts(model, stage))
    errors.extend(validate_compiler_failure_triage(model, stage))
    errors.extend(validate_task_planning_repair_ledger(model, stage))
    errors.extend(validate_atomic_issue_quality_review(model, stage))
    errors.extend(validate_multi_perspective_review(model, stage))
    if not execution_only_planning:
        errors.extend(validate_variant_impact_artifacts(model, stage))
        errors.extend(validate_progress_change_producer_chain(model, stage))
        errors.extend(validate_external_side_effect_contract(model, stage))
        errors.extend(validate_runtime_materialization_parity(model, stage))
        errors.extend(validate_runtime_test_topology(model, stage))
    errors.extend(validate_atomic_task_decomposition(model, stage))
    errors.extend(validate_mock_acceptance(model, stage))
    errors.extend(validate_no_production_downgrade_language(model, stage))
    return errors


def _row_value(row: dict[str, str], *names: str) -> str:
    lowered = {key.lower(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None:
            return value.strip()
    for key, value in row.items():
        normalized = re.sub(r"[^a-z0-9]+", "", key.lower())
        for name in names:
            if normalized == re.sub(r"[^a-z0-9]+", "", name.lower()):
                return value.strip()
    return ""


def _is_closed_or_accepted(value: str) -> bool:
    return bool(re.search(r"\b(closed|resolved|accepted[- ]risk|non[- ]blocking|done|fixed|n/a)\b|关闭|已解决|接受风险|非阻塞|不适用", value, re.IGNORECASE))


def _simple_markdown_table_dicts(markdown: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            header = None
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", cell.replace(" ", "")) for cell in cells):
            continue
        if header is None:
            header = cells
            continue
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def _placeholder_or_empty(value: str) -> bool:
    stripped = value.strip()
    return not stripped or bool(
        re.search(
            r"^<.*>$|\b(TBD|TODO|unknown|not recorded|missing|none|pass/fail|yes/no|ready / not ready)\b|待确认|未记录|未知",
            stripped,
            re.IGNORECASE,
        )
    )


def _row_has_placeholder(row: dict[str, str], *columns: str) -> bool:
    if not columns:
        return any(_placeholder_or_empty(value) for value in row.values())
    return any(_placeholder_or_empty(_row_value(row, column)) for column in columns)


def _stage_has_passed_receipt(model: WorkflowModel, stage: str) -> bool:
    state = as_dict(model.workflow.get("stage_status"))
    receipt = as_dict(as_dict(model.workflow.get("stage_receipts")).get(stage))
    return state.get(stage) == "passed" and receipt.get("status") == "passed"


def _stage_not_applicable(model: WorkflowModel, stage: str) -> bool:
    return as_dict(model.workflow.get("stage_status")).get(stage) == "not_applicable"


def _all_tasks_passed(model: WorkflowModel) -> bool:
    if not model.tasks:
        return False
    return all(task_is_passed(model, str(task_id)) for task_id in model.tasks)


def launch_execution_prerequisite_errors(model: WorkflowModel) -> list[str]:
    errors = execution_completion_errors(model)
    if stage_construction_enabled(model):
        errors.extend(validate_stage_receipts(model, "product-acceptance"))
    return errors


def validate_launch_readiness(change_dir: Path) -> list[str]:
    review_path = change_dir / "launch-readiness-review.md"
    if not review_path.exists():
        return [f"{review_path}: missing; create from ai-dev-methodology/templates/launch-readiness-review.md after PR creation"]

    model = WorkflowModel(change_dir)
    body = review_path.read_text(encoding="utf-8", errors="ignore")
    errors: list[str] = []

    required_headings = [
        "Review Input",
        "Production Launch Standard Sources",
        "Closure Review",
        "Findings",
        "Resolution Ledger",
        "Final Verdict",
    ]
    for heading in required_headings:
        if not re.search(rf"^##+\s+{re.escape(heading)}\s*$", body, re.IGNORECASE | re.MULTILINE):
            errors.append(f"launch-readiness-review.md: missing required section '{heading}'")

    review_input = first_markdown_section(body, "Review Input")
    review_fields = {
        _row_value(row, "Field"): _row_value(row, "Value")
        for row in _simple_markdown_table_dicts(review_input)
        if _row_value(row, "Field")
    }
    pr_or_diff_value = next(
        (value for key, value in review_fields.items() if re.search(r"PR|pull|diff artifact|Integration", key, re.IGNORECASE)),
        "",
    )
    base_value = next((value for key, value in review_fields.items() if re.search(r"\bBase\b|target", key, re.IGNORECASE)), "")
    head_value = next((value for key, value in review_fields.items() if re.search(r"\bHead\b|source", key, re.IGNORECASE)), "")
    diff_source_value = next((value for key, value in review_fields.items() if re.search(r"Diff source|compare", key, re.IGNORECASE)), "")

    if _placeholder_or_empty(pr_or_diff_value) or not re.search(r"https://github\.com/[^)\s]+/pull/\d+|\bPR[- #:]?\s*\d+\b|\bpull request\b|(?:^|[/\w.-])[^|\n]*(?:\.diff|\.patch|diff|compare)[^|\n]*", pr_or_diff_value, re.IGNORECASE):
        errors.append("launch-readiness-review.md: Review Input must include integration PR URL/ID or explicit equivalent diff artifact")
    if _placeholder_or_empty(base_value) or _placeholder_or_empty(head_value) or _placeholder_or_empty(diff_source_value):
        errors.append("launch-readiness-review.md: Review Input must record base/head or equivalent diff source")
    launch_git_state = current_git_state(change_dir)
    current_head = text(launch_git_state.get("head"))
    if current_head and current_head not in head_value:
        errors.append(
            "launch-readiness-review.md: Review Input Head must include the current local Git HEAD commit "
            f"{current_head}; refresh/push the PR or diff artifact before launch review"
        )
    if current_head:
        pr_url_match = re.search(r"https://github\.com/[^\s|]+/pull/\d+", pr_or_diff_value)
        pr_number_match = re.search(r"\bPR[- #:]?\s*(\d+)\b", pr_or_diff_value, re.IGNORECASE)
        pr_ref = pr_url_match.group(0) if pr_url_match else (pr_number_match.group(1) if pr_number_match else "")
        if pr_ref:
            try:
                pr_result = subprocess.run(
                    ["gh", "pr", "view", pr_ref, "--json", "headRefOid", "--jq", ".headRefOid"],
                    cwd=str(git_root_for(change_dir) or change_dir),
                    text=True,
                    capture_output=True,
                    check=False,
                )
            except FileNotFoundError:
                pr_result = None
            if pr_result is None or pr_result.returncode != 0:
                errors.append(
                    "launch-readiness-review.md: cannot verify the integration PR head with `gh pr view`; "
                    "install/authenticate gh or use an explicit equivalent diff artifact bound to current HEAD"
                )
            elif pr_result.stdout.strip() != current_head:
                errors.append(
                    f"launch-readiness-review.md: integration PR head {pr_result.stdout.strip() or '<empty>'} "
                    f"does not equal current local HEAD {current_head}"
                )
        else:
            artifact = Path(pr_or_diff_value).expanduser()
            if not artifact.is_absolute():
                artifact = (git_root_for(change_dir) or change_dir) / artifact
            if not artifact.is_file():
                errors.append(
                    "launch-readiness-review.md: equivalent diff artifact must be an existing file; "
                    f"missing {artifact}"
                )
            else:
                artifact_digest = sha256_file(artifact)
                artifact_body = artifact.read_text(encoding="utf-8", errors="replace")
                if current_head not in artifact_body:
                    errors.append(
                        "launch-readiness-review.md: equivalent diff artifact must declare the current local HEAD SHA"
                    )
                if current_head not in diff_source_value or artifact_digest not in diff_source_value:
                    errors.append(
                        "launch-readiness-review.md: equivalent Diff source must include the current local HEAD SHA "
                        "and the equivalent artifact SHA-256"
                    )
    uncommitted_business_paths = changed_paths_outside_change(change_dir)
    if uncommitted_business_paths:
        preview = ", ".join(uncommitted_business_paths[:12])
        suffix = "" if len(uncommitted_business_paths) <= 12 else f", ... (+{len(uncommitted_business_paths) - 12} more)"
        errors.append(
            "launch-readiness-review.md: current Git HEAD does not contain all business changes; "
            f"commit and refresh the PR/diff before launch review: {preview}{suffix}"
        )

    errors.extend(f"launch readiness prerequisite: {error}" for error in launch_execution_prerequisite_errors(model))
    if model.tasks and not _all_tasks_passed(model):
        missing = sorted(str(task_id) for task_id in model.tasks if not task_is_passed(model, str(task_id)))
        preview = ", ".join(missing[:12])
        suffix = "" if len(missing) <= 12 else f", ... (+{len(missing) - 12} more)"
        errors.append(f"launch-readiness-review.md: all Atomic Issues must have pass-task receipts before launch readiness; missing {preview}{suffix}")

    if stage_construction_enabled(model):
        stage_status = as_dict(model.workflow.get("stage_status"))
        for acceptance_stage in ["mock-acceptance", "product-acceptance"]:
            if stage_status.get(acceptance_stage) not in {"passed", "not_applicable"}:
                errors.append(
                    f"launch-readiness-review.md: {acceptance_stage} must be passed or explicitly not_applicable "
                    f"before launch readiness; actual={stage_status.get(acceptance_stage, 'missing')}"
                )

    mock_acceptance_needed = any((change_dir / rel).exists() for rel in [
        "mock-backend-matrix.yaml",
        "mock-frontend-action-matrix.yaml",
        "mock-acceptance-cases.yaml",
        "mock-acceptance.md",
        "mock-acceptance-execution.yaml",
    ])
    if mock_acceptance_needed and not _stage_has_passed_receipt(model, "mock-acceptance") and not _stage_not_applicable(model, "mock-acceptance"):
        errors.append("launch-readiness-review.md: mock-acceptance artifacts exist but stage_receipts.mock-acceptance is not passed")
    product_acceptance_needed = (change_dir / "acceptance" / "product-acceptance-review.md").exists()
    if product_acceptance_needed and not _stage_has_passed_receipt(model, "product-acceptance") and not _stage_not_applicable(model, "product-acceptance"):
        errors.append("launch-readiness-review.md: product acceptance artifact exists but stage_receipts.product-acceptance is not passed")

    source_terms = ["proposal.md", "spec.md", "aip.md", "plan.md", "contracts", "verification", "acceptance"]
    source_hits = sum(1 for term in source_terms if re.search(re.escape(term), body, re.IGNORECASE))
    if source_hits < 4:
        errors.append("launch-readiness-review.md: Production Launch Standard Sources must cite current requirement sources, contracts, verification, and acceptance evidence")

    acceptance_file_exists = (change_dir / "mock-acceptance.md").exists() or (change_dir / "mock-acceptance-execution.yaml").exists() or (change_dir / "acceptance" / "product-acceptance-review.md").exists()
    if acceptance_file_exists and not re.search(r"mock-acceptance|product-acceptance|acceptance/product-acceptance-review\.md|mock-acceptance-execution\.yaml", body, re.IGNORECASE):
        errors.append("launch-readiness-review.md: acceptance artifacts exist but are not referenced as review evidence")
    if not acceptance_file_exists and not re.search(r"acceptance.+(?:N/A|not applicable|not run|accepted risk|不适用|未运行|接受风险)", body, re.IGNORECASE | re.DOTALL):
        errors.append("launch-readiness-review.md: acceptance evidence must be referenced or explicitly marked N/A/Not Run with risk")

    standard_rows = _simple_markdown_table_dicts(first_markdown_section(body, "Production Launch Standard Sources"))
    for row in standard_rows:
        source = _row_value(row, "Source") or "<unknown>"
        if _row_has_placeholder(row, "Path / URL / ID", "How it defines launch standard"):
            errors.append(f"launch-readiness-review.md: Production Launch Standard Sources row '{source}' still has placeholder/empty values")

    closure_rows = _simple_markdown_table_dicts(first_markdown_section(body, "Closure Review"))
    closure_text = "\n".join(
        " ".join(row.values())
        for row in closure_rows
        if _row_value(row, "Closure", "Dimension", "Closure dimension")
    ).lower()
    for dimension in LAUNCH_READINESS_CLOSURE_DIMENSIONS:
        if dimension not in closure_text:
            errors.append(f"launch-readiness-review.md: Closure Review missing dimension '{dimension}'")
    for row in closure_rows:
        closure = _row_value(row, "Closure", "Dimension", "Closure dimension") or "<unknown>"
        if _row_has_placeholder(row, "Evidence", "Verdict", "Notes"):
            errors.append(f"launch-readiness-review.md: Closure Review row '{closure}' still has placeholder/empty values")
        verdict = _row_value(row, "Verdict")
        if verdict and not re.fullmatch(r"pass|passed|n/a|not applicable|accepted[- ]risk|是|通过|不适用|接受风险", verdict.strip(), re.IGNORECASE):
            errors.append(f"launch-readiness-review.md: Closure Review row '{closure}' verdict must be pass/N/A/accepted-risk, got '{verdict}'")

    finding_rows = [
        row for row in _simple_markdown_table_dicts(first_markdown_section(body, "Findings"))
        if _row_value(row, "Type", "Finding type", "Classification") or re.search(r"\bLRR-\d{3}\b", _row_value(row, "ID", "Finding ID"), re.IGNORECASE)
    ]
    if not finding_rows:
        errors.append("launch-readiness-review.md: Findings must contain at least one explicit row, even if only 'no findings' / allowed variance")
    for row in finding_rows:
        finding_id = _row_value(row, "ID", "Finding ID") or "<unknown>"
        finding_type = _row_value(row, "Type", "Finding type", "Classification")
        if _row_has_placeholder(row, "ID", "Type", "Severity", "Source / evidence", "Owner", "Required action", "Status"):
            errors.append(f"launch-readiness-review.md: {finding_id} finding row still has placeholder/empty values")
        if finding_type and finding_type not in LAUNCH_READINESS_FINDING_TYPES:
            errors.append(f"launch-readiness-review.md: {finding_id} has invalid finding type '{finding_type}'")
        severity = _row_value(row, "Severity", "Blocking", "Launch blocking")
        status = _row_value(row, "Status", "Closure status")
        evidence = " ".join([
            _row_value(row, "Source / evidence", "Evidence"),
            _row_value(row, "Required action", "Action"),
            status,
        ])
        if finding_type == "launch_decision_required" and not re.search(
            r"human[- ]confirmed|user[- ]confirmed|user decision|launch decision|accepted[- ]risk|scope adjusted|confirmed by|人工确认|用户确认|人.*确认|上线决策|接受风险|调整上线范围",
            evidence,
            re.IGNORECASE,
        ):
            errors.append(
                f"launch-readiness-review.md: {finding_id} is launch_decision_required but lacks human launch decision evidence"
            )
        if re.search(r"\b(blocking|yes|P0|P1|launch-blocking)\b|是|阻塞", severity, re.IGNORECASE) and not _is_closed_or_accepted(status):
            errors.append(f"launch-readiness-review.md: {finding_id} is launch-blocking but status is not closed/resolved/accepted-risk")

    fix_rows = _simple_markdown_table_dicts(first_markdown_section(body, "Resolution Ledger"))
    for row in fix_rows:
        item = _row_value(row, "Item") or "<unknown>"
        if _row_has_placeholder(row):
            errors.append(f"launch-readiness-review.md: Resolution Ledger row '{item}' still has placeholder/empty values")

    final_verdict = first_markdown_section(body, "Final Verdict")
    if re.search(r"yes/no|ready / not ready|<[^>]+>", final_verdict, re.IGNORECASE):
        errors.append("launch-readiness-review.md: Final Verdict still contains template placeholder text")
    verdict_match = re.search(r"launch_ready\s*:\s*(yes|no)\b|Launch ready\s*[:|]\s*(yes|no)\b|上线就绪\s*[:|]\s*(yes|no|是|否)", final_verdict, re.IGNORECASE)
    if not verdict_match:
        errors.append("launch-readiness-review.md: Final Verdict must include launch_ready: yes/no")
    elif verdict_match.group(1) and verdict_match.group(1).lower() != "yes":
        errors.append("launch-readiness-review.md: Final Verdict is not launch_ready: yes")
    elif verdict_match.lastindex and verdict_match.group(verdict_match.lastindex).lower() in {"no", "否"}:
        errors.append("launch-readiness-review.md: Final Verdict is not launch_ready: yes")

    blockers_match = re.search(r"open_launch_blockers\s*:\s*(\d+)|Open launch blockers\s*[:|]\s*(\d+)|未关闭上线阻塞\s*[:|]\s*(\d+)", final_verdict, re.IGNORECASE)
    if not blockers_match:
        errors.append("launch-readiness-review.md: Final Verdict must include open_launch_blockers: N")
    else:
        blocker_count = next((int(group) for group in blockers_match.groups() if group is not None), None)
        if blocker_count:
            errors.append(f"launch-readiness-review.md: Final Verdict has open_launch_blockers: {blocker_count}")

    if "workflowctl.py pass-stage" in body and not re.search(r"不得|must not|do not|not use|不支持", body, re.IGNORECASE):
        errors.append("launch-readiness-review.md: must not model launch readiness as workflowctl.py pass-stage")

    return errors


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write_yaml(path: Path, data: Any) -> None:
    if yaml is None:
        raise ValueError("PyYAML is required for workflowctl pass-stage")
    atomic_write_text(path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False))


def append_workflow_event(change_dir: Path, event_type: str, details: dict[str, Any]) -> None:
    path = change_dir / "workflow-events.yaml"
    doc = as_dict(load_yaml(path)) if path.exists() else {"schema_version": 1, "events": []}
    events = as_list(doc.get("events"))
    previous_hash = text(as_dict(events[-1]).get("event_hash")) if events else ""
    event = {
        "sequence": len(events) + 1,
        "event_type": event_type,
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "previous_hash": previous_hash,
        "details": details,
    }
    event["event_hash"] = stable_json_digest(event)
    events.append(event)
    doc["events"] = events
    write_yaml(path, doc)


def validate_workflow_events(change_dir: Path) -> list[str]:
    path = change_dir / "workflow-events.yaml"
    if not path.exists():
        return []
    doc = as_dict(load_yaml(path))
    errors: list[str] = []
    if doc.get("schema_version") != 1:
        errors.append(f"{path}: schema_version must be 1")
    previous_hash = ""
    for index, raw in enumerate(as_list(doc.get("events")), 1):
        event = as_dict(raw)
        if event.get("sequence") != index:
            errors.append(f"{path}: event sequence {event.get('sequence')} must equal {index}")
        if text(event.get("previous_hash")) != previous_hash:
            errors.append(f"{path}: event {index} previous_hash is stale")
        recorded_hash = text(event.get("event_hash"))
        expected_hash = stable_json_digest({key: value for key, value in event.items() if key != "event_hash"})
        if recorded_hash != expected_hash:
            errors.append(f"{path}: event {index} hash is forged or stale")
        previous_hash = recorded_hash
    return errors


def print_workflow_metrics(change_dir: Path) -> int:
    path = change_dir / "workflow-events.yaml"
    if not path.exists():
        print("No workflow events recorded")
        return 0
    errors = validate_workflow_events(change_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    events = [as_dict(item) for item in as_list(as_dict(load_yaml(path)).get("events"))]
    counts: dict[str, int] = defaultdict(int)
    for event in events:
        counts[text(event.get("event_type"))] += 1
    print(f"events_total: {len(events)}")
    for event_type in sorted(counts):
        print(f"{event_type}: {counts[event_type]}")
    return 0


def issue_stage_receipt(change_dir: Path, stage: str) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl pass-stage", file=sys.stderr)
        return 2
    if stage in {"pre-execution", "execution", "acceptance", "all"}:
        print(f"{stage}: pass-stage is only for prerequisite artifact stages, not admission/execution stages", file=sys.stderr)
        return 2

    validate_errors = validate(change_dir, stage)
    artifact_validator = Path(__file__).with_name("validate_artifacts.py")
    artifact_result = subprocess.run(
        [sys.executable, str(artifact_validator), str(change_dir), "--stage", stage],
        text=True,
        capture_output=True,
        check=False,
    )
    if artifact_result.returncode != 0:
        output = (artifact_result.stderr or artifact_result.stdout).strip()
        for line in output.splitlines():
            if line.strip():
                validate_errors.append(f"validate_artifacts: {line.strip()}")
    current_model = WorkflowModel(change_dir)
    receipt_errors = validate_stage_receipts(current_model, stage)
    current_stage_receipt_errors = [
        error
        for error in receipt_errors
        if error.startswith(f"stage_status.{stage}=passed")
        or error.startswith(f"stage_receipts.{stage}.")
        or error.startswith(f"stage_receipts.{stage}:")
    ]
    effective_errors = [error for error in validate_errors if error not in current_stage_receipt_errors]
    if effective_errors:
        for error in effective_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    model = WorkflowModel(change_dir)
    workflow_doc = model.workflow
    stage_status = as_dict(workflow_doc.get("stage_status"))
    stage_receipts = as_dict(workflow_doc.get("stage_receipts"))
    try:
        append_errors = plan_append_only_errors(change_dir, workflow_doc, stage)
        if append_errors:
            raise ValueError("; ".join(append_errors))
        write_stage_plan_snapshot(change_dir, stage)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    hashes = artifact_digest_map(change_dir, stage)
    missing = [
        rel
        for rel in stage_required_artifact_rels(change_dir, stage)
        if not (change_dir / rel).exists()
    ]
    if missing:
        for rel in missing:
            print(f"ERROR: {stage}: required artifact {rel} is missing", file=sys.stderr)
        return 1

    if stage == "task-planning":
        old_receipt = as_dict(stage_receipts.get("task-planning"))
        if old_receipt:
            old_upstream = as_dict(old_receipt.get("upstream_stage_receipt_hashes"))
            current_upstream = upstream_receipt_hashes_for_task_planning(workflow_doc)
            if old_upstream and old_upstream != current_upstream and not task_planning_reseal_or_regeneration_evidence(change_dir):
                print(
                    "ERROR: task-planning upstream receipt hashes changed since the previous task-planning receipt; "
                    "add Task Planning Regeneration Evidence or Task Planning Impact Proof to atomic-planning-context-pack.md "
                    "before re-sealing task-planning",
                    file=sys.stderr,
                )
                return 1

    receipt = {
        "stage": stage,
        "status": "passed",
        "issued_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "validator": "workflowctl.py",
        "command": f"python3 {Path(__file__).as_posix()} validate {stage} {change_dir.as_posix()}",
        "artifact_hashes": hashes,
        "upstream_stage_receipt_hashes": stage_upstream_receipt_hashes(workflow_doc, stage),
    }
    receipt["receipt_hash"] = canonical_receipt_hash(receipt)
    stage_status[stage] = "passed"
    stage_receipts[stage] = receipt
    workflow_doc["stage_status"] = stage_status
    workflow_doc["stage_receipts"] = stage_receipts
    write_yaml(change_dir / "workflow-state.yaml", workflow_doc)
    append_workflow_event(
        change_dir,
        "stage_passed",
        {"stage": stage, "receipt_hash": receipt["receipt_hash"]},
    )
    print(f"Stage {stage} passed and receipt written")
    return 0


def mark_stage_na(
    change_dir: Path,
    stage: str,
    decision_id: str,
    reason: str,
    product_semantics: str,
    verification: str,
) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl mark-stage-na", file=sys.stderr)
        return 2
    model = WorkflowModel(change_dir)
    errors = validate_workflow_runtime(model.workflow)
    policy = workflow_profile_policy(model.workflow)
    allowed = {text(item) for item in as_list(policy.get("whole_stage_na_allowed"))}
    if stage not in STAGE_CONSTRUCTION_STAGES:
        errors.append(f"{stage}: whole-stage N/A is unsupported")
    if stage not in allowed:
        errors.append(f"{stage}: whole-stage N/A is forbidden for profile {workflow_profile(model.workflow)}")
    if not re.fullmatch(rf"(?:{DECISION_ID_PATTERN}|AUTH-\d{{3}})", decision_id):
        errors.append(f"{stage}: decision-id must be a concrete workflow decision ID")
    for name, value in [("reason", reason), ("product-semantics", product_semantics), ("verification", verification)]:
        if len(value.strip()) < 12:
            errors.append(f"{stage}: --{name} must be concrete (at least 12 characters)")
    status = as_dict(model.workflow.get("stage_status")).get(stage)
    if status == "passed":
        errors.append(f"{stage}: cannot replace a passed receipt with N/A without backflow")
    for prerequisite in effective_stage_prerequisites(model.workflow, stage):
        if prerequisite == "execution":
            errors.extend(execution_completion_errors(model))
        elif as_dict(model.workflow.get("stage_status")).get(prerequisite) not in {"passed", "not_applicable"}:
            errors.append(f"{stage}: prerequisite {prerequisite} is not receipted")
    receipt_errors = validate_stage_receipts(model, stage)
    current_receipt_prefixes = (
        f"stage_status.{stage}=not_applicable",
        f"stage_na_receipts.{stage}.",
        f"stage_na_receipts.{stage}:",
    )
    errors.extend(error for error in receipt_errors if not error.startswith(current_receipt_prefixes))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    workflow_doc = model.workflow
    receipt = {
        "stage": stage,
        "status": "not_applicable",
        "issued_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "validator": "workflowctl.py",
        "command": f"python3 {Path(__file__).as_posix()} mark-stage-na {stage} {change_dir.as_posix()}",
        "profile": workflow_profile(workflow_doc),
        "decision_id": decision_id,
        "reason": reason.strip(),
        "product_semantics": product_semantics.strip(),
        "verification": verification.strip(),
        "upstream_stage_receipt_hashes": stage_upstream_receipt_hashes(workflow_doc, stage),
    }
    receipt["receipt_hash"] = canonical_receipt_hash(receipt)
    statuses = as_dict(workflow_doc.get("stage_status"))
    statuses[stage] = "not_applicable"
    na_receipts = as_dict(workflow_doc.get("stage_na_receipts"))
    na_receipts[stage] = receipt
    stage_receipts = as_dict(workflow_doc.get("stage_receipts"))
    stage_receipts.pop(stage, None)
    workflow_doc["stage_status"] = statuses
    workflow_doc["stage_na_receipts"] = na_receipts
    workflow_doc["stage_receipts"] = stage_receipts
    write_yaml(change_dir / "workflow-state.yaml", workflow_doc)
    append_workflow_event(
        change_dir,
        "stage_marked_na",
        {"stage": stage, "decision_id": decision_id, "receipt_hash": receipt["receipt_hash"]},
    )
    print(f"Stage {stage} marked not_applicable with a verified receipt")
    return 0


def validate_workflow_defects_doc(
    path: Path,
    doc: dict[str, Any],
    require_promoted: bool = False,
) -> list[str]:
    marker_present = any(
        "late_detection_defect" in read_optional(candidate)
        for candidate in path.parent.glob("*.md")
        if candidate.is_file()
    )
    errors: list[str] = []
    if doc.get("schema_version") != 1:
        errors.append(f"{path}: schema_version must be 1")
    signatures: dict[str, str] = {}
    required = [
        "gate", "failure_signature", "detected_stage", "should_have_caught_stage",
        "classification", "affected_rule", "affected_artifact", "repair_action",
        "promotion_target", "runtime_version_introduced", "recurrence_count", "status",
    ]
    for defect_id, raw in as_dict(doc.get("defects")).items():
        defect = as_dict(raw)
        if not re.fullmatch(r"LD-\d{3}", str(defect_id)):
            errors.append(f"{path}: invalid defect ID {defect_id}")
        for field in required:
            if not nonempty(defect.get(field)):
                errors.append(f"{path}: {defect_id}.{field} is required")
        signature = text(defect.get("failure_signature")).lower()
        if signature in signatures:
            errors.append(f"{path}: duplicate failure_signature in {signatures[signature]} and {defect_id}; increment recurrence_count instead")
        elif signature:
            signatures[signature] = str(defect_id)
        if not isinstance(defect.get("recurrence_count"), int) or int(defect.get("recurrence_count", 0)) < 1:
            errors.append(f"{path}: {defect_id}.recurrence_count must be >= 1")
        if "machine" not in text(defect.get("promotion_target")).lower() and "test" not in text(defect.get("promotion_target")).lower() and ".yaml" not in text(defect.get("promotion_target")):
            errors.append(f"{path}: {defect_id}.promotion_target must name a machine rule or test target")
        status = text(defect.get("status")).lower()
        if status not in {"open", "promoted", "closed"}:
            errors.append(f"{path}: {defect_id}.status must be open/promoted/closed")
        if status in {"promoted", "closed"}:
            if not nonempty(defect.get("runtime_version_fixed")):
                errors.append(f"{path}: {defect_id}.runtime_version_fixed is required after promotion")
            evidence = as_dict(defect.get("promotion_evidence"))
            for field in ["target_paths", "target_components", "target_hashes", "test_id", "runtime_manifest_hash", "promoted_at"]:
                if not nonempty(evidence.get(field)):
                    errors.append(f"{path}: {defect_id}.promotion_evidence.{field} is required")
            if text(defect.get("promotion_receipt_hash")) != canonical_defect_promotion_hash(defect):
                errors.append(f"{path}: {defect_id}.promotion_receipt_hash is forged or stale")
            if status == "promoted":
                manifest = load_workflow_runtime_manifest()
                current_version = text(manifest.get("runtime_version"))
                fixed_version = text(defect.get("runtime_version_fixed"))
                root = WORKFLOW_RUNTIME_MANIFEST_PATH.parent.parent
                component_paths = {
                    (root / text(as_dict(component).get("path"))).resolve(): name
                    for name, component in as_dict(manifest.get("components")).items()
                    if text(as_dict(component).get("path"))
                }
                target_paths = [Path(text(item)).expanduser().resolve() for item in as_list(evidence.get("target_paths"))]
                target_components = as_dict(evidence.get("target_components"))
                recorded_hashes = as_dict(evidence.get("target_hashes"))
                if fixed_version == current_version:
                    if text(evidence.get("runtime_manifest_hash")) != sha256_file(WORKFLOW_RUNTIME_MANIFEST_PATH):
                        errors.append(f"{path}: {defect_id}.promotion_evidence.runtime_manifest_hash is stale")
                    for target in target_paths:
                        component_name = component_paths.get(target)
                        if not component_name or not target.is_file():
                            errors.append(f"{path}: {defect_id} promotion target is not a current runtime component: {target}")
                        elif text(target_components.get(target.as_posix())) != component_name:
                            errors.append(f"{path}: {defect_id} promotion target component mapping is stale: {target}")
                        elif text(recorded_hashes.get(target.as_posix())) != sha256_file(target):
                            errors.append(f"{path}: {defect_id} promotion target hash is stale: {target}")
                    test_id = text(evidence.get("test_id"))
                    if test_id and not any(
                        test_id in target.read_text(encoding="utf-8", errors="replace")
                        for target in target_paths
                        if target.is_file()
                    ):
                        errors.append(f"{path}: {defect_id} promotion test/rule ID is absent from targets")
                else:
                    workflow_doc = as_dict(load_yaml(path.parent / "workflow-state.yaml"))
                    fixed_migration = next(
                        (
                            as_dict(item)
                            for item in as_list(workflow_doc.get("runtime_migrations"))
                            if text(as_dict(item).get("to_version")) == fixed_version
                            and text(as_dict(item).get("current_manifest_hash")) == text(evidence.get("runtime_manifest_hash"))
                        ),
                        {},
                    )
                    if not fixed_migration or text(fixed_migration.get("audit_hash")) != canonical_audit_hash(fixed_migration):
                        errors.append(f"{path}: {defect_id} has no intact historical runtime migration for its promotion")
                    else:
                        fixed_hashes = as_dict(fixed_migration.get("current_component_hashes"))
                        for target in target_paths:
                            component_name = text(target_components.get(target.as_posix()))
                            if not component_name or text(fixed_hashes.get(component_name)) != text(recorded_hashes.get(target.as_posix())):
                                errors.append(f"{path}: {defect_id} historical promotion target is not sealed by its runtime migration: {target}")
                            current_component = as_dict(as_dict(manifest.get("components")).get(component_name))
                            current_path = root / text(current_component.get("path"))
                            if not current_component or not current_path.is_file():
                                errors.append(f"{path}: {defect_id} promoted runtime component was removed: {component_name}")
                            elif text(evidence.get("test_id")) not in current_path.read_text(encoding="utf-8", errors="replace"):
                                errors.append(f"{path}: {defect_id} promoted rule/test ID was removed from current component: {component_name}")
        elif require_promoted:
            errors.append(
                f"{path}: {defect_id} remains open; promote the machine rule/regression test before passing another gate"
            )
    return errors


def validate_workflow_defects(change_dir: Path, require_promoted: bool = True) -> list[str]:
    path = change_dir / "workflow-defects.yaml"
    marker_present = any(
        "late_detection_defect" in read_optional(candidate)
        for candidate in change_dir.glob("*.md")
        if candidate.is_file()
    )
    if marker_present and not path.exists():
        return [f"{path}: late_detection_defect marker requires a structured defect ledger"]
    if not path.exists():
        return []
    return validate_workflow_defects_doc(path, as_dict(load_yaml(path)), require_promoted)


def record_late_defect(
    change_dir: Path,
    gate: str,
    failure_signature: str,
    detected_stage: str,
    should_have_caught_stage: str,
    classification: str,
    affected_rule: str,
    affected_artifact: str,
    repair_action: str,
    promotion_target: str,
) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl record-late-defect", file=sys.stderr)
        return 2
    path = change_dir / "workflow-defects.yaml"
    manifest = load_workflow_runtime_manifest()
    doc = as_dict(load_yaml(path)) if path.exists() else {
        "schema_version": 1,
        "runtime_version": text(manifest.get("runtime_version")),
        "defects": {},
    }
    candidate = copy.deepcopy(doc)
    defects = as_dict(candidate.get("defects"))
    normalized = re.sub(r"\s+", " ", failure_signature.strip()).lower()
    for defect_id, raw in defects.items():
        defect = as_dict(raw)
        if re.sub(r"\s+", " ", text(defect.get("failure_signature"))).lower() == normalized:
            defect.update(
                {
                    "gate": gate,
                    "failure_signature": failure_signature.strip(),
                    "detected_stage": detected_stage,
                    "should_have_caught_stage": should_have_caught_stage,
                    "classification": classification,
                    "affected_rule": affected_rule,
                    "affected_artifact": affected_artifact,
                    "repair_action": repair_action,
                    "promotion_target": promotion_target,
                    "runtime_version_introduced": text(load_workflow_runtime_manifest().get("runtime_version")),
                    "runtime_version_fixed": "",
                    "recurrence_count": int(defect.get("recurrence_count", 1)) + 1,
                    "status": "open",
                }
            )
            defect.pop("promotion_evidence", None)
            defect.pop("promotion_receipt_hash", None)
            validation_errors = validate_workflow_defects_doc(path, candidate, False)
            if validation_errors:
                for error in validation_errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            write_yaml(path, candidate)
            append_workflow_event(
                change_dir,
                "late_defect_recorded",
                {"defect_id": defect_id, "failure_signature": failure_signature.strip(), "recurrence": defect["recurrence_count"]},
            )
            print(f"Late defect {defect_id} recurrence incremented and fields refreshed")
            return 0
    next_number = max([int(str(key).split("-")[-1]) for key in defects if re.fullmatch(r"LD-\d{3}", str(key))] or [0]) + 1
    defect_id = f"LD-{next_number:03d}"
    defects[defect_id] = {
        "gate": gate,
        "failure_signature": failure_signature.strip(),
        "detected_stage": detected_stage,
        "should_have_caught_stage": should_have_caught_stage,
        "classification": classification,
        "affected_rule": affected_rule,
        "affected_artifact": affected_artifact,
        "repair_action": repair_action,
        "promotion_target": promotion_target,
        "runtime_version_introduced": text(manifest.get("runtime_version")),
        "runtime_version_fixed": "",
        "recurrence_count": 1,
        "status": "open",
    }
    candidate["defects"] = defects
    validation_errors = validate_workflow_defects_doc(path, candidate, False)
    if validation_errors:
        for error in validation_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    write_yaml(path, candidate)
    append_workflow_event(
        change_dir,
        "late_defect_recorded",
        {"defect_id": defect_id, "failure_signature": failure_signature.strip(), "recurrence": 1},
    )
    print(f"Late defect {defect_id} recorded")
    return 0


def promote_late_defect(
    change_dir: Path,
    defect_id: str,
    target_paths: list[str],
    test_id: str,
) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl promote-late-defect", file=sys.stderr)
        return 2
    path = change_dir / "workflow-defects.yaml"
    doc = as_dict(load_yaml(path, required=True))
    defects = as_dict(doc.get("defects"))
    defect = as_dict(defects.get(defect_id))
    if not defect:
        print(f"ERROR: {defect_id}: missing from workflow-defects.yaml", file=sys.stderr)
        return 1
    if text(defect.get("status")).lower() != "open":
        print(f"ERROR: {defect_id}: only open defects can be promoted", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parent.parent
    resolved: list[Path] = []
    for raw in target_paths:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        if not candidate.is_file():
            print(f"ERROR: promotion target does not exist: {candidate}", file=sys.stderr)
            return 1
        resolved.append(candidate)
    if not resolved:
        print("ERROR: at least one --target-path is required", file=sys.stderr)
        return 1
    manifest = load_workflow_runtime_manifest()
    component_paths = {
        (root / text(as_dict(component).get("path"))).resolve(): name
        for name, component in as_dict(manifest.get("components")).items()
        if text(as_dict(component).get("path"))
    }
    outside_manifest = [candidate for candidate in resolved if candidate.resolve() not in component_paths]
    if outside_manifest:
        print(
            "ERROR: promotion targets must be released runtime components: "
            + ", ".join(candidate.as_posix() for candidate in outside_manifest),
            file=sys.stderr,
        )
        return 1
    regression_target = (root / "scripts" / "validate_skill_suite.py").resolve()
    if regression_target not in {candidate.resolve() for candidate in resolved}:
        print("ERROR: promotion requires scripts/validate_skill_suite.py as a regression target", file=sys.stderr)
        return 1
    behavior_targets = [candidate for candidate in resolved if candidate.resolve() != regression_target]
    if not behavior_targets:
        print("ERROR: promotion requires at least one behavior-affecting runtime component", file=sys.stderr)
        return 1
    if test_id not in regression_target.read_text(encoding="utf-8", errors="replace"):
        print(f"ERROR: promotion test ID {test_id} is absent from validate_skill_suite.py", file=sys.stderr)
        return 1
    if not any(test_id in candidate.read_text(encoding="utf-8", errors="replace") for candidate in behavior_targets):
        print(f"ERROR: promotion rule ID {test_id} is absent from behavior targets", file=sys.stderr)
        return 1
    introduced = text(defect.get("runtime_version_introduced"))
    current_version = text(manifest.get("runtime_version"))
    if not introduced or introduced == current_version:
        print(
            f"ERROR: {defect_id}: publish a new runtime version before promotion "
            f"(introduced={introduced or '<empty>'}, current={current_version})",
            file=sys.stderr,
        )
        return 1
    workflow_doc = as_dict(load_yaml(change_dir / "workflow-state.yaml", required=True))
    matching_migration = next(
        (
            as_dict(item)
            for item in reversed(as_list(workflow_doc.get("runtime_migrations")))
            if text(as_dict(item).get("to_version")) == current_version
            and text(defect.get("should_have_caught_stage")) in as_list(as_dict(item).get("invalidated_stages"))
        ),
        {},
    )
    if not matching_migration:
        print(
            f"ERROR: {defect_id}: latest runtime migration did not invalidate should_have_caught_stage "
            f"{defect.get('should_have_caught_stage')}",
            file=sys.stderr,
        )
        return 1
    if text(matching_migration.get("audit_hash")) != canonical_audit_hash(matching_migration):
        print(f"ERROR: {defect_id}: matching runtime migration audit is forged or stale", file=sys.stderr)
        return 1
    if text(matching_migration.get("current_manifest_hash")) != sha256_file(WORKFLOW_RUNTIME_MANIFEST_PATH):
        print(f"ERROR: {defect_id}: matching runtime migration does not seal the installed manifest", file=sys.stderr)
        return 1
    previous_hashes = as_dict(matching_migration.get("previous_component_hashes"))
    current_hashes = as_dict(matching_migration.get("current_component_hashes"))
    if (
        not text(previous_hashes.get("stage_construction_contract"))
        or text(previous_hashes.get("stage_construction_contract"))
        == text(current_hashes.get("stage_construction_contract"))
        or text(current_hashes.get("stage_construction_contract"))
        != text(as_dict(as_dict(manifest.get("components")).get("stage_construction_contract")).get("sha256"))
    ):
        print(f"ERROR: {defect_id}: migration does not prove a released stage construction rule change", file=sys.stderr)
        return 1
    defect["status"] = "promoted"
    defect["runtime_version_fixed"] = text(manifest.get("runtime_version"))
    defect["promotion_evidence"] = {
        "target_paths": [candidate.as_posix() for candidate in resolved],
        "target_components": {
            candidate.as_posix(): component_paths[candidate.resolve()] for candidate in resolved
        },
        "target_hashes": {candidate.as_posix(): sha256_file(candidate) for candidate in resolved},
        "test_id": test_id,
        "runtime_manifest_hash": sha256_file(WORKFLOW_RUNTIME_MANIFEST_PATH),
        "promoted_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    defect["promotion_receipt_hash"] = canonical_defect_promotion_hash(defect)
    defects[defect_id] = defect
    doc["defects"] = defects
    validation_errors = validate_workflow_defects_doc(path, doc, False)
    if validation_errors:
        for error in validation_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    write_yaml(path, doc)
    append_workflow_event(
        change_dir,
        "late_defect_promoted",
        {"defect_id": defect_id, "test_id": test_id, "target_paths": defect["promotion_evidence"]["target_paths"]},
    )
    print(f"Late defect {defect_id} promoted with verified rule/test evidence")
    return 0


def begin_execution(change_dir: Path) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl begin-execution", file=sys.stderr)
        return 2

    validate_errors = validate(change_dir, "pre-execution")
    artifact_validator = Path(__file__).with_name("validate_artifacts.py")
    artifact_result = subprocess.run(
        [sys.executable, str(artifact_validator), str(change_dir), "--stage", "pre-execution"],
        text=True,
        capture_output=True,
        check=False,
    )
    if artifact_result.returncode != 0:
        output = (artifact_result.stderr or artifact_result.stdout).strip()
        for line in output.splitlines():
            if line.strip():
                validate_errors.append(f"validate_artifacts: {line.strip()}")
    if validate_errors:
        for error in validate_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    model = WorkflowModel(change_dir)
    workflow_doc = model.workflow
    stage_status = as_dict(workflow_doc.get("stage_status"))
    if stage_status.get("execution") not in {None, "", "not_started"}:
        print(f"ERROR: execution already started or invalid status: {stage_status.get('execution')}", file=sys.stderr)
        return 1

    prereq_receipts = stage_upstream_receipt_hashes(workflow_doc, "pre-execution")
    receipt = {
        "status": "started",
        "issued_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "validator": "workflowctl.py",
        "command": f"python3 {Path(__file__).as_posix()} begin-execution {change_dir.as_posix()}",
        "artifact_hashes": artifact_digest_map(change_dir, "pre-execution"),
        "sealed_artifact_hashes": sealed_artifact_digest_map(change_dir),
        "stage_receipt_hashes": prereq_receipts,
        "git_state": current_git_state(change_dir),
    }
    receipt["receipt_hash"] = canonical_receipt_hash(receipt)
    stage_status["execution"] = "in_progress"
    workflow_doc["stage_status"] = stage_status
    workflow_doc["execution_receipt"] = receipt
    workflow_doc.setdefault("task_receipts", {})
    write_yaml(change_dir / "workflow-state.yaml", workflow_doc)
    append_workflow_event(
        change_dir,
        "execution_started",
        {"receipt_hash": receipt["receipt_hash"], "task_count": len(model.tasks)},
    )
    print("Execution started and receipt written")
    return 0


def admit_task(change_dir: Path, task_id: str) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl admit-task", file=sys.stderr)
        return 2
    model = WorkflowModel(change_dir)
    if task_id not in model.tasks:
        print(f"ERROR: {task_id}: unknown task", file=sys.stderr)
        return 1

    errors = execution_receipt_errors(model)
    errors.extend(validate_task_receipt_chain(model, task_id))
    errors.extend(validate_stage_receipts(model, "pre-execution"))
    errors.extend(validate_atomic_issue_packets(model))
    errors.extend(pre_admit_baseline_errors(model, task_id))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    task = as_dict(model.tasks.get(task_id))
    allowlist = task_files(task)
    if not allowlist:
        print(f"ERROR: {task_id}: task-dag files allowlist is empty", file=sys.stderr)
        return 1
    current_errors = validate_task_diff(change_dir, task_id)
    # A task may be admitted before any task receipt exists, so ignore the
    # expected not-admitted error while still rejecting stale execution state.
    current_errors = [error for error in current_errors if "task is not admitted" not in error]
    if current_errors:
        for error in current_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    workflow_doc = model.workflow
    receipts = as_dict(workflow_doc.get("task_receipts"))
    issue_path = change_dir / str(task.get("issue", ""))
    packet_path = change_dir / "atomic-issue-packets.yaml"
    repo_root = git_root_for(change_dir)
    baseline_changed_paths = sorted(git_changed_paths(repo_root)) if repo_root is not None else []
    baseline_changed_path_hashes = (
        changed_path_digest_map(repo_root, set(baseline_changed_paths)) if repo_root is not None else {}
    )
    receipt = {
        "task": task_id,
        "status": "admitted",
        "issued_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "validator": "workflowctl.py",
        "command": f"python3 {Path(__file__).as_posix()} admit-task {task_id} {change_dir.as_posix()}",
        "file_allowlist": allowlist,
        "issue_path": str(task.get("issue", "")),
        "issue_hash": sha256_file(issue_path) if issue_path.exists() else "",
        "packet_hash": sha256_file(packet_path) if packet_path.exists() else "",
        "baseline_changed_paths": baseline_changed_paths,
        "baseline_changed_path_hashes": baseline_changed_path_hashes,
        "predecessor_receipts": {
            predecessor: as_dict(task_receipt_for(model, predecessor)).get("receipt_hash")
            for predecessor in sorted(predecessor_tasks(model, task_id))
        },
        "execution_receipt_hash": as_dict(workflow_doc.get("execution_receipt")).get("receipt_hash"),
    }
    receipt["receipt_hash"] = canonical_receipt_hash(receipt)
    receipts[task_id] = receipt
    workflow_doc["task_receipts"] = receipts
    write_yaml(change_dir / "workflow-state.yaml", workflow_doc)
    append_workflow_event(
        change_dir,
        "task_admitted",
        {"task_id": task_id, "receipt_hash": receipt["receipt_hash"]},
    )
    print(f"Task {task_id} admitted and file allowlist sealed")
    return 0


def command_exit_for_task_diff(change_dir: Path, task_id: str) -> int:
    errors = validate_task_diff(change_dir, task_id)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Task diff validation passed for {task_id}")
    return 0


def print_task_review_hashes(change_dir: Path, task_id: str) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl review-hashes", file=sys.stderr)
        return 2
    model = WorkflowModel(change_dir)
    if task_id not in model.tasks:
        print(f"ERROR: {task_id}: unknown task", file=sys.stderr)
        return 1
    errors = admitted_task_receipt_errors(model, task_id)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    hashes = current_changed_path_hashes_for_task(model, task_id)
    print(yaml.safe_dump(hashes, allow_unicode=True, sort_keys=True))
    return 0


def declared_proof_files_for_task(change_dir: Path, task_id: str) -> set[str]:
    declared: set[str] = set()
    for rel, section_name, owner_labels, file_labels in [
        (
            "runtime-test-topology-matrix.md",
            "Proof Owner File Matrix",
            ("Owner issue",),
            ("Proof file/path", "Fixture/support file"),
        ),
        (
            "atomic-task-decomposition.md",
            "Proof Owner Allowlist Matrix",
            ("Owner Txxx",),
            ("Proof file/path", "Fixture/support file/path"),
        ),
    ]:
        body = read_optional(change_dir / rel)
        if not body:
            continue
        for row in markdown_table_dicts(section(body, section_name)):
            owners = " ".join(table_get(row, label) for label in owner_labels)
            if task_id not in owners:
                continue
            for label in file_labels:
                value = table_get(row, label).strip("`")
                if value and not re.search(r"\b(?:N/A|none|not applicable|不适用|无)\b", value, re.IGNORECASE):
                    declared.add(value)
    return declared


def append_allowlist_recovery(
    workflow_doc: dict[str, Any],
    task_id: str,
    add_files: list[str],
    backflow_id: str,
    reason: str,
) -> None:
    recoveries = as_list(workflow_doc.get("allowlist_recoveries"))
    recovery = {
        "task": task_id,
        "files": add_files,
        "backflow_id": backflow_id,
        "reason": reason,
        "recovered_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "command": (
            f"python3 {Path(__file__).as_posix()} recover-task-allowlist {task_id} "
            f"<change-dir> --backflow-id {backflow_id} --add-file ..."
        ),
    }
    recovery["recovery_hash"] = stable_json_digest(
        {
            "task": task_id,
            "files": add_files,
            "backflow_id": backflow_id,
            "reason": reason,
            "recovered_at": recovery["recovered_at"],
        }
    )
    recoveries.append(recovery)
    workflow_doc["allowlist_recoveries"] = recoveries


def ignorable_reseal_error(error: str) -> bool:
    return any(
        marker in error
        for marker in [
            "execution_receipt artifact hash mismatch",
            "execution_receipt sealed artifact hash mismatch",
            "planning artifacts changed after begin-execution",
            "sealed planning artifacts changed after execution started",
            "sealed planning artifact changed during execution",
            "pre-execution admission: stage_status.execution must be not_started",
            "pre-execution admission: code/worktree changes exist before the gate passed",
            "stage must be rerun and re-receipted after artifact edits",
            "artifact hash mismatch for",
        ]
    )


def ignorable_reseal_validation_error(change_dir: Path, error: str) -> bool:
    if ignorable_reseal_error(error):
        return True
    if (
        "stage_receipts.task-planning upstream receipt hashes are stale" in error
        and task_planning_reseal_or_regeneration_evidence(change_dir)
    ):
        return True
    return False


def execution_reseal_stage_order(workflow_doc: dict[str, Any]) -> list[str]:
    stage_status = as_dict(workflow_doc.get("stage_status"))
    ordered: list[str] = []
    for stage in TASK_PLANNING_UPSTREAM_RECEIPT_STAGES + ["task-planning"]:
        if stage not in ordered and stage_status.get(stage) in {"passed", "not_applicable"}:
            ordered.append(stage)
    for stage in STAGE_PREREQUISITES["pre-execution"]:
        if stage not in ordered and stage_status.get(stage) in {"passed", "not_applicable"}:
            ordered.append(stage)
    return ordered


def refresh_stage_receipt_chain(
    change_dir: Path,
    workflow_doc: dict[str, Any],
    stages: list[str],
    reason: str,
    recovered_at: str,
) -> list[str]:
    stage_status = as_dict(workflow_doc.get("stage_status"))
    stage_receipts = as_dict(workflow_doc.get("stage_receipts"))
    na_receipts = as_dict(workflow_doc.get("stage_na_receipts"))
    resealed: list[str] = []
    for stage in stages:
        status = text(stage_status.get(stage))
        source = na_receipts if status == "not_applicable" else stage_receipts
        receipt = as_dict(source.get(stage))
        if not receipt:
            continue
        if status == "passed":
            receipt["artifact_hashes"] = artifact_digest_map(change_dir, stage)
        receipt["upstream_stage_receipt_hashes"] = stage_upstream_receipt_hashes(workflow_doc, stage)
        receipt["receipt_recovered_at"] = recovered_at
        receipt["receipt_recovery_reason"] = reason
        receipt["receipt_hash"] = canonical_receipt_hash(receipt)
        source[stage] = receipt
        resealed.append(stage)
    workflow_doc["stage_receipts"] = stage_receipts
    workflow_doc["stage_na_receipts"] = na_receipts
    return resealed


def invalidate_acceptance_receipts(workflow_doc: dict[str, Any]) -> list[str]:
    stage_status = as_dict(workflow_doc.get("stage_status"))
    stage_receipts = as_dict(workflow_doc.get("stage_receipts"))
    na_receipts = as_dict(workflow_doc.get("stage_na_receipts"))
    invalidated: list[str] = []
    for stage in ["mock-acceptance", "product-acceptance"]:
        if stage_status.get(stage) not in {None, "", "not_started"}:
            stage_status[stage] = "pending-rewrite"
            invalidated.append(stage)
        stage_receipts.pop(stage, None)
        na_receipts.pop(stage, None)
    workflow_doc["stage_status"] = stage_status
    workflow_doc["stage_receipts"] = stage_receipts
    workflow_doc["stage_na_receipts"] = na_receipts
    return invalidated


def backflow_declared_artifact_patterns(trigger: dict[str, Any]) -> list[str]:
    invalidates = as_dict(trigger.get("invalidates"))
    return [str(item).strip().strip("/") for item in as_list(invalidates.get("artifacts")) if str(item).strip()]


def rel_matches_declared_artifact(rel: str, patterns: list[str]) -> bool:
    normalized = rel.strip("/")
    for pattern in patterns:
        candidate = pattern.strip("/")
        if not candidate:
            continue
        if candidate in {"*", "**"}:
            return True
        if candidate.endswith("/"):
            if normalized.startswith(candidate):
                return True
        elif candidate.endswith("/**"):
            if normalized.startswith(candidate[:-3].rstrip("/") + "/"):
                return True
        elif any(ch in candidate for ch in "*?[]"):
            if fnmatch.fnmatch(normalized, candidate):
                return True
        elif normalized == candidate or normalized.startswith(candidate.rstrip("/") + "/"):
            return True
    return False


def undeclared_reseal_artifacts(change_dir: Path, trigger: dict[str, Any]) -> list[str]:
    patterns = backflow_declared_artifact_patterns(trigger)
    changed = planning_paths_changed_after_execution_start(change_dir)
    if not changed:
        return []
    return [rel for rel in changed if not rel_matches_declared_artifact(rel, patterns)]


def refresh_execution_and_task_receipts(change_dir: Path, workflow_doc: dict[str, Any], task_id: str, reason: str) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    refresh_stage_receipt_chain(
        change_dir,
        workflow_doc,
        ["task-planning", "pre-execution"],
        reason,
        now,
    )
    stage_receipts = as_dict(workflow_doc.get("stage_receipts"))

    execution_receipt = as_dict(workflow_doc.get("execution_receipt"))
    if execution_receipt:
        prereq_receipts = stage_upstream_receipt_hashes(workflow_doc, "pre-execution")
        execution_receipt["artifact_hashes"] = artifact_digest_map(change_dir, "pre-execution")
        execution_receipt["sealed_artifact_hashes"] = sealed_artifact_digest_map(change_dir)
        execution_receipt["stage_receipt_hashes"] = prereq_receipts
        execution_receipt["git_state"] = current_git_state(change_dir)
        execution_receipt["receipt_recovered_at"] = now
        execution_receipt["receipt_recovery_reason"] = reason
        execution_receipt["receipt_hash"] = canonical_receipt_hash(execution_receipt)
        workflow_doc["execution_receipt"] = execution_receipt

    model = WorkflowModel(change_dir)
    task = as_dict(model.tasks.get(task_id))
    receipts = as_dict(workflow_doc.get("task_receipts"))
    receipt = as_dict(receipts.get(task_id))
    if receipt:
        repo_root = git_root_for(change_dir)
        baseline_changed_paths = sorted(git_changed_paths(repo_root)) if repo_root is not None else []
        baseline_changed_path_hashes = (
            changed_path_digest_map(repo_root, set(baseline_changed_paths)) if repo_root is not None else {}
        )
        issue_path = change_dir / str(task.get("issue", ""))
        packet_path = change_dir / "atomic-issue-packets.yaml"
        allowlist = task_files(task)
        receipt["file_allowlist"] = allowlist
        receipt["issue_hash"] = sha256_file(issue_path) if issue_path.exists() else ""
        receipt["packet_hash"] = sha256_file(packet_path) if packet_path.exists() else ""
        receipt["baseline_changed_paths"] = baseline_changed_paths
        receipt["baseline_changed_path_hashes"] = baseline_changed_path_hashes
        receipt["execution_receipt_hash"] = as_dict(workflow_doc.get("execution_receipt")).get("receipt_hash")
        receipt["receipt_recovered_at"] = now
        receipt["receipt_recovery_reason"] = reason
        receipt["receipt_hash"] = canonical_receipt_hash(receipt)
        receipts[task_id] = receipt
        workflow_doc["task_receipts"] = receipts


def reseal_execution_backflow(change_dir: Path, trigger_id: str, reason: str) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl reseal-execution-backflow", file=sys.stderr)
        return 2

    model = WorkflowModel(change_dir)
    trigger = as_dict(model.backflow_triggers.get(trigger_id))
    if not trigger:
        print(f"ERROR: {trigger_id}: missing backflow trigger; create backflow.yaml trigger first", file=sys.stderr)
        return 1

    workflow_path = change_dir / "workflow-state.yaml"
    workflow_doc = as_dict(load_yaml(workflow_path, required=True))
    stage_status = as_dict(workflow_doc.get("stage_status"))
    if stage_status.get("execution") != "in_progress":
        print(
            "ERROR: reseal-execution-backflow is only for execution=in_progress local backflow; "
            "use pass-stage/begin-execution before execution starts",
            file=sys.stderr,
        )
        return 1

    invalidates = as_dict(trigger.get("invalidates"))
    if not any(as_list(invalidates.get(key)) for key in ["decisions", "contracts", "verifications", "tasks"]):
        print(
            f"ERROR: {trigger_id}: invalidates is empty; run workflowctl.py backflow after recording the trigger, "
            "then repair affected artifacts before reseal",
            file=sys.stderr,
        )
        return 1
    if trigger.get("status") in {None, "", "open", "blocked"}:
        print(
            f"ERROR: {trigger_id}: backflow trigger must be resolved/closed after affected artifacts are repaired "
            "before reseal-execution-backflow can refresh sealed receipts",
            file=sys.stderr,
        )
        return 1
    undeclared_artifacts = undeclared_reseal_artifacts(change_dir, trigger)
    if undeclared_artifacts:
        preview = ", ".join(undeclared_artifacts[:12])
        suffix = "" if len(undeclared_artifacts) <= 12 else f", ... (+{len(undeclared_artifacts) - 12} more)"
        print(
            f"ERROR: {trigger_id}: planning artifacts changed after execution started but are not listed in "
            f"backflow invalidates.artifacts: {preview}{suffix}",
            file=sys.stderr,
        )
        return 1

    compiler = Path(__file__).with_name("atomic_issue_compile.py")
    compile_result = subprocess.run([sys.executable, str(compiler), str(change_dir)], text=True, capture_output=True, check=False)
    if compile_result.returncode != 0:
        output = (compile_result.stderr or compile_result.stdout).strip()
        print(f"ERROR: atomic_issue_compile failed: {output}", file=sys.stderr)
        return 1
    check_result = subprocess.run(
        [sys.executable, str(compiler), "--check", str(change_dir)],
        text=True,
        capture_output=True,
        check=False,
    )
    if check_result.returncode != 0:
        output = (check_result.stderr or check_result.stdout).strip()
        print(f"ERROR: atomic_issue_compile --check failed: {output}", file=sys.stderr)
        return 1

    for stage in ["task-planning", "pre-execution"]:
        validate_errors = [
            error
            for error in validate(change_dir, stage)
            if not ignorable_reseal_validation_error(change_dir, error)
        ]
        if validate_errors:
            for error in validate_errors:
                print(f"ERROR: {stage}: {error}", file=sys.stderr)
            return 1

    artifact_validator = Path(__file__).with_name("validate_artifacts.py")
    for stage in ["task-planning", "pre-execution"]:
        artifact_result = subprocess.run(
            [sys.executable, str(artifact_validator), str(change_dir), "--stage", stage],
            text=True,
            capture_output=True,
            check=False,
        )
        if artifact_result.returncode != 0:
            output = (artifact_result.stderr or artifact_result.stdout).strip()
            filtered = [
                line
                for line in output.splitlines()
                if not ignorable_reseal_validation_error(change_dir, line)
            ]
            if filtered:
                for line in filtered:
                    print(f"ERROR: validate_artifacts {stage}: {line}", file=sys.stderr)
                return 1

    model = WorkflowModel(change_dir)
    trigger = as_dict(model.backflow_triggers.get(trigger_id))
    impact = compute_backflow_impact(model, trigger)
    impacted_tasks = set(impact["direct_tasks"]) | set(impact["propagated_tasks"])
    unresolved_direct = []
    for task_id in sorted(impact["direct_tasks"]):
        status = text(as_dict(model.tasks.get(task_id)).get("status")).lower()
        if status in {"blocked", "pending-rewrite", "superseded", ""}:
            unresolved_direct.append(f"{task_id}:{status or 'missing-status'}")
    if unresolved_direct:
        print(
            f"ERROR: {trigger_id}: direct impacted tasks must be repaired before reseal; unresolved: "
            + ", ".join(unresolved_direct),
            file=sys.stderr,
        )
        return 1

    workflow_doc = as_dict(load_yaml(workflow_path, required=True))
    stage_status = as_dict(workflow_doc.get("stage_status"))
    resealed_stages = refresh_stage_receipt_chain(
        change_dir,
        workflow_doc,
        execution_reseal_stage_order(workflow_doc),
        f"{trigger_id}: {reason}",
        datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )
    stage_receipts = as_dict(workflow_doc.get("stage_receipts"))

    execution_receipt = as_dict(workflow_doc.get("execution_receipt"))
    if not execution_receipt:
        print("ERROR: execution_receipt missing; cannot reseal execution backflow", file=sys.stderr)
        return 1
    prereq_receipts = stage_upstream_receipt_hashes(workflow_doc, "pre-execution")
    execution_receipt["artifact_hashes"] = artifact_digest_map(change_dir, "pre-execution")
    execution_receipt["sealed_artifact_hashes"] = sealed_artifact_digest_map(change_dir)
    execution_receipt["stage_receipt_hashes"] = prereq_receipts
    execution_receipt["git_state"] = current_git_state(change_dir)
    execution_receipt["receipt_recovered_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    execution_receipt["receipt_recovery_reason"] = f"{trigger_id}: {reason}"
    execution_receipt["invalidated_tasks"] = sorted(impacted_tasks)
    execution_receipt["receipt_hash"] = canonical_receipt_hash(execution_receipt)
    workflow_doc["execution_receipt"] = execution_receipt

    receipts = as_dict(workflow_doc.get("task_receipts"))
    removed: list[str] = []
    for task_id in sorted(impacted_tasks):
        if task_id in receipts:
            removed.append(task_id)
            receipts.pop(task_id, None)
    workflow_doc["task_receipts"] = receipts
    invalidated_acceptance_stages = invalidate_acceptance_receipts(workflow_doc)
    reseals = as_list(workflow_doc.get("backflow_reseals"))
    reseals.append(
        {
            "trigger": trigger_id,
            "reason": reason,
            "resealed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "resealed_stage_receipts": resealed_stages,
            "invalidated_tasks": sorted(impacted_tasks),
            "removed_task_receipts": removed,
            "invalidated_acceptance_stages": invalidated_acceptance_stages,
            "command": (
                f"python3 {Path(__file__).as_posix()} reseal-execution-backflow "
                f"{change_dir.as_posix()} {trigger_id}"
            ),
        }
    )
    workflow_doc["backflow_reseals"] = reseals
    write_yaml(workflow_path, workflow_doc)
    append_workflow_event(
        change_dir,
        "execution_backflow_resealed",
        {
            "trigger_id": trigger_id,
            "resealed_stages": resealed_stages,
            "invalidated_tasks": sorted(impacted_tasks),
            "invalidated_acceptance_stages": invalidated_acceptance_stages,
        },
    )
    print("Execution backflow resealed")
    print(f"  trigger: {trigger_id}")
    print(f"  resealed_stage_receipts: {', '.join(resealed_stages) or '-'}")
    print(f"  invalidated_tasks: {', '.join(sorted(impacted_tasks)) or '-'}")
    print(f"  removed_task_receipts: {', '.join(removed) or '-'}")
    print(f"  invalidated_acceptance_stages: {', '.join(invalidated_acceptance_stages) or '-'}")
    return 0


def recover_task_allowlist(change_dir: Path, task_id: str, add_files: list[str], backflow_id: str, reason: str) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl recover-task-allowlist", file=sys.stderr)
        return 2
    model = WorkflowModel(change_dir)
    if task_id not in model.tasks:
        print(f"ERROR: {task_id}: unknown task", file=sys.stderr)
        return 1
    if backflow_id not in model.backflow_triggers:
        print(f"ERROR: {backflow_id}: missing backflow trigger; create backflow before allowlist recovery", file=sys.stderr)
        return 1
    declared = declared_proof_files_for_task(change_dir, task_id)
    missing_decl = [path for path in add_files if path not in declared]
    if missing_decl:
        print(
            "ERROR: proof files must be declared in runtime-test-topology-matrix.md or atomic-task-decomposition.md before recovery: "
            + ", ".join(missing_decl),
            file=sys.stderr,
        )
        return 1

    task_dag_path = change_dir / "task-dag.yaml"
    packet_path = change_dir / "atomic-issue-packets.yaml"
    task_dag = as_dict(load_yaml(task_dag_path, required=True))
    packet_doc = as_dict(load_yaml(packet_path, required=True))
    original_task_dag_text = task_dag_path.read_text(encoding="utf-8")
    original_packet_text = packet_path.read_text(encoding="utf-8")
    workflow_path = change_dir / "workflow-state.yaml"
    original_workflow_text = workflow_path.read_text(encoding="utf-8") if workflow_path.exists() else ""
    tasks_doc = as_dict(task_dag.get("tasks"))
    task = as_dict(tasks_doc.get(task_id))
    if not task:
        print(f"ERROR: {task_id}: missing from task-dag.yaml", file=sys.stderr)
        return 1
    files = as_list(task.get("files"))
    for path in add_files:
        if path not in files:
            files.append(path)
    task["files"] = files
    tasks_doc[task_id] = task
    task_dag["tasks"] = tasks_doc

    packets_doc = as_dict(packet_doc.get("packets"))
    packet = as_dict(packets_doc.get(task_id))
    if not packet:
        print(f"ERROR: {task_id}: missing packet", file=sys.stderr)
        return 1
    files_to_change = as_list(packet.get("files_to_change"))
    existing = {str(as_dict(row).get("path")) for row in files_to_change}
    for path in add_files:
        if path not in existing:
            files_to_change.append(
                {
                    "path": path,
                    "change": "Proof owner file added by workflowctl recover-task-allowlist",
                    "notes": f"Backflow {backflow_id}: {reason}",
                }
            )
    packet["files_to_change"] = files_to_change
    packets_doc[task_id] = packet
    packet_doc["packets"] = packets_doc

    write_yaml(task_dag_path, task_dag)
    write_yaml(packet_path, packet_doc)

    compiler = Path(__file__).with_name("atomic_issue_compile.py")
    result = subprocess.run([sys.executable, str(compiler), str(change_dir)], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        atomic_write_text(task_dag_path, original_task_dag_text)
        atomic_write_text(packet_path, original_packet_text)
        if original_workflow_text:
            atomic_write_text(workflow_path, original_workflow_text)
        output = (result.stderr or result.stdout).strip()
        print(f"ERROR: atomic_issue_compile failed: {output}", file=sys.stderr)
        return 1

    workflow_doc = as_dict(load_yaml(workflow_path, required=True))
    append_allowlist_recovery(workflow_doc, task_id, add_files, backflow_id, reason)
    refresh_execution_and_task_receipts(
        change_dir,
        workflow_doc,
        task_id,
        f"{backflow_id}: {reason}",
    )
    write_yaml(workflow_path, workflow_doc)
    append_workflow_event(
        change_dir,
        "task_allowlist_recovered",
        {"task_id": task_id, "files": add_files, "backflow_id": backflow_id},
    )
    print(f"Recovered allowlist for {task_id}: {', '.join(add_files)}")
    return 0


def verification_log_has_task(change_dir: Path, task_id: str) -> bool:
    entries = verification_entries_for_task(verification_log_payload(change_dir), task_id)
    return bool(entries and verification_entry_passed(entries[-1]))


def verification_log_payload(change_dir: Path) -> Any:
    payloads: list[Any] = []
    for rel in ("task-verification-log.yaml", "execution-state.yaml"):
        path = change_dir / rel
        if path.exists():
            payloads.append(load_yaml(path))
    return payloads


def verification_entries_for_task(payload: Any, task_id: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        explicit_owner = text(payload.get("task")) or text(payload.get("task_id"))
        if explicit_owner == task_id:
            entries.append(payload)
        for key, value in payload.items():
            if str(key) == task_id and isinstance(value, dict):
                entries.append(value)
            elif key not in {"task", "task_id"}:
                entries.extend(verification_entries_for_task(value, task_id))
    elif isinstance(payload, list):
        for item in payload:
            entries.extend(verification_entries_for_task(item, task_id))
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        digest = stable_json_digest(entry)
        if digest not in seen:
            seen.add(digest)
            unique.append(entry)
    return unique


def verification_entry_passed(entry: dict[str, Any]) -> bool:
    outcome = " ".join(
        text(entry.get(key))
        for key in ("status", "result", "verdict", "outcome")
        if text(entry.get(key))
    ) or flatten_text(entry)
    if re.search(r"\b(?:fail(?:ed|ure)?|error|blocked|not[- ]run)\b|失败|错误|阻塞|未运行", outcome, re.IGNORECASE):
        return False
    return bool(re.search(r"\bpass(?:ed)?\b|通过|成功", outcome, re.IGNORECASE))


def task_semantic_review_payload(change_dir: Path) -> Any:
    path = change_dir / "task-semantic-review.yaml"
    if path.exists():
        return load_yaml(path)
    return {}


def semantic_review_entries_for_task(payload: Any, task_id: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for key in ("reviews", "entries", "tasks"):
            for item in as_list(payload.get(key)):
                item_dict = as_dict(item)
                if (
                    str(item_dict.get("task")) == task_id
                    or str(item_dict.get("task_id")) == task_id
                    or task_id in flatten_text(item_dict.get("scope"))
                ):
                    entries.append(item_dict)
        for key, value in payload.items():
            if str(key) == task_id and isinstance(value, dict):
                entry = dict(value)
                entry.setdefault("task", task_id)
                entries.append(entry)
            elif key not in {"reviews", "entries", "tasks"}:
                entries.extend(semantic_review_entries_for_task(value, task_id))
    elif isinstance(payload, list):
        for item in payload:
            entries.extend(semantic_review_entries_for_task(item, task_id))
    return entries


def latest_semantic_review_entry(change_dir: Path, task_id: str) -> dict[str, Any]:
    entries = semantic_review_entries_for_task(task_semantic_review_payload(change_dir), task_id)
    if not entries:
        return {}
    return entries[-1]


def current_changed_path_hashes_for_task(model: WorkflowModel, task_id: str) -> dict[str, str]:
    repo_root = git_root_for(model.change_dir)
    if repo_root is None:
        return {}
    receipt = task_receipt_for(model, task_id)
    allowlist = [str(item) for item in as_list(receipt.get("file_allowlist")) if str(item).strip()]
    paths: set[str] = set()
    for path in git_changed_paths(repo_root):
        if path_matches_allowlist(path, allowlist):
            paths.add(path)
    return changed_path_digest_map(repo_root, paths)


def task_semantic_review_errors(model: WorkflowModel, task_id: str) -> list[str]:
    errors: list[str] = []
    entry = latest_semantic_review_entry(model.change_dir, task_id)
    if not entry:
        return [
            f"{task_id}: missing task-semantic-review.yaml entry; "
            "run task-local semantic review before pass-task"
        ]

    verdict = text(entry.get("verdict")).lower().replace("_", "-")
    if verdict not in {"pass", "passed", "no-findings", "no-blocking-findings"}:
        errors.append(f"{task_id}: semantic review verdict must be pass/no-findings, got {entry.get('verdict')!r}")

    reviewer_type = text(entry.get("reviewer_type")).lower().replace("_", "-")
    if reviewer_type not in {"readonly-subagent", "read-only-subagent"}:
        errors.append(
            f"{task_id}: semantic review reviewer_type must be readonly-subagent or read-only-subagent; main-local fallback is not allowed, got {entry.get('reviewer_type')!r}"
        )
    errors.extend(validate_subagent_execution_proof(entry, f"{task_id}: task-semantic-review", model.change_dir))

    for key in ("issue_alignment", "contract_alignment", "verification_alignment", "diff_scope_alignment"):
        value = text(entry.get(key)).lower().replace("_", "-")
        if value not in {"pass", "passed", "ok", "no-findings", "no-blocking-findings"}:
            errors.append(f"{task_id}: semantic review {key} must pass, got {entry.get(key)!r}")

    blocking = as_list(entry.get("blocking_findings")) + as_list(entry.get("blockers"))
    blocking = [item for item in blocking if nonempty(item)]
    if blocking:
        errors.append(f"{task_id}: semantic review has blocking findings; fix or backflow before pass-task")

    required_sections = flatten_text(entry.get("checked_sections"))
    if not re.search(r"provided|contract|obligation|契约", required_sections, re.IGNORECASE):
        errors.append(
            f"{task_id}: semantic review checked_sections must mention contract/provided obligations"
        )
    if not re.search(r"negative|forbidden|verification|assertion|验证|负向|禁止|断言", required_sections, re.IGNORECASE):
        errors.append(
            f"{task_id}: semantic review checked_sections must mention verification/negative assertions"
        )

    if "changed_path_hashes" not in entry:
        errors.append(f"{task_id}: semantic review changed_path_hashes is missing")
    else:
        recorded_hashes = as_dict(entry.get("changed_path_hashes"))
        current_hashes = current_changed_path_hashes_for_task(model, task_id)
        if {str(k): str(v) for k, v in recorded_hashes.items()} != current_hashes:
            errors.append(
                f"{task_id}: semantic review changed_path_hashes is stale; rerun review after current diff changes"
            )

    return errors


def frontend_task_verification_errors(model: WorkflowModel, task_id: str) -> list[str]:
    errors: list[str] = []
    if task_id not in frontend_task_ids(model):
        return errors
    payload = verification_log_payload(model.change_dir)
    entries = verification_entries_for_task(payload, task_id)
    if not entries:
        return [f"{task_id}: frontend task lacks task-verification-log.yaml/execution-state.yaml entries"]
    passed_text = flatten_text([
        entry
        for entry in entries
        if re.search(r"\bpass(?:ed)?\b|通过|成功", flatten_text(entry), re.IGNORECASE)
    ])
    not_run_text = flatten_text([
        entry
        for entry in entries
        if NOT_RUN_RE.search(flatten_text(entry))
    ])
    if not STRONG_FRONTEND_PROOF_RE.search(passed_text):
        errors.append(
            f"{task_id}: frontend task cannot pass with only build/lint/typecheck/payload evidence; "
            "requires passed browser/DOM/click/network/screenshot-or-trace evidence"
        )
    if WEAK_FRONTEND_PROOF_RE.search(passed_text) and not STRONG_FRONTEND_PROOF_RE.search(passed_text):
        errors.append(f"{task_id}: frontend task passed evidence is weak build/lint/typecheck only")
    if not_run_text and re.search(r"\bbrowser|playwright|DOM|click|submit|network|screenshot|trace|浏览器|点击|网络|截图", not_run_text, re.IGNORECASE):
        if not re.search(r"mock-frontend-action-matrix\.yaml|mock-acceptance-cases\.yaml|case[_-]?id|UI-ACT-\d+", not_run_text, re.IGNORECASE):
            errors.append(
                f"{task_id}: frontend browser proof is not_run/deferred without a concrete mock frontend action case id"
            )
        else:
            errors.append(
                f"{task_id}: frontend browser proof is not_run/deferred; pass-task cannot mark frontend UI issue passed until delegated case passes"
            )
    packet = as_dict(model.packets.get(task_id))
    action_ids = [
        text(as_dict(row).get("action_id"))
        for row in as_list(packet.get("action_route_component"))
        if text(as_dict(row).get("action_id"))
    ]
    for action_id in action_ids:
        if action_id not in passed_text:
            errors.append(f"{task_id}: passed frontend evidence must mention row-level action {action_id}")
    return errors


def backend_task_verification_errors(model: WorkflowModel, task_id: str) -> list[str]:
    errors: list[str] = []
    if task_id not in backend_task_ids(model):
        return errors
    packet = as_dict(model.packets.get(task_id))
    task = as_dict(model.tasks.get(task_id))
    if BACKEND_BROWSER_PROOF_RE.search(
        flatten_text([packet.get("verification"), packet.get("browser_verification"), packet.get("action_route_component")])
    ):
        errors.append(f"{task_id}: backend task claims browser/DOM/render proof; UI proof must live in frontend/mock acceptance tasks")
    if not BACKEND_BEHAVIOR_SIGNAL_RE.search(flatten_text([packet, task])):
        return errors
    payload = verification_log_payload(model.change_dir)
    entries = verification_entries_for_task(payload, task_id)
    if not entries:
        return [f"{task_id}: backend behavior task lacks task-verification-log.yaml/execution-state.yaml entries"]
    passed_text = flatten_text([
        entry
        for entry in entries
        if re.search(r"\bpass(?:ed)?\b|通过|成功", flatten_text(entry), re.IGNORECASE)
    ])
    if not BACKEND_TEST_PROOF_RE.search(passed_text):
        errors.append(
            f"{task_id}: backend behavior task cannot pass with compile/build evidence only; "
            "requires targeted unit/integration/API/runtime assertions"
        )
    if BACKEND_COMPILE_ONLY_RE.search(passed_text) and not BACKEND_TEST_PROOF_RE.search(passed_text):
        errors.append(f"{task_id}: backend passed evidence is compile-only")
    for row in as_list(packet.get("backend_behavior_verification")):
        row_dict = as_dict(row)
        behavior_id = text(row_dict.get("behavior_id"))
        if behavior_id and behavior_id not in passed_text:
            errors.append(f"{task_id}: passed backend evidence must mention behavior_id {behavior_id}")
    return errors


def mock_task_verification_errors(model: WorkflowModel, task_id: str) -> list[str]:
    target = mock_acceptance_task_target(model, task_id)
    if not target:
        return []
    validator = SKILLS_ROOT / "mock-acceptance-gate" / "scripts" / "validate_mock_acceptance_cases.py"
    if not validator.exists():
        return [f"{task_id}: mock acceptance validator is missing: {validator}"]
    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            str(model.change_dir),
            "--mode",
            "execution",
            "--target",
            target,
            "--owner-task",
            task_id,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    errors: list[str] = []
    output = (result.stderr or result.stdout).strip()
    for line in output.splitlines():
        if line.strip():
            errors.append(f"{task_id}: mock execution ledger incomplete: {line.strip()}")
    return errors


def pass_task(change_dir: Path, task_id: str) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl pass-task", file=sys.stderr)
        return 2
    model = WorkflowModel(change_dir)
    if task_id not in model.tasks:
        print(f"ERROR: {task_id}: unknown task", file=sys.stderr)
        return 1
    errors = validate_task_diff(change_dir, task_id)
    errors.extend(validate_task_receipt_chain(model, task_id))
    if not verification_log_has_task(change_dir, task_id):
        errors.append(
            f"{task_id}: missing passing verification evidence in task-verification-log.yaml or execution-state.yaml; "
            "do not write verification results into sealed tasks.md"
        )
    if not verification_entries_for_task(verification_log_payload(change_dir), task_id):
        errors.append(
            f"{task_id}: verification log must contain a structured task entry so pass-task can seal task-local evidence"
        )
    errors.extend(frontend_task_verification_errors(model, task_id))
    errors.extend(backend_task_verification_errors(model, task_id))
    errors.extend(mock_task_verification_errors(model, task_id))
    errors.extend(task_semantic_review_errors(model, task_id))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    workflow_doc = model.workflow
    receipts = as_dict(workflow_doc.get("task_receipts"))
    admitted = as_dict(receipts.get(task_id))
    task = as_dict(model.tasks.get(task_id))
    semantic_review_entry = latest_semantic_review_entry(change_dir, task_id)
    semantic_review_hash = stable_json_digest(semantic_review_entry)
    receipt = dict(admitted)
    receipt.update(
        {
            "task": task_id,
            "status": "passed",
            "passed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "validator": "workflowctl.py",
            "command": f"python3 {Path(__file__).as_posix()} pass-task {task_id} {change_dir.as_posix()}",
            "diff_validated": True,
            "verification_log": "task-verification-log.yaml or execution-state.yaml",
            "verification_log_hash": stable_json_digest(
                verification_entries_for_task(verification_log_payload(change_dir), task_id)
            ),
            "semantic_review_log": "task-semantic-review.yaml",
            "semantic_review_hash": semantic_review_hash,
            "semantic_review_verdict": semantic_review_entry.get("verdict"),
            "provided_contracts": as_list(task.get("provides")),
            "verification": as_list(task.get("verification")),
            "git_state": current_git_state(change_dir),
        }
    )
    repo_root = git_root_for(change_dir)
    receipt["passed_changed_path_hashes"] = (
        changed_path_digest_map(repo_root, git_changed_paths(repo_root)) if repo_root is not None else {}
    )
    declared_outputs: set[str] = set()
    if repo_root is not None:
        for rel in task_files(task):
            if any(ch in rel for ch in "*?[]"):
                continue
            candidate = repo_root / rel
            if candidate.is_file():
                declared_outputs.add(rel)
    receipt["passed_declared_output_hashes"] = (
        changed_path_digest_map(repo_root, declared_outputs) if repo_root is not None else {}
    )
    receipt["passed_git_commit"] = text(as_dict(receipt.get("git_state")).get("head"))
    receipt["receipt_hash"] = canonical_receipt_hash(receipt)
    receipts[task_id] = receipt
    workflow_doc["task_receipts"] = receipts
    write_yaml(change_dir / "workflow-state.yaml", workflow_doc)
    append_workflow_event(
        change_dir,
        "task_passed",
        {"task_id": task_id, "receipt_hash": receipt["receipt_hash"]},
    )
    print(f"Task {task_id} passed and receipt written")
    return 0


def print_graph(change_dir: Path) -> int:
    model = WorkflowModel(change_dir)
    print("digraph workflow {")
    for req_id, req in {**model.requirements, **model.scenarios}.items():
        print(f'  "{req_id}" [shape=box];')
        for target in as_list(as_dict(req).get("consumed_by")):
            print(f'  "{req_id}" -> "{target}";')
    for cid, contract in model.contracts.items():
        c = as_dict(contract)
        for src in as_list(c.get("source")):
            print(f'  "{src}" -> "{cid}";')
        if c.get("provider_issue"):
            print(f'  "{cid}" -> "{c.get("provider_issue")}" [label="provider"];')
        for task_id in as_list(c.get("consumer_issues")):
            print(f'  "{cid}" -> "{task_id}" [label="consumer"];')
        for ver_id in as_list(c.get("verification")):
            print(f'  "{cid}" -> "{ver_id}" [label="verifies"];')
    for edge in model.edges:
        e = as_dict(edge)
        if e.get("from") and e.get("to"):
            print(f'  "{e.get("from")}" -> "{e.get("to")}" [label="{e.get("type", "")}"];')
    print("}")
    return 0


def downstream_tasks(model: WorkflowModel, seed_tasks: set[str]) -> set[str]:
    graph: dict[str, set[str]] = defaultdict(set)
    for edge in model.edges:
        e = as_dict(edge)
        src = str(e.get("from", ""))
        dst = str(e.get("to", ""))
        if src in model.tasks and dst in model.tasks:
            graph[src].add(dst)

    seen: set[str] = set()
    queue = deque(seed_tasks)
    while queue:
        tid = queue.popleft()
        for nxt in graph.get(tid, set()):
            if nxt not in seen and nxt not in seed_tasks:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def compute_backflow_impact(model: WorkflowModel, trigger: dict[str, Any]) -> dict[str, set[str]]:
    invalidates = as_dict(trigger.get("invalidates"))
    decisions = set(map(str, as_list(invalidates.get("decisions"))))
    contracts = set(map(str, as_list(invalidates.get("contracts"))))
    verifications = set(map(str, as_list(invalidates.get("verifications"))))
    direct_tasks = set(map(str, as_list(invalidates.get("tasks"))))

    for cid, raw in model.contracts.items():
        contract = as_dict(raw)
        if decisions & set(map(str, as_list(contract.get("source")))):
            contracts.add(cid)

    for dec_id in list(decisions):
        decision = as_dict(model.decisions.get(dec_id))
        for affected in map(str, as_list(decision.get("affects"))):
            if affected in model.decisions:
                decisions.add(affected)
            elif affected in model.contracts:
                contracts.add(affected)
            elif affected in model.verifications:
                verifications.add(affected)
            elif affected in model.tasks:
                direct_tasks.add(affected)

    for cid in contracts:
        contract = as_dict(model.contracts.get(cid))
        verifications |= set(map(str, as_list(contract.get("verification"))))
        if contract.get("provider_issue"):
            direct_tasks.add(str(contract.get("provider_issue")))
        direct_tasks |= set(map(str, as_list(contract.get("consumer_issues"))))

    for vid, raw in model.verifications.items():
        ver = as_dict(raw)
        if (decisions | contracts) & set(map(str, as_list(ver.get("source")))):
            verifications.add(vid)

    for tid, raw in model.tasks.items():
        task = as_dict(raw)
        task_decisions = set(map(str, as_list(task.get("decisions"))))
        task_contracts = set(map(str, as_list(task.get("consumes")))) | set(map(str, as_list(task.get("provides"))))
        task_verifications = set(map(str, as_list(task.get("verification"))))
        if (decisions & task_decisions) or (contracts & task_contracts) or (verifications & task_verifications):
            direct_tasks.add(tid)

    propagated_tasks = downstream_tasks(model, direct_tasks)
    return {
        "decisions": decisions,
        "contracts": contracts,
        "verifications": verifications,
        "direct_tasks": direct_tasks,
        "propagated_tasks": propagated_tasks,
    }


def apply_backflow(change_dir: Path, trigger_id: str) -> int:
    if yaml is None:
        print("PyYAML is required for workflowctl backflow", file=sys.stderr)
        return 2
    model = WorkflowModel(change_dir)
    trigger = as_dict(model.backflow_triggers.get(trigger_id))
    if not trigger:
        print(f"{trigger_id}: not found in backflow.yaml", file=sys.stderr)
        return 1
    impact = compute_backflow_impact(model, trigger)
    changed = False

    for dec_id in impact["decisions"]:
        dec = as_dict(model.decisions.get(dec_id))
        if dec and dec.get("status") == "locked":
            dec["status"] = "pending-rewrite"
            model.decisions[dec_id] = dec
            changed = True
    for contract_id in impact["contracts"]:
        contract = as_dict(model.contracts.get(contract_id))
        if contract and contract.get("status") == "locked":
            contract["status"] = "pending-rewrite"
            model.contracts[contract_id] = contract
            changed = True
    for task_id in impact["direct_tasks"]:
        task = as_dict(model.tasks.get(task_id))
        if task and task.get("status") not in {"blocked", "pending-rewrite", "pending-rerun"}:
            task["status"] = "pending-rewrite"
            model.tasks[task_id] = task
            changed = True
    for task_id in impact["propagated_tasks"]:
        task = as_dict(model.tasks.get(task_id))
        if task and task.get("status") not in {"blocked", "pending-rewrite", "pending-rerun"}:
            task["status"] = "pending-rerun"
            model.tasks[task_id] = task
            changed = True
    for ver_id in impact["verifications"]:
        ver = as_dict(model.verifications.get(ver_id))
        if ver and ver.get("status") not in {"blocked", "pending-rerun", "not_run"}:
            ver["status"] = "pending-rerun"
            model.verifications[ver_id] = ver
            changed = True
    invalidates = as_dict(trigger.get("invalidates"))
    merged_invalidates = {
        "artifacts": as_list(invalidates.get("artifacts")),
        "decisions": sorted(impact["decisions"]),
        "contracts": sorted(impact["contracts"]),
        "verifications": sorted(impact["verifications"]),
        "tasks": sorted(impact["direct_tasks"] | impact["propagated_tasks"]),
    }
    if merged_invalidates != invalidates:
        trigger["invalidates"] = merged_invalidates
        model.backflow_triggers[trigger_id] = trigger
        changed = True
    if changed:
        model.semantic["decisions"] = model.decisions
        model.contracts_doc["contracts"] = model.contracts
        model.dag_doc["tasks"] = model.tasks
        model.verification_doc["verifications"] = model.verifications
        model.backflow_doc["triggers"] = model.backflow_triggers
        write_yaml(change_dir / "semantic-objects.yaml", model.semantic)
        write_yaml(change_dir / "contracts.yaml", model.contracts_doc)
        write_yaml(change_dir / "task-dag.yaml", model.dag_doc)
        write_yaml(change_dir / "verification.yaml", model.verification_doc)
        write_yaml(change_dir / "backflow.yaml", model.backflow_doc)
    append_workflow_event(
        change_dir,
        "backflow_applied",
        {
            "trigger_id": trigger_id,
            "decisions": sorted(impact["decisions"]),
            "contracts": sorted(impact["contracts"]),
            "verifications": sorted(impact["verifications"]),
            "tasks": sorted(impact["direct_tasks"] | impact["propagated_tasks"]),
        },
    )
    print("Backflow impact:")
    for key in ["decisions", "contracts", "verifications", "direct_tasks", "propagated_tasks"]:
        print(f"  {key}: {', '.join(sorted(impact[key])) or '-'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("stage", choices=ALL_STAGES)
    validate_parser.add_argument("change_dir", type=Path)

    prepare_stage_parser = sub.add_parser("prepare-stage")
    prepare_stage_parser.add_argument("stage", choices=sorted(STAGE_CONSTRUCTION_STAGES))
    prepare_stage_parser.add_argument("change_dir", type=Path)

    reopen_stage_parser = sub.add_parser("reopen-stage")
    reopen_stage_parser.add_argument("stage", choices=sorted(STAGE_CONSTRUCTION_STAGES))
    reopen_stage_parser.add_argument("change_dir", type=Path)
    reopen_stage_parser.add_argument("--backflow-id", required=True)
    reopen_stage_parser.add_argument("--reason", required=True)

    migrate_runtime_parser = sub.add_parser("migrate-workflow-runtime")
    migrate_runtime_parser.add_argument("change_dir", type=Path)
    migrate_runtime_parser.add_argument("--profile", choices=sorted(WORKFLOW_PROFILES))
    migrate_runtime_parser.add_argument("--from-stage", choices=sorted(STAGE_CONSTRUCTION_STAGES))

    mark_stage_na_parser = sub.add_parser("mark-stage-na")
    mark_stage_na_parser.add_argument("stage", choices=sorted(STAGE_CONSTRUCTION_STAGES))
    mark_stage_na_parser.add_argument("change_dir", type=Path)
    mark_stage_na_parser.add_argument("--decision-id", required=True)
    mark_stage_na_parser.add_argument("--reason", required=True)
    mark_stage_na_parser.add_argument("--product-semantics", required=True)
    mark_stage_na_parser.add_argument("--verification", required=True)

    late_defect_parser = sub.add_parser("record-late-defect")
    late_defect_parser.add_argument("change_dir", type=Path)
    late_defect_parser.add_argument("--gate", required=True)
    late_defect_parser.add_argument("--failure-signature", required=True)
    late_defect_parser.add_argument("--detected-stage", required=True)
    late_defect_parser.add_argument("--should-have-caught-stage", required=True)
    late_defect_parser.add_argument("--classification", required=True)
    late_defect_parser.add_argument("--affected-rule", required=True)
    late_defect_parser.add_argument("--affected-artifact", required=True)
    late_defect_parser.add_argument("--repair-action", required=True)
    late_defect_parser.add_argument("--promotion-target", required=True)

    promote_defect_parser = sub.add_parser("promote-late-defect")
    promote_defect_parser.add_argument("change_dir", type=Path)
    promote_defect_parser.add_argument("defect_id")
    promote_defect_parser.add_argument("--target-path", action="append", required=True)
    promote_defect_parser.add_argument("--test-id", required=True)

    validate_obligation_parser = sub.add_parser("validate-obligation")
    validate_obligation_parser.add_argument("stage", choices=sorted(STAGE_CONSTRUCTION_STAGES))
    validate_obligation_parser.add_argument("obligation_id")
    validate_obligation_parser.add_argument("change_dir", type=Path)
    validate_obligation_parser.add_argument("--not-applicable", action="store_true")

    validate_stage_construction_parser = sub.add_parser("validate-stage-construction")
    validate_stage_construction_parser.add_argument("stage", choices=sorted(STAGE_CONSTRUCTION_STAGES))
    validate_stage_construction_parser.add_argument("change_dir", type=Path)

    launch_readiness_parser = sub.add_parser("validate-launch-readiness")
    launch_readiness_parser.add_argument("change_dir", type=Path)

    pass_stage_parser = sub.add_parser("pass-stage")
    pass_stage_parser.add_argument("stage", choices=[
        "source-intake",
        "prd",
        "aip",
        "readiness",
        "design",
        "archaeology",
        "migration",
        "frontend-contract",
        "contract",
        "verification",
        "task-planning",
        "mock-acceptance",
        "product-acceptance",
    ])
    pass_stage_parser.add_argument("change_dir", type=Path)

    begin_execution_parser = sub.add_parser("begin-execution")
    begin_execution_parser.add_argument("change_dir", type=Path)

    admit_task_parser = sub.add_parser("admit-task")
    admit_task_parser.add_argument("task_id")
    admit_task_parser.add_argument("change_dir", type=Path)

    validate_task_diff_parser = sub.add_parser("validate-task-diff")
    validate_task_diff_parser.add_argument("task_id")
    validate_task_diff_parser.add_argument("change_dir", type=Path)

    recover_task_parser = sub.add_parser("recover-task-allowlist")
    recover_task_parser.add_argument("task_id")
    recover_task_parser.add_argument("change_dir", type=Path)
    recover_task_parser.add_argument("--add-file", action="append", required=True)
    recover_task_parser.add_argument("--backflow-id", required=True)
    recover_task_parser.add_argument("--reason", required=True)

    reseal_backflow_parser = sub.add_parser("reseal-execution-backflow")
    reseal_backflow_parser.add_argument("change_dir", type=Path)
    reseal_backflow_parser.add_argument("trigger_id")
    reseal_backflow_parser.add_argument("--reason", required=True)

    review_hashes_parser = sub.add_parser("review-hashes")
    review_hashes_parser.add_argument("task_id")
    review_hashes_parser.add_argument("change_dir", type=Path)

    pass_task_parser = sub.add_parser("pass-task")
    pass_task_parser.add_argument("task_id")
    pass_task_parser.add_argument("change_dir", type=Path)

    graph_parser = sub.add_parser("graph")
    graph_parser.add_argument("change_dir", type=Path)

    metrics_parser = sub.add_parser("metrics")
    metrics_parser.add_argument("change_dir", type=Path)

    backflow_parser = sub.add_parser("backflow")
    backflow_parser.add_argument("change_dir", type=Path)
    backflow_parser.add_argument("trigger_id")

    args = parser.parse_args()
    if args.command == "migrate-workflow-runtime":
        return migrate_workflow_runtime(args.change_dir, args.profile, args.from_stage)
    if args.command == "mark-stage-na":
        return mark_stage_na(
            args.change_dir,
            args.stage,
            args.decision_id,
            args.reason,
            args.product_semantics,
            args.verification,
        )
    if args.command == "record-late-defect":
        return record_late_defect(
            args.change_dir,
            args.gate,
            args.failure_signature,
            args.detected_stage,
            args.should_have_caught_stage,
            args.classification,
            args.affected_rule,
            args.affected_artifact,
            args.repair_action,
            args.promotion_target,
        )
    if args.command == "promote-late-defect":
        return promote_late_defect(args.change_dir, args.defect_id, args.target_path, args.test_id)
    if args.command == "prepare-stage":
        return prepare_stage(args.change_dir, args.stage)
    if args.command == "reopen-stage":
        return reopen_stage(args.change_dir, args.stage, args.backflow_id, args.reason)
    if args.command == "validate-obligation":
        return validate_obligation(args.change_dir, args.stage, args.obligation_id, args.not_applicable)
    if args.command == "validate-stage-construction":
        errors = validate_stage_construction(WorkflowModel(args.change_dir), args.stage)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"Stage construction validation passed for stage {args.stage}")
        return 0
    if args.command == "validate":
        errors = validate(args.change_dir, args.stage)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"Structured workflow validation passed for stage {args.stage}")
        return 0
    if args.command == "validate-launch-readiness":
        errors = validate_launch_readiness(args.change_dir)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("Launch readiness validation passed")
        return 0
    if args.command == "pass-stage":
        return issue_stage_receipt(args.change_dir, args.stage)
    if args.command == "begin-execution":
        return begin_execution(args.change_dir)
    if args.command == "admit-task":
        return admit_task(args.change_dir, args.task_id)
    if args.command == "validate-task-diff":
        return command_exit_for_task_diff(args.change_dir, args.task_id)
    if args.command == "recover-task-allowlist":
        return recover_task_allowlist(args.change_dir, args.task_id, args.add_file, args.backflow_id, args.reason)
    if args.command == "reseal-execution-backflow":
        return reseal_execution_backflow(args.change_dir, args.trigger_id, args.reason)
    if args.command == "review-hashes":
        return print_task_review_hashes(args.change_dir, args.task_id)
    if args.command == "pass-task":
        return pass_task(args.change_dir, args.task_id)
    if args.command == "graph":
        return print_graph(args.change_dir)
    if args.command == "metrics":
        return print_workflow_metrics(args.change_dir)
    if args.command == "backflow":
        return apply_backflow(args.change_dir, args.trigger_id)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
