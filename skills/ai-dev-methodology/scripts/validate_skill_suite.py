#!/usr/bin/env python3
"""Validate high-risk consistency rules across the AutoMQ workflow skills."""

from __future__ import annotations

import ast
import argparse
import copy
import contextlib
import hashlib
import importlib.util
import inspect
import io
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills"

STANDARD_WORKFLOW = ROOT / "automq-ai-dev-workflow" / "SKILL.md"
CONTEXTPACK_WORKFLOW = ROOT / "automq-ai-dev-workflow-contextpack" / "SKILL.md"
MOCK_VALIDATOR = ROOT / "mock-acceptance-gate" / "scripts" / "validate_mock_acceptance_cases.py"
PLAYGROUND_VALIDATOR = ROOT / "mock-acceptance-gate" / "scripts" / "validate_playground_simulation_contract.py"
MOCK_ACCEPTANCE_SKILL = ROOT / "mock-acceptance-gate" / "SKILL.md"
MOCK_ACCEPTANCE_VALIDATOR = ROOT / "mock-acceptance-gate" / "scripts" / "validate_mock_acceptance_cases.py"
METHODOLOGY = ROOT / "ai-dev-methodology"
WORKFLOWCTL = METHODOLOGY / "scripts" / "workflowctl.py"
ARTIFACT_VALIDATOR = METHODOLOGY / "scripts" / "validate_artifacts.py"
TEMPLATES = METHODOLOGY / "templates"
ARTIFACT_COMPLETENESS = METHODOLOGY / "references" / "artifact-completeness-spec.md"
RUNTIME_RESOURCE_ROUTING = METHODOLOGY / "references" / "runtime-resource-routing.md"
EXPERIENCE_CONSTRAINTS = METHODOLOGY / "references" / "experience-shaped-implicit-constraints.md"
RUNTIME_MODE_MATERIALIZATION = METHODOLOGY / "references" / "experience" / "runtime-mode-materialization-parity.md"
FRONTEND_SKILL = ROOT / "frontend-contract-design" / "SKILL.md"
CONTRACT_SKILL = ROOT / "cross-module-contract-sdd" / "SKILL.md"
ATOMIC_PLANNING_SKILL = ROOT / "atomic-task-planning" / "SKILL.md"
AIP_TEMPLATE_SKILL = ROOT / "aip-template" / "SKILL.md"
AIP_TEMPLATE_REFERENCE = ROOT / "aip-template" / "references" / "steering.md"
AIP_READINESS_SKILL = ROOT / "aip-readiness-review" / "SKILL.md"
STAGE_CONSTRUCTION_CONTRACT = METHODOLOGY / "templates" / "stage-construction-contracts.yaml"
STANDARD_WORKFLOW_STATE_TEMPLATE = METHODOLOGY / "templates" / "workflow-state.yaml"
CONTEXTPACK_WORKFLOW_STATE_TEMPLATE = METHODOLOGY / "templates" / "workflow-state-contextpack.yaml"
WORKFLOW_RUNTIME_MANIFEST = METHODOLOGY / "templates" / "workflow-runtime-manifest.yaml"
WORKFLOW_DEFECT_TEMPLATE = METHODOLOGY / "templates" / "workflow-defects.yaml"
WORKFLOW_EVENT_TEMPLATE = METHODOLOGY / "templates" / "workflow-events.yaml"
WORKFLOW_STATE_MACHINE_TEMPLATE = METHODOLOGY / "templates" / "workflow-state-machine.yaml"
STAGE_CONSTRUCTION_REFERENCE = METHODOLOGY / "references" / "stage-construction-protocol.md"
CONTEXTPACK_RULE_REFERENCE = ROOT / "automq-ai-dev-workflow-contextpack" / "references" / "workflow-rule-reference.md"
CONTEXTPACK_AGENT_METADATA = ROOT / "automq-ai-dev-workflow-contextpack" / "agents" / "openai.yaml"

REQUIRED_SHARED_SNIPPETS = [
    (
        "mock execution ledger wording",
        "执行后 `mock-acceptance` stage 必须把 blocking rows 的 row-level evidence 写入 "
        "`mock-acceptance-execution.yaml`，再由 `workflowctl.py pass-stage mock-acceptance` 签收；"
        "不得修改 sealed matrix/case 文件去标 passed。",
    ),
    (
        "production-vs-acceptance boundary",
        "`mock acceptance`、`no-cloud`、“不上真实云验收”或 repo-specific acceptance runtime "
        "这类词不得解释为“功能可不真实实现”。",
    ),
]

FORBIDDEN_WORKFLOW_PATTERNS = [
    re.compile(r"blocking rows\s+更新为\s+`?passed`?", re.IGNORECASE),
    re.compile(r"sealed matrix/case.*改成\s+passed", re.IGNORECASE),
]

NEW_REQUIRED_ARTIFACTS = {
    "workflow-workdir.md": [
        METHODOLOGY / "templates" / "workflow-workdir.md",
        METHODOLOGY / "SKILL.md",
        CONTEXTPACK_WORKFLOW,
        WORKFLOWCTL,
        ARTIFACT_VALIDATOR,
    ],
    "existing-object-action-consumer-graph.md": [
        METHODOLOGY / "templates" / "existing-object-action-consumer-graph.md",
        METHODOLOGY / "SKILL.md",
        ARTIFACT_COMPLETENESS,
        ROOT / "code-archaeology-sdd" / "SKILL.md",
        WORKFLOWCTL,
        ARTIFACT_VALIDATOR,
    ],
    "variant-impact-matrix.md": [
        METHODOLOGY / "templates" / "variant-impact-matrix.md",
        METHODOLOGY / "SKILL.md",
        ARTIFACT_COMPLETENESS,
        EXPERIENCE_CONSTRAINTS,
        ROOT / "code-archaeology-sdd" / "SKILL.md",
        ATOMIC_PLANNING_SKILL,
        WORKFLOWCTL,
        ARTIFACT_VALIDATOR,
    ],
    "progress-change-producer-chain-matrix.md": [
        METHODOLOGY / "templates" / "progress-change-producer-chain-matrix.md",
        METHODOLOGY / "SKILL.md",
        ARTIFACT_COMPLETENESS,
        EXPERIENCE_CONSTRAINTS,
        CONTRACT_SKILL,
        ROOT / "verification-matrix" / "SKILL.md",
        ATOMIC_PLANNING_SKILL,
        WORKFLOWCTL,
        ARTIFACT_VALIDATOR,
    ],
    "external-side-effect-contract-matrix.md": [
        METHODOLOGY / "templates" / "external-side-effect-contract-matrix.md",
        METHODOLOGY / "SKILL.md",
        ARTIFACT_COMPLETENESS,
        EXPERIENCE_CONSTRAINTS,
        CONTRACT_SKILL,
        ROOT / "verification-matrix" / "SKILL.md",
        ATOMIC_PLANNING_SKILL,
        WORKFLOWCTL,
        ARTIFACT_VALIDATOR,
    ],
    "runtime-test-topology-matrix.md": [
        METHODOLOGY / "templates" / "runtime-test-topology-matrix.md",
        METHODOLOGY / "SKILL.md",
        ARTIFACT_COMPLETENESS,
        EXPERIENCE_CONSTRAINTS,
        ROOT / "code-archaeology-sdd" / "SKILL.md",
        ROOT / "verification-matrix" / "SKILL.md",
        ATOMIC_PLANNING_SKILL,
        WORKFLOWCTL,
        ARTIFACT_VALIDATOR,
    ],
    "runtime-materialization-parity.md": [
        METHODOLOGY / "templates" / "runtime-materialization-parity.md",
        METHODOLOGY / "SKILL.md",
        ARTIFACT_COMPLETENESS,
        EXPERIENCE_CONSTRAINTS,
        ATOMIC_PLANNING_SKILL,
        WORKFLOWCTL,
        ARTIFACT_VALIDATOR,
    ],
    "mechanism-design-model.md": [
        METHODOLOGY / "templates" / "mechanism-design-model.md",
        METHODOLOGY / "SKILL.md",
        ARTIFACT_COMPLETENESS,
        AIP_READINESS_SKILL,
        ROOT / "new-feature-design" / "SKILL.md",
        CONTRACT_SKILL,
        ROOT / "verification-matrix" / "SKILL.md",
        ATOMIC_PLANNING_SKILL,
        WORKFLOWCTL,
        ARTIFACT_VALIDATOR,
    ],
    "task-planning-repair-ledger.yaml": [
        METHODOLOGY / "templates" / "task-planning-repair-ledger.yaml",
        METHODOLOGY / "SKILL.md",
        CONTEXTPACK_WORKFLOW,
        WORKFLOWCTL,
        ARTIFACT_VALIDATOR,
    ],
    "frontend-api-payload-contract-matrix.md": [FRONTEND_SKILL, WORKFLOWCTL, ARTIFACT_VALIDATOR],
    "contract-semantic-type-matrix.md": [CONTRACT_SKILL, WORKFLOWCTL, ARTIFACT_VALIDATOR],
    "api-wire-shape-matrix.md": [CONTRACT_SKILL, WORKFLOWCTL, ARTIFACT_VALIDATOR],
    "atomic-task-decomposition.md": [ATOMIC_PLANNING_SKILL, WORKFLOWCTL, ARTIFACT_VALIDATOR],
    "launch-readiness-review.md": [
        METHODOLOGY / "templates" / "launch-readiness-review.md",
        METHODOLOGY / "SKILL.md",
        STANDARD_WORKFLOW,
        CONTEXTPACK_WORKFLOW,
        WORKFLOWCTL,
    ],
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def quiet_call(function, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return function(*args, **kwargs)


def read_with_direct_skill_references(path: Path) -> str:
    body = read(path)
    if path == CONTEXTPACK_WORKFLOW and CONTEXTPACK_RULE_REFERENCE.exists():
        body += "\n" + read(CONTEXTPACK_RULE_REFERENCE)
    if path == METHODOLOGY / "SKILL.md" and RUNTIME_RESOURCE_ROUTING.exists():
        body += "\n" + read(RUNTIME_RESOURCE_ROUTING)
    return body


def set_root(skills_root: Path) -> None:
    global ROOT, STANDARD_WORKFLOW, CONTEXTPACK_WORKFLOW, MOCK_VALIDATOR, PLAYGROUND_VALIDATOR
    global METHODOLOGY, WORKFLOWCTL, ARTIFACT_VALIDATOR, TEMPLATES, ARTIFACT_COMPLETENESS, RUNTIME_RESOURCE_ROUTING
    global EXPERIENCE_CONSTRAINTS, RUNTIME_MODE_MATERIALIZATION, FRONTEND_SKILL, CONTRACT_SKILL
    global ATOMIC_PLANNING_SKILL, AIP_TEMPLATE_SKILL, AIP_TEMPLATE_REFERENCE, AIP_READINESS_SKILL, NEW_REQUIRED_ARTIFACTS
    global STAGE_CONSTRUCTION_CONTRACT, STANDARD_WORKFLOW_STATE_TEMPLATE, CONTEXTPACK_WORKFLOW_STATE_TEMPLATE, STAGE_CONSTRUCTION_REFERENCE
    global WORKFLOW_RUNTIME_MANIFEST, WORKFLOW_DEFECT_TEMPLATE, WORKFLOW_EVENT_TEMPLATE, WORKFLOW_STATE_MACHINE_TEMPLATE
    global CONTEXTPACK_RULE_REFERENCE, CONTEXTPACK_AGENT_METADATA

    ROOT = skills_root
    STANDARD_WORKFLOW = ROOT / "automq-ai-dev-workflow" / "SKILL.md"
    CONTEXTPACK_WORKFLOW = ROOT / "automq-ai-dev-workflow-contextpack" / "SKILL.md"
    MOCK_VALIDATOR = ROOT / "mock-acceptance-gate" / "scripts" / "validate_mock_acceptance_cases.py"
    PLAYGROUND_VALIDATOR = ROOT / "mock-acceptance-gate" / "scripts" / "validate_playground_simulation_contract.py"
    METHODOLOGY = ROOT / "ai-dev-methodology"
    WORKFLOWCTL = METHODOLOGY / "scripts" / "workflowctl.py"
    ARTIFACT_VALIDATOR = METHODOLOGY / "scripts" / "validate_artifacts.py"
    TEMPLATES = METHODOLOGY / "templates"
    ARTIFACT_COMPLETENESS = METHODOLOGY / "references" / "artifact-completeness-spec.md"
    RUNTIME_RESOURCE_ROUTING = METHODOLOGY / "references" / "runtime-resource-routing.md"
    EXPERIENCE_CONSTRAINTS = METHODOLOGY / "references" / "experience-shaped-implicit-constraints.md"
    RUNTIME_MODE_MATERIALIZATION = METHODOLOGY / "references" / "experience" / "runtime-mode-materialization-parity.md"
    FRONTEND_SKILL = ROOT / "frontend-contract-design" / "SKILL.md"
    CONTRACT_SKILL = ROOT / "cross-module-contract-sdd" / "SKILL.md"
    ATOMIC_PLANNING_SKILL = ROOT / "atomic-task-planning" / "SKILL.md"
    AIP_TEMPLATE_SKILL = ROOT / "aip-template" / "SKILL.md"
    AIP_TEMPLATE_REFERENCE = ROOT / "aip-template" / "references" / "steering.md"
    AIP_READINESS_SKILL = ROOT / "aip-readiness-review" / "SKILL.md"
    STAGE_CONSTRUCTION_CONTRACT = METHODOLOGY / "templates" / "stage-construction-contracts.yaml"
    STANDARD_WORKFLOW_STATE_TEMPLATE = METHODOLOGY / "templates" / "workflow-state.yaml"
    CONTEXTPACK_WORKFLOW_STATE_TEMPLATE = METHODOLOGY / "templates" / "workflow-state-contextpack.yaml"
    WORKFLOW_RUNTIME_MANIFEST = METHODOLOGY / "templates" / "workflow-runtime-manifest.yaml"
    WORKFLOW_DEFECT_TEMPLATE = METHODOLOGY / "templates" / "workflow-defects.yaml"
    WORKFLOW_EVENT_TEMPLATE = METHODOLOGY / "templates" / "workflow-events.yaml"
    WORKFLOW_STATE_MACHINE_TEMPLATE = METHODOLOGY / "templates" / "workflow-state-machine.yaml"
    STAGE_CONSTRUCTION_REFERENCE = METHODOLOGY / "references" / "stage-construction-protocol.md"
    CONTEXTPACK_RULE_REFERENCE = ROOT / "automq-ai-dev-workflow-contextpack" / "references" / "workflow-rule-reference.md"
    CONTEXTPACK_AGENT_METADATA = ROOT / "automq-ai-dev-workflow-contextpack" / "agents" / "openai.yaml"
    NEW_REQUIRED_ARTIFACTS = {
        "workflow-workdir.md": [
            METHODOLOGY / "templates" / "workflow-workdir.md",
            METHODOLOGY / "SKILL.md",
            CONTEXTPACK_WORKFLOW,
            WORKFLOWCTL,
            ARTIFACT_VALIDATOR,
        ],
        "existing-object-action-consumer-graph.md": [
            METHODOLOGY / "templates" / "existing-object-action-consumer-graph.md",
            METHODOLOGY / "SKILL.md",
            ARTIFACT_COMPLETENESS,
            ROOT / "code-archaeology-sdd" / "SKILL.md",
            WORKFLOWCTL,
            ARTIFACT_VALIDATOR,
        ],
        "variant-impact-matrix.md": [
            METHODOLOGY / "templates" / "variant-impact-matrix.md",
            METHODOLOGY / "SKILL.md",
            ARTIFACT_COMPLETENESS,
            EXPERIENCE_CONSTRAINTS,
            ROOT / "code-archaeology-sdd" / "SKILL.md",
            ATOMIC_PLANNING_SKILL,
            WORKFLOWCTL,
            ARTIFACT_VALIDATOR,
        ],
        "progress-change-producer-chain-matrix.md": [
            METHODOLOGY / "templates" / "progress-change-producer-chain-matrix.md",
            METHODOLOGY / "SKILL.md",
            ARTIFACT_COMPLETENESS,
            EXPERIENCE_CONSTRAINTS,
            CONTRACT_SKILL,
            ROOT / "verification-matrix" / "SKILL.md",
            ATOMIC_PLANNING_SKILL,
            WORKFLOWCTL,
            ARTIFACT_VALIDATOR,
        ],
        "external-side-effect-contract-matrix.md": [
            METHODOLOGY / "templates" / "external-side-effect-contract-matrix.md",
            METHODOLOGY / "SKILL.md",
            ARTIFACT_COMPLETENESS,
            EXPERIENCE_CONSTRAINTS,
            CONTRACT_SKILL,
            ROOT / "verification-matrix" / "SKILL.md",
            ATOMIC_PLANNING_SKILL,
            WORKFLOWCTL,
            ARTIFACT_VALIDATOR,
        ],
        "runtime-test-topology-matrix.md": [
            METHODOLOGY / "templates" / "runtime-test-topology-matrix.md",
            METHODOLOGY / "SKILL.md",
            ARTIFACT_COMPLETENESS,
            EXPERIENCE_CONSTRAINTS,
            ROOT / "code-archaeology-sdd" / "SKILL.md",
            ROOT / "verification-matrix" / "SKILL.md",
            ATOMIC_PLANNING_SKILL,
            WORKFLOWCTL,
            ARTIFACT_VALIDATOR,
        ],
        "runtime-materialization-parity.md": [
            METHODOLOGY / "templates" / "runtime-materialization-parity.md",
            METHODOLOGY / "SKILL.md",
            ARTIFACT_COMPLETENESS,
            EXPERIENCE_CONSTRAINTS,
            ATOMIC_PLANNING_SKILL,
            WORKFLOWCTL,
            ARTIFACT_VALIDATOR,
        ],
        "mechanism-design-model.md": [
            METHODOLOGY / "templates" / "mechanism-design-model.md",
            METHODOLOGY / "SKILL.md",
            ARTIFACT_COMPLETENESS,
            AIP_READINESS_SKILL,
            ROOT / "new-feature-design" / "SKILL.md",
            CONTRACT_SKILL,
            ROOT / "verification-matrix" / "SKILL.md",
            ATOMIC_PLANNING_SKILL,
            WORKFLOWCTL,
            ARTIFACT_VALIDATOR,
        ],
        "task-planning-repair-ledger.yaml": [
            METHODOLOGY / "templates" / "task-planning-repair-ledger.yaml",
            METHODOLOGY / "SKILL.md",
            CONTEXTPACK_WORKFLOW,
            WORKFLOWCTL,
            ARTIFACT_VALIDATOR,
        ],
        "frontend-api-payload-contract-matrix.md": [FRONTEND_SKILL, WORKFLOWCTL, ARTIFACT_VALIDATOR],
        "contract-semantic-type-matrix.md": [CONTRACT_SKILL, WORKFLOWCTL, ARTIFACT_VALIDATOR],
        "api-wire-shape-matrix.md": [CONTRACT_SKILL, WORKFLOWCTL, ARTIFACT_VALIDATOR],
        "atomic-task-decomposition.md": [ATOMIC_PLANNING_SKILL, WORKFLOWCTL, ARTIFACT_VALIDATOR],
        "launch-readiness-review.md": [
            METHODOLOGY / "templates" / "launch-readiness-review.md",
            METHODOLOGY / "SKILL.md",
            STANDARD_WORKFLOW,
            CONTEXTPACK_WORKFLOW,
            WORKFLOWCTL,
        ],
    }


def python_constant_set(path: Path, name: str) -> set[str]:
    tree = ast.parse(read(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        if isinstance(value, set):
            return {str(item) for item in value}
    return set()


def python_constant_list(path: Path, name: str) -> list[str]:
    tree = ast.parse(read(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        if isinstance(value, list):
            return [str(item) for item in value]
    return []


def template_surface_types() -> set[str]:
    body = read(TEMPLATES / "decision-surface-discovery.md")
    match = re.search(r"`Surface type`\s*可选：(.+?)。", body)
    if not match:
        return set()
    return {item for item in re.findall(r"`([^`]+)`", match.group(1)) if item}


def validate_workflow_drift() -> list[str]:
    errors: list[str] = []
    standard = read(STANDARD_WORKFLOW)
    contextpack = read_with_direct_skill_references(CONTEXTPACK_WORKFLOW)
    for label, snippet in REQUIRED_SHARED_SNIPPETS:
        if snippet not in standard:
            errors.append(f"{STANDARD_WORKFLOW}: missing required shared snippet: {label}")
        if snippet not in contextpack:
            errors.append(f"{CONTEXTPACK_WORKFLOW}: missing required shared snippet: {label}")
    for path, body in [(STANDARD_WORKFLOW, standard), (CONTEXTPACK_WORKFLOW, contextpack)]:
        for pattern in FORBIDDEN_WORKFLOW_PATTERNS:
            match = pattern.search(body)
            if match:
                errors.append(f"{path}: forbidden stale workflow wording: {match.group(0)}")
    return errors


def validate_contract_obligation_validator_drift() -> list[str]:
    errors: list[str] = []
    for constant in [
        "CONTRACT_OBLIGATION_OPERATION_TERMS",
        "CONTRACT_OBLIGATION_RESOURCE_TERMS",
        "CONTRACT_OBLIGATION_CONSUMER_MODULE_TERMS",
    ]:
        artifact_value = python_constant_list(ARTIFACT_VALIDATOR, constant)
        workflow_value = python_constant_list(WORKFLOWCTL, constant)
        if artifact_value != workflow_value:
            errors.append(f"{WORKFLOWCTL} and {ARTIFACT_VALIDATOR}: {constant} drift")

    required_functions = [
        "field_has_multiple_explicit_terms",
        "specialized_contract_row_ids",
        "validate_specialized_rows_in_contract_obligations",
        "executable_obligation_row_granularity_errors",
        "contract_provider_module_is_multi_owner",
        "executable_obligation_column_drift_errors",
        "markdown_table_column_count_errors",
    ]
    for path in [WORKFLOWCTL, ARTIFACT_VALIDATOR]:
        body = read(path)
        for fn in required_functions:
            if f"def {fn}" not in body:
                errors.append(f"{path}: missing contract obligation validator helper {fn}")
        for snippet in [
            "owner_module_format_errors",
            "contract_row_owner_module",
            "Owner module must be a concrete MOD-* module",
        ]:
            if snippet not in body:
                errors.append(f"{path}: missing owner-module hardgate helper/snippet: {snippet}")
        if "Contract Executable Obligation Matrix must consume" not in body:
            errors.append(f"{path}: missing specialized matrix row -> contract obligation consumption check")
    return errors


def validate_planning_statuses() -> list[str]:
    errors: list[str] = []
    for path in [MOCK_VALIDATOR, PLAYGROUND_VALIDATOR]:
        body = read(path)
        match = re.search(r"PLANNING_STATUSES\s*=\s*\{([^}]*)\}", body)
        if not match:
            errors.append(f"{path}: missing PLANNING_STATUSES")
            continue
        statuses = {item.strip().strip("\"'") for item in match.group(1).split(",") if item.strip()}
        if "passed" in statuses:
            errors.append(f"{path}: planning statuses must not include passed; execution evidence belongs in mutable ledgers")
        required = {"planned", "pending", "not_run", "not_started", "not_applicable"}
        missing = sorted(required - statuses)
        if missing:
            errors.append(f"{path}: planning statuses missing {', '.join(missing)}")
    return errors


def validate_new_artifact_wiring() -> list[str]:
    errors: list[str] = []
    workflowctl_only_artifacts = {"launch-readiness-review.md"}
    for artifact, required_paths in NEW_REQUIRED_ARTIFACTS.items():
        template = TEMPLATES / artifact
        if not template.exists():
            errors.append(f"{template}: missing required template for workflow artifact {artifact}")
        elif not read(template).strip():
            errors.append(f"{template}: template is empty")
        for path in required_paths:
            if path == template:
                continue
            body = read_with_direct_skill_references(path)
            if artifact not in body:
                errors.append(f"{path}: missing required artifact wiring/reference: {artifact}")
    for path in [WORKFLOWCTL, ARTIFACT_VALIDATOR]:
        body = read_with_direct_skill_references(path)
        for artifact in NEW_REQUIRED_ARTIFACTS:
            if path == ARTIFACT_VALIDATOR and artifact in workflowctl_only_artifacts:
                continue
            if f'"{artifact}"' not in body:
                errors.append(f"{path}: {artifact} must be present in Python artifact lists")
    workflowctl_body = read(WORKFLOWCTL)
    if "validate-launch-readiness" not in workflowctl_body or "validate_launch_readiness" not in workflowctl_body:
        errors.append(f"{WORKFLOWCTL}: launch-readiness-review.md must be enforced by validate-launch-readiness")
    return errors


def markdown_table_cell_count_errors(path: Path) -> list[str]:
    errors: list[str] = []
    header_cells: list[str] | None = None
    header_line = 0
    for line_no, raw_line in enumerate(read(path).splitlines(), start=1):
        line = raw_line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            header_cells = None
            header_line = 0
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        is_separator = all(re.fullmatch(r":?-+:?", cell.replace(" ", "")) for cell in cells)
        if is_separator:
            if header_cells is not None and len(cells) != len(header_cells):
                errors.append(
                    f"{path}: markdown table separator on line {line_no} has {len(cells)} cells, "
                    f"but header on line {header_line} has {len(header_cells)}"
                )
            continue
        if header_cells is None:
            header_cells = cells
            header_line = line_no
            continue
        if len(cells) != len(header_cells):
            errors.append(
                f"{path}: markdown table row on line {line_no} has {len(cells)} cells, "
                f"but header on line {header_line} has {len(header_cells)}"
            )
    return errors


def validate_template_table_integrity() -> list[str]:
    errors: list[str] = []
    for path in [
        TEMPLATES / "cross-module-contract.md",
        TEMPLATES / "atomic-task-decomposition.md",
        TEMPLATES / "task-dag.md",
    ]:
        errors.extend(markdown_table_cell_count_errors(path))
    return errors


def validate_semantic_carrier_projection_wiring() -> list[str]:
    errors: list[str] = []
    required = [
        (METHODOLOGY / "SKILL.md", "Semantic carrier projection"),
        (ATOMIC_PLANNING_SKILL, "Semantic Carrier Projection Matrix"),
        (TEMPLATES / "semantic-objects.yaml", "semantic_carrier_projections"),
        (TEMPLATES / "atomic-issue-packets.yaml", "projection_id"),
        (TEMPLATES / "task-dag.yaml", "SCP-001"),
        (WORKFLOWCTL, "validate_semantic_carrier_projections"),
        (WORKFLOWCTL, "semantic_carrier_projections"),
        (METHODOLOGY / "scripts" / "atomic_issue_compile.py", "matches_any(carrier_text, rule[\"source_patterns\"])"),
    ]
    for path, snippet in required:
        body = read_with_direct_skill_references(path)
        if snippet not in body:
            errors.append(f"{path}: missing semantic carrier projection wiring snippet: {snippet}")
    return errors


def validate_playground_connect_scope_wiring() -> list[str]:
    errors: list[str] = []
    required = [
        (STANDARD_WORKFLOW, "automqbox 非 Connect 功能"),
        (STANDARD_WORKFLOW, "只有在开发 Connect 相关功能时才启用 `playground`"),
        (CONTEXTPACK_WORKFLOW, "automqbox 非 Connect 功能"),
        (CONTEXTPACK_WORKFLOW, "只有在开发 Connect 相关功能时才启用 `playground`"),
        (MOCK_ACCEPTANCE_SKILL, "automqbox/CMP non-Connect"),
        (MOCK_ACCEPTANCE_SKILL, "do not read [references/cmp-playground.md]"),
        (MOCK_ACCEPTANCE_VALIDATOR, "CONNECT_DOMAIN_SIGNAL_RE"),
        (MOCK_ACCEPTANCE_VALIDATOR, "is_connect_playground"),
        (MOCK_ACCEPTANCE_VALIDATOR, "automqbox/CMP Connect-only"),
    ]
    for path, snippet in required:
        body = read_with_direct_skill_references(path)
        if snippet not in body:
            errors.append(f"{path}: missing automqbox/CMP Connect-only playground scope snippet: {snippet}")
    forbidden = [
        (MOCK_ACCEPTANCE_VALIDATOR, r"\bautomqbox\|cmp-playground"),
        (MOCK_ACCEPTANCE_VALIDATOR, r"\bNoCloud\|PlaygroundAcceptanceProperties"),
    ]
    for path, pattern in forbidden:
        if re.search(pattern, read(path)):
            errors.append(f"{path}: playground signal regex must not trigger on generic automqbox or NoCloud alone")
    import importlib.util

    spec = importlib.util.spec_from_file_location("mock_acceptance_validator_scope", MOCK_ACCEPTANCE_VALIDATOR)
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)

    generic_template = read(ROOT / "mock-acceptance-gate" / "templates" / "mock-acceptance.md")
    generic_scope = validator.playground_scope_status(
        generic_template
        + "\nautomqbox/CMP cmp-app generic billing/settings feature with generic no-cloud mock acceptance"
    )
    if generic_scope["is_connect_playground"]:
        errors.append(f"{ROOT / 'mock-acceptance-gate' / 'templates' / 'mock-acceptance.md'}: generic mock acceptance template must not trigger automqbox/CMP Connect playground scope")

    plugin_scope = validator.playground_scope_status(
        "automqbox/CMP packaged playground generic extension settings page for billing and access management"
    )
    if plugin_scope["is_connect_playground"]:
        errors.append(f"{MOCK_ACCEPTANCE_VALIDATOR}: generic plugin wording must not trigger Connect playground scope")

    connect_scope_text = (
        "automqbox/CMP cmp-app packaged playground /connect/clusters "
        "ConnectCluster ConnectorController cmp-playground"
    )
    connect_scope = validator.playground_scope_status(connect_scope_text)
    if not connect_scope["is_connect_playground"]:
        errors.append(f"{MOCK_ACCEPTANCE_VALIDATOR}: explicit automqbox/CMP Connect playground scope was not detected")

    minimal_report = "\n".join(
        f"## {heading}\ncase_id MAC-001 decision N/A"
        for heading in validator.REQUIRED_REPORT_SECTIONS
    ) + "\n## Case Execution Matrix\nMAC-001\n## Backend Mock Matrix\nMBM-001\n## Frontend Action Matrix\nMFM-001\n"
    report_errors = validator.validate_report(
        Path("/tmp/automq-skill-suite-scope"),
        minimal_report,
        [],
        [],
        [],
        mode="planning",
        combined_scope_text=connect_scope_text,
    )
    if not any("CMP Playground Architecture Matrix" in error for error in report_errors):
        errors.append(f"{MOCK_ACCEPTANCE_VALIDATOR}: Connect playground scope must require CMP Playground report sections")
    return errors


def validate_reviewer_wait_timeout_wiring() -> list[str]:
    errors: list[str] = []
    required = [
        (CONTEXTPACK_WORKFLOW, "使用 30–60 秒 `wait_agent` 轮询"),
        (CONTEXTPACK_WORKFLOW, "累计等待窗口至少 30 分钟"),
        (CONTEXTPACK_WORKFLOW, "窗口内未返回时不得中断 reviewer、缩小 review scope"),
        (CONTEXTPACK_WORKFLOW, "frozen review packet 和 reviewer 要审的 canonical artifacts 必须保持冻结"),
        (CONTEXTPACK_WORKFLOW, "以相同 frozen packet 和同等 review scope 重启 reviewer"),
        (CONTEXTPACK_WORKFLOW, "超时不是降低 gate 标准、缩小审查范围"),
        (ROOT / "atomic-execution-sdd" / "SKILL.md", "单次等待超时必须设置为至少 30 分钟"),
    ]
    for path, snippet in required:
        body = read_with_direct_skill_references(path)
        if snippet not in body:
            errors.append(f"{path}: missing readonly reviewer wait-timeout hard gate snippet: {snippet}")
    return errors


def validate_contract_executable_obligation_wiring() -> list[str]:
    errors: list[str] = []
    required = [
        (TEMPLATES / "contracts.yaml", "executable_obligations"),
        (TEMPLATES / "contracts.yaml", "edge:"),
        (TEMPLATES / "contracts.yaml", "edge_type"),
        (TEMPLATES / "contracts.yaml", "provider_module must be owner-single"),
        (TEMPLATES / "cross-module-contract.md", "C-xxx-OBL-001"),
        (TEMPLATES / "cross-module-contract.md", "Edge type"),
        (TEMPLATES / "cross-module-contract.md", "Column integrity rule"),
        (TEMPLATES / "task-dag.yaml", "provides_obligations"),
        (CONTRACT_SKILL, "contracts.yaml.contracts[C-xxx].executable_obligations"),
        (CONTRACT_SKILL, "provider_module` 必须是 owner-single"),
        (CONTRACT_SKILL, "semantic_contract_edge` + `consumer assumption"),
        (CONTRACT_SKILL, "列漂移"),
        (CONTRACT_SKILL, "Edge type"),
        (ATOMIC_PLANNING_SKILL, "executable_obligations"),
        (ATOMIC_PLANNING_SKILL, "semantic_contract_edge"),
        (ATOMIC_PLANNING_SKILL, "semantic_contract_edge + consumer assumption"),
        (ATOMIC_PLANNING_SKILL, "Contract Ingress Invariant Check"),
        (ATOMIC_PLANNING_SKILL, "provider_module` 必须 owner-single"),
        (ATOMIC_PLANNING_SKILL, "provides_obligations` 只能列 owner-single `semantic_contract_edge`"),
        (WORKFLOWCTL, "validate_contract_executable_obligations"),
        (WORKFLOWCTL, "contract_provider_module_is_multi_owner"),
        (WORKFLOWCTL, "executable_obligation_column_drift_errors"),
        (WORKFLOWCTL, "non-provider obligation"),
        (WORKFLOWCTL, "semantic_contract_edge obligation must have exactly one task-dag provides_obligations owner"),
        (WORKFLOWCTL, "active_contract_obligation_rows(model)"),
        (WORKFLOWCTL, "\"Edge type\""),
        (ARTIFACT_VALIDATOR, "\"Edge type\""),
        (ARTIFACT_VALIDATOR, "contract_provider_module_is_multi_owner"),
        (ARTIFACT_VALIDATOR, "executable_obligation_column_drift_errors"),
        (ARTIFACT_VALIDATOR, "non-provider obligation"),
        (ARTIFACT_VALIDATOR, "semantic_contract_edge obligation must have exactly"),
        (ARTIFACT_VALIDATOR, "PROVIDER_OWNED_EDGE_TYPE_RE"),
    ]
    for path, snippet in required:
        body = read(path)
        if snippet not in body:
            errors.append(f"{path}: missing contract executable obligation wiring snippet: {snippet}")
    return errors


def validate_surface_type_contract_drift() -> list[str]:
    errors: list[str] = []
    template_types = template_surface_types()
    if not template_types:
        return [f"{TEMPLATES / 'decision-surface-discovery.md'}: cannot parse Surface type list"]

    artifact_types = python_constant_set(ARTIFACT_VALIDATOR, "DECISION_SURFACE_ALLOWED_TYPES")
    compiler_types = python_constant_set(METHODOLOGY / "scripts" / "atomic_issue_compile.py", "DECISION_SURFACE_ALLOWED_TYPES")
    for path, accepted in [(ARTIFACT_VALIDATOR, artifact_types), (METHODOLOGY / "scripts" / "atomic_issue_compile.py", compiler_types)]:
        missing = sorted(template_types - accepted)
        if missing:
            errors.append(f"{path}: DECISION_SURFACE_ALLOWED_TYPES missing template surface types: {', '.join(missing)}")
    for path, accepted in [(ARTIFACT_VALIDATOR, artifact_types), (METHODOLOGY / "scripts" / "atomic_issue_compile.py", compiler_types)]:
        extra = sorted(accepted - template_types - {"mock-playground"})
        if extra:
            errors.append(f"{path}: DECISION_SURFACE_ALLOWED_TYPES has undocumented surface types: {', '.join(extra)}")

    packet_template = read(TEMPLATES / "atomic-issue-packets.yaml")
    missing_from_packet_comment = sorted(t for t in template_types if t not in packet_template)
    if missing_from_packet_comment:
        errors.append(
            f"{TEMPLATES / 'atomic-issue-packets.yaml'}: decision surface packet comment missing types: "
            + ", ".join(missing_from_packet_comment)
        )
    return errors


def validate_runtime_mode_materialization_reference() -> list[str]:
    errors: list[str] = []
    if not RUNTIME_MODE_MATERIALIZATION.exists():
        return [f"{RUNTIME_MODE_MATERIALIZATION}: missing runtime mode materialization parity reference"]

    reference = read(RUNTIME_MODE_MATERIALIZATION)
    index = read(EXPERIENCE_CONSTRAINTS)
    required_reference_phrases = [
        "Additive coexisting mode",
        "Replacement / retirement",
        "Internal substrate refactor",
        "Capability reduction / scoped mode",
        "runtime-materialization-parity.md",
        "resource exists / ASG exists / pod exists / process starts",
        "assuming the image/AMI/container already contains required plugins, config, or secrets without a locked source",
    ]
    for phrase in required_reference_phrases:
        if phrase not in reference:
            errors.append(f"{RUNTIME_MODE_MATERIALIZATION}: missing required phrase: {phrase}")

    if "EXP-010 Runtime Mode Materialization Parity" not in index:
        errors.append(f"{EXPERIENCE_CONSTRAINTS}: missing EXP-010 index entry")
    if "references/experience/runtime-mode-materialization-parity.md" not in index:
        errors.append(f"{EXPERIENCE_CONSTRAINTS}: missing runtime parity reference path")

    workflow_phrase = "runtime mode materialization parity"
    carrier_phrase = "runtime artifact/config/plugin/secret/bootstrap/entrypoint/readback"
    for path in [STANDARD_WORKFLOW, CONTEXTPACK_WORKFLOW]:
        body = read_with_direct_skill_references(path)
        if workflow_phrase not in body:
            errors.append(f"{path}: missing runtime mode materialization parity decision-surface wording")
        if "references/experience/runtime-mode-materialization-parity.md" not in body:
            errors.append(f"{path}: missing on-demand runtime parity reference path")
        if carrier_phrase not in body:
            errors.append(f"{path}: missing runtime parity dense semantic carrier wording")

    planning = read(ATOMIC_PLANNING_SKILL)
    if workflow_phrase not in planning:
        errors.append(f"{ATOMIC_PLANNING_SKILL}: missing runtime parity semantic carrier wording")
    if "runtime-materialization-parity.md" not in planning:
        errors.append(f"{ATOMIC_PLANNING_SKILL}: missing runtime-materialization-parity.md consumption wording")
    if "decision-surface-discovery.md" not in planning:
        errors.append(f"{ATOMIC_PLANNING_SKILL}: missing decision-surface-discovery consumption wording")
    return errors


def validate_aip_design_closure_reference() -> list[str]:
    errors: list[str] = []
    required_phrases = [
        "Mechanism-Level Design Closure Matrix",
        "AIP Narrative Materialization Gate",
    ]
    for path in [
        AIP_TEMPLATE_SKILL,
        AIP_TEMPLATE_REFERENCE,
        AIP_READINESS_SKILL,
        ARTIFACT_COMPLETENESS,
        WORKFLOWCTL,
        ARTIFACT_VALIDATOR,
    ]:
        body = read(path)
        for phrase in required_phrases:
            if phrase not in body:
                errors.append(f"{path}: missing AIP design closure phrase: {phrase}")

    for path in [STANDARD_WORKFLOW, CONTEXTPACK_WORKFLOW, AIP_TEMPLATE_SKILL, AIP_READINESS_SKILL]:
        body = read_with_direct_skill_references(path)
        if "writing-style" not in body or not re.search(r"(?:仅用于|只在|仅在).{0,40}`?aip\.md`?.{0,20}正文|only.*AIP narrative", body, re.IGNORECASE):
            errors.append(f"{path}: writing-style must be explicitly limited to aip.md narrative text")

    for path in [WORKFLOWCTL, ARTIFACT_VALIDATOR]:
        body = read(path)
        for helper in [
            "validate_mechanism_design_closure",
            "validate_aip_narrative_materialization",
            "validate_mechanism_model_row_identity",
        ]:
            if f"def {helper}" not in body:
                errors.append(f"{path}: missing AIP design closure validator helper {helper}")
    # SC-AIP-GLOBAL-COMPAT-001 regression: AIP construction must invoke the
    # deterministic artifact checks before the readonly review packet is frozen.
    contract_body = read(STAGE_CONSTRUCTION_CONTRACT)
    workflowctl_body = read(WORKFLOWCTL)
    if "SC-AIP-GLOBAL-COMPAT-001" not in contract_body:
        errors.append(f"{STAGE_CONSTRUCTION_CONTRACT}: missing SC-AIP-GLOBAL-COMPAT-001")
    if "validate_aip_construction_compatibility" not in workflowctl_body:
        errors.append(f"{WORKFLOWCTL}: missing AIP construction compatibility hook")
    return errors


def validate_aip_design_closure_runtime_smoke() -> list[str]:
    errors: list[str] = []
    import importlib.util

    workflow_spec = importlib.util.spec_from_file_location("workflowctl_aip_smoke", WORKFLOWCTL)
    workflowctl = importlib.util.module_from_spec(workflow_spec)
    workflow_spec.loader.exec_module(workflowctl)
    artifact_spec = importlib.util.spec_from_file_location("validate_artifacts_aip_smoke", ARTIFACT_VALIDATOR)
    artifact_validator = importlib.util.module_from_spec(artifact_spec)
    artifact_spec.loader.exec_module(artifact_validator)

    aip_self_report = """# AIP（AutoMQ Improvement Proposal）模板
## AIP 元信息
x
## 评审记录
x
## AIP 正文结构
### 1. 背景
背景 Problem Goals Non-goals 目标 非目标 Architecture 接口 数据 状态 任务 部署 云资源 Observability metrics logs 兼容 rollback Verification
### 2. 问题定义
x
### 3. 调研论证
x
### 4. 解决方案
#### Mechanism-Level Design Closure Matrix
| Design question | Selected mechanism | Rejected alternatives | Current code evidence | External fact / constraint | Interface impact | State/runtime impact | Failure behavior | Verification | Downstream C/VER |
|---|---|---|---|---|---|---|---|---|---|
| create autoscaling policy during create | call production provider policy API with owner service | reject no policy at create because runtime autoscaling would not work | services/Foo.java | FACT-001 | API returns policy id | state stores policy relation | permission failure returns typed error | VER-001 | C-001 / VER-001 |
### 5. 原型设计
x
### 6. 接口设计
x
### 7. 依赖选型
x
### 8. 方案详情
#### AIP Narrative Materialization Gate
| Source design object | Must appear in AIP section | Narrative requirement | Status |
|---|---|---|---|
| ADEC-001 / FACT-001 | 4. 解决方案 | 正文必须说明 provider API 和 policy 创建机制 | materialized |
### 9. 兼容性问题
x
### 10. 被拒绝的其他方案
x
### 11. 落地计划
x
## AIP 验收
x
### 发布验收
x
### 上线验收
x
"""
    design_sources = """## 决策摘要
| ID | Type | Decision key | Question | Final decision | Decided by | Status |
|---|---|---|---|---|---|---|
| ADEC-001 | architecture | runtime.mechanism | Which runtime mechanism? | Use provider API path | ai-engineering | locked |

## External Capability Fact Matrix
| Fact ID | Source ID | External system | Capability/API/resource | Official fact | Preconditions/limits | Failure behavior | Confidence | Downstream impact |
|---|---|---|---|---|---|---|---|---|
| FACT-001 | SRC-001 | AWS | ASG | Official fact says use scaling policy API for CPU policy. | permission required | AccessDenied fails | high | ADEC-001 |

## Current Architecture Understanding
| Area | Current architecture / behavior | Evidence path / command | Engineering implication | Gap / DEC |
|---|---|---|---|---|
| runtime | current runtime path | services/Foo.java | use existing owner | ADEC-001 |
"""
    wf_errors = workflowctl.validate_aip_narrative_materialization(aip_self_report, design_sources, "aip.md")
    if not any("marked materialized but is absent" in error for error in wf_errors):
        errors.append(f"{WORKFLOWCTL}: AIP narrative gate self-report smoke was not rejected")
    artifact_errors = artifact_validator.validate_aip_narrative_materialization(Path("/tmp/aip-smoke"), aip_self_report, design_sources, "aip.md")
    if not any("marked materialized but is absent" in error for error in artifact_errors):
        errors.append(f"{ARTIFACT_VALIDATOR}: AIP narrative gate self-report smoke was not rejected")

    unrelated_evidence_table = """## Readiness Local Audit Report
| Audit scope | Evidence | Verdict |
|---|---|---|
| stage routing | decision-reviews/readiness-decisions.md | pass |
"""
    canonical_architecture_table = """## Current Architecture Understanding
| Area | Current architecture / behavior | Evidence path / command | Engineering implication | Gap / DEC |
|---|---|---|---|---|
| runtime | current runtime path | services/Foo.java | preserve current owner | ADEC-001 |
"""
    for validator_name, unrelated_values, canonical_values in [
        (
            str(WORKFLOWCTL),
            workflowctl.current_architecture_evidence_values(unrelated_evidence_table),
            workflowctl.current_architecture_evidence_values(canonical_architecture_table),
        ),
        (
            str(ARTIFACT_VALIDATOR),
            artifact_validator.current_architecture_evidence_values(unrelated_evidence_table),
            artifact_validator.current_architecture_evidence_values(canonical_architecture_table),
        ),
    ]:
        if unrelated_values:
            errors.append(f"{validator_name}: unrelated Evidence table was misclassified as Current Architecture evidence")
        if canonical_values != ["services/Foo.java"]:
            errors.append(f"{validator_name}: canonical Current Architecture evidence was not extracted: {canonical_values}")

    internal_api_aip = aip_self_report.replace("FACT-001", "locked N/A").replace("call production provider policy API with owner service", "call internal service API with owner service")
    internal_api_aip = internal_api_aip.replace("provider API 和 policy 创建机制", "内部 API 和 policy 创建机制")
    mech_errors = workflowctl.validate_mechanism_design_closure(internal_api_aip, "aip.md")
    if any("external mechanism row must reference" in error for error in mech_errors):
        errors.append(f"{WORKFLOWCTL}: internal API locked N/A smoke incorrectly required external MECH/FACT/CONSTRAINT")
    artifact_mech_errors = artifact_validator.validate_mechanism_design_closure(Path("/tmp/aip-smoke"), internal_api_aip, "aip.md")
    if any("external mechanism row must reference" in error for error in artifact_mech_errors):
        errors.append(f"{ARTIFACT_VALIDATOR}: internal API locked N/A smoke incorrectly required external MECH/FACT/CONSTRAINT")

    duplicate_model_rows = """## External API Parameter Map
| Parameter row | External system/API/resource | Parameter / option |
|---|---|---|
| EXTAPI-011 | Kubernetes VersionApi | GET /version/ reachability |
| EXTAPI-011 | RPC core | error envelope category/code |
"""
    unique_model_rows = duplicate_model_rows.replace(
        "| EXTAPI-011 | RPC core |",
        "| EXTAPI-012 | RPC core |",
    )
    audit_reference_rows = """## Mechanism Row Inventory
| Mechanism row | Selected production mechanism | Canonical owner |
|---|---|---|
| MECH-001 | route through the canonical provider | rpc-core |

## Mechanism Design Local Audit
| Mechanism row | Auditor finding | Required backflow |
|---|---|---|
| MECH-001 | none | none |
"""
    for validator_name, duplicate_errors, unique_errors, audit_errors in [
        (
            str(WORKFLOWCTL),
            workflowctl.validate_mechanism_model_row_identity(duplicate_model_rows, "mechanism-design"),
            workflowctl.validate_mechanism_model_row_identity(unique_model_rows, "mechanism-design"),
            workflowctl.validate_mechanism_model_row_identity(audit_reference_rows, "mechanism-design"),
        ),
        (
            str(ARTIFACT_VALIDATOR),
            artifact_validator.validate_mechanism_model_row_identity(duplicate_model_rows, "mechanism-design-model.md"),
            artifact_validator.validate_mechanism_model_row_identity(unique_model_rows, "mechanism-design-model.md"),
            artifact_validator.validate_mechanism_model_row_identity(audit_reference_rows, "mechanism-design-model.md"),
        ),
    ]:
        if not any("duplicate rows: EXTAPI-011" in error for error in duplicate_errors):
            errors.append(f"{validator_name}: duplicate semantic mechanism row ID was accepted")
        if unique_errors:
            errors.append(f"{validator_name}: unique semantic mechanism row IDs were rejected: {unique_errors}")
        if audit_errors:
            errors.append(f"{validator_name}: mechanism audit references were misclassified as canonical row definitions: {audit_errors}")
    canonical_row_smokes = [
        ("Mechanism row", "MECH-001", "Selected production mechanism", "Canonical owner"),
        ("Sequence row", "OPSEQ-001", "Ordered production steps", "External calls/resources"),
        ("Parameter row", "EXTAPI-001", "External system/API/resource", "Parameter / option"),
        ("Event row", "EVT-001", "Event / step", "State owner"),
        ("Runtime row", "RMM-001", "Mode / runtime", "New mode materialization design"),
        ("Resource row", "RLM-001", "Selection/provenance", "Create timing"),
        ("Failure row", "FCM-001", "Failure point", "Consistency invariant"),
        ("Interface row", "MIM-001", "Producer module", "Consumer module"),
    ]
    for label, row_id, signature_one, signature_two in canonical_row_smokes:
        duplicate_rows = (
            f"| {label} | {signature_one} | {signature_two} |\n"
            "|---|---|---|\n"
            f"| {row_id} | first definition | owner one |\n"
            f"| {row_id} | second definition | owner two |\n"
        )
        for validator_name, duplicate_errors in [
            (
                str(WORKFLOWCTL),
                workflowctl.validate_mechanism_model_row_identity(duplicate_rows, "mechanism-design"),
            ),
            (
                str(ARTIFACT_VALIDATOR),
                artifact_validator.validate_mechanism_model_row_identity(duplicate_rows, "mechanism-design-model.md"),
            ),
        ]:
            if not any(f"duplicate rows: {row_id}" in error for error in duplicate_errors):
                errors.append(f"{validator_name}: duplicate canonical {row_id} identity was accepted")
    with tempfile.TemporaryDirectory() as tmp:
        change_dir = Path(tmp) / "specs" / "changes" / "aip-global-compat-smoke"
        change_dir.mkdir(parents=True)
        (change_dir / "proposal.md").write_text("K8s external API architecture\n", encoding="utf-8")
        (change_dir / "spec.md").write_text("REQ-001 requires Kubernetes runtime.\n", encoding="utf-8")
        (change_dir / "plan.md").write_text("AIP 工程方案需要外部能力研究。\n", encoding="utf-8")
        (change_dir / "aip.md").write_text("# AIP\n", encoding="utf-8")
        (change_dir / "external-capability-research.md").write_text(
            "## External Capability Fact Matrix\n"
            "| Fact ID | Source ID | Evidence anchor | Source-observed fact |\n"
            "|---|---|---|---|\n"
            "| FACT-001 | EXT-SRC-001 | EVID-001 | thin |\n",
            encoding="utf-8",
        )
        workflowctl.write_yaml(
            change_dir / "workflow-state.yaml",
            {
                "schema_version": 2,
                "workflow": {"skill": "automq-ai-dev-workflow-contextpack", "profile": "full"},
                "stage_status": {"aip": "in_progress"},
            },
        )
        compatibility_errors = workflowctl.validate_aip_construction_compatibility(change_dir)
        if not any("External Capability Fact Matrix must include" in error for error in compatibility_errors):
            errors.append(
                f"{WORKFLOWCTL}: SC-AIP-GLOBAL-COMPAT-001 did not reject an incompatible external fact matrix: {compatibility_errors}"
            )
    return errors


def write_minimal_model_files(change_dir: Path) -> None:
    for rel in [
        "workflow-state.yaml",
        "semantic-objects.yaml",
        "contracts.yaml",
        "verification.yaml",
        "task-dag.yaml",
        "backflow.yaml",
        "atomic-issue-packets.yaml",
    ]:
        (change_dir / rel).write_text("{}\n", encoding="utf-8")


GOOD_PRODUCER_MATRIX = """# Progress / Change Producer Chain Matrix

## Progress / Change Producer Chain Matrix

| Chain ID | Object/action | Variant | Mutation API / entrypoint | Canonical change writer | State owner / table | Task/event producer | Correlation key | Write timing | Last-change readback | Change detail readback | Frontend/mock consumer | Terminal / polling rule | Failure behavior | Verification | Owner issue |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PCP-001 | ConnectCluster/create | asg | `POST /connect/clusters` | InstanceChange manager writer | change/task tables | CreateConnectTaskInstanceFactory task step writer | `clusterId -> changeId` | before runtime side effect | `/last-change` readback for same clusterId returns changeId | `/changes/{changeId}` change detail readback | progress page | terminal stops polling | failed step with reason | same created id create -> `/last-change` -> `/changes/{changeId}` API readback proof | T001 |

## Producer Chain Equivalence Matrix

| Equivalence row | Existing variant chain | New variant chain | Equivalent consumer assumption | Allowed difference | Forbidden shortcut | Verification |
|---|---|---|---|---|---|---|
| PCE-001 | k8s create change/task steps | asg create change/task steps | `/last-change` returns current create change | step names | fixture-only progress | same created id readback |
"""


WEAK_PRODUCER_MATRIX = GOOD_PRODUCER_MATRIX.replace(
    "InstanceChange manager writer",
    "mock event writer",
).replace(
    "CreateConnectTaskInstanceFactory task step writer",
    "mock task event writer",
)


def validate_new_artifact_runtime_smoke() -> list[str]:
    errors: list[str] = []
    import importlib.util

    validator_spec = importlib.util.spec_from_file_location("validate_artifacts_smoke", ARTIFACT_VALIDATOR)
    artifact_validator = importlib.util.module_from_spec(validator_spec)
    validator_spec.loader.exec_module(artifact_validator)

    workflow_spec = importlib.util.spec_from_file_location("workflowctl_smoke", WORKFLOWCTL)
    workflowctl = importlib.util.module_from_spec(workflow_spec)
    workflow_spec.loader.exec_module(workflowctl)

    with tempfile.TemporaryDirectory(prefix="automq-skill-suite-") as tmp:
        root = Path(tmp)
        for name, matrix in [("good", GOOD_PRODUCER_MATRIX), ("weak", WEAK_PRODUCER_MATRIX), ("ordinary", "")]:
            change_dir = root / name
            change_dir.mkdir()
            write_minimal_model_files(change_dir)
            (change_dir / "proposal.md").write_text(
                "This change updates request validation and response mapping for a remote service adapter.\n",
                encoding="utf-8",
            )
            if matrix:
                (change_dir / "progress-change-producer-chain-matrix.md").write_text(matrix, encoding="utf-8")

        good_errors = artifact_validator.validate_progress_change_producer_chain(root / "good", "contract", "", "", "", "")
        if good_errors:
            errors.append(f"{ARTIFACT_VALIDATOR}: good producer-chain smoke should pass, got {good_errors}")
        weak_errors = artifact_validator.validate_progress_change_producer_chain(root / "weak", "contract", "", "", "", "")
        if not any("weak or missing production Canonical change writer" in error for error in weak_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: weak producer-chain smoke did not reject mock writer")
        ordinary_errors = artifact_validator.validate_variant_impact_artifacts(
            root / "ordinary",
            "archaeology",
            (root / "ordinary" / "proposal.md").read_text(encoding="utf-8"),
            "",
            "",
            "",
        )
        if ordinary_errors:
            errors.append(f"{ARTIFACT_VALIDATOR}: ordinary provider/API text should not trigger variant artifacts: {ordinary_errors}")
        side_effect_matrix = """# External Side Effect Contract Matrix

## External Side Effect Contract Matrix

| Effect ID | Source | Operation/action | External system | Production side-effect owner | Required production call/resource mutation | Physical dependency allowed? | No-cloud/playground substitute boundary | Minimum acceptable proof | Failure/partial failure semantics | State/readback consumer | Contract ID | Verification ID | Owner issue |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ESE-001 | C-001 | update capacity | AWS ASG | runtime manager/provider operator | provider API setCapacity resource mutation | no real cloud in playground | mock only replaces physical cloud endpoint, not provider call | integration provider call capture plus event readback | typed FAILED event and API readback | detail/progress API readback | C-001 | VER-001 | T001 |
"""
        topology_matrix = """# Runtime Test Topology Matrix

## Runtime Test Topology Matrix

| Topology ID | Behavior/contract | Production path | Proof module/package | Proof file/path | Fixture/support files | Required build/install/freshness step | Why this proof owner is necessary | Staleness risk if skipped | Verification command | Expected result | Owner issue |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RTT-001 | C-001 runtime side effect | service manager -> runtime provider | runtime tests | services/test/RuntimeProofTest.java | N/A | ./mvnw -pl service install | service-only proof cannot observe provider boundary | stale artifact | ./mvnw -pl runtime -Dtest=RuntimeProofTest test | BUILD SUCCESS | T001 |

## Proof Owner File Matrix

| Verification ID | Owner issue | Proof file/path | Must be in task-dag files? | Must be in packet files_to_change? | Fixture/support file | Reason | Status |
|---|---|---|---:|---:|---|---|---|
| VER-001 | T001 | services/test/RuntimeProofTest.java | no | no | N/A | runtime proof owner | planned |
"""
        side_dir = root / "side-effect"
        side_dir.mkdir()
        write_minimal_model_files(side_dir)
        (side_dir / "external-side-effect-contract-matrix.md").write_text(side_effect_matrix, encoding="utf-8")
        (side_dir / "runtime-test-topology-matrix.md").write_text(topology_matrix, encoding="utf-8")
        side_errors = artifact_validator.validate_external_side_effect_contract(side_dir, "contract", "", "", "", "")
        topo_errors = artifact_validator.validate_runtime_test_topology(side_dir, "verification", "", "", "", "")
        if side_errors or topo_errors:
            errors.append(f"{ARTIFACT_VALIDATOR}: side-effect/topology smoke should pass, got {side_errors + topo_errors}")

        rmp_dir = root / "runtime-materialization"
        rmp_dir.mkdir()
        write_minimal_model_files(rmp_dir)
        (rmp_dir / "proposal.md").write_text("Add a new runtime mode that changes bootstrap, plugins, secrets, and product config materialization.\n", encoding="utf-8")
        (rmp_dir / "spec.md").write_text("Runtime mode materialization parity is required.\n", encoding="utf-8")
        (rmp_dir / "plan.md").write_text("runtime mode materialization parity must be locked.\n", encoding="utf-8")
        (rmp_dir / "tasks.md").write_text("T001 runtime materialization owner task.\n", encoding="utf-8")
        (rmp_dir / "decision-surface-discovery.md").write_text(
            """# Decision Surface Discovery

## Decision Surface Inventory

| Surface ID | Trigger source | Surface type | Object/capability/action | Why this is a decision surface | Current evidence | Required decision | Decision owner stage | Blocks next stage |
|---|---|---|---|---|---|---|---|---:|
| DS-001 | REQ-001 | runtime-mode-materialization-parity | new runtime mode | bootstrap/plugins/config/secrets change | source | classify runtime mode change | design | yes |
""",
            encoding="utf-8",
        )
        missing_rmp_errors = artifact_validator.validate_runtime_materialization_parity(
            rmp_dir, "design", (rmp_dir / "proposal.md").read_text(encoding="utf-8"), (rmp_dir / "spec.md").read_text(encoding="utf-8"), (rmp_dir / "plan.md").read_text(encoding="utf-8"), (rmp_dir / "tasks.md").read_text(encoding="utf-8")
        )
        if not any("runtime mode materialization parity signal exists" in error for error in missing_rmp_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: missing runtime materialization parity artifact was not rejected")
        rmp_matrix = """# Runtime Materialization Parity

## Runtime Mode Change Classification

| Decision ID | Source | Existing mode(s) | New / changed mode | Classification | Evidence | Locked decision | Owner stage |
|---|---|---|---|---|---|---|---|
| DESIGN-DEC-001 | REQ-001 | k8s | asg | Additive coexisting mode | existing runtime and new runtime source | locked C-001/VER-001/T001 | design |

## Product Capability Parity Matrix

| Capability ID | Product capability | Existing mode baseline | New / changed mode obligation | Supported? | If not supported, product/API/UI expression | Contract ID | Verification ID | Owner issue |
|---|---|---|---|---|---|---|---|---|
| RMP-CAP-001 | runtime worker create | existing mode renders runtime config/plugins/secrets/bootstrap/readback | new mode materializes equivalent runtime config/plugins/secrets/bootstrap/readback | yes | N/A | C-001 | VER-001 | T001 |

## Runtime Materialization Mapping

| Mapping ID | Mode | Capability input | Existing mode materialization evidence | New / changed mode materialization design | Production owner | Required files/modules | Failure semantics | Verification | Owner issue |
|---|---|---|---|---|---|---|---|---|---|
| RMP-MAP-001 | mode-a | Runtime artifact | existing runtime artifact source | runtime artifact is selected from locked artifact source | runtime manager | runtime/RuntimeManager.java | typed failed state and readback | integration test proves runtime artifact selection | T001 |
| RMP-MAP-002 | mode-a | Product config | existing product config renderer | product config is rendered to runtime-readable path | runtime manager | runtime/RuntimeManager.java | typed failed state and readback | integration test proves Product config readback | T001 |
| RMP-MAP-003 | mode-a | Plugins/extensions | existing plugin mount path | installs plugins/extensions from locked artifact source | runtime manager | runtime/RuntimeManager.java | typed failed state and readback | integration test proves Plugins/extensions readback | T001 |
| RMP-MAP-004 | mode-a | Secrets/security config | existing secret delivery path | writes Secrets/security config to runtime-readable path | runtime manager | runtime/RuntimeManager.java | typed failed state and readback | integration test proves Secrets/security config readback | T001 |
| RMP-MAP-005 | mode-a | Dependency endpoints | existing dependency endpoint injection | injects dependency endpoints through startup config | runtime manager | runtime/RuntimeManager.java | typed failed state and readback | integration test proves Dependency endpoints readback | T001 |
| RMP-MAP-006 | mode-a | Bootstrap/entrypoint | existing bootstrap path | bootstrap/entrypoint materializes config before ready | runtime manager | runtime/RuntimeManager.java | typed failed state and readback | integration test proves Bootstrap/entrypoint readback | T001 |
| RMP-MAP-007 | mode-a | Lifecycle operations | existing lifecycle operation owner | lifecycle operations update runtime materialization state | runtime manager | runtime/RuntimeManager.java | typed failed state and readback | integration test proves Lifecycle operations readback | T001 |
| RMP-MAP-008 | mode-a | Readback/observability | existing status/readback path | exposes readback/observability for materialized inputs | runtime manager | runtime/RuntimeManager.java | typed failed state and readback | integration test proves Readback/observability | T001 |

## Runtime Parity Negative Assertions

| Assertion ID | Forbidden shortcut | Why invalid | Detection proof | Backflow target |
|---|---|---|---|---|
| RMP-NEG-001 | Resource created but product config/plugins/secrets are not materialized | Resource existence does not prove runtime capability | Runtime config/plugin/secret readback | design/contract/task-planning |
| RMP-NEG-002 | image/AMI/container assumed to contain plugins/config/secrets without source | hidden image assumptions are invalid | locked artifact source and runtime readback | AIP/design/contract |
"""
        (rmp_dir / "runtime-materialization-parity.md").write_text(rmp_matrix, encoding="utf-8")
        (rmp_dir / "atomic-planning-context-pack.md").write_text("runtime-materialization-parity.md consumed for runtime materialization parity.\n", encoding="utf-8")
        (rmp_dir / "atomic-task-decomposition.md").write_text("Runtime Materialization Task Map consumes runtime-materialization-parity.md for RMP-MAP rows.\n", encoding="utf-8")
        (rmp_dir / "atomic-issue-packets.yaml").write_text(
            "schema_version: 1\npackets:\n  T001:\n    semantic_carriers:\n      - carrier: runtime materialization Runtime artifact Product config Plugins/extensions Secrets/security config Bootstrap/entrypoint Readback/observability\n",
            encoding="utf-8",
        )
        (rmp_dir / "task-dag.yaml").write_text("schema_version: 1\ntasks:\n  T001:\n    title: runtime materialization RMP owner\n    files: []\nedges: []\n", encoding="utf-8")
        good_rmp_errors = artifact_validator.validate_runtime_materialization_parity(
            rmp_dir, "pre-execution", (rmp_dir / "proposal.md").read_text(encoding="utf-8"), (rmp_dir / "spec.md").read_text(encoding="utf-8"), (rmp_dir / "plan.md").read_text(encoding="utf-8"), (rmp_dir / "tasks.md").read_text(encoding="utf-8")
        )
        if good_rmp_errors:
            errors.append(f"{ARTIFACT_VALIDATOR}: good runtime materialization smoke should pass, got {good_rmp_errors}")

        good_model = workflowctl.WorkflowModel(root / "good")
        workflow_good_errors = workflowctl.validate_progress_change_producer_chain(good_model, "contract")
        if workflow_good_errors:
            errors.append(f"{WORKFLOWCTL}: good producer-chain smoke should pass, got {workflow_good_errors}")
        weak_model = workflowctl.WorkflowModel(root / "weak")
        workflow_weak_errors = workflowctl.validate_progress_change_producer_chain(weak_model, "contract")
        if not any("weak or missing production Canonical change writer" in error for error in workflow_weak_errors):
            errors.append(f"{WORKFLOWCTL}: weak producer-chain smoke did not reject mock writer")
        side_model = workflowctl.WorkflowModel(side_dir)
        workflow_side_errors = workflowctl.validate_external_side_effect_contract(side_model, "contract")
        workflow_topo_errors = workflowctl.validate_runtime_test_topology(side_model, "verification")
        if workflow_side_errors or workflow_topo_errors:
            errors.append(f"{WORKFLOWCTL}: side-effect/topology smoke should pass, got {workflow_side_errors + workflow_topo_errors}")
        workflow_rmp_errors = workflowctl.validate_runtime_materialization_parity(workflowctl.WorkflowModel(rmp_dir), "pre-execution")
        if workflow_rmp_errors:
            errors.append(f"{WORKFLOWCTL}: good runtime materialization smoke should pass, got {workflow_rmp_errors}")

        bad_owner_dir = root / "bad-owner-module"
        bad_owner_dir.mkdir()
        write_minimal_model_files(bad_owner_dir)
        (bad_owner_dir / "plan.md").write_text(
            """# Plan

## Contract Executable Obligation Matrix

| Contract | Sub-obligation ID | Edge | Edge type | Sub-obligation type | Semantic type | Operation / surface | Canonical owner | Fields/resource/state | Provider guarantee | Consumer assumption | Failure / timing detail | State/resource owner | Owner module | Verification proof | Split hint |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C-001 | C-001-OBL-001 | MOD-RUNTIME -> MOD-API | semantic_contract_edge | provider guarantee | External side effect | create provider resource | resource writer | resourceId/provenance | provider creates resource | API consumes readback | typed failure | runtime resource state | VER-001 | VER-001 proof | provider task |
""",
            encoding="utf-8",
        )
        (bad_owner_dir / "contracts.yaml").write_text(
            """schema_version: 1
contracts:
  C-001:
    status: locked
    provider_module: MOD-RUNTIME
    executable_obligations:
      - obligation_id: C-001-OBL-001
        edge: MOD-RUNTIME -> MOD-API
        edge_type: semantic_contract_edge
        row_kind: provider guarantee
        semantic_type: External side effect
        operation_surface: create provider resource
        canonical_owner: resource writer
        owner_module: VER-001
        fields_resource_state: resourceId/provenance
        provider_guarantee: provider creates resource
        consumer_assumption: API consumes readback
        failure_timing_detail: typed failure
        state_resource_owner: runtime resource state
        verification: VER-001 proof
        split_hint: provider task
""",
            encoding="utf-8",
        )
        bad_owner_artifact_errors = artifact_validator.validate_contract_matrix_artifacts(
            bad_owner_dir,
            "task-planning",
            (bad_owner_dir / "plan.md").read_text(encoding="utf-8"),
            "",
        )
        if not any("Owner module must be a concrete MOD-*" in error for error in bad_owner_artifact_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: bad Owner module=VER-* smoke was not rejected")
        bad_owner_workflow_errors = workflowctl.validate_contract_executable_obligations(workflowctl.WorkflowModel(bad_owner_dir), "task-planning")
        if not any("Owner module must be a concrete MOD-*" in error for error in bad_owner_workflow_errors):
            errors.append(f"{WORKFLOWCTL}: bad Owner module=VER-* smoke was not rejected")

        mixed_owner_dir = root / "mixed-owner-contract"
        mixed_owner_dir.mkdir()
        write_minimal_model_files(mixed_owner_dir)
        (mixed_owner_dir / "contracts.yaml").write_text(
            """schema_version: 1
contracts:
  C-001:
    status: locked
    provider_module: MOD-RUNTIME
    provider_issue: T002
    executable_obligations:
      - obligation_id: C-001-OBL-001
        edge: MOD-FRONTEND -> MOD-API
        edge_type: semantic_contract_edge
        row_kind: provider guarantee
        semantic_type: Wire/API shape
        operation_surface: validate request body
        canonical_owner: API validation owner
        owner_module: MOD-API
        fields_resource_state: allowed key worker_spec and forbidden key capacity
        provider_guarantee: API rejects capacity aliases before persistence.
        consumer_assumption: frontend can submit exact worker_spec payload.
        failure_timing_detail: invalid key fails before mutation.
        state_resource_owner: API request schema
        verification: VER-001
        split_hint: provider task T001
      - obligation_id: C-001-OBL-002
        edge: MOD-API -> MOD-RUNTIME
        edge_type: semantic_contract_edge
        row_kind: provider guarantee
        semantic_type: Runtime materialization
        operation_surface: apply runtime refresh
        canonical_owner: runtime materialization owner
        owner_module: MOD-RUNTIME
        fields_resource_state: runtime refresh id and status
        provider_guarantee: runtime starts refresh and persists status.
        consumer_assumption: API can read refresh status.
        failure_timing_detail: refresh failure writes typed reason.
        state_resource_owner: runtime refresh state
        verification: VER-002
        split_hint: provider task T002
""",
            encoding="utf-8",
        )
        (mixed_owner_dir / "task-dag.yaml").write_text(
            """schema_version: 1
tasks:
  T001:
    title: API request shape
    primary_module: MOD-API
    status: pending
    sources: [REQ-001]
    verification: [VER-001]
    provides: []
    provides_obligations: [C-001-OBL-001]
    issue: atomic-issues/T001.md
  T002:
    title: Runtime refresh
    primary_module: MOD-RUNTIME
    status: pending
    sources: [REQ-001]
    verification: [VER-002]
    provides: []
    provides_obligations: [C-001-OBL-002]
    issue: atomic-issues/T002.md
edges: []
""",
            encoding="utf-8",
        )
        (mixed_owner_dir / "semantic-objects.yaml").write_text(
            """schema_version: 1
requirements:
  REQ-001:
    semantic_carriers:
      - User updates worker_spec through an API shape owner and a runtime refresh owner.
""",
            encoding="utf-8",
        )
        (mixed_owner_dir / "verification.yaml").write_text(
            """schema_version: 1
verifications:
  VER-001:
    command: mvn test -Dtest=ApiShapeTest
  VER-002:
    command: mvn test -Dtest=RuntimeRefreshTest
""",
            encoding="utf-8",
        )
        (mixed_owner_dir / "atomic-issues").mkdir()
        (mixed_owner_dir / "atomic-issues" / "T001.md").write_text("# T001\n", encoding="utf-8")
        (mixed_owner_dir / "atomic-issues" / "T002.md").write_text("# T002\n", encoding="utf-8")
        mixed_model = workflowctl.WorkflowModel(mixed_owner_dir)
        mixed_contract_errors = workflowctl.validate_contract_executable_obligations(mixed_model, "task-planning")
        if not any("provider_module cannot summarize multiple executable owner modules" in error for error in mixed_contract_errors):
            errors.append(f"{WORKFLOWCTL}: mixed-owner coarse contract provider_module was not rejected")
        mixed_task_errors = workflowctl.validate_tasks(mixed_model)
        if mixed_task_errors:
            errors.append(f"{WORKFLOWCTL}: mixed-owner provides_obligations-only DAG should pass task owner checks, got {mixed_task_errors}")
        artifact_mixed_errors = artifact_validator.validate_task_dag(mixed_owner_dir, "", "")
        if any("provides_obligations lists" in error or "provider_module is" in error for error in artifact_mixed_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: mixed-owner obligation owners were incorrectly constrained by coarse provider_module: {artifact_mixed_errors}")
        (mixed_owner_dir / "contracts.yaml").write_text(
            (mixed_owner_dir / "contracts.yaml").read_text(encoding="utf-8").replace("    provider_module: MOD-RUNTIME\n    provider_issue: T002\n", ""),
            encoding="utf-8",
        )
        mixed_composition_model = workflowctl.WorkflowModel(mixed_owner_dir)
        mixed_composition_contract_errors = workflowctl.validate_contracts(mixed_composition_model, "task-planning")
        if any("C-001: missing provider_module" in error or "C-001: provider_issue is required" in error for error in mixed_composition_contract_errors):
            errors.append(f"{WORKFLOWCTL}: mixed-owner composition contract should not require coarse provider identity: {mixed_composition_contract_errors}")
        artifact_mixed_composition_errors = artifact_validator.validate_contract_matrix_artifacts(
            mixed_owner_dir,
            "task-planning",
            "",
            "",
        )
        if any("C-001 missing provider_module" in error or "C-001 provider_issue is required" in error for error in artifact_mixed_composition_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: mixed-owner composition contract should not require coarse provider identity: {artifact_mixed_composition_errors}")
        (mixed_owner_dir / "contracts.yaml").write_text(
            (mixed_owner_dir / "contracts.yaml").read_text(encoding="utf-8").replace(
                "        row_kind: provider guarantee\n",
                "        row_kind: consumer assumption\n",
                1,
            ),
            encoding="utf-8",
        )
        bad_non_provider_owner_errors = workflowctl.validate_contract_executable_obligations(workflowctl.WorkflowModel(mixed_owner_dir), "task-planning")
        if not any("non-provider obligation C-001-OBL-001 uses semantic_contract_edge" in error for error in bad_non_provider_owner_errors):
            errors.append(f"{WORKFLOWCTL}: semantic_contract_edge with consumer row_kind was not rejected")
        artifact_bad_non_provider_errors = artifact_validator.validate_contract_matrix_artifacts(
            mixed_owner_dir,
            "task-planning",
            "",
            "",
        )
        if not any("non-provider obligation C-001-OBL-001 uses semantic_contract_edge" in error for error in artifact_bad_non_provider_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: semantic_contract_edge with consumer row_kind was not rejected")
        (mixed_owner_dir / "contracts.yaml").write_text(
            (mixed_owner_dir / "contracts.yaml").read_text(encoding="utf-8").replace(
                "        row_kind: consumer assumption\n",
                "        row_kind: provider guarantee\n",
                1,
            ),
            encoding="utf-8",
        )
        (mixed_owner_dir / "contracts.yaml").write_text(
            (mixed_owner_dir / "contracts.yaml").read_text(encoding="utf-8").replace(
                "        row_kind: provider guarantee\n",
                "",
                1,
            ),
            encoding="utf-8",
        )
        missing_row_kind_errors = workflowctl.validate_contract_executable_obligations(workflowctl.WorkflowModel(mixed_owner_dir), "task-planning")
        if not any("non-provider obligation C-001-OBL-001 uses semantic_contract_edge with row_kind <missing>" in error for error in missing_row_kind_errors):
            errors.append(f"{WORKFLOWCTL}: semantic_contract_edge with missing row_kind was not rejected")
        artifact_missing_row_kind_errors = artifact_validator.validate_contract_matrix_artifacts(
            mixed_owner_dir,
            "task-planning",
            "",
            "",
        )
        if not any("non-provider obligation C-001-OBL-001 uses semantic_contract_edge with row_kind <missing>" in error for error in artifact_missing_row_kind_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: semantic_contract_edge with missing row_kind was not rejected")
        (mixed_owner_dir / "contracts.yaml").write_text(
            (mixed_owner_dir / "contracts.yaml").read_text(encoding="utf-8").replace(
                "        edge_type: semantic_contract_edge\n        semantic_type: Wire/API shape\n",
                "        edge_type: semantic_contract_edge\n        row_kind: provider guarantee\n        semantic_type: Wire/API shape\n",
                1,
            ),
            encoding="utf-8",
        )
        (mixed_owner_dir / "task-dag.yaml").write_text(
            (mixed_owner_dir / "task-dag.yaml").read_text(encoding="utf-8").replace("provides: []", "provides: [C-001]", 1),
            encoding="utf-8",
        )
        coarse_task_errors = workflowctl.validate_tasks(workflowctl.WorkflowModel(mixed_owner_dir))
        if not any("multiple owner modules" in error for error in coarse_task_errors):
            errors.append(f"{WORKFLOWCTL}: mixed-owner coarse provides C-001 was not rejected")
        artifact_coarse_errors = artifact_validator.validate_task_dag(mixed_owner_dir, "", "")
        if not any("multiple owner modules" in error for error in artifact_coarse_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: mixed-owner coarse provides C-001 was not rejected")

        single_owner_missing_provider_dir = root / "single-owner-missing-provider"
        single_owner_missing_provider_dir.mkdir()
        write_minimal_model_files(single_owner_missing_provider_dir)
        (single_owner_missing_provider_dir / "contracts.yaml").write_text(
            """schema_version: 1
contracts:
  C-001:
    status: locked
    trigger: create
    normal_path: provider creates resource
    failure_path: typed failure
    consistency: readback consistent
    timing: synchronous
    consumer_modules: [MOD-API]
    executable_obligations:
      - obligation_id: C-001-OBL-001
        edge: MOD-RUNTIME -> MOD-API
        edge_type: semantic_contract_edge
        row_kind: provider guarantee
        semantic_type: External side effect
        operation_surface: create provider resource
        canonical_owner: runtime writer
        owner_module: MOD-RUNTIME
        fields_resource_state: resourceId/provenance
        provider_guarantee: provider creates resource
        consumer_assumption: API reads resource state
        failure_timing_detail: typed failure
        state_resource_owner: runtime resource state
        verification: VER-001
        split_hint: provider task
""",
            encoding="utf-8",
        )
        single_missing_errors = workflowctl.validate_contracts(
            workflowctl.WorkflowModel(single_owner_missing_provider_dir),
            "task-planning",
        )
        if not any("C-001: missing provider_module" in error for error in single_missing_errors):
            errors.append(f"{WORKFLOWCTL}: owner-single contract missing provider_module was not rejected")

        projection_dir = root / "semantic-projection-id"
        projection_dir.mkdir()
        write_minimal_model_files(projection_dir)
        (projection_dir / "semantic-objects.yaml").write_text(
            """schema_version: 1
requirements:
  REQ-001:
    semantic_carriers:
      - User create flow includes API shape and runtime side effect.
    consumed_by: [T001]
semantic_carrier_projections:
  REQ-001:
    - projection_id: SCP-001-T001
      source: REQ-001
      owner_module: MOD-API
      owner_task: T001
      operation_surface: validate request body
      semantic_type: Wire/API shape
      must_preserve:
        - API validates exact worker_spec body and rejects capacity aliases.
      excluded_owner_semantics:
        - Runtime refresh side effect belongs to MOD-RUNTIME.
""",
            encoding="utf-8",
        )
        (projection_dir / "task-dag.yaml").write_text(
            """schema_version: 1
tasks:
  T001:
    title: API request shape
    primary_module: MOD-API
    status: pending
    sources: [REQ-001]
    semantic_carriers: [SCP-001-T001]
    verification: [VER-001]
    issue: atomic-issues/T001.md
edges: []
""",
            encoding="utf-8",
        )
        projection_errors = workflowctl.validate_semantic_carrier_projections(workflowctl.WorkflowModel(projection_dir), "task-planning")
        if projection_errors:
            errors.append(f"{WORKFLOWCTL}: SCP-001-T001 projection id should pass, got {projection_errors}")

        compiler_spec = importlib.util.spec_from_file_location("atomic_issue_compile_smoke", METHODOLOGY / "scripts" / "atomic_issue_compile.py")
        compiler = importlib.util.module_from_spec(compiler_spec)
        compiler_spec.loader.exec_module(compiler)
        consumer_packet = {
            "title": "ASG runtime consumes managed resource prerequisites",
            "primary_module": "MOD-ASG-RUNTIME",
            "module_responsibility": "Consume SG/IAM provenance created by MOD-MANAGED-RESOURCES.",
            "semantic_carriers": [
                {
                    "source": "C-010",
                    "owner_module": "MOD-MANAGED-RESOURCES",
                    "semantic_type": "Resource ownership",
                    "carrier": "managed resource ownership provenance for SG",
                    "must_preserve": ["SG identity and provenance are consumed by ASG runtime"],
                    "copied_to": ["consumed_contract_snapshots"],
                    "verification": "VER-011",
                    "omission_failure": "ASG runtime cannot consume SG identity",
                }
            ],
            "consumed_contract_snapshots": [
                {
                    "contract": "C-010-OBL-001",
                    "provider": "MOD-MANAGED-RESOURCES",
                    "may_assume": "SG provenance exists before ASG runtime create.",
                    "details": "ASG runtime consumes sgId only.",
                    "forbidden_interpretation": "ASG runtime does not own SG creation or cleanup.",
                }
            ],
            "behavior_details": {
                "inputs": "Consume SG identity from C-010-OBL-001.",
                "outputs": "Use SG identity for ASG launch.",
                "error_behavior": "Stop if prerequisite is missing.",
                "state_persistence": "No SG provenance writer in this task.",
                "compatibility": "No ownership lifecycle change.",
                "boundary_conditions": "Does not create or cleanup managed resources.",
            },
            "implementation_steps": ["Use existing SG identity from consumed contract; do not create or cleanup SG resources."],
            "verification": [{"check": "consumer smoke", "command": "mvn test", "expected_result": "pass", "proves": "consumer only", "failure_meaning": "missing prerequisite"}],
        }
        consumer_errors = compiler.validate_managed_resource_ownership_packet("T999", consumer_packet)
        if consumer_errors:
            errors.append(f"{METHODOLOGY / 'scripts' / 'atomic_issue_compile.py'}: managed resource consumer was incorrectly treated as owner: {consumer_errors}")
        recover_dir = root / "recover"
        recover_dir.mkdir()
        write_minimal_model_files(recover_dir)
        (recover_dir / "backflow.yaml").write_text("triggers:\n  BF-001:\n    status: resolved\n", encoding="utf-8")
        (recover_dir / "task-dag.yaml").write_text(
            "schema_version: 1\ntasks:\n  T001:\n    title: test\n    primary_module: runtime\n    files: []\n    issue: atomic-issues/T001.md\nedges: []\nparallel_groups: []\n",
            encoding="utf-8",
        )
        (recover_dir / "atomic-issue-packets.yaml").write_text(
            "schema_version: 1\npackets:\n  T001:\n    title: test\n    issue_path: atomic-issues/T001.md\n    primary_module: runtime\n    files_to_change: []\n",
            encoding="utf-8",
        )
        (recover_dir / "runtime-test-topology-matrix.md").write_text(topology_matrix, encoding="utf-8")
        bad_recover = subprocess.run(
            [
                sys.executable,
                str(WORKFLOWCTL),
                "recover-task-allowlist",
                "T001",
                str(recover_dir),
                "--add-file",
                "services/test/OtherTest.java",
                "--backflow-id",
                "BF-001",
                "--reason",
                "smoke",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if bad_recover.returncode == 0 or "must be declared" not in (bad_recover.stderr + bad_recover.stdout):
            errors.append(f"{WORKFLOWCTL}: recover-task-allowlist must reject undeclared proof files")
        recover_topology_matrix = """# Runtime Test Topology Matrix

## Runtime Test Topology Matrix

| Topology ID | Behavior/contract | Production path | Proof module/package | Proof file/path | Fixture/support files | Required build/install/freshness step | Why this proof owner is necessary | Staleness risk if skipped | Verification command | Expected result | Owner issue |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RTT-001 | C-001 proof fixture allowlist | proof fixture packaging path | proof fixture package | specs/proofs/runtime-proof.yaml | N/A | python3 scripts/check_allowlist_fixture.py specs/proofs/runtime-proof.yaml | owner issue must edit the proof fixture directly | stale fixture can hide allowlist drift | python3 scripts/check_allowlist_fixture.py specs/proofs/runtime-proof.yaml | command exits 0 and reads fixture | T001 |

## Proof Owner File Matrix

| Verification ID | Owner issue | Proof file/path | Must be in task-dag files? | Must be in packet files_to_change? | Fixture/support file | Reason | Status |
|---|---|---|---:|---:|---|---|---|
| VER-001 | T001 | specs/proofs/runtime-proof.yaml | yes | yes | N/A | declared proof owner file must be recoverable only after backflow | resolved |
"""
        recover_packet = """schema_version: 1
packets:
  T001:
    title: Proof Owner Fixture Allowlist
    issue_path: atomic-issues/T001.md
    primary_module: proof-owner-fixture
    module_responsibility: Maintain the declared proof owner fixture allowlist for one verification closure.
    scope:
      in:
        - Include the declared proof fixture path in the owner issue allowlist for this verification closure.
      out:
        - Do not change product code, API shape, runtime behavior, or frontend behavior from this recovery task.
    atomicity_review:
      atomic_boundary_check:
        zero_decision: All product and architecture decisions are already locked; this recovery only materializes one declared file path.
        single_layer_change: The task owns one proof fixture allowlist layer and does not mix implementation code.
        self_contained_context: The owner issue, packet, and declared fixture path provide enough context for execution.
        short_verification_loop: One local fixture check command closes the verification loop for this owner file.
        no_error_propagation: Failure blocks this owner issue before downstream execution can consume stale proof evidence.
      primary_closure: "one provided contract: declared proof fixture file is editable by its owner issue"
      user_action_flows:
        - "N/A: no user action is owned by this proof-file packet"
      stateful_operations:
        - "N/A: no stateful operation is owned by this proof-file packet"
      provided_contracts:
        - "C-001 proof owner fixture allowlist contract"
      verification_loops:
        - "VER-001 local fixture check command"
      fileset_reason: The fileset is limited to the declared proof fixture file and no production source paths.
      split_candidates_considered:
        - Product implementation files stay in their own owner issues; this packet only recovers proof fixture ownership.
      merge_rationale: ""
      still_atomic_because: It materializes one declared proof owner file for one verification closure.
    sources:
      - id: REQ-001
        excerpt: Proof owner fixture file must be included in the owner allowlist before execution edits.
    decisions:
      - id: DEC-001
        decision: Declared proof owner file is edited only by the owner issue during execution.
        why_it_matters: It prevents execution-time file expansion beyond the sealed task boundary.
    semantic_carriers:
      - source: C-001
        carrier: declared proof fixture ownership
        must_preserve:
          - The owner issue must include specs/proofs/runtime-proof.yaml in files_to_change before execution edits that proof fixture.
        copied_to:
          - behavior_details
          - implementation_steps
          - verification
        verification: VER-001
        omission_failure: The proof fixture could be edited outside the owner issue and bypass task diff validation.
    contract_excerpts:
      - id: C-001
        trigger: A verification proof file is declared for owner issue T001.
        normal_path: The declared proof fixture path is present in the owner issue allowlist.
        failure_path: Missing allowlist entry blocks execution until backflow recovery materializes the declared file.
        consistency: The same proof fixture path appears in packet files_to_change and task-dag files.
        timing: Recovery happens before execution of the owner issue begins.
        verification_excerpt: VER-001 checks the fixture path can be loaded by the local check command.
    execution_preconditions:
      - upstream: C-001
        already_true: Backflow BF-001 exists and declares that the owner proof file was omitted.
        evidence: runtime-test-topology-matrix names T001 as owner of specs/proofs/runtime-proof.yaml.
        if_false: Stop and record backflow before changing any allowlist.
    provided_contract_obligations:
      - contract: C-001
        downstream_consumer: task diff validation for owner issue T001
        must_guarantee: specs/proofs/runtime-proof.yaml is listed as an editable owner file for T001.
        observable_output: task-dag files and packet files_to_change contain the same proof fixture path.
        verification: VER-001
    invariant_carryover:
      - invariant: Only declared proof owner files may be recovered into an allowlist.
        source: C-001
        must_remain_true: Undeclared file paths still fail recovery and cannot be silently added.
        regression_check: Recovering services/test/OtherTest.java remains rejected.
    preconditions_failure_handling:
      - failure: Declared proof file is missing from topology and decomposition artifacts.
        classification: contract-materialization-gap
        required_backflow: Create or update the backflow trigger before any recovery command succeeds.
        do_not_do: Do not add arbitrary files directly to packet files_to_change.
    existing_code_references:
      - pattern: proof fixture owner file
        path: specs/proofs/runtime-proof.yaml
        follow: Keep the owner proof fixture path stable across task-dag and packet files.
        do_not_inherit: Do not use unrelated product source files as proof owner placeholders.
    files_to_change: []
    behavior_details:
      inputs: Declared proof owner file path specs/proofs/runtime-proof.yaml from the topology matrix.
      outputs: Owner issue T001 exposes the same proof fixture path in packet and task-dag allowlists.
      error_behavior: Undeclared files remain rejected by recovery before any packet compilation occurs.
      state_persistence: Workflow state records the recovery entry and refreshed receipts when present.
      compatibility: Existing sealed artifacts keep their meaning; only the declared owner file path is materialized.
      boundary_conditions: Recovery is limited to BF-001 and owner issue T001 for this fixture path.
    implementation_steps:
      - Add the declared proof fixture path to the owner issue allowlist through the recovery command.
      - Recompile the owner issue so Markdown reflects packet files_to_change and task-dag files.
    verification:
      - id: VER-001
        check: local fixture owner allowlist check
        command: python3 scripts/check_allowlist_fixture.py specs/proofs/runtime-proof.yaml
        expected_result: command exits 0 after reading the declared proof fixture path.
        proves: The owner issue exposes specs/proofs/runtime-proof.yaml for execution-time diff validation.
        failure_meaning: The proof owner allowlist still misses the declared fixture path.
    prohibited_changes:
      - Do not add undeclared files or unrelated production code paths during this recovery.
      - Do not mark task execution passed from this recovery command alone.
    done_criteria:
      - T001 packet and task-dag both contain specs/proofs/runtime-proof.yaml.
      - workflow-state.yaml records the allowlist recovery with BF-001.
"""
        (recover_dir / "runtime-test-topology-matrix.md").write_text(recover_topology_matrix, encoding="utf-8")
        (recover_dir / "atomic-issue-packets.yaml").write_text(recover_packet, encoding="utf-8")
        workflow_doc = workflowctl.load_yaml(recover_dir / "workflow-state.yaml")
        workflow_doc["execution_receipt"] = {
            "status": "started",
            "artifact_hashes": workflowctl.artifact_digest_map(recover_dir, "pre-execution"),
            "sealed_artifact_hashes": workflowctl.sealed_artifact_digest_map(recover_dir),
            "stage_receipt_hashes": {"task-planning": "smoke-task-planning-receipt"},
            "git_state": workflowctl.current_git_state(recover_dir),
        }
        workflowctl.write_yaml(recover_dir / "workflow-state.yaml", workflow_doc)
        good_recover = subprocess.run(
            [
                sys.executable,
                str(WORKFLOWCTL),
                "recover-task-allowlist",
                "T001",
                str(recover_dir),
                "--add-file",
                "specs/proofs/runtime-proof.yaml",
                "--backflow-id",
                "BF-001",
                "--reason",
                "declared proof owner file omitted from allowlist",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if good_recover.returncode != 0:
            errors.append(f"{WORKFLOWCTL}: recover-task-allowlist should accept declared proof files: {good_recover.stderr or good_recover.stdout}")
        else:
            task_dag_after = read(recover_dir / "task-dag.yaml")
            packet_after = read(recover_dir / "atomic-issue-packets.yaml")
            workflow_after = read(recover_dir / "workflow-state.yaml")
            if "specs/proofs/runtime-proof.yaml" not in task_dag_after:
                errors.append(f"{WORKFLOWCTL}: recover-task-allowlist did not update task-dag files")
            if "specs/proofs/runtime-proof.yaml" not in packet_after:
                errors.append(f"{WORKFLOWCTL}: recover-task-allowlist did not update packet files_to_change")
            if "allowlist_recoveries" not in workflow_after or "BF-001" not in workflow_after:
                errors.append(f"{WORKFLOWCTL}: recover-task-allowlist did not append workflow recovery ledger")
            receipt_errors = workflowctl.execution_receipt_errors(workflowctl.WorkflowModel(recover_dir))
            if receipt_errors:
                errors.append(f"{WORKFLOWCTL}: recover-task-allowlist left stale execution receipt: {receipt_errors}")
    return errors


def validate_human_decision_and_mpr_smoke() -> list[str]:
    errors: list[str] = []
    workflow_spec = importlib.util.spec_from_file_location("workflowctl_human_mpr_smoke", WORKFLOWCTL)
    workflowctl = importlib.util.module_from_spec(workflow_spec)
    assert workflow_spec.loader is not None
    workflow_spec.loader.exec_module(workflowctl)

    artifact_spec = importlib.util.spec_from_file_location("validate_artifacts_human_mpr_smoke", ARTIFACT_VALIDATOR)
    artifact_validator = importlib.util.module_from_spec(artifact_spec)
    assert artifact_spec.loader is not None
    artifact_spec.loader.exec_module(artifact_validator)

    def write_common(change_dir: Path) -> None:
        (change_dir / "decision-reviews").mkdir(parents=True, exist_ok=True)
        (change_dir / "multi-perspective-reviews").mkdir(parents=True, exist_ok=True)
        (change_dir / "workflow-state.yaml").write_text(
            """schema_version: 1
workflow:
  skill: automq-ai-dev-workflow-contextpack
  context_pack_required: true
stage_status:
  source-intake: not_started
  prd: in_progress
  aip: not_started
  readiness: not_started
  design: not_started
  archaeology: not_started
  migration: not_started
  frontend-contract: not_started
  contract: not_started
  verification: not_started
  task-planning: not_started
  execution: not_started
  mock-acceptance: not_started
  product-acceptance: not_started
stage_receipts: {}
""",
            encoding="utf-8",
        )
        (change_dir / "proposal.md").write_text(
            """# Proposal

## Human Decision Participation Gate

Mode: human-decision-participation.

## Product Decisions

| ID | Question | Final decision | Status |
|---|---|---|---|
| PDEC-001 | Which resource owner creates the runtime resource? | user decides | open |
""",
            encoding="utf-8",
        )
        (change_dir / "spec.md").write_text("## Requirements\n\nREQ-001 requires PDEC-001.\n", encoding="utf-8")
        (change_dir / "plan.md").write_text("", encoding="utf-8")
        (change_dir / "tasks.md").write_text("", encoding="utf-8")
        (change_dir / "source-intake-ledger.md").write_text("", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="automq-human-mpr-smoke-") as tmp:
        root = Path(tmp)
        bad = root / "bad"
        bad.mkdir()
        write_common(bad)
        (bad / "decision-reviews" / "prd-decisions.md").write_text(
            """# PRD Decisions

## 决策摘要

| ID | Type | Decision key | Question | Final decision | Decided by | Status |
|---|---|---|---|---|---|---|
| PDEC-001 | product | runtime-owner | Who creates the runtime resource? | User decides | user-confirmed | locked |

## 决策详情

### PDEC-001: runtime owner

| Item | Content |
|---|---|
| Question | Who creates the runtime resource? |
| Final decision | User decides |
| Decided by | user-confirmed |
""",
            encoding="utf-8",
        )
        bad_model = workflowctl.WorkflowModel(bad)
        bad_workflow_errors = workflowctl.validate_human_decision_records(bad_model, "prd")
        if not bad_workflow_errors:
            errors.append(f"{WORKFLOWCTL}: missing one-by-one human decision prompt record was not rejected")
        bad_artifact_errors = artifact_validator.validate_human_decision_records(
            bad,
            "prd",
            "\n".join((bad / name).read_text(encoding="utf-8") for name in ["proposal.md", "spec.md", "plan.md", "tasks.md", "source-intake-ledger.md"]),
            artifact_validator.read_yaml(bad / "workflow-state.yaml"),
        )
        if not bad_artifact_errors:
            errors.append(f"{ARTIFACT_VALIDATOR}: missing one-by-one human decision prompt record was not rejected")

        good = root / "good"
        good.mkdir()
        write_common(good)
        interaction = """## User Decision Interaction

| Stage | Decision ID | Decision key | Question | Prompt ID | Prompt summary | Recommended option | Alternatives | Why recommended | User impact | Affected artifacts | Verification | User response | Final status | Decided at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| prd | PDEC-001 | runtime-owner | Who creates the runtime resource? | HDP-001 | Human Decision Prompt explained resource ownership. | user-created | ai-created | preserves ownership clarity | user-visible ownership | proposal.md; decision-reviews/prd-decisions.md | VER-001 | confirmed by user | locked | 2026-06-12T00:00:00Z |
"""
        (good / "proposal.md").write_text((good / "proposal.md").read_text(encoding="utf-8") + "\n" + interaction, encoding="utf-8")
        (good / "decision-reviews" / "prd-decisions.md").write_text(
            """# PRD Decisions

## 决策摘要

| ID | Type | Decision key | Question | Final decision | Decided by | Status |
|---|---|---|---|---|---|---|
| PDEC-001 | product | runtime-owner | Who creates the runtime resource? | User creates runtime resource | user-confirmed via HDP-001 at 2026-06-12T00:00:00Z | locked |

## 决策详情

### PDEC-001: runtime owner

| Item | Content |
|---|---|
| Question | Who creates the runtime resource? |
| Human Decision Prompt | HDP-001 |
| Prompt summary | Human Decision Prompt explained resource ownership. |
| User response | confirmed by user |
| Final decision | User creates runtime resource |
| Status | locked |
| Decided at | 2026-06-12T00:00:00Z |
""",
            encoding="utf-8",
        )
        good_model = workflowctl.WorkflowModel(good)
        good_workflow_errors = workflowctl.validate_human_decision_records(good_model, "prd")
        if good_workflow_errors:
            errors.append(f"{WORKFLOWCTL}: complete human decision record should pass, got {good_workflow_errors}")
        good_artifact_errors = artifact_validator.validate_human_decision_records(
            good,
            "prd",
            "\n".join((good / name).read_text(encoding="utf-8") for name in ["proposal.md", "spec.md", "plan.md", "tasks.md", "source-intake-ledger.md"]),
            artifact_validator.read_yaml(good / "workflow-state.yaml"),
        )
        if good_artifact_errors:
            errors.append(f"{ARTIFACT_VALIDATOR}: complete human decision record should pass, got {good_artifact_errors}")

        bundle_dir = root / "good-decision-bundle"
        bundle_dir.mkdir()
        write_common(bundle_dir)
        (bundle_dir / "decision-bundles").mkdir()
        bundle_interaction = """## User Decision Interaction

| Stage | Decision ID | Decision key | Prompt ID | Prompt summary | Recommended option | Alternatives | User response | Final status | Decided at |
|---|---|---|---|---|---|---|---|---|---|
| prd | PDEC-001; PDEC-002 | bundled-product-decisions | HDB-001 | Batch prompt lists both decisions and all impacts. | adopt both recommendations | reject or split either decision | 同意以上全部列出的决策 | locked | 2026-07-17T00:00:00Z |
"""
        (bundle_dir / "proposal.md").write_text(
            (bundle_dir / "proposal.md").read_text(encoding="utf-8")
            + "\nPDEC-002 selects the second product behavior.\n"
            + bundle_interaction,
            encoding="utf-8",
        )
        (bundle_dir / "decision-reviews" / "prd-decisions.md").write_text(
            """# PRD Decisions

| ID | Decision key | Final decision | Status |
|---|---|---|---|
| PDEC-001 | runtime-owner | user-created | locked |
| PDEC-002 | lifecycle-owner | controller-created | locked |
""",
            encoding="utf-8",
        )
        prompt_snapshot = (
            "HDB-001 asks the user to approve PDEC-001 runtime ownership and PDEC-002 lifecycle ownership. "
            "It lists the recommended choices, rejected alternatives, product impact, verification impact, and downstream consumers."
        )
        bundle_doc = {
            "schema_version": 1,
            "bundle_id": "HDB-001",
            "stage": "prd",
            "prompt_snapshot": prompt_snapshot,
            "prompt_hash": hashlib.sha256((prompt_snapshot + "\n").encode("utf-8")).hexdigest(),
            "response_scope": "all-listed",
            "user_response": "同意以上全部列出的决策",
            "status": "locked",
            "decided_at": "2026-07-17T00:00:00Z",
            "decisions": [
                {
                    "decision_id": "PDEC-001",
                    "decision_key": "runtime.owner",
                    "recommendation": "The user owns runtime creation.",
                    "alternatives": "The controller creates the runtime instead.",
                    "impact": "Locks ownership, API behavior, verification, and downstream consumers.",
                    "batch_eligible": True,
                },
                {
                    "decision_id": "PDEC-002",
                    "decision_key": "lifecycle.owner",
                    "recommendation": "The controller owns lifecycle reconciliation.",
                    "alternatives": "The user performs lifecycle reconciliation manually.",
                    "impact": "Locks lifecycle states, failure behavior, verification, and consumers.",
                    "batch_eligible": True,
                },
            ],
        }
        bundle_doc["receipt_hash"] = workflowctl.canonical_receipt_hash(bundle_doc)
        workflowctl.write_yaml(bundle_dir / "decision-bundles" / "HDB-001.yaml", bundle_doc)
        prd_hashes_before_downstream_bundle = workflowctl.artifact_digest_map(bundle_dir, "prd")
        artifact_prd_hashes_before_downstream_bundle = artifact_validator.artifact_digest_map(bundle_dir, "prd")
        downstream_bundle = copy.deepcopy(bundle_doc)
        downstream_bundle["bundle_id"] = "HDB-002"
        downstream_bundle["stage"] = "aip"
        downstream_bundle["decisions"][0]["decision_id"] = "ADEC-001"
        downstream_bundle["decisions"][1]["decision_id"] = "ADEC-002"
        downstream_bundle["receipt_hash"] = workflowctl.canonical_receipt_hash(downstream_bundle)
        workflowctl.write_yaml(bundle_dir / "decision-bundles" / "HDB-002.yaml", downstream_bundle)
        for validator_name, before_hashes, after_hashes in [
            (
                str(WORKFLOWCTL),
                prd_hashes_before_downstream_bundle,
                workflowctl.artifact_digest_map(bundle_dir, "prd"),
            ),
            (
                str(ARTIFACT_VALIDATOR),
                artifact_prd_hashes_before_downstream_bundle,
                artifact_validator.artifact_digest_map(bundle_dir, "prd"),
            ),
        ]:
            if before_hashes != after_hashes or "decision-bundles/HDB-002.yaml" in after_hashes:
                errors.append(f"{validator_name}: downstream AIP decision bundle invalidated the PRD receipt")
        bundled_ids, bundle_errors = workflowctl.human_decision_bundle_records(bundle_dir, "prd")
        if bundle_errors or bundled_ids != {"PDEC-001", "PDEC-002"}:
            errors.append(f"{WORKFLOWCTL}: valid decision bundle was rejected: {bundle_errors}, ids={bundled_ids}")
        artifact_bundled_ids, artifact_bundle_errors = artifact_validator.human_decision_bundle_records(bundle_dir, "prd")
        if artifact_bundle_errors or artifact_bundled_ids != {"PDEC-001", "PDEC-002"}:
            errors.append(
                f"{ARTIFACT_VALIDATOR}: valid decision bundle was rejected: {artifact_bundle_errors}, ids={artifact_bundled_ids}"
            )
        bundled_workflow_errors = workflowctl.validate_human_decision_records(
            workflowctl.WorkflowModel(bundle_dir), "prd"
        )
        if bundled_workflow_errors:
            errors.append(f"{WORKFLOWCTL}: valid bundled human decisions should pass: {bundled_workflow_errors}")
        bundled_artifact_errors = artifact_validator.validate_human_decision_records(
            bundle_dir,
            "prd",
            "\n".join(
                (bundle_dir / name).read_text(encoding="utf-8")
                for name in ["proposal.md", "spec.md", "plan.md", "tasks.md", "source-intake-ledger.md"]
            ),
            artifact_validator.read_yaml(bundle_dir / "workflow-state.yaml"),
        )
        if bundled_artifact_errors:
            errors.append(f"{ARTIFACT_VALIDATOR}: valid bundled human decisions should pass: {bundled_artifact_errors}")

        negative_bundle = copy.deepcopy(bundle_doc)
        negative_bundle["user_response"] = "不同意以上全部列出的决策"
        negative_bundle["receipt_hash"] = workflowctl.canonical_receipt_hash(negative_bundle)
        workflowctl.write_yaml(bundle_dir / "decision-bundles" / "HDB-001.yaml", negative_bundle)
        for validator_name, bundle_result in [
            (str(WORKFLOWCTL), workflowctl.human_decision_bundle_records(bundle_dir, "prd")),
            (str(ARTIFACT_VALIDATOR), artifact_validator.human_decision_bundle_records(bundle_dir, "prd")),
        ]:
            if not any("affirmatively confirm all listed" in error for error in bundle_result[1]):
                errors.append(f"{validator_name}: negative batch response was accepted")

        invalid_time_bundle = copy.deepcopy(bundle_doc)
        invalid_time_bundle["decided_at"] = "decided at some later time"
        invalid_time_bundle["receipt_hash"] = workflowctl.canonical_receipt_hash(invalid_time_bundle)
        workflowctl.write_yaml(bundle_dir / "decision-bundles" / "HDB-001.yaml", invalid_time_bundle)
        for validator_name, bundle_result in [
            (str(WORKFLOWCTL), workflowctl.human_decision_bundle_records(bundle_dir, "prd")),
            (str(ARTIFACT_VALIDATOR), artifact_validator.human_decision_bundle_records(bundle_dir, "prd")),
        ]:
            if not any("ISO-8601" in error for error in bundle_result[1]):
                errors.append(f"{validator_name}: non-timestamp decided_at was accepted")

        wrong_stage_bundle = copy.deepcopy(bundle_doc)
        wrong_stage_bundle["decisions"][1]["decision_id"] = "ADEC-002"
        wrong_stage_bundle["receipt_hash"] = workflowctl.canonical_receipt_hash(wrong_stage_bundle)
        workflowctl.write_yaml(bundle_dir / "decision-bundles" / "HDB-001.yaml", wrong_stage_bundle)
        for validator_name, bundle_result in [
            (str(WORKFLOWCTL), workflowctl.human_decision_bundle_records(bundle_dir, "prd")),
            (str(ARTIFACT_VALIDATOR), artifact_validator.human_decision_bundle_records(bundle_dir, "prd")),
        ]:
            if not any("must belong to stage prd" in error for error in bundle_result[1]):
                errors.append(f"{validator_name}: cross-stage decision bundle was accepted")

        malformed_bundle_path = bundle_dir / "decision-bundles" / "HDB-003.yaml"
        malformed_bundle_path.write_text("schema_version: [unterminated\n", encoding="utf-8")
        for validator_name, bundle_result in [
            (str(WORKFLOWCTL), workflowctl.human_decision_bundle_records(bundle_dir, "prd")),
            (str(ARTIFACT_VALIDATOR), artifact_validator.human_decision_bundle_records(bundle_dir, "prd")),
        ]:
            if not bundle_result[1]:
                errors.append(f"{validator_name}: malformed decision bundle did not produce a repairable validation error")
        malformed_bundle_path.unlink()

        def write_ai_authority_common(change_dir: Path, authority_section: str) -> None:
            (change_dir / "decision-reviews").mkdir(parents=True, exist_ok=True)
            (change_dir / "workflow-state.yaml").write_text(
                """schema_version: 1
stage_status:
  source-intake: not_started
  prd: in_progress
  aip: not_started
  readiness: not_started
  design: not_started
  archaeology: not_started
  migration: not_started
  frontend-contract: not_started
  contract: not_started
  verification: not_started
  task-planning: not_started
  execution: not_started
  mock-acceptance: not_started
  product-acceptance: not_started
stage_receipts: {}
""",
                encoding="utf-8",
            )
            (change_dir / "proposal.md").write_text(
                f"""# Proposal

{authority_section}

## Product Decisions

PDEC-001 chooses product behavior.
""",
                encoding="utf-8",
            )
            (change_dir / "spec.md").write_text("REQ-001 depends on PDEC-001.\n", encoding="utf-8")
            (change_dir / "plan.md").write_text("", encoding="utf-8")
            (change_dir / "tasks.md").write_text("", encoding="utf-8")
            (change_dir / "source-intake-ledger.md").write_text("", encoding="utf-8")
            (change_dir / "decision-reviews" / "prd-decisions.md").write_text(
                """# PRD Decisions

| ID | Decision key | Status |
|---|---|---|
| PDEC-001 | product-behavior | locked |
""",
                encoding="utf-8",
            )

        bad_auth = root / "bad-auth-enum"
        bad_auth.mkdir()
        write_ai_authority_common(
            bad_auth,
            """## Decision Authority

Allowed values documented here: user-confirmed / ai-authorized / not-authorized.
""",
        )
        bad_auth_model = workflowctl.WorkflowModel(bad_auth)
        bad_auth_workflow_errors = workflowctl.validate_human_decision_records(bad_auth_model, "prd")
        if not any("PDEC-001" in error or "requires human decision records" in error for error in bad_auth_workflow_errors):
            errors.append(f"{WORKFLOWCTL}: ai-authorized enum text was incorrectly treated as real user authorization")
        bad_auth_artifact_errors = artifact_validator.validate_human_decision_records(
            bad_auth,
            "prd",
            "\n".join((bad_auth / name).read_text(encoding="utf-8") for name in ["proposal.md", "spec.md", "plan.md", "tasks.md", "source-intake-ledger.md"]),
            artifact_validator.read_yaml(bad_auth / "workflow-state.yaml"),
        )
        if not any("PDEC-001" in error or "requires human decision records" in error for error in bad_auth_artifact_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: ai-authorized enum text was incorrectly treated as real user authorization")

        good_auth = root / "good-auth-table"
        good_auth.mkdir()
        write_ai_authority_common(
            good_auth,
            """## Decision Authority

| Scope | Authority | Evidence | Limits |
|---|---|---|---|
| product decisions | ai-authorized | 2026-06-12 user message: 授权 AI 按推荐方案锁定 PRD product decisions | only current PDEC scope |
""",
        )
        good_auth_workflow_errors = workflowctl.validate_human_decision_records(workflowctl.WorkflowModel(good_auth), "prd")
        if good_auth_workflow_errors:
            errors.append(f"{WORKFLOWCTL}: explicit scoped AI authorization should pass, got {good_auth_workflow_errors}")
        good_auth_artifact_errors = artifact_validator.validate_human_decision_records(
            good_auth,
            "prd",
            "\n".join((good_auth / name).read_text(encoding="utf-8") for name in ["proposal.md", "spec.md", "plan.md", "tasks.md", "source-intake-ledger.md"]),
            artifact_validator.read_yaml(good_auth / "workflow-state.yaml"),
        )
        if good_auth_artifact_errors:
            errors.append(f"{ARTIFACT_VALIDATOR}: explicit scoped AI authorization should pass, got {good_auth_artifact_errors}")

        bad_mpr = root / "bad-mpr"
        bad_mpr.mkdir()
        write_common(bad_mpr)
        (bad_mpr / "multi-perspective-reviews" / "prd.yaml").write_text(
            """schema_version: 1
review_scope:
  stage_under_review: prd
  gate_name: prd
  main_agent_owner: main
  required_reviewer_count: 2
frozen_input_packet:
  stage_objective: Lock PRD.
  review_objective: Review PRD.
  frozen_artifacts:
    - path: proposal.md
      role: prd
  reviewable_scope:
    - PRD
  non_reviewable_scope:
    - code
  digest_policy:
    stage_artifact_digest: workflowctl.artifact_receipt_digest
    workflow_workdir_policy: normalized-identity-before-resume-verification
    treat_receipt_digest_as_raw_sha256: false
  decision_surface_inputs:
    required_when_applicable: false
reviewers:
  - reviewer_id: R1
    reviewer_type: readonly-subagent
    perspective: product-semantics
    assigned_objective: Review product semantics.
    frozen_input_refs:
      - proposal.md
    forbidden_scope:
      - code
    status: completed
  - reviewer_id: R2
    reviewer_type: main-local-fallback
    perspective: architecture-owner
    assigned_objective: Review owner.
    frozen_input_refs:
      - proposal.md
    forbidden_scope:
      - code
    status: completed
findings: []
main_agent_dispositions: []
gate_result:
  verdict: pass
  blocking_findings_open: []
  validators_rerun:
    - workflowctl validate prd
  ready_for_next_stage: true
""",
            encoding="utf-8",
        )
        mpr_workflow_errors = workflowctl.validate_multi_perspective_review(workflowctl.WorkflowModel(bad_mpr), "prd")
        if not any("main-local fallback is not allowed" in error or "invalid reviewer_type" in error for error in mpr_workflow_errors):
            errors.append(f"{WORKFLOWCTL}: main-local-fallback reviewer was not rejected")
        mpr_artifact_errors = artifact_validator.validate_multi_perspective_review(bad_mpr, "prd")
        if not any("main-local fallback is not allowed" in error or "invalid reviewer_type" in error for error in mpr_artifact_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: main-local-fallback reviewer was not rejected")

        repair_review = artifact_validator.read_yaml(bad_mpr / "multi-perspective-reviews" / "prd.yaml")
        repair_review["review_scope"]["review_kind"] = "semantic-repair"
        repair_review["review_scope"]["required_reviewer_count"] = 1
        repair_review["reviewers"] = repair_review["reviewers"][:1]
        workflowctl.write_yaml(bad_mpr / "multi-perspective-reviews" / "prd.yaml", repair_review)
        for validator_name, review_errors in [
            (str(WORKFLOWCTL), workflowctl.validate_multi_perspective_review(workflowctl.WorkflowModel(bad_mpr), "prd")),
            (str(ARTIFACT_VALIDATOR), artifact_validator.validate_multi_perspective_review(bad_mpr, "prd")),
        ]:
            if not any("repair_context.previous_review_ref" in error for error in review_errors):
                errors.append(f"{validator_name}: repair review bypassed initial-review evidence")
        repair_review["repair_context"] = {
            "previous_review_ref": "multi-perspective-reviews/archive/prd-initial.yaml",
            "triggering_findings": [
                {
                    "finding_id": "MPR-001",
                    "perspective": "product-semantics",
                    "root_cause": "The canonical PRD owner omitted one product invariant.",
                    "canonical_owner": "proposal.md#Product Semantics",
                    "invariant": "The repaired product semantic remains consistent in all projections.",
                    "affected_artifacts": ["proposal.md"],
                    "projection_targets": ["spec.md#Acceptance Scenarios"],
                    "deterministic_proof": "workflowctl preflight-stage-closures prd passes.",
                    "negative_assertion": "No stale contradictory product semantic remains.",
                }
            ],
            "changed_artifacts": ["proposal.md"],
            "narrowed_review_reason": "Only the accepted product-semantics finding changed in this repair.",
        }
        workflowctl.write_yaml(bad_mpr / "multi-perspective-reviews" / "prd.yaml", repair_review)
        for validator_name, review_errors in [
            (str(WORKFLOWCTL), workflowctl.validate_multi_perspective_review(workflowctl.WorkflowModel(bad_mpr), "prd")),
            (str(ARTIFACT_VALIDATOR), artifact_validator.validate_multi_perspective_review(bad_mpr, "prd")),
        ]:
            if any("requires at least" in error for error in review_errors):
                errors.append(f"{validator_name}: one-reviewer semantic repair was rejected by review policy")
            if any("triggering finding perspectives" in error for error in review_errors):
                errors.append(f"{validator_name}: correctly scoped repair perspectives were rejected")

        bad_repair = copy.deepcopy(repair_review)
        bad_repair["repair_context"]["triggering_findings"][0]["projection_targets"] = []
        bad_repair["reviewers"][0]["perspective"] = "architecture-owner"
        workflowctl.write_yaml(bad_mpr / "multi-perspective-reviews" / "prd.yaml", bad_repair)
        for validator_name, review_errors in [
            (str(WORKFLOWCTL), workflowctl.validate_multi_perspective_review(workflowctl.WorkflowModel(bad_mpr), "prd")),
            (str(ARTIFACT_VALIDATOR), artifact_validator.validate_multi_perspective_review(bad_mpr, "prd")),
        ]:
            if not any("projection_targets" in error for error in review_errors):
                errors.append(f"{validator_name}: repair review accepted an unclosed projection set")
            if not any("exactly match triggering finding perspectives" in error for error in review_errors):
                errors.append(f"{validator_name}: repair review accepted unrelated reviewer perspectives")

        extra_reviewer_repair = copy.deepcopy(repair_review)
        extra_reviewer = copy.deepcopy(extra_reviewer_repair["reviewers"][0])
        extra_reviewer["reviewer_id"] = "R-extra"
        extra_reviewer_repair["reviewers"].append(extra_reviewer)
        workflowctl.write_yaml(bad_mpr / "multi-perspective-reviews" / "prd.yaml", extra_reviewer_repair)
        for validator_name, review_errors in [
            (str(WORKFLOWCTL), workflowctl.validate_multi_perspective_review(workflowctl.WorkflowModel(bad_mpr), "prd")),
            (str(ARTIFACT_VALIDATOR), artifact_validator.validate_multi_perspective_review(bad_mpr, "prd")),
        ]:
            if not any("reviewers count must exactly equal" in error for error in review_errors):
                errors.append(f"{validator_name}: repair review accepted redundant same-perspective reviewers")

        if "source-intake" in workflowctl.MULTI_PERSPECTIVE_REVIEW_STAGES:
            errors.append(f"{WORKFLOWCTL}: source-intake must not require a multi-perspective review")
        if "source-intake" in artifact_validator.MULTI_PERSPECTIVE_REVIEW_STAGES:
            errors.append(f"{ARTIFACT_VALIDATOR}: source-intake must not require a multi-perspective review")

        if "acceptance" in workflowctl.MULTI_PERSPECTIVE_REVIEW_STAGES:
            errors.append(f"{WORKFLOWCTL}: generic acceptance must not be a standalone multi-perspective review stage")
        if "acceptance" in artifact_validator.MULTI_PERSPECTIVE_REVIEW_STAGES:
            errors.append(f"{ARTIFACT_VALIDATOR}: generic acceptance must not be a standalone multi-perspective review stage")
    return errors


def validate_launch_readiness_smoke() -> list[str]:
    errors: list[str] = []
    import importlib.util

    workflow_spec = importlib.util.spec_from_file_location("workflowctl_launch_readiness_smoke", WORKFLOWCTL)
    workflowctl = importlib.util.module_from_spec(workflow_spec)
    workflow_spec.loader.exec_module(workflowctl)

    def write_launch_state(change_dir: Path, *, with_mock_receipt: bool = True) -> None:
        (change_dir / "tasks.md").write_text("T001 launch readiness smoke task\n", encoding="utf-8")
        (change_dir / "mock-acceptance.md").write_text("mock acceptance evidence\n", encoding="utf-8")
        (change_dir / "task-dag.yaml").write_text(
            """schema_version: 1
tasks:
  T001:
    title: launch readiness smoke task
edges: []
""",
            encoding="utf-8",
        )
        (change_dir / "workflow-state.yaml").write_text(
            """schema_version: 1
workflow:
  context_pack_required: false
stage_status:
  execution: in_progress
  mock-acceptance: passed
  product-acceptance: not_applicable
stage_receipts:
  mock-acceptance:
    stage: mock-acceptance
    status: passed
task_receipts:
  T001:
    task: T001
    status: passed
    passed_at: 2026-06-16T00:00:00+00:00
    validator: workflowctl.py
    command: workflowctl pass-task T001
    diff_validated: true
    verification_log: task-verification-log.yaml
    verification_log_hash: legacy-smoke
    semantic_review_log: task-semantic-review.yaml
    semantic_review_hash: smoke
    semantic_review_verdict: pass
    git_state: {}
    passed_git_commit: legacy-smoke
    passed_changed_path_hashes: {}
    passed_declared_output_hashes: {}
    receipt_hash: legacy-smoke
execution_receipt:
  status: started
  artifact_hashes: {}
  sealed_artifact_hashes: {}
  stage_receipt_hashes:
    pre-execution: placeholder
""",
            encoding="utf-8",
        )
        if not with_mock_receipt:
            (change_dir / "workflow-state.yaml").write_text(
                (change_dir / "workflow-state.yaml").read_text(encoding="utf-8").replace("mock-acceptance: passed", "mock-acceptance: in_progress").replace(
                    """stage_receipts:
  mock-acceptance:
    stage: mock-acceptance
    status: passed
""",
                    "stage_receipts:\n  {}\n",
                ),
                encoding="utf-8",
            )
        workflow_doc = workflowctl.load_yaml(change_dir / "workflow-state.yaml")
        workflow_doc["execution_receipt"]["artifact_hashes"] = workflowctl.artifact_digest_map(change_dir, "pre-execution")
        workflow_doc["execution_receipt"]["sealed_artifact_hashes"] = workflowctl.sealed_artifact_digest_map(change_dir)
        workflowctl.write_yaml(change_dir / "workflow-state.yaml", workflow_doc)

    valid_review = """# Launch Readiness Review

## Review Input

| Field | Value |
|---|---|
| Integration PR / diff artifact | diff-artifact-001 |
| Base | main |
| Head | codex/example-head-uid |
| Diff source | PR compare URL |
| Review date | 2026-06-16 |
| Reviewer | main agent |

## Production Launch Standard Sources

| Source | Path / URL / ID | How it defines launch standard |
|---|---|---|
| Product requirement | proposal.md / spec.md / REQ-001 / SCN-001 | user journey |
| AIP / engineering decision | aip.md / plan.md / ADEC-001 / DEC-001 | architecture |
| Contract source | contracts.yaml / C-001 | semantic contract |
| Verification source | verification.yaml / VER-001 | proof |
| Acceptance evidence | mock-acceptance.md / mock-acceptance-execution.yaml / acceptance/product-acceptance-review.md | evidence |
| Actual implementation | PR diff / changed files | implementation |

## Closure Review

| Closure | Review question | Evidence | Verdict | Notes |
|---|---|---|---|---|
| User journey | Key requirement user journeys are end-to-end closed. | PR/API/browser evidence | pass | closed |
| Domain semantic | Core domain semantics are implemented as behavior. | code/test evidence | pass | closed |
| Runtime / external effect | Required provider/API/runtime side effects occur. | provider/readback evidence | pass | closed |
| State and failure | State and failure semantics match runtime. | test/log/event evidence | pass | closed |
| Compatibility and boundary | Existing/new mode boundaries do not leak. | API/UI/DB evidence | pass | closed |
| Acceptance evidence | Evidence covers representative launch scenarios. | mock/product evidence | pass | closed |

## Findings

| ID | Type | Severity | Source / evidence | Owner | Required action | Status |
|---|---|---|---|---|---|---|
| LRR-001 | allowed_implementation_variance | non-blocking | PR and requirement evidence | main | record variance | closed |

## Resolution Ledger

| Item | Finding ID | Action type | Artifact / code changed | Verification rerun | Result |
|---|---|---|---|---|---|
| LRR-FIX-001 | LRR-001 | recorded variance | launch-readiness-review.md | workflowctl validate-launch-readiness | closed |

## Final Verdict

launch_ready: yes
open_launch_blockers: 0
"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        missing_errors = workflowctl.validate_launch_readiness(root / "missing")
        if not any("missing" in error for error in missing_errors):
            errors.append(f"{WORKFLOWCTL}: missing launch-readiness-review.md was not rejected")

        good = root / "good"
        good.mkdir()
        write_launch_state(good)
        (good / "mock-acceptance.md").write_text("mock acceptance evidence\n", encoding="utf-8")
        (good / "launch-readiness-review.md").write_text(valid_review, encoding="utf-8")
        good_errors = workflowctl.validate_launch_readiness(good)
        if good_errors:
            errors.append(f"{WORKFLOWCTL}: valid launch readiness review should pass, got {good_errors}")

        missing_acceptance = root / "missing-acceptance-stages"
        missing_acceptance.mkdir()
        write_launch_state(missing_acceptance, with_mock_receipt=False)
        missing_acceptance_state = workflowctl.as_dict(
            workflowctl.load_yaml(missing_acceptance / "workflow-state.yaml")
        )
        missing_acceptance_state["schema_version"] = 2
        workflowctl.as_dict(missing_acceptance_state.get("workflow"))[
            "stage_construction_protocol"
        ] = "stage-construction-v1"
        acceptance_status = workflowctl.as_dict(missing_acceptance_state.get("stage_status"))
        acceptance_status["mock-acceptance"] = "not_started"
        acceptance_status["product-acceptance"] = "not_started"
        workflowctl.write_yaml(missing_acceptance / "workflow-state.yaml", missing_acceptance_state)
        (missing_acceptance / "launch-readiness-review.md").write_text(valid_review, encoding="utf-8")
        acceptance_errors = workflowctl.validate_launch_readiness(missing_acceptance)
        if not all(any(stage in error and "passed or explicitly not_applicable" in error for error in acceptance_errors) for stage in ["mock-acceptance", "product-acceptance"]):
            errors.append(f"{WORKFLOWCTL}: launch readiness allowed unclosed acceptance stages")

        no_pr = root / "no-pr"
        no_pr.mkdir()
        write_launch_state(no_pr)
        (no_pr / "mock-acceptance.md").write_text("mock acceptance evidence\n", encoding="utf-8")
        (no_pr / "launch-readiness-review.md").write_text(
            valid_review.replace("diff-artifact-001", "not recorded"),
            encoding="utf-8",
        )
        no_pr_errors = workflowctl.validate_launch_readiness(no_pr)
        if not any("PR" in error or "diff artifact" in error for error in no_pr_errors):
            errors.append(f"{WORKFLOWCTL}: missing PR/diff input was not rejected")

        bad_type = root / "bad-type"
        bad_type.mkdir()
        write_launch_state(bad_type)
        (bad_type / "mock-acceptance.md").write_text("mock acceptance evidence\n", encoding="utf-8")
        (bad_type / "launch-readiness-review.md").write_text(
            valid_review.replace("allowed_implementation_variance", "implementation_difference"),
            encoding="utf-8",
        )
        bad_type_errors = workflowctl.validate_launch_readiness(bad_type)
        if not any("invalid finding type" in error for error in bad_type_errors):
            errors.append(f"{WORKFLOWCTL}: invalid launch readiness finding type was not rejected")

        open_blocker = root / "open-blocker"
        open_blocker.mkdir()
        write_launch_state(open_blocker)
        (open_blocker / "mock-acceptance.md").write_text("mock acceptance evidence\n", encoding="utf-8")
        (open_blocker / "launch-readiness-review.md").write_text(
            valid_review
            .replace("allowed_implementation_variance | non-blocking", "implementation_gap | launch-blocking")
            .replace("record variance | closed", "fix code | open")
            .replace("open_launch_blockers: 0", "open_launch_blockers: 1"),
            encoding="utf-8",
        )
        open_blocker_errors = workflowctl.validate_launch_readiness(open_blocker)
        if not any("launch-blocking" in error for error in open_blocker_errors):
            errors.append(f"{WORKFLOWCTL}: open launch-blocking finding was not rejected")
        if not any("open_launch_blockers" in error for error in open_blocker_errors):
            errors.append(f"{WORKFLOWCTL}: nonzero open_launch_blockers was not rejected")

        template_like = root / "template-like"
        template_like.mkdir()
        write_launch_state(template_like)
        template_body = (TEMPLATES / "launch-readiness-review.md").read_text(encoding="utf-8")
        template_body = (
            template_body
            .replace("<GitHub PR URL, PR ID, or equivalent diff artifact>", "diff-artifact-001")
            .replace("<base branch or commit>", "main")
            .replace("<head branch or commit>", "codex/example-head-uid")
            .replace("<PR compare URL, local diff command, or review artifact path>", "diff-artifact-001/files")
        )
        (template_like / "mock-acceptance.md").write_text("mock acceptance evidence\n", encoding="utf-8")
        (template_like / "launch-readiness-review.md").write_text(template_body, encoding="utf-8")
        template_errors = workflowctl.validate_launch_readiness(template_like)
        if not any("placeholder" in error or "pass/N/A/accepted-risk" in error for error in template_errors):
            errors.append(f"{WORKFLOWCTL}: template-like incomplete launch readiness review was not rejected")

        missing_execution = root / "missing-execution"
        missing_execution.mkdir()
        (missing_execution / "task-dag.yaml").write_text("schema_version: 1\ntasks: {}\nedges: []\n", encoding="utf-8")
        (missing_execution / "mock-acceptance.md").write_text("mock acceptance evidence\n", encoding="utf-8")
        (missing_execution / "launch-readiness-review.md").write_text(valid_review, encoding="utf-8")
        missing_execution_errors = workflowctl.validate_launch_readiness(missing_execution)
        if not any("execution_receipt is missing" in error for error in missing_execution_errors):
            errors.append(f"{WORKFLOWCTL}: missing execution receipt was not rejected")

        missing_mock_receipt = root / "missing-mock-receipt"
        missing_mock_receipt.mkdir()
        write_launch_state(missing_mock_receipt, with_mock_receipt=False)
        (missing_mock_receipt / "mock-acceptance.md").write_text("mock acceptance evidence\n", encoding="utf-8")
        (missing_mock_receipt / "launch-readiness-review.md").write_text(valid_review, encoding="utf-8")
        missing_mock_errors = workflowctl.validate_launch_readiness(missing_mock_receipt)
        if not any("stage_receipts.mock-acceptance" in error for error in missing_mock_errors):
            errors.append(f"{WORKFLOWCTL}: missing mock-acceptance receipt was not rejected")

        undecided = root / "undecided"
        undecided.mkdir()
        write_launch_state(undecided)
        (undecided / "mock-acceptance.md").write_text("mock acceptance evidence\n", encoding="utf-8")
        (undecided / "launch-readiness-review.md").write_text(
            valid_review.replace(
                "allowed_implementation_variance | non-blocking | PR and requirement evidence | main | record variance | closed",
                "launch_decision_required | launch-blocking | PR exposes release choice | human owner | ask user to decide | closed",
            ),
            encoding="utf-8",
        )
        undecided_errors = workflowctl.validate_launch_readiness(undecided)
        if not any("lacks human launch decision evidence" in error for error in undecided_errors):
            errors.append(f"{WORKFLOWCTL}: launch_decision_required without human decision evidence was not rejected")

        decided = root / "decided"
        decided.mkdir()
        write_launch_state(decided)
        (decided / "mock-acceptance.md").write_text("mock acceptance evidence\n", encoding="utf-8")
        (decided / "launch-readiness-review.md").write_text(
            valid_review.replace(
                "allowed_implementation_variance | non-blocking | PR and requirement evidence | main | record variance | closed",
                "launch_decision_required | launch-blocking | user-confirmed accepted-risk for release scope | human owner | launch decision recorded; scope adjusted | accepted-risk",
            ),
            encoding="utf-8",
        )
        decided_errors = workflowctl.validate_launch_readiness(decided)
        if decided_errors:
            errors.append(f"{WORKFLOWCTL}: launch_decision_required with human decision evidence should pass, got {decided_errors}")
    return errors


def validate_stage_construction_protocol() -> list[str]:
    errors: list[str] = []
    required_paths = [
        STAGE_CONSTRUCTION_CONTRACT,
        STANDARD_WORKFLOW_STATE_TEMPLATE,
        CONTEXTPACK_WORKFLOW_STATE_TEMPLATE,
        WORKFLOW_RUNTIME_MANIFEST,
        WORKFLOW_DEFECT_TEMPLATE,
        WORKFLOW_EVENT_TEMPLATE,
        WORKFLOW_STATE_MACHINE_TEMPLATE,
        STAGE_CONSTRUCTION_REFERENCE,
        CONTEXTPACK_RULE_REFERENCE,
        CONTEXTPACK_AGENT_METADATA,
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"{path}: required stage construction resource is missing")
    if errors:
        return errors

    contextpack_body = read(CONTEXTPACK_WORKFLOW)
    methodology_body = read_with_direct_skill_references(METHODOLOGY / "SKILL.md")
    workflowctl_body = read(WORKFLOWCTL)
    for phrase in [
        "prepare-stage",
        "reopen-stage",
        "validate-obligation",
        "validate-stage-construction",
        "stage-construction-v1",
        "late_detection_defect",
    ]:
        if phrase not in contextpack_body:
            errors.append(f"{CONTEXTPACK_WORKFLOW}: missing stage construction phrase {phrase}")
    for phrase in ["stage-construction-protocol.md", "stage-construction-contracts.yaml", "prepare-stage"]:
        if phrase not in methodology_body:
            errors.append(f"{METHODOLOGY / 'SKILL.md'}: missing stage construction wiring {phrase}")
    for command in [
        "prepare-stage",
        "preflight-stage-closures",
        "validate-obligation",
        "validate-stage-construction",
        "migrate-workflow-runtime",
        "mark-stage-na",
        "record-late-defect",
        "promote-late-defect",
    ]:
        if f'add_parser("{command}")' not in workflowctl_body:
            errors.append(f"{WORKFLOWCTL}: CLI command {command} is not registered")
    if len(contextpack_body.splitlines()) > 500:
        errors.append(f"{CONTEXTPACK_WORKFLOW}: must remain under 500 lines for progressive disclosure")
    if len(read(METHODOLOGY / "SKILL.md").splitlines()) > 500:
        errors.append(f"{METHODOLOGY / 'SKILL.md'}: must remain under 500 lines for progressive disclosure")
    metadata = read(CONTEXTPACK_AGENT_METADATA)
    if "$automq-ai-dev-workflow-contextpack" not in metadata:
        errors.append(f"{CONTEXTPACK_AGENT_METADATA}: default_prompt must mention the skill explicitly")

    workflow_spec = importlib.util.spec_from_file_location("workflowctl_stage_construction_smoke", WORKFLOWCTL)
    if workflow_spec is None or workflow_spec.loader is None:
        return errors + [f"{WORKFLOWCTL}: could not load stage construction smoke module"]
    workflowctl = importlib.util.module_from_spec(workflow_spec)
    workflow_spec.loader.exec_module(workflowctl)
    for stage in ["contract", "verification", "task-planning", "pre-execution"]:
        if "migration" not in workflowctl.STAGE_PREREQUISITES.get(stage, []):
            errors.append(f"{WORKFLOWCTL}: {stage} prerequisite graph omits migration")
    full_template_state = workflowctl.as_dict(workflowctl.load_yaml(CONTEXTPACK_WORKFLOW_STATE_TEMPLATE))
    if workflowctl.effective_stage_prerequisites(full_template_state, "mock-acceptance") != ["execution"]:
        errors.append(f"{WORKFLOWCTL}: mock-acceptance no longer requires execution")
    if workflowctl.effective_stage_prerequisites(full_template_state, "product-acceptance") != ["execution", "mock-acceptance"]:
        errors.append(f"{WORKFLOWCTL}: product-acceptance prerequisite chain is incomplete")
    artifact_spec = importlib.util.spec_from_file_location("validate_artifacts_contextpack_smoke", ARTIFACT_VALIDATOR)
    if artifact_spec is None or artifact_spec.loader is None:
        return errors + [f"{ARTIFACT_VALIDATOR}: could not load contextpack isolation smoke module"]
    artifact_validator = importlib.util.module_from_spec(artifact_spec)
    artifact_spec.loader.exec_module(artifact_validator)
    for name, pattern in [
        ("workflowctl mechanism", workflowctl.MECHANISM_UNRESOLVED_RE),
        ("artifact mechanism", artifact_validator.MECHANISM_UNRESOLVED_RE),
        ("artifact external research", artifact_validator.EXTERNAL_RESEARCH_BLOCKED_RE),
        ("artifact decision surface", artifact_validator.OPEN_DECISION_SURFACE_RE),
    ]:
        if pattern.search("status UNKNOWN implementation BLOCKED"):
            errors.append(f"{name}: legal uppercase enum or implementation prose is treated as unresolved")
        if not pattern.search("status unknown blocked TBD TODO 待确认 未知 未决"):
            errors.append(f"{name}: real unresolved markers are no longer blocked")
    try:
        contract = workflowctl.load_stage_construction_contract()
    except Exception as exc:
        return errors + [f"{STAGE_CONSTRUCTION_CONTRACT}: failed to load: {exc}"]
    runtime_manifest = workflowctl.load_workflow_runtime_manifest()
    runtime_components = workflowctl.as_dict(runtime_manifest.get("components"))
    required_owner_components = {
        "product_requirement_design_skill",
        "aip_template_skill",
        "requirement_readiness_review_skill",
        "new_feature_design_skill",
        "code_archaeology_sdd_skill",
        "migration_diff_analysis_skill",
        "frontend_contract_design_skill",
        "cross_module_contract_sdd_skill",
        "verification_matrix_skill",
        "atomic_task_planning_skill",
        "atomic_execution_sdd_skill",
        "mock_acceptance_gate_skill",
        "mock_acceptance_validator",
        "product_acceptance_review_skill",
        "runtime_resource_bundle",
    }
    missing_owner_components = sorted(required_owner_components - set(runtime_components))
    if missing_owner_components:
        errors.append(f"{WORKFLOW_RUNTIME_MANIFEST}: unpinned stage owner skills: {missing_owner_components}")
    if workflowctl.as_dict(runtime_components.get("validate_skill_suite")).get("behavior_affecting") is not False:
        errors.append(f"{WORKFLOW_RUNTIME_MANIFEST}: validate_skill_suite must be pinned but non-behavior-affecting")
    resource_bundle = workflowctl.as_dict(runtime_components.get("runtime_resource_bundle"))
    if resource_bundle and workflowctl.runtime_component_actual_hash(METHODOLOGY, resource_bundle) != resource_bundle.get("sha256"):
        errors.append(f"{WORKFLOW_RUNTIME_MANIFEST}: runtime resource bundle digest is stale")
    runtime_pin = {
        "version": runtime_manifest.get("runtime_version"),
        "manifest_sha256": workflowctl.sha256_file(WORKFLOW_RUNTIME_MANIFEST),
        "component_hashes": workflowctl.runtime_component_hashes(runtime_manifest),
    }
    if workflowctl.WORKFLOW_STATE_MACHINE != artifact_validator.WORKFLOW_STATE_MACHINE:
        errors.append("workflowctl.py and validate_artifacts.py loaded different workflow state machines")
    if workflowctl.STAGE_PREREQUISITES != artifact_validator.STAGE_PREREQUISITES:
        errors.append("workflowctl.py and validate_artifacts.py loaded different prerequisite graphs")
    if workflowctl.VALID_STAGE_STATUS != artifact_validator.VALID_STAGE_STATUS:
        errors.append("workflowctl.py and validate_artifacts.py loaded different stage statuses")
    if workflowctl.STAGE_RECEIPT_REQUIRED_ARTIFACTS != artifact_validator.STAGE_RECEIPT_REQUIRED_ARTIFACTS:
        errors.append("workflowctl.py and validate_artifacts.py loaded different receipt artifact maps")
    if workflowctl.PLAN_SNAPSHOT_STAGES != artifact_validator.PLAN_SNAPSHOT_STAGES:
        errors.append("workflowctl.py and validate_artifacts.py loaded different plan snapshot stages")
    if workflowctl.REVIEW_POLICY != artifact_validator.REVIEW_POLICY:
        errors.append("workflowctl.py and validate_artifacts.py loaded different review policies")

    markdown_table_fixture = """| Name | Value |
|---|---|
| ordinary-row | surface contract words are data, not a header |
| escaped-pipe | left \\| right |
| inline-code-pipe | `left | right` |
"""
    for validator_name, tables, dicts in [
        (
            str(WORKFLOWCTL),
            workflowctl.markdown_tables(markdown_table_fixture),
            workflowctl.markdown_table_dicts(markdown_table_fixture),
        ),
        (
            str(ARTIFACT_VALIDATOR),
            artifact_validator.markdown_tables(markdown_table_fixture),
            artifact_validator.table_dicts(markdown_table_fixture),
        ),
    ]:
        if len(tables) != 1 or tables[0][0] != ["Name", "Value"]:
            errors.append(f"{validator_name}: Markdown table header detection regressed: {tables}")
        if len(dicts) != 3 or any(set(row) != {"Name", "Value"} for row in dicts):
            errors.append(f"{validator_name}: data containing surface/contract was reinterpreted as a header: {dicts}")
        if dicts and dicts[1].get("Value") != r"left \| right":
            errors.append(f"{validator_name}: escaped pipe changed Markdown table cell boundaries: {dicts}")
        if dicts and dicts[2].get("Value") != "left | right":
            errors.append(f"{validator_name}: inline-code pipe changed Markdown table cell boundaries: {dicts}")

    with tempfile.TemporaryDirectory(prefix="automq-reference-digest-") as digest_tmp:
        digest_path = Path(digest_tmp) / "semantic.md"
        digest_path.write_text(
            """# Semantic Objects

## Product Decisions

| ID | Decision |
|---|---|
| PDEC-001 | keep the selected owner behavior |
| PDEC-002 | keep the independent lifecycle behavior |

## Unrelated Notes

initial note
""",
            encoding="utf-8",
        )
        section_digest, _ = workflowctl.artifact_reference_digest(
            digest_path, "semantic.md#Product Decisions"
        )
        object_digest, _ = workflowctl.artifact_reference_digest(
            digest_path, "semantic.md#Product Decisions", "PDEC-001"
        )
        digest_path.write_text(
            digest_path.read_text(encoding="utf-8").replace("initial note", "changed unrelated note"),
            encoding="utf-8",
        )
        if workflowctl.artifact_reference_digest(digest_path, "semantic.md#Product Decisions")[0] != section_digest:
            errors.append(f"{WORKFLOWCTL}: unrelated section edit invalidated a section-scoped obligation receipt")
        digest_path.write_text(
            digest_path.read_text(encoding="utf-8").replace(
                "keep the independent lifecycle behavior", "change only the independent lifecycle behavior"
            ),
            encoding="utf-8",
        )
        if workflowctl.artifact_reference_digest(
            digest_path, "semantic.md#Product Decisions", "PDEC-001"
        )[0] != object_digest:
            errors.append(f"{WORKFLOWCTL}: another object row invalidated an object-scoped obligation receipt")
        digest_path.write_text(
            digest_path.read_text(encoding="utf-8").replace(
                "keep the selected owner behavior", "change the selected owner behavior"
            ),
            encoding="utf-8",
        )
        if workflowctl.artifact_reference_digest(
            digest_path, "semantic.md#Product Decisions", "PDEC-001"
        )[0] == object_digest:
            errors.append(f"{WORKFLOWCTL}: selected object edit did not invalidate its obligation receipt")
        try:
            workflowctl.artifact_reference_digest(digest_path, "semantic.md#Missing Section")
        except ValueError:
            pass
        else:
            errors.append(f"{WORKFLOWCTL}: missing Markdown section silently fell back to whole-file hashing")
    state_machine = workflowctl.WORKFLOW_STATE_MACHINE
    expected_review_stages = {
        "source-intake", "prd", "aip", "readiness", "design", "archaeology", "migration",
        "frontend-contract", "contract", "verification", "task-planning", "pre-execution",
        "mock-acceptance", "product-acceptance",
    }
    if set(workflowctl.REVIEW_POLICY) != expected_review_stages:
        errors.append(
            f"workflow state machine: review_policy stage coverage drifted: {sorted(workflowctl.REVIEW_POLICY)}"
        )
    for review_stage, policy in workflowctl.REVIEW_POLICY.items():
        required = policy.get("required")
        values = [policy.get("initial_min"), policy.get("repair_min"), policy.get("max")]
        if not isinstance(required, bool) or any(not isinstance(value, int) for value in values):
            errors.append(f"workflow state machine: {review_stage} review policy has invalid field types")
            continue
        initial_min, repair_min, maximum = values
        if not (0 <= repair_min <= initial_min <= maximum):
            errors.append(f"workflow state machine: {review_stage} review policy bounds are inconsistent")
        if required is False and any(values):
            errors.append(f"workflow state machine: optional review stage {review_stage} must have zero reviewer bounds")
        if required is True and repair_min < 1:
            errors.append(f"workflow state machine: required review stage {review_stage} must allow at least one repair reviewer")
    stage_order = [str(item) for item in workflowctl.as_list(state_machine.get("stage_order"))]
    construction_stages = {
        str(item) for item in workflowctl.as_list(state_machine.get("construction_stages"))
    }
    runtime_prerequisites = {
        str(item) for item in workflowctl.as_list(state_machine.get("runtime_prerequisites"))
    }
    order_index = {stage: index for index, stage in enumerate(stage_order)}
    for stage, prerequisites in workflowctl.STAGE_PREREQUISITES.items():
        if stage not in order_index:
            errors.append(f"workflow state machine: prerequisite owner {stage} is absent from stage_order")
            continue
        for prerequisite in prerequisites:
            if prerequisite not in order_index and prerequisite not in runtime_prerequisites:
                errors.append(f"workflow state machine: {stage} has unknown prerequisite {prerequisite}")
            elif prerequisite in order_index and order_index[prerequisite] >= order_index[stage]:
                errors.append(f"workflow state machine: {stage} depends on non-earlier stage {prerequisite}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(stage: str) -> None:
        if stage in visiting:
            errors.append(f"workflow state machine: prerequisite cycle reaches {stage}")
            return
        if stage in visited:
            return
        visiting.add(stage)
        for prerequisite in workflowctl.STAGE_PREREQUISITES.get(stage, []):
            if prerequisite in workflowctl.STAGE_PREREQUISITES:
                visit(prerequisite)
        visiting.remove(stage)
        visited.add(stage)

    for stage in workflowctl.STAGE_PREREQUISITES:
        visit(stage)
    if not construction_stages.issubset(order_index):
        errors.append("workflow state machine: a construction stage is unreachable from stage_order")
    for stage, prerequisites in workflowctl.STAGE_PREREQUISITES.items():
        for prerequisite in prerequisites:
            if stage in construction_stages | {"execution"} and stage not in workflowctl.downstream_stage_closure(
                full_template_state, prerequisite
            ):
                errors.append(
                    f"workflow state machine: downstream invalidation misses edge {prerequisite} -> {stage}"
                )
    receipt_kinds = workflowctl.as_dict(state_machine.get("receipt_kinds"))
    reopenable = {
        str(item)
        for item in workflowctl.as_list(workflowctl.as_dict(state_machine.get("recovery")).get("reopenable_statuses"))
    }
    for stage in receipt_kinds:
        if stage in construction_stages and not {"passed", "not_applicable"}.intersection(reopenable):
            errors.append(f"workflow state machine: terminal receipt stage {stage} has no recovery status")
    if re.search(r"prerequisite_map\s*=\s*\{\s*['\"]prd['\"]", read(ARTIFACT_VALIDATOR)):
        errors.append(f"{ARTIFACT_VALIDATOR}: duplicate hardcoded prerequisite map remains")
    for module, mutable_paths in [
        (workflowctl, workflowctl.EXECUTION_MUTABLE_RELATIVE),
        (artifact_validator, artifact_validator.EXECUTION_MUTABLE_RELATIVE),
    ]:
        if "workflow-events.yaml" not in mutable_paths:
            errors.append(f"{Path(module.__file__)}: workflow-events.yaml must remain execution mutable")
    rules = workflowctl.as_dict(contract.get("rules"))
    stages = workflowctl.as_dict(contract.get("stages"))
    standard_state = workflowctl.as_dict(workflowctl.load_yaml(STANDARD_WORKFLOW_STATE_TEMPLATE))
    contextpack_state = workflowctl.as_dict(workflowctl.load_yaml(CONTEXTPACK_WORKFLOW_STATE_TEMPLATE))
    if standard_state.get("schema_version") != 1 or workflowctl.stage_construction_enabled_doc(standard_state):
        errors.append(f"{STANDARD_WORKFLOW_STATE_TEMPLATE}: standard schema v1 template must not enable stage construction")
    if contextpack_state.get("schema_version") != 2 or not workflowctl.stage_construction_enabled_doc(contextpack_state):
        errors.append(f"{CONTEXTPACK_WORKFLOW_STATE_TEMPLATE}: contextpack schema v2 template must enable stage construction")
    obsolete_template = METHODOLOGY / "templates" / "stage-obligations.yaml"
    if obsolete_template.exists():
        errors.append(f"{obsolete_template}: obsolete hand-authored ledger template must be removed")
    for stage, raw in stages.items():
        for rule_id in workflowctl.as_list(workflowctl.as_dict(raw).get("always")):
            if str(rule_id) not in rules:
                errors.append(f"{STAGE_CONSTRUCTION_CONTRACT}: stage {stage} references unknown rule {rule_id}")
    for trigger_name, raw in workflowctl.as_dict(contract.get("triggers")).items():
        for stage, rule_ids in workflowctl.as_dict(workflowctl.as_dict(raw).get("rules_by_stage")).items():
            if stage not in stages:
                errors.append(f"{STAGE_CONSTRUCTION_CONTRACT}: trigger {trigger_name} references unknown stage {stage}")
            for rule_id in workflowctl.as_list(rule_ids):
                if str(rule_id) not in rules:
                    errors.append(
                        f"{STAGE_CONSTRUCTION_CONTRACT}: trigger {trigger_name}/{stage} references unknown rule {rule_id}"
                    )

    with tempfile.TemporaryDirectory(prefix="automq-stage-construction-") as tmp:
        repo = Path(tmp)
        subprocess.run(["git", "init", str(repo)], check=True, text=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "stage-construction@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Stage Construction Smoke"], check=True)
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "seed.txt"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "test: seed"], check=True, text=True, capture_output=True)
        branch = subprocess.run(
            ["git", "-C", str(repo), "branch", "--show-current"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        change_dir = repo / "specs" / "changes" / "stage-construction-smoke"
        change_dir.mkdir(parents=True)
        workdir_body = f"""# Workflow Workdir Identity

| Item | Value |
|---|---|
| Worktree path | {repo} |
| Change dir absolute path | {change_dir} |
| Change id | stage-construction-smoke |
| Branch name | {branch} |
| Base branch | {branch} |
| Base commit | {head} |
| Base source mode | pinned-commit |
| Remote ref | none |
| Remote OID | none |
| Remote fetched at | none |
| Fetch command evidence | pinned local test commit |
| Git top level | {repo} |

## Resume Verification

| Check | Result |
|---|---|
| Initial | matched |
"""
        (change_dir / "workflow-workdir.md").write_text(workdir_body, encoding="utf-8")
        (change_dir / "external-capability-research.md").write_text(
            "# AIP-owned external research\n", encoding="utf-8"
        )
        if "external-capability-research.md" in workflowctl.artifact_digest_map(change_dir, "source-intake"):
            errors.append(f"{WORKFLOWCTL}: source-intake receipt still seals AIP-owned external research")
        workflowctl.write_yaml(
            change_dir / "workflow-state.yaml",
            {
                "schema_version": 2,
                "workflow": {
                    "skill": "automq-ai-dev-workflow-contextpack",
                    "profile": "full",
                    "stage_construction_protocol": "stage-construction-v1",
                    "runtime": runtime_pin,
                    "change_id": "stage-construction-smoke",
                    "change_dir_abs": change_dir.as_posix(),
                    "worktree_path": repo.as_posix(),
                    "branch_name": branch,
                    "base_commit": head,
                },
                "stage_status": {"source-intake": "not_started", "execution": "not_started"},
                "stage_receipts": {},
            },
        )
        if workflowctl.prepare_stage(change_dir, "source-intake") != 0:
            errors.append(f"{WORKFLOWCTL}: prepare-stage source-intake smoke failed")
            return errors
        ledger_path, pack_path = workflowctl.stage_construction_paths(change_dir, "source-intake")
        if not ledger_path.exists() or not pack_path.exists():
            errors.append(f"{WORKFLOWCTL}: prepare-stage did not generate ledger and execution pack")
            return errors
        pack_body = read(pack_path)
        for required_pack_text in ["Stage Construction Inputs", "Embedded Completeness Excerpt", "Required Artifacts"]:
            if required_pack_text not in pack_body:
                errors.append(f"{WORKFLOWCTL}: execution pack omitted construction guidance {required_pack_text}")
        initial_errors = workflowctl.validate_stage_construction(
            workflowctl.WorkflowModel(change_dir), "source-intake"
        )
        if not any("status must be closed/not_applicable" in error for error in initial_errors):
            errors.append(f"{WORKFLOWCTL}: open obligations were not rejected: {initial_errors}")

        (change_dir / "source-intake-ledger.md").write_text(
            """# Source Intake Ledger

## Source Inventory

| Source ID | Type | Path / URL / origin | Provided by | Read status | Read method | Used for | If unread, reason | Follow-up |
|---|---|---|---|---|---|---|---|---|
| SRC-001 | requirement | user request | user | read | conversation | PRD REQ-001 and AUTH-001 | none | none |

## Source To Semantic Object Map

| Source ID | Extracted object | Extracted semantics | Target artifact | Status | Gap / conflict |
|---|---|---|---|---|---|
| SRC-001 | REQ-001 AUTH-001 | update an existing deployment; AI may make implementation decisions only | proposal.md | mapped | none |

## Source Conflict Matrix

| Conflict | Source A | Source B | Conflicting semantics | Decision required | Resolution DEC | Status |
|---|---|---|---|---|---|---|
| none | SRC-001 | none | no conflict | no | AUTH-001 | locked |
""",
            encoding="utf-8",
        )
        ledger = workflowctl.as_dict(workflowctl.load_yaml(ledger_path))
        for row in workflowctl.as_list(ledger.get("obligations")):
            item = workflowctl.as_dict(row)
            closure = workflowctl.default_stage_closure()
            artifacts = (
                ["workflow-workdir.md", "source-intake-ledger.md"]
                if item.get("rule_id") == "SC-WORKDIR-001"
                else ["source-intake-ledger.md"]
            )
            closure.update(
                {
                    "canonical_artifacts": artifacts,
                    "evidence": [f"{artifacts[0]}#smoke provides concrete stage evidence"],
                    "semantic_objects": ["SRC-001: source and authorization semantics"],
                    "decisions": ["AUTH-001: source-intake authorization scope is explicitly recorded"],
                    "downstream_consumers": ["prd: consumes SRC-001 and authorization scope"],
                }
            )
            item["closure"] = closure
        workflowctl.write_yaml(ledger_path, ledger)
        for row in workflowctl.as_list(ledger.get("obligations")):
            obligation_id = str(workflowctl.as_dict(row).get("obligation_id"))
            if workflowctl.validate_obligation(change_dir, "source-intake", obligation_id) != 0:
                errors.append(f"{WORKFLOWCTL}: validate-obligation smoke failed for {obligation_id}")
        closed_errors = workflowctl.validate_stage_construction(
            workflowctl.WorkflowModel(change_dir), "source-intake"
        )
        if closed_errors:
            errors.append(f"{WORKFLOWCTL}: closed stage construction should pass, got {closed_errors}")

        clean_ledger_text = read(ledger_path)
        clean_pack_text = read(pack_path)
        for field, replacement in [
            ("obligation_id", "TAMPERED-OBLIGATION-ID"),
            ("required_closure", []),
            ("allow_not_applicable", True),
            ("trigger", {"kind": "signal", "signals": ["tampered"], "evidence": [], "digest": "tampered"}),
        ]:
            tampered = workflowctl.as_dict(workflowctl.load_yaml(ledger_path))
            first_row = workflowctl.as_dict(workflowctl.as_list(tampered.get("obligations"))[0])
            first_row[field] = replacement
            workflowctl.write_yaml(ledger_path, tampered)
            tamper_errors = workflowctl.validate_stage_construction(
                workflowctl.WorkflowModel(change_dir), "source-intake"
            )
            if not any(
                f"metadata {field} differs" in error
                or (field == "obligation_id" and "stale/fake obligation IDs" in error)
                for error in tamper_errors
            ):
                errors.append(f"{WORKFLOWCTL}: tampered ledger {field} was not rejected: {tamper_errors}")
            ledger_path.write_text(clean_ledger_text, encoding="utf-8")
        pack_path.write_text(clean_pack_text + "tampered execution instruction\n", encoding="utf-8")
        pack_errors = workflowctl.validate_stage_construction(
            workflowctl.WorkflowModel(change_dir), "source-intake"
        )
        if not any("execution pack differs from deterministic ledger rendering" in error for error in pack_errors):
            errors.append(f"{WORKFLOWCTL}: modified execution pack was not rejected: {pack_errors}")
        pack_path.write_text(clean_pack_text, encoding="utf-8")

        if workflowctl.prepare_stage(change_dir, "source-intake") != 0:
            errors.append(f"{WORKFLOWCTL}: idempotent prepare-stage source-intake failed")
        else:
            reloaded = workflowctl.as_dict(workflowctl.load_yaml(ledger_path))
            statuses = {
                str(workflowctl.as_dict(row).get("status"))
                for row in workflowctl.as_list(reloaded.get("obligations"))
            }
            if statuses != {"closed"}:
                errors.append(f"{WORKFLOWCTL}: idempotent prepare-stage did not preserve fresh row receipts: {statuses}")

        source_hashes = workflowctl.artifact_digest_map(change_dir, "source-intake")
        for rel in [
            "stage-construction/source-intake-obligations.yaml",
            "stage-construction/source-intake-execution-pack.md",
        ]:
            if rel not in source_hashes:
                errors.append(f"{WORKFLOWCTL}: stage receipt digest does not seal {rel}")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", "test: prepare source intake stage"],
            check=True,
            text=True,
            capture_output=True,
        )
        if workflowctl.issue_stage_receipt(change_dir, "source-intake") != 0:
            errors.append(f"{WORKFLOWCTL}: pass-stage integration smoke failed for source-intake")
            return errors
        workflow_doc = workflowctl.as_dict(workflowctl.load_yaml(change_dir / "workflow-state.yaml"))
        source_receipt = workflowctl.as_dict(
            workflowctl.as_dict(workflow_doc.get("stage_receipts")).get("source-intake")
        )
        if source_receipt.get("status") != "passed":
            errors.append(f"{WORKFLOWCTL}: pass-stage did not write a passed source-intake receipt")
        forged_state = workflowctl.as_dict(workflowctl.load_yaml(change_dir / "workflow-state.yaml"))
        workflowctl.as_dict(workflowctl.as_dict(forged_state.get("stage_receipts")).get("source-intake"))["receipt_hash"] = "FORGED"
        workflowctl.write_yaml(change_dir / "workflow-state.yaml", forged_state)
        forged_errors = workflowctl.validate_stage_receipts(workflowctl.WorkflowModel(change_dir), "source-intake")
        if not any("forged or stale" in error for error in forged_errors):
            errors.append(f"{WORKFLOWCTL}: forged stage receipt hash was accepted: {forged_errors}")
        workflowctl.write_yaml(change_dir / "workflow-state.yaml", workflow_doc)

        passed_snapshots = {
            path: path.read_bytes()
            for path in [ledger_path, pack_path, change_dir / "workflow-state.yaml"]
        }
        if workflowctl.prepare_stage(change_dir, "source-intake") != 0:
            errors.append(f"{WORKFLOWCTL}: prepare-stage should no-op for a fresh passed stage")
        for path, before in passed_snapshots.items():
            if path.read_bytes() != before:
                errors.append(f"{WORKFLOWCTL}: fresh passed-stage prepare modified {path.name}")

        if workflowctl.prepare_stage(change_dir, "prd") != 0:
            errors.append(f"{WORKFLOWCTL}: prepare-stage prd trigger smoke failed")
        else:
            prd_ledger_path, _ = workflowctl.stage_construction_paths(change_dir, "prd")
            prd_ledger = workflowctl.as_dict(workflowctl.load_yaml(prd_ledger_path))
            prd_rule_ids = {
                str(workflowctl.as_dict(row).get("rule_id"))
                for row in workflowctl.as_list(prd_ledger.get("obligations"))
            }
            if "SC-OPERATION-MUTABILITY-001" not in prd_rule_ids:
                errors.append(
                    f"{WORKFLOWCTL}: update existing deployment signal did not produce SC-OPERATION-MUTABILITY-001"
                )
            if "SC-PRD-GLOBAL-COMPAT-001" not in prd_rule_ids:
                errors.append(
                    f"{WORKFLOWCTL}: PRD construction omitted SC-PRD-GLOBAL-COMPAT-001"
                )
            if "SC-VERSION-BRANCH-ALIGNMENT-001" not in prd_rule_ids:
                errors.append(
                    f"{WORKFLOWCTL}: PRD construction omitted SC-VERSION-BRANCH-ALIGNMENT-001"
                )
            missing_alignment_errors = artifact_validator.validate_version_alignment(
                change_dir,
                "control-plane branch/version signal without its alignment artifact",
                "",
            )
            if not any("missing Version Branch Alignment Matrix" in error for error in missing_alignment_errors):
                errors.append(
                    f"{ARTIFACT_VALIDATOR}: SC-VERSION-BRANCH-ALIGNMENT-001 regression did not reject a missing matrix: "
                    f"{missing_alignment_errors}"
                )
            prd_compat_errors = workflowctl.validate_prd_construction_compatibility(change_dir)
            if not any(
                "PRD missing Current Product/Code Understanding" in error
                or "missing Artifact Rubric Scorecard" in error
                for error in prd_compat_errors
            ):
                errors.append(
                    f"{WORKFLOWCTL}: SC-PRD-GLOBAL-COMPAT-001 did not reject incomplete PRD artifacts: {prd_compat_errors}"
                )
            for row in workflowctl.as_list(prd_ledger.get("obligations")):
                item = workflowctl.as_dict(row)
                if item.get("rule_id") in {"SC-PRD-SEMANTICS-001", "SC-OPERATION-MUTABILITY-001"}:
                    required = set(workflowctl.as_list(item.get("required_closure")))
                    if required & {"contracts", "verifications"}:
                        errors.append(
                            f"{WORKFLOWCTL}: PRD obligation requires future-stage closure fields: {sorted(required)}"
                        )

            preflight_ledger = copy.deepcopy(prd_ledger)
            preflight_rows = [workflowctl.as_dict(row) for row in workflowctl.as_list(preflight_ledger.get("obligations"))]
            if len(preflight_rows) >= 2:
                expected_rules = []
                for row in preflight_rows[:2]:
                    row["status"] = "open"
                    row["closure"] = {}
                    row.pop("validation", None)
                    expected_rules.append(str(row.get("rule_id")))
                workflowctl.write_yaml(prd_ledger_path, preflight_ledger)
                preflight_stderr = io.StringIO()
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(preflight_stderr):
                    preflight_result = workflowctl.preflight_stage_closures(change_dir, "prd")
                preflight_output = preflight_stderr.getvalue()
                if preflight_result == 0 or not all(item in preflight_output for item in expected_rules):
                    errors.append(
                        f"{WORKFLOWCTL}: closure preflight did not aggregate row failures: {preflight_output}"
                    )
                workflowctl.write_yaml(prd_ledger_path, prd_ledger)

            workflow_before_stale = read(change_dir / "workflow-state.yaml")
            stale_workflow = workflowctl.as_dict(workflowctl.load_yaml(change_dir / "workflow-state.yaml"))
            stale_receipts = workflowctl.as_dict(stale_workflow.get("stage_receipts"))
            workflowctl.as_dict(stale_receipts.get("source-intake"))["receipt_hash"] = "stale-upstream-receipt"
            workflowctl.write_yaml(change_dir / "workflow-state.yaml", stale_workflow)
            context_errors, _, _ = workflowctl.stage_construction_context(
                workflowctl.WorkflowModel(change_dir), "prd"
            )
            first_prd_obligation = str(
                workflowctl.as_dict(workflowctl.as_list(prd_ledger.get("obligations"))[0]).get("obligation_id")
            )
            if not any("upstream stage receipt hashes changed" in error for error in context_errors):
                errors.append(f"{WORKFLOWCTL}: stale upstream receipt was not detected: {context_errors}")
            if quiet_call(workflowctl.validate_obligation, change_dir, "prd", first_prd_obligation) == 0:
                errors.append(f"{WORKFLOWCTL}: validate-obligation accepted stale upstream receipt context")
            (change_dir / "workflow-state.yaml").write_text(workflow_before_stale, encoding="utf-8")

            source_before_trigger_change = read(change_dir / "source-intake-ledger.md")
            (change_dir / "source-intake-ledger.md").write_text(
                source_before_trigger_change.replace("update an existing deployment", "replace an existing deployment"),
                encoding="utf-8",
            )
            trigger_errors, _, _ = workflowctl.stage_construction_context(
                workflowctl.WorkflowModel(change_dir), "prd"
            )
            if not any("applicability trigger profile changed" in error for error in trigger_errors):
                errors.append(f"{WORKFLOWCTL}: stale trigger/input fingerprint was not detected: {trigger_errors}")
            if quiet_call(workflowctl.validate_obligation, change_dir, "prd", first_prd_obligation) == 0:
                errors.append(f"{WORKFLOWCTL}: validate-obligation accepted stale trigger context")
            (change_dir / "source-intake-ledger.md").write_text(source_before_trigger_change, encoding="utf-8")

        source_before_stale = read(change_dir / "source-intake-ledger.md")
        with (change_dir / "source-intake-ledger.md").open("a", encoding="utf-8") as handle:
            handle.write("changed after stage receipt\n")
        stale_errors = workflowctl.validate_stage_construction(
            workflowctl.WorkflowModel(change_dir), "source-intake"
        )
        if not any("canonical artifact edit" in error for error in stale_errors):
            errors.append(f"{WORKFLOWCTL}: stale row receipt after artifact edit was not rejected: {stale_errors}")
        stale_passed_snapshots = {
            path: path.read_bytes()
            for path in [ledger_path, pack_path, change_dir / "workflow-state.yaml"]
        }
        if quiet_call(workflowctl.prepare_stage, change_dir, "source-intake") == 0:
            errors.append(f"{WORKFLOWCTL}: prepare-stage rewrote a stale passed stage without backflow")
        for path, before in stale_passed_snapshots.items():
            if path.read_bytes() != before:
                errors.append(f"{WORKFLOWCTL}: rejected stale passed-stage prepare modified {path.name}")
        (change_dir / "backflow.yaml").write_text(
            "schema_version: 1\ntriggers:\n  BF-REOPEN-001:\n    status: open\n    resolution_stage: source-intake\n    invalidates:\n      artifacts:\n        - source-intake-ledger.md\n",
            encoding="utf-8",
        )
        reopen_state = workflowctl.as_dict(workflowctl.load_yaml(change_dir / "workflow-state.yaml"))
        reopen_status = workflowctl.as_dict(reopen_state.get("stage_status"))
        reopen_status.update({"prd": "passed", "execution": "in_progress"})
        workflowctl.as_dict(reopen_state.get("stage_receipts"))["prd"] = {
            "stage": "prd", "status": "passed", "receipt_hash": "downstream-receipt"
        }
        reopen_state["execution_receipt"] = {"status": "started", "receipt_hash": "execution-receipt"}
        reopen_state["task_receipts"] = {"T001": {"status": "admitted", "receipt_hash": "task-receipt"}}
        workflowctl.write_yaml(change_dir / "workflow-state.yaml", reopen_state)
        if workflowctl.apply_backflow(change_dir, "BF-REOPEN-001") != 0:
            errors.append(f"{WORKFLOWCTL}: reopen smoke could not apply its backflow trigger")
        elif workflowctl.reopen_stage(
            change_dir,
            "source-intake",
            "BF-REOPEN-001",
            "source receipt is stale after canonical artifact repair",
        ) != 0:
            errors.append(f"{WORKFLOWCTL}: stale passed stage could not be reopened")
        else:
            reopened = workflowctl.as_dict(workflowctl.load_yaml(change_dir / "workflow-state.yaml"))
            reopened_status = workflowctl.as_dict(reopened.get("stage_status"))
            if reopened_status.get("source-intake") != "pending-rewrite" or reopened_status.get("prd") != "pending-rewrite":
                errors.append(f"{WORKFLOWCTL}: reopen-stage did not transitively invalidate downstream stages: {reopened_status}")
            if workflowctl.as_dict(reopened.get("stage_receipts")):
                errors.append(f"{WORKFLOWCTL}: reopen-stage left invalidated stage receipts")
            if reopened_status.get("execution") != "not_started" or reopened.get("execution_receipt") or workflowctl.as_dict(reopened.get("task_receipts")):
                errors.append(f"{WORKFLOWCTL}: reopen-stage did not reset execution receipts")
            audit = workflowctl.as_dict(workflowctl.as_list(reopened.get("stage_reopens"))[-1])
            if audit.get("audit_hash") != workflowctl.canonical_audit_hash(audit):
                errors.append(f"{WORKFLOWCTL}: reopen-stage audit hash is invalid")
            if workflowctl.validate_stage_reopens(workflowctl.WorkflowModel(change_dir)):
                errors.append(f"{WORKFLOWCTL}: valid reopen-stage audit failed validation")
        (change_dir / "source-intake-ledger.md").write_text(source_before_stale, encoding="utf-8")

        negative_dir = repo / "specs" / "changes" / "negative-trigger-smoke"
        negative_dir.mkdir(parents=True)
        (negative_dir / "spec.md").write_text(
            "本需求不涉及迁移，也不涉及更新、编辑或重建。 buildformfactor remains an internal token.\n",
            encoding="utf-8",
        )
        negative_prd_rules, _, _ = workflowctl.stage_construction_scan(negative_dir, "prd", contract)
        if "SC-OPERATION-MUTABILITY-001" in negative_prd_rules:
            errors.append(f"{WORKFLOWCTL}: negative operation wording falsely triggered mutability obligation")
        negative_contract_rules, _, _ = workflowctl.stage_construction_scan(negative_dir, "contract", contract)
        if "SC-FRONTEND-ACTION-001" in negative_contract_rules:
            errors.append(f"{WORKFLOWCTL}: substring inside buildformfactor falsely triggered frontend obligation")
        (negative_dir / "spec.md").write_text(
            "本需求不涉及迁移。It must update an existing deployment after creation.\n",
            encoding="utf-8",
        )
        mixed_rules, _, _ = workflowctl.stage_construction_scan(negative_dir, "prd", contract)
        if "SC-OPERATION-MUTABILITY-001" not in mixed_rules:
            errors.append(f"{WORKFLOWCTL}: a separate negative sentence suppressed a positive mutability signal")

        context_dir = repo / "specs" / "changes" / "missing-context-smoke"
        context_dir.mkdir(parents=True)
        context_workdir = workdir_body.replace(change_dir.as_posix(), context_dir.as_posix()).replace(
            "stage-construction-smoke", "missing-context-smoke"
        )
        (context_dir / "workflow-workdir.md").write_text(context_workdir, encoding="utf-8")
        context_state = {
            "schema_version": 2,
            "workflow": {
                "skill": "automq-ai-dev-workflow-contextpack",
                "profile": "full",
                "stage_construction_protocol": "stage-construction-v1",
                "runtime": runtime_pin,
                "change_id": "missing-context-smoke",
                "change_dir_abs": context_dir.as_posix(),
                "worktree_path": repo.as_posix(),
                "branch_name": branch,
                "base_commit": head,
            },
            "stage_status": {
                "source-intake": "not_applicable",
                "prd": "not_applicable",
                "aip": "not_applicable",
                "readiness": "not_applicable",
                "design": "not_started",
            },
            "stage_receipts": {},
        }
        workflowctl.write_yaml(context_dir / "workflow-state.yaml", context_state)
        if quiet_call(workflowctl.prepare_stage, context_dir, "design") == 0:
            errors.append(f"{WORKFLOWCTL}: prepare-stage accepted raw not_applicable prerequisites without N/A receipts")

        strong_context_dir = repo / "specs" / "changes" / "strong-context-smoke"
        strong_context_dir.mkdir(parents=True)
        strong_workdir = workdir_body.replace(change_dir.as_posix(), strong_context_dir.as_posix()).replace(
            "stage-construction-smoke", "strong-context-smoke"
        )
        (strong_context_dir / "workflow-workdir.md").write_text(strong_workdir, encoding="utf-8")
        (strong_context_dir / "proposal.md").write_text("REQ-001 locks a concrete product semantic for downstream design.\n", encoding="utf-8")
        strong_state = {
            "schema_version": 2,
            "workflow": {
                "skill": "automq-ai-dev-workflow-contextpack",
                "profile": "execution-only",
                "stage_construction_protocol": "stage-construction-v1",
                "runtime": runtime_pin,
                "change_id": "strong-context-smoke",
                "change_dir_abs": strong_context_dir.as_posix(),
                "worktree_path": repo.as_posix(),
                "branch_name": branch,
                "base_commit": head,
            },
            "stage_status": {"design": "not_started", "execution": "not_started"},
            "stage_receipts": {},
            "stage_na_receipts": {},
        }
        workflowctl.write_yaml(strong_context_dir / "workflow-state.yaml", strong_state)
        if workflowctl.validate_aip_artifacts(workflowctl.WorkflowModel(strong_context_dir), "design"):
            errors.append(f"{WORKFLOWCTL}: execution-only profile incorrectly required AIP artifacts")

        execution_only_receipt_dir = repo / "specs" / "changes" / "execution-only-receipt-smoke"
        execution_only_receipt_dir.mkdir(parents=True)
        execution_only_state = {
            "schema_version": 2,
            "workflow": {
                "skill": "automq-ai-dev-workflow-contextpack",
                "profile": "execution-only",
                "stage_construction_protocol": "stage-construction-v1",
                "runtime": runtime_pin,
            },
            "stage_status": {"task-planning": "passed", "execution": "not_started"},
            "stage_receipts": {},
            "stage_na_receipts": {},
        }
        workflowctl.write_yaml(execution_only_receipt_dir / "workflow-state.yaml", execution_only_state)
        for rel in workflowctl.stage_required_artifact_rels(execution_only_receipt_dir, "task-planning"):
            path = execution_only_receipt_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(f"receipt smoke artifact: {rel}\n", encoding="utf-8")
        task_planning_receipt = {
            "stage": "task-planning",
            "status": "passed",
            "issued_at": "2026-07-15T00:00:00+00:00",
            "validator": "workflowctl.py",
            "command": f"python3 {WORKFLOWCTL} validate task-planning {execution_only_receipt_dir}",
            "artifact_hashes": workflowctl.artifact_digest_map(execution_only_receipt_dir, "task-planning"),
            "upstream_stage_receipt_hashes": {},
        }
        task_planning_receipt["receipt_hash"] = workflowctl.canonical_receipt_hash(task_planning_receipt)
        execution_only_state["stage_receipts"] = {"task-planning": task_planning_receipt}
        workflowctl.write_yaml(execution_only_receipt_dir / "workflow-state.yaml", execution_only_state)
        execution_only_receipt_errors = workflowctl.validate_stage_receipts(
            workflowctl.WorkflowModel(execution_only_receipt_dir), "pre-execution"
        )
        if execution_only_receipt_errors:
            errors.append(
                f"{WORKFLOWCTL}: execution-only task-planning receipt with no upstream stages could not enter pre-execution: "
                f"{execution_only_receipt_errors}"
            )
        routing_errors = artifact_validator.validate_change(execution_only_receipt_dir, "task-planning")
        forbidden_upstream_diagnostics = [
            error
            for error in routing_errors
            if any(
                marker in error
                for marker in [
                    "source-intake-ledger.md",
                    "missing Product Requirement",
                    "AIP is required",
                    "mechanism-design-model.md",
                    "decision-surface-discovery.md",
                    "Semantic Consumption Matrix",
                ]
            )
        ]
        if forbidden_upstream_diagnostics:
            errors.append(
                f"{ARTIFACT_VALIDATOR}: execution-only routing still ran upstream completeness gates: "
                f"{forbidden_upstream_diagnostics[:5]}"
            )
        workflow_routing_errors = workflowctl.validate(execution_only_receipt_dir, "task-planning")
        workflow_forbidden = [
            error
            for error in workflow_routing_errors
            if any(
                marker in error
                for marker in [
                    "mechanism-design-model.md",
                    "Decision Surface",
                    "stateful-behavior",
                    "runtime-materialization-parity",
                    "runtime-test-topology",
                ]
            )
        ]
        if workflow_forbidden:
            errors.append(
                f"{WORKFLOWCTL}: execution-only routing still ran upstream signal validators: {workflow_forbidden[:5]}"
            )

        reseal_chain_dir = repo / "specs" / "changes" / "reseal-na-chain-smoke"
        reseal_chain_dir.mkdir(parents=True)
        chain_status = {
            "design": "passed",
            "archaeology": "passed",
            "migration": "not_applicable",
            "frontend-contract": "not_applicable",
            "contract": "passed",
            "verification": "passed",
            "task-planning": "passed",
            "execution": "in_progress",
        }
        chain_state = {
            "schema_version": 2,
            "workflow": {
                "skill": "automq-ai-dev-workflow-contextpack",
                "profile": "full",
                "stage_construction_protocol": "stage-construction-v1",
                "runtime": runtime_pin,
            },
            "stage_status": chain_status,
            "stage_receipts": {},
            "stage_na_receipts": {},
        }
        workflowctl.write_yaml(reseal_chain_dir / "workflow-state.yaml", chain_state)
        for chain_stage in workflowctl.execution_reseal_stage_order(chain_state):
            status = chain_status[chain_stage]
            receipt = {
                "stage": chain_stage,
                "status": status,
                "issued_at": "2026-07-15T00:00:00+00:00",
                "validator": "workflowctl.py",
                "command": f"workflowctl {'mark-stage-na' if status == 'not_applicable' else 'validate'} {chain_stage}",
                "upstream_stage_receipt_hashes": workflowctl.stage_upstream_receipt_hashes(chain_state, chain_stage),
            }
            receipt["receipt_hash"] = workflowctl.canonical_receipt_hash(receipt)
            target = chain_state["stage_na_receipts"] if status == "not_applicable" else chain_state["stage_receipts"]
            target[chain_stage] = receipt
        workflowctl.refresh_stage_receipt_chain(
            reseal_chain_dir,
            chain_state,
            workflowctl.execution_reseal_stage_order(chain_state),
            "BF-CHAIN-001: refresh mixed passed and N/A chain",
            "2026-07-15T01:00:00+00:00",
        )
        for chain_stage in workflowctl.execution_reseal_stage_order(chain_state):
            status = chain_status[chain_stage]
            source = chain_state["stage_na_receipts"] if status == "not_applicable" else chain_state["stage_receipts"]
            receipt = workflowctl.as_dict(source.get(chain_stage))
            if receipt.get("receipt_hash") != workflowctl.canonical_receipt_hash(receipt):
                errors.append(f"{WORKFLOWCTL}: mixed reseal chain wrote invalid hash for {chain_stage}")
            if workflowctl.as_dict(receipt.get("upstream_stage_receipt_hashes")) != workflowctl.stage_upstream_receipt_hashes(chain_state, chain_stage):
                errors.append(f"{WORKFLOWCTL}: mixed reseal chain left stale upstream hashes for {chain_stage}")

        completion_dir = repo / "specs" / "changes" / "execution-completion-smoke"
        completion_dir.mkdir(parents=True)
        workflowctl.write_yaml(
            completion_dir / "task-dag.yaml",
            {"schema_version": 1, "tasks": {"T001": {"title": "completion smoke"}}, "edges": []},
        )
        completion_state = {
            "schema_version": 2,
            "workflow": {
                "skill": "automq-ai-dev-workflow-contextpack",
                "profile": "execution-only",
                "stage_construction_protocol": "stage-construction-v1",
                "runtime": runtime_pin,
            },
            "stage_status": {"task-planning": "passed", "execution": "in_progress"},
            "stage_receipts": {"task-planning": {"receipt_hash": "task-planning-smoke"}},
            "stage_na_receipts": {},
            "task_receipts": {},
        }
        workflowctl.write_yaml(completion_dir / "workflow-state.yaml", completion_state)
        forged_minimal = {"task": "T001", "status": "passed"}
        forged_minimal["receipt_hash"] = workflowctl.canonical_receipt_hash(forged_minimal)
        completion_state["task_receipts"] = {"T001": forged_minimal}
        workflowctl.write_yaml(completion_dir / "workflow-state.yaml", completion_state)
        if workflowctl.task_is_passed(workflowctl.WorkflowModel(completion_dir), "T001"):
            errors.append(f"{WORKFLOWCTL}: minimal self-hashed task receipt bypassed required execution evidence")
        workflowctl.write_yaml(
            completion_dir / "task-verification-log.yaml",
            {"entries": [{"task": "T001", "status": "passed", "result": "completion smoke passed"}]},
        )
        completion_verification_entries = workflowctl.verification_entries_for_task(
            workflowctl.verification_log_payload(completion_dir), "T001"
        )
        semantic_entry = {"task": "T001", "verdict": "pass"}
        workflowctl.write_yaml(completion_dir / "task-semantic-review.yaml", {"reviews": [semantic_entry]})
        execution_receipt = {
            "status": "started",
            "issued_at": "2026-07-15T00:00:00+00:00",
            "validator": "workflowctl.py",
            "command": "workflowctl begin-execution",
            "artifact_hashes": workflowctl.artifact_digest_map(completion_dir, "pre-execution"),
            "sealed_artifact_hashes": workflowctl.sealed_artifact_digest_map(completion_dir),
            "stage_receipt_hashes": {"task-planning": "task-planning-smoke"},
            "git_state": workflowctl.current_git_state(completion_dir),
        }
        execution_receipt["receipt_hash"] = workflowctl.canonical_receipt_hash(execution_receipt)
        task_receipt = {
            "task": "T001",
            "status": "passed",
            "passed_at": "2026-07-15T00:01:00+00:00",
            "validator": "workflowctl.py",
            "command": "workflowctl pass-task T001",
            "diff_validated": True,
            "verification_log": "task-verification-log.yaml",
            "verification_log_hash": workflowctl.stable_json_digest(completion_verification_entries),
            "semantic_review_log": "task-semantic-review.yaml",
            "semantic_review_hash": workflowctl.stable_json_digest(semantic_entry),
            "semantic_review_verdict": "pass",
            "git_state": workflowctl.current_git_state(completion_dir),
            "passed_git_commit": workflowctl.current_git_state(completion_dir).get("head"),
            "passed_changed_path_hashes": {},
            "passed_declared_output_hashes": {},
            "execution_receipt_hash": execution_receipt["receipt_hash"],
        }
        task_receipt["receipt_hash"] = workflowctl.canonical_receipt_hash(task_receipt)
        completion_state["execution_receipt"] = execution_receipt
        completion_state["task_receipts"] = {"T001": task_receipt}
        workflowctl.write_yaml(completion_dir / "workflow-state.yaml", completion_state)
        if workflowctl.execution_completion_errors(workflowctl.WorkflowModel(completion_dir)):
            errors.append(f"{WORKFLOWCTL}: completed Atomic Issues could not satisfy the mock-acceptance execution prerequisite")
        mutated_verification = workflowctl.as_dict(workflowctl.load_yaml(completion_dir / "task-verification-log.yaml"))
        workflowctl.as_dict(workflowctl.as_list(mutated_verification.get("entries"))[0])["result"] = "rewritten after pass-task"
        workflowctl.write_yaml(completion_dir / "task-verification-log.yaml", mutated_verification)
        if workflowctl.task_is_passed(workflowctl.WorkflowModel(completion_dir), "T001"):
            errors.append(f"{WORKFLOWCTL}: task receipt did not become stale after task-local verification evidence changed")
        workflowctl.write_yaml(
            completion_dir / "task-verification-log.yaml",
            {"entries": [{"task": "T001", "status": "passed", "result": "completion smoke passed"}]},
        )
        unrelated_append = workflowctl.as_dict(workflowctl.load_yaml(completion_dir / "task-verification-log.yaml"))
        workflowctl.as_list(unrelated_append.get("entries")).append(
            {"task": "T002", "status": "passed", "predecessor": "T001", "result": "second task passed"}
        )
        workflowctl.write_yaml(completion_dir / "task-verification-log.yaml", unrelated_append)
        if not workflowctl.task_is_passed(workflowctl.WorkflowModel(completion_dir), "T001"):
            errors.append(f"{WORKFLOWCTL}: unrelated task log entry referencing T001 invalidated T001 receipt")
        failed_current = copy.deepcopy(unrelated_append)
        workflowctl.as_dict(workflowctl.as_list(failed_current.get("entries"))[0]).update(
            {"status": "failed", "result": "current task failed"}
        )
        workflowctl.write_yaml(completion_dir / "task-verification-log.yaml", failed_current)
        if workflowctl.verification_log_has_task(completion_dir, "T001"):
            errors.append(f"{WORKFLOWCTL}: passing evidence from another task masked a failed current task entry")
        workflowctl.write_yaml(
            completion_dir / "task-verification-log.yaml",
            {"entries": [{"task": "T001", "status": "passed", "result": "completion smoke passed"}]},
        )
        mock_upstream = workflowctl.stage_upstream_receipt_hashes(completion_state, "mock-acceptance")
        if mock_upstream != {"execution": execution_receipt["receipt_hash"]}:
            errors.append(f"{WORKFLOWCTL}: mock-acceptance receipt does not pin the execution receipt hash")
        if workflowctl.mark_stage_na(
            completion_dir,
            "mock-acceptance",
            "AUTH-001",
            "this execution path has no external adapter or mock acceptance surface",
            "users observe the completed backend behavior without a mock-only runtime",
            "task receipts and negative adapter scan prove mock acceptance is not applicable",
        ) != 0:
            errors.append(f"{WORKFLOWCTL}: mock-acceptance N/A was blocked by the non-terminal execution status")
        else:
            completion_after_na = workflowctl.as_dict(workflowctl.load_yaml(completion_dir / "workflow-state.yaml"))
            mock_na_receipt = workflowctl.as_dict(
                workflowctl.as_dict(completion_after_na.get("stage_na_receipts")).get("mock-acceptance")
            )
            if workflowctl.as_dict(mock_na_receipt.get("upstream_stage_receipt_hashes")) != {
                "execution": execution_receipt["receipt_hash"]
            }:
                errors.append(f"{WORKFLOWCTL}: mock-acceptance N/A receipt did not pin execution")

        acceptance_invalidation_state = {
            "stage_status": {"mock-acceptance": "passed", "product-acceptance": "not_applicable"},
            "stage_receipts": {"mock-acceptance": {"receipt_hash": "mock"}},
            "stage_na_receipts": {"product-acceptance": {"receipt_hash": "product-na"}},
        }
        invalidated_acceptance = workflowctl.invalidate_acceptance_receipts(acceptance_invalidation_state)
        if invalidated_acceptance != ["mock-acceptance", "product-acceptance"]:
            errors.append(f"{WORKFLOWCTL}: execution reseal did not invalidate both acceptance stages")
        if acceptance_invalidation_state["stage_receipts"] or acceptance_invalidation_state["stage_na_receipts"]:
            errors.append(f"{WORKFLOWCTL}: execution reseal left stale acceptance receipts")

        acceptance_reopen_dir = repo / "specs" / "changes" / "acceptance-reopen-smoke"
        acceptance_reopen_dir.mkdir(parents=True)
        workflowctl.write_yaml(
            acceptance_reopen_dir / "workflow-state.yaml",
            {
                "schema_version": 2,
                "workflow": {
                    "skill": "automq-ai-dev-workflow-contextpack",
                    "profile": "execution-only",
                    "stage_construction_protocol": "stage-construction-v1",
                    "runtime": runtime_pin,
                },
                "stage_status": {
                    "task-planning": "passed",
                    "execution": "in_progress",
                    "mock-acceptance": "passed",
                    "product-acceptance": "passed",
                },
                "stage_receipts": {
                    "mock-acceptance": {"stage": "mock-acceptance", "status": "passed", "receipt_hash": "mock"},
                    "product-acceptance": {"stage": "product-acceptance", "status": "passed", "receipt_hash": "product"},
                },
                "stage_na_receipts": {},
                "execution_receipt": {"status": "started", "receipt_hash": "execution"},
                "task_receipts": {"T001": {"status": "passed", "receipt_hash": "task"}},
            },
        )
        (acceptance_reopen_dir / "backflow.yaml").write_text(
            "schema_version: 1\ntriggers:\n  BF-ACCEPT-001:\n    status: open\n    resolution_stage: mock-acceptance\n    invalidates:\n      artifacts:\n        - mock-acceptance.md\n",
            encoding="utf-8",
        )
        if workflowctl.reopen_stage(
            acceptance_reopen_dir,
            "mock-acceptance",
            "BF-ACCEPT-001",
            "mock acceptance evidence must be regenerated after fixture repair",
        ) != 0:
            errors.append(f"{WORKFLOWCTL}: mock-acceptance could not be reopened independently")
        else:
            acceptance_reopened = workflowctl.as_dict(
                workflowctl.load_yaml(acceptance_reopen_dir / "workflow-state.yaml")
            )
            acceptance_status = workflowctl.as_dict(acceptance_reopened.get("stage_status"))
            if acceptance_status.get("execution") != "in_progress" or not acceptance_reopened.get("execution_receipt"):
                errors.append(f"{WORKFLOWCTL}: acceptance-only reopen incorrectly reset execution")
            if acceptance_status.get("mock-acceptance") != "pending-rewrite" or acceptance_status.get("product-acceptance") != "pending-rewrite":
                errors.append(f"{WORKFLOWCTL}: acceptance-only reopen did not invalidate downstream acceptance")
            if not workflowctl.as_dict(acceptance_reopened.get("task_receipts")):
                errors.append(f"{WORKFLOWCTL}: acceptance-only reopen incorrectly removed task receipts")
        (context_dir / "design-context-pack.md").write_text(
            "# Design Context Pack\n\n" + "Locked PRD and AIP context with source, decisions, modules, risks, and verification inputs. " * 3,
            encoding="utf-8",
        )
        (strong_context_dir / "design-context-pack.md").write_text(
            "# Design Context Pack\n\n" + "filler text " * 30,
            encoding="utf-8",
        )
        if quiet_call(workflowctl.prepare_stage, strong_context_dir, "design") == 0:
            errors.append(f"{WORKFLOWCTL}: filler context pack passed structured preflight")
        excerpt = "REQ-001 fixes the product behavior and is copied here for the design module boundary decision."
        excerpt_hash = __import__("hashlib").sha256(excerpt.encode("utf-8")).hexdigest()
        source_hash = workflowctl.sha256_file(strong_context_dir / "proposal.md")
        (strong_context_dir / "design-context-pack.md").write_text(
            f"""# Design Context Pack

## Source Artifacts

| Path | SHA-256 |
|---|---|
| proposal.md | {source_hash} |

## Consumed Semantic Objects

- REQ-001

## Copied Semantic Excerpt

{excerpt}
Semantic digest: {excerpt_hash}

## Downstream Coverage Targets

- design module boundary and contract preparation

## Unresolved Required Rows

none
""",
            encoding="utf-8",
        )
        if workflowctl.prepare_stage(strong_context_dir, "design") != 0:
            errors.append(f"{WORKFLOWCTL}: structured context pack was rejected")

        if quiet_call(
            workflowctl.mark_stage_na,
            strong_context_dir,
            "source-intake",
            "AUTH-001",
            "source intake cannot be skipped",
            "user input remains mandatory",
            "source trace must be verified",
        ) == 0:
            errors.append(f"{WORKFLOWCTL}: forbidden whole-stage N/A was accepted")
        if workflowctl.mark_stage_na(
            strong_context_dir,
            "migration",
            "MIG-DEC-001",
            "no existing persisted semantics require migration",
            "users observe no data or API migration behavior",
            "negative migration scan proves no migration path",
        ) != 0:
            errors.append(f"{WORKFLOWCTL}: eligible whole-stage N/A was rejected")
        else:
            na_errors = workflowctl.validate_stage_receipts(workflowctl.WorkflowModel(strong_context_dir), "migration")
            if na_errors:
                errors.append(f"{WORKFLOWCTL}: valid N/A receipt failed validation: {na_errors}")
            valid_na_text = read(strong_context_dir / "workflow-state.yaml")
            stale_na_state = workflowctl.as_dict(workflowctl.load_yaml(strong_context_dir / "workflow-state.yaml"))
            stale_na = workflowctl.as_dict(workflowctl.as_dict(stale_na_state.get("stage_na_receipts")).get("migration"))
            stale_na["upstream_stage_receipt_hashes"] = {"prd": "stale-upstream"}
            stale_na["receipt_hash"] = workflowctl.canonical_receipt_hash(stale_na)
            workflowctl.write_yaml(strong_context_dir / "workflow-state.yaml", stale_na_state)
            stale_na_errors = workflowctl.validate_stage_receipts(workflowctl.WorkflowModel(strong_context_dir), "migration")
            if not any("upstream_stage_receipt_hashes is stale" in error for error in stale_na_errors):
                errors.append(f"{WORKFLOWCTL}: stale N/A upstream receipt chain was accepted")
            if workflowctl.mark_stage_na(
                strong_context_dir,
                "migration",
                "MIG-DEC-001",
                "no existing persisted semantics require migration",
                "users observe no data or API migration behavior",
                "negative migration scan proves no migration path",
            ) != 0:
                errors.append(f"{WORKFLOWCTL}: mark-stage-na could not repair a stale current N/A receipt")
            elif workflowctl.validate_stage_receipts(workflowctl.WorkflowModel(strong_context_dir), "migration"):
                errors.append(f"{WORKFLOWCTL}: repaired N/A receipt still failed validation")
            (strong_context_dir / "workflow-state.yaml").write_text(valid_na_text, encoding="utf-8")

        (strong_context_dir / "spec.md").write_text(
            """# Specification

RMM-999 and DS-999-OBL-IGNORE are outside typed carrier headings.

## Managed Resource Ownership Matrix

RMM-001 and RMM-002 are separate managed resources.

## Operation Mutability Matrix

DS-001-OBL-UPDATE and DS-002-OBL-RESIZE are separate operations.
""",
            encoding="utf-8",
        )
        managed_ids = workflowctl.stage_rule_object_ids(strong_context_dir, "SC-MANAGED-RESOURCE-001", contract)
        mutability_ids = workflowctl.stage_rule_object_ids(strong_context_dir, "SC-OPERATION-MUTABILITY-001", contract)
        if managed_ids != ["RMM-001", "RMM-002"] or mutability_ids != ["DS-001-OBL-UPDATE", "DS-002-OBL-RESIZE"]:
            errors.append(f"{WORKFLOWCTL}: typed obligation decomposition failed: {managed_ids}, {mutability_ids}")
        (strong_context_dir / "task-dag.yaml").write_text(
            "# RMM-777 and DS-777-OBL-STALE are stale downstream examples\ntasks: []\n",
            encoding="utf-8",
        )
        if workflowctl.stage_rule_object_ids(strong_context_dir, "SC-MANAGED-RESOURCE-001", contract) != managed_ids:
            errors.append(f"{WORKFLOWCTL}: downstream task-dag content contaminated PRD typed obligations")

        if workflowctl.mark_stage_na(
            strong_context_dir,
            "frontend-contract",
            "UI-DEC-001",
            "the requirement exposes no user interface or browser action",
            "users observe only backend API behavior with no frontend route",
            "negative route and component scan proves no frontend action exists",
        ) != 0:
            errors.append(f"{WORKFLOWCTL}: backend-only workflow could not mark frontend-contract N/A")
        contract_excerpt = "REQ-001 fixes backend ownership and contract behavior without introducing any frontend user action."
        contract_excerpt_hash = __import__("hashlib").sha256(contract_excerpt.encode("utf-8")).hexdigest()
        (strong_context_dir / "contract-context-pack.md").write_text(
            f"""# Contract Context Pack

## Source Artifacts

| Path | SHA-256 |
|---|---|
| proposal.md | {source_hash} |

## Consumed Semantic Objects

- REQ-001

## Copied Semantic Excerpt

{contract_excerpt}
Semantic digest: {contract_excerpt_hash}

## Downstream Coverage Targets

- backend provider and consumer contract ownership

## Unresolved Required Rows

none
""",
            encoding="utf-8",
        )
        (strong_context_dir / "contracts.yaml").write_text(
            "schema_version: 1\ncontracts: {}\n# C-001-OBL-001 is a template example only\n",
            encoding="utf-8",
        )
        if workflowctl.stage_rule_object_ids(strong_context_dir, "SC-CONTRACT-SEMANTICS-001", contract):
            errors.append(f"{WORKFLOWCTL}: YAML comments created a fake typed contract obligation")
        if workflowctl.prepare_stage(strong_context_dir, "contract") != 0:
            errors.append(f"{WORKFLOWCTL}: backend-only contract bootstrap was blocked before typed IDs existed")
        else:
            contract_ledger_path, _ = workflowctl.stage_construction_paths(strong_context_dir, "contract")
            bootstrap_ledger = workflowctl.as_dict(workflowctl.load_yaml(contract_ledger_path))
            bootstrap_rows = [workflowctl.as_dict(item) for item in workflowctl.as_list(bootstrap_ledger.get("obligations"))]
            bootstrap_semantic_rows = [
                row for row in bootstrap_rows if row.get("rule_id") == "SC-CONTRACT-SEMANTICS-001"
            ]
            if len(bootstrap_semantic_rows) != 1 or bootstrap_semantic_rows[0].get("object_id"):
                errors.append(f"{WORKFLOWCTL}: bootstrap contract ledger unexpectedly invented typed IDs")
            bootstrap_errors = workflowctl.validate_stage_construction(
                workflowctl.WorkflowModel(strong_context_dir), "contract"
            )
            if not any("bootstrap obligation" in error for error in bootstrap_errors):
                errors.append(f"{WORKFLOWCTL}: final contract gate accepted a coarse typed bootstrap")
            workflowctl.write_yaml(
                strong_context_dir / "contracts.yaml",
                {
                    "schema_version": 1,
                    "contracts": {
                        "C-001": {
                            "executable_obligations": [{"id": "C-001-OBL-001"}],
                        }
                    },
                },
            )
            if workflowctl.prepare_stage(strong_context_dir, "contract") != 0:
                errors.append(f"{WORKFLOWCTL}: contract bootstrap could not expand after typed IDs were created")
            else:
                expanded = workflowctl.as_dict(workflowctl.load_yaml(contract_ledger_path))
                expanded_rows = [workflowctl.as_dict(item) for item in workflowctl.as_list(expanded.get("obligations"))]
                semantic_rows = [row for row in expanded_rows if row.get("rule_id") == "SC-CONTRACT-SEMANTICS-001"]
                owner_rows = [row for row in expanded_rows if row.get("rule_id") == "SC-CONTRACT-OWNER-001"]
                if [row.get("object_id") for row in semantic_rows] != ["C-001-OBL-001"]:
                    errors.append(f"{WORKFLOWCTL}: typed contract semantics did not expand deterministically: {semantic_rows}")
                if len(owner_rows) != 1 or owner_rows[0].get("object_id"):
                    errors.append(f"{WORKFLOWCTL}: backend contract owner rule still depends on frontend UI-ACT IDs")

        runtime_bad = workflowctl.as_dict(workflowctl.load_yaml(strong_context_dir / "workflow-state.yaml"))
        workflowctl.write_yaml(
            strong_context_dir / "backflow.yaml",
            {
                "schema_version": 1,
                "triggers": {
                    "BF-LEGACY-OPEN": {
                        "status": "open",
                        "earliest_missing_stage": "prd",
                        "required_backflow": "Repair the PRD projection before continuing.",
                        "invalidates": {"artifacts": [], "decisions": [], "contracts": [], "verifications": [], "tasks": []},
                    },
                    "BF-LEGACY-RESOLVED": {
                        "status": "resolved",
                        "required_backflow": "Return to aip and repair the mechanism model.",
                        "resolved_at": "2026-07-16T00:00:00+00:00",
                        "resolution": "The historical AIP repair was completed and reviewed.",
                        "invalidates": {"artifacts": [], "decisions": [], "contracts": [], "verifications": [], "tasks": []},
                    },
                },
            },
        )
        if workflowctl.infer_historical_backflow_resolution_stage(
            {"required_backflow": "Repair all affected artifacts before continuing."},
            workflowctl.as_dict(workflowctl.load_yaml(strong_context_dir / "workflow-state.yaml")),
            "BF-NONEXISTENT",
        ):
            errors.append(f"{WORKFLOWCTL}: pseudo-stage all was inferred as a backflow resolution stage")
        runtime_bad_pin = workflowctl.as_dict(workflowctl.as_dict(runtime_bad.get("workflow")).get("runtime"))
        runtime_bad_pin["version"] = "forged-runtime"
        workflowctl.as_dict(runtime_bad_pin.get("component_hashes"))["atomic_issue_template"] = "forged-component"
        if not workflowctl.validate_workflow_runtime(runtime_bad):
            errors.append(f"{WORKFLOWCTL}: runtime mismatch was accepted")
        workflowctl.write_yaml(strong_context_dir / "workflow-state.yaml", runtime_bad)
        if workflowctl.migrate_workflow_runtime(strong_context_dir, "execution-only") != 0:
            errors.append(f"{WORKFLOWCTL}: explicit runtime migration failed")
        else:
            migrated_state = workflowctl.as_dict(workflowctl.load_yaml(strong_context_dir / "workflow-state.yaml"))
            if workflowctl.validate_workflow_runtime(migrated_state):
                errors.append(f"{WORKFLOWCTL}: migrated runtime pin is invalid")
            migrated_status = workflowctl.as_dict(migrated_state.get("stage_status"))
            migrations = [workflowctl.as_dict(item) for item in workflowctl.as_list(migrated_state.get("runtime_migrations"))]
            latest_migration = migrations[-1] if migrations else {}
            migrated_backflows = workflowctl.as_dict(
                workflowctl.as_dict(workflowctl.load_yaml(strong_context_dir / "backflow.yaml")).get("triggers")
            )
            open_trigger = workflowctl.as_dict(migrated_backflows.get("BF-LEGACY-OPEN"))
            resolved_trigger = workflowctl.as_dict(migrated_backflows.get("BF-LEGACY-RESOLVED"))
            migration_reopens = [
                workflowctl.as_dict(item)
                for item in workflowctl.as_list(migrated_state.get("stage_reopens"))
                if workflowctl.text(workflowctl.as_dict(item).get("backflow_id")) == "BF-LEGACY-OPEN"
            ]
            if open_trigger.get("resolution_stage") != "prd" or len(migration_reopens) != 1:
                errors.append(f"{WORKFLOWCTL}: migration did not adopt historical open backflow atomically")
            elif migration_reopens[0].get("execution_reset") is not False:
                errors.append(f"{WORKFLOWCTL}: migration reopen falsely claimed an execution reset")
            if resolved_trigger.get("resolution_stage") != "aip" or not workflowctl.as_dict(
                resolved_trigger.get("legacy_resolution_evidence")
            ):
                errors.append(f"{WORKFLOWCTL}: migration did not seal historical resolved backflow evidence")
            if workflowctl.validate_stage_reopens(workflowctl.WorkflowModel(strong_context_dir)):
                errors.append(f"{WORKFLOWCTL}: runtime-migration reopen audit failed canonical validation")
            if workflowctl.validate_backflow(workflowctl.WorkflowModel(strong_context_dir)):
                errors.append(f"{WORKFLOWCTL}: migrated historical backflows failed canonical validation")
            forged_legacy = copy.deepcopy(migrated_backflows)
            evidence = workflowctl.as_dict(
                workflowctl.as_dict(forged_legacy.get("BF-LEGACY-RESOLVED")).get("legacy_resolution_evidence")
            )
            evidence["adopted_at"] = "2099-01-01T00:00:00+00:00"
            evidence["evidence_hash"] = workflowctl.stable_json_digest(
                {key: value for key, value in evidence.items() if key != "evidence_hash"}
            )
            workflowctl.write_yaml(
                strong_context_dir / "backflow.yaml",
                {"schema_version": 1, "triggers": forged_legacy},
            )
            if not any(
                "lacks a valid runtime migration audit" in error
                for error in workflowctl.validate_backflow(workflowctl.WorkflowModel(strong_context_dir))
            ):
                errors.append(f"{WORKFLOWCTL}: self-hashed legacy evidence bypassed migration provenance")
            workflowctl.write_yaml(
                strong_context_dir / "backflow.yaml",
                {"schema_version": 1, "triggers": migrated_backflows},
            )
            if (
                migrated_status.get("migration") != "not_applicable"
                or migrated_status.get("execution") != "not_started"
                or "task-planning" not in workflowctl.as_list(latest_migration.get("invalidated_stages"))
                or latest_migration.get("full_invalidation") is not False
            ):
                errors.append(
                    f"{WORKFLOWCTL}: component-scoped migration invalidated the wrong stages: "
                    f"{migrated_status}, {latest_migration}"
                )
            scoped_state = workflowctl.as_dict(workflowctl.load_yaml(strong_context_dir / "workflow-state.yaml"))
            scoped_runtime = workflowctl.as_dict(workflowctl.as_dict(scoped_state.get("workflow")).get("runtime"))
            scoped_runtime["version"] = "contextpack-runtime-2026.07.14.2"
            scoped_runtime["manifest_sha256"] = "old-manifest"
            workflowctl.as_dict(scoped_runtime.get("component_hashes"))["stage_construction_contract"] = "old-contract"
            scoped_status = workflowctl.as_dict(scoped_state.get("stage_status"))
            scoped_status["task-planning"] = "in_progress"
            scoped_status["execution"] = "in_progress"
            workflowctl.write_yaml(strong_context_dir / "workflow-state.yaml", scoped_state)
            workflowctl.write_yaml(
                strong_context_dir / "workflow-defects.yaml",
                {
                    "schema_version": 1,
                    "runtime_version": "contextpack-runtime-2026.07.14.2",
                    "defects": {
                        "LD-001": {
                            "gate": "task-planning-final",
                            "failure_signature": "task packet rule discovered too late",
                            "detected_stage": "task-planning",
                            "should_have_caught_stage": "task-planning",
                            "classification": "missing-machine-rule",
                            "affected_rule": "SC-TASK-PACKET-001",
                            "affected_artifact": "atomic-issue-packets.yaml",
                            "repair_action": "add task packet construction rule",
                            "promotion_target": "stage-construction-contracts.yaml regression test",
                            "runtime_version_introduced": "contextpack-runtime-2026.07.14.2",
                            "runtime_version_fixed": "",
                            "recurrence_count": 1,
                            "status": "open",
                        }
                    },
                },
            )
            if workflowctl.migrate_workflow_runtime(strong_context_dir, "execution-only", "task-planning") != 0:
                errors.append(f"{WORKFLOWCTL}: defect-scoped runtime migration failed")
            else:
                scoped_migrated = workflowctl.as_dict(workflowctl.load_yaml(strong_context_dir / "workflow-state.yaml"))
                scoped_audit = workflowctl.as_dict(workflowctl.as_list(scoped_migrated.get("runtime_migrations"))[-1])
                invalidated = workflowctl.as_list(scoped_audit.get("invalidated_stages"))
                if scoped_audit.get("scoped_from_stage") != "task-planning" or "source-intake" in invalidated or "task-planning" not in invalidated:
                    errors.append(f"{WORKFLOWCTL}: defect-scoped migration had excessive blast radius: {scoped_audit}")

        defect_dir = repo / "specs" / "changes" / "late-defect-smoke"
        defect_dir.mkdir(parents=True)
        defect_args = (
            defect_dir, "contract-final", "missing provider owner for managed resource", "contract", "prd",
            "missing-machine-rule", "SC-MANAGED-RESOURCE-001", "spec.md", "repair PRD ownership matrix",
            "stage-construction-contracts.yaml negative test",
        )
        invalid_defect_args = (*defect_args[:-1], "manual follow-up later")
        if quiet_call(workflowctl.record_late_defect, *invalid_defect_args) == 0:
            errors.append(f"{WORKFLOWCTL}: invalid late defect promotion target was accepted")
        if (defect_dir / "workflow-defects.yaml").exists():
            errors.append(f"{WORKFLOWCTL}: failed late defect command poisoned the defect ledger")
        updated_defect_args = (
            *defect_args[:-2],
            "repair PRD ownership matrix and add provider evidence",
            "stage-construction-contracts.yaml regression test",
        )
        second_defect_args = (
            defect_dir, "contract-final", "missing verification owner for managed resource", "contract", "prd",
            "missing-machine-rule", "SC-MANAGED-RESOURCE-001", "spec.md", "repair PRD verification ownership",
            "stage-construction-contracts.yaml regression test",
        )
        if (
            workflowctl.record_late_defect(*defect_args) != 0
            or workflowctl.record_late_defect(*updated_defect_args) != 0
            or workflowctl.record_late_defect(*second_defect_args) != 0
        ):
            errors.append(f"{WORKFLOWCTL}: late defect recording failed")
        else:
            defect_doc = workflowctl.as_dict(workflowctl.load_yaml(defect_dir / "workflow-defects.yaml"))
            defect = workflowctl.as_dict(workflowctl.as_dict(defect_doc.get("defects")).get("LD-001"))
            if defect.get("recurrence_count") != 2 or defect.get("repair_action") != "repair PRD ownership matrix and add provider evidence":
                errors.append(f"{WORKFLOWCTL}: duplicate late defect signature was not consolidated")
            for raw in workflowctl.as_dict(defect_doc.get("defects")).values():
                workflowctl.as_dict(raw)["runtime_version_introduced"] = "contextpack-runtime-2026.07.14.2"
            workflowctl.write_yaml(defect_dir / "workflow-defects.yaml", defect_doc)
            defect_migration = {
                "from_version": "contextpack-runtime-2026.07.14.2",
                "to_version": runtime_manifest.get("runtime_version"),
                "previous_manifest_hash": "old-manifest",
                "current_manifest_hash": workflowctl.sha256_file(WORKFLOW_RUNTIME_MANIFEST),
                "invalidated_stages": list(workflowctl.ALL_STAGES),
                "previous_component_hashes": {
                    "stage_construction_contract": "old-contract",
                    "validate_skill_suite": "old-suite",
                },
                "current_component_hashes": {
                    "stage_construction_contract": workflowctl.as_dict(
                        runtime_components.get("stage_construction_contract")
                    ).get("sha256"),
                    "validate_skill_suite": workflowctl.as_dict(
                        runtime_components.get("validate_skill_suite")
                    ).get("sha256"),
                },
            }
            defect_migration["audit_hash"] = workflowctl.canonical_audit_hash(defect_migration)
            workflowctl.write_yaml(
                defect_dir / "workflow-state.yaml",
                {"runtime_migrations": [defect_migration]},
            )
            if not workflowctl.validate_workflow_defects(defect_dir):
                errors.append(f"{WORKFLOWCTL}: open late defect did not block workflow validation")
            repaired_artifact = defect_dir / "spec.md"
            repaired_artifact.write_text(
                "# Product requirement\n\nThe managed resource owner is now explicit and verifiable.\n",
                encoding="utf-8",
            )
            (defect_dir / "unrelated.md").write_text("unrelated evidence\n", encoding="utf-8")
            if quiet_call(
                workflowctl.repair_late_defect,
                defect_dir,
                "LD-001",
                "prd",
                ["unrelated.md"],
                ["python3 -c 'print(\"unrelated validator\")'"],
            ) == 0:
                errors.append(f"{WORKFLOWCTL}: unrelated artifact falsely repaired a late defect")
            if quiet_call(
                workflowctl.repair_late_defect,
                defect_dir,
                "LD-001",
                "prd",
                ["spec.md"],
                ["python3 -c 'raise SystemExit(3)'"],
            ) == 0:
                errors.append(f"{WORKFLOWCTL}: failing validator command falsely repaired a late defect")
            if workflowctl.repair_late_defect(
                defect_dir,
                "LD-001",
                "prd",
                ["spec.md"],
                ["python3 -c 'print(\"local repair validator passed\")'"],
            ) != 0:
                errors.append(f"{WORKFLOWCTL}: local late-defect repair was rejected")
            else:
                locally_repaired_doc = workflowctl.as_dict(
                    workflowctl.load_yaml(defect_dir / "workflow-defects.yaml")
                )
                locally_repaired = workflowctl.as_dict(
                    workflowctl.as_dict(locally_repaired_doc.get("defects")).get("LD-001")
                )
                isolated_doc = {
                    "schema_version": 1,
                    "defects": {"LD-001": copy.deepcopy(locally_repaired)},
                }
                if workflowctl.validate_workflow_defects_doc(
                    defect_dir / "workflow-defects.yaml", isolated_doc, True
                ):
                    errors.append(f"{WORKFLOWCTL}: intact locally repaired defect still blocked product workflow")
                repaired_body = repaired_artifact.read_text(encoding="utf-8")
                repaired_artifact.write_text(repaired_body + "changed after repair\n", encoding="utf-8")
                stale_local_errors = workflowctl.validate_workflow_defects_doc(
                    defect_dir / "workflow-defects.yaml", isolated_doc, True
                )
                if not any("local repair evidence is stale" in error for error in stale_local_errors):
                    errors.append(f"{WORKFLOWCTL}: stale local repair artifact hash was accepted")
                repaired_artifact.write_text(repaired_body, encoding="utf-8")
            if "workflow-defects.yaml" not in workflowctl.stage_required_artifact_rels(defect_dir, "prd"):
                errors.append(f"{WORKFLOWCTL}: defect ledger is not sealed into stage receipts")
            if "workflow-defects.yaml" in workflowctl.stage_required_artifact_rels(defect_dir, "source-intake"):
                errors.append(f"{WORKFLOWCTL}: defect ledger invalidated receipts before should_have_caught_stage")
            scope_dir = repo / "specs" / "changes" / "late-defect-scope-smoke"
            scope_dir.mkdir(parents=True)
            scope_doc = {
                "schema_version": 1,
                "defects": {
                    "LD-001": {"should_have_caught_stage": "prd", "status": "promoted"},
                },
            }
            workflowctl.write_yaml(scope_dir / "workflow-defects.yaml", scope_doc)
            prd_digest_before = workflowctl.workflow_defects_stage_digest(scope_dir / "workflow-defects.yaml", "prd")
            scope_doc["defects"]["LD-002"] = {"should_have_caught_stage": "contract", "status": "open"}
            workflowctl.write_yaml(scope_dir / "workflow-defects.yaml", scope_doc)
            if workflowctl.workflow_defects_stage_digest(scope_dir / "workflow-defects.yaml", "prd") != prd_digest_before:
                errors.append(f"{WORKFLOWCTL}: later-stage defect changed an earlier stage-scoped ledger digest")
            if quiet_call(
                workflowctl.promote_late_defect,
                defect_dir,
                "LD-001",
                ["templates/workflow-state-contextpack.yaml", "scripts/validate_skill_suite.py"],
                "SC-MANAGED-RESOURCE-001",
            ) == 0:
                errors.append(f"{WORKFLOWCTL}: non-manifest behavior target promoted a late defect")
            insufficient_state = workflowctl.as_dict(workflowctl.load_yaml(defect_dir / "workflow-state.yaml"))
            workflowctl.as_dict(workflowctl.as_list(insufficient_state.get("runtime_migrations"))[-1])[
                "invalidated_stages"
            ] = ["task-planning", "execution", "mock-acceptance", "product-acceptance"]
            insufficient_migration = workflowctl.as_dict(workflowctl.as_list(insufficient_state.get("runtime_migrations"))[-1])
            insufficient_migration["audit_hash"] = workflowctl.canonical_audit_hash(insufficient_migration)
            workflowctl.write_yaml(defect_dir / "workflow-state.yaml", insufficient_state)
            if quiet_call(
                workflowctl.promote_late_defect,
                defect_dir,
                "LD-001",
                ["templates/stage-construction-contracts.yaml", "scripts/validate_skill_suite.py"],
                "SC-MANAGED-RESOURCE-001",
            ) == 0:
                errors.append(f"{WORKFLOWCTL}: defect promotion ignored insufficient migration stage coverage")
            sufficient_state = workflowctl.as_dict(workflowctl.load_yaml(defect_dir / "workflow-state.yaml"))
            workflowctl.as_dict(workflowctl.as_list(sufficient_state.get("runtime_migrations"))[-1])[
                "invalidated_stages"
            ] = list(workflowctl.ALL_STAGES)
            sufficient_migration = workflowctl.as_dict(workflowctl.as_list(sufficient_state.get("runtime_migrations"))[-1])
            sufficient_migration["audit_hash"] = workflowctl.canonical_audit_hash(sufficient_migration)
            workflowctl.write_yaml(defect_dir / "workflow-state.yaml", sufficient_state)
            if workflowctl.promote_late_defect(
                defect_dir,
                "LD-001",
                ["templates/stage-construction-contracts.yaml", "scripts/validate_skill_suite.py"],
                "SC-MANAGED-RESOURCE-001",
            ) != 0:
                errors.append(f"{WORKFLOWCTL}: first late defect promotion failed while another defect remained open")
            elif not workflowctl.validate_workflow_defects(defect_dir):
                errors.append(f"{WORKFLOWCTL}: remaining open late defect did not keep workflow blocked")
            if workflowctl.promote_late_defect(
                defect_dir,
                "LD-002",
                ["templates/stage-construction-contracts.yaml", "scripts/validate_skill_suite.py"],
                "SC-MANAGED-RESOURCE-001",
            ) != 0:
                errors.append(f"{WORKFLOWCTL}: second late defect promotion failed")
            elif workflowctl.validate_workflow_defects(defect_dir):
                errors.append(f"{WORKFLOWCTL}: all promoted late defects did not validate")
            original_manifest_loader = workflowctl.load_workflow_runtime_manifest
            future_manifest = copy.deepcopy(runtime_manifest)
            future_manifest["runtime_version"] = "contextpack-runtime-2026.07.14.5"
            workflowctl.load_workflow_runtime_manifest = lambda: future_manifest
            try:
                if workflowctl.validate_workflow_defects(defect_dir):
                    errors.append(f"{WORKFLOWCTL}: later runtime made historical promoted-defect evidence unrecoverably stale")
                future_without_rule = copy.deepcopy(future_manifest)
                workflowctl.as_dict(future_without_rule.get("components")).pop("stage_construction_contract", None)
                workflowctl.load_workflow_runtime_manifest = lambda: future_without_rule
                if not workflowctl.validate_workflow_defects(defect_dir):
                    errors.append(f"{WORKFLOWCTL}: later runtime removed a promoted rule without invalidating its defect evidence")
            finally:
                workflowctl.load_workflow_runtime_manifest = original_manifest_loader
            recurrence_dir = repo / "specs" / "changes" / "late-defect-recurrence-smoke"
            recurrence_dir.mkdir(parents=True)
            workflowctl.write_yaml(recurrence_dir / "workflow-defects.yaml", workflowctl.load_yaml(defect_dir / "workflow-defects.yaml"))
            workflowctl.write_yaml(recurrence_dir / "workflow-state.yaml", workflowctl.load_yaml(defect_dir / "workflow-state.yaml"))
            recurrence_source = workflowctl.as_dict(
                workflowctl.as_dict(workflowctl.load_yaml(recurrence_dir / "workflow-defects.yaml").get("defects")).get("LD-001")
            )
            if workflowctl.record_late_defect(
                recurrence_dir,
                recurrence_source.get("gate"),
                recurrence_source.get("failure_signature"),
                recurrence_source.get("detected_stage"),
                recurrence_source.get("should_have_caught_stage"),
                recurrence_source.get("classification"),
                recurrence_source.get("affected_rule"),
                recurrence_source.get("affected_artifact"),
                recurrence_source.get("repair_action"),
                recurrence_source.get("promotion_target"),
            ) != 0:
                errors.append(f"{WORKFLOWCTL}: promoted late defect could not be reopened on recurrence")
            else:
                recurrence_row = workflowctl.as_dict(
                    workflowctl.as_dict(workflowctl.load_yaml(recurrence_dir / "workflow-defects.yaml").get("defects")).get("LD-001")
                )
                if (
                    recurrence_row.get("status") != "open"
                    or recurrence_row.get("runtime_version_introduced") != runtime_manifest.get("runtime_version")
                    or recurrence_row.get("promotion_evidence")
                    or recurrence_row.get("promotion_receipt_hash")
                    or recurrence_row.get("local_repair_evidence")
                ):
                    errors.append(f"{WORKFLOWCTL}: recurring promoted defect retained stale promotion/runtime evidence")
            promoted_doc = workflowctl.as_dict(workflowctl.load_yaml(defect_dir / "workflow-defects.yaml"))
            promoted_ld1 = workflowctl.as_dict(workflowctl.as_dict(promoted_doc.get("defects")).get("LD-001"))
            target_hashes = workflowctl.as_dict(workflowctl.as_dict(promoted_ld1.get("promotion_evidence")).get("target_hashes"))
            first_target = next(iter(target_hashes), "")
            if first_target:
                target_hashes[first_target] = "forged"
                workflowctl.write_yaml(defect_dir / "workflow-defects.yaml", promoted_doc)
                if not workflowctl.validate_workflow_defects(defect_dir):
                    errors.append(f"{WORKFLOWCTL}: forged promoted-defect evidence was accepted")

        event_dir = repo / "specs" / "changes" / "workflow-events-smoke"
        event_dir.mkdir(parents=True)
        workflowctl.append_workflow_event(event_dir, "stage_prepared", {"stage": "prd"})
        workflowctl.append_workflow_event(event_dir, "obligation_validated", {"stage": "prd", "id": "OBL-001"})
        if workflowctl.validate_workflow_events(event_dir):
            errors.append(f"{WORKFLOWCTL}: valid workflow event hash chain was rejected")
        event_doc = workflowctl.as_dict(workflowctl.load_yaml(event_dir / "workflow-events.yaml"))
        event_rows = [workflowctl.as_dict(item) for item in workflowctl.as_list(event_doc.get("events"))]
        if len(event_rows) != 2 or event_rows[1].get("previous_hash") != event_rows[0].get("event_hash"):
            errors.append(f"{WORKFLOWCTL}: workflow events are not sequentially hash chained")
        with contextlib.redirect_stdout(io.StringIO()) as metrics_output:
            metrics_result = workflowctl.print_workflow_metrics(event_dir)
        if metrics_result != 0 or "events_total: 2" not in metrics_output.getvalue():
            errors.append(f"{WORKFLOWCTL}: workflow metrics did not report event counts")
        event_rows[0]["details"] = {"stage": "forged"}
        workflowctl.write_yaml(event_dir / "workflow-events.yaml", event_doc)
        if not workflowctl.validate_workflow_events(event_dir):
            errors.append(f"{WORKFLOWCTL}: tampered workflow event was accepted")
        validate_body = inspect.getsource(workflowctl.validate)
        if "validate_workflow_events" in validate_body:
            errors.append(f"{WORKFLOWCTL}: advisory workflow telemetry must not deadlock canonical stage validation")

        backflow_resolution_dir = repo / "specs" / "changes" / "backflow-resolution-smoke"
        backflow_resolution_dir.mkdir(parents=True)
        workflowctl.write_yaml(
            backflow_resolution_dir / "workflow-state.yaml",
            {
                "stage_status": {"prd": "passed"},
                "stage_receipts": {
                    "prd": {
                        "stage": "prd",
                        "status": "passed",
                        "issued_at": "2026-07-17T00:00:00+00:00",
                        "receipt_hash": "fresh-prd-receipt",
                    }
                },
                "stage_reopens": [
                    {
                        "stage": "prd",
                        "backflow_id": "BF-AUTO-001",
                        "reopened_at": "2026-07-17T00:00:00+00:00",
                    }
                ],
            },
        )
        workflowctl.write_yaml(
            backflow_resolution_dir / "backflow.yaml",
            {
                "schema_version": 1,
                "triggers": {
                    "BF-AUTO-001": {
                        "status": "open",
                        "resolution_stage": "prd",
                        "invalidates": {
                            "artifacts": ["proposal.md"],
                            "decisions": [],
                            "contracts": [],
                            "verifications": [],
                            "tasks": [],
                        },
                    }
                },
            },
        )
        missing_reopen_state = workflowctl.as_dict(
            workflowctl.load_yaml(backflow_resolution_dir / "workflow-state.yaml")
        )
        saved_reopens = missing_reopen_state.pop("stage_reopens")
        workflowctl.write_yaml(backflow_resolution_dir / "workflow-state.yaml", missing_reopen_state)
        if not any(
            "no matching reopen audit" in error
            for error in workflowctl.validate_backflow(workflowctl.WorkflowModel(backflow_resolution_dir))
        ):
            errors.append(f"{WORKFLOWCTL}: open backflow without reopen audit did not block revalidation")
        missing_reopen_state["stage_reopens"] = saved_reopens
        workflowctl.write_yaml(backflow_resolution_dir / "workflow-state.yaml", missing_reopen_state)
        workflowctl.auto_resolve_backflows(backflow_resolution_dir, "prd")
        resolved_trigger = workflowctl.as_dict(
            workflowctl.as_dict(
                workflowctl.load_yaml(backflow_resolution_dir / "backflow.yaml").get("triggers")
            ).get("BF-AUTO-001")
        )
        if (
            resolved_trigger.get("status") != "resolved"
            or resolved_trigger.get("resolution_receipt_hash") != "fresh-prd-receipt"
        ):
            errors.append(f"{WORKFLOWCTL}: fresh resolution-stage receipt did not auto-resolve backflow")
        if workflowctl.validate_backflow(workflowctl.WorkflowModel(backflow_resolution_dir)):
            errors.append(f"{WORKFLOWCTL}: auto-resolved backflow failed canonical validation")

        identity_path = event_dir / "workflow-workdir.md"
        identity_path.write_text("# Workflow Workdir Identity\n\n| Item | Value |\n|---|---|\n| Change id | x |\n\n## Resume Verification\n\ninitial\n", encoding="utf-8")
        identity_digest = workflowctl.artifact_receipt_digest(identity_path, "workflow-workdir.md")
        identity_path.write_text(
            identity_path.read_text(encoding="utf-8") + "resume matched\n| Change id | forged |\n",
            encoding="utf-8",
        )
        if workflowctl.artifact_receipt_digest(identity_path, "workflow-workdir.md") != identity_digest:
            errors.append(f"{WORKFLOWCTL}: resume audit append invalidated stable workflow identity digest")
        identity_body = re.split(
            r"^##+\s+Resume Verification\b",
            identity_path.read_text(encoding="utf-8"),
            maxsplit=1,
            flags=re.MULTILINE,
        )[0]
        if workflowctl.markdown_table_values(identity_body).get("change id") != "x":
            errors.append(f"{WORKFLOWCTL}: resume audit duplicate keys reinterpreted sealed workflow identity")
        ancestry_head = workflowctl.command_output(["git", "-C", str(repo), "rev-parse", "HEAD"])
        ancestry_branch = workflowctl.command_output(["git", "-C", str(repo), "branch", "--show-current"])
        if ancestry_head and ancestry_branch:
            ancestry_dir = repo / "specs" / "changes" / "workdir-ancestry-smoke"
            ancestry_dir.mkdir(parents=True)
            ancestry_identity = f"""# Workflow Workdir Identity

## Canonical Workdir

| Item | Value |
|---|---|
| Target repo | smoke |
| Worktree path | {repo.as_posix()} |
| Change dir absolute path | {ancestry_dir.as_posix()} |
| Change id | workdir-ancestry-smoke |
| Branch name | {ancestry_branch} |
| Base branch | {ancestry_branch} |
| Base commit | {ancestry_head} |
| Base source mode | pinned-commit |
| Remote ref | none |
| Remote OID | none |
| Remote fetched at | none |
| Fetch command evidence | pinned local test commit |
| Git top level | {repo.as_posix()} |

## Resume Verification
"""
            (ancestry_dir / "workflow-workdir.md").write_text(ancestry_identity, encoding="utf-8")
            workflowctl.write_yaml(
                ancestry_dir / "workflow-state.yaml",
                {
                    "workflow": {
                        "change_id": "workdir-ancestry-smoke",
                        "change_dir_abs": ancestry_dir.as_posix(),
                        "worktree_path": repo.as_posix(),
                        "branch_name": ancestry_branch,
                        "base_commit": ancestry_head,
                    }
                },
            )
            if workflowctl.validate_workdir_identity(workflowctl.WorkflowModel(ancestry_dir)):
                errors.append(f"{WORKFLOWCTL}: valid base-commit ancestry was rejected")
            identity_before_resume = (ancestry_dir / "workflow-workdir.md").read_bytes()
            if workflowctl.verify_resume(ancestry_dir) != 0:
                errors.append(f"{WORKFLOWCTL}: verify-resume rejected a matching identity")
            if (ancestry_dir / "workflow-workdir.md").read_bytes() != identity_before_resume:
                errors.append(f"{WORKFLOWCTL}: verify-resume modified the receipt-bearing workflow identity")
            resume_events = workflowctl.as_list(
                workflowctl.as_dict(workflowctl.load_yaml(ancestry_dir / "workflow-events.yaml")).get("events")
            )
            if not any(workflowctl.text(workflowctl.as_dict(item).get("event_type")) == "resume_verified" for item in resume_events):
                errors.append(f"{WORKFLOWCTL}: verify-resume did not append a hash-chained resume event")

            stale_remote_identity = ancestry_identity.replace(
                f"| Base branch | {ancestry_branch} |", "| Base branch | origin/main |"
            )
            (ancestry_dir / "workflow-workdir.md").write_text(stale_remote_identity, encoding="utf-8")
            for validator_name, identity_errors in [
                (
                    str(WORKFLOWCTL),
                    workflowctl.validate_workdir_identity(workflowctl.WorkflowModel(ancestry_dir)),
                ),
                (
                    str(ARTIFACT_VALIDATOR),
                    artifact_validator.validate_workdir_identity(
                        ancestry_dir, artifact_validator.read_yaml(ancestry_dir / "workflow-state.yaml")
                    ),
                ),
            ]:
                if not any("origin base requires" in error for error in identity_errors):
                    errors.append(f"{validator_name}: origin base accepted without fetched-remote evidence")

            fresh_remote_identity = (
                stale_remote_identity
                .replace("| Base source mode | pinned-commit |", "| Base source mode | fetched-remote |")
                .replace("| Remote ref | none |", "| Remote ref | origin/main |")
                .replace("| Remote OID | none |", f"| Remote OID | {ancestry_head} |")
                .replace("| Remote fetched at | none |", "| Remote fetched at | 2026-07-17T00:00:00Z |")
                .replace(
                    "| Fetch command evidence | pinned local test commit |",
                    "| Fetch command evidence | git fetch origin main completed |",
                )
            )
            (ancestry_dir / "workflow-workdir.md").write_text(fresh_remote_identity, encoding="utf-8")
            for validator_name, identity_errors in [
                (
                    str(WORKFLOWCTL),
                    workflowctl.validate_workdir_identity(workflowctl.WorkflowModel(ancestry_dir)),
                ),
                (
                    str(ARTIFACT_VALIDATOR),
                    artifact_validator.validate_workdir_identity(
                        ancestry_dir, artifact_validator.read_yaml(ancestry_dir / "workflow-state.yaml")
                    ),
                ),
            ]:
                if identity_errors:
                    errors.append(f"{validator_name}: fresh remote base identity was rejected: {identity_errors}")

            (ancestry_dir / "workflow-workdir.md").write_text(ancestry_identity, encoding="utf-8")
            invalid_base = "0" * 40
            (ancestry_dir / "workflow-workdir.md").write_text(
                ancestry_identity.replace(ancestry_head, invalid_base), encoding="utf-8"
            )
            ancestry_state = workflowctl.as_dict(workflowctl.load_yaml(ancestry_dir / "workflow-state.yaml"))
            workflowctl.as_dict(ancestry_state.get("workflow"))["base_commit"] = invalid_base
            workflowctl.write_yaml(ancestry_dir / "workflow-state.yaml", ancestry_state)
            if not any(
                "base commit" in error
                for error in workflowctl.validate_workdir_identity(workflowctl.WorkflowModel(ancestry_dir))
            ):
                errors.append(f"{WORKFLOWCTL}: nonexistent base commit passed workdir identity validation")
        (event_dir / "plan.md").write_text("# Plan\n\n## Design\naccepted design\n", encoding="utf-8")
        workflowctl.write_stage_plan_snapshot(event_dir, "design")
        snapshot_path = event_dir / "stage-snapshots" / "design-plan.md"
        snapshot_digest = workflowctl.sha256_file(snapshot_path)
        (event_dir / "plan.md").write_text("# Plan\n\n## Design\naccepted design\n\n## Archaeology\nnew downstream facts\n", encoding="utf-8")
        if workflowctl.sha256_file(snapshot_path) != snapshot_digest:
            errors.append(f"{WORKFLOWCTL}: downstream plan edits changed an accepted stage snapshot")
        if "plan.md" in workflowctl.STAGE_RECEIPT_REQUIRED_ARTIFACTS.get("design", []):
            errors.append(f"{WORKFLOWCTL}: shared plan.md remains directly sealed by design receipt")
        (event_dir / "plan.md").write_text("# Plan\n\n## AIP\nlocked design\n", encoding="utf-8")
        workflowctl.write_stage_plan_snapshot(event_dir, "aip")
        append_only_state = {
            "workflow": {"profile": "full", "stage_construction_protocol": "stage-construction-v1"},
            "stage_status": {"aip": "passed"},
        }
        (event_dir / "plan.md").write_text("# Plan\n\n## AIP\nlocked design\n\n## Readiness\nready\n", encoding="utf-8")
        if workflowctl.plan_append_only_errors(event_dir, append_only_state, "readiness"):
            errors.append(f"{WORKFLOWCTL}: append-only downstream plan extension was rejected")
        (event_dir / "plan.md").write_text("# Plan\n\n## AIP\nrewritten design\n", encoding="utf-8")
        snapshot_rewrite_errors = workflowctl.plan_append_only_errors(event_dir, append_only_state, "readiness")
        if not snapshot_rewrite_errors:
            errors.append(f"{WORKFLOWCTL}: downstream plan rewrite of accepted snapshot was allowed")
        elif not any("after the generated `---` wrapper" in error and "do not copy the snapshot header" in error for error in snapshot_rewrite_errors):
            errors.append(f"{WORKFLOWCTL}: snapshot rewrite diagnostic does not explain the accepted plan body boundary")
        workflowctl.write_yaml(event_dir / "workflow-state.yaml", append_only_state)
        preflight_output = io.StringIO()
        with contextlib.redirect_stdout(preflight_output), contextlib.redirect_stderr(preflight_output):
            preflight_result = workflowctl.preflight_stage_closures(event_dir, "readiness")
        if preflight_result == 0 or "rewrites accepted aip semantics" not in preflight_output.getvalue():
            errors.append(f"{WORKFLOWCTL}: closure preflight did not reject a downstream rewrite of the accepted plan snapshot")

        reviewer_output = event_dir / "reviewer-outputs" / "review-001.md"
        reviewer_output.parent.mkdir(parents=True)
        reviewer_output.write_text("No blocking findings.\n", encoding="utf-8")
        proof = {
            "subagent_execution": {
                "agent_id": "agent-001",
                "agent_type": "readonly-subagent",
                "spawn_agent_evidence": "spawn_agent agent_id=agent-001",
                "wait_agent_evidence": "wait_agent final status completed",
                "final_status": "completed",
                "final_message_digest": workflowctl.sha256_file(reviewer_output),
                "reviewer_output_source": "reviewer-outputs/review-001.md",
                "close_agent_evidence": "kept-live for reuse",
            }
        }
        if workflowctl.validate_subagent_execution_proof(proof, "review smoke", event_dir):
            errors.append(f"{WORKFLOWCTL}: valid reviewer output digest proof was rejected")
        workflowctl.as_dict(proof["subagent_execution"])["final_message_digest"] = "0" * 64
        if not workflowctl.validate_subagent_execution_proof(proof, "review smoke", event_dir):
            errors.append(f"{WORKFLOWCTL}: forged reviewer output digest was accepted")

        business_path = repo / "business-output.txt"
        business_path.write_text("passed output\n", encoding="utf-8")
        freshness_model = type("FreshnessModel", (), {})()
        freshness_model.change_dir = event_dir
        freshness_model.workflow = {
            "task_receipts": {
                "T001": {
                    "status": "passed",
                    "passed_at": "2026-07-15T00:00:00+00:00",
                    "passed_changed_path_hashes": {
                        "business-output.txt": workflowctl.sha256_file(business_path),
                    },
                }
            }
        }
        if workflowctl.passed_task_output_freshness_errors(freshness_model):
            errors.append(f"{WORKFLOWCTL}: fresh passed task output was rejected")
        business_path.write_text("changed after pass\n", encoding="utf-8")
        if not workflowctl.passed_task_output_freshness_errors(freshness_model):
            errors.append(f"{WORKFLOWCTL}: changed passed task output was accepted")

        standard_dir = repo / "specs" / "changes" / "standard-v1-smoke"
        standard_dir.mkdir(parents=True)
        workflowctl.write_yaml(
            standard_dir / "workflow-state.yaml",
            {
                "schema_version": 1,
                "workflow": {"skill": "automq-ai-dev-workflow"},
                "stage_status": {"prd": "in_progress"},
                "stage_receipts": {},
            },
        )
        standard_errors = workflowctl.validate_stage_construction(
            workflowctl.WorkflowModel(standard_dir), "prd"
        )
        if standard_errors:
            errors.append(f"{WORKFLOWCTL}: standard schema v1 workflow incorrectly required construction artifacts: {standard_errors}")
        (standard_dir / "proposal.md").write_text("REQ-001 mentions Context Pack Experiment as prose only.\n", encoding="utf-8")
        if workflowctl.stage_construction_enabled_doc(workflowctl.as_dict(workflowctl.load_yaml(standard_dir / "workflow-state.yaml"))):
            errors.append(f"{WORKFLOWCTL}: standard schema v1 prose incorrectly enabled contextpack mode")
        standard_artifact_errors = artifact_validator.validate_change(standard_dir, "aip")
        if any("AIP Creation Hard Gate" in error for error in standard_artifact_errors):
            errors.append(f"{ARTIFACT_VALIDATOR}: standard schema v1 prose incorrectly triggered contextpack AIP gate")

        legacy_dir = repo / "specs" / "changes" / "legacy-contextpack-v1-smoke"
        legacy_dir.mkdir(parents=True)
        workflowctl.write_yaml(
            legacy_dir / "workflow-state.yaml",
            {
                "schema_version": 1,
                "workflow": {"skill": "automq-ai-dev-workflow-contextpack", "context_pack_required": True},
                "stage_status": {"prd": "passed"},
                "stage_receipts": {"prd": {"status": "passed", "receipt_hash": "historical-format"}},
            },
        )
        legacy_errors = workflowctl.validate(legacy_dir, "all")
        if len(legacy_errors) != 1 or "migrate-workflow-runtime" not in legacy_errors[0]:
            errors.append(f"{WORKFLOWCTL}: legacy contextpack v1 was not frozen behind explicit migration: {legacy_errors}")
        legacy_artifact_errors = artifact_validator.validate_change(legacy_dir, "all")
        if len(legacy_artifact_errors) != 1 or "migrate-workflow-runtime" not in legacy_artifact_errors[0]:
            errors.append(f"{ARTIFACT_VALIDATOR}: legacy contextpack v1 was not frozen behind explicit migration")
        if quiet_call(workflowctl.prepare_stage, legacy_dir, "prd") == 0:
            errors.append(f"{WORKFLOWCTL}: prepare-stage silently migrated legacy contextpack v1")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AutoMQ workflow skill-suite wiring")
    parser.add_argument("--skills-root", type=Path, default=ROOT)
    args = parser.parse_args()
    set_root(args.skills_root)

    errors = (
        validate_workflow_drift()
        + validate_contract_obligation_validator_drift()
        + validate_planning_statuses()
        + validate_new_artifact_wiring()
        + validate_template_table_integrity()
        + validate_semantic_carrier_projection_wiring()
        + validate_playground_connect_scope_wiring()
        + validate_reviewer_wait_timeout_wiring()
        + validate_contract_executable_obligation_wiring()
        + validate_surface_type_contract_drift()
        + validate_runtime_mode_materialization_reference()
        + validate_aip_design_closure_reference()
        + validate_aip_design_closure_runtime_smoke()
        + validate_new_artifact_runtime_smoke()
        + validate_human_decision_and_mpr_smoke()
        + validate_launch_readiness_smoke()
        + validate_stage_construction_protocol()
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("AutoMQ workflow skill-suite validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
