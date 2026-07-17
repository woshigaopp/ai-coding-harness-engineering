#!/usr/bin/env python3
"""Validate AutoMQ AI workflow artifacts.

This script checks structural gates plus common semantic failure modes that
cause non-self-contained Atomic Issues. It is still not a replacement for the
human 0/1/2 rubric review, but it must reject artifacts that only satisfy the
template shape while leaving execution semantics in global documents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None

WORKFLOW_RUNTIME_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "templates" / "workflow-runtime-manifest.yaml"
WORKFLOW_STATE_MACHINE_PATH = Path(__file__).resolve().parent.parent / "templates" / "workflow-state-machine.yaml"
SKILLS_ROOT = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills"


def load_workflow_state_machine() -> dict:
    if yaml is None:
        raise ValueError("PyYAML is required for workflow state-machine loading")
    doc = yaml.safe_load(WORKFLOW_STATE_MACHINE_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise ValueError(f"{WORKFLOW_STATE_MACHINE_PATH}: schema_version must be 1")
    return doc


WORKFLOW_STATE_MACHINE = load_workflow_state_machine()
STAGE_PREREQUISITES = {
    str(stage): [str(item) for item in values]
    for stage, values in dict(WORKFLOW_STATE_MACHINE.get("prerequisites", {})).items()
}
RUNTIME_PREREQUISITES = {
    str(item) for item in WORKFLOW_STATE_MACHINE.get("runtime_prerequisites", [])
}


REQUIRED_ISSUE_HEADINGS = [
    "Goal|目标",
    "Scope|范围",
    "Source Context|来源上下文",
    "Module Contract Closure|模块契约闭包",
    "Locked Decisions|锁定决策",
    "Contract Excerpts|契约摘录",
    "Execution Preconditions|执行前提",
    "Consumed Contract Snapshot",
    "Provided Contract Obligation",
    "Invariant Carryover",
    "Preconditions Failure Handling",
    "Existing Code References|现有代码参考",
    "Files To Change|修改文件",
    "Behavior Details|行为细节",
    "Implementation Steps|实现步骤",
    "Verification|验证",
    "Prohibited Changes|禁止事项",
    "Done Criteria|完成标准",
]

REQUIRED_DECISION_HEADINGS = [
    "Source Inputs|来源输入",
    "Decision Summary|决策摘要",
    "Decision Details|决策详情",
]

AIP_TEMPLATE_HEADINGS = [
    ("AIP title", r"AIP（AutoMQ Improvement Proposal）模板|AIP\\s*\\(AutoMQ Improvement Proposal\\)"),
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

REQUIRED_CONTEXT_PACK_SECTIONS = [
    (
        "Source Rehydration Ledger|上下文恢复来源清单",
        ["Artifact", "Path", "Read status", "Consumed"],
    ),
    (
        "Upstream Semantic Index|上游语义索引",
        ["Object ID", "Type", "Executable semantics", "Source artifact", "Status"],
    ),
    (
        "Module And Contract Pack|Module and Contract Pack|模块与契约包",
        ["Module", "Owned state", "Provided contracts", "Consumed contracts"],
    ),
    (
        "Frontend Action Pack|前端 Action Pack|前端动作包",
        ["Action", "Route", "Landing component", "Verification"],
    ),
    (
        "Mock / Acceptance Runtime Pack|Mock Runtime Playground Pack|Mock/Runtime/Playground Pack|Mock 运行时 Playground 包",
        ["Area", "Mock", "Real contract source", "Verification"],
    ),
    (
        "Verification Pack|验证包",
        ["Verification", "Expected result", "Proves", "Failure meaning"],
    ),
    (
        "Task Generation Constraints|任务生成约束",
        ["Constraint", "Source", "Applies to", "Must appear"],
    ),
]

REQUIRED_BOUNDARY_CONTEXT_SECTIONS = [
    (
        "Source Rehydration Ledger|上下文恢复来源清单",
        ["Artifact", "Path", "Read status", "Consumed"],
    ),
    (
        "Semantic Index|语义索引",
        ["Object ID", "Executable semantics", "Source"],
    ),
    (
        "Decision And Constraint Pack|Decision and Constraint Pack|决策与约束包",
        ["Decision", "Constraint", "Status"],
    ),
    (
        "Boundary-Specific Pack|Boundary Specific Pack|边界专用包",
        ["Area", "Fact", "Source"],
    ),
    (
        "Downstream Coverage Map|下游覆盖映射",
        ["Object", "Downstream", "Status"],
    ),
]

REQUIRED_ACCEPTANCE_CONTEXT_SECTIONS = [
    (
        "Implemented Issue Ledger|已实现 Issue 清单",
        ["Task", "Status", "Diff", "Verification"],
    ),
    (
        "Acceptance Semantic Index|验收语义索引",
        ["Object ID", "Expected result", "Status"],
    ),
    (
        "Runtime Freshness Pack|运行时新鲜度包",
        ["Item", "Evidence", "Status"],
    ),
    (
        "Browser API Path Pack|Browser/API Path Pack|浏览器 API 路径包",
        ["Route", "API", "Evidence"],
    ),
    (
        "Mock Real Boundary Pack|Mock/Real Boundary Pack|Mock 真实边界包",
        ["Area", "Real code", "Mock", "Source"],
    ),
    (
        "Not Run And Cloud Boundary|Not Run and Cloud Boundary|未验证与云边界",
        ["Item", "Blocks done", "Owner"],
    ),
    (
        "Handoff QA Checklist|交付 QA 清单",
        ["Check", "Expected", "Status"],
    ),
]

DECISION_ID_PATTERN = (
    r"(?:PDEC|ADEC|DEC(?:-[A-Z][A-Z0-9]*)?|READY-DEC|ARCH-DEC|"
    r"DESIGN-DEC|MIG-DEC|UI-DEC|VER-DEC|TASK-DEC)-\d{3}"
)
DECISION_ID_RE = re.compile(rf"\b{DECISION_ID_PATTERN}\b")
EXTERNAL_DESIGN_OBJECT_ID_RE = re.compile(r"\b(?:MECH|EXTMECH|FACT|EXT|CONSTRAINT|XCON)-\d{3}\b")
DECISION_RANGE_RE = re.compile(
    rf"\b(?:{DECISION_ID_PATTERN}|C-\d{{3}})\s*(?:\.\.|-|到|~)\s*(?:(?:{DECISION_ID_PATTERN}|C)-)?\d{{3}}\b"
)
SOURCE_ID_RE = re.compile(r"\b(?:REQ|SCN|C|MIG)-\d{3}\b|" + DECISION_ID_RE.pattern)
UPSTREAM_ID_PATTERN = (
    rf"\b(REQ-\d{{3}}|SCN-\d{{3}}|{DECISION_ID_PATTERN}|C-\d{{3}}|MIG-\d{{3}}|VER-\d{{3}})\b"
)
VAGUE_SCOPE_RE = re.compile(
    r"\b(?:new helper under|helper package|as discovered|if missing|where needed|as needed|if present|"
    r"according to (?:Decision Registry|plan|spec)|see (?:Decision Registry|plan|spec)|TBD|TODO)\b",
    re.IGNORECASE,
)
CJK_RE = re.compile(r"[\u3400-\u9fff]")
LATIN_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z]{2,}\b")
GENERIC_PACKET_TEXT_RE = re.compile(
    r"(?:REQ|SCN)-\d{3}\s+针对\s+.+?的执行输入：本任务只处理已锁定的字段、接口、页面或验收行"
    r"|Executable requirement semantics for (?:REQ|SCN)-\d{3} must be preserved by owner tasks"
    r"|(?:FACT|CONSTRAINT|EXT|XCON|MECH|EXTMECH)-\d{3}\s+constrains provider resources, scaling, reachability, lifecycle, or mock boundary behavior"
    r"|(?:PDEC|ADEC|DEC|MIG-DEC|UI-DEC|TASK-DEC)-\d{3}\s+locks the .+? behavior used by this task; implementation must not reinterpret it"
    r"|Decision\s+(?:PDEC|ADEC|DEC|MIG-DEC|UI-DEC|TASK-DEC)-\d{3}\s+is locked and cannot be reinterpreted during implementation"
    r"|Implement/prove\s+.+?\s+owned behavior here"
    r"|Allowlist owner path for API/service/persistence/runtime proof semantics when this backend contract requires it"
    r"|(?:FACT|EXT|MECH)-\d{3}\s+constrains .+? behavior"
    r"|(?:CONSTRAINT|XCON|EXTMECH)-\d{3}\s+constrains .+? behavior",
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
BLOCKING_NOT_RUN_RE = re.compile(
    r"\|\s*[^|\n]+\|\s*[^|\n]*\b(?:P0|P1)\b[^|\n]*\|"
    r"|\|\s*[^|\n]*\|\s*yes\s*\|"
    r"|\|\s*[^|\n]*(?:Blocks done|阻塞完成)[^|\n]*\|\s*(?:yes|是)\s*\|",
    re.IGNORECASE,
)
STATEFUL_SIGNAL_RE = re.compile(
    r"\b(lifecycle|progress|event|events|terminal|polling|retry|state\s*graph|state\s*machine|"
    r"task\s*step|change\s*tracking|step\s*graph)\b|"
    r"生命周期|进度|事件|状态机|状态图|终态|轮询|重试|任务步骤|变更追踪|状态推进",
    re.IGNORECASE,
)
MOCK_ACCEPTANCE_SIGNAL_RE = re.compile(
    r"\b(mock|repo-specific acceptance runtime|acceptance runtime|MockData|MockControllerAspect|@MockFor|fixture|no-cloud|"
    r"external dependenc(?:y|ies)|provider|orchestrator|runtime|packaged acceptance|packaged playground|repo-specific packaged acceptance|"
    r"mock-acceptance|browser acceptance|Playwright|DOM|HAR|trace)\b|"
    r"模拟|验收|无云|外部依赖|浏览器|点击|提交|前端",
    re.IGNORECASE,
)
DECISION_SURFACE_SIGNAL_RE = re.compile(
    r"\b(?:purpose-only|purpose\s+only|mode|deployment\s+mode|runtime\s+mode|compute\s+mode|storage\s+mode|network\s+mode|"
    r"lifecycle|post[- ]?create|after\s+create|create|update|delete|resize|save|scale|import|bind|"
    r"mutation|persistent|persistence|schema|mock|frontend|ui|action|button|route|page|tab|"
    r"capability|external\s+dependenc(?:y|ies))\b|"
    r"只给.*目标|只给.*purpose|模式|部署模式|运行时|生命周期|创建后|创建|更新|删除|扩缩|保存|持久化|落库|表结构|"
    r"能力|前端|页面|按钮|操作|路由|控制器|外部依赖|验收|模拟",
    re.IGNORECASE,
)
MODE_SURFACE_SIGNAL_RE = re.compile(
    r"\b(?:mode|deployment\s+mode|runtime\s+mode|compute\s+mode|storage\s+mode|network\s+mode)\b|模式|部署模式|运行时模式",
    re.IGNORECASE,
)
MUTATION_SURFACE_SIGNAL_RE = re.compile(
    r"\b(?:create|update|delete|resize|save|scale|import|bind|mutation|persistent|persistence|schema)\b|创建|更新|删除|扩缩|保存|持久化|落库|表结构",
    re.IGNORECASE,
)
POST_CREATE_SURFACE_SIGNAL_RE = re.compile(r"\b(?:post[- ]?create|after\s+create|create)\b|创建后|创建成功后|创建", re.IGNORECASE)
FRONTEND_SURFACE_SIGNAL_RE = re.compile(
    r"\b(?:frontend|ui|action|button|route|page|component|tab|form|wizard)\b|前端|页面|按钮|操作|路由|组件|表单",
    re.IGNORECASE,
)
DECISION_SURFACE_ALLOWED_TYPES = {
    "mode-consumer",
    "capability",
    "frontend-action",
    "post-create-consumer",
    "persistent-mutation",
    "operation-mutability",
    "managed-resource-ownership",
    "runtime-lifecycle",
    "runtime-mode-materialization-parity",
    "mock-acceptance-runtime",
    "mock-playground",  # legacy alias; new artifacts should use mock-acceptance-runtime
    "observability",
    "permission",
    "compatibility",
}
DECISION_SURFACE_OWNER_STAGES = {
    "PRD",
    "AIP",
    "readiness",
    "design",
    "archaeology",
    "migration",
    "frontend-contract",
    "cross-module-contract",
    "verification",
    "task-planning",
}
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
DECISION_SURFACE_EXECUTION_FIELDS = {
    "scope",
    "module_responsibility",
    "provided_contract_obligations",
    "consumed_contract_snapshots",
    "invariant_carryover",
    "behavior_details",
    "backend_behavior_verification",
    "persistent_mutation_proofs",
    "stateful_behavior",
    "frontend_user_task",
    "action_route_component",
    "mode_field_display_matrix",
    "form_state_matrix",
    "mode_negative_assertions",
    "fixture_needs",
    "browser_verification",
    "implementation_steps",
    "verification",
    "prohibited_changes",
    "done_criteria",
}
DECISION_SURFACE_APPENDIX_ONLY_FIELDS = {
    "source",
    "sources",
    "source_context",
    "context",
    "context_pack",
    "appendix",
    "traceability",
    "plan",
    "spec",
    "proposal",
    "decision_surfaces",
    "semantic_carriers",
    "contract_excerpts",
}
OPEN_DECISION_SURFACE_RE = re.compile(
    r"\b(?:needs-decision|open|unknown|todo|tbd|blocked|TBD|TODO|待确认|未知|未决|阻塞)\b",
)
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
DECISION_SURFACE_ID_RE = re.compile(r"\bDS-\d{3}\b")
EXTERNAL_CAPABILITY_SIGNAL_RE = re.compile(
    r"\b(?:AWS|EC2|ASG|Auto\s*Scaling|Launch\s*Template|K8s|Kubernetes|Helm|Terraform|IAM|VPC|Subnet|"
    r"Security\s*Group|cloud\s+resource|cloud\s+api|provider|SDK|third[- ]party|external\s+(?:system|api|dependency)|"
    r"official\s+(?:doc|documentation|api)|autoscaling|auto[- ]?scaling|scheduling|lifecycle|runtime|metrics|logs|events|"
    r"no-cloud|repo-specific acceptance runtime|acceptance runtime|mock\s+external)\b|"
    r"云资源|云API|官方文档|官方接口|外部系统|外部依赖|第三方|自动伸缩|调度|生命周期|运行时|"
    r"指标|日志|事件|模拟外部|无云|验收",
    re.IGNORECASE,
)
EXTERNAL_RESEARCH_BLOCKED_RE = re.compile(
    r"\b(?:unread|unknown-blocking|open|todo|tbd|blocked|TBD|TODO|待确认|未知|未读|阻塞|未决)\b",
)
MECHANISM_UNRESOLVED_RE = re.compile(
    r"\b(?:TBD|TODO|tbd|todo|unknown|open|blocked|待确认|未知|未决|后续决定)\b",
)
EXTERNAL_FACT_ID_RE = re.compile(r"\b(?:FACT|EXT|CONSTRAINT|XCON)-\d{3}\b")
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
MOCK_ACCEPTANCE_PLANNING_STAGES = {"task-planning", "pre-execution"}
MOCK_ACCEPTANCE_EXECUTION_STAGES = {"all", "mock-acceptance", "product-acceptance"}
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
STATEFUL_MATRIX_COLUMNS = [
    "Operation",
    "Mode",
    "From state",
    "Trigger",
    "Event",
    "Status",
    "To state",
    "Terminal",
    "Failure",
    "Verification",
]
SUPERSEDED_REF_RE = re.compile(rf"\b(?:{DECISION_ID_PATTERN}|C-\d{{3}}|VER-\d{{3}}|T\d{{3}})\b")
VALID_STAGE_STATUS = set(WORKFLOW_STATE_MACHINE.get("valid_stage_statuses", []))

REVIEW_POLICY = {
    str(stage): dict(policy) if isinstance(policy, dict) else {}
    for stage, policy in dict(WORKFLOW_STATE_MACHINE.get("review_policy", {})).items()
}
MULTI_PERSPECTIVE_REVIEW_STAGES = {
    stage for stage, policy in REVIEW_POLICY.items() if policy.get("required") is True
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
MULTI_PERSPECTIVE_ALLOWED_STAGES = {
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
    "pre-execution",
    "execution",
    "mock-acceptance",
    "product-acceptance",
    "acceptance",
    "all",
    "convergence-retrospective",
} | set(MULTI_PERSPECTIVE_STAGE_ALIASES)
MULTI_PERSPECTIVE_ALLOWED_REVIEWER_TYPES = {"readonly-subagent", "read-only-subagent"}
MULTI_PERSPECTIVE_ALLOWED_DISPOSITIONS = {"accepted", "rejected", "deferred", "backflow-created", "superseded"}
MULTI_PERSPECTIVE_ALLOWED_SEVERITIES = {"blocker", "major", "minor", "question"}

WORKDIR_IDENTITY_ARTIFACT = "workflow-workdir.md"
PLAN_SNAPSHOT_STAGES = {
    str(item) for item in WORKFLOW_STATE_MACHINE.get("plan_snapshot_stages", [])
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
ISO_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})")

OPTIONAL_RECEIPT_ARTIFACTS = {
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
    "Task Merge Split Decision Matrix": [
        "Candidate rows",
        "Proposed Txxx",
        "Same primary module?",
        "Same semantic type?",
        "Same operation/surface?",
        "Same short verification?",
        "Decision",
        "Reason / backflow",
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
NOT_RUN_RE = re.compile(r"\bnot[_ -]?run|未运行|未执行|defer(?:red)?|后置|跳过\b", re.IGNORECASE)

TASK_EXECUTION_LOG_RE = re.compile(
    r"Atomic Execution Log|Verification Result|Fresh command|Fresh result|Local Review|"
    r"执行日志|验证结果|本地审计|Fresh Maven|reactor build success",
    re.IGNORECASE,
)

TERMINAL_TASK_STATUS_RE = re.compile(
    r"^\|\s*T\d{3}\s*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|\s*(?:passed|done|completed|完成)\s*\|",
    re.IGNORECASE | re.MULTILINE,
)

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


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def read_yaml(path: Path) -> dict:
    if yaml is None or not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_receipt_hash(receipt: dict) -> str:
    payload = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def workflow_profile_policy(workflow_state: dict) -> dict:
    manifest = read_yaml(WORKFLOW_RUNTIME_MANIFEST_PATH)
    profiles = manifest.get("profiles", {}) if isinstance(manifest.get("profiles"), dict) else {}
    workflow = workflow_state.get("workflow", {}) if isinstance(workflow_state.get("workflow"), dict) else {}
    profile = str(workflow.get("profile", "full")).strip() or "full"
    return profiles.get(profile, {}) if isinstance(profiles.get(profile), dict) else {}


def artifact_digest_map(change_dir: Path, stage: str) -> dict[str, str]:
    digests: dict[str, str] = {}
    rels = stage_receipt_artifact_rels(change_dir, stage) + list(OPTIONAL_RECEIPT_ARTIFACTS.get(stage, []))
    for rel in rels:
        path = change_dir / rel
        if path.exists():
            digests[rel] = (
                workflow_defects_stage_digest(path, stage)
                if rel == "workflow-defects.yaml"
                else artifact_receipt_digest(path, rel)
            )
    if stage in HUMAN_DECISION_REQUIRED_STAGES:
        for path in sorted((change_dir / "decision-bundles").glob("*.yaml")):
            if str(read_yaml(path).get("stage", "")).strip() != stage:
                continue
            rel = path.relative_to(change_dir).as_posix()
            digests[rel] = sha256_file(path)
    return digests


def workflow_defects_stage_digest(path: Path, stage: str) -> str:
    doc = read_yaml(path)
    stage_order = [str(item) for item in WORKFLOW_STATE_MACHINE.get("stage_order", [])]
    if stage not in stage_order:
        return sha256_file(path)
    stage_index = stage_order.index(stage)
    scoped = {
        str(defect_id): raw
        for defect_id, raw in (doc.get("defects", {}) or {}).items()
        if isinstance(raw, dict)
        and str(raw.get("should_have_caught_stage", "")).strip() in stage_order
        and stage_order.index(str(raw.get("should_have_caught_stage", "")).strip()) <= stage_index
    }
    payload = {"schema_version": doc.get("schema_version"), "defects": scoped}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def stage_receipt_artifact_rels(change_dir: Path, stage: str) -> list[str]:
    rels = list(STAGE_RECEIPT_REQUIRED_ARTIFACTS.get(stage, []))
    defect_path = change_dir / "workflow-defects.yaml"
    if defect_path.is_file():
        defect_doc = read_yaml(defect_path)
        stage_order = [str(item) for item in WORKFLOW_STATE_MACHINE.get("stage_order", [])]
        caught_stages = [
            str(raw.get("should_have_caught_stage", "")).strip()
            for raw in (defect_doc.get("defects", {}) or {}).values()
            if isinstance(raw, dict) and str(raw.get("should_have_caught_stage", "")).strip() in stage_order
        ]
        earliest = min(caught_stages, key=stage_order.index, default="")
        if not earliest or (stage in stage_order and stage_order.index(stage) >= stage_order.index(earliest)):
            rels.append("workflow-defects.yaml")
    if stage in PLAN_SNAPSHOT_STAGES:
        rels.append(f"stage-snapshots/{stage}-plan.md")
    return rels


def artifact_receipt_digest(path: Path, rel: str) -> str:
    if rel == WORKDIR_IDENTITY_ARTIFACT:
        body = path.read_text(encoding="utf-8", errors="replace")
        identity = re.split(r"^##+\s+Resume Verification\b", body, maxsplit=1, flags=re.MULTILINE)[0]
        return hashlib.sha256((identity.rstrip() + "\n").encode("utf-8")).hexdigest()
    return sha256_file(path)


def has_stateful_signal(value: str) -> bool:
    return bool(STATEFUL_SIGNAL_RE.search(value))


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


def command_output(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def markdown_table_values(markdown: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = split_markdown_table_row(stripped)
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


def validate_workdir_identity(change_dir: Path, workflow_state: dict) -> list[str]:
    errors: list[str] = []
    path = change_dir / WORKDIR_IDENTITY_ARTIFACT
    if not path.exists():
        errors.append(
            f"{change_dir}: missing {WORKDIR_IDENTITY_ARTIFACT}; "
            "create workdir identity before purpose.md/source-intake and verify it after context resume"
        )
        return errors

    body = read(path)
    identity_body = re.split(r"^##+\s+Resume Verification\b", body, maxsplit=1, flags=re.MULTILINE)[0]
    values = markdown_table_values(identity_body)
    required = [
        "worktree path", "change dir absolute path", "change id", "branch name",
        "base branch", "base commit", "base source mode", "git top level",
    ]
    for key in required:
        if not text(values.get(key)):
            errors.append(f"{path}: Canonical Workdir missing {key}")

    actual_change_dir = canonical_resolve(change_dir.as_posix())
    recorded_change_dir = canonical_resolve(text(values.get("change dir absolute path")))
    if recorded_change_dir and recorded_change_dir != actual_change_dir:
        errors.append(f"{path}: change dir mismatch; expected {recorded_change_dir}, actual {actual_change_dir}")

    recorded_change_id = text(values.get("change id"))
    if recorded_change_id and recorded_change_id != change_dir.name:
        errors.append(f"{path}: change id mismatch; expected {recorded_change_id}, actual {change_dir.name}")

    repo_root = git_root_for(change_dir)
    actual_repo_root = canonical_resolve(repo_root.as_posix()) if repo_root else ""
    for label in ["worktree path", "git top level"]:
        recorded = canonical_resolve(text(values.get(label)))
        if recorded and actual_repo_root and recorded != actual_repo_root:
            errors.append(f"{path}: {label} mismatch; expected {recorded}, actual {actual_repo_root}")

    actual_branch = command_output(["git", "-C", str(repo_root), "branch", "--show-current"]) if repo_root else ""
    recorded_branch = text(values.get("branch name"))
    if recorded_branch and actual_branch and recorded_branch != actual_branch:
        errors.append(f"{path}: branch mismatch; expected {recorded_branch}, actual {actual_branch}")

    recorded_base = text(values.get("base commit"))
    base_branch = text(values.get("base branch"))
    base_source_mode = text(values.get("base source mode"))
    if base_source_mode not in {"fetched-remote", "pinned-commit", "local-only"}:
        errors.append(f"{path}: base source mode is invalid: {base_source_mode or '<empty>'}")
    if base_branch.startswith("origin/"):
        if base_source_mode != "fetched-remote":
            errors.append(f"{path}: origin base requires base source mode=fetched-remote")
        if text(values.get("remote oid")) != recorded_base:
            errors.append(f"{path}: Remote OID must equal Base commit for an origin base")
        if not ISO_TIMESTAMP_RE.fullmatch(text(values.get("remote fetched at"))):
            errors.append(f"{path}: Remote fetched at must be an ISO-8601 timestamp for an origin base")
        if "git fetch" not in text(values.get("fetch command evidence")):
            errors.append(f"{path}: Fetch command evidence must record git fetch for an origin base")

    workflow = workflow_state.get("workflow", {}) if isinstance(workflow_state.get("workflow"), dict) else {}
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
                errors.append(f"{change_dir}: workflow-state.yaml workflow.{state_key} does not match {WORKDIR_IDENTITY_ARTIFACT} {identity_key}")
        elif state_value and identity_value and state_value != identity_value:
            errors.append(f"{change_dir}: workflow-state.yaml workflow.{state_key} does not match {WORKDIR_IDENTITY_ARTIFACT} {identity_key}")

    if not re.search(r"^##+\s+Resume Verification\b", body, re.MULTILINE):
        errors.append(f"{path}: missing Resume Verification section")
    return errors


def validate_subagent_execution_proof(container: dict, context: str) -> list[str]:
    errors: list[str] = []
    proof = container.get("subagent_execution", {}) if isinstance(container.get("subagent_execution"), dict) else {}
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


def git_changed_paths(repo_root: Path) -> set[str]:
    changed: set[str] = set()
    for command in [
        ["git", "-C", str(repo_root), "diff", "--name-only"],
        ["git", "-C", str(repo_root), "diff", "--cached", "--name-only"],
        ["git", "-C", str(repo_root), "ls-files", "--others", "--exclude-standard"],
    ]:
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


def changed_paths_relative_to_change(change_dir: Path) -> set[str]:
    repo_root = git_root_for(change_dir)
    if repo_root is None:
        return set()
    try:
        change_rel = change_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return set()
    prefix = f"{change_rel}/"
    return {
        path[len(prefix):]
        for path in git_changed_paths(repo_root)
        if path.startswith(prefix)
    }


def headings(markdown: str) -> set[str]:
    found: set[str] = set()
    for line in markdown.splitlines():
        match = re.match(r"^#{2,}\s+(.+?)\s*$", line)
        if match:
            found.add(match.group(1).strip())
    return found


def heading_options(spec: str) -> list[str]:
    return [item.strip() for item in spec.split("|")]


def has_any_heading(present: set[str], spec: str) -> bool:
    return any(option in present for option in heading_options(spec))


def first_existing_section(markdown: str, *names: str) -> str:
    for name in names:
        found = section(markdown, name)
        if found:
            return found
    return ""


def all_existing_sections(markdown: str, *names: str) -> list[str]:
    found: list[str] = []
    for name in names:
        pattern = re.compile(rf"^##+\s+{re.escape(name)}\s*$", re.MULTILINE)
        for match in pattern.finditer(markdown):
            start = match.end()
            level = re.match(r"^(##+)", match.group(0)).group(1)
            next_match = re.search(rf"^{re.escape(level)}\s+", markdown[start:], re.MULTILINE)
            end = start + next_match.start() if next_match else len(markdown)
            found.append(markdown[start:end])
    return found


def first_section_with_columns(markdown: str, names: list[str], columns: list[str]) -> str:
    fallback = ""
    for found in all_existing_sections(markdown, *names):
        if not fallback:
            fallback = found
        if has_table_columns(found, columns):
            return found
    return fallback


def ids(pattern: str, text: str) -> set[str]:
    return set(re.findall(pattern, text))


def design_object_ids(text: str) -> set[str]:
    decision_ids = {item for item in DECISION_ID_RE.findall(text) if not item.startswith("PDEC-")}
    return decision_ids | set(EXTERNAL_DESIGN_OBJECT_ID_RE.findall(text))


AIP_SECTION_PATTERNS = [
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
    for row in table_dicts(markdown):
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


def has_table_columns(section_text: str, columns: list[str]) -> bool:
    normalized = section_text.lower()
    return all(col.lower() in normalized for col in columns)


def has_any_pattern(section_text: str, *patterns: str) -> bool:
    return any(re.search(pattern, section_text, re.IGNORECASE) for pattern in patterns)


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


def split_markdown_table_row(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|") and not value.endswith(r"\|"):
        value = value[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    in_code = False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            current.append(char)
            continue
        if char == "`":
            in_code = not in_code
            current.append(char)
            continue
        if char == "|" and not in_code:
            cells.append("".join(current).strip().strip("`"))
            current = []
            continue
        current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip().strip("`"))
    return cells


def markdown_tables(section_text: str) -> list[tuple[list[str], list[list[str]]]]:
    lines = section_text.splitlines()
    tables: list[tuple[list[str], list[list[str]]]] = []
    index = 0
    while index + 1 < len(lines):
        header_line = lines[index].strip()
        separator_line = lines[index + 1].strip()
        if not (header_line.startswith("|") and header_line.endswith("|")):
            index += 1
            continue
        if not (separator_line.startswith("|") and separator_line.endswith("|")):
            index += 1
            continue
        headers = split_markdown_table_row(header_line)
        separators = split_markdown_table_row(separator_line)
        if len(headers) != len(separators) or not separators or not all(
            re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in separators
        ):
            index += 1
            continue
        rows: list[list[str]] = []
        index += 2
        while index < len(lines):
            data_line = lines[index].strip()
            if not (data_line.startswith("|") and data_line.endswith("|")):
                break
            rows.append(split_markdown_table_row(data_line))
            index += 1
        tables.append((headers, rows))
    return tables


def table_rows(section_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for headers, data in markdown_tables(section_text):
        rows.append(headers)
        rows.extend(data)
    return rows


def table_dicts(section_text: str) -> list[dict[str, str]]:
    data: list[dict[str, str]] = []
    for raw_headers, rows in markdown_tables(section_text):
        headers = [cell.strip() for cell in raw_headers]
        for row in rows:
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))
            mapped = {headers[idx]: row[idx].strip() for idx in range(len(headers))}
            if any(value for value in mapped.values()):
                data.append(mapped)
    return data


def markdown_table_column_count_errors(section_text: str, columns: list[str], artifact: str) -> list[str]:
    normalized_columns = {re.sub(r"[^a-z0-9]+", "", column.lower()) for column in columns}
    errors: list[str] = []
    for headers, rows in markdown_tables(section_text):
        normalized_row = {re.sub(r"[^a-z0-9]+", "", cell.lower()) for cell in headers}
        if not normalized_columns <= normalized_row:
            continue
        expected = len(headers)
        for row_number, row in enumerate(rows, start=1):
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


def flatten_text(value) -> str:
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    if value is None:
        return ""
    return str(value).strip()


def validate_mechanism_design_closure(change_dir: Path, aip: str, artifact: str) -> list[str]:
    errors: list[str] = []
    body = first_existing_section(aip, "Mechanism-Level Design Closure Matrix", "机制级设计闭合矩阵")
    if not body:
        errors.append(f"{change_dir}: missing Mechanism-Level Design Closure Matrix")
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
    if not has_table_columns(body, columns):
        errors.append(f"{artifact}: Mechanism-Level Design Closure Matrix must include columns {', '.join(columns)}")
    rows = table_dicts(body)
    if not rows:
        errors.append(f"{artifact}: Mechanism-Level Design Closure Matrix must include concrete rows")
        return errors
    blocked_re = re.compile(r"\b(?:TBD|TODO|unknown-blocking|open|blocked|后续|待定|待确认|再决定|task-planning)\b", re.IGNORECASE)
    weak_question_re = re.compile(r"^(?:support|支持|实现|enable|ability|capability|能力|方案|design)\b|^(?:ASG|K8s|HPA|autoscaling|runtime)$", re.IGNORECASE)
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
        for column, min_len in [
            ("Selected mechanism", 16),
            ("Rejected alternatives", 12),
            ("Current code evidence", 8),
            ("Interface impact", 8),
            ("State/runtime impact", 8),
            ("Failure behavior", 8),
            ("Verification", 5),
            ("Downstream C/VER", 3),
        ]:
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


def validate_aip_narrative_materialization(change_dir: Path, aip: str, design_sources: str, artifact: str) -> list[str]:
    errors: list[str] = []
    body = first_existing_section(aip, "AIP Narrative Materialization Gate", "AIP 正文物化门禁")
    if not body:
        errors.append(f"{change_dir}: missing AIP Narrative Materialization Gate")
        return errors
    columns = ["Source design object", "Must appear in AIP section", "Narrative requirement", "Status"]
    if not has_table_columns(body, columns):
        errors.append(f"{artifact}: AIP Narrative Materialization Gate must include columns {', '.join(columns)}")
    rows = table_dicts(body)
    if not rows:
        errors.append(f"{artifact}: AIP Narrative Materialization Gate must include concrete rows")
        return errors
    aip_text_without_gate = aip.replace(body, "")
    for row in rows:
        joined = " | ".join(row.values())
        row_ids = design_object_ids(table_get(row, "Source design object") or joined)
        status = table_get(row, "Status")
        if not re.search(r"\b(?:materialized|locked n/a|n/a|not applicable|不适用|blocked)\b", status, re.IGNORECASE):
            errors.append(f"{artifact}: AIP Narrative Materialization Gate row has invalid status: {joined}")
        if re.search(r"\bblocked\b|阻塞", status, re.IGNORECASE):
            errors.append(f"{artifact}: AIP Narrative Materialization Gate contains blocked row: {joined}")
        if len(table_get(row, "Must appear in AIP section")) < 4:
            errors.append(f"{artifact}: narrative materialization row lacks AIP section: {joined}")
        if len(table_get(row, "Narrative requirement")) < 16:
            errors.append(f"{artifact}: narrative materialization row lacks concrete narrative requirement: {joined}")
        if re.search(r"\bmaterialized\b", status, re.IGNORECASE):
            target_section = aip_sections_for_reference(aip, table_get(row, "Must appear in AIP section"))
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
    for row in table_dicts(markdown):
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


def validate_mechanism_design_model(change_dir: Path, stage: str, proposal: str, spec: str, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "aip", "readiness", "design", "archaeology", "contract", "frontend-contract", "verification", "task-planning", "pre-execution"}:
        return errors
    combined = "\n".join(
        [
            proposal,
            spec,
            plan,
            tasks,
            read(change_dir / "aip.md"),
            read(change_dir / "external-capability-research.md"),
            read(change_dir / "decision-surface-discovery.md"),
        ]
    )
    has_trigger = bool(EXTERNAL_CAPABILITY_SIGNAL_RE.search(combined)) or bool(
        re.search(
            r"\b(?:progress|change|event|runtime materialization|resource lifecycle|failure consistency|HPA|ASG|autoscaling|metrics source)\b"
            r"|进度|变更|事件|运行时物化|资源生命周期|失败一致性|自动扩缩|指标来源",
            combined,
            re.IGNORECASE,
        )
    )
    path = change_dir / "mechanism-design-model.md"
    body = read(path)
    if has_trigger and not body.strip():
        errors.append(f"{path}: mechanism-level implementation signal exists but mechanism-design-model.md is missing or empty")
        return errors
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
        section_body = first_existing_section(body, section_name)
        if not section_body:
            errors.append(f"{path}: missing {section_name}")
            continue
        if not has_table_columns(section_body, columns):
            errors.append(f"{path}: {section_name} must include columns {', '.join(columns)}")
        rows = table_dicts(section_body)
        if not rows:
            errors.append(f"{path}: {section_name} must include concrete rows or locked N/A rows")
            continue
        for row in rows:
            joined = " | ".join(row.values())
            if MECHANISM_UNRESOLVED_RE.search(joined):
                errors.append(f"{path}: {section_name} contains unresolved implementation decision: {joined}")
            if MECHANISM_PLACEHOLDER_RE.search(joined):
                errors.append(f"{path}: {section_name} contains template placeholder/generic mechanism text: {joined}")

    weak_re = re.compile(
        r"^\s*(?:support|支持|实现|enable|reuse|复用|use existing|same as existing|create resource|record event|provider call|mode-specific|能力|资源创建|记录事件|调用provider)\s*$",
        re.IGNORECASE,
    )
    for row in table_dicts(first_existing_section(body, "Mechanism Row Inventory")):
        joined = " | ".join(row.values())
        row_id = table_get(row, "Mechanism row")
        if not re.search(r"\bMECH-\d{3}\b", row_id):
            errors.append(f"{path}: Mechanism Row Inventory row must use MECH-xxx id: {joined}")
        operation = table_get(row, "Operation / surface")
        if not re.search(r"\b(create|update|delete|readback|validate|submit|scale|autoscaling|policy|metrics?|logs?|runtime|materiali[sz]e|cleanup|protect|failure|event|progress)\b|创建|更新|删除|读回|校验|提交|扩缩|策略|指标|日志|运行时|物化|清理|保护|失败|事件|进度", operation, re.IGNORECASE):
            errors.append(f"{path}: {row_id or '<missing>'} operation/surface is not concrete: {operation or '<missing>'}")
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
                errors.append(f"{path}: {row_id or '<missing>'} has weak {column}: {value or '<empty>'}")
        evidence = table_get(row, "Current code evidence")
        if evidence and not re.search(r"(?:/|\\|\.java|\.ts|\.tsx|\.go|\.py|\.yaml|\.yml|\.tf|rg |grep |mvn |pnpm |npm |curl )", evidence):
            errors.append(f"{path}: {row_id or '<missing>'} Current code evidence must include path or command: {evidence}")
        if not re.search(r"\b(?:C|VER)-\d{3}\b", table_get(row, "Downstream C/VER")):
            errors.append(f"{path}: {row_id or '<missing>'} must map to downstream C/VER")

    mechanism_ids = {mid for mid in re.findall(r"\bMECH-\d{3}\b", body)}
    for mech_id in sorted(mechanism_ids):
        references = len(re.findall(rf"\b{re.escape(mech_id)}\b", body))
        if references < 3:
            errors.append(f"{path}: {mech_id} is not propagated into design model detail rows")

    if stage in {"contract", "verification", "task-planning", "pre-execution", "all"}:
        downstream = "\n".join([plan, tasks, read(change_dir / "contracts.yaml"), read(change_dir / "verification.yaml"), read(change_dir / "atomic-task-decomposition.md"), read(change_dir / "atomic-issue-packets.yaml")])
        for model_id in sorted(implementation_affecting_mechanism_ids(body)):
            if not re.search(rf"\b{re.escape(model_id)}\b", downstream):
                errors.append(f"{path}: mechanism design row {model_id} is not consumed by contract/verification/task artifacts")
    if stage in {"task-planning", "pre-execution", "all"}:
        decomposition = read(change_dir / "atomic-task-decomposition.md")
        if "Mechanism Row To Task Map" not in decomposition:
            errors.append(f"{change_dir / 'atomic-task-decomposition.md'}: missing Mechanism Row To Task Map")
        packets = read(change_dir / "atomic-issue-packets.yaml")
        for required in ["MECH-", "OPSEQ-", "EXTAPI-", "EVT-", "RMM-", "RLM-", "FCM-", "MIM-"]:
            if required in body and required not in packets:
                errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: must carry {required.rstrip('-')} mechanism semantics into owner packets")
    return errors


def component_paths(value) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for match in FRONTEND_COMPONENT_PATH_RE.finditer(flatten_text(value)):
        path = match.group(1).strip().strip("`").strip(",.;")
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def path_in_allowlist(path: str, allowlist: list[str]) -> bool:
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


def issue_markdown_text(change_dir: Path, task_id: str, packet: dict) -> str:
    issue_path = str(packet.get("issue_path") or f"atomic-issues/{task_id}.md").strip()
    return read(change_dir / issue_path)


def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def salient_terms(value: str) -> list[str]:
    raw_terms = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u3400-\u9fff]{2,}", value)
    stop = {"must", "should", "with", "without", "field", "fields", "display", "create", "page", "mode"}
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


def is_generic_packet_text(value: str) -> bool:
    return bool(GENERIC_PACKET_TEXT_RE.search(str(value)))


def non_empty_data_rows(section_text: str) -> list[list[str]]:
    rows = table_rows(section_text)
    data: list[list[str]] = []
    for row in rows:
        joined = " ".join(row).strip().lower()
        if not joined:
            continue
        if any(
            cell.lower()
            in {
                "source",
                "module",
                "item",
                "contract",
                "interaction / contract",
                "req/scn",
                "action id",
                "edge id",
                "txxx",
                "candidate rows",
            }
            for cell in row[:1]
        ):
            continue
        if all(not cell.strip() for cell in row):
            continue
        data.append(row)
    return data


def has_meaningful_rows(section_text: str) -> bool:
    placeholders = re.compile(r"^(?:|n/a|none|tbd|todo|unknown|<.*>|\s+)$", re.IGNORECASE)
    for row in non_empty_data_rows(section_text):
        meaningful = [cell for cell in row if not placeholders.fullmatch(cell.strip())]
        if len(meaningful) >= 2:
            return True
    return False


def contract_ids_from_text(markdown: str) -> set[str]:
    return set(re.findall(r"\bC-\d{3}\b", markdown))


def locked_na(value: str) -> bool:
    return bool(re.fullmatch(r"(?:N/A|not applicable|不适用|locked N/A|locked-na|locked not applicable)", value.strip(), re.IGNORECASE))


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
    r"consumer\s+assumption|verification\s+proof|proof[- ]?only|carrier[- ]?only|locked\s+N/A|locked-na|not applicable|N/A|不适用",
    re.IGNORECASE,
)


def normalize_contract_edge_type(value: str) -> str:
    return re.sub(r"[\s-]+", "_", cell_text(value).strip().lower())


def is_contract_edge_type_value(value: str) -> bool:
    return normalize_contract_edge_type(value) in CONTRACT_EDGE_TYPE_CANONICAL_VALUES


def contract_provider_module_is_multi_owner(value: str) -> bool:
    cleaned = cell_text(value)
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


def executable_obligation_row_too_thin(row: dict[str, str]) -> bool:
    joined = flatten_text(row)
    if not joined:
        return True
    if is_generic_packet_text(joined):
        return True
    payload_fields = [
        table_get(row, "Edge"),
        table_get(row, "Edge type"),
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
    if len(CJK_RE.findall(joined)) < 20 and len(re.findall(r"[A-Za-z][A-Za-z0-9_.:/-]{3,}", joined)) < 10:
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
    value = flatten_text(value).strip()
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
        body = read(change_dir / rel)
        if not body.strip():
            continue
        for row in table_dicts(first_existing_section(body, section_name)):
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
                f"{change_dir / 'plan.md'}: Contract Executable Obligation Matrix must consume {rel} row {row_id}"
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
OBLIGATION_ROW_ID_RE = re.compile(
    r"\b(?:C-\d{3}-OBL-\d{3}|ESE-\d{3}|PCP?-\d{3}|RMM-\d{3}|RMP-\d{3}|VIM-\d{3}|UI-ACT-\d{3})\b"
)
CONTRACT_OR_OBLIGATION_ID_RE = re.compile(r"\bC-\d{3}(?:-OBL-\d{3})?\b")
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


def obligation_id_is_coarse_contract(value: str) -> bool:
    return bool(COARSE_CONTRACT_ID_RE.fullmatch(str(value or "").strip()))


def canonical_provider_ref(value: str) -> bool:
    raw = cell_text(value)
    if not raw or locked_na(raw):
        return False
    return bool(re.fullmatch(r"C-\d{3}", raw) or OBLIGATION_ROW_ID_RE.fullmatch(raw))


def row_is_semantic_provider(row: dict[str, str]) -> bool:
    row_kind = table_get(row, "Sub-obligation type") or table_get(row, "Row kind")
    edge_type = table_get(row, "Edge type")
    if CARRIER_EDGE_TYPE_RE.search(edge_type):
        return False
    return bool(
        PROVIDER_OWNED_EDGE_TYPE_RE.search(edge_type)
        and PROVIDER_ROW_KIND_RE.search(row_kind)
        and not NON_PROVIDER_ROW_KIND_RE.search(row_kind)
    )


def semantic_provider_obligation_ids_by_contract(rows_by_id: dict[str, dict[str, str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for row_id, row in rows_by_id.items():
        if row_is_semantic_provider(row):
            contract_id = obligation_contract_id(row) or contract_base_id(row_id)
            if contract_id:
                result.setdefault(contract_id, set()).add(row_id)
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


def provider_claim_refs(value) -> set[str]:
    claims: set[str] = set()
    raw = flatten_text(value)
    for chunk in re.split(r"(?:\n|<br\s*/?>|[.;。；])", raw, flags=re.IGNORECASE):
        if not CONTRACT_OR_OBLIGATION_ID_RE.search(chunk):
            continue
        if PROVIDER_CLAIM_LANGUAGE_RE.search(chunk) and not NON_PROVIDER_CLAIM_LANGUAGE_RE.search(chunk):
            claims.update(CONTRACT_OR_OBLIGATION_ID_RE.findall(chunk))
    return claims


def cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def normalize_contract_obligation_row(contract_id: str, row: dict) -> dict[str, str]:
    obligation_id = cell_text(
        row.get("obligation_id")
        or row.get("sub_obligation_id")
        or row.get("Sub-obligation ID")
        or row.get("id")
    )
    normalized = {
        "Contract": contract_id,
        "Sub-obligation ID": obligation_id,
        "Edge": cell_text(row.get("edge") or row.get("Edge")),
        "Edge type": cell_text(row.get("edge_type") or row.get("Edge type")),
        "Sub-obligation type": cell_text(row.get("row_kind") or row.get("sub_obligation_type") or row.get("Sub-obligation type")),
        "Semantic type": cell_text(row.get("semantic_type") or row.get("Semantic type")),
        "Operation / surface": cell_text(row.get("operation_surface") or row.get("operation") or row.get("Operation / surface")),
        "Canonical owner": cell_text(row.get("canonical_owner") or row.get("Canonical owner")),
        "Fields/resource/state": cell_text(row.get("fields_resource_state") or row.get("fields") or row.get("Fields/resource/state")),
        "Provider guarantee": cell_text(row.get("provider_guarantee") or row.get("Provider guarantee")),
        "Consumer assumption": cell_text(row.get("consumer_assumption") or row.get("Consumer assumption")),
        "Failure / timing detail": cell_text(row.get("failure_timing_detail") or row.get("failure_timing") or row.get("Failure / timing detail")),
        "State/resource owner": cell_text(row.get("state_resource_owner") or row.get("state_owner") or row.get("State/resource owner")),
        "Owner module": cell_text(
            row.get("owner_module")
            or row.get("Owner module")
            or row.get("suggested_owner_module")
            or row.get("Suggested owner module")
            or row.get("canonical_owner_module")
        ),
        "Suggested owner module": cell_text(row.get("suggested_owner_module") or row.get("Suggested owner module")),
        "Verification proof": flatten_text(row.get("verification") or row.get("verification_proof") or row.get("Verification proof")),
        "Split hint": cell_text(row.get("split_hint") or row.get("Split hint")),
    }
    normalized["_obligation_id"] = obligation_id
    normalized["_obligation_group_id"] = obligation_id
    normalized["_row_id_aliases"] = obligation_id
    normalized["_row_text"] = flatten_text(row)
    return normalized


def contract_obligation_rows_from_yaml(change_dir: Path) -> list[dict[str, str]]:
    doc = read_yaml(change_dir / "contracts.yaml")
    rows: list[dict[str, str]] = []
    for contract_id, raw_contract in as_dict(doc.get("contracts")).items():
        contract = as_dict(raw_contract)
        for raw_row in as_list(contract.get("executable_obligations") or contract.get("obligations")):
            row = normalize_contract_obligation_row(str(contract_id), as_dict(raw_row))
            if not cell_text(row.get("Sub-obligation ID")) or obligation_row_locked_na(row):
                continue
            rows.append(row)
    return rows


def active_contract_obligation_rows(change_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = contract_obligation_rows_from_yaml(change_dir)
    plan = read(change_dir / "plan.md")
    executable = first_existing_section(
        plan,
        "Contract Executable Obligation Matrix",
        "Contract Executable Obligations",
        "契约可执行子义务矩阵",
    )
    for row in table_dicts(executable):
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


def contract_base_id(value: str) -> str:
    raw = cell_text(value)
    if re.fullmatch(r"C-\d{3}", raw):
        return raw
    match = re.match(r"^(C-\d{3})-OBL-\d{3}$", raw)
    return match.group(1) if match else ""


def obligation_contract_id(row: dict[str, str]) -> str:
    return cell_text(table_get(row, "Contract") or contract_base_id(table_get(row, "Sub-obligation ID")))


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
        str(value or "").strip()
        for value in payloads
        if str(value or "").strip()
        and not locked_na(str(value or "").strip())
        and len(str(value or "").strip()) >= 8
    ]
    if not meaningful:
        return True
    hits = sum(1 for value in meaningful if semantic_payload_copied(value, target_text))
    return hits >= min(len(meaningful), 3)


def normalized_owner_tokens(value: str) -> set[str]:
    raw = str(value or "").strip()
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
    expected_text = str(expected or "").strip().upper()
    actual_text = str(actual or "").strip().upper()
    return bool(expected_tokens & actual_tokens) and (expected_text in actual_text or actual_text in expected_text)


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


def cells_contain(row: list[str], *patterns: str) -> bool:
    text = " | ".join(row)
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def section_contains_blocking_not_run(section_text: str) -> bool:
    for row in table_rows(section_text):
        joined = " | ".join(row)
        if re.search(r"\b(P0|P1)\b", joined, re.IGNORECASE):
            return True
        if re.search(r"\bBlocks done\b\s*\|?\s*(yes|true)|阻塞完成\s*\|?\s*是", joined, re.IGNORECASE):
            return True
    return False


def status_rows_with(section_text: str, status_patterns: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table_rows(section_text):
        joined = " | ".join(row)
        if any(re.search(pattern, joined, re.IGNORECASE) for pattern in status_patterns):
            rows.append(row)
    return rows


def extract_superseded_objects(markdown: str) -> set[str]:
    superseded: set[str] = set()
    for row in table_rows(markdown):
        joined = " | ".join(row)
        if row and re.search(r"^Supersedes\s*/\s*superseded by$", row[0], re.IGNORECASE):
            continue
        if re.search(r"\bsuperseded\b|已废弃|被替代", joined, re.IGNORECASE):
            for match in SUPERSEDED_REF_RE.findall(joined):
                superseded.add(match)
    return superseded


def prose_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    in_fence = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line:
            continue
        if line.startswith("|") or line.startswith("!") or line.startswith("http"):
            continue
        line = re.sub(r"`[^`]+`", "", line)
        line = re.sub(r"https?://\S+", "", line)
        if line:
            lines.append(line)
    return lines


def mostly_non_chinese(markdown: str) -> bool:
    text = "\n".join(prose_lines(markdown))
    cjk = len(CJK_RE.findall(text))
    latin = len(LATIN_WORD_RE.findall(text))
    # Code-heavy short docs are handled by other checks; this catches English
    # narrative artifacts while allowing mixed Chinese with code identifiers.
    return latin >= 30 and cjk < 20


def heading_ids(markdown: str) -> set[str]:
    found: set[str] = set()
    for line in markdown.splitlines():
        match = re.match(r"^###\s+(.+?)\s*$", line)
        if match:
            found.update(DECISION_ID_RE.findall(match.group(1)))
    return found


def summary_decision_ids(markdown: str) -> set[str]:
    summary = first_existing_section(markdown, "决策摘要", "Decision Summary")
    found: set[str] = set()
    for row in table_rows(summary):
        if not row:
            continue
        first = row[0]
        if first.lower() == "id":
            continue
        found.update(DECISION_ID_RE.findall(first))
    return found


def validate_atomic_issue(path: Path) -> list[str]:
    text = read(path)
    errors: list[str] = []
    if not text.strip():
        return [f"{path}: empty or missing"]

    present = headings(text)
    for heading in REQUIRED_ISSUE_HEADINGS:
        if not has_any_heading(present, heading):
            errors.append(f"{path}: missing heading ## {heading_options(heading)[-1]}")

    if mostly_non_chinese(text):
        errors.append(f"{path}: main narrative appears to be English; AutoMQ workflow artifacts must default to Chinese")

    verification = first_existing_section(text, "验证", "Verification")
    if verification and not has_table_columns(verification, ["Expected result", "Proves", "Failure meaning"]):
        errors.append(f"{path}: Verification must include Expected result, Proves, and Failure meaning / Not Run risk columns")

    source_context = first_existing_section(text, "来源上下文", "Source Context")
    if source_context and re.search(r"\|\s*(REQ|SCN|DEC|C|MIG)-\w+\s*\|\s*\|", source_context):
        errors.append(f"{path}: Source Context appears to list IDs without excerpts")
    if source_context:
        source_ids = SOURCE_ID_RE.findall(source_context)
        cjk = len(CJK_RE.findall(source_context))
        if source_ids and cjk < max(30, len(source_ids) * 12):
            errors.append(f"{path}: Source Context is too thin; copy concrete source semantics, not just IDs or short summaries")
        if re.search(r"^\s*-\s*(?:REQ|SCN|C|MIG|PDEC|ADEC|DEC)-\d{3}\s*:", source_context, re.MULTILINE):
            errors.append(f"{path}: Source Context uses ID bullet summaries; use excerpt table with implementation-relevant semantics")

    contracts = first_existing_section(text, "契约摘录", "Contract Excerpts")
    if contracts and not has_table_columns(contracts, ["Trigger", "Normal path", "Failure path", "Consistency", "Timing", "Verification"]):
        errors.append(f"{path}: Contract Excerpts must include Trigger, Normal path, Failure path, Consistency, Timing, and Verification")
    if contracts and not has_meaningful_rows(contracts):
        errors.append(f"{path}: Contract Excerpts has no meaningful data rows")

    preconditions = first_existing_section(text, "执行前提", "Execution Preconditions")
    if preconditions:
        if not has_table_columns(preconditions, ["Already true", "Evidence", "If false"]):
            errors.append(f"{path}: Execution Preconditions must include Already true, Evidence, and If false")
        if re.search(r"\|\s*(?:T\d{3}|C-\d{3})\s*\|\s*(?:T\d{3}\s+completed|completed|done|完成)\s*\|", preconditions, re.IGNORECASE):
            errors.append(f"{path}: Execution Preconditions uses task completion instead of already-true facts")
        if not has_any_pattern(preconditions, r"backflow", r"回流", r"blocked", r"阻塞", r"stop", r"停止"):
            errors.append(f"{path}: Execution Preconditions must say what to do if the precondition is false")

    consumed_snapshot = first_existing_section(text, "Consumed Contract Snapshot")
    if consumed_snapshot:
        if not has_table_columns(consumed_snapshot, ["Provider", "This task may assume", "Field/state/error/timing", "Forbidden interpretation"]):
            errors.append(f"{path}: Consumed Contract Snapshot must include Provider, This task may assume, Field/state/error/timing details, and Forbidden interpretation")
        if not has_meaningful_rows(consumed_snapshot):
            errors.append(f"{path}: Consumed Contract Snapshot has no meaningful data rows")
        if re.search(r"\|\s*C-\d{3}\s*\|\s*[^|\n]*\|\s*(?:[^|\n]{0,20})\s*\|", consumed_snapshot) and len(CJK_RE.findall(consumed_snapshot)) < 30:
            errors.append(f"{path}: Consumed Contract Snapshot appears ID-only or too thin; copy executable contract facts")

    provided_obligation = first_existing_section(text, "Provided Contract Obligation")
    if provided_obligation:
        if not has_table_columns(provided_obligation, ["Downstream consumer", "This task must guarantee", "Observable output", "Verification proving"]):
            errors.append(f"{path}: Provided Contract Obligation must include Downstream consumer, guarantee, observable output/state, and verification proving it")
        if not has_meaningful_rows(provided_obligation):
            errors.append(f"{path}: Provided Contract Obligation has no meaningful data rows")

    invariant_carryover = first_existing_section(text, "Invariant Carryover")
    if invariant_carryover:
        if not has_table_columns(invariant_carryover, ["Invariant", "Source", "Must remain true", "Regression check"]):
            errors.append(f"{path}: Invariant Carryover must include invariant, source, must-remain-true behavior, and regression check")

    precondition_failure = first_existing_section(text, "Preconditions Failure Handling")
    if precondition_failure:
        if not has_table_columns(precondition_failure, ["Failure", "Classification", "Required backflow", "Do not do"]):
            errors.append(f"{path}: Preconditions Failure Handling must include Failure, Classification, Required backflow, and Do not do")
        if not has_any_pattern(precondition_failure, r"backflow", r"回流", r"contract-materialization-gap", r"atomic-issue-not-self-contained"):
            errors.append(f"{path}: Preconditions Failure Handling must classify missing preconditions/materialization as a backflow gap")

    module_closure = first_existing_section(text, "模块契约闭包", "Module Contract Closure")
    if module_closure and not has_table_columns(
        module_closure,
        ["Primary module", "Consumed contracts", "Provided contracts"],
    ):
        errors.append(f"{path}: Module Contract Closure must include Primary module, Consumed contracts, and Provided contracts")
    if module_closure and re.search(r"\|\s*(Primary module|Consumed contracts assumed true|Provided contracts implemented/preserved)\s*\|\s*\|", module_closure):
        errors.append(f"{path}: Module Contract Closure has empty primary/consumed/provided contract fields")
    if module_closure and re.search(
        r"\|\s*(Primary module|Consumed contracts assumed true|Provided contracts implemented/preserved)\s*\|\s*(?:TBD|TODO|unknown|<.*?>)\s*\|",
        module_closure,
        re.IGNORECASE,
    ):
        errors.append(f"{path}: Module Contract Closure still contains placeholder primary/consumed/provided values")

    files = first_existing_section(text, "修改文件", "Files To Change")
    if files and VAGUE_SCOPE_RE.search(files):
        errors.append(f"{path}: Files To Change contains vague/open-ended scope; use exact paths or precise new-file rules")

    steps = first_existing_section(text, "实现步骤", "Implementation Steps")
    if steps and re.search(r"\b(?:according to|as needed|if needed|where appropriate|choose|decide|参考.+即可)\b", steps, re.IGNORECASE):
        errors.append(f"{path}: Implementation Steps appear to leave choices to the implementer")

    if re.search(r"\b(?:Decision Registry|完整\s*plan|full\s+plan|see\s+plan|见\s*plan|见\s*Decision Registry)\b", text, re.IGNORECASE):
        errors.append(f"{path}: references global docs for necessary semantics; copy required semantics into the issue")

    if "TBD" in text or "TODO" in text:
        errors.append(f"{path}: contains TBD/TODO")

    return errors


def validate_stage_decision_doc(path: Path) -> list[str]:
    text = read(path)
    errors: list[str] = []
    if not text.strip():
        return [f"{path}: empty or missing"]

    present = headings(text)
    for heading in REQUIRED_DECISION_HEADINGS:
        if not has_any_heading(present, heading):
            errors.append(f"{path}: missing heading ## {heading_options(heading)[-1]}")

    if mostly_non_chinese(text):
        errors.append(f"{path}: main narrative appears to be English; decision documents must default to Chinese")

    summary = first_existing_section(text, "决策摘要", "Decision Summary")
    if summary and not has_table_columns(summary, ["ID", "Type", "Question", "Final decision", "Decided by", "Status"]):
        errors.append(f"{path}: Decision Summary must include ID, Type, Question, Final decision, Decided by, Status")
    if summary and not has_any_pattern(summary, r"Decision key", r"决策.*key", r"决策键"):
        errors.append(f"{path}: Decision Summary must include Decision key for consistency checks")
    if re.search(r"\|\s*[^|\n]+\|\s*[^|\n]*\|\s*open\s*\|", summary, re.IGNORECASE):
        errors.append(f"{path}: Decision Summary contains open decisions")

    if DECISION_RANGE_RE.search(text):
        errors.append(f"{path}: decision ranges are not allowed; each decision needs its own detail section")

    summary_ids = summary_decision_ids(text)
    detail_ids = heading_ids(text)
    for decision_id in sorted(summary_ids - detail_ids):
        errors.append(f"{path}: decision {decision_id} is in summary but missing an individual ### detail section")

    details = first_existing_section(text, "决策详情", "Decision Details")
    if details and not has_table_columns(details, ["Rejected alternatives", "Downstream Atomic Issue impact", "Verification"]):
        errors.append(
            f"{path}: Decision Details must include rejected alternatives, downstream Atomic Issue impact, and verification"
        )
    if details and not has_any_pattern(details, r"Decision key", r"决策.*key", r"决策键"):
        errors.append(f"{path}: Decision Details must include Decision key")

    if "TBD" in text or "TODO" in text:
        errors.append(f"{path}: contains TBD/TODO")

    return errors


def validate_source_intake(path: Path) -> list[str]:
    text = read(path)
    errors: list[str] = []
    if not text.strip():
        return [f"{path}: missing Source Intake Ledger"]

    inventory = first_existing_section(text, "Source Inventory")
    semantic_map = first_existing_section(text, "Source To Semantic Object Map")
    conflicts = first_existing_section(text, "Source Conflict Matrix")

    if not inventory:
        errors.append(f"{path}: missing Source Inventory")
    if not semantic_map:
        errors.append(f"{path}: missing Source To Semantic Object Map")
    if not conflicts:
        errors.append(f"{path}: missing Source Conflict Matrix")

    if inventory and not has_table_columns(
        inventory,
        ["Source ID", "Type", "Path", "Read status", "Read method", "Used for"],
    ):
        errors.append(f"{path}: Source Inventory must include Source ID, Type, Path/URL, Read status, Read method, and Used for")
    if semantic_map and not has_table_columns(
        semantic_map,
        ["Source ID", "Extracted object", "Extracted semantics", "Target artifact", "Status"],
    ):
        errors.append(f"{path}: Source To Semantic Object Map must include source, extracted object/semantics, target artifact, and status")
    if conflicts and not has_table_columns(conflicts, ["Conflict", "Source A", "Source B", "Decision required", "Resolution DEC", "Status"]):
        errors.append(f"{path}: Source Conflict Matrix must include conflict sources, required decision, resolution DEC, and status")

    if "read / unread / blocked / irrelevant / superseded" in text:
        errors.append(f"{path}: appears to contain template placeholder read-status options")
    if "REQ-xxx / SCN-xxx / DEC-xxx" in text:
        errors.append(f"{path}: appears to contain template placeholder semantic-object options")

    for row in table_rows(inventory):
        if not row or row[0].lower() == "source id":
            continue
        joined = " | ".join(row)
        if re.search(r"\b(unread|blocked)\b", joined, re.IGNORECASE) and not re.search(
            r"\b(irrelevant|superseded)\b", joined, re.IGNORECASE
        ):
            errors.append(f"{path}: Source Inventory contains unread/blocked source row: {joined}")
        if len(row) >= 7 and row[4].strip().lower() == "read" and not row[6].strip():
            errors.append(f"{path}: read source has no downstream Used for mapping: {joined}")

    for row in table_rows(semantic_map):
        if not row or row[0].lower() == "source id":
            continue
        joined = " | ".join(row)
        if re.search(r"\b(conflict|blocked)\b", joined, re.IGNORECASE):
            errors.append(f"{path}: Source To Semantic Object Map has unresolved conflict/blocked row: {joined}")

    for row in table_rows(conflicts):
        if not row or row[0].lower() == "conflict":
            continue
        joined = " | ".join(row)
        if re.search(r"\bopen\b", joined, re.IGNORECASE):
            errors.append(f"{path}: Source Conflict Matrix contains open conflict row: {joined}")

    return errors


def validate_prd_completeness(change_dir: Path, proposal: str, spec: str, plan: str) -> list[str]:
    errors: list[str] = []
    combined = proposal + "\n" + spec + "\n" + plan
    if not (proposal or spec):
        return errors

    propose = first_existing_section(
        combined,
        "Propose Extraction",
        "Propose Extraction Table",
        "需求提取",
        "原始意图提取",
    )
    if not propose:
        errors.append(f"{change_dir}: PRD missing Propose Extraction; external docs/dialogue must be treated as propose/source, not final PRD")
    elif not has_table_columns(
        propose,
        ["Source ID", "Propose statement", "Explicit fact", "Inferred fact", "Unknown"],
    ):
        errors.append(
            f"{change_dir}: Propose Extraction must include Source ID, Propose statement, Explicit fact, Inferred fact, and Unknown/decision needed"
        )

    current = first_existing_section(
        combined,
        "Current Product/Code Understanding",
        "Current Product Code Understanding",
        "当前产品/代码理解",
        "当前项目现状理解",
    )
    if not current:
        errors.append(f"{change_dir}: PRD missing Current Product/Code Understanding before locking requirements")
    elif not has_table_columns(
        current,
        ["Area", "Current behavior", "Evidence", "Product implication", "Gap"],
    ):
        errors.append(
            f"{change_dir}: Current Product/Code Understanding must include Area, Current behavior, Evidence path/command, Product implication, and Gap/decision"
        )
    elif not re.search(r"(?:/|\\|\.java|\.ts|\.tsx|\.vue|\.go|\.py|\.yaml|\.yml|\.tf|rg |grep |mvn |pnpm |npm |curl )", current):
        errors.append(f"{change_dir}: Current Product/Code Understanding lacks concrete evidence paths or commands")

    code_scope = first_existing_section(combined, "Code Scope Discovery", "Search Coverage", "代码范围发现")
    if not code_scope:
        errors.append(f"{change_dir}: PRD missing Code Scope Discovery with search coverage and stop conditions")
    elif not has_any_pattern(code_scope, r"Stop condition", r"停止条件") or not has_any_pattern(code_scope, r"Evidence", r"证据"):
        errors.append(f"{change_dir}: Code Scope Discovery must include evidence and stop conditions")
    elif re.search(r"\|\s*yes\s*\|[^|\n]*\|\s*[^|\n]*\|\s*[^|\n]*\|\s*[^|\n]*\|\s*no\s*\|", code_scope, re.IGNORECASE):
        errors.append(f"{change_dir}: Code Scope Discovery has required area without stop condition")

    user_decision = first_existing_section(combined, "User Decision Interaction", "用户决策交互")
    has_pdec = bool(re.search(r"\bPDEC-\d{3}\b", combined))
    if has_pdec and not user_decision and not re.search(r"ai-authorized|AI.*授权|用户.*授权.*AI", combined, re.IGNORECASE):
        errors.append(f"{change_dir}: PDEC exists but missing User Decision Interaction or explicit AI product-decision authorization")
    if user_decision:
        if not has_table_columns(user_decision, ["Decision ID", "Question", "Recommended option", "Alternatives", "User response", "Final status"]):
            errors.append(f"{change_dir}: User Decision Interaction must include decision, recommendation, alternatives, user response, and final status")
        if re.search(r"\|\s*PDEC-\d{3}[^|\n]*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|\s*(?:no-response|ambiguous|needs-change)[^|\n]*\|\s*locked\s*\|", user_decision, re.IGNORECASE):
            errors.append(f"{change_dir}: User Decision Interaction locks ambiguous/no-response product decision")

    source_trace = first_existing_section(combined, "Source Trace", "Source Trace Table", "Source Trace and Research Evidence")
    if not source_trace:
        errors.append(f"{change_dir}: PRD missing Source Trace; input sources must be normalized into workflow-owned PRD")

    required_sections = [
        ("User Scenario Table|用户与场景", ["User", "Goal"]),
        ("Product Object Model|产品对象模型", ["Object", "User-facing"]),
        ("Scope|功能范围|In Scope", ["In Scope"]),
        ("用户可见配置|Config", ["Config"]),
        ("用户可见状态|State", ["State"]),
        ("用户可见错误和降级|Error", ["Scenario", "Product behavior"]),
        ("权限和可见性|Permission", ["Required permission"]),
        ("场景与验收|Scenario Acceptance|Acceptance", ["Given", "When", "Then"]),
        ("产品决策|Product Decisions", ["Decision", "Status"]),
    ]
    for names, columns in required_sections:
        section_text = first_existing_section(combined, *heading_options(names))
        if not section_text:
            errors.append(f"{change_dir}: PRD missing required section {heading_options(names)[0]}")
        elif columns and not any(col.lower() in section_text.lower() for col in columns):
            errors.append(f"{change_dir}: PRD section {heading_options(names)[0]} appears incomplete")

    prd_gate = first_existing_section(
        combined,
        "PRD Completeness Gate",
        "PRD 完整度门禁",
        "PRD 完备性门禁",
    )
    if not prd_gate:
        errors.append(f"{change_dir}: PRD missing PRD Completeness Gate")
    else:
        if not has_table_columns(prd_gate, ["Dimension", "Complete", "Evidence", "Open decision", "Blocks next stage"]):
            errors.append(
                f"{change_dir}: PRD Completeness Gate must include Dimension, Complete, Evidence section, Open decision, and Blocks next stage"
            )
        for row in table_rows(prd_gate):
            if not row or row[0].lower() == "dimension":
                continue
            joined = " | ".join(row)
            if re.search(r"\|\s*(?:no|否)\s*\|", joined, re.IGNORECASE) and re.search(
                r"\|\s*(?:yes|是)\s*\|", joined, re.IGNORECASE
            ):
                errors.append(f"{change_dir}: PRD Completeness Gate contains blocking incomplete row: {joined}")

    product_decisions = first_existing_section(combined, "产品决策", "Product Decisions")
    if product_decisions and re.search(r"\|\s*PDEC-\d{3}[^|\n]*\|\s*[^|\n]*\|\s*[^|\n]*\|\s*[^|\n]*\|\s*open\s*\|", product_decisions, re.IGNORECASE):
        errors.append(f"{change_dir}: PRD contains open PDEC; cannot enter downstream workflow")

    if re.search(r"\b(final PRD|accepted PRD|直接采用|原文即PRD|原文就是PRD)\b", combined, re.IGNORECASE):
        errors.append(f"{change_dir}: PRD appears to accept external input as final PRD; must normalize as propose/source")

    return errors


def validate_semantic_consumption(change_dir: Path, proposal: str, spec: str, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    combined = proposal + "\n" + spec + "\n" + plan + "\n" + tasks
    upstream_ids = ids(
        r"\b(REQ-\d{3}|SCN-\d{3}|PDEC-\d{3}|ADEC-\d{3}|DEC-\d{3}|DESIGN-DEC-\d{3}|ARCH-DEC-\d{3}|MIG-DEC-\d{3}|UI-DEC-\d{3}|VER-DEC-\d{3}|TASK-DEC-\d{3}|C-\d{3}|MIG-\d{3}|VER-\d{3})\b",
        combined,
    )
    if not upstream_ids:
        return errors

    semantic = first_existing_section(
        combined,
        "Semantic Consumption Matrix",
        "Semantic Consumption Matrix - New Feature Design",
        "Semantic Consumption Matrix - Code Archaeology",
        "Semantic Consumption Matrix - Cross-Module Contract",
        "Semantic Consumption Matrix - Verification",
        "Semantic Consumption Matrix - Atomic Task Planning",
        "语义消费矩阵",
    )
    if not semantic:
        errors.append(f"{change_dir}: upstream semantic IDs exist but missing Semantic Consumption Matrix")
        return errors

    if not has_table_columns(
        semantic,
        ["Upstream object", "How consumed", "Derived object", "Copied semantics", "Dropped semantics", "Status"],
    ):
        errors.append(
            f"{change_dir}: Semantic Consumption Matrix must include Upstream object, How consumed, Derived object, Copied semantics, Dropped semantics, and Status"
        )

    if "REQ-001 / SCN-001 / PDEC-001" in semantic or "requirement / scenario / product-decision" in semantic:
        errors.append(f"{change_dir}: Semantic Consumption Matrix appears to contain template placeholder rows")

    for upstream_id in sorted(upstream_ids):
        if upstream_id.startswith("T"):
            continue
        if upstream_id not in semantic:
            errors.append(f"{change_dir}: upstream object {upstream_id} missing from Semantic Consumption Matrix")

    for row in table_rows(semantic):
        if not row or row[0].lower() == "upstream object":
            continue
        joined = " | ".join(row)
        if re.search(r"\bblocked\b|阻塞", joined, re.IGNORECASE):
            errors.append(f"{change_dir}: Semantic Consumption Matrix contains blocked row: {joined}")
        if re.search(r"\|\s*(?:dropped|丢弃|ignored)\b", joined, re.IGNORECASE) and not re.search(
            r"\b(DEC-|PDEC-|ADEC-|N/A|不适用|明确不需要|locked)\b", joined, re.IGNORECASE
        ):
            errors.append(f"{change_dir}: Semantic Consumption Matrix drops semantics without locked decision/N/A reason: {joined}")
        if re.search(r"\b(REQ|SCN|PDEC|DEC|C|MIG|VER)-\d{3}\b", joined) and re.search(
            r"\|\s*(?:copied|transformed|verified|consumed)\s*\|", joined, re.IGNORECASE
        ):
            cjk = len(CJK_RE.findall(joined))
            if cjk < 12 and not re.search(r"\b(C-|VER-|T\d{3}|DEC-|N/A)\b", joined):
                errors.append(f"{change_dir}: Semantic Consumption Matrix row appears ID-only without copied semantics: {joined}")

    return errors


def validate_engineering_propose(change_dir: Path, plan: str) -> list[str]:
    errors: list[str] = []
    if not re.search(r"AIP|Architecture|Engineering|Terraform|OpenAPI|工程|架构|接口", plan, re.IGNORECASE):
        return errors

    intake = first_existing_section(plan, "Engineering Propose Extraction", "Engineering Propose Intake", "工程 Propose 提取")
    current = first_existing_section(plan, "Current Architecture Understanding", "当前架构理解")
    gate = first_existing_section(plan, "Engineering Decision Completeness Gate", "工程决策完整度门禁")

    if not intake:
        errors.append(f"{change_dir}: engineering/AIP content exists but missing Engineering Propose Extraction")
    elif not has_table_columns(intake, ["Source ID", "Engineering propose", "Explicit engineering fact", "Inferred engineering fact", "Unknown"]):
        errors.append(f"{change_dir}: Engineering Propose Extraction must include source, propose, explicit/inferred facts, and unknown decisions")

    if not current:
        errors.append(f"{change_dir}: engineering/AIP content exists but missing Current Architecture Understanding")
    elif not has_table_columns(current, ["Area", "Current architecture", "Evidence", "Engineering implication", "Gap"]):
        errors.append(f"{change_dir}: Current Architecture Understanding must include area, current architecture, evidence, implication, and gap/DEC")
    elif not re.search(r"(?:/|\\|\.java|\.ts|\.tsx|\.go|\.py|\.yaml|\.yml|\.tf|rg |grep |mvn |pnpm |npm |curl )", current):
        errors.append(f"{change_dir}: Current Architecture Understanding lacks concrete evidence paths or commands")

    if not gate:
        errors.append(f"{change_dir}: engineering/AIP content exists but missing Engineering Decision Completeness Gate")
    else:
        if not has_table_columns(gate, ["Dimension", "Complete", "Evidence", "Open DEC", "Blocks next stage"]):
            errors.append(f"{change_dir}: Engineering Decision Completeness Gate must include Dimension, Complete, Evidence, Open DEC, and Blocks next stage")
        for row in table_rows(gate):
            if not row or row[0].lower() == "dimension":
                continue
            joined = " | ".join(row)
            if re.search(r"\|\s*(?:no|否)\s*\|", joined, re.IGNORECASE) and re.search(r"\|\s*(?:yes|是)\s*\|", joined, re.IGNORECASE):
                errors.append(f"{change_dir}: Engineering Decision Completeness Gate contains blocking incomplete row: {joined}")

    return errors


def validate_verification_feasibility(change_dir: Path, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    combined = plan + "\n" + tasks
    if not re.search(r"Verification Matrix|验证矩阵|VER-\d{3}", combined):
        return errors

    feasibility = first_existing_section(combined, "Verification Feasibility Gate", "Verification Feasibility Matrix", "验证可行性门禁")
    if not feasibility:
        errors.append(f"{change_dir}: Verification Matrix exists but missing Verification Feasibility Gate")
        return errors
    if not has_table_columns(feasibility, ["Verification", "Source", "Required", "Environment", "Available", "Setup", "Fallback", "Blocks done"]):
        errors.append(f"{change_dir}: Verification Feasibility Gate must include verification, source, required, environment/fixture, available, setup, fallback, and blocks done")
    for row in table_rows(feasibility):
        if not row or row[0].lower() == "verification":
            continue
        joined = " | ".join(row)
        if re.search(r"\|\s*yes\s*\|[^|\n]*\|\s*[^|\n]*\|\s*no\s*\|", joined, re.IGNORECASE) and re.search(
            r"\|\s*yes\s*\|", joined, re.IGNORECASE
        ):
            if not re.search(r"Not Run|blocked|risk|风险|阻塞", joined, re.IGNORECASE):
                errors.append(f"{change_dir}: required unavailable verification lacks blocking Not Run/fallback risk: {joined}")
    return errors


def validate_version_alignment(change_dir: Path, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    combined = plan + "\n" + tasks
    if not re.search(r"TERRAFORM_BRANCH|IAC_BRANCH|IAC repo|test-orchestration repo|deployment-template repo|control-plane|data-plane|版本|分支", combined, re.IGNORECASE):
        return errors
    alignment = first_existing_section(combined, "Version Branch Alignment Matrix", "Version / Branch Alignment", "版本分支对齐")
    if not alignment:
        errors.append(f"{change_dir}: version/branch signals exist but missing Version Branch Alignment Matrix")
        return errors
    if not has_table_columns(alignment, ["Component", "Repo", "Branch", "Required by", "Evidence", "Aligned", "Risk"]):
        errors.append(f"{change_dir}: Version Branch Alignment Matrix must include component, repo, branch/version, required by, evidence, aligned, and risk/action")
    if re.search(r"\|\s*[^|\n]+\|\s*[^|\n]+\|\s*[^|\n]+\|\s*[^|\n]+\|\s*[^|\n]*\|\s*no\s*\|", alignment, re.IGNORECASE):
        errors.append(f"{change_dir}: Version Branch Alignment Matrix contains unaligned row")
    return errors


def validate_stateful_behavior_matrix(change_dir: Path, proposal: str, spec: str, plan: str, tasks: str, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {
        "all",
        "archaeology",
        "contract",
        "verification",
        "task-planning",
        "pre-execution",
        "mock-acceptance",
        "product-acceptance",
    }:
        return errors
    combined = "\n".join([proposal, spec, plan, tasks, read(change_dir / "atomic-issue-packets.yaml")])
    if not has_stateful_signal(combined):
        return errors

    matrix_yaml = change_dir / "stateful-behavior-matrix.yaml"
    matrix_md = change_dir / "stateful-behavior-matrix.md"
    matrix_text = read(matrix_md)
    if not matrix_yaml.exists() and not matrix_text.strip():
        errors.append(
            f"{change_dir}: lifecycle/progress/event/status/terminal signal exists but missing stateful-behavior-matrix.yaml or stateful-behavior-matrix.md"
        )
        return errors

    if matrix_text.strip():
        if not has_table_columns(matrix_text, STATEFUL_MATRIX_COLUMNS):
            errors.append(
                f"{matrix_md}: Stateful Behavior Matrix must include columns {', '.join(STATEFUL_MATRIX_COLUMNS)}"
            )
        if not has_meaningful_rows(matrix_text):
            errors.append(f"{matrix_md}: Stateful Behavior Matrix must include concrete transition rows")
        if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", matrix_text, re.IGNORECASE):
            errors.append(f"{matrix_md}: contains unresolved stateful behavior value")

    if matrix_yaml.exists():
        if yaml is None:
            errors.append(f"{matrix_yaml}: PyYAML is required to validate stateful behavior matrix")
        else:
            try:
                data = yaml.safe_load(matrix_yaml.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                errors.append(f"{matrix_yaml}: invalid YAML: {exc}")
                return errors
            behaviors = data.get("stateful_behaviors")
            if not isinstance(behaviors, list) or not behaviors:
                errors.append(f"{matrix_yaml}: stateful_behaviors must define at least one behavior")
                return errors
            required = {
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
            }
            for behavior in behaviors:
                if not isinstance(behavior, dict):
                    errors.append(f"{matrix_yaml}: stateful behavior row must be a mapping")
                    continue
                rows = behavior.get("rows")
                if not isinstance(rows, list) or not rows:
                    errors.append(f"{matrix_yaml}: behavior {behavior.get('behavior_id') or '<missing>'} must include rows")
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        errors.append(f"{matrix_yaml}: stateful transition row must be a mapping")
                        continue
                    missing = sorted(field for field in required if not str(row.get(field, "")).strip())
                    if missing:
                        errors.append(
                            f"{matrix_yaml}: stateful row {row.get('row_id') or '<missing>'} missing {', '.join(missing)}"
                        )
                    if row.get("terminal") not in {True, False, "true", "false", "yes", "no"}:
                        errors.append(f"{matrix_yaml}: stateful row {row.get('row_id') or '<missing>'} terminal must be explicit true/false")
                    consumers = row.get("consumers") or behavior.get("consumers")
                    if not consumers:
                        errors.append(f"{matrix_yaml}: stateful row {row.get('row_id') or '<missing>'} missing consumers")
                    if not row.get("frontend_assertion") and not row.get("mock_fixture_ref"):
                        errors.append(
                            f"{matrix_yaml}: stateful row {row.get('row_id') or '<missing>'} must bind frontend_assertion or mock_fixture_ref"
                        )
            coverage = data.get("stateful_transition_coverage")
            if not isinstance(coverage, list) or not coverage:
                errors.append(f"{matrix_yaml}: stateful_transition_coverage is required")
            consumer_matrix = data.get("stateful_consumer_matrix")
            if not isinstance(consumer_matrix, list) or not consumer_matrix:
                errors.append(f"{matrix_yaml}: stateful_consumer_matrix is required")
    return errors


def validate_rubric_scorecard(change_dir: Path, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    combined = plan + "\n" + tasks
    scorecard = first_existing_section(combined, "Artifact Rubric Scorecard", "Rubric Scorecard", "Artifact Review Scorecard", "评分表")
    if not scorecard:
        errors.append(f"{change_dir}: missing Artifact Rubric Scorecard; structural validation is not enough")
        return errors
    if not has_table_columns(scorecard, ["Artifact", "Rubric", "Dimension", "Score", "Evidence", "Fix"]):
        errors.append(f"{change_dir}: Artifact Rubric Scorecard must include Artifact, Rubric, Dimension, Score, Evidence, and Fix required")
    if re.search(r"\|\s*[^|\n]+\|\s*[^|\n]+\|\s*[^|\n]+\|\s*0\s*\|", scorecard):
        errors.append(f"{change_dir}: Artifact Rubric Scorecard contains score 0")
    if re.search(r"\|\s*[^|\n]+\|\s*[^|\n]+\|\s*[^|\n]+\|\s*1\s*\|[^|\n]*\|\s*\|", scorecard):
        errors.append(f"{change_dir}: Artifact Rubric Scorecard contains score 1 without fix/risk action")
    return errors


def validate_decision_consistency(change_dir: Path, plan: str, decision_text: str) -> list[str]:
    errors: list[str] = []
    combined = plan + "\n" + decision_text

    if re.search(r"Decision Registry|Decision Summary|决策摘要", combined) and not re.search(
        r"Decision key|决策.*key|决策键", combined, re.IGNORECASE
    ):
        errors.append(f"{change_dir}: decisions exist but missing Decision key")

    if re.search(r"Decision Registry", plan) and not re.search(
        r"Decision Consistency Matrix|决策一致性", plan, re.IGNORECASE
    ):
        errors.append(f"{change_dir}: Decision Registry exists but missing Decision Consistency Matrix")

    consistency = first_existing_section(plan, "Decision Consistency Matrix", "决策一致性矩阵")
    if consistency:
        if not has_table_columns(consistency, ["Decision key", "Active decision", "Conflict", "Status"]):
            errors.append(f"{change_dir}: Decision Consistency Matrix must include Decision key, Active decision, Conflict, and Status")
        for row in table_rows(consistency):
            if not row or row[0].lower() == "decision key":
                continue
            joined = " | ".join(row)
            if re.search(r"\bConflict\?\s*\|\s*yes\b|\|\s*yes\s*\|", joined, re.IGNORECASE) and re.search(
                r"\b(open|unresolved|待确认)\b", joined, re.IGNORECASE
            ):
                errors.append(f"{change_dir}: Decision Consistency Matrix contains unresolved conflict row: {joined}")
            if re.search(r"\|\s*open\s*\|", joined, re.IGNORECASE):
                errors.append(f"{change_dir}: Decision Consistency Matrix contains open row: {joined}")

    return errors


def human_decision_participation_enabled(text_value: str) -> bool:
    return bool(
        re.search(
            r"human-decision-participation|我参与决策|每个决策让我确认|不要自动决策|后续决策都问我|我来拍板",
            text_value,
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
    evidence = flatten_text(value)
    if len(evidence) < 8:
        return False
    if re.search(r"\b(?:TBD|TODO|unknown|not-authorized|not authorized)\b|待确认|未授权", evidence, re.IGNORECASE):
        return False
    if re.search(r"\buser message\s*/\s*doc\s*/\s*meeting note\b|用户消息\s*/\s*文档\s*/\s*会议", evidence, re.IGNORECASE):
        return False
    if evidence.lower() in {"user message", "doc", "meeting note", "user message / doc / meeting note"}:
        return False
    return True


def authority_table_authorizes_ai(prefix: str, text_value: str) -> bool:
    for section_text in [first_existing_section(text_value, "Decision Authority", "决策权限"), text_value]:
        for row in table_dicts(section_text):
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


def explicit_user_authorization_text(prefix: str, text_value: str) -> bool:
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
    return any(re.search(pattern, text_value, re.IGNORECASE) for pattern in patterns)


def ai_decision_authorized_for(prefix: str, text_value: str) -> bool:
    return authority_table_authorizes_ai(prefix, text_value) or explicit_user_authorization_text(prefix, text_value)


def user_decision_interaction_section(text_value: str) -> str:
    return first_existing_section(text_value, "User Decision Interaction", "用户决策交互")


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


def decision_ids_for_stage(stage: str, text_value: str) -> set[str]:
    found = set(DECISION_ID_RE.findall(text_value))
    if stage == "prd":
        return {item for item in found if item.startswith("PDEC-")}
    if stage in {"aip", "readiness"}:
        return {item for item in found if item.startswith("ADEC-")}
    return {
        item
        for item in found
        if not item.startswith("PDEC-") and not item.startswith("ADEC-")
    }


def explicit_bundle_confirmation(value: str) -> bool:
    response = re.sub(r"\s+", " ", value.strip())
    if not response:
        return False
    if re.search(
        r"(?:do\s+not|don't|not\s+(?:agree|approve|confirm)|disagree|except|only|"
        r"不同意|不确认|不采用|拒绝|除.+外|仅(?:同意|确认|采用))",
        response,
        re.IGNORECASE,
    ):
        return False
    affirmative = bool(re.search(r"confirm|agree|approve|同意|确认|采用", response, re.IGNORECASE))
    complete_scope = bool(
        re.search(r"all(?:[-\s]+listed)?|every|above|listed|全部|所有|以上|逐项", response, re.IGNORECASE)
    )
    return affirmative and complete_scope


def human_decision_bundle_records(change_dir: Path, stage: str) -> tuple[set[str], list[str]]:
    accepted: set[str] = set()
    errors: list[str] = []
    for path in sorted((change_dir / "decision-bundles").glob("*.yaml")):
        doc = read_yaml(path)
        label = path.relative_to(change_dir).as_posix()
        if doc.get("schema_version") != 1:
            errors.append(f"{label}: schema_version must be 1")
            continue
        bundle_id = str(doc.get("bundle_id", "")).strip()
        if not re.fullmatch(r"HDB-\d{3}", bundle_id):
            errors.append(f"{label}: bundle_id must match HDB-xxx")
        elif path.stem != bundle_id:
            errors.append(f"{label}: filename must match bundle_id {bundle_id}")
        bundle_stage = str(doc.get("stage", "")).strip()
        if bundle_stage not in HUMAN_DECISION_REQUIRED_STAGES:
            errors.append(f"{label}: stage must name a human-decision stage")
            continue
        if bundle_stage != stage:
            continue
        decisions = [item for item in doc.get("decisions", []) if isinstance(item, dict)] if isinstance(doc.get("decisions"), list) else []
        if len(decisions) < 2:
            errors.append(f"{label}: a decision bundle must contain at least two decisions")
        decision_ids = [str(item.get("decision_id", "")).strip() for item in decisions]
        if any(not re.fullmatch(DECISION_ID_PATTERN, item) for item in decision_ids):
            errors.append(f"{label}: every bundled decision must have a valid decision_id")
        if len(set(decision_ids)) != len(decision_ids):
            errors.append(f"{label}: bundled decision IDs must be unique")
        if set(decision_ids) != decision_ids_for_stage(stage, " ".join(decision_ids)):
            errors.append(f"{label}: every bundled decision must belong to stage {stage}")
        for item in decisions:
            decision_id = str(item.get("decision_id", "")).strip() or "<missing>"
            for field in ["decision_key", "recommendation", "alternatives", "impact"]:
                if len(str(item.get(field, "")).strip()) < 8:
                    errors.append(f"{label}: {decision_id}.{field} is incomplete")
            if item.get("batch_eligible") is not True:
                errors.append(f"{label}: {decision_id}.batch_eligible must be true")
        prompt_snapshot = str(doc.get("prompt_snapshot", "")).strip()
        expected_prompt_hash = hashlib.sha256((prompt_snapshot.rstrip() + "\n").encode("utf-8")).hexdigest()
        if len(prompt_snapshot) < 80 or str(doc.get("prompt_hash", "")).strip() != expected_prompt_hash:
            errors.append(f"{label}: prompt_snapshot/prompt_hash must seal the complete displayed decision bundle")
        if str(doc.get("response_scope", "")).strip() != "all-listed":
            errors.append(f"{label}: response_scope must be all-listed")
        if not explicit_bundle_confirmation(str(doc.get("user_response", "")).strip()):
            errors.append(f"{label}: user_response must affirmatively confirm all listed decisions without exceptions")
        if str(doc.get("status", "")).strip() != "locked" or not ISO_TIMESTAMP_RE.fullmatch(
            str(doc.get("decided_at", "")).strip()
        ):
            errors.append(f"{label}: status must be locked and decided_at must be an ISO-8601 timestamp")
        if str(doc.get("receipt_hash", "")).strip() != canonical_receipt_hash(doc):
            errors.append(f"{label}: receipt_hash is forged or stale")
        if not any(error.startswith(f"{label}:") for error in errors):
            accepted.update(decision_ids)
    return accepted, errors


def has_human_decision_record(
    decision_id: str,
    decision_doc: str,
    interaction: str,
    bundled_decision_ids: set[str] | None = None,
) -> bool:
    if decision_id in (bundled_decision_ids or set()):
        return True
    row_texts: list[str] = []
    for row in table_dicts(interaction):
        if decision_id in " ".join(row.values()):
            row_texts.append(" | ".join(row.values()))
    for row in table_dicts(decision_doc):
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


def validate_human_decision_records(change_dir: Path, stage: str, combined_text: str, workflow_state: dict) -> list[str]:
    errors: list[str] = []
    if stage not in HUMAN_DECISION_REQUIRED_STAGES and stage != "all":
        return errors
    stage_status = workflow_state.get("stage_status", {}) if isinstance(workflow_state.get("stage_status"), dict) else {}
    stages = sorted(HUMAN_DECISION_REQUIRED_STAGES) if stage == "all" else [stage]
    interaction = user_decision_interaction_section(combined_text)
    human_mode = human_decision_participation_enabled(combined_text + "\n" + flatten_text(workflow_state))
    bundled_by_stage: dict[str, set[str]] = {}
    for stage_name in stages:
        bundled_ids, bundle_errors = human_decision_bundle_records(change_dir, stage_name)
        bundled_by_stage[stage_name] = bundled_ids
        errors.extend(bundle_errors)
    if human_mode and not interaction:
        errors.append(f"{change_dir}: human-decision-participation is enabled but User Decision Interaction ledger is missing")
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
        if not has_table_columns(interaction, required_columns):
            errors.append(f"{change_dir}: User Decision Interaction must include stage, decision id/key, prompt id/summary, recommendation, alternatives, user response, final status, and decided-at")
        if re.search(r"batch|批量|以上.*都|all agreed|all approved|一并确认", interaction, re.IGNORECASE) and not any(
            bundled_by_stage.values()
        ):
            errors.append(
                f"{change_dir}: batched confirmation requires a valid decision-bundles/HDB-xxx.yaml receipt"
            )
    for stage_name in stages:
        decision_doc_path = decision_doc_for_stage(change_dir, stage_name)
        decision_doc = read(decision_doc_path)
        stage_text = "\n".join(
            [
                combined_text,
                decision_doc,
                read(change_dir / "decision-reviews" / "decision-registry.md"),
                read(change_dir / "decision-registry.md"),
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
            errors.append(f"{change_dir}: {stage_name} requires human decision records but User Decision Interaction ledger is missing")
        if not decision_doc.strip():
            errors.append(f"{change_dir}: {stage_name} requires human decision records but {decision_doc_path.relative_to(change_dir)} is missing or empty")
            continue
        for decision_id in sorted(decision_ids):
            if prefixes and not any(decision_id.startswith(prefix) for prefix in prefixes) and not human_mode:
                continue
            if not has_human_decision_record(
                decision_id,
                decision_doc,
                interaction,
                bundled_by_stage.get(stage_name),
            ):
                errors.append(
                    f"{change_dir}: {decision_id} requires an individual Human Decision Prompt record or a valid decision bundle receipt"
                )
    return errors


def validate_contract_discovery(change_dir: Path, plan: str) -> list[str]:
    errors: list[str] = []
    has_contracts = re.search(r"Module Contract Graph|Contract List|Cross-Module Contract|跨模块契约|模块契约图", plan)
    discovery = first_existing_section(
        plan,
        "Contract Discovery Coverage Matrix",
        "Contract Discovery Coverage",
        "契约发现覆盖矩阵",
    )
    if has_contracts and not discovery:
        errors.append(f"{change_dir}: contracts exist but missing Contract Discovery Coverage Matrix")
    if discovery:
        if not has_table_columns(
            discovery,
            ["Source area", "Evidence reviewed", "Contract candidates", "Locked contracts", "Residual risk"],
        ):
            errors.append(
                f"{change_dir}: Contract Discovery Coverage Matrix must include Source area, Evidence reviewed, Contract candidates, Locked contracts, and Residual risk"
            )
        for row in table_rows(discovery):
            if not row or row[0].lower() == "source area":
                continue
            joined = " | ".join(row)
            if re.search(r"\b(residual|risk|风险)\b", joined, re.IGNORECASE) and not re.search(
                r"\b(N/A|none|无|VER-|Not Run|已进入验证|已记录)\b", joined, re.IGNORECASE
            ):
                errors.append(f"{change_dir}: Contract Discovery Coverage has residual risk not mapped to verification/not-run: {joined}")
    return errors


def validate_task_dag(change_dir: Path, tasks: str, plan: str) -> list[str]:
    errors: list[str] = []
    combined = tasks + "\n" + plan
    task_ids = ids(r"\b(T\d{3})\b", tasks)
    if task_ids and not re.search(r"Task DAG|任务\s*DAG", combined, re.IGNORECASE):
        errors.append(f"{change_dir}: tasks exist but missing Task DAG")
        return errors

    dag_nodes = first_existing_section(combined, "DAG Nodes")
    dag_edges = first_existing_section(combined, "DAG Edges")
    topo = first_existing_section(combined, "Topological Execution Order")
    parallel = first_existing_section(combined, "Parallel Groups")

    if task_ids:
        if not dag_nodes:
            errors.append(f"{change_dir}: Task DAG missing DAG Nodes")
        if not dag_edges:
            errors.append(f"{change_dir}: Task DAG missing DAG Edges")
        if not topo:
            errors.append(f"{change_dir}: Task DAG missing Topological Execution Order")
        if not parallel:
            errors.append(f"{change_dir}: Task DAG missing Parallel Groups")

    if dag_nodes and not has_table_columns(
        dag_nodes,
        ["Task", "Primary module", "Provides contracts", "Consumes contracts", "Verification gate"],
    ):
        errors.append(f"{change_dir}: DAG Nodes must include Task, Primary module, Provides contracts, Consumes contracts, and Verification gate")
    if dag_edges and not has_table_columns(
        dag_edges,
        ["From task", "To task", "Dependency type", "Reason", "Failure propagation"],
    ):
        errors.append(f"{change_dir}: DAG Edges must include From task, To task, Dependency type, Reason, and Failure propagation")
    if topo and not has_table_columns(topo, ["Order", "Task", "Why now", "Blocked by", "Unlocks"]):
        errors.append(f"{change_dir}: Topological Execution Order must include Order, Task, Why now, Blocked by, and Unlocks")

    node_text = dag_nodes
    for task_id in sorted(task_ids):
        if dag_nodes and task_id not in node_text:
            errors.append(f"{change_dir}: task {task_id} is missing from DAG Nodes")

    if dag_edges and re.search(r"\|\s*T\d{3}\s*\|\s*T\d{3}\s*\|\s*\|", dag_edges):
        errors.append(f"{change_dir}: DAG Edges contains dependency without type/reason")
    if dag_edges and re.search(r"\|\s*T\d{3}\s*\|\s*T\d{3}\s*\|[^|\n]*\|[^|\n]*\|\s*(?:unknown|TBD|TODO|)\s*\|", dag_edges, re.IGNORECASE):
        errors.append(f"{change_dir}: DAG Edges contains unknown or empty failure propagation")
    if parallel and re.search(r"\|\s*P\d+[^|\n]*\|[^|\n]*\|\s*no\s*\|", parallel, re.IGNORECASE):
        errors.append(f"{change_dir}: Parallel Groups contains non-disjoint file/contract/verification group")

    if TASK_EXECUTION_LOG_RE.search(tasks):
        errors.append(
            f"{change_dir / 'tasks.md'}: tasks.md contains execution log/verification results; "
            "tasks.md is sealed planning output; use task-verification-log.yaml/execution-state.yaml for verification, "
            "task-semantic-review.yaml for task-local review, mock-acceptance-execution.yaml for mock row evidence, "
            "and workflowctl pass-task receipts for task completion"
        )
    if TERMINAL_TASK_STATUS_RE.search(tasks):
        errors.append(
            f"{change_dir / 'tasks.md'}: task rows contain terminal status passed/done/completed; "
            "task completion must be derived from workflow-state task_receipts"
        )

    dag_doc = read_yaml(change_dir / "task-dag.yaml")
    contract_doc = read_yaml(change_dir / "contracts.yaml")
    dag_tasks = as_dict(dag_doc.get("tasks"))
    contracts = as_dict(contract_doc.get("contracts"))
    if dag_tasks:
        active_rows = active_contract_obligation_rows(change_dir)
        obligation_rows_by_id = {
            obligation_row_id(row): row
            for row in active_rows
            if obligation_row_id(row) and not obligation_id_is_coarse_contract(obligation_row_id(row))
        }
        semantic_provider_obligations_by_contract = semantic_provider_obligation_ids_by_contract(obligation_rows_by_id)

        provider_contract_owners: dict[str, set[str]] = {}
        provider_obligation_owners: dict[str, set[str]] = {}
        for task_id, raw_task in dag_tasks.items():
            task = as_dict(raw_task)
            task_module = cell_text(task.get("primary_module"))
            task_provides_obligations = set(map(str, as_list(task.get("provides_obligations"))))
            for contract_id in map(str, as_list(task.get("provides"))):
                contract = as_dict(contracts.get(contract_id))
                if not contract:
                    errors.append(f"{change_dir / 'task-dag.yaml'}: {task_id} provides unknown contract {contract_id}")
                    continue
                provider_contract_owners.setdefault(contract_id, set()).add(str(task_id))
                semantic_ids = semantic_provider_obligations_by_contract.get(contract_id, set())
                if not semantic_ids:
                    errors.append(
                        f"{change_dir / 'task-dag.yaml'}: {task_id} lists provides {contract_id}, but {contract_id} "
                        "has no semantic_contract_edge executable obligation; proof/carrier/composition rows cannot be semantic provides"
                    )
                elif not contract_semantic_provider_is_owner_single(obligation_rows_by_id, contract_id):
                    owner_modules = ", ".join(sorted(semantic_provider_owner_modules_for_contract(obligation_rows_by_id, contract_id)))
                    errors.append(
                        f"{change_dir / 'task-dag.yaml'}: {task_id} lists provides {contract_id}, but semantic provider "
                        f"obligations under {contract_id} have multiple owner modules ({owner_modules}); keep coarse C-xxx "
                        "as a composition index and list only owner-single provides_obligations"
                    )
                elif not semantic_ids <= task_provides_obligations:
                    missing = ", ".join(sorted(semantic_ids - task_provides_obligations))
                    errors.append(
                        f"{change_dir / 'task-dag.yaml'}: {task_id} lists coarse provides {contract_id} without explicitly "
                        f"providing all owner semantic obligations ({missing})"
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
                            f"{change_dir / 'task-dag.yaml'}: {task_id} primary_module {task_module} lists provides {contract_id}, "
                            f"but it does not own semantic provider obligations {', '.join(mismatched)}"
                        )

            for obligation_id in map(str, as_list(task.get("provides_obligations"))):
                if not obligation_id:
                    continue
                if obligation_id_is_coarse_contract(obligation_id):
                    errors.append(
                        f"{change_dir / 'task-dag.yaml'}: {task_id} provides_obligations must use C-xxx-OBL-yyy owner rows, "
                        f"not coarse {obligation_id}"
                    )
                    continue
                if not canonical_provider_ref(obligation_id):
                    errors.append(
                        f"{change_dir / 'task-dag.yaml'}: {task_id} provides_obligations contains non-canonical provider ref {obligation_id}"
                    )
                    continue
                obligation_row = obligation_rows_by_id.get(obligation_id)
                if not obligation_row:
                    errors.append(
                        f"{change_dir / 'task-dag.yaml'}: {task_id} provides_obligations lists {obligation_id}, "
                        "but no active Contract Executable Obligation Matrix row exists"
                    )
                    continue
                edge_type = table_get(obligation_row, "Edge type")
                if not row_is_semantic_provider(obligation_row):
                    errors.append(
                        f"{change_dir / 'task-dag.yaml'}: {task_id} provides_obligations lists {obligation_id}, "
                        f"but its edge_type is {edge_type or '<missing>'}; only semantic_contract_edge provider guarantee obligations can be provided"
                    )
                owner_module = contract_row_owner_module(obligation_row)
                if owner_module and task_module and not owner_modules_compatible(owner_module, task_module):
                    errors.append(
                        f"{change_dir / 'task-dag.yaml'}: {task_id} provides_obligations lists {obligation_id}, "
                        f"but suggested owner module is {owner_module} and task primary_module is {task_module}"
                    )
                provider_obligation_owners.setdefault(obligation_id, set()).add(str(task_id))

        for contract_id, owners in sorted(provider_contract_owners.items()):
            if len(owners) > 1:
                errors.append(
                    f"{change_dir / 'task-dag.yaml'}: {contract_id} has multiple semantic provider owners "
                    f"{', '.join(sorted(owners))}"
                )
        for obligation_id, owners in sorted(provider_obligation_owners.items()):
            if len(owners) > 1:
                errors.append(
                    f"{change_dir / 'task-dag.yaml'}: {obligation_id} has multiple semantic provider owners "
                    f"{', '.join(sorted(owners))}"
                )
        for obligation_id in sorted(obligation_rows_by_id):
            row = obligation_rows_by_id[obligation_id]
            if not row_is_semantic_provider(row):
                continue
            owners = provider_obligation_owners.get(obligation_id, set())
            if len(owners) != 1:
                errors.append(
                    f"{change_dir / 'task-dag.yaml'}: {obligation_id} semantic_contract_edge obligation must have exactly "
                    f"one provides_obligations owner, got {', '.join(sorted(owners)) or 'none'}"
                )

    return errors


def validate_atomic_planning_context_pack(
    change_dir: Path,
    proposal: str,
    spec: str,
    plan: str,
    tasks: str,
    issue_paths: list[Path],
) -> list[str]:
    errors: list[str] = []
    has_task_planning = bool(tasks.strip() or issue_paths)
    if not has_task_planning:
        return errors

    context_path = change_dir / "atomic-planning-context-pack.md"
    context = read(context_path)
    if not context.strip():
        errors.append(
            f"{change_dir}: tasks/atomic issues exist but missing atomic-planning-context-pack.md; "
            "atomic task planning must rehydrate canonical artifacts before generating tasks"
        )
        return errors

    present = headings(context)
    for section_spec, columns in REQUIRED_CONTEXT_PACK_SECTIONS:
        if not has_any_heading(present, section_spec):
            errors.append(f"{context_path}: missing heading ## {heading_options(section_spec)[-1]}")
            continue
        section_text = first_existing_section(context, *heading_options(section_spec))
        if columns and not has_table_columns(section_text, columns):
            errors.append(f"{context_path}: section {heading_options(section_spec)[0]} must include columns {', '.join(columns)}")
        if not has_meaningful_rows(section_text):
            errors.append(f"{context_path}: section {heading_options(section_spec)[0]} has no meaningful data rows")

    if mostly_non_chinese(context):
        errors.append(f"{context_path}: main narrative appears to be English; workflow artifacts must default to Chinese")
    if "TBD" in context or "TODO" in context:
        errors.append(f"{context_path}: contains TBD/TODO")

    source_ledger = first_existing_section(context, "Source Rehydration Ledger", "上下文恢复来源清单")
    if source_ledger:
        for row in table_rows(source_ledger):
            if not row or row[0].lower() == "artifact":
                continue
            joined = " | ".join(row)
            if re.search(r"\b(unread|blocked|missing)\b|未读|阻塞|缺失", joined, re.IGNORECASE) and not re.search(
                r"\b(N/A|not applicable|不适用|irrelevant|superseded|已替代)\b", joined, re.IGNORECASE
            ):
                errors.append(f"{context_path}: Source Rehydration Ledger contains unread/blocked required artifact row: {joined}")

    semantic_index = first_existing_section(context, "Upstream Semantic Index", "上游语义索引")
    upstream_ids = ids(UPSTREAM_ID_PATTERN, proposal + "\n" + spec + "\n" + plan + "\n" + tasks)
    for upstream_id in sorted(upstream_ids):
        if upstream_id not in semantic_index:
            errors.append(f"{context_path}: upstream object {upstream_id} missing from Upstream Semantic Index")

    for row in table_rows(semantic_index):
        if not row or row[0].lower() == "object id":
            continue
        joined = " | ".join(row)
        if re.search(r"\b(REQ|SCN|PDEC|ADEC|DEC|C|MIG|VER)-\d{3}\b", joined):
            cjk = len(CJK_RE.findall(joined))
            if cjk < 12 and not re.search(r"\b(N/A|not applicable|不适用)\b", joined, re.IGNORECASE):
                errors.append(f"{context_path}: Upstream Semantic Index row appears ID-only without executable semantics: {joined}")
        if re.search(r"\b(blocked|unknown|missing|待确认|未知|阻塞)\b", joined, re.IGNORECASE):
            errors.append(f"{context_path}: Upstream Semantic Index contains unresolved row: {joined}")

    context_index_text = "\n".join(
        [
            semantic_index,
            first_existing_section(context, "Module And Contract Pack", "Module and Contract Pack", "模块与契约包"),
            first_existing_section(context, "Frontend Action Pack", "前端 Action Pack", "前端动作包"),
            first_existing_section(
                context,
                "Mock / Acceptance Runtime Pack",
                "Mock Runtime Playground Pack",
                "Mock/Runtime/Playground Pack",
                "Mock 运行时 Playground 包",
            ),
            first_existing_section(context, "Verification Pack", "验证包"),
            first_existing_section(context, "Task Generation Constraints", "任务生成约束"),
        ]
    )

    issue_ids = {path.stem.split("-", 1)[0] for path in issue_paths}
    task_ids = ids(r"\b(T\d{3})\b", tasks)
    for task_id in sorted(issue_ids | task_ids):
        if task_id not in context:
            errors.append(f"{context_path}: task {task_id} missing from context pack traceability")

    all_issue_text = "\n".join(read(path) for path in issue_paths)
    for issue_id in sorted(issue_ids):
        issue_text = next((read(path) for path in issue_paths if path.stem.startswith(issue_id)), "")
        issue_source_ids = ids(UPSTREAM_ID_PATTERN, issue_text)
        for source_id in sorted(issue_source_ids):
            if source_id not in context_index_text:
                errors.append(f"{context_path}: {issue_id} references {source_id} but context pack lacks executable source/contract/verification row")

    if re.search(r"\b(REQ|SCN|PDEC|ADEC|DEC|C|MIG|VER)-\d{3}\b", all_issue_text) and not semantic_index:
        errors.append(f"{context_path}: atomic issues reference upstream objects but Context Pack lacks Upstream Semantic Index")

    if "Atomic Planning Context Pack" not in tasks and "atomic-planning-context-pack" not in tasks:
        errors.append(f"{change_dir / 'tasks.md'}: tasks.md must link or summarize atomic-planning-context-pack.md")

    return errors


def validate_atomic_issue_packets(change_dir: Path, tasks: str, issue_paths: list[Path]) -> list[str]:
    errors: list[str] = []
    if not tasks.strip() and not issue_paths:
        return errors

    packet_path = change_dir / "atomic-issue-packets.yaml"
    if not packet_path.exists():
        errors.append(
            f"{change_dir}: missing atomic-issue-packets.yaml; Atomic Issues must be compiled from per-task sealed context packets"
        )
        return errors

    compiler = Path(__file__).with_name("atomic_issue_compile.py")
    result = subprocess.run(
        [sys.executable, str(compiler), str(change_dir), "--check"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        for line in output.splitlines():
            if line.strip():
                errors.append(f"atomic_issue_compile: {line.strip()}")

    dag_doc = read_yaml(change_dir / "task-dag.yaml")
    packet_doc = read_yaml(packet_path)
    dag_tasks = as_dict(dag_doc.get("tasks"))
    packets = as_dict(packet_doc.get("packets"))
    allowed_provider_refs_by_task: dict[str, set[str]] = {}
    for task_id, raw_task in dag_tasks.items():
        task = as_dict(raw_task)
        allowed = set(map(str, as_list(task.get("provides"))))
        for obligation_id in map(str, as_list(task.get("provides_obligations"))):
            if canonical_provider_ref(obligation_id):
                allowed.add(obligation_id)
        allowed_provider_refs_by_task[str(task_id)] = allowed

    for task_id, raw_task in dag_tasks.items():
        task = as_dict(raw_task)
        packet = as_dict(packets.get(task_id))
        if not packet:
            errors.append(f"{packet_path}: {task_id} missing packet")
            continue
        expected_provider_refs = allowed_provider_refs_by_task.get(str(task_id), set())
        provided_rows = [as_dict(row) for row in as_list(packet.get("provided_contract_obligations"))]
        for row in provided_rows:
            contract_ref = cell_text(row.get("contract"))
            if contract_ref:
                if not canonical_provider_ref(contract_ref):
                    errors.append(
                        f"{packet_path}: {task_id} provided_contract_obligations uses non-canonical provider ref {contract_ref}; "
                        "carrier/proof rows belong in preconditions/carriers/verification, not provider obligations"
                    )
                elif contract_ref not in expected_provider_refs:
                    errors.append(
                        f"{packet_path}: {task_id} provided_contract_obligations claims {contract_ref}, "
                        "but task-dag.yaml does not list it in provides/provides_obligations"
                    )
            for claimed_ref in provider_claim_refs(row):
                if claimed_ref not in expected_provider_refs:
                    errors.append(
                        f"{packet_path}: {task_id} provided_contract_obligations text claims provider ownership of {claimed_ref}, "
                        "but task-dag.yaml does not list it in provides/provides_obligations"
                    )
        for field_name, value in [
            ("atomicity_review", packet.get("atomicity_review")),
            ("module/scope", [
                packet.get("title"),
                packet.get("module_responsibility"),
                packet.get("owned_state_data_resources"),
                packet.get("scope"),
            ]),
        ]:
            for claimed_ref in provider_claim_refs(value):
                if claimed_ref not in expected_provider_refs:
                    errors.append(
                        f"{packet_path}: {task_id} {field_name} claims provider ownership of {claimed_ref}, "
                        "but task-dag.yaml does not list it in provides/provides_obligations"
                    )

    return errors


def packet_execution_text(packet: dict) -> str:
    return flatten_text({field: packet.get(field) for field in DECISION_SURFACE_EXECUTION_FIELDS})


def validate_decision_surface_discovery(
    change_dir: Path,
    proposal: str,
    spec: str,
    plan: str,
    tasks: str,
    stage: str,
) -> list[str]:
    errors: list[str] = []
    combined = "\n".join([proposal, spec, plan, tasks, read(change_dir / "source-intake-ledger.md")])
    if stage == "source-intake" or not combined.strip():
        return errors

    required_by_signal = bool(DECISION_SURFACE_SIGNAL_RE.search(combined))
    surface_path = change_dir / "decision-surface-discovery.md"
    surface_text = read(surface_path)
    if required_by_signal and not surface_text.strip():
        errors.append(
            f"{change_dir}: missing decision-surface-discovery.md; "
            "mode/mutation/frontend/post-create/mock signals require discovering decision surfaces before locking decisions"
        )
        return errors
    if not surface_text.strip():
        return errors
    workflow_state = read_yaml(change_dir / "workflow-state.yaml")
    stage_status = workflow_state.get("stage_status", {}) if isinstance(workflow_state.get("stage_status"), dict) else {}

    required_sections = ["Decision Surface Inventory", "Owner Assignment Gate"]
    if MODE_SURFACE_SIGNAL_RE.search(combined):
        required_sections.append("Mode Consumer Matrix")
    if POST_CREATE_SURFACE_SIGNAL_RE.search(combined):
        required_sections.append("Post-Create Consumer Audit")
    if FRONTEND_SURFACE_SIGNAL_RE.search(combined):
        required_sections.append("Frontend Action Surface Graph")
    if re.search(r"\bcapability\b|能力|logs|metrics|connector|events|workers|update-config|resize", combined, re.IGNORECASE):
        required_sections.append("Capability Support Matrix")
    for section_name in required_sections:
        section_text = first_existing_section(surface_text, section_name)
        if not section_text:
            errors.append(f"{surface_path}: missing required section ## {section_name}")
        elif not has_meaningful_rows(section_text):
            errors.append(f"{surface_path}: section {section_name} must include concrete non-placeholder rows")

    inventory = first_existing_section(surface_text, "Decision Surface Inventory")
    if inventory and not has_table_columns(
        inventory,
        [
            "Surface ID",
            "Surface type",
            "Object/capability/action",
            "Required decision",
            "Decision owner stage",
            "Blocks next stage",
        ],
    ):
        errors.append(
            f"{surface_path}: Decision Surface Inventory must include Surface ID, Surface type, "
            "Object/capability/action, Required decision, Decision owner stage, and Blocks next stage"
        )

    owner_gate = first_existing_section(surface_text, "Owner Assignment Gate")
    if owner_gate and not has_table_columns(
        owner_gate,
        [
            "Surface ID",
            "Derived decision/contract/verification",
            "Owner issue",
            "Copied into packet section",
            "Execution obligation",
            "Pass-task evidence required",
            "Status",
        ],
    ):
        errors.append(
            f"{surface_path}: Owner Assignment Gate must include Surface ID, derived decision/contract/verification, "
            "Owner issue, copied packet section, execution obligation, pass-task evidence, and status"
        )

    known_surface_ids: set[str] = set()
    surface_types: dict[str, str] = {}
    owner_stage_by_surface: dict[str, str] = {}
    inventory_row_by_surface: dict[str, str] = {}
    owner_by_surface: dict[str, str] = {}
    obligation_by_surface: dict[str, str] = {}
    copied_by_surface: dict[str, list[str]] = {}
    owner_gate_row_by_surface: dict[str, str] = {}
    n_a_surfaces: set[str] = set()
    planning_stage = stage in {"all", "task-planning", "pre-execution"}

    def is_locked_na(text: str) -> bool:
        return bool(DECISION_SURFACE_LOCKED_NA_RE.search(text))

    def is_blocked_backflow(text: str) -> bool:
        return bool(DECISION_SURFACE_BLOCKED_BACKFLOW_RE.search(text))

    def has_open_decision_surface_value(text: str) -> bool:
        if is_locked_na(text) or is_blocked_backflow(text):
            return False
        return bool(OPEN_DECISION_SURFACE_RE.search(text))

    def is_decision_surface_closed(text: str) -> bool:
        return bool(is_locked_na(text) or is_blocked_backflow(text) or DECISION_SURFACE_CLOSED_RE.search(text))

    for row in table_dicts(inventory):
        surface_id = table_get(row, "Surface ID")
        if not surface_id or surface_id.lower() == "surface id":
            continue
        if not DECISION_SURFACE_ID_RE.fullmatch(surface_id):
            errors.append(f"{surface_path}: invalid Surface ID {surface_id}; use DS-xxx")
            continue
        known_surface_ids.add(surface_id)
        surface_type = table_get(row, "Surface type")
        surface_types[surface_id] = surface_type
        if surface_type not in DECISION_SURFACE_ALLOWED_TYPES:
            errors.append(f"{surface_path}: {surface_id} has invalid Surface type {surface_type}")
        owner_stage = table_get(row, "Decision owner stage")
        joined = " | ".join(row.values())
        owner_stage_by_surface[surface_id] = owner_stage
        inventory_row_by_surface[surface_id] = joined
        if owner_stage not in DECISION_SURFACE_OWNER_STAGES:
            errors.append(f"{surface_path}: {surface_id} has invalid Decision owner stage {owner_stage}")
        if has_open_decision_surface_value(joined):
            errors.append(f"{surface_path}: {surface_id} still has open/unknown/blocked decision surface values")
        required_decision = table_get(row, "Required decision")
        if len(required_decision) < 12:
            errors.append(f"{surface_path}: {surface_id} Required decision is too thin")

    for row in table_dicts(owner_gate):
        surface_id = table_get(row, "Surface ID")
        if not surface_id or surface_id.lower() == "surface id":
            continue
        if not DECISION_SURFACE_ID_RE.fullmatch(surface_id):
            errors.append(f"{surface_path}: Owner Assignment Gate has invalid Surface ID {surface_id}")
            continue
        owner_issue = table_get(row, "Owner issue")
        copied = table_get(row, "Copied into packet section")
        obligation = table_get(row, "Execution obligation")
        status = table_get(row, "Status")
        if is_locked_na(" | ".join(row.values())):
            n_a_surfaces.add(surface_id)
        owner_by_surface[surface_id] = owner_issue
        obligation_by_surface[surface_id] = obligation
        owner_gate_row_by_surface[surface_id] = " | ".join(row.values())
        copied_by_surface[surface_id] = [
            item.strip().strip("`")
            for item in re.split(r"[,，/;；\s]+", copied)
            if item.strip()
        ]
        if has_open_decision_surface_value(" | ".join(row.values())):
            errors.append(f"{surface_path}: Owner Assignment Gate row {surface_id} is open/unknown/blocked")
        if len(obligation) < 16:
            errors.append(f"{surface_path}: Owner Assignment Gate row {surface_id} Execution obligation is too thin")
        if surface_id not in n_a_surfaces:
            if planning_stage and not re.fullmatch(r"T\d{3}", owner_issue):
                errors.append(f"{surface_path}: {surface_id} must have concrete Owner issue Txxx or locked N/A")
            if planning_stage and not copied_by_surface[surface_id]:
                errors.append(f"{surface_path}: {surface_id} must name Copied into packet section")
            if planning_stage:
                for target in copied_by_surface[surface_id]:
                    if target in DECISION_SURFACE_APPENDIX_ONLY_FIELDS:
                        errors.append(f"{surface_path}: {surface_id} copied into {target}, which is source/appendix only")
                    elif target not in DECISION_SURFACE_EXECUTION_FIELDS:
                        errors.append(f"{surface_path}: {surface_id} copied section {target} is not a recognized execution packet section")
        if re.search(r"\bpass(?:ed)?\b|通过|done|完成", status, re.IGNORECASE) and surface_id not in n_a_surfaces:
            evidence = table_get(row, "Pass-task evidence required")
            if len(evidence) < 16:
                errors.append(f"{surface_path}: {surface_id} cannot pass without concrete pass-task evidence requirement")

    for surface_id in sorted(known_surface_ids):
        if surface_id not in owner_by_surface:
            errors.append(f"{surface_path}: {surface_id} missing from Owner Assignment Gate")
            continue
        owner_stage = owner_stage_by_surface.get(surface_id, "")
        owner_workflow_stage = DECISION_SURFACE_STAGE_ALIASES.get(owner_stage)
        owner_stage_is_due = owner_workflow_stage and (
            stage_status.get(owner_workflow_stage) == "passed" or stage == owner_workflow_stage
        )
        if owner_stage_is_due and surface_id not in n_a_surfaces:
            combined_row = " | ".join(
                [
                    inventory_row_by_surface.get(surface_id, ""),
                    owner_gate_row_by_surface.get(surface_id, ""),
                    owner_by_surface.get(surface_id, ""),
                    obligation_by_surface.get(surface_id, ""),
                ]
            )
            if ROUTED_DECISION_SURFACE_RE.search(combined_row) or not is_decision_surface_closed(combined_row):
                stage_reason = "is being signed off" if stage == owner_workflow_stage else "is already passed"
                errors.append(
                    f"{surface_path}: {surface_id} owner stage {owner_stage} {stage_reason}, "
                    "but the decision surface is still routed/stage-owned instead of closed as locked decision/contract/verification/Txxx, locked N/A, or blocked backflow"
                )

    mode_matrix = first_existing_section(surface_text, "Mode Consumer Matrix")
    if mode_matrix:
        for row in table_dicts(mode_matrix):
            joined = " | ".join(row.values())
            if has_open_decision_surface_value(joined):
                errors.append(f"{surface_path}: Mode Consumer Matrix contains open row: {joined}")
            if planning_stage and not table_get(row, "Owner issue") and not re.search(r"not-applicable|not applicable|N/A|不适用", joined, re.IGNORECASE):
                errors.append(f"{surface_path}: Mode Consumer Matrix row lacks Owner issue or explicit N/A: {joined}")

    capability_matrix = first_existing_section(surface_text, "Capability Support Matrix")
    if capability_matrix:
        for row in table_dicts(capability_matrix):
            joined = " | ".join(row.values())
            if has_open_decision_surface_value(joined):
                errors.append(f"{surface_path}: Capability Support Matrix contains open row: {joined}")
            if planning_stage and not table_get(row, "Owner issue") and not re.search(r"not-applicable|not applicable|N/A|不适用", joined, re.IGNORECASE):
                errors.append(f"{surface_path}: Capability Support Matrix row lacks Owner issue or explicit N/A: {joined}")

    if stage not in {"task-planning", "pre-execution", "all"}:
        return errors

    packet_doc = read_yaml(change_dir / "atomic-issue-packets.yaml")
    packets = as_dict(packet_doc.get("packets"))
    if not packets:
        errors.append(f"{change_dir}: decision surfaces exist but atomic-issue-packets.yaml has no packets")
        return errors

    for surface_id in sorted(known_surface_ids - n_a_surfaces):
        owner = owner_by_surface.get(surface_id, "")
        if not owner:
            continue
        packet = as_dict(packets.get(owner))
        if not packet:
            errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: owner packet {owner} for {surface_id} is missing")
            continue
        surface_rows = [as_dict(row) for row in as_list(packet.get("decision_surfaces"))]
        packet_surface = next((row for row in surface_rows if row.get("surface_id") == surface_id), None)
        if not packet_surface:
            errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: {surface_id} is not copied into owner packet {owner}.decision_surfaces")
            continue
        if packet_surface.get("surface_type") != surface_types.get(surface_id):
            errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: {owner}.{surface_id} surface_type differs from discovery")
        packet_copied = {str(item).strip() for item in as_list(packet_surface.get("copied_to"))}
        for target in copied_by_surface.get(surface_id, []):
            if target not in packet_copied:
                errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: {owner}.{surface_id} missing copied_to target {target}")
        if surface_types.get(surface_id) == "persistent-mutation" and not as_list(packet.get("persistent_mutation_proofs")):
            errors.append(
                f"{change_dir / 'atomic-issue-packets.yaml'}: {owner}.{surface_id} is persistent-mutation "
                "but owner packet lacks persistent_mutation_proofs"
            )
        if surface_types.get(surface_id) == "runtime-lifecycle" and not as_list(packet.get("stateful_behavior")):
            errors.append(
                f"{change_dir / 'atomic-issue-packets.yaml'}: {owner}.{surface_id} is runtime-lifecycle "
                "but owner packet lacks stateful_behavior"
            )
        execution_text = packet_execution_text(packet)
        obligation = obligation_by_surface.get(surface_id, "")
        if obligation and not semantic_payload_copied(obligation, execution_text):
            errors.append(
                f"{change_dir / 'atomic-issue-packets.yaml'}: {owner}.{surface_id} execution obligation is not materialized "
                "in execution-facing packet sections"
            )

    return errors


def validate_external_capability_research(
    change_dir: Path,
    proposal: str,
    spec: str,
    plan: str,
    tasks: str,
    stage: str,
) -> list[str]:
    errors: list[str] = []
    if stage in {"source-intake", "prd"}:
        return errors
    combined = "\n".join([proposal, spec, plan, tasks, read(change_dir / "source-intake-ledger.md")])
    if not combined.strip():
        return errors

    research_path = change_dir / "external-capability-research.md"
    research = read(research_path)
    required_by_signal = bool(EXTERNAL_CAPABILITY_SIGNAL_RE.search(combined))
    if required_by_signal and not research.strip():
        errors.append(
            f"{change_dir}: missing external-capability-research.md; "
            "external/cloud/K8s/runtime/autoscaling/mock dependency signals require official capability research before AIP/design/contract/task planning"
        )
        return errors
    if not research.strip():
        return errors

    required_sections = [
        "Research Source Inventory",
        "External Capability Fact Matrix",
        "Capability Support / Non-Support Matrix",
        "External Mechanism Explanation Matrix",
        "External Mechanism Decision Matrix",
        "External Constraint Matrix",
        "Design Implication Matrix",
        "Research Consumption Gate",
    ]
    if re.search(r"\bmock|no-cloud|fixture|repo-specific acceptance runtime|acceptance runtime|模拟|验收|无云\b", combined + "\n" + research, re.IGNORECASE):
        required_sections.append("Mock / Acceptance Runtime External Boundary Map")
    section_aliases = {
        "Mock / Acceptance Runtime External Boundary Map": (
            "Mock / Acceptance Runtime External Boundary Map",
            "Mock / Playground External Boundary Map",
        ),
    }
    for section_name in required_sections:
        section_text = first_existing_section(research, *section_aliases.get(section_name, (section_name,)))
        if not section_text:
            errors.append(f"{research_path}: missing required section ## {section_name}")
        elif not has_meaningful_rows(section_text):
            errors.append(f"{research_path}: section {section_name} must include concrete non-placeholder rows")

    source_inventory = first_existing_section(research, "Research Source Inventory")
    if source_inventory and not has_table_columns(
        source_inventory,
        ["Source ID", "System/provider", "Source type", "URL/path/command", "Official?", "Read status", "Used for", "Confidence"],
    ):
        errors.append(f"{research_path}: Research Source Inventory must include source/system/type/path/official/read status/used/confidence columns")
    has_official_or_real_source = False
    for row in table_dicts(source_inventory):
        joined = " | ".join(row.values())
        if EXTERNAL_RESEARCH_BLOCKED_RE.search(joined):
            errors.append(f"{research_path}: Research Source Inventory contains unread/blocked/open source row: {joined}")
        if re.search(r"\b(?:yes|true|official|sdk|api reference|standard|adapter|source|sample|真实|官方|源码|样例)\b", joined, re.IGNORECASE):
            has_official_or_real_source = True
    if source_inventory and not has_official_or_real_source:
        errors.append(f"{research_path}: at least one official document, SDK/API reference, standard, real adapter/source, or real response sample is required")

    fact_matrix = first_existing_section(research, "External Capability Fact Matrix")
    if fact_matrix and not has_table_columns(
        fact_matrix,
        ["Fact ID", "Source ID", "External system", "Capability/API/resource", "Official fact", "Preconditions/limits", "Failure behavior", "Confidence", "Downstream impact"],
    ):
        errors.append(f"{research_path}: External Capability Fact Matrix must include fact/source/system/capability/official fact/limits/failure/confidence/downstream columns")
    fact_ids: set[str] = set()
    for row in table_dicts(fact_matrix):
        fact_id = table_get(row, "Fact ID")
        if fact_id and fact_id.lower() != "fact id":
            if not EXTERNAL_FACT_ID_RE.fullmatch(fact_id):
                errors.append(f"{research_path}: invalid Fact ID {fact_id}; use FACT-xxx or EXT-xxx")
            fact_ids.add(fact_id)
        joined = " | ".join(row.values())
        if EXTERNAL_RESEARCH_BLOCKED_RE.search(joined):
            errors.append(f"{research_path}: External Capability Fact Matrix contains blocked/open/unknown row: {joined}")
        if len(table_get(row, "Official fact")) < 20:
            errors.append(f"{research_path}: fact {fact_id or '<missing>'} Official fact is too thin")
        if len(table_get(row, "Downstream impact")) < 8:
            errors.append(f"{research_path}: fact {fact_id or '<missing>'} lacks Downstream impact")

    support_matrix = first_existing_section(research, "Capability Support / Non-Support Matrix")
    for row in table_dicts(support_matrix):
        joined = " | ".join(row.values())
        supported = table_get(row, "Supported?")
        if supported and supported not in {"yes", "partial", "no", "unknown-blocking"}:
            errors.append(f"{research_path}: Supported? must be yes/partial/no/unknown-blocking: {joined}")
        if "unknown-blocking" in supported:
            errors.append(f"{research_path}: Capability Support Matrix has unknown-blocking row: {joined}")
        if supported in {"partial", "no"} and len(table_get(row, "User-visible behavior")) < 8:
            errors.append(f"{research_path}: partial/no capability must define user-visible behavior: {joined}")

    mechanism_matrix = first_existing_section(research, "External Mechanism Decision Matrix")
    mechanism_explanation = first_existing_section(research, "External Mechanism Explanation Matrix")
    if mechanism_explanation and not has_table_columns(
        mechanism_explanation,
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
        errors.append(
            f"{research_path}: External Mechanism Explanation Matrix must include mechanism principle, API/resource/metric, parameter meanings, lifecycle behavior, failure semantics, and required mechanism-design row"
        )
    for row in table_dicts(mechanism_explanation):
        mechanism_id = table_get(row, "Mechanism ID")
        joined = " | ".join(row.values())
        if EXTERNAL_RESEARCH_BLOCKED_RE.search(joined):
            errors.append(f"{research_path}: External Mechanism Explanation Matrix contains blocked/open/unknown row: {joined}")
        if MECHANISM_PLACEHOLDER_RE.search(joined):
            errors.append(f"{research_path}: External Mechanism Explanation Matrix contains template placeholder/generic mechanism text: {joined}")
        for label, min_len in [
            ("Mechanism principle", 24),
            ("Key API/resource/metric", 8),
            ("Key parameters and meanings", 20),
            ("Lifecycle create/update/delete/prune behavior", 16),
            ("Failure/permission/metric semantics", 16),
            ("Required mechanism-design row", 8),
        ]:
            if len(table_get(row, label)) < min_len:
                errors.append(f"{research_path}: mechanism explanation {mechanism_id or '<missing>'} {label} is too thin")
        if mechanism_id and not re.fullmatch(r"(?:MECH|EXTMECH)-\d{3}", mechanism_id):
            errors.append(f"{research_path}: invalid Mechanism ID {mechanism_id}; use MECH-xxx or EXTMECH-xxx")
        if not MECHANISM_MODEL_ID_RE.search(table_get(row, "Required mechanism-design row")):
            errors.append(f"{research_path}: mechanism explanation {mechanism_id or '<missing>'} must map to mechanism-design-model.md row")

    mechanism_ids: set[str] = set()
    if mechanism_matrix and not has_table_columns(
        mechanism_matrix,
        [
            "Mechanism ID",
            "Product semantic",
            "External system",
            "Official mechanism/API/resource",
            "AutoMQ field mapping",
            "Non-equivalent / unsupported semantic",
            "Failure/permission/metric-missing behavior",
            "Required DEC/ADEC",
            "Required contract",
            "Required verification",
            "Owner task / packet carrier",
        ],
    ):
        errors.append(
            f"{research_path}: External Mechanism Decision Matrix must include mechanism id, product semantic, "
            "external system, official mechanism/API/resource, field mapping, unsupported semantic, failure/permission/metric behavior, DEC/C/VER, and owner task/packet carrier"
        )
    for row in table_dicts(mechanism_matrix):
        mechanism_id = table_get(row, "Mechanism ID")
        if mechanism_id and mechanism_id.lower() != "mechanism id":
            if not re.fullmatch(r"(?:MECH|EXTMECH)-\d{3}", mechanism_id):
                errors.append(f"{research_path}: invalid Mechanism ID {mechanism_id}; use MECH-xxx or EXTMECH-xxx")
            mechanism_ids.add(mechanism_id)
        joined = " | ".join(row.values())
        if EXTERNAL_RESEARCH_BLOCKED_RE.search(joined):
            errors.append(f"{research_path}: External Mechanism Decision Matrix contains blocked/open/unknown row: {joined}")
        required_values = [
            ("Product semantic", 12),
            ("Official mechanism/API/resource", 16),
            ("AutoMQ field mapping", 16),
            ("Non-equivalent / unsupported semantic", 8),
            ("Failure/permission/metric-missing behavior", 12),
            ("Required DEC/ADEC", 4),
            ("Required contract", 3),
            ("Required verification", 5),
            ("Owner task / packet carrier", 4),
        ]
        for label, min_len in required_values:
            if len(table_get(row, label)) < min_len:
                errors.append(f"{research_path}: mechanism {mechanism_id or '<missing>'} {label} is too thin")
        if not re.search(r"\b(?:DEC|ADEC|PDEC|READY-DEC|DESIGN-DEC)-\d{3}\b", table_get(row, "Required DEC/ADEC")):
            errors.append(f"{research_path}: mechanism {mechanism_id or '<missing>'} must map to a DEC/ADEC")
        if not re.search(r"\bC-\d{3}\b", table_get(row, "Required contract")):
            errors.append(f"{research_path}: mechanism {mechanism_id or '<missing>'} must map to a C-xxx contract")
        if not re.search(r"\bVER-\d{3}\b", table_get(row, "Required verification")):
            errors.append(f"{research_path}: mechanism {mechanism_id or '<missing>'} must map to a VER-xxx verification")
        if not re.search(r"\bT\d{3}\b|packet|carrier|semantic", table_get(row, "Owner task / packet carrier"), re.IGNORECASE):
            errors.append(f"{research_path}: mechanism {mechanism_id or '<missing>'} must map to an owner task or packet carrier")

    constraint_matrix = first_existing_section(research, "External Constraint Matrix")
    constraint_ids: set[str] = set()
    for row in table_dicts(constraint_matrix):
        constraint_id = table_get(row, "Constraint ID")
        if constraint_id and constraint_id.lower() != "constraint id":
            if not EXTERNAL_FACT_ID_RE.fullmatch(constraint_id):
                errors.append(f"{research_path}: invalid Constraint ID {constraint_id}; use CONSTRAINT-xxx or XCON-xxx")
            constraint_ids.add(constraint_id)
        joined = " | ".join(row.values())
        if EXTERNAL_RESEARCH_BLOCKED_RE.search(joined):
            errors.append(f"{research_path}: External Constraint Matrix contains blocked/open/unknown row: {joined}")
        if len(table_get(row, "Required AutoMQ rule")) < 12:
            errors.append(f"{research_path}: constraint {constraint_id or '<missing>'} Required AutoMQ rule is too thin")

    implication_matrix = first_existing_section(research, "Design Implication Matrix")
    consumption_gate = first_existing_section(research, "Research Consumption Gate")
    if implication_matrix and not (
        has_table_columns(
            implication_matrix,
            ["Fact/constraint/mechanism", "Affected decision", "Affected module/API", "Required contract", "Required verification", "Status"],
        )
        or has_table_columns(
            implication_matrix,
            ["Fact/constraint", "Affected decision", "Affected module/API", "Required contract", "Required verification", "Status"],
        )
    ):
        errors.append(
            f"{research_path}: Design Implication Matrix must include fact/constraint/mechanism, decision, module/API, contract, verification, and status"
        )
    if consumption_gate and not (
        has_table_columns(
            consumption_gate,
            [
                "Fact/constraint/mechanism",
                "Consumed by ADEC/DEC",
                "Consumed by contract",
                "Consumed by verification",
                "Consumed by semantic carrier / packet",
                "Dropped / N/A reason",
                "Status",
            ],
        )
        or has_table_columns(
            consumption_gate,
            [
                "Fact/constraint",
                "Consumed by ADEC/DEC",
                "Consumed by contract",
                "Consumed by verification",
                "Consumed by semantic carrier / packet",
                "Dropped / N/A reason",
                "Status",
            ],
        )
    ):
        errors.append(
            f"{research_path}: Research Consumption Gate must include ADEC/DEC, contract, verification, semantic carrier/packet, N/A reason, and status"
        )
    for row in table_dicts(implication_matrix) + table_dicts(consumption_gate):
        joined = " | ".join(row.values())
        if EXTERNAL_RESEARCH_BLOCKED_RE.search(joined):
            errors.append(f"{research_path}: research consumption/implication contains blocked/open/unknown row: {joined}")

    if stage not in {"task-planning", "pre-execution", "all"}:
        return errors

    downstream_text = "\n".join([plan, tasks, read(change_dir / "atomic-issue-packets.yaml"), read(change_dir / "atomic-planning-context-pack.md")])
    required_ids = fact_ids | constraint_ids | mechanism_ids
    for object_id in sorted(required_ids):
        row_texts = [
            " | ".join(row.values())
            for row in table_dicts(consumption_gate)
            if object_id in " | ".join(row.values())
        ]
        if row_texts and re.search(r"\blocked\s+N/A\b|locked N/A|not-applicable|not applicable|不适用|Not Run|未运行", "\n".join(row_texts), re.IGNORECASE):
            continue
        if object_id not in downstream_text:
            errors.append(
                f"{research_path}: external fact/constraint/mechanism {object_id} is not consumed by task planning packets/context; "
                "research-only facts cannot enter execution"
            )

    return errors


def validate_boundary_context_pack(
    change_dir: Path,
    filename: str,
    section_names: tuple[str, ...],
    section_specs: list[tuple[str, list[str]]],
    required: bool,
    purpose: str,
    fallback_files: tuple[str, ...] = ("plan.md",),
) -> list[str]:
    errors: list[str] = []
    context_path = change_dir / filename
    context = read(context_path)

    if not context.strip():
        for fallback in fallback_files:
            fallback_text = read(change_dir / fallback)
            for section_name in section_names:
                context = first_existing_section(fallback_text, section_name)
                if context:
                    context_path = change_dir / fallback
                    break
            if context:
                break

    if required and not context.strip():
        errors.append(f"{change_dir}: missing {filename} or plan.md context section for {purpose}")
        return errors
    if not context.strip():
        return errors

    if mostly_non_chinese(context):
        errors.append(f"{context_path}: main narrative appears to be English; workflow artifacts must default to Chinese")
    if "TBD" in context or "TODO" in context:
        errors.append(f"{context_path}: contains TBD/TODO")

    present = headings(context)
    for section_spec, columns in section_specs:
        if not has_any_heading(present, section_spec):
            errors.append(f"{context_path}: missing heading ## {heading_options(section_spec)[-1]} for {purpose}")
            continue
        section_text = first_existing_section(context, *heading_options(section_spec))
        if columns and not has_table_columns(section_text, columns):
            errors.append(f"{context_path}: section {heading_options(section_spec)[0]} must include columns {', '.join(columns)}")
        if not has_meaningful_rows(section_text):
            errors.append(f"{context_path}: section {heading_options(section_spec)[0]} has no meaningful data rows")

    semantic = first_existing_section(context, "Semantic Index", "语义索引", "Acceptance Semantic Index", "验收语义索引")
    for row in table_rows(semantic):
        if not row or row[0].lower() in {"object id", "object"}:
            continue
        joined = " | ".join(row)
        if re.search(r"\b(REQ|SCN|PDEC|ADEC|DEC|C|MIG|VER)-\d{3}\b", joined):
            cjk = len(CJK_RE.findall(joined))
            if cjk < 12 and not re.search(r"\b(N/A|not applicable|不适用)\b", joined, re.IGNORECASE):
                errors.append(f"{context_path}: Semantic Index row appears ID-only without executable semantics: {joined}")
        if re.search(r"\b(blocked|unknown|missing|待确认|未知|阻塞)\b", joined, re.IGNORECASE):
            errors.append(f"{context_path}: Semantic Index contains unresolved row: {joined}")

    source_ledger = first_existing_section(context, "Source Rehydration Ledger", "上下文恢复来源清单")
    for row in table_rows(source_ledger):
        if not row or row[0].lower() == "artifact":
            continue
        joined = " | ".join(row)
        if re.search(r"\b(unread|blocked|missing)\b|未读|阻塞|缺失", joined, re.IGNORECASE) and not re.search(
            r"\b(N/A|not applicable|不适用|irrelevant|superseded|已替代)\b", joined, re.IGNORECASE
        ):
            errors.append(f"{context_path}: Source Rehydration Ledger contains unread/blocked required row: {joined}")

    return errors


def validate_repo_isolation(change_dir: Path, proposal: str, spec: str, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    combined = proposal + "\n" + spec + "\n" + plan + "\n" + tasks
    needs_isolation = re.search(
        r"全新.*worktree|不能参考本地其他分支|forbidden local branch|Repo Isolation|隔离 worktree",
        combined,
        re.IGNORECASE,
    )
    if not needs_isolation:
        return errors

    isolation = first_existing_section(combined, "Repo Isolation Gate", "仓库隔离门禁")
    if not isolation:
        errors.append(f"{change_dir}: repo isolation signals exist but missing Repo Isolation Gate")
        return errors
    if not has_table_columns(
        isolation,
        ["Target repo", "Base branch", "Base commit", "UID", "Worktree path", "Branch name", "Forbidden sources", "Allowed sources"],
    ):
        errors.append(
            f"{change_dir}: Repo Isolation Gate must include target repo, base branch/commit, UID, worktree path, branch name, forbidden and allowed sources"
        )
    if not re.search(r"\bcodex/[^|\n\s]*[0-9a-fA-F]{4,}|codex/[^|\n\s]*(?:uid|UID|uuid)", isolation):
        errors.append(f"{change_dir}: Repo Isolation Gate branch name must use codex/ prefix and unique UID")
    if not re.search(r"Forbidden sources", isolation, re.IGNORECASE) or not re.search(r"其他分支|other worktree|local branch|forbidden", isolation, re.IGNORECASE):
        errors.append(f"{change_dir}: Repo Isolation Gate must explicitly list forbidden local branches/worktrees")
    if re.search(r"\b(?:unknown|TBD|TODO|待确认)\b", isolation, re.IGNORECASE):
        errors.append(f"{change_dir}: Repo Isolation Gate contains unresolved values")
    return errors


def validate_aip_hard_gate(
    change_dir: Path,
    proposal: str,
    spec: str,
    plan: str,
    tasks: str,
    workflow_state: dict,
    contextpack_mode: bool,
) -> list[str]:
    errors: list[str] = []
    combined = proposal + "\n" + spec + "\n" + plan + "\n" + tasks
    has_large_workflow = bool(re.search(r"\bREQ-\d{3}\b|Decision Registry|Module Contract Graph|Atomic Issue|Task DAG", combined))
    aip_signals = bool(re.search(r"AIP|Architecture|Engineering|Terraform|OpenAPI|架构|工程|接口|云资源|部署模式", combined, re.IGNORECASE))
    stage_status = workflow_state.get("stage_status", {}) if isinstance(workflow_state.get("stage_status"), dict) else {}
    aip_not_applicable = stage_status.get("aip") == "not_applicable"
    workflow_meta = workflow_state.get("workflow", {}) if isinstance(workflow_state.get("workflow"), dict) else {}
    profile = str(workflow_meta.get("profile", "full")).strip() or "full"
    profile_requires_aip = profile in {"full", "migration"}
    if contextpack_mode and profile in {"execution-only", "repair"}:
        return errors
    contextpack_requires_aip = contextpack_mode and profile_requires_aip and bool(proposal or spec or plan or tasks)
    if not ((has_large_workflow and aip_signals) or contextpack_requires_aip):
        return errors
    if aip_not_applicable:
        errors.append(f"{change_dir}: AIP Creation Hard Gate cannot be not_applicable for a large engineering workflow")

    aip_path = change_dir / "aip.md"
    aip = read(aip_path)
    if not aip.strip():
        errors.append(f"{change_dir}: large workflow has engineering/AIP signals but missing aip.md; AIP Creation Hard Gate blocks downstream stages")
    else:
        errors.extend(validate_ordered_heading_patterns(aip, AIP_TEMPLATE_HEADINGS, str(aip_path)))
        required = [
            r"背景|Background",
            r"问题|Problem",
            r"Goals|目标",
            r"Non-goals|非目标",
            r"解决方案|Selected architecture|Architecture|架构",
            r"被拒绝|Rejected alternatives|反选",
            r"接口|Interfaces|OpenAPI|Terraform",
            r"数据|状态|任务|Data|State|Task",
            r"部署|cloud|IAM|K8s|ASG|EC2",
            r"观测|Observability|metrics|logs",
            r"兼容|rollback|Compatibility",
            r"验证|Verification",
        ]
        for pattern in required:
            if not re.search(pattern, aip, re.IGNORECASE):
                errors.append(f"{aip_path}: AIP missing required section matching {pattern}")
        if re.search(r"^#+\s*(?:Background / problem|Goals / non-goals|Selected architecture|Rejected alternatives|Interfaces|Data/state/task model|Deployment/cloud/IAM|Observability|Compatibility/rollback|Verification strategy)\s*$", aip, re.IGNORECASE | re.MULTILINE):
            errors.append(f"{aip_path}: engineering-completeness outline must not replace AutoMQ AIP template headings; put these as subsections/tables under the standard template")
        errors.extend(validate_mechanism_design_closure(change_dir, aip, str(aip_path)))
        design_sources = "\n".join(
            [
                plan,
                read(change_dir / "decision-reviews" / "aip-decisions.md"),
                read(change_dir / "external-capability-research.md"),
            ]
        )
        errors.extend(validate_aip_narrative_materialization(change_dir, aip, design_sources, str(aip_path)))

    aip_decision = change_dir / "decision-reviews" / "aip-decisions.md"
    if not read(aip_decision).strip():
        errors.append(f"{change_dir}: missing decision-reviews/aip-decisions.md for AIP decisions")

    if "Engineering Decision Completeness Gate" not in plan and "工程决策完整度门禁" not in plan:
        errors.append(f"{change_dir}: missing Engineering Decision Completeness Gate after AIP")
    return errors


def validate_workflow_state_gate(change_dir: Path, workflow_state: dict, current_stage: str | None = None) -> list[str]:
    errors: list[str] = []
    stage_status = workflow_state.get("stage_status", {}) if isinstance(workflow_state.get("stage_status"), dict) else {}
    stage_receipts = workflow_state.get("stage_receipts", {}) if isinstance(workflow_state.get("stage_receipts"), dict) else {}
    stage_na_receipts = workflow_state.get("stage_na_receipts", {}) if isinstance(workflow_state.get("stage_na_receipts"), dict) else {}
    prerequisite_map = {stage: list(values) for stage, values in STAGE_PREREQUISITES.items()}
    task_planning_upstream_stages = [
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
    ]
    profile_policy = workflow_profile_policy(workflow_state) if workflow_state.get("schema_version") == 2 else {}
    profile_required = {
        str(item).strip()
        for item in profile_policy.get("required_receipt_stages", [])
        if str(item).strip()
    }
    if profile_required:
        prerequisite_map = {
            stage: [
                prerequisite
                for prerequisite in prerequisites
                if prerequisite in profile_required or prerequisite in RUNTIME_PREREQUISITES
            ]
            for stage, prerequisites in prerequisite_map.items()
        }
    whole_stage_na_allowed = {
        str(item).strip()
        for item in profile_policy.get("whole_stage_na_allowed", [])
        if str(item).strip()
    }

    def upstream_hashes(target_stage: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for prerequisite in prerequisite_map.get(target_stage, []):
            if prerequisite == "execution":
                execution_receipt = (
                    workflow_state.get("execution_receipt")
                    if isinstance(workflow_state.get("execution_receipt"), dict)
                    else {}
                )
                receipt_hash = str(execution_receipt.get("receipt_hash", "")).strip()
                if receipt_hash:
                    result[prerequisite] = receipt_hash
                continue
            source = stage_na_receipts if stage_status.get(prerequisite) == "not_applicable" else stage_receipts
            receipt = source.get(prerequisite) if isinstance(source.get(prerequisite), dict) else {}
            receipt_hash = str(receipt.get("receipt_hash", "")).strip()
            if receipt_hash:
                result[prerequisite] = receipt_hash
        return result
    if current_stage:
        receipt_scope = set(prerequisite_map.get(current_stage, []))
        receipt_scope.add(current_stage)
    else:
        receipt_scope = {stage for stage, status in stage_status.items() if status == "passed"}
    for stage, status in stage_status.items():
        if status not in VALID_STAGE_STATUS:
            errors.append(
                f"{change_dir}: workflow-state stage_status.{stage} uses invalid status {status}; "
                "valid gate statuses are passed/not_applicable only after validation, plus not_started/in_progress/blocked/pending-rewrite/pending-rerun"
            )
        if (
            status == "passed"
            and stage in receipt_scope
            and stage != current_stage
            and stage not in {"execution", "acceptance"}
        ):
            receipt = stage_receipts.get(stage) if isinstance(stage_receipts.get(stage), dict) else {}
            if not receipt:
                errors.append(
                    f"{change_dir}: workflow-state stage_status.{stage}=passed without stage_receipts.{stage}; "
                    "do not hand-edit passed, run workflowctl.py pass-stage after validator/rubric passes"
                )
                continue
            if receipt.get("status") != "passed":
                errors.append(f"{change_dir}: workflow-state stage_receipts.{stage}.status must be passed")
            if receipt.get("stage") and receipt.get("stage") != stage:
                errors.append(f"{change_dir}: workflow-state stage_receipts.{stage}.stage mismatch")
            command = str(receipt.get("command", ""))
            if f"validate {stage}" not in command:
                errors.append(f"{change_dir}: workflow-state stage_receipts.{stage}.command must record workflowctl validate {stage}")
            if workflow_state.get("schema_version") == 2 and receipt.get("receipt_hash") != canonical_receipt_hash(receipt):
                errors.append(f"{change_dir}: workflow-state stage_receipts.{stage}.receipt_hash is forged or stale")
            if workflow_state.get("schema_version") == 2:
                recorded_upstream = receipt.get("upstream_stage_receipt_hashes") if isinstance(receipt.get("upstream_stage_receipt_hashes"), dict) else {}
                if recorded_upstream != upstream_hashes(stage):
                    errors.append(f"{change_dir}: workflow-state stage_receipts.{stage}.upstream_stage_receipt_hashes is stale")
            recorded_hashes = receipt.get("artifact_hashes") if isinstance(receipt.get("artifact_hashes"), dict) else {}
            expected_hashes = artifact_digest_map(change_dir, stage)
            for rel in stage_receipt_artifact_rels(change_dir, stage):
                if not (change_dir / rel).exists():
                    errors.append(f"{change_dir}: workflow-state stage_receipts.{stage} required artifact missing: {rel}")
            if not recorded_hashes:
                errors.append(f"{change_dir}: workflow-state stage_receipts.{stage}.artifact_hashes is missing")
            for rel, digest in expected_hashes.items():
                if recorded_hashes.get(rel) != digest:
                    errors.append(
                        f"{change_dir}: workflow-state stage_receipts.{stage} artifact hash mismatch for {rel}; "
                        "stage must be rerun and re-receipted after edits"
                    )
            if stage == "task-planning":
                expected_upstream = upstream_hashes("task-planning")
                recorded_upstream = (
                    receipt.get("upstream_stage_receipt_hashes")
                    if isinstance(receipt.get("upstream_stage_receipt_hashes"), dict)
                    else {}
                )
                if not recorded_upstream and expected_upstream:
                    errors.append(
                        f"{change_dir}: workflow-state stage_receipts.task-planning.upstream_stage_receipt_hashes is missing; "
                        "rerun workflowctl.py pass-stage task-planning to seal Atomic Issues against upstream receipts"
                    )
                elif recorded_upstream != expected_upstream:
                    context = read(change_dir / "atomic-planning-context-pack.md")
                    has_reseal_or_regeneration_evidence = bool(
                        re.search(r"^##+\s+Task Planning (?:Impact Proof|Regeneration Evidence)\b", context, re.MULTILINE)
                    )
                    if not has_reseal_or_regeneration_evidence:
                        errors.append(
                            f"{change_dir}: workflow-state stage_receipts.task-planning upstream receipt hashes are stale; "
                            "upstream semantic artifacts changed after task-planning, regenerate task-planning by default or provide Task Planning Impact Proof before local reseal"
                        )
        if status == "not_applicable" and workflow_state.get("schema_version") == 2:
            receipt = stage_na_receipts.get(stage) if isinstance(stage_na_receipts.get(stage), dict) else {}
            if not receipt:
                errors.append(f"{change_dir}: workflow-state stage_status.{stage}=not_applicable without stage_na_receipts.{stage}")
            else:
                if stage not in whole_stage_na_allowed:
                    errors.append(f"{change_dir}: workflow-state whole-stage N/A is forbidden for {stage}")
                if receipt.get("receipt_hash") != canonical_receipt_hash(receipt):
                    errors.append(f"{change_dir}: workflow-state stage_na_receipts.{stage}.receipt_hash is forged or stale")
                recorded_upstream = receipt.get("upstream_stage_receipt_hashes") if isinstance(receipt.get("upstream_stage_receipt_hashes"), dict) else {}
                if recorded_upstream != upstream_hashes(stage):
                    errors.append(f"{change_dir}: workflow-state stage_na_receipts.{stage}.upstream_stage_receipt_hashes is stale")

    execution_status = stage_status.get("execution")
    execution_receipt = workflow_state.get("execution_receipt") if isinstance(workflow_state.get("execution_receipt"), dict) else {}
    if execution_receipt and execution_status == "not_started":
        errors.append(f"{change_dir}: execution_receipt exists but stage_status.execution is not_started")
    if execution_status and execution_status != "not_started" and not execution_receipt:
        errors.append(f"{change_dir}: execution={execution_status} without execution_receipt; run workflowctl.py begin-execution")
    if execution_receipt:
        if execution_receipt.get("status") != "started":
            errors.append(f"{change_dir}: execution_receipt.status must be started")
        if workflow_state.get("schema_version") == 2 and execution_receipt.get("receipt_hash") != canonical_receipt_hash(execution_receipt):
            errors.append(f"{change_dir}: execution_receipt.receipt_hash is forged or stale")
        recorded_stage_receipts = (
            execution_receipt.get("stage_receipt_hashes")
            if isinstance(execution_receipt.get("stage_receipt_hashes"), dict)
            else {}
        )
        if workflow_state.get("schema_version") == 2 and recorded_stage_receipts != upstream_hashes("pre-execution"):
            errors.append(f"{change_dir}: execution_receipt.stage_receipt_hashes is stale")
        recorded = execution_receipt.get("artifact_hashes") if isinstance(execution_receipt.get("artifact_hashes"), dict) else {}
        expected = artifact_digest_map(change_dir, "pre-execution")
        for rel, digest in expected.items():
            if recorded.get(rel) != digest:
                errors.append(f"{change_dir}: execution_receipt artifact hash mismatch for {rel}; re-run pre-execution and begin-execution")
        sealed_recorded = execution_receipt.get("sealed_artifact_hashes") if isinstance(execution_receipt.get("sealed_artifact_hashes"), dict) else {}
        sealed_expected = sealed_artifact_digest_map(change_dir)
        for rel, digest in sealed_expected.items():
            if sealed_recorded.get(rel) != digest:
                errors.append(
                    f"{change_dir}: execution_receipt sealed artifact hash mismatch for {rel}; "
                    "planning artifacts changed after execution started"
                )
        changed_planning = sorted(rel for rel in changed_paths_relative_to_change(change_dir) if not mutable_execution_path(rel))
        for rel in changed_planning:
            path = change_dir / rel
            if path.exists() and sealed_recorded.get(rel) == artifact_receipt_digest(path, rel):
                continue
            errors.append(
                f"{change_dir}: sealed planning artifact changed during execution: {rel}; "
                "write execution evidence to task-verification-log.yaml, task-semantic-review.yaml, "
                "mock-acceptance-execution.yaml, or task-receipts instead"
            )

    if execution_status and execution_status != "not_started" and not execution_receipt:
        repo_root = git_root_for(change_dir)
        if repo_root is not None:
            try:
                change_rel = change_dir.resolve().relative_to(repo_root.resolve()).as_posix()
                outside_changes = sorted(
                    path
                    for path in git_changed_paths(repo_root)
                    if path != change_rel and not path.startswith(f"{change_rel}/")
                )
            except ValueError:
                outside_changes = []
            if outside_changes:
                preview = ", ".join(outside_changes[:12])
                suffix = "" if len(outside_changes) <= 12 else f", ... (+{len(outside_changes) - 12} more)"
                errors.append(
                    f"{change_dir}: workflow-state says execution={execution_status} while non-spec code/worktree changes exist before artifact gates pass: "
                    f"{preview}{suffix}"
                )
    return errors


def validate_not_run(change_dir: Path, tasks: str, plan: str) -> list[str]:
    errors: list[str] = []
    combined = tasks + "\n" + plan
    not_run = first_existing_section(combined, "Not Run", "Not Run Risk Table", "未运行", "未验证风险")
    if not_run:
        if re.search(r"\b(Not Run Risk Table|Not Run)\b", combined) and not has_any_pattern(
            not_run, r"Severity", r"Blocks done", r"Owner", r"approval", r"Source", r"严重级别", r"阻塞完成"
        ):
            errors.append(f"{change_dir}: Not Run table must include Source, Severity, Owner/approval, and Blocks done")
        if section_contains_blocking_not_run(not_run):
            if not re.search(r"risk-accepted-by-user|用户.*接受|owner.*approval|批准", not_run, re.IGNORECASE):
                errors.append(f"{change_dir}: Not Run contains P0/P1 or Blocks done item without explicit risk acceptance; cannot mark done")
            if re.search(r"\b(done|completed|完成)\b", tasks, re.IGNORECASE):
                errors.append(f"{change_dir}: tasks appear done while blocking Not Run items exist")
    return errors


def validate_backflow(change_dir: Path, tasks: str, plan: str, all_issue_text: str, decision_text: str) -> list[str]:
    errors: list[str] = []
    combined = plan + "\n" + tasks + "\n" + decision_text
    has_backflow_signal = re.search(r"Backflow Trigger|Backflow Invalidation|Supersession Record|superseded|pending-rewrite|pending-rerun|回流|失效|被替代", combined, re.IGNORECASE)
    backflow_columns = ["Trigger ID", "Invalidated artifacts", "Invalidated decisions", "Invalidated contracts", "Invalidated Atomic Issues", "Verification to rerun", "New status"]
    backflow = first_section_with_columns(combined, ["Backflow Invalidation Matrix", "回流失效矩阵"], backflow_columns)
    trigger = first_existing_section(combined, "Backflow Trigger", "回流触发")
    supersession = first_existing_section(combined, "Supersession Record", "替代记录")

    if has_backflow_signal and not backflow:
        errors.append(f"{change_dir}: backflow/supersession signal exists but missing Backflow Invalidation Matrix")
    if backflow and not has_table_columns(backflow, backflow_columns):
        errors.append(
            f"{change_dir}: Backflow Invalidation Matrix must include invalidated artifacts, decisions, contracts, issues, verification rerun, and new status"
        )
    if has_backflow_signal and not trigger:
        errors.append(f"{change_dir}: backflow/supersession signal exists but missing Backflow Trigger")
    if re.search(r"\bsuperseded\b|被替代", combined, re.IGNORECASE) and not supersession:
        errors.append(f"{change_dir}: superseded objects exist but missing Supersession Record")

    superseded = extract_superseded_objects(combined)
    if superseded:
        for obj in sorted(superseded):
            if obj in all_issue_text:
                errors.append(f"{change_dir}: active atomic issues reference superseded object {obj}")

    if backflow and re.search(r"\|\s*BF-\d{3}[^|\n]*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|\s*\|", backflow):
        errors.append(f"{change_dir}: Backflow Invalidation Matrix has rows without verification rerun")

    return errors


def validate_mock_acceptance_artifacts(change_dir: Path, stage: str) -> list[str]:
    errors: list[str] = []
    planning_mode = stage in MOCK_ACCEPTANCE_PLANNING_STAGES
    execution_mode = stage in MOCK_ACCEPTANCE_EXECUTION_STAGES
    if not planning_mode and not execution_mode:
        return errors
    combined = "\n".join(
        read(change_dir / rel)
        for rel in [
            "proposal.md",
            "spec.md",
            "plan.md",
            "tasks.md",
            "atomic-planning-context-pack.md",
            "verification.yaml",
            "contracts.yaml",
            "atomic-issue-packets.yaml",
        ]
    )
    if planning_mode and not MOCK_ACCEPTANCE_SIGNAL_RE.search(combined):
        return errors
    validator = SKILLS_ROOT / "mock-acceptance-gate" / "scripts" / "validate_mock_acceptance_cases.py"
    if not validator.exists():
        return [f"{change_dir}: mock acceptance validator missing: {validator}"]
    mode = "planning" if planning_mode else "execution"
    result = subprocess.run(
        [sys.executable, str(validator), str(change_dir), "--mode", mode],
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


def validate_no_production_downgrade_language(change_dir: Path, stage: str) -> list[str]:
    if stage not in {"all", "contract", "verification", "task-planning", "pre-execution", "mock-acceptance", "product-acceptance"}:
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
        path = change_dir / rel
        body = read(path)
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


def validate_frontend_contract_artifacts(change_dir: Path, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "frontend-contract", "contract", "verification", "task-planning", "pre-execution"}:
        return errors

    combined = "\n".join(
        read(change_dir / name)
        for name in [
            "plan.md",
            "proposal.md",
            "spec.md",
            "aip.md",
            "tasks.md",
            "atomic-planning-context-pack.md",
            "frontend-page-inventory.md",
            "frontend-action-inventory.md",
            "frontend-route-component-matrix.md",
            "frontend-mode-field-display-matrix.md",
            "frontend-form-state-matrix.md",
            "frontend-mode-leakage-negative-matrix.md",
            "frontend-api-payload-contract-matrix.md",
            "frontend-fixture-need-matrix.md",
            "frontend-browser-verification-matrix.md",
            "frontend-reference-pattern-matrix.md",
        ]
    )
    has_frontend_signal = bool(
        re.search(r"frontend|UI|browser|DOM|page|route|component|form|wizard|submit|click|前端|页面|表单|浏览器|路由|组件", combined, re.IGNORECASE)
    )
    if not has_frontend_signal:
        return errors

    for rel, columns in REQUIRED_FRONTEND_CONTRACT_FILES.items():
        path = change_dir / rel
        body = read(path)
        if not body.strip():
            errors.append(f"{path}: required frontend contract artifact is missing or empty")
            continue
        if not has_table_columns(body, columns):
            errors.append(f"{path}: must include columns {', '.join(columns)}")
        if not has_meaningful_rows(body):
            errors.append(f"{path}: must include at least one meaningful non-placeholder data row")
        if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
            errors.append(f"{path}: contains unresolved TBD/TODO/unknown value")

    reference_signal = bool(FRONTEND_REFERENCE_SIGNAL_RE.search(combined))
    if reference_signal:
        for rel, columns in REFERENCE_FRONTEND_CONTRACT_FILES.items():
            path = change_dir / rel
            body = read(path)
            if not body.strip():
                errors.append(
                    f"{path}: reference UI signal found but required artifact is missing or empty; "
                    "reference UI cannot be reduced to field/selector semantics"
                )
                continue
            if not has_table_columns(body, columns):
                errors.append(f"{path}: must include columns {', '.join(columns)}")
            if not has_meaningful_rows(body):
                errors.append(f"{path}: must include at least one meaningful non-placeholder data row")
            if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
                errors.append(f"{path}: contains unresolved TBD/TODO/unknown value")

    route_matrix = read(change_dir / "frontend-route-component-matrix.md")
    if route_matrix:
        for row in table_rows(route_matrix):
            joined = " | ".join(row)
            if row and row[0].lower() == "action id":
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
                        errors.append(f"{change_dir / 'frontend-route-component-matrix.md'}: action row lacks {label} proof: {joined}")

    field_matrix = read(change_dir / "frontend-mode-field-display-matrix.md")
    if field_matrix:
        for row in table_rows(field_matrix):
            joined = " | ".join(row)
            if row and row[0].lower() == "surface":
                continue
            for label, pattern in [
                ("must hide/absence assertion", r"absent|hide|hidden|not\s+(?:show|render|submit)|no\s+|without|forbid|forbidden|禁止|隐藏|不得|不显示|不渲染|不存在"),
                ("fixture/assertion", r"fixture|DOM|browser|visible|absent|selector|assert|截图|浏览器|断言|可见"),
            ]:
                if not re.search(pattern, joined, re.IGNORECASE):
                    errors.append(f"{change_dir / 'frontend-mode-field-display-matrix.md'}: field display row lacks {label}: {joined}")

    browser_matrix = read(change_dir / "frontend-browser-verification-matrix.md")
    if browser_matrix:
        browser_text = browser_matrix
        required_groups = [
            ("browser/click steps", r"browser|playwright|click|submit|浏览器|点击|提交"),
            ("network/API assertions", r"network|request|response|API|GET|POST|PUT|PATCH|DELETE|接口|网络"),
            ("DOM assertions", r"\bDOM\b|visible|text|selector|disabled|enabled|文案|可见|选择器|禁用"),
            ("screenshot/trace evidence", r"screenshot|trace|HAR|video|截图|轨迹|录屏"),
        ]
        for label, pattern in required_groups:
            if not re.search(pattern, browser_text, re.IGNORECASE):
                errors.append(f"{change_dir / 'frontend-browser-verification-matrix.md'}: missing {label}")
        if re.search(r"\b(build|lint|typecheck|tsc|payload|compile)\b", browser_text, re.IGNORECASE) and not re.search(
            r"browser|playwright|DOM|click|submit|network|screenshot|trace|浏览器|点击|提交|网络|截图",
            browser_text,
            re.IGNORECASE,
        ):
            errors.append(
                f"{change_dir / 'frontend-browser-verification-matrix.md'}: build/lint/payload proof cannot close frontend user-flow verification"
            )

    context = read(change_dir / "atomic-planning-context-pack.md")
    packets = read(change_dir / "atomic-issue-packets.yaml")
    if stage in {"all", "task-planning", "pre-execution"} and (context or packets):
        frontend_contract_files = dict(REQUIRED_FRONTEND_CONTRACT_FILES)
        if reference_signal:
            frontend_contract_files.update(REFERENCE_FRONTEND_CONTRACT_FILES)
        for rel in frontend_contract_files:
            if rel not in context:
                errors.append(f"{change_dir / 'atomic-planning-context-pack.md'}: must consume {rel} for frontend task planning")
        packet_required_terms = [
            "frontend_user_task",
            "action_route_component",
            "mode_field_display_matrix",
            "form_state_matrix",
            "mode_negative_assertions",
            "api_payload_contract_matrix",
            "fixture_needs",
            "browser_verification",
            "experience_rubric",
        ]
        for term in packet_required_terms:
            if term not in packets:
                errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: frontend packets must include {term}")
        if reference_signal and "reference_ui_patterns" not in packets:
            errors.append(
                f"{change_dir / 'atomic-issue-packets.yaml'}: frontend packets must include reference_ui_patterns when source/frontend contract references existing UI"
            )

        packet_doc = read_yaml(change_dir / "atomic-issue-packets.yaml")
        dag_doc = read_yaml(change_dir / "task-dag.yaml")
        packet_map = packet_doc.get("packets", {}) if isinstance(packet_doc.get("packets", {}), dict) else {}
        task_map = dag_doc.get("tasks", {}) if isinstance(dag_doc.get("tasks", {}), dict) else {}
        route_rows = table_dicts(route_matrix)
        field_rows = table_dicts(field_matrix)
        form_rows = table_dicts(read(change_dir / "frontend-form-state-matrix.md"))
        negative_rows = table_dicts(read(change_dir / "frontend-mode-leakage-negative-matrix.md"))
        payload_rows = table_dicts(read(change_dir / "frontend-api-payload-contract-matrix.md"))
        browser_rows = table_dicts(browser_matrix)
        reference_rows = table_dicts(read(change_dir / "frontend-reference-pattern-matrix.md"))
        action_to_browser = {table_get(row, "Action ID"): row for row in browser_rows if table_get(row, "Action ID")}

        for row in reference_rows:
            reference_id = table_get(row, "Reference ID")
            if not reference_id:
                continue
            owner = table_get(row, "Owner issue", "Owning issue")
            if not re.match(r"T\d{3}", owner):
                errors.append(f"{change_dir / 'frontend-reference-pattern-matrix.md'}: {reference_id} lacks concrete Owner issue")
                continue
            if owner not in task_map:
                errors.append(f"{change_dir / 'frontend-reference-pattern-matrix.md'}: {reference_id} owner {owner} is missing from task-dag.yaml")
                continue
            owner_packet = packet_map.get(owner, {}) if isinstance(packet_map.get(owner, {}), dict) else {}
            reference_section_text = flatten_text(owner_packet.get("reference_ui_patterns"))
            for required in [
                reference_id,
                table_get(row, "Target surface/action"),
                table_get(row, "Reference file/component"),
                table_get(row, "Must reuse/adapt"),
                table_get(row, "Visual/layout obligation"),
                table_get(row, "Interaction/state obligation"),
                table_get(row, "Browser/visual proof"),
            ]:
                required_text = str(required).strip()
                if required_text and not semantic_payload_copied(required_text, reference_section_text):
                    errors.append(
                        f"{change_dir / 'atomic-issue-packets.yaml'}: reference pattern {reference_id} not copied into "
                        f"owner packet {owner}.reference_ui_patterns: {required_text}. "
                        "Source Context or semantic_carriers alone do not count"
                    )
            if not component_paths(table_get(row, "Reference file/component")):
                errors.append(f"{change_dir / 'frontend-reference-pattern-matrix.md'}: {reference_id} must name concrete reference page/component file")
            visual_text = flatten_text([table_get(row, "Must reuse/adapt"), table_get(row, "Visual/layout obligation")])
            if not re.search(r"layout|section|order|group|spacing|component|control|review|summary|table|tab|布局|分组|顺序|组件|控件|预览|摘要|表格", visual_text, re.IGNORECASE):
                errors.append(f"{change_dir / 'frontend-reference-pattern-matrix.md'}: {reference_id} must specify visual/layout/component obligations, not only data fields")
            if not STRONG_FRONTEND_PROOF_RE.search(table_get(row, "Browser/visual proof")):
                errors.append(f"{change_dir / 'frontend-reference-pattern-matrix.md'}: {reference_id} lacks browser/screenshot/DOM/trace visual proof")

        for row in route_rows:
            action_id = table_get(row, "Action ID")
            if not re.match(r"UI-ACT-\d+", action_id):
                continue
            owner = table_get(row, "Owner issue", "Owning issue")
            if not re.match(r"T\d{3}", owner):
                errors.append(f"{change_dir / 'frontend-route-component-matrix.md'}: {action_id} lacks concrete Owner issue")
                continue
            if owner not in task_map:
                errors.append(f"{change_dir / 'frontend-route-component-matrix.md'}: {action_id} owner {owner} is missing from task-dag.yaml")
                continue
            packet = packet_map.get(owner, {}) if isinstance(packet_map.get(owner, {}), dict) else {}
            action_section_text = flatten_text(packet.get("action_route_component"))
            if action_id not in action_section_text:
                errors.append(
                    f"{change_dir / 'atomic-issue-packets.yaml'}: {action_id} is not copied into owner packet "
                    f"{owner}.action_route_component; Source Context or semantic_carriers alone do not count as matrix consumption"
                )
            task = task_map.get(owner, {}) if isinstance(task_map.get(owner, {}), dict) else {}
            task_files = [str(item) for item in task.get("files", [])] if isinstance(task.get("files", []), list) else []
            packet_files = [
                str(item.get("path"))
                for item in packet.get("files_to_change", [])
                if isinstance(item, dict) and item.get("path")
            ]
            allowlist = task_files + packet_files
            owner_text = flatten_text([task, packet])
            if not (FRONTEND_TASK_RE.search(owner_text) or FRONTEND_FILE_RE.search(owner_text)):
                errors.append(f"{change_dir / 'frontend-route-component-matrix.md'}: {action_id} owner {owner} is not a frontend task")
            for label, value in [
                ("source component", table_get(row, "Source component")),
                ("landing component/file", table_get(row, "Landing component/file")),
                ("router definition", table_get(row, "Router definition")),
                ("click handler / route builder", table_get(row, "Click handler / route builder", "Click handler")),
            ]:
                paths = component_paths(value)
                if label in {"source component", "landing component/file"} and not paths:
                    errors.append(f"{change_dir / 'frontend-route-component-matrix.md'}: {action_id} {label} must name concrete file path")
                if label == "router definition" and not paths and not re.search(
                    r"file[- ]?based router|landing component owns route|Next pages router|Next app router|文件路由",
                    value,
                    re.IGNORECASE,
                ):
                    errors.append(f"{change_dir / 'frontend-route-component-matrix.md'}: {action_id} router definition must name file or explicit file-based route ownership")
                for path in paths:
                    if not path_in_allowlist(path, allowlist):
                        errors.append(f"{change_dir / 'frontend-route-component-matrix.md'}: {action_id} {label} {path} is not in owner {owner} files")
            browser = action_to_browser.get(action_id)
            if not browser:
                errors.append(f"{change_dir / 'frontend-browser-verification-matrix.md'}: {action_id} lacks row-level browser verification")
            else:
                browser_text = flatten_text(browser)
                if NOT_RUN_RE.search(browser_text):
                    errors.append(f"{change_dir / 'frontend-browser-verification-matrix.md'}: {action_id} browser verification is not-run/deferred")
                if not STRONG_FRONTEND_PROOF_RE.search(browser_text):
                    errors.append(f"{change_dir / 'frontend-browser-verification-matrix.md'}: {action_id} must include click/network/DOM/screenshot-or-trace proof")

        for row in field_rows:
            surface = table_get(row, "Surface")
            owner = table_get(row, "Owner issue", "Owning issue")
            if not surface:
                continue
            if not re.match(r"T\d{3}", owner):
                errors.append(f"{change_dir / 'frontend-mode-field-display-matrix.md'}: surface {surface} lacks Owner issue")
                continue
            owner_packet = packet_map.get(owner, {}) if isinstance(packet_map.get(owner, {}), dict) else {}
            field_section_text = flatten_text(
                owner_packet.get("mode_field_display_matrix") or owner_packet.get("field_display_matrix")
            )
            for required in [surface, table_get(row, "Must show"), table_get(row, "Must hide"), table_get(row, "Assertion")]:
                required_text = str(required).strip()
                if required_text and not semantic_payload_copied(required_text, field_section_text):
                    errors.append(
                        f"{change_dir / 'atomic-issue-packets.yaml'}: field display surface {surface} not fully copied into "
                        f"owner packet {owner}.mode_field_display_matrix: {required_text}. "
                        "Source Context or semantic_carriers alone do not count"
                    )

        frontend_owner_ids = {
            owner
            for owner, packet in packet_map.items()
            if isinstance(packet, dict)
            and (FRONTEND_TASK_RE.search(flatten_text(packet)) or FRONTEND_FILE_RE.search(flatten_text(packet)))
        }
        for row in form_rows:
            form = table_get(row, "Form/step")
            if not form:
                continue
            owners = {
                table_get(field_row, "Owner issue", "Owning issue")
                for field_row in field_rows
                if table_get(field_row, "Owner issue", "Owning issue")
                and (
                    table_get(row, "Mode/state") in table_get(field_row, "Mode/state")
                    or table_get(field_row, "Surface").split("/")[0].strip().lower() in form.lower()
                )
            }
            if not owners:
                owners = frontend_owner_ids
            matched = False
            for owner in owners:
                owner_packet = packet_map.get(owner, {}) if isinstance(packet_map.get(owner, {}), dict) else {}
                form_section_text = flatten_text(owner_packet.get("form_state_matrix"))
                required_values = [
                    form,
                    table_get(row, "Active fields"),
                    table_get(row, "Inactive/hidden fields"),
                    table_get(row, "Validation trigger"),
                    table_get(row, "Submit participation"),
                ]
                if all(
                    not str(value).strip() or semantic_payload_copied(str(value).strip(), form_section_text)
                    for value in required_values
                ):
                    matched = True
                    break
            if not matched:
                errors.append(
                    f"{change_dir / 'atomic-issue-packets.yaml'}: form state row {form} is not copied into any "
                    "frontend owner packet.form_state_matrix; Source Context or semantic_carriers alone do not count"
                )

        for row in negative_rows:
            surface = table_get(row, "Surface/action")
            if not surface:
                continue
            owner = table_get(row, "Owner issue", "Owning issue")
            if not re.match(r"T\d{3}", owner):
                errors.append(f"{change_dir / 'frontend-mode-leakage-negative-matrix.md'}: negative leakage row {surface} lacks Owner issue")
                continue
            owner_packet = packet_map.get(owner, {}) if isinstance(packet_map.get(owner, {}), dict) else {}
            negative_section_text = flatten_text(
                [
                    owner_packet.get("mode_negative_assertions"),
                    (owner_packet.get("browser_verification") or {}).get("negative_assertions")
                    if isinstance(owner_packet.get("browser_verification"), dict)
                    else "",
                ]
            )
            for required in [
                surface,
                table_get(row, "Mode/state"),
                table_get(row, "Forbidden DOM/text"),
                table_get(row, "Forbidden payload fields"),
                table_get(row, "Forbidden route/API"),
                table_get(row, "Assertion method"),
            ]:
                required_text = str(required).strip()
                if required_text and not semantic_payload_copied(required_text, negative_section_text):
                    errors.append(
                        f"{change_dir / 'atomic-issue-packets.yaml'}: negative leakage row {surface} not copied into "
                        f"owner packet {owner}.mode_negative_assertions/browser_verification.negative_assertions: "
                        f"{required_text}. Source Context or semantic_carriers alone do not count"
                    )

        for row in payload_rows:
            action_id = table_get(row, "Action ID")
            joined = " | ".join(row.values())
            if not action_id or re.fullmatch(r"(?:N/A|not applicable|不适用)", action_id.strip(), re.IGNORECASE):
                continue
            owner = table_get(row, "Owner issue", "Owning issue")
            if not re.match(r"T\d{3}", owner):
                errors.append(f"{change_dir / 'frontend-api-payload-contract-matrix.md'}: {action_id} lacks concrete Owner issue")
                continue
            owner_packet = packet_map.get(owner, {}) if isinstance(packet_map.get(owner, {}), dict) else {}
            payload_section_text = flatten_text(
                [
                    owner_packet.get("api_payload_contract_matrix"),
                    owner_packet.get("verification"),
                    (owner_packet.get("browser_verification") or {}).get("network_assertions")
                    if isinstance(owner_packet.get("browser_verification"), dict)
                    else "",
                ]
            )
            for label in [
                "Method/path",
                "Request body canonical path",
                "Allowed keys",
                "Forbidden keys / semantic aliases",
                "Required/nullable/default/derived rule",
                "Legacy compatibility rule",
                "Network exact-key assertion",
            ]:
                value = table_get(row, label)
                if not value or re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", value, re.IGNORECASE):
                    errors.append(f"{change_dir / 'frontend-api-payload-contract-matrix.md'}: {action_id} missing {label}")
                elif not semantic_payload_copied(value, payload_section_text):
                    errors.append(
                        f"{change_dir / 'atomic-issue-packets.yaml'}: API payload row {action_id} {label} not copied into "
                        f"owner packet {owner}.api_payload_contract_matrix/browser_verification.network_assertions"
                    )
            assertion = table_get(row, "Network exact-key assertion")
            if assertion and not re.search(r"\bObject\.keys|exact|keys?\(|schema|snapshot|request|network|body|字段|精确|键\b", assertion, re.IGNORECASE):
                errors.append(f"{change_dir / 'frontend-api-payload-contract-matrix.md'}: {action_id} lacks executable exact-key assertion")

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
                errors.append(f"{change_dir / 'frontend-browser-verification-matrix.md'}: {action_id} has no owner from frontend-route-component-matrix.md")
                continue
            owner_packet = packet_map.get(owner, {}) if isinstance(packet_map.get(owner, {}), dict) else {}
            browser_section_text = flatten_text(owner_packet.get("browser_verification"))
            for required in [
                action_id,
                table_get(row, "User task ID"),
                table_get(row, "Browser steps"),
                table_get(row, "Network assertions"),
                table_get(row, "DOM assertions"),
                table_get(row, "Screenshot/trace"),
            ]:
                required_text = str(required).strip()
                if required_text and not semantic_payload_copied(required_text, browser_section_text):
                    errors.append(
                        f"{change_dir / 'atomic-issue-packets.yaml'}: browser verification row {action_id} not copied into "
                        f"owner packet {owner}.browser_verification: {required_text}. "
                        "Source Context or semantic_carriers alone do not count"
                    )

    return errors


def validate_contract_matrix_artifacts(change_dir: Path, stage: str, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "contract", "verification", "task-planning", "pre-execution"}:
        return errors
    combined = "\n".join([plan, tasks, read(change_dir / "contracts.yaml"), read(change_dir / "atomic-issue-packets.yaml")])
    has_contract_signal = bool(re.search(r"\bC-\d{3}\b|Module Contract Graph|Provider/Consumer|跨模块|契约", combined, re.IGNORECASE))
    if not has_contract_signal:
        return errors
    for rel, columns in REQUIRED_CONTRACT_MATRIX_FILES.items():
        path = change_dir / rel
        body = read(path)
        if not body.strip():
            errors.append(f"{path}: required contract matrix artifact is missing or empty")
            continue
        if not has_table_columns(body, columns):
            errors.append(f"{path}: must include columns {', '.join(columns)}")
        if not has_meaningful_rows(body):
            errors.append(f"{path}: must include at least one meaningful data row or locked N/A row")
        if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
            errors.append(f"{path}: contains unresolved TBD/TODO/unknown value")

    executable = first_existing_section(
        plan,
        "Contract Executable Obligation Matrix",
        "Contract Executable Obligations",
        "契约可执行子义务矩阵",
    )
    if not executable:
        errors.append(f"{change_dir / 'plan.md'}: contracts exist but missing Contract Executable Obligation Matrix")
        obligation_rows = []
        executable_text = ""
        source_contract_ids = contract_ids_from_text(
            read(change_dir / "contracts.yaml")
            + "\n"
            + first_existing_section(plan, "Module Contract Graph", "模块契约图")
            + "\n"
            + first_existing_section(
                plan,
                "Contract Materialization Source Matrix",
                "Contract Materialization Matrix",
                "契约物化来源矩阵",
            )
        )
    else:
        if not (
            has_table_columns(executable, CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS)
            or has_table_columns(executable, LEGACY_CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS)
        ):
            errors.append(
                f"{change_dir / 'plan.md'}: Contract Executable Obligation Matrix must include columns "
                f"{', '.join(CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS)}"
            )
        if re.search(r"\b(TBD|TODO|unknown|待确认|未知|blocked)\b", executable, re.IGNORECASE):
            errors.append(f"{change_dir / 'plan.md'}: Contract Executable Obligation Matrix contains unresolved TBD/TODO/unknown/blocked value")
        errors.extend(
            markdown_table_column_count_errors(
                executable,
                CONTRACT_EXECUTABLE_OBLIGATION_COLUMNS,
                str(change_dir / "plan.md"),
            )
        )
        obligation_rows = table_dicts(executable)
        executable_text = flatten_text(obligation_rows)
        source_contract_ids = contract_ids_from_text(
            read(change_dir / "contracts.yaml")
            + "\n"
            + first_existing_section(plan, "Module Contract Graph", "模块契约图")
            + "\n"
            + first_existing_section(
                plan,
                "Contract Materialization Source Matrix",
                "Contract Materialization Matrix",
                "契约物化来源矩阵",
            )
        )
        if source_contract_ids and not obligation_rows:
            errors.append(f"{change_dir / 'plan.md'}: Contract Executable Obligation Matrix has no data rows")
        for cid in sorted(source_contract_ids):
            cid_rows = [row for row in obligation_rows if cid in flatten_text(row)]
            if not cid_rows:
                errors.append(f"{change_dir / 'plan.md'}: contract {cid} missing executable sub-obligation rows")
                continue
            for row in cid_rows:
                if executable_obligation_row_too_thin(row):
                    errors.append(
                        f"{change_dir / 'plan.md'}: contract {cid} executable obligation row is too thin/generic: {flatten_text(row)}"
                    )
                for detail in executable_obligation_row_granularity_errors(row):
                    errors.append(f"{change_dir / 'plan.md'}: contract {cid} executable obligation row is too coarse: {detail}")
                for detail in owner_module_format_errors(row):
                    errors.append(f"{change_dir / 'plan.md'}: contract {cid} {detail}")
            for label in [
                "Provider guarantee",
                "Consumer assumption",
                "Failure / timing detail",
                "State/resource owner",
                "Verification proof",
            ]:
                if not any(table_get(row, label) and not locked_na(table_get(row, label)) for row in cid_rows):
                    errors.append(f"{change_dir / 'plan.md'}: contract {cid} executable obligations missing {label}")
        if is_generic_packet_text(executable_text):
            errors.append(f"{change_dir / 'plan.md'}: Contract Executable Obligation Matrix contains generic placeholder text")
        errors.extend(validate_specialized_rows_in_contract_obligations(change_dir, executable_text))

    active_obligation_rows = active_contract_obligation_rows(change_dir)
    active_rows_by_contract: dict[str, list[dict[str, str]]] = {}
    for row in active_obligation_rows:
        cid = table_get(row, "Contract")
        if not re.fullmatch(r"C-\d{3}", cid):
            cid = next(iter(contract_ids_from_text(table_get(row, "Sub-obligation ID"))), cid)
        if cid:
            active_rows_by_contract.setdefault(cid, []).append(row)

    contract_yaml = read_yaml(change_dir / "contracts.yaml")
    contracts = as_dict(contract_yaml.get("contracts"))
    for cid, raw_contract in contracts.items():
        contract = as_dict(raw_contract)
        if contract.get("external_provider") is True or contract.get("status") in {"superseded", "not_applicable", "locked-na"}:
            continue
        yaml_rows = [
            row
            for row in contract_obligation_rows_from_yaml(change_dir)
            if str(cid) == table_get(row, "Contract") or str(cid) in flatten_text(row)
        ]
        if stage in {"all", "task-planning", "pre-execution"} and not yaml_rows:
            errors.append(
                f"{change_dir / 'contracts.yaml'}: {cid} executable_obligations are required before task-planning; "
                "do not send a coarse C-xxx directly into task DAG"
            )
        cid_rows = active_rows_by_contract.get(str(cid), [])
        if not cid_rows:
            continue
        provider_module = cell_text(contract.get("provider_module"))
        if contract_provider_module_is_multi_owner(provider_module):
            errors.append(
                f"{change_dir / 'contracts.yaml'}: {cid} provider_module must be owner-single, got {provider_module}; "
                "split semantic provider obligations or keep the coarse C-xxx as a composition index without multi-owner provider_module"
            )
        owner_modules = {
            contract_row_owner_module(row)
            for row in cid_rows
            if row_is_semantic_provider(row) and contract_row_owner_module(row)
        }
        if provider_module and len(owner_modules) > 1:
            errors.append(
                f"{change_dir / 'contracts.yaml'}: {cid} provider_module cannot summarize multiple executable owner modules "
                f"({', '.join(sorted(owner_modules))}); keep C-xxx as a composition index and put provider ownership on C-xxx-OBL-yyy rows"
            )
        provider_rows = 0
        for yaml_row in yaml_rows:
            obligation_id = table_get(yaml_row, "Sub-obligation ID")
            if not table_get(yaml_row, "Edge"):
                errors.append(
                    f"{change_dir / 'contracts.yaml'}: {cid} executable_obligations[{obligation_id or '<missing>'}] "
                    "missing edge; YAML must be isomorphic with Markdown Contract Executable Obligation Matrix"
                )
        for row in cid_rows:
            obligation_id = table_get(row, "Sub-obligation ID")
            edge_type = table_get(row, "Edge type")
            row_kind = table_get(row, "Sub-obligation type") or table_get(row, "Row kind")
            owner_module = contract_row_owner_module(row)
            if obligation_id_is_coarse_contract(obligation_id):
                errors.append(
                    f"{change_dir / 'contracts.yaml'}: {cid} executable obligation must use "
                    f"C-xxx-OBL-yyy or specialized row ID, not coarse {obligation_id}"
                )
            errors.extend(
                f"{change_dir / 'contracts.yaml'}: {cid} {detail}"
                for detail in executable_obligation_column_drift_errors(row)
            )
            errors.extend(
                f"{change_dir / 'contracts.yaml'}: {cid} {detail}"
                for detail in owner_module_format_errors(row)
            )
            if not table_get(row, "Edge"):
                errors.append(
                    f"{change_dir / 'contracts.yaml'}: {cid} executable obligation "
                    f"{obligation_id or '<missing>'} missing edge"
                )
            if not edge_type:
                errors.append(
                    f"{change_dir / 'contracts.yaml'}: {cid} executable obligation "
                    f"{obligation_id or '<missing>'} missing edge_type"
                )
            elif not (PROVIDER_OWNED_EDGE_TYPE_RE.search(edge_type) or CARRIER_EDGE_TYPE_RE.search(edge_type)):
                errors.append(
                    f"{change_dir / 'contracts.yaml'}: {cid} executable obligation "
                    f"{obligation_id or '<missing>'} has invalid edge_type {edge_type}; "
                    "use semantic_contract_edge, carrier_order_edge, verification_prerequisite_edge, or proof_only_edge"
                )
            if PROVIDER_OWNED_EDGE_TYPE_RE.search(edge_type) and not row_is_semantic_provider(row):
                errors.append(
                    f"{change_dir / 'contracts.yaml'}: {cid} non-provider obligation "
                    f"{obligation_id or '<missing>'} uses semantic_contract_edge with row_kind {row_kind or '<missing>'}; "
                    "consumer/proof/carrier rows must use carrier_order_edge, verification_prerequisite_edge, or proof_only_edge"
                )
            is_provider = row_is_semantic_provider(row)
            if is_provider:
                provider_rows += 1
                if not owner_module:
                    errors.append(
                        f"{change_dir / 'contracts.yaml'}: {cid} provider obligation "
                        f"{obligation_id or '<missing>'} requires owner_module"
                    )
                elif provider_module and len(owner_modules) <= 1 and not owner_modules_compatible(provider_module, owner_module):
                    errors.append(
                        f"{change_dir / 'contracts.yaml'}: {cid} provider obligation "
                        f"{obligation_id or '<missing>'} owner_module {owner_module} "
                        f"does not match owner-single provider_module {provider_module}"
                    )
            elif PROVIDER_ROW_KIND_RE.search(row_kind) and CARRIER_EDGE_TYPE_RE.search(edge_type):
                errors.append(
                    f"{change_dir / 'contracts.yaml'}: {cid} provider guarantee "
                    f"{obligation_id or '<missing>'} cannot use non-provider edge_type {edge_type}; "
                    "split carrier/proof into a separate row"
                )
        if provider_module and provider_rows == 0:
            errors.append(
                f"{change_dir / 'contracts.yaml'}: {cid} no semantic_contract_edge provider obligation row exists "
                f"for provider_module {provider_module}; carrier/proof rows cannot close the contract provider"
            )

    if stage not in {"all", "task-planning", "pre-execution"}:
        return errors

    context = read(change_dir / "atomic-planning-context-pack.md")
    packets = read(change_dir / "atomic-issue-packets.yaml")
    for rel in REQUIRED_CONTRACT_MATRIX_FILES:
        if rel not in context:
            errors.append(f"{change_dir / 'atomic-planning-context-pack.md'}: must consume {rel}")
    if "Contract Executable Obligation Matrix" not in context and "contract executable" not in context.lower():
        errors.append(f"{change_dir / 'atomic-planning-context-pack.md'}: must consume Contract Executable Obligation Matrix")

    for row in table_dicts(read(change_dir / "api-wire-shape-matrix.md")):
        contract = table_get(row, "Contract")
        joined = " | ".join(row.values())
        if not contract or re.fullmatch(r"(?:N/A|not applicable|不适用)", contract.strip(), re.IGNORECASE):
            continue
        for label in [
            "Method/path",
            "Request canonical body/query",
            "Allowed keys",
            "Forbidden keys / semantic aliases",
            "Required/nullable/default/derived rule",
            "Legacy compatibility rule",
            "Exact-key verification",
        ]:
            value = table_get(row, label)
            if not value or re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", value, re.IGNORECASE):
                errors.append(f"{change_dir / 'api-wire-shape-matrix.md'}: {contract} missing {label}")
            elif not semantic_payload_copied(value, packets):
                errors.append(f"{change_dir / 'api-wire-shape-matrix.md'}: {contract} {label} not copied into atomic-issue-packets.yaml")
    return errors


def validate_atomic_task_decomposition(change_dir: Path, stage: str, tasks: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "task-planning", "pre-execution"}:
        return errors
    if not tasks.strip() and not read(change_dir / "atomic-issue-packets.yaml").strip():
        return errors
    path = change_dir / "atomic-task-decomposition.md"
    body = read(path)
    if not body.strip():
        return [f"{path}: required task-planning artifact is missing or empty"]
    if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
        errors.append(f"{path}: contains unresolved TBD/TODO/unknown value")
    for section_name, columns in REQUIRED_ATOMIC_DECOMPOSITION_SECTIONS.items():
        section_text = first_existing_section(body, section_name)
        if not section_text:
            errors.append(f"{path}: missing section {section_name}")
            continue
        if not has_table_columns(section_text, columns):
            errors.append(f"{path}: section {section_name} must include columns {', '.join(columns)}")
        if not has_meaningful_rows(section_text):
            errors.append(f"{path}: section {section_name} must include at least one meaningful data row or locked N/A row")
    for row in table_dicts(body):
        joined = " | ".join(row.values())
        if re.search(r"\b(?:blocked-backflow|blocked|unknown)\b|待确认|未知|阻塞", joined, re.IGNORECASE) and not re.search(
            r"\blocked\s+N/A\b|locked N/A|not applicable|不适用", joined, re.IGNORECASE
        ):
            errors.append(f"{path}: contains blocking row: {joined}")
    for task_id in ids(r"\b(T\d{3})\b", tasks):
        if task_id not in body:
            errors.append(f"{path}: task {task_id} missing from atomic task decomposition matrices")
    packets = read(change_dir / "atomic-issue-packets.yaml")
    dag = read(change_dir / "task-dag.yaml") + "\n" + tasks
    context = read(change_dir / "atomic-planning-context-pack.md")
    edge_section = first_existing_section(body, "Contract Edge Decomposition Matrix")
    edge_rows = table_dicts(edge_section)
    pc_rows = table_dicts(first_existing_section(body, "Provider Consumer Task Decision Matrix"))
    merge_rows = table_dicts(first_existing_section(body, "Task Merge Split Decision Matrix"))
    obligation_rows = active_contract_obligation_rows(change_dir)
    obligation_groups: dict[str, dict[str, str]] = {}
    for obligation in obligation_rows:
        gid = obligation_group_id(obligation)
        if gid and gid not in obligation_groups:
            obligation_groups[gid] = obligation
    row_to_tasks: dict[str, set[str]] = {}
    packet_doc = read_yaml(change_dir / "atomic-issue-packets.yaml")
    packet_map = packet_doc.get("packets", {}) if isinstance(packet_doc.get("packets"), dict) else {}
    for gid, obligation in obligation_groups.items():
        if not gid:
            continue
        missing_targets: list[str] = []
        for label, target in [
            ("atomic-planning-context-pack.md", context),
            ("atomic-task-decomposition.md", body),
            ("task-dag.yaml/tasks.md", dag),
            ("atomic-issue-packets.yaml", packets),
        ]:
            if not text_mentions_obligation_group(target, obligation):
                missing_targets.append(label)
        if missing_targets:
            errors.append(
                f"{path}: contract executable obligation {gid} is not mapped through "
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
            errors.append(f"{path}: contract executable obligation {gid} has no Txxx/proof-only/locked N/A/backflow owner mapping")
        for task_id in sorted(mapped_tasks):
            packet = packet_map.get(task_id, {}) if isinstance(packet_map.get(task_id, {}), dict) else {}
            packet_text = flatten_text(packet)
            if not text_mentions_obligation_group(packet_text, obligation):
                errors.append(f"{path}: contract executable obligation {gid} maps to {task_id} but is not copied into that owner packet")
            elif not obligation_payload_materialized(obligation, packet_text):
                errors.append(
                    f"{path}: contract executable obligation {gid} maps to {task_id} "
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
                f"{path}: {task_id} merges multiple high-risk obligation rows {', '.join(unique_ids)} "
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
                    f"{path}: {task_id} high-risk merge must prove same module/type/operation/verification for {', '.join(unique_ids)}: {joined}"
                )
            if re.search(r"\b(?:same module|same page|related work|task count|方便|相关|owner closure|同一模块|同页|相关工作|减少任务)\b", joined, re.IGNORECASE) and not all(
                text_has_row_id(joined, oid) for oid in unique_ids
            ):
                errors.append(f"{path}: {task_id} high-risk merge rationale is too weak: {joined}")
    proof_section = first_existing_section(body, "Proof Owner Allowlist Matrix")
    for row in table_dicts(proof_section):
        proof_file = table_get(row, "Proof file/path").strip("`")
        if not proof_file:
            continue
        if re.search(r"\b(?:yes|true|是|required|must)\b", table_get(row, "Added to packet files_to_change?"), re.IGNORECASE) and proof_file not in packets:
            errors.append(f"{path}: proof file {proof_file} is marked packet-required but missing from atomic-issue-packets.yaml")
        if re.search(r"\b(?:yes|true|是|required|must)\b", table_get(row, "Added to task-dag files?"), re.IGNORECASE) and proof_file not in dag:
            errors.append(f"{path}: proof file {proof_file} is marked task-dag-required but missing from task-dag files")
    load_section = first_existing_section(body, "Semantic Load Split Matrix")
    for row in table_dicts(load_section):
        joined = " | ".join(row.values())
        split_required = table_get(row, "Split required?")
        rationale = table_get(row, "Merge rationale / backflow")
        if re.search(r"\b(?:yes|true|是|required|must)\b", split_required, re.IGNORECASE) and not re.search(
            r"\b(?:backflow|split|拆|回流|T\d{3}|locked N/A|not applicable)\b",
            rationale,
            re.IGNORECASE,
        ):
            errors.append(f"{path}: semantic load row requires split but lacks split/backflow rationale: {joined}")
        if re.search(r"\b(?:same module|same page|related work|task count|方便|相关)\b", rationale, re.IGNORECASE):
            errors.append(f"{path}: semantic load merge rationale is too weak: {joined}")
    return errors


def validate_atomic_issue_quality_review(change_dir: Path, stage: str, tasks: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "task-planning", "pre-execution"}:
        return errors
    packet_doc = read_yaml(change_dir / "atomic-issue-packets.yaml")
    packets = packet_doc.get("packets", {}) if isinstance(packet_doc.get("packets"), dict) else {}
    task_ids = ids(r"\b(T\d{3})\b", tasks) | set(map(str, packets.keys()))
    if not task_ids:
        return errors
    path = change_dir / "atomic-issue-quality-review.yaml"
    review_doc = read_yaml(path)
    if not review_doc:
        return [f"{path}: required planning quality review artifact is missing or empty"]
    scope = review_doc.get("review_scope", {}) if isinstance(review_doc.get("review_scope"), dict) else {}
    reviewer_type = str(scope.get("reviewer_type", "")).strip().lower().replace("_", "-")
    if reviewer_type not in {"readonly-subagent", "read-only-subagent"}:
        errors.append(f"{path}: review_scope.reviewer_type must be readonly-subagent or read-only-subagent; main-local fallback is not allowed")
    errors.extend(validate_subagent_execution_proof(scope, f"{path}: review_scope"))
    reviewed_outputs = flatten_text(scope.get("validator_outputs_reviewed"))
    for required in ["atomic_issue_compile", "validate_artifacts", "workflowctl"]:
        if required not in reviewed_outputs:
            errors.append(f"{path}: review_scope.validator_outputs_reviewed must include {required}")
    boundary_definition = scope.get("atomic_boundary_definition", {}) if isinstance(scope.get("atomic_boundary_definition"), dict) else {}
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
                f"{path}: review_scope.atomic_boundary_definition must include the methodology Atomic Boundary conditions: "
                "zero decision, single-layer change, self-contained context, short verification loop, and no error propagation"
            )
            break
    if not re.search(r"primary[_ -]?closure|action[- ]?flow|stateful|provided contract|verification loop|用户动作|状态机|提供.*契约|验证闭环|拆分.*证据", boundary_definition_text, re.IGNORECASE):
        errors.append(
            f"{path}: review_scope.atomic_boundary_definition must state that primary_closure/action-flow/stateful operation/provided contract/verification loop are split evidence, not the Atomic Boundary definition"
        )
    reviews = review_doc.get("reviews", [])
    rows = [row for row in reviews if isinstance(row, dict)] if isinstance(reviews, list) else []
    rows_by_task = {str(row.get("task", "")).strip(): row for row in rows if str(row.get("task", "")).strip()}
    for task_id in sorted(task_ids):
        row = rows_by_task.get(task_id)
        if not row:
            errors.append(f"{path}: missing review row for {task_id}")
            continue
        if str(row.get("verdict", "")).strip().lower() != "pass":
            errors.append(f"{path}: {task_id} verdict must be pass before pre-execution")
        for field in [
            "source_context_quality",
            "no_validator_gaming",
            "owner_boundary",
            "atomicity",
            "brief_overflow_handling",
            "frontend_backend_proof_boundary",
            "compiler_failure_triage",
        ]:
            value = str(row.get(field, "")).strip().lower().replace("_", "-")
            if value not in {"pass", "not-applicable", "not applicable", "n/a"}:
                errors.append(f"{path}: {task_id}.{field} must be pass or not_applicable, got {row.get(field)!r}")
        boundary_check = row.get("atomic_boundary_check", {}) if isinstance(row.get("atomic_boundary_check"), dict) else {}
        for field in [
            "zero_decision",
            "single_layer_change",
            "self_contained_context",
            "short_verification_loop",
            "no_error_propagation",
        ]:
            value = str(boundary_check.get(field, "")).strip().lower().replace("_", "-")
            if value != "pass":
                errors.append(f"{path}: {task_id}.atomic_boundary_check.{field} must be pass")
        split_note = flatten_text(boundary_check.get("split_evidence_used"))
        if not re.search(r"primary[_ -]?closure|action[- ]?flow|stateful|provided contract|verification loop|用户动作|状态机|提供.*契约|验证闭环|拆分.*证据", split_note, re.IGNORECASE):
            errors.append(
                f"{path}: {task_id}.atomic_boundary_check.split_evidence_used must mention split evidence and must not replace the five Atomic Boundary checks"
            )
        if row.get("blocking_findings"):
            errors.append(f"{path}: {task_id} has blocking_findings")
        if len(flatten_text(row.get("evidence"))) < 80:
            errors.append(f"{path}: {task_id} evidence is too thin")
        evidence = flatten_text(row.get("evidence"))
        if not re.search(r"atomic-issues/T\d{3}\.md|atomic-issue-packets\.yaml|task-dag\.yaml|contracts\.yaml|verification\.yaml|atomic-task-decomposition\.md", evidence):
            errors.append(f"{path}: {task_id} evidence must cite artifact path or section")
        if TEMPLATE_REVIEW_EVIDENCE_RE.search(evidence):
            errors.append(f"{path}: {task_id} evidence is template-like; cite concrete section names, fields, owners, or rows reviewed")

    for task_id, packet_raw in packets.items():
        packet = packet_raw if isinstance(packet_raw, dict) else {}
        issue_text = issue_markdown_text(change_dir, str(task_id), packet)
        source_text = flatten_text(packet.get("sources")) + "\n" + first_existing_section(issue_text, "Source Context", "来源上下文")
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
            errors.append(f"{path}: {task_id} Source Context appears to contain task self-requirements instead of upstream facts")
        if QUALITY_GATE_PHRASE_RE.search(execution_text + "\n" + source_text):
            errors.append(f"{path}: {task_id} contains validator/gate phrase instead of executable semantics")
        file_text = flatten_text(packet.get("files_to_change"))
        if ALLOWLIST_CEILING_RE.search(file_text):
            errors.append(f"{path}: {task_id} files_to_change contains allowlist-ceiling/validator-feasibility wording")
        module_text = flatten_text([packet.get("title"), packet.get("primary_module"), packet.get("module_responsibility")])
        is_frontend = bool(FRONTEND_FILE_RE.search(file_text) or FRONTEND_TASK_RE.search(module_text))
        is_backend = bool(not is_frontend and re.search(r"\bbackend|后端|service|manager|controller|runtime|provider\b", module_text + " " + file_text, re.IGNORECASE))
        if is_frontend and FRONTEND_CLAIMS_PROVIDER_PROOF_RE.search(execution_text):
            errors.append(f"{path}: {task_id} frontend packet claims provider/ownership cleanup proof; move proof to backend owner task")
        if is_frontend and packet.get("managed_resource_ownership"):
            errors.append(f"{path}: {task_id} frontend packet must not own managed_resource_ownership rows; move ownership lifecycle to backend owner task")
        if is_backend and BACKEND_CLAIMS_BROWSER_PROOF_RE.search(execution_text):
            errors.append(f"{path}: {task_id} backend packet claims browser/DOM proof; move proof to frontend owner task")
    return errors


def normalize_multi_perspective_stage(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    return MULTI_PERSPECTIVE_STAGE_ALIASES.get(normalized, normalized)


def repair_triggering_finding_errors(value: object, label: str) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    perspectives: set[str] = set()
    rows = value if isinstance(value, list) else []
    if not rows:
        return [f"{label} must contain structured finding rows"], perspectives
    for index, raw in enumerate(rows, 1):
        row = raw if isinstance(raw, dict) else {}
        row_label = f"{label}[{index}]"
        for field in ["finding_id", "perspective", "root_cause", "canonical_owner", "invariant", "deterministic_proof", "negative_assertion"]:
            if len(str(row.get(field, "")).strip()) < 4:
                errors.append(f"{row_label}.{field} is required and must be concrete")
        perspective = str(row.get("perspective", "")).strip()
        if perspective:
            perspectives.add(perspective)
        for field in ["affected_artifacts", "projection_targets"]:
            values = row.get(field)
            if not isinstance(values, list) or not any(len(str(item).strip()) >= 4 for item in values):
                errors.append(f"{row_label}.{field} must list concrete targets")
    return errors, perspectives


def validate_multi_perspective_review(change_dir: Path, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in MULTI_PERSPECTIVE_REVIEW_STAGES and stage != "all":
        return errors

    if stage == "all":
        workflow_state = read_yaml(change_dir / "workflow-state.yaml")
        stage_status = workflow_state.get("stage_status", {}) if isinstance(workflow_state.get("stage_status"), dict) else {}
        stages_to_validate = sorted(
            s
            for s in MULTI_PERSPECTIVE_REVIEW_STAGES
            if (change_dir / "multi-perspective-reviews" / f"{s}.yaml").exists() or stage_status.get(s) == "passed"
        )
        all_errors: list[str] = []
        for stage_name in stages_to_validate:
            all_errors.extend(validate_multi_perspective_review(change_dir, stage_name))
        return all_errors

    path = change_dir / "multi-perspective-reviews" / f"{stage}.yaml"
    doc = read_yaml(path)
    if not doc:
        return [f"{path}: required multi-perspective review artifact is missing or empty"]

    scope = doc.get("review_scope", {}) if isinstance(doc.get("review_scope"), dict) else {}
    scope_stage_raw = str(scope.get("stage_under_review", "")).strip()
    scope_stage = normalize_multi_perspective_stage(scope_stage_raw)
    if scope_stage_raw and scope_stage_raw.lower().replace("_", "-") not in MULTI_PERSPECTIVE_ALLOWED_STAGES:
        errors.append(f"{path}: unknown review_scope.stage_under_review {scope_stage_raw!r}")
    if stage != "all" and scope_stage and scope_stage != stage:
        errors.append(f"{path}: review_scope.stage_under_review {scope_stage_raw!r} resolves to {scope_stage!r}, expected {stage!r}")
    if not scope_stage_raw:
        errors.append(f"{path}: review_scope.stage_under_review is required")
    for field in ["gate_name", "main_agent_owner"]:
        if not str(scope.get(field, "")).strip():
            errors.append(f"{path}: review_scope.{field} is required")
    try:
        required_count = int(scope.get("required_reviewer_count"))
    except Exception:
        required_count = -1
    review_kind = str(scope.get("review_kind", "")).strip() or "initial"
    if review_kind not in {"initial", "semantic-repair", "projection-repair", "format-repair"}:
        errors.append(f"{path}: unsupported review_scope.review_kind {review_kind!r}")
    policy = REVIEW_POLICY.get(stage, {})
    minimum = int(policy.get("initial_min", 1)) if review_kind == "initial" else int(policy.get("repair_min", 1))
    maximum = int(policy.get("max", 5))
    if required_count < minimum:
        errors.append(f"{path}: {review_kind} requires at least {minimum} reviewer(s), got {required_count}")
    if required_count > maximum:
        errors.append(f"{path}: stage policy allows at most {maximum} reviewer(s), got {required_count}")
    if review_kind != "initial":
        repair_context = doc.get("repair_context", {}) if isinstance(doc.get("repair_context"), dict) else {}
        if len(str(repair_context.get("previous_review_ref", "")).strip()) < 8:
            errors.append(f"{path}: repair_context.previous_review_ref is required for repair review")
        changed = [str(item).strip() for item in repair_context.get("changed_artifacts", [])] if isinstance(repair_context.get("changed_artifacts"), list) else []
        repair_errors, triggering_perspectives = repair_triggering_finding_errors(
            repair_context.get("triggering_findings"), f"{path}: repair_context.triggering_findings"
        )
        errors.extend(repair_errors)
        if not any(len(item) >= 4 for item in changed):
            errors.append(f"{path}: repair_context.changed_artifacts is required for repair review")
        if len(str(repair_context.get("narrowed_review_reason", "")).strip()) < 12:
            errors.append(f"{path}: repair_context.narrowed_review_reason must justify narrowed perspectives")

    packet = doc.get("frozen_input_packet", {}) if isinstance(doc.get("frozen_input_packet"), dict) else {}
    if not isinstance(packet.get("frozen_artifacts"), list) or not packet.get("frozen_artifacts"):
        errors.append(f"{path}: frozen_input_packet.frozen_artifacts must list reviewed canonical artifacts")
    for field in ["stage_objective", "review_objective"]:
        if not str(packet.get(field, "")).strip():
            errors.append(f"{path}: frozen_input_packet.{field} is required")
    for field in ["reviewable_scope", "non_reviewable_scope"]:
        if not isinstance(packet.get(field), list) or not packet.get(field):
            errors.append(f"{path}: frozen_input_packet.{field} is required")
    digest_policy = packet.get("digest_policy", {}) if isinstance(packet.get("digest_policy"), dict) else {}
    if str(digest_policy.get("stage_artifact_digest", "")).strip() != "workflowctl.artifact_receipt_digest":
        errors.append(f"{path}: frozen_input_packet.digest_policy.stage_artifact_digest must be workflowctl.artifact_receipt_digest")
    if str(digest_policy.get("workflow_workdir_policy", "")).strip() != "normalized-identity-before-resume-verification":
        errors.append(f"{path}: frozen_input_packet.digest_policy.workflow_workdir_policy must describe the normalized identity digest")
    if digest_policy.get("treat_receipt_digest_as_raw_sha256") is not False:
        errors.append(f"{path}: frozen_input_packet.digest_policy.treat_receipt_digest_as_raw_sha256 must be false")

    if scope_stage in {"prd", "readiness", "aip", "design", "contract", "verification", "task-planning", "pre-execution"}:
        ds_inputs = packet.get("decision_surface_inputs", {}) if isinstance(packet.get("decision_surface_inputs"), dict) else {}
        if ds_inputs.get("required_when_applicable") is not False:
            if not str(ds_inputs.get("decision_surface_discovery_path", "")).strip():
                errors.append(f"{path}: decision_surface_inputs.decision_surface_discovery_path is required for decision-bearing stages")
            for field in [
                "generative_stress_tests_reviewed",
                "surface_obligation_projection_reviewed",
                "semantic_consumption_matrix_reviewed",
            ]:
                if ds_inputs.get(field) is not True:
                    errors.append(f"{path}: decision_surface_inputs.{field} must be true or required_when_applicable=false")

    reviewers = doc.get("reviewers") if isinstance(doc.get("reviewers"), list) else []
    if not reviewers:
        errors.append(f"{path}: reviewers must include completed reviewer rows")
    if required_count > 0 and len(reviewers) < required_count:
        errors.append(f"{path}: reviewers count {len(reviewers)} is less than required_reviewer_count {required_count}")
    completed_count = 0
    reviewer_ids: set[str] = set()
    perspectives: set[str] = set()
    for idx, raw in enumerate(reviewers, 1):
        row = raw if isinstance(raw, dict) else {}
        rid = str(row.get("reviewer_id", "")).strip()
        if not rid:
            errors.append(f"{path}: reviewer row {idx} missing reviewer_id")
        elif rid in reviewer_ids:
            errors.append(f"{path}: duplicate reviewer_id {rid}")
        else:
            reviewer_ids.add(rid)
        reviewer_type = str(row.get("reviewer_type", "")).strip().lower().replace("_", "-")
        if reviewer_type not in MULTI_PERSPECTIVE_ALLOWED_REVIEWER_TYPES:
            errors.append(f"{path}: reviewer {rid or idx} has invalid reviewer_type {row.get('reviewer_type')!r}")
        errors.extend(validate_subagent_execution_proof(row, f"{path}: reviewer {rid or idx}"))
        perspective = str(row.get("perspective", "")).strip()
        if not perspective:
            errors.append(f"{path}: reviewer {rid or idx} missing perspective")
        else:
            perspectives.add(perspective)
        if not str(row.get("assigned_objective", "")).strip():
            errors.append(f"{path}: reviewer {rid or idx} missing assigned_objective")
        for field in ["frozen_input_refs", "forbidden_scope"]:
            if not isinstance(row.get(field), list) or not row.get(field):
                errors.append(f"{path}: reviewer {rid or idx} must list {field}")
        status = str(row.get("status", "")).strip().lower()
        if status == "completed":
            completed_count += 1
        elif status:
            errors.append(f"{path}: reviewer {rid or idx} status must be completed before gate pass, got {status!r}")
        else:
            errors.append(f"{path}: reviewer {rid or idx} missing status")
    if required_count > 0 and completed_count < required_count:
        errors.append(f"{path}: completed reviewer count {completed_count} is less than required_reviewer_count {required_count}")
    if required_count >= 2 and len(perspectives) < 2:
        errors.append(f"{path}: stage-level review needs at least two distinct reviewer perspectives")
    if review_kind != "initial":
        if len(reviewers) != required_count:
            errors.append(f"{path}: repair reviewers count must exactly equal required_reviewer_count")
        if required_count != len(triggering_perspectives):
            errors.append(f"{path}: repair required_reviewer_count must equal unique triggering finding perspectives")
        if perspectives != triggering_perspectives:
            errors.append(f"{path}: repair reviewer perspectives must exactly match triggering finding perspectives")

    findings = doc.get("findings") if isinstance(doc.get("findings"), list) else []
    finding_ids: set[str] = set()
    blocker_ids: set[str] = set()
    for idx, raw in enumerate(findings, 1):
        row = raw if isinstance(raw, dict) else {}
        fid = str(row.get("finding_id", "")).strip()
        if not fid:
            errors.append(f"{path}: finding row {idx} missing finding_id")
        elif fid in finding_ids:
            errors.append(f"{path}: duplicate finding_id {fid}")
        else:
            finding_ids.add(fid)
        rid = str(row.get("reviewer_id", "")).strip()
        if rid and reviewer_ids and rid not in reviewer_ids:
            errors.append(f"{path}: finding {fid or idx} references unknown reviewer_id {rid}")
        severity = str(row.get("severity", "")).strip().lower()
        if severity not in MULTI_PERSPECTIVE_ALLOWED_SEVERITIES:
            errors.append(f"{path}: finding {fid or idx} has invalid severity {row.get('severity')!r}")
        if severity == "blocker" and fid:
            blocker_ids.add(fid)
        if not isinstance(row.get("evidence_paths"), list) or not row.get("evidence_paths"):
            errors.append(f"{path}: finding {fid or idx} must cite evidence_paths")
        for field in ["violated_rule", "why_current_artifact_is_insufficient", "suggested_backflow_stage"]:
            if not str(row.get(field, "")).strip():
                errors.append(f"{path}: finding {fid or idx} missing {field}")

    dispositions = doc.get("main_agent_dispositions") if isinstance(doc.get("main_agent_dispositions"), list) else []
    disposition_by_finding: dict[str, dict] = {}
    for idx, raw in enumerate(dispositions, 1):
        row = raw if isinstance(raw, dict) else {}
        fid = str(row.get("finding_id", "")).strip()
        if not fid:
            errors.append(f"{path}: disposition row {idx} missing finding_id")
            continue
        if fid in disposition_by_finding:
            errors.append(f"{path}: duplicate disposition for {fid}")
        disposition_by_finding[fid] = row
        if finding_ids and fid not in finding_ids:
            errors.append(f"{path}: disposition references unknown finding_id {fid}")
        disposition = str(row.get("disposition", "")).strip().lower()
        if disposition not in MULTI_PERSPECTIVE_ALLOWED_DISPOSITIONS:
            errors.append(f"{path}: disposition for {fid} has invalid disposition {row.get('disposition')!r}")
        if not str(row.get("disposition_reason", "")).strip():
            errors.append(f"{path}: disposition for {fid} missing disposition_reason")
        if disposition == "rejected" and (not isinstance(row.get("counter_evidence_paths"), list) or not row.get("counter_evidence_paths")):
            errors.append(f"{path}: rejected finding {fid} requires counter_evidence_paths")
        if disposition == "backflow-created" and not str(row.get("backflow_id", "")).strip():
            errors.append(f"{path}: backflow-created finding {fid} requires backflow_id")
        if disposition in {"accepted", "backflow-created"} and row.get("canonical_updates_completed") is not True:
            errors.append(f"{path}: {disposition} finding {fid} requires canonical_updates_completed=true")
        if row.get("human_decision_prompt_required") is True and not str(row.get("human_decision_prompt_id", "")).strip():
            errors.append(f"{path}: finding {fid} requires human_decision_prompt_id")
    for fid in sorted(finding_ids):
        if fid not in disposition_by_finding:
            errors.append(f"{path}: finding {fid} lacks main_agent_disposition")

    gate = doc.get("gate_result", {}) if isinstance(doc.get("gate_result"), dict) else {}
    verdict = str(gate.get("verdict", "")).strip().lower()
    if verdict not in {"blocked", "pass"}:
        errors.append(f"{path}: gate_result.verdict must be blocked or pass")
    open_blockers = gate.get("blocking_findings_open")
    if not isinstance(open_blockers, list):
        errors.append(f"{path}: gate_result.blocking_findings_open must be a list")
        open_blockers = []
    if verdict == "pass":
        if open_blockers:
            errors.append(f"{path}: gate_result.verdict=pass but blocking_findings_open is not empty")
        unresolved = [
            fid
            for fid in blocker_ids
            if str(disposition_by_finding.get(fid, {}).get("disposition", "")).strip().lower()
            not in {"rejected", "backflow-created", "superseded"}
        ]
        if unresolved:
            errors.append(f"{path}: blocker findings lack closing disposition: {', '.join(sorted(unresolved))}")
        if gate.get("ready_for_next_stage") is not True:
            errors.append(f"{path}: gate_result.verdict=pass requires ready_for_next_stage=true")
        if not isinstance(gate.get("validators_rerun"), list) or not gate.get("validators_rerun"):
            errors.append(f"{path}: gate_result.verdict=pass requires validators_rerun evidence")
    if verdict == "blocked" and gate.get("ready_for_next_stage") is True:
        errors.append(f"{path}: blocked gate cannot set ready_for_next_stage=true")
    return errors


def validate_compiler_failure_triage(change_dir: Path, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "task-planning", "pre-execution"}:
        return errors
    packets_doc = read_yaml(change_dir / "atomic-issue-packets.yaml")
    packets = packets_doc.get("packets", {}) if isinstance(packets_doc.get("packets"), dict) else {}
    if not packets:
        return errors
    path = change_dir / "compiler-failure-triage.yaml"
    doc = read_yaml(path)
    if not doc:
        return [f"{path}: required compiler failure triage artifact is missing or empty"]
    scope = doc.get("triage_scope", {}) if isinstance(doc.get("triage_scope"), dict) else {}
    if str(scope.get("no_packet_edits_before_triage", "")).strip().lower() not in {"true", "yes", "是"}:
        errors.append(f"{path}: triage_scope.no_packet_edits_before_triage must be true")
    rows = doc.get("rows", [])
    rows = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    allowed_decisions = {"current-task-owner", "move-to-existing-owner", "split-new-task", "upstream-backflow", "validator-gap-blocked"}
    for idx, row in enumerate(rows, start=1):
        rid = str(row.get("id", f"row-{idx}")).strip()
        task = str(row.get("task", "")).strip()
        if not re.match(r"^T\d{3}$", task):
            errors.append(f"{path}: {rid}.task must be a Txxx id")
        if not str(row.get("compiler_error", "")).strip():
            errors.append(f"{path}: {rid}.compiler_error is required")
        owner_decision = str(row.get("owner_decision", "")).strip()
        if owner_decision not in allowed_decisions:
            errors.append(f"{path}: {rid}.owner_decision must be one of {sorted(allowed_decisions)}, got {owner_decision!r}")
        reason = flatten_text(row.get("true_owner_reason"))
        if owner_decision == "current-task-owner":
            if not re.search(r"atomic-task-decomposition\.md|contracts\.yaml|decision-surface-discovery\.md|task-dag\.yaml|C-\d{3}|DS-\d{3}", reason):
                errors.append(f"{path}: {rid}.true_owner_reason must cite owner assignment evidence for current-task-owner")
        if owner_decision in {"move-to-existing-owner", "split-new-task", "upstream-backflow"}:
            move = row.get("task_split_or_move", {}) if isinstance(row.get("task_split_or_move"), dict) else {}
            if not flatten_text(move):
                errors.append(f"{path}: {rid}.task_split_or_move is required for {owner_decision}")
        if owner_decision == "validator-gap-blocked":
            if not re.search(r"blocked|阻塞|do not|不得|不能", flatten_text(row.get("allowed_fix")) + " " + flatten_text(row.get("prohibited_fix")), re.IGNORECASE):
                errors.append(f"{path}: {rid} validator-gap-blocked must explicitly block packet/task-dag expansion")
        delta = row.get("files_to_change_delta", {}) if isinstance(row.get("files_to_change_delta"), dict) else {}
        added = flatten_text(delta.get("added"))
        if added and owner_decision != "current-task-owner":
            errors.append(f"{path}: {rid} adds files_to_change but owner_decision is {owner_decision}; only current-task-owner may add true write scope")
        if ALLOWLIST_CEILING_RE.search(flatten_text(row)):
            errors.append(f"{path}: {rid} contains allowlist-ceiling/validator-feasibility wording")
    summary = doc.get("summary", {}) if isinstance(doc.get("summary"), dict) else {}
    if not rows and sum(int(summary.get(key, 0) or 0) for key in ["current_task_owner_fixes", "moved_to_existing_owner", "split_new_task", "upstream_backflow", "validator_gap_blocked"]) == 0:
        errors.append(f"{path}: rows or summary counts must record compiler failure triage decisions")
    return errors


def validate_task_planning_repair_ledger(change_dir: Path, stage: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "task-planning", "pre-execution"}:
        return errors
    packets_doc = read_yaml(change_dir / "atomic-issue-packets.yaml")
    packets = packets_doc.get("packets", {}) if isinstance(packets_doc.get("packets"), dict) else {}
    if not packets:
        return errors
    path = change_dir / "task-planning-repair-ledger.yaml"
    doc = read_yaml(path)
    if not doc:
        return [f"{path}: required task planning repair ledger artifact is missing or empty"]
    if str(doc.get("stage", "")).strip() not in {"task-planning", "atomic-task-planning"}:
        errors.append(f"{path}: stage must be task-planning")
    scope = doc.get("ledger_scope", {}) if isinstance(doc.get("ledger_scope"), dict) else {}
    if not str(scope.get("generator_entrypoint", "")).strip():
        errors.append(f"{path}: ledger_scope.generator_entrypoint is required")
    rule = flatten_text(scope.get("rule")).lower()
    for required in ["regression", "fixed", "generator"]:
        if required not in rule:
            errors.append(f"{path}: ledger_scope.rule must mention {required}")
    rows = doc.get("repair_iterations", [])
    rows = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
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
    for idx, row in enumerate(rows, start=1):
        signature = str(row.get("failure_signature", "")).strip()
        if not signature or signature.startswith("<"):
            continue
        rid = str(row.get("iteration_id") or f"row-{idx}").strip()
        status = str(row.get("status", "")).strip()
        if status not in allowed_status:
            errors.append(f"{path}: {rid}.status must be one of {sorted(allowed_status)}")
        if status in {"open", "fixed"}:
            previous = active_signatures.get(signature)
            if previous:
                errors.append(
                    f"{path}: duplicate active/fixed failure_signature {signature} in {previous} and {rid}; "
                    "reappearing fixed signatures must be generator-invariant-failure, not another local repair"
                )
            active_signatures[signature] = rid
        if str(row.get("failure_class", "")).strip() not in allowed_classes:
            errors.append(f"{path}: {rid}.failure_class must be one of {sorted(allowed_classes)}")
        affected = [str(item).strip() for item in as_list(row.get("affected_tasks")) if str(item).strip()]
        if not affected:
            errors.append(f"{path}: {rid}.affected_tasks is required")
        for task_id in affected:
            if not re.match(r"^T\d{3}$", task_id):
                errors.append(f"{path}: {rid}.affected_tasks contains non-Txxx id {task_id!r}")
        for field in ["root_cause", "owner_invariant"]:
            if not str(row.get(field, "")).strip():
                errors.append(f"{path}: {rid}.{field} is required")
        if not [item for item in as_list(row.get("forbidden_regression")) if len(str(item).strip()) >= 8 and not str(item).strip().startswith("<")]:
            errors.append(f"{path}: {rid}.forbidden_regression is required")
        if not [item for item in as_list(row.get("generator_rules_changed")) if len(str(item).strip()) >= 6 and not str(item).strip().startswith("<")]:
            errors.append(f"{path}: {rid}.generator_rules_changed is required")
        checks = [item for item in as_list(row.get("regression_checks")) if isinstance(item, dict)]
        if not checks:
            errors.append(f"{path}: {rid}.regression_checks is required")
        for cidx, check in enumerate(checks, start=1):
            cid = str(check.get("check_id") or f"check-{cidx}").strip()
            for field in ["command", "expected_result"]:
                value = str(check.get(field, "")).strip()
                if not value or value.startswith("<"):
                    errors.append(f"{path}: {rid}.{cid}.{field} is required")
            last_result = str(check.get("last_result", "")).strip()
            if status == "fixed" and (not last_result or last_result.startswith("<")):
                errors.append(f"{path}: {rid}.{cid}.last_result is required for fixed rows")
    known = doc.get("known_regressions", [])
    known = [row for row in known if isinstance(row, dict)] if isinstance(known, list) else []
    for idx, row in enumerate(known, start=1):
        signature = str(row.get("signature", "")).strip()
        if not signature or signature.startswith("<"):
            continue
        if not str(row.get("owner_invariant", "")).strip():
            errors.append(f"{path}: known_regressions[{idx}].owner_invariant is required")
        if not [item for item in as_list(row.get("must_not_reappear_in")) if str(item).strip()]:
            errors.append(f"{path}: known_regressions[{idx}].must_not_reappear_in is required")
        if not str(row.get("regression_check_command", "")).strip():
            errors.append(f"{path}: known_regressions[{idx}].regression_check_command is required")
    return errors


def validate_variant_impact_artifacts(change_dir: Path, stage: str, proposal: str, spec: str, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "archaeology", "contract", "verification", "task-planning", "pre-execution"}:
        return errors
    combined = "\n".join(
        [
            proposal,
            spec,
            plan,
            tasks,
            read(change_dir / "decision-surface-discovery.md"),
            read(change_dir / "stateful-behavior-matrix.md"),
            read(change_dir / "contracts.yaml"),
            read(change_dir / "task-dag.yaml"),
            read(change_dir / "atomic-issue-packets.yaml"),
        ]
    )
    decision_surface = read(change_dir / "decision-surface-discovery.md")
    has_decision_surface_variant = bool(VARIANT_DECISION_SURFACE_RE.search(decision_surface)) and bool(
        re.search(r"\b(?:same|shared|existing|old|consumer|readback|post[- ]?create|runtime|mode|variant|deployment|provider)\b|同一|共享|旧|消费者|读回|创建后|运行时|模式|变体", decision_surface, re.IGNORECASE)
    )
    has_structural_variant_evidence = bool(
        re.search(r"Existing Object-Action-Consumer Graph|Variant Impact Matrix|Mode Semantic Inheritance Audit|same object|same action|shared entry|old consumer assumption|同一.*(?:对象|操作|入口)|旧.*(?:假设|消费者)", combined, re.IGNORECASE)
    )
    has_variant_signal = has_decision_surface_variant or has_structural_variant_evidence
    has_variant_artifact = any((change_dir / rel).exists() for rel in REQUIRED_OBJECT_ACTION_CONSUMER_FILES)
    if not has_variant_signal and not has_variant_artifact:
        return errors

    for rel, columns in REQUIRED_OBJECT_ACTION_CONSUMER_FILES.items():
        path = change_dir / rel
        body = read(path)
        if not body.strip():
            errors.append(f"{path}: variant/object-action signal exists but required artifact is missing or empty")
            continue
        if not has_table_columns(body, columns):
            errors.append(f"{path}: must include columns {', '.join(columns)}")
        if not has_meaningful_rows(body):
            errors.append(f"{path}: must include concrete code-derived rows")
        if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
            errors.append(f"{path}: contains unresolved TBD/TODO/unknown value")

    variant_body = read(change_dir / "variant-impact-matrix.md")
    variant_detection = first_existing_section(variant_body, "Variant Detection Matrix")
    for row in table_dicts(variant_detection):
        joined = " | ".join(row.values())
        if re.search(r"\b(?:yes|supported|must|需要|支持)\b", joined, re.IGNORECASE):
            for label in ["New variant candidate", "Object/entity", "Existing action / mutation", "Shared entry/API/page", "Shared state/readback", "Detection evidence"]:
                if not table_get(row, label):
                    errors.append(f"{change_dir / 'variant-impact-matrix.md'}: required variant row missing {label}: {joined}")
            if not re.search(r"\b(C-\d{3}|VER-\d{3}|T\d{3}|locked|决策|contract|verification)\b", joined, re.IGNORECASE):
                errors.append(f"{change_dir / 'variant-impact-matrix.md'}: supported variant row lacks contract/verification/task mapping: {joined}")

    parity_section = first_existing_section(variant_body, "Old Consumer Parity Matrix")
    if variant_body.strip() and not parity_section:
        errors.append(f"{change_dir / 'variant-impact-matrix.md'}: missing Old Consumer Parity Matrix")
    for row in table_dicts(parity_section):
        joined = " | ".join(row.values())
        must_satisfy = table_get(row, "Must new variant satisfy?")
        if re.search(r"\b(?:yes|true|must|required|需要|支持|是)\b", must_satisfy, re.IGNORECASE):
            for label in ["New variant", "Object/action", "Existing consumer surface", "Old variant assumption", "New producer/behavior", "Contract candidate", "Verification"]:
                value = table_get(row, label)
                if not value or re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", value, re.IGNORECASE):
                    errors.append(f"{change_dir / 'variant-impact-matrix.md'}: parity row missing {label}: {joined}")
            if re.search(r"progress|change|last-change|event|task step|进度|变更|事件|任务步骤", joined, re.IGNORECASE):
                if not read(change_dir / "progress-change-producer-chain-matrix.md").strip():
                    errors.append(
                        f"{change_dir / 'variant-impact-matrix.md'}: progress/change parity row requires progress-change-producer-chain-matrix.md: {joined}"
                    )

    if stage in {"task-planning", "pre-execution", "all"}:
        context = read(change_dir / "atomic-planning-context-pack.md")
        packets = read(change_dir / "atomic-issue-packets.yaml")
        decomposition = read(change_dir / "atomic-task-decomposition.md")
        for rel in REQUIRED_OBJECT_ACTION_CONSUMER_FILES:
            if (change_dir / rel).exists() and rel not in context:
                errors.append(f"{change_dir / 'atomic-planning-context-pack.md'}: must consume {rel}")
        if (change_dir / "variant-impact-matrix.md").exists():
            if "variant-impact-matrix.md" not in decomposition:
                errors.append(f"{change_dir / 'atomic-task-decomposition.md'}: must map variant-impact-matrix.md rows to decomposed task edges")
            if not re.search(r"variant|变体|Existing Object|Object-Action|old consumer|旧.*consumer|consumer assumption", packets, re.IGNORECASE):
                errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: must carry variant/object-action consumer semantics into owner packets")
    return errors


def validate_progress_change_producer_chain(change_dir: Path, stage: str, proposal: str, spec: str, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "contract", "verification", "task-planning", "pre-execution", "mock-acceptance", "product-acceptance"}:
        return errors
    combined = "\n".join(
        [
            proposal,
            spec,
            plan,
            tasks,
            read(change_dir / "existing-object-action-consumer-graph.md"),
            read(change_dir / "variant-impact-matrix.md"),
            read(change_dir / "stateful-behavior-matrix.md"),
            read(change_dir / "stateful-behavior-matrix.yaml"),
            read(change_dir / "contracts.yaml"),
            read(change_dir / "verification.yaml"),
            read(change_dir / "atomic-issue-packets.yaml"),
        ]
    )
    has_progress_signal = bool(PROGRESS_CHANGE_SIGNAL_RE.search(combined))
    path = change_dir / "progress-change-producer-chain-matrix.md"
    body = read(path)
    if not has_progress_signal and not body.strip():
        return errors
    if not body.strip():
        errors.append(f"{path}: progress/change/last-change signal exists but producer chain matrix is missing or empty")
        return errors
    if not has_table_columns(body, PROGRESS_CHANGE_PRODUCER_COLUMNS):
        errors.append(f"{path}: must include columns {', '.join(PROGRESS_CHANGE_PRODUCER_COLUMNS)}")
    if not has_meaningful_rows(body):
        errors.append(f"{path}: must include concrete producer chain rows")
    if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
        errors.append(f"{path}: contains unresolved TBD/TODO/unknown value")

    chain_section = first_existing_section(body, "Progress / Change Producer Chain Matrix")
    rows = table_dicts(chain_section)
    for row in rows:
        chain_id = table_get(row, "Chain ID") or "<missing>"
        joined = " | ".join(row.values())
        if re.search(r"\b(?:N/A|not applicable|不适用|locked N/A)\b", joined, re.IGNORECASE):
            continue
        for label in PROGRESS_CHANGE_PRODUCER_COLUMNS:
            value = table_get(row, label)
            if not value:
                errors.append(f"{path}: chain {chain_id} missing {label}")
        for label in ["Canonical change writer", "State owner / table", "Task/event producer", "Correlation key", "Last-change readback", "Change detail readback", "Verification", "Owner issue"]:
            value = table_get(row, label)
            strong_re = PRODUCTION_FIELD_STRONG_RE[label]
            if not value or WEAK_PRODUCER_VALUE_RE.search(value) or not strong_re.search(value):
                errors.append(f"{path}: chain {chain_id} has weak or missing production {label}: {value or '<empty>'}")
        correlation_text = " ".join(
            [
                table_get(row, "Correlation key"),
                table_get(row, "Last-change readback"),
                table_get(row, "Change detail readback"),
                table_get(row, "Verification"),
            ]
        )
        if not SAME_ID_CHAIN_RE.search(correlation_text):
            errors.append(f"{path}: chain {chain_id} lacks same-id owner/verification/correlation proof")

    if stage in {"task-planning", "pre-execution", "all"}:
        context = read(change_dir / "atomic-planning-context-pack.md")
        packets = read(change_dir / "atomic-issue-packets.yaml")
        decomposition = read(change_dir / "atomic-task-decomposition.md")
        dag = read(change_dir / "task-dag.yaml") + "\n" + tasks
        if "progress-change-producer-chain-matrix.md" not in context:
            errors.append(f"{change_dir / 'atomic-planning-context-pack.md'}: must consume progress-change-producer-chain-matrix.md")
        if "progress-change-producer-chain-matrix.md" not in decomposition:
            errors.append(f"{change_dir / 'atomic-task-decomposition.md'}: must decompose progress-change producer chain rows")
        for required in ["change writer", "last-change", "change detail", "correlation", "progress/change producer"]:
            if not re.search(re.escape(required), packets, re.IGNORECASE):
                errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: must carry {required} semantics for progress/change producer tasks")
        if not re.search(r"progress|change|last-change|producer|event|state-machine|前端.*进度|变更", dag, re.IGNORECASE):
            errors.append(f"{change_dir / 'task-dag.yaml'}: must include DAG edge from runtime/change producer to progress/change consumer")
    return errors


def validate_external_side_effect_contract(change_dir: Path, stage: str, proposal: str, spec: str, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "contract", "verification", "task-planning", "pre-execution", "mock-acceptance", "product-acceptance"}:
        return errors
    combined = "\n".join(
        [
            proposal,
            spec,
            plan,
            tasks,
            read(change_dir / "external-capability-research.md"),
            read(change_dir / "contracts.yaml"),
            read(change_dir / "verification.yaml"),
            read(change_dir / "atomic-issue-packets.yaml"),
            read(change_dir / "mock-acceptance-cases.yaml"),
        ]
    )
    path = change_dir / "external-side-effect-contract-matrix.md"
    body = read(path)
    has_signal = bool(EXTERNAL_SIDE_EFFECT_SIGNAL_RE.search(combined))
    if not has_signal and not body.strip():
        return errors
    if not body.strip():
        errors.append(f"{path}: external side-effect signal exists but matrix is missing or empty")
        return errors
    if not has_table_columns(body, EXTERNAL_SIDE_EFFECT_COLUMNS):
        errors.append(f"{path}: must include columns {', '.join(EXTERNAL_SIDE_EFFECT_COLUMNS)}")
    if not has_meaningful_rows(body):
        errors.append(f"{path}: must include concrete external side-effect rows")
    if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
        errors.append(f"{path}: contains unresolved TBD/TODO/unknown value")
    section_text = first_existing_section(body, "External Side Effect Contract Matrix")
    for row in table_dicts(section_text):
        joined = " | ".join(row.values())
        if re.search(r"\b(?:N/A|not applicable|不适用|locked N/A)\b", joined, re.IGNORECASE):
            continue
        effect_id = table_get(row, "Effect ID") or "<missing>"
        for label in EXTERNAL_SIDE_EFFECT_COLUMNS:
            value = table_get(row, label)
            if not value:
                errors.append(f"{path}: effect {effect_id} missing {label}")
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
                errors.append(f"{path}: effect {effect_id} has weak or missing {label}: {value or '<empty>'}")
        proof_text = " ".join(
            [
                table_get(row, "Required production call/resource mutation"),
                table_get(row, "Minimum acceptable proof"),
                table_get(row, "State/readback consumer"),
            ]
        )
        if not re.search(r"\b(?:provider|operator|API|SDK|resource|scheduler|runtime|setCapacity|create|update|delete|readback|event|integration|mock-composition|cloud-runtime)\b|生产|调用|资源|读回|事件|运行时", proof_text, re.IGNORECASE):
            errors.append(f"{path}: effect {effect_id} lacks concrete production call/readback proof")
    if stage in {"task-planning", "pre-execution", "all"}:
        context = read(change_dir / "atomic-planning-context-pack.md")
        packets = read(change_dir / "atomic-issue-packets.yaml")
        decomposition = read(change_dir / "atomic-task-decomposition.md")
        if "external-side-effect-contract-matrix.md" not in context:
            errors.append(f"{change_dir / 'atomic-planning-context-pack.md'}: must consume external-side-effect-contract-matrix.md")
        if "external-side-effect-contract-matrix.md" not in decomposition:
            errors.append(f"{change_dir / 'atomic-task-decomposition.md'}: must decompose external side-effect rows")
        for required in ["external_side_effects", "production side effect", "minimum acceptable proof", "substitute boundary"]:
            if not re.search(re.escape(required), packets, re.IGNORECASE):
                errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: must carry {required} semantics for external side-effect tasks")
    return errors


def validate_runtime_test_topology(change_dir: Path, stage: str, proposal: str, spec: str, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "archaeology", "verification", "task-planning", "pre-execution"}:
        return errors
    combined = "\n".join(
        [
            proposal,
            spec,
            plan,
            tasks,
            read(change_dir / "external-side-effect-contract-matrix.md"),
            read(change_dir / "progress-change-producer-chain-matrix.md"),
            read(change_dir / "verification.yaml"),
            read(change_dir / "atomic-issue-packets.yaml"),
            read(change_dir / "task-dag.yaml"),
        ]
    )
    path = change_dir / "runtime-test-topology-matrix.md"
    body = read(path)
    has_signal = bool(RUNTIME_TEST_TOPOLOGY_SIGNAL_RE.search(combined)) or bool(read(change_dir / "external-side-effect-contract-matrix.md").strip())
    if not has_signal and not body.strip():
        return errors
    if not body.strip():
        errors.append(f"{path}: runtime/proof topology signal exists but matrix is missing or empty")
        return errors
    if not has_table_columns(body, RUNTIME_TEST_TOPOLOGY_COLUMNS):
        errors.append(f"{path}: must include columns {', '.join(RUNTIME_TEST_TOPOLOGY_COLUMNS)}")
    if not has_meaningful_rows(body):
        errors.append(f"{path}: must include concrete runtime proof topology rows")
    if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
        errors.append(f"{path}: contains unresolved TBD/TODO/unknown value")
    topology_section = first_existing_section(body, "Runtime Test Topology Matrix")
    for row in table_dicts(topology_section):
        joined = " | ".join(row.values())
        if re.search(r"\b(?:N/A|not applicable|不适用|locked N/A)\b", joined, re.IGNORECASE):
            continue
        topology_id = table_get(row, "Topology ID") or "<missing>"
        for label in RUNTIME_TEST_TOPOLOGY_COLUMNS:
            if not table_get(row, label):
                errors.append(f"{path}: topology {topology_id} missing {label}")
        proof_file = table_get(row, "Proof file/path")
        if proof_file and not re.search(r"\.(?:java|kt|scala|py|ts|tsx|js|jsx|yaml|yml|feature|sh)\b", proof_file):
            errors.append(f"{path}: topology {topology_id} proof file/path must be concrete: {proof_file}")
        if not re.search(r"\b(?:mvn|gradle|npm|pnpm|yarn|pytest|go test|cargo|playwright|browser|curl|install|package|test)\b|测试|安装|构建", table_get(row, "Verification command"), re.IGNORECASE):
            errors.append(f"{path}: topology {topology_id} verification command is not executable enough")
    proof_section = first_existing_section(body, "Proof Owner File Matrix")
    if body.strip() and not proof_section:
        errors.append(f"{path}: missing Proof Owner File Matrix")
    packets = read(change_dir / "atomic-issue-packets.yaml")
    dag = read(change_dir / "task-dag.yaml") + "\n" + tasks
    for row in table_dicts(proof_section):
        joined = " | ".join(row.values())
        if re.search(r"\b(?:N/A|not applicable|不适用|locked N/A)\b", joined, re.IGNORECASE):
            continue
        verification_id = table_get(row, "Verification ID") or "<missing>"
        owner_issue = table_get(row, "Owner issue")
        proof_file = table_get(row, "Proof file/path").strip("`")
        must_task = table_get(row, "Must be in task-dag files?")
        must_packet = table_get(row, "Must be in packet files_to_change?")
        for label in PROOF_OWNER_FILE_COLUMNS:
            if not table_get(row, label):
                errors.append(f"{path}: proof owner row {verification_id} missing {label}")
        if proof_file and re.search(r"\b(?:yes|true|是|required|must)\b", must_packet, re.IGNORECASE) and proof_file not in packets:
            errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: proof file {proof_file} from {verification_id} must be in owner packet files_to_change")
        if proof_file and re.search(r"\b(?:yes|true|是|required|must)\b", must_task, re.IGNORECASE) and proof_file not in dag:
            errors.append(f"{change_dir / 'task-dag.yaml'}: proof file {proof_file} from {verification_id} must be in task files allowlist")
        if owner_issue and owner_issue not in packets + "\n" + dag:
            errors.append(f"{path}: owner issue {owner_issue} for proof {verification_id} missing from packet/task DAG")
    if stage in {"task-planning", "pre-execution", "all"}:
        context = read(change_dir / "atomic-planning-context-pack.md")
        if "runtime-test-topology-matrix.md" not in context:
            errors.append(f"{change_dir / 'atomic-planning-context-pack.md'}: must consume runtime-test-topology-matrix.md")
        decomposition = read(change_dir / "atomic-task-decomposition.md")
        if "Proof Owner File" not in decomposition and "runtime-test-topology-matrix.md" not in decomposition:
            errors.append(f"{change_dir / 'atomic-task-decomposition.md'}: must map runtime proof owner files into task allowlists")
    return errors


def validate_runtime_materialization_parity(change_dir: Path, stage: str, proposal: str, spec: str, plan: str, tasks: str) -> list[str]:
    errors: list[str] = []
    if stage not in {"all", "design", "contract", "verification", "task-planning", "pre-execution", "mock-acceptance", "product-acceptance"}:
        return errors
    combined = "\n".join(
        [
            proposal,
            spec,
            plan,
            tasks,
            read(change_dir / "decision-surface-discovery.md"),
            read(change_dir / "external-capability-research.md"),
            read(change_dir / "contracts.yaml"),
            read(change_dir / "verification.yaml"),
            read(change_dir / "atomic-issue-packets.yaml"),
        ]
    )
    path = change_dir / "runtime-materialization-parity.md"
    body = read(path)
    has_surface = "runtime-mode-materialization-parity" in read(change_dir / "decision-surface-discovery.md")
    has_signal = has_surface or bool(RUNTIME_MATERIALIZATION_SIGNAL_RE.search(combined))
    if not has_signal and not body.strip():
        return errors
    if not body.strip():
        errors.append(f"{path}: runtime mode materialization parity signal exists but artifact is missing or empty")
        return errors
    required_sections = {
        "Runtime Mode Change Classification": RUNTIME_MATERIALIZATION_CLASSIFICATION_COLUMNS,
        "Product Capability Parity Matrix": RUNTIME_CAPABILITY_PARITY_COLUMNS,
        "Runtime Materialization Mapping": RUNTIME_MATERIALIZATION_MAPPING_COLUMNS,
    }
    for section_name, columns in required_sections.items():
        section_text = first_existing_section(body, section_name)
        if not section_text:
            errors.append(f"{path}: missing {section_name}")
            continue
        if not has_table_columns(section_text, columns):
            errors.append(f"{path}: {section_name} must include columns {', '.join(columns)}")
        if not has_meaningful_rows(section_text):
            errors.append(f"{path}: {section_name} must include concrete rows")
    if re.search(r"\b(TBD|TODO|unknown|待确认|未知)\b", body, re.IGNORECASE):
        errors.append(f"{path}: contains unresolved TBD/TODO/unknown value")

    classifications = first_existing_section(body, "Runtime Mode Change Classification")
    for row in table_dicts(classifications):
        joined = " | ".join(row.values())
        classification = table_get(row, "Classification")
        if not re.search(
            r"Additive coexisting mode|Replacement / retirement|Internal substrate refactor|Capability reduction / scoped mode|新增并存|替换|退役|内部.*重构|能力.*(?:降级|收缩)",
            classification,
            re.IGNORECASE,
        ):
            errors.append(f"{path}: classification row has invalid or weak Classification: {joined}")
        if not re.search(r"\b(?:PDEC|ADEC|DEC|DESIGN-DEC|MIG-DEC|C-|VER-|T)\d{0,3}|locked|决策|契约|验证|任务", joined, re.IGNORECASE):
            errors.append(f"{path}: classification row lacks locked decision/contract/verification/task trace: {joined}")

    capability_rows = table_dicts(first_existing_section(body, "Product Capability Parity Matrix"))
    mapping_body = first_existing_section(body, "Runtime Materialization Mapping")
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
    mapping_text = mapping_body + "\n" + body
    for capability_input in required_inputs:
        if not re.search(re.escape(capability_input), mapping_text, re.IGNORECASE):
            errors.append(f"{path}: Runtime Materialization Mapping must consider capability input {capability_input}")
    for row in capability_rows:
        joined = " | ".join(row.values())
        supported = table_get(row, "Supported?")
        unsupported_expr = table_get(row, "If not supported, product/API/UI expression")
        if re.search(r"\b(?:no|false|unsupported|不支持|否)\b", supported, re.IGNORECASE):
            if not re.search(r"\b(?:hidden|disabled|rejected|unavailable|not supported|隐藏|禁用|拒绝|不可用|不支持)\b", unsupported_expr, re.IGNORECASE):
                errors.append(f"{path}: unsupported capability lacks product/API/UI expression: {joined}")
        else:
            for label in ["Existing mode baseline", "New / changed mode obligation", "Contract ID", "Verification ID", "Owner issue"]:
                if not table_get(row, label):
                    errors.append(f"{path}: supported capability row missing {label}: {joined}")

    for row in table_dicts(mapping_body):
        joined = " | ".join(row.values())
        if re.search(r"\b(?:N/A|not applicable|不适用|locked N/A)\b", joined, re.IGNORECASE):
            continue
        mapping_id = table_get(row, "Mapping ID") or "<missing>"
        for label in RUNTIME_MATERIALIZATION_MAPPING_COLUMNS:
            if not table_get(row, label):
                errors.append(f"{path}: mapping {mapping_id} missing {label}")
        for label in ["New / changed mode materialization design", "Production owner", "Failure semantics", "Verification", "Owner issue"]:
            value = table_get(row, label)
            if not value or re.search(r"\b(?:resource exists|ASG exists|pod exists|process starts|DB state|final status|mock-only|fixture-only|same as old|same as above)\b|只.*(?:资源|状态|mock|fixture)|仅.*(?:资源|状态|mock|fixture)", value, re.IGNORECASE):
                errors.append(f"{path}: mapping {mapping_id} has weak or missing {label}: {value or '<empty>'}")
    negative_section = first_existing_section(body, "Runtime Parity Negative Assertions")
    if not negative_section:
        errors.append(f"{path}: missing Runtime Parity Negative Assertions")
    elif not re.search(r"Resource created|resource exists|ASG exists|pod exists|process starts|image/AMI/container|plugins|config|secrets|资源|插件|配置|密钥", negative_section, re.IGNORECASE):
        errors.append(f"{path}: Runtime Parity Negative Assertions must reject resource-exists/image-assumption shortcuts")

    if stage in {"task-planning", "pre-execution", "all"}:
        context = read(change_dir / "atomic-planning-context-pack.md")
        packets = read(change_dir / "atomic-issue-packets.yaml")
        decomposition = read(change_dir / "atomic-task-decomposition.md")
        dag = read(change_dir / "task-dag.yaml") + "\n" + tasks
        if "runtime-materialization-parity.md" not in context:
            errors.append(f"{change_dir / 'atomic-planning-context-pack.md'}: must consume runtime-materialization-parity.md")
        if "runtime-materialization-parity.md" not in decomposition and "runtime materialization" not in decomposition.lower():
            errors.append(f"{change_dir / 'atomic-task-decomposition.md'}: must decompose runtime materialization parity rows")
        for required in ["runtime materialization", "Runtime artifact", "Product config", "Plugins/extensions", "Secrets/security config", "Bootstrap/entrypoint", "Readback/observability"]:
            if not re.search(re.escape(required), packets, re.IGNORECASE):
                errors.append(f"{change_dir / 'atomic-issue-packets.yaml'}: must carry {required} semantics for runtime materialization owner tasks")
        if not re.search(r"runtime materialization|runtime-materialization|RMP-|物化", dag, re.IGNORECASE):
            errors.append(f"{change_dir / 'task-dag.yaml'}: must include runtime materialization provider/consumer DAG edges or owner task")
    return errors


def validate_change(change_dir: Path, stage: str = "all") -> list[str]:
    errors: list[str] = []
    tasks = read(change_dir / "tasks.md")
    plan = read(change_dir / "plan.md")
    spec = read(change_dir / "spec.md")
    proposal = read(change_dir / "proposal.md")
    ledger = read(change_dir / "source-intake-ledger.md")
    combined_all = proposal + "\n" + spec + "\n" + plan + "\n" + tasks + "\n" + ledger
    workflow_state = read_yaml(change_dir / "workflow-state.yaml")
    workflow_mode = workflow_state.get("workflow", {}) if isinstance(workflow_state.get("workflow"), dict) else {}
    if (
        workflow_state.get("schema_version", 0) < 2
        and workflow_mode.get("skill") == "automq-ai-dev-workflow-contextpack"
        and not workflow_mode.get("stage_construction_protocol")
    ):
        return [
            f"{change_dir}: legacy contextpack schema v1 is frozen; "
            "run workflowctl.py migrate-workflow-runtime <change-dir> --profile <profile> before current artifact validation"
        ]
    contextpack_mode = bool(
        workflow_mode.get("skill") == "automq-ai-dev-workflow-contextpack"
        or workflow_mode.get("context_pack_required") is True
        or workflow_mode.get("stage_construction_protocol") == "stage-construction-v1"
        or workflow_state.get("schema_version") == 2
    )
    profile = str(workflow_mode.get("profile", "full")).strip() or "full"
    execution_only_planning = (
        contextpack_mode
        and profile == "execution-only"
        and stage in {"all", "task-planning", "pre-execution"}
    )
    early_stage = stage in {"source-intake", "prd", "aip", "readiness"}
    design_or_later_stage = not execution_only_planning and stage in {
        "all",
        "design",
        "archaeology",
        "migration",
        "frontend-contract",
        "contract",
        "verification",
        "task-planning",
        "pre-execution",
    }
    planning_or_later_stage = stage in {"all", "task-planning", "pre-execution"}

    if workflow_state or (change_dir / WORKDIR_IDENTITY_ARTIFACT).exists() or proposal or spec or plan or tasks:
        errors.extend(validate_workdir_identity(change_dir, workflow_state))

    if proposal or spec or plan or tasks:
        errors.extend(validate_workflow_state_gate(change_dir, workflow_state, None if stage == "all" else stage))
        if not execution_only_planning and stage in {"all", "source-intake", "prd", "aip", "readiness", "design", "archaeology", "contract", "frontend-contract", "verification", "task-planning", "pre-execution"}:
            errors.extend(validate_source_intake(change_dir / "source-intake-ledger.md"))
        if not execution_only_planning and stage in {"all", "prd", "aip", "readiness", "design", "archaeology", "contract", "frontend-contract", "verification", "task-planning", "pre-execution"}:
            errors.extend(validate_prd_completeness(change_dir, proposal, spec, plan))
            errors.extend(validate_decision_surface_discovery(change_dir, proposal, spec, plan, tasks, stage))
        if not execution_only_planning:
            errors.extend(validate_human_decision_records(change_dir, stage, combined_all, workflow_state))
        if not execution_only_planning and stage in {"all", "aip", "readiness", "design", "archaeology", "contract", "frontend-contract", "verification", "task-planning", "pre-execution"}:
            errors.extend(validate_external_capability_research(change_dir, proposal, spec, plan, tasks, stage))
            errors.extend(validate_mechanism_design_model(change_dir, stage, proposal, spec, plan, tasks))
        if not execution_only_planning and stage in {"all", "design", "archaeology", "contract", "frontend-contract", "verification", "task-planning", "pre-execution"}:
            errors.extend(validate_semantic_consumption(change_dir, proposal, spec, plan, tasks))
        if not execution_only_planning and stage in {"all", "aip", "readiness", "design", "archaeology", "contract", "frontend-contract", "verification", "task-planning", "pre-execution"}:
            errors.extend(validate_engineering_propose(change_dir, plan))
            errors.extend(validate_aip_hard_gate(change_dir, proposal, spec, plan, tasks, workflow_state, contextpack_mode))
        if not execution_only_planning and stage in {"all", "verification", "task-planning", "pre-execution"}:
            errors.extend(validate_verification_feasibility(change_dir, plan, tasks))
        if not execution_only_planning and stage in {"all", "prd", "aip", "readiness", "design", "archaeology", "contract", "frontend-contract", "verification", "task-planning", "pre-execution"}:
            errors.extend(validate_version_alignment(change_dir, plan, tasks))
            errors.extend(validate_rubric_scorecard(change_dir, plan, tasks))
            errors.extend(validate_repo_isolation(change_dir, proposal, spec, plan, tasks))
        errors.extend(validate_multi_perspective_review(change_dir, stage))
        if not execution_only_planning and stage in {"all", "archaeology", "contract", "verification", "task-planning", "pre-execution"}:
            errors.extend(validate_stateful_behavior_matrix(change_dir, proposal, spec, plan, tasks, stage))
            errors.extend(validate_variant_impact_artifacts(change_dir, stage, proposal, spec, plan, tasks))
        if not execution_only_planning and stage in {"all", "contract", "verification", "task-planning", "pre-execution", "mock-acceptance", "product-acceptance"}:
            errors.extend(validate_progress_change_producer_chain(change_dir, stage, proposal, spec, plan, tasks))
            errors.extend(validate_external_side_effect_contract(change_dir, stage, proposal, spec, plan, tasks))
        if not execution_only_planning and stage in {"all", "design", "contract", "verification", "task-planning", "pre-execution", "mock-acceptance", "product-acceptance"}:
            errors.extend(validate_runtime_materialization_parity(change_dir, stage, proposal, spec, plan, tasks))
        if not execution_only_planning and stage in {"all", "archaeology", "verification", "task-planning", "pre-execution"}:
            errors.extend(validate_runtime_test_topology(change_dir, stage, proposal, spec, plan, tasks))

        workflowctl = Path(__file__).with_name("workflowctl.py")
        sidecar_names = [
            "workflow-state.yaml",
            "semantic-objects.yaml",
            "contracts.yaml",
            "verification.yaml",
            "task-dag.yaml",
            "backflow.yaml",
        ]
        has_any_sidecar = any((change_dir / name).exists() for name in sidecar_names)
        if stage in {"all", "pre-execution"} and (tasks or has_any_sidecar):
            try:
                result = subprocess.run(
                    [sys.executable, str(workflowctl), "validate", "pre-execution", str(change_dir)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
            except OSError as exc:
                errors.append(f"{change_dir}: failed to run workflowctl.py: {exc}")
            else:
                if result.returncode != 0:
                    output = (result.stderr or result.stdout).strip()
                    for line in output.splitlines():
                        if line.strip():
                            errors.append(f"workflowctl: {line.strip()}")

    if contextpack_mode and design_or_later_stage:
        if not re.search(r"Workflow Mode", combined_all) or not re.search(r"Context pack required\s*\|\s*yes", combined_all, re.IGNORECASE):
            errors.append(f"{change_dir}: contextpack workflow must record Workflow Mode with Context pack required=yes")
        has_design_stage = bool(re.search(r"New Feature Design|Code Archaeology|Module Boundary|DESIGN-DEC|考古|新设计|模块边界", plan))
        has_contract_stage = bool(re.search(r"Frontend Contract|Cross-Module Contract|Module Contract Graph|C-\d{3}|前端契约|跨模块契约", plan))
        has_acceptance_stage = bool(
            re.search(
                r"mock-acceptance|product-acceptance|Acceptance Context|packaged acceptance|packaged playground|repo-specific acceptance runtime|验收",
                plan + "\n" + tasks,
                re.IGNORECASE,
            )
        )
        errors.extend(
            validate_boundary_context_pack(
                change_dir,
                "design-context-pack.md",
                ("Design Context Rehydration", "设计上下文恢复"),
                REQUIRED_BOUNDARY_CONTEXT_SECTIONS,
                has_design_stage,
                "PRD/AIP -> design/archaeology",
            )
        )
        errors.extend(
            validate_boundary_context_pack(
                change_dir,
                "contract-context-pack.md",
                ("Contract Context Rehydration", "契约上下文恢复"),
                REQUIRED_BOUNDARY_CONTEXT_SECTIONS,
                has_contract_stage,
                "archaeology/design -> frontend/cross-module contract",
            )
        )
        errors.extend(
            validate_boundary_context_pack(
                change_dir,
                "acceptance-context-pack.md",
                ("Acceptance Context Rehydration", "验收上下文恢复"),
                REQUIRED_ACCEPTANCE_CONTEXT_SECTIONS,
                has_acceptance_stage,
                "implementation -> mock/product acceptance",
                fallback_files=("mock-acceptance.md", "plan.md"),
            )
        )

    if not execution_only_planning:
        errors.extend(validate_frontend_contract_artifacts(change_dir, stage))
    errors.extend(validate_contract_matrix_artifacts(change_dir, stage, plan, tasks))
    errors.extend(validate_atomic_task_decomposition(change_dir, stage, tasks))
    errors.extend(validate_compiler_failure_triage(change_dir, stage))
    errors.extend(validate_task_planning_repair_ledger(change_dir, stage))
    errors.extend(validate_atomic_issue_quality_review(change_dir, stage, tasks))
    errors.extend(validate_mock_acceptance_artifacts(change_dir, stage))
    errors.extend(validate_no_production_downgrade_language(change_dir, stage))

    if not execution_only_planning:
        artifact_names = ["proposal.md", "spec.md"] if stage in {"source-intake", "prd"} else ["proposal.md", "spec.md", "plan.md", "tasks.md"]
        for artifact in artifact_names:
            artifact_path = change_dir / artifact
            text = read(artifact_path)
            if text and mostly_non_chinese(text):
                errors.append(f"{artifact_path}: main narrative appears to be English; workflow artifacts must default to Chinese")

    if not execution_only_planning and "Decision Registry" in plan and "Decision Document Index" not in plan:
        errors.append(f"{change_dir}: Decision Registry exists but missing Decision Document Index")

    has_module_boundary = bool(re.search(r"Module Boundary|模块边界", plan))

    if design_or_later_stage and has_module_boundary:
        if not re.search(r"Data Ownership (?:Evidence|Design)|数据所有权", plan):
            errors.append(f"{change_dir}: Module Boundary exists but missing Data Ownership Evidence/Design")
        if not re.search(r"State-Machine Boundary (?:Evidence|Design)|状态机|状态变迁", plan):
            errors.append(f"{change_dir}: Module Boundary exists but missing State-Machine Boundary Evidence/Design")
        if not re.search(r"Change Independence (?:Evidence|Design)|Future Change Independence Design|变更独立", plan):
            errors.append(f"{change_dir}: Module Boundary exists but missing Change Independence Evidence/Design")

    if design_or_later_stage and has_module_boundary and not re.search(r"Module Boundary Validation|模块边界验证", plan):
        errors.append(f"{change_dir}: Module Boundary exists but missing Module Boundary Validation gate")

    boundary_validation = first_existing_section(
        plan,
        "Module Boundary Validation",
        "Module Boundary Validation Matrix",
        "模块边界验证",
    )
    if boundary_validation:
        if not (
            has_any_pattern(boundary_validation, r"\bModule\b", r"模块")
            and has_any_pattern(boundary_validation, r"evidence", r"证据")
            and has_any_pattern(boundary_validation, r"\bDecision\b", r"决策")
        ):
            errors.append(f"{change_dir}: Module Boundary Validation must include module, evidence, and decision fields")
        if not (
            has_any_pattern(boundary_validation, r"writer", r"写入方")
            and has_any_pattern(boundary_validation, r"State-machine", r"状态机")
            and has_any_pattern(boundary_validation, r"Change-independence", r"变更独立", r"future.*change")
        ):
            errors.append(
                f"{change_dir}: Module Boundary Validation must include writer ownership, state-machine, and change-independence evidence"
            )
        if not (
            has_any_pattern(boundary_validation, r"Interface count", r"接口.*数量")
            and has_any_pattern(boundary_validation, r"Interaction count", r"交互点.*数量")
            and has_any_pattern(boundary_validation, r"Too large", r"过大")
            and has_any_pattern(boundary_validation, r"Too small", r"过小")
        ):
            errors.append(
                f"{change_dir}: Module Boundary Validation must include interface count, interaction count, too-large risk, and too-small risk"
            )
        if re.search(r"needs-(?:contract|design)-review|unknown|待确认", boundary_validation, re.IGNORECASE):
            errors.append(f"{change_dir}: Module Boundary Validation contains unresolved review/unknown decisions")
        if re.search(r"\|\s*(?:keep|split|merge|保留|拆分|合并)\s*\|\s*\|", boundary_validation, re.IGNORECASE):
            errors.append(f"{change_dir}: Module Boundary Validation has boundary decisions without evidence/risk fields")

    if design_or_later_stage and re.search(r"Module Contract Graph|模块契约图", plan) and not re.search(
        r"Module Composition Verification|模块组合验证", plan + "\n" + tasks
    ):
        errors.append(f"{change_dir}: Module Contract Graph exists but missing Module Composition Verification gate")

    module_contract_graph = first_existing_section(plan, "Module Contract Graph", "模块契约图")
    if design_or_later_stage and module_contract_graph and not (
        has_any_pattern(module_contract_graph, r"\bModule\b", r"模块")
        and has_any_pattern(module_contract_graph, r"Provided contracts", r"提供.*契约", r"对外.*契约")
        and has_any_pattern(module_contract_graph, r"Consumed contracts", r"消费.*契约", r"依赖.*契约")
    ):
        errors.append(f"{change_dir}: Module Contract Graph must include Module, Provided contracts, and Consumed contracts")

    if design_or_later_stage:
        errors.extend(validate_contract_discovery(change_dir, plan))

    provider_consumer = first_existing_section(
        plan,
        "Provider/Consumer Assumption Matrix",
        "Provider / Consumer Assumptions",
        "Provider Consumer Assumption Matrix",
        "提供方消费方假设矩阵",
    )
    if design_or_later_stage and module_contract_graph and not provider_consumer:
        errors.append(f"{change_dir}: Module Contract Graph exists but missing Provider/Consumer Assumption Matrix")
    if design_or_later_stage and provider_consumer:
        if not (
            has_any_pattern(provider_consumer, r"Provider guarantee", r"提供方.*保证", r"provider")
            and has_any_pattern(provider_consumer, r"Consumer assumption", r"消费方.*假设", r"consumer")
            and has_any_pattern(provider_consumer, r"Mismatch decision", r"不匹配.*决策", r"差异.*决策")
        ):
            errors.append(
                f"{change_dir}: Provider/Consumer Assumption Matrix must include provider guarantee, consumer assumption, and mismatch decision"
            )
        if re.search(r"\|\s*(?:blocked|unknown|待确认)\s*\|", provider_consumer, re.IGNORECASE):
            errors.append(f"{change_dir}: Provider/Consumer Assumption Matrix contains blocked/unknown mismatch decisions")

    materialization = first_existing_section(
        plan,
        "Contract Materialization Source Matrix",
        "Contract Materialization Matrix",
        "契约物化来源矩阵",
    )
    if design_or_later_stage and module_contract_graph and not materialization:
        errors.append(f"{change_dir}: Module Contract Graph exists but missing Contract Materialization Source Matrix")
    if design_or_later_stage and materialization:
        if not has_table_columns(
            materialization,
            [
                "Contract",
                "Provider guarantee facts",
                "Consumer assumption facts",
                "Field/state/error/timing details",
                "Preconditions for consumer tasks",
                "Obligations for provider tasks",
                "Forbidden interpretations",
            ],
        ):
            errors.append(f"{change_dir}: Contract Materialization Source Matrix must include provider facts, consumer facts, field/state/error/timing details, preconditions, obligations, and forbidden interpretations")
        if re.search(r"\|\s*(?:blocked|unknown|待确认|TBD|TODO)\s*\|", materialization, re.IGNORECASE):
            errors.append(f"{change_dir}: Contract Materialization Source Matrix contains blocked/unknown/TODO rows")
        for row in table_rows(materialization):
            if not row or row[0].lower() == "contract":
                continue
            joined = " | ".join(row)
            if re.search(r"\bC-\d{3}\b", joined) and len(CJK_RE.findall(joined)) < 30:
                errors.append(f"{change_dir}: Contract Materialization Source Matrix row appears too thin or ID-only: {joined}")

    if design_or_later_stage and re.search(r"\bREQ-\d{3}\b|\bSCN-\d{3}\b", spec + "\n" + plan) and "Verification Matrix" in plan and not re.search(
        r"Composition path|模块组合|Module Composition", plan
    ):
        errors.append(f"{change_dir}: Verification Matrix exists but lacks module composition verification coverage")

    composition_verification = first_existing_section(
        plan + "\n" + tasks,
        "Module Composition Verification",
        "Module Composition Verification Matrix",
        "模块组合验证",
    )
    if design_or_later_stage and composition_verification:
        if not (
            has_any_pattern(composition_verification, r"Composition path", r"组合路径", r"模块链路")
            and has_any_pattern(composition_verification, r"Provider contracts", r"提供方.*契约", r"provider")
            and has_any_pattern(composition_verification, r"Consumer assumptions", r"消费方.*假设", r"consumer")
            and has_any_pattern(composition_verification, r"Expected result", r"预期")
            and has_any_pattern(composition_verification, r"Proves", r"证明")
        ):
            errors.append(
                f"{change_dir}: Module Composition Verification must include Composition path, Provider contracts, Consumer assumptions, Expected result, and Proves"
            )
        if re.search(r"^\s*\|[^|\n]*(REQ|SCN)-\d{3}[^|\n]*\|\s*\|", composition_verification, re.MULTILINE):
            errors.append(f"{change_dir}: Module Composition Verification has REQ/SCN rows without composition path")
        if re.search(r"\|\s*(?:unit|单测)\s*\|", composition_verification, re.IGNORECASE):
            errors.append(f"{change_dir}: Module Composition Verification cannot be satisfied by unit/module-local tests only")

    traceability = first_existing_section(
        plan + "\n" + tasks,
        "Traceability Matrix",
        "Coverage Matrix",
        "可追溯矩阵",
    )
    if planning_or_later_stage and module_contract_graph and not re.search(r"Module-to-Issue|Module To Issue|模块.*Issue", plan + "\n" + tasks):
        errors.append(f"{change_dir}: missing Module-to-Issue coverage before atomic execution")
    if planning_or_later_stage and module_contract_graph and not re.search(r"Contract Closure Coverage|契约闭包覆盖", plan + "\n" + tasks):
        errors.append(f"{change_dir}: missing Contract Closure Coverage before atomic execution")
    if planning_or_later_stage and re.search(r"\bREQ-\d{3}\b|\bSCN-\d{3}\b", spec + "\n" + plan) and not re.search(
        r"Requirement Composition Coverage|需求.*组合.*覆盖", plan + "\n" + tasks
    ):
        errors.append(f"{change_dir}: missing Requirement Composition Coverage before atomic execution")
    if design_or_later_stage and traceability and re.search(r"\|\s*[^|\n]*\|\s*[^|\n]*\|\s*[^|\n]*\|\s*[^|\n]*\|\s*gap\s*\|", traceability, re.IGNORECASE):
        errors.append(f"{change_dir}: Traceability/Coverage matrix still contains gap rows")

    decision_dir = change_dir / "decision-reviews"
    decision_paths = sorted(decision_dir.glob("*-decisions.md")) if decision_dir.exists() else []
    decision_ids = ids(DECISION_ID_RE.pattern, plan + "\n" + spec)
    if not execution_only_planning and decision_ids and not decision_paths:
        errors.append(f"{change_dir}: decisions exist but missing decision-reviews/*-decisions.md")

    if not execution_only_planning:
        for decision_doc in decision_paths:
            errors.extend(validate_stage_decision_doc(decision_doc))

    all_decision_text = "\n".join(read(path) for path in decision_paths)
    if not execution_only_planning and not early_stage:
        errors.extend(validate_decision_consistency(change_dir, plan, all_decision_text))
    if not execution_only_planning:
        for decision_id in sorted(decision_ids):
            if decision_id not in all_decision_text:
                errors.append(f"{change_dir}: decision {decision_id} is not referenced in any stage decision document")

    if not planning_or_later_stage:
        return errors

    issue_dir = change_dir / "atomic-issues"
    issue_paths = sorted(issue_dir.glob("T*.md")) if issue_dir.exists() else []
    if not issue_paths:
        errors.append(f"{change_dir}: missing atomic-issues/Txxx.md files")

    errors.extend(validate_atomic_planning_context_pack(change_dir, proposal, spec, plan, tasks, issue_paths))
    errors.extend(validate_atomic_issue_packets(change_dir, tasks, issue_paths))

    for issue in issue_paths:
        errors.extend(validate_atomic_issue(issue))

    task_ids = ids(r"\b(T\d{3})\b", tasks)
    issue_ids = {path.stem for path in issue_paths}
    for task_id in sorted(task_ids - issue_ids):
        errors.append(f"{change_dir}: task {task_id} has no atomic issue file")

    for issue_id in sorted(issue_ids - task_ids):
        errors.append(f"{change_dir}: atomic issue {issue_id} is not indexed in tasks.md")

    all_issue_text = "\n".join(read(path) for path in issue_paths)
    errors.extend(validate_task_dag(change_dir, tasks, plan))
    errors.extend(validate_not_run(change_dir, tasks, plan))
    errors.extend(validate_backflow(change_dir, tasks, plan, all_issue_text, all_decision_text))
    contract_ids = ids(r"\b(C-\d{3})\b", plan)
    for contract_id in sorted(contract_ids):
        if contract_id not in all_issue_text:
            errors.append(f"{change_dir}: contract {contract_id} is not referenced in any atomic issue")

    source_ids = ids(rf"\b(REQ-\d{{3}}|SCN-\d{{3}}|{DECISION_ID_PATTERN}|MIG-\d{{3}})\b", spec + "\n" + plan)
    combined = tasks + "\n" + all_issue_text
    for source_id in sorted(source_ids):
        if source_id not in combined:
            errors.append(f"{change_dir}: source {source_id} is not covered by tasks/issues")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("change_dir", type=Path, help="specs/changes/<change-id> directory")
    parser.add_argument(
        "--stage",
        choices=[
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
            "pre-execution",
            "mock-acceptance",
            "product-acceptance",
            "all",
        ],
        default="all",
        help="validate only the gates that should be satisfied by this stage",
    )
    args = parser.parse_args()

    errors = validate_change(args.change_dir, args.stage)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Artifact validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
