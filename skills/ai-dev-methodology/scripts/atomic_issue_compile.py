#!/usr/bin/env python3
"""Compile per-task Atomic Issue packets into sealed Atomic Issue Markdown.

The packet file is the per-task intermediate representation. It must already
contain executable source, decision, contract, verification, invariant, and
backflow semantics. This compiler intentionally refuses to invent missing
semantics from global docs; missing packet fields mean the workflow must
backflow to contract/task planning.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any


try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    yaml = None


PLACEHOLDER_RE = re.compile(r"^(?:|n/a|none|todo|tbd|unknown|待确认|未知|<.*>)$", re.IGNORECASE)
DECISION_ID_PATTERN = (
    r"(?:PDEC|ADEC|DEC(?:-[A-Z][A-Z0-9]*)?|READY-DEC|ARCH-DEC|"
    r"DESIGN-DEC|MIG-DEC|UI-DEC|VER-DEC|TASK-DEC)-\d{3}"
)
ID_ONLY_RE = re.compile(rf"^(?:REQ|SCN|C|MIG|VER)-\d{{3}}$|^{DECISION_ID_PATTERN}$|^T\d{{3}}$")
GLOBAL_DOC_RE = re.compile(r"\b(?:见|see|according to|refer to)\s*(?:plan|spec|proposal|Decision Registry|C-\d{3}|REQ-\d{3})", re.IGNORECASE)
TASK_RE = re.compile(r"^T\d{3}$")
SURFACE_ID_RE = re.compile(r"^DS-\d{3}$")
GENERIC_CARRIER_RE = re.compile(
    r"^(?:use selectors|provider selectors|mode[- ]specific|same api paths|follow existing pattern|参考.*|按.*实现|保持一致)$",
    re.IGNORECASE,
)
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
LABEL_ONLY_CARRIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)+$")

DENSE_PACKET_RULES: list[dict[str, Any]] = [
    {
        "name": "asg-infra-selector",
        "source_patterns": [
            r"\bASG\b.*(?:infrastructure|infra|VPC|Subnet|Security\s*Group|SecurityGroup|\bSG\b|IAM|Instance\s*Type|InstanceType|selector|auto[- ]?create|raw\s*(?:text|AWS|ID)|text\s*box)",
            r"(?:infrastructure|infra|VPC|Subnet|Security\s*Group|SecurityGroup|\bSG\b|IAM|Instance\s*Type|InstanceType|selector|auto[- ]?create|raw\s*(?:text|AWS|ID)|text\s*box).*\bASG\b",
        ],
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
        "name": "explicit-failure-vs-unknown",
        "source_patterns": [
            r"explicit.*unknown",
            r"unknown.*explicit",
            r"unreachable.*unknown",
            r"unknown.*unreachable",
            r"明确.*未知",
            r"不可达.*未知",
        ],
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
        "name": "managed-resource-ownership",
        "source_patterns": [
            r"(?:auto[- ]?create|default[- ]?created|generated\s+resource|managed\s+resource|select[- ]?existing|existing\s+resource).{0,160}(?:provider[_ -]?writer|create[_ -]?timing|provenance|ownership|state owner|persist|readback|cleanup|protect|detach|idempot|writer|operator|owned\s+resource|existing\s+resource)",
            r"(?:provider[_ -]?writer|create[_ -]?timing|provenance|ownership|state owner|persist|readback|cleanup|protect|detach|idempot|writer|operator|owned\s+resource|existing\s+resource).{0,160}(?:auto[- ]?create|default[- ]?created|generated\s+resource|managed\s+resource|select[- ]?existing|existing\s+resource)",
            r"(?:自动创建|默认创建|生成资源|托管资源|选择已有|已有资源|现有资源).{0,100}(?:写入|创建时机|归属|所有权|状态所有者|持久|读回|清理|保护|解绑|幂等)",
        ],
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
        "name": "stateful-behavior",
        "source_patterns": [
            r"\b(lifecycle|progress|event|events|terminal|polling|retry|state\s*graph|state\s*machine|task\s*step|change\s*tracking|step\s*graph)\b",
            r"生命周期|进度|事件|状态机|状态图|终态|轮询|重试|任务步骤|变更追踪|状态推进",
        ],
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

FRONTEND_TASK_RE = re.compile(
    r"\b(frontend|ui|browser|dom|page|component|form|wizard)\b"
    r"|前端|页面|表单|组件|浏览器",
    re.IGNORECASE,
)
FRONTEND_FILE_RE = re.compile(
    r"(^|/)(?:frontend|web|ui|src/)?(?:pages?|components?|routes|app)/|\.tsx?$|\.jsx?$",
    re.IGNORECASE,
)
FRONTEND_MUTATION_RE = re.compile(
    r"\b(create|submit|update|resize|delete|scale|save|bind|import|export|confirm|wizard|form)\b"
    r"|创建|提交|更新|扩缩|删除|保存|确认|表单",
    re.IGNORECASE,
)
FRONTEND_REFERENCE_SIGNAL_RE = re.compile(
    r"\b(?:(?:reference|refer(?:red)? to) (?:UI|page|component|pattern|experience|implementation)|follow(?:ing)? existing|existing pattern|same (?:experience|layout|ui)|"
    r"like .*?(?:page|component|wizard|form|selector|table|card|experience)|visual parity|layout parity|component parity)\b"
    r"|参考|参照|借鉴|对齐.*(?:体验|页面|组件|布局)|一致.*(?:体验|页面|组件|布局)|像.*(?:页面|组件|体验)|创建体验",
    re.IGNORECASE,
)
WEAK_FRONTEND_VERIFICATION_RE = re.compile(r"\b(build|lint|typecheck|tsc|payload|compile)\b", re.IGNORECASE)
STRONG_FRONTEND_VERIFICATION_RE = re.compile(
    r"\b(browser|playwright|DOM|click|submit|network|route|API|screenshot|trace|HAR)\b"
    r"|浏览器|点击|提交|网络|截图|路由|接口",
    re.IGNORECASE,
)
ABSENCE_ASSERTION_RE = re.compile(
    r"\b(absent|hide|hidden|not\s+(?:show|render|submit|route)|no\s+|without|forbid|forbidden|exclude|"
    r"禁止|隐藏|不得|不显示|不渲染|不提交|不存在|排除)\b",
    re.IGNORECASE,
)
FRONTEND_COMPONENT_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./:-])((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:tsx|jsx|ts|js))\b",
    re.IGNORECASE,
)
REFERENCE_UI_PATTERN_PATH_RE = FRONTEND_COMPONENT_PATH_RE
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
NON_APPLICABLE_PROOF_RE = re.compile(
    r"\b(?:N/A|not\s+applicable|not\s+required|not\s+a\s+frontend|no\s+frontend|no\s+browser|"
    r"does\s+not\s+claim|proof\s+only\s+in\s+frontend|out\s+of\s+scope)\b"
    r"|不适用|不需要|非前端|无前端|无浏览器|不声明|不证明|不属于本任务",
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
ACCEPTANCE_TASK_RE = re.compile(
    r"\b(?:MOD-ACCEPTANCE|acceptance|mock matrix|mock acceptance|packaged|no-cloud|playground|proof-only|proof only)\b"
    r"|验收|无云|证明任务|证明边界",
    re.IGNORECASE,
)
PRODUCTION_MAIN_FILE_RE = re.compile(
    r"^(?:backend|server|service|api|common|repository|runtime|[^/]+)/(?:src/main/(?:java|kotlin|scala)|src/main)/",
    re.IGNORECASE,
)
BACKEND_LAYER_PATTERNS = {
    "backend-api": re.compile(r"Controller|OpenAPI|/controller/|/model/(?:param|vo)/|Param\.java|VO\.java|DTO\.java", re.IGNORECASE),
    "backend-data": re.compile(r"Repository|Mapper|/repository/|/dataobject/|DO\.java|migration|\.sql\b", re.IGNORECASE),
    "backend-domain": re.compile(r"/service/|Service|/manager/|Manager|/model/entity/|Entity|Domain", re.IGNORECASE),
    "backend-runtime": re.compile(r"/task/|Task|Payload|Executor|Factory|Step|cluster-manager|runtime|Lifecycle", re.IGNORECASE),
    "backend-test": re.compile(r"/src/test/|Test\.java|IT\.java", re.IGNORECASE),
}
AUDIT_ONLY_SECTIONS = {
    "sources",
    "decision_surfaces",
    "external_capability_facts",
    "semantic_carriers",
    "decisions",
    "contract_excerpts",
    "execution_preconditions",
    "consumed_contract_snapshots",
    "provided_contract_obligations",
    "invariant_carryover",
    "preconditions_failure_handling",
    "existing_code_references",
    "owned_state_data_resources",
    "internal_invariants",
}
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
    "mock-playground",
    "observability",
    "permission",
    "compatibility",
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
    "managed_resource_ownership",
    "stateful_behavior",
    "frontend_user_task",
    "action_route_component",
    "reference_ui_patterns",
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
    "sources",
    "source_context",
    "decision_surfaces",
    "semantic_carriers",
    "decisions",
    "contract_excerpts",
    "existing_code_references",
    "traceability_appendix",
    "appendix",
    "plan",
    "spec",
    "proposal",
    "context_pack",
}
EXTERNAL_FACT_ID_RE = re.compile(r"^(?:FACT|EXT|CONSTRAINT|XCON|MECH|EXTMECH)-\d{3}$")
EXTERNAL_FACT_ID_LABEL = "FACT/EXT/CONSTRAINT/XCON/MECH/EXTMECH-xxx"
EXTERNAL_CAPABILITY_EXECUTION_FIELDS = DECISION_SURFACE_EXECUTION_FIELDS
EXTERNAL_CAPABILITY_APPENDIX_ONLY_FIELDS = DECISION_SURFACE_APPENDIX_ONLY_FIELDS | {
    "external_capability_facts",
    "external-capability-research",
    "research",
    "aip",
}
OPEN_DECISION_SURFACE_RE = re.compile(
    r"\b(?:needs-decision|open|unknown|todo|tbd|blocked|待确认|未知|未决|阻塞)\b",
    re.IGNORECASE,
)
MAX_EXECUTION_STEPS = 8
MAX_ACTION_ROWS_PER_FRONTEND_TASK = 2
MAX_FIELD_ROWS_PER_FRONTEND_TASK = 6
MAX_FORM_ROWS_PER_FRONTEND_TASK = 4
MAX_STATEFUL_ROWS_PER_TASK = 5
MAX_CARRIER_ROWS_PER_TASK = 18
MAX_CARRIER_PRESERVE_ITEMS_PER_ROW = 3
MAX_SOURCE_ROWS_PER_TASK = 8
MAX_CONTRACT_ROWS_PER_TASK = 6
MAX_PACKET_EXECUTION_WORDS = 2600
MECHANICAL_REWRITE_RE = re.compile(
    r"\b(?:downstream\s+UI|text\s+boxeses|evidence\s+evidence|consumer\s+is\s+downstream\s+downstream|"
    r"SECURITY_access\s+role_CHECK|record-state|shown selector proof|script showed selector proof)\b",
    re.IGNORECASE,
)
GAMING_HINT_RE = re.compile(
    r"\b(?:materialized task-planning carrier|missing .* breaks task planning validation|"
    r"遗漏 .* 会让本任务无法满足|validator|regex|exact proof|exact-copy|为了.*通过|gate keyword)\b",
    re.IGNORECASE,
)
ALLOWLIST_CEILING_RE = re.compile(
    r"allowlist ceiling|validator feasibility|not an implementation instruction|support only|"
    r"仅.*allowlist|仅.*validator|不是.*实现.*指令|不作为.*实现|校验.*范围|门禁.*范围",
    re.IGNORECASE,
)
BROAD_TASK_TITLE_RE = re.compile(
    r"\b(?:post[-_ ]?create consumers?|frontend\s+UX|complete\s+UI|all\s+actions?|fixture\s+graph|acceptance\s+environment|"
    r"packaged\s+acceptance|representative\s+acceptance|backend\s+fixture\s+graph)\b"
    r"|创建后.*消费者|前端体验|完整.*前端|所有.*操作|夹具图|验收环境|代表性验收",
    re.IGNORECASE,
)
ACTION_WORD_RE = re.compile(
    r"\b(create|submit|detail|inspect|update[-_ ]?config|update[-_ ]?worker|worker[_-]?spec|resize|progress|event|delete|logs?|metrics?|workers?|connectors?)\b"
    r"|创建|提交|详情|查看|更新配置|修改配置|规格|扩缩|进度|事件|删除|日志|指标|Worker|Connector",
    re.IGNORECASE,
)
PLANNED_AS_PROOF_RE = re.compile(
    r"\b(?:score\s+2\s+planned|planned:\s+covered|planned browser action|planned row|rows do not execute tests yet|future Playwright|future execution ledger)\b"
    r"|计划.*覆盖|计划.*浏览器|未来.*执行|尚不执行",
    re.IGNORECASE,
)
ACTION_ID_RE = re.compile(r"^(?:UI-ACT|FA|MFA|MAC|MB|MES)-[A-Za-z0-9_-]+$")
STRONG_MERGE_RATIONALE_RE = re.compile(
    r"\b(?:same\s+(?:form|submit|transaction|request|endpoint|route|component|source component|landing component|"
    r"verification command|test method|writer|state owner)|shared\s+(?:writer|state owner|route|landing component|fixture|"
    r"browser proof|test assertion)|cannot\s+split|would\s+break\s+(?:compile|contract|transaction|schema|route)|"
    r"single\s+(?:commit|mutation|round[- ]?trip|state transition))\b"
    r"|同一(?:表单|提交|事务|请求|接口|路由|组件|源组件|落点组件|验证命令|测试方法|写入路径|状态所有者|状态迁移)"
    r"|共享(?:写入|状态所有者|路由|落点|fixture|浏览器证明|测试断言)"
    r"|无法拆分|拆分会(?:破坏|导致|造成)|单一(?:提交|mutation|状态迁移|往返)",
    re.IGNORECASE,
)
WEAK_MERGE_RATIONALE_RE = re.compile(
    r"\b(?:same\s+(?:module|page|area)|related|all related|convenient|small enough|reduce task count|one frontend task|"
    r"validator|gate|rubric|for coverage|to pass)\b"
    r"|同一(?:模块|页面|区域)|相关|方便|顺手|任务数|一个前端任务|过(?:校验|门禁)|为了覆盖|为了通过",
    re.IGNORECASE,
)
NON_APPLICABLE_ATOMICITY_RE = re.compile(
    r"\b(?:not\s+applicable|not\s+owned|none\s+owned|no\s+user\s+action|no\s+stateful|no\s+stateful\s+operation|"
    r"does\s+not\s+own|not\s+part\s+of\s+this\s+packet|pure\s+backend|pure\s+verification)\b"
    r"|不适用|不拥有|不涉及|无用户动作|无状态机|无状态操作|纯后端|纯验证|不属于本任务",
    re.IGNORECASE,
)
ALLOWLIST_FEASIBILITY_RULES: list[dict[str, Any]] = [
    {
        "name": "backend-api-surface",
        "scope": "backend",
        "semantic_patterns": [
            r"\b(?:API|接口|controller|DTO|VO|Param|request|response|返回|入参|出参|OpenAPI)\b",
        ],
        "file_patterns": [
            r"/controller/|Controller\.java$|/model/(?:param|vo)/|Param\.java$|VO\.java$|DTO\.java$|openapi|api",
        ],
        "explain": "API/request/response/VO/DTO semantics require API surface files in files_to_change",
    },
    {
        "name": "backend-persistence",
        "scope": "backend",
        "semantic_patterns": [
            r"\b(?:persist|persistence|database|DB|SQL|repository|mapper|DO|dataobject|migration|持久化|数据库|表结构|兼容旧行|老数据)\b",
            r"\b(?:DB|database|repository|mapper|DO|dataobject|migration|SQL)\s+schema\b|\bschema\s+(?:migration|compatib|change)\b",
        ],
        "file_patterns": [
            r"/repository/|Repository\.java$|Mapper\.java$|/dataobject/|DO\.java$|migration|\.sql$|schema",
        ],
        "explain": "persistence/compatibility semantics require DO/repository/mapper/migration files in files_to_change",
    },
    {
        "name": "backend-domain-service",
        "scope": "backend",
        "semantic_patterns": [
            r"\b(?:service|manager|domain|entity|business validation|业务校验|领域|实体|状态持久|决策持久)\b",
        ],
        "file_patterns": [
            r"/service/|Service\.java$|/manager/|Manager\.java$|/model/entity/|Entity\.java$",
        ],
        "explain": "domain/service/entity semantics require service/manager/entity files in files_to_change",
    },
    {
        "name": "backend-runtime-lifecycle",
        "scope": "backend",
        "semantic_patterns": [
            r"\b(?:executor|factory|lifecycle|progress|event|events|terminal|polling|retry|state\s*graph|state\s*machine|task\s*step|step\s*graph|运行时执行器|生命周期|进度|事件|状态机|终态|轮询|重试|任务步骤)\b",
            r"\bruntime\b.{0,80}\b(?:executor|factory|lifecycle|progress|event|terminal|polling|retry|state|task)\b",
            r"\b(?:executor|factory|lifecycle|progress|event|terminal|polling|retry|state|task)\b.{0,80}\bruntime\b",
            r"\bpayload\b.{0,80}\b(?:executor|factory|lifecycle|event|progress)\b",
            r"\b(?:executor|factory|lifecycle|event|progress)\b.{0,80}\bpayload\b",
        ],
        "file_patterns": [
            r"/task/|Task|Payload|Executor|Factory|Step|cluster-manager|runtime|Lifecycle",
        ],
        "explain": "runtime/task/lifecycle semantics require task/payload/executor/factory files in files_to_change",
    },
    {
        "name": "frontend-action-source-handler-landing",
        "scope": "frontend",
        "semantic_patterns": [
            r"\b(?:action|click|submit|route|router|handler|landing|dropdown|tab|wizard|操作|点击|提交|路由|下拉|详情|配置|容量|进度)\b",
        ],
        "file_patterns": [
            r"\.tsx?$|\.jsx?$|/pages?/|/components?/|/routes/|/app/",
        ],
        "explain": "frontend action-flow semantics require concrete source/handler/router/landing files in files_to_change",
    },
]


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise ValueError("PyYAML is required for atomic issue compilation")
    if not path.exists():
        raise ValueError(f"{path}: missing atomic issue packet file")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def is_meaningful(value: Any, min_chars: int = 8) -> bool:
    value_text = text(value)
    if PLACEHOLDER_RE.match(value_text):
        return False
    if ID_ONLY_RE.match(value_text):
        return False
    if GLOBAL_DOC_RE.search(value_text):
        return False
    return len(value_text) >= min_chars


def is_reference(value: Any, min_chars: int = 4) -> bool:
    value_text = text(value)
    if PLACEHOLDER_RE.match(value_text):
        return False
    if GLOBAL_DOC_RE.search(value_text):
        return False
    return len(value_text) >= min_chars


def meaningful_items(value: Any, min_chars: int = 4) -> list[str]:
    items = [text(item) for item in as_list(value)]
    return [item for item in items if is_meaningful(item, min_chars=min_chars)]


def flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    return text(value)


def matches_any(value: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, value, re.IGNORECASE) for pattern in patterns)


NEGATIVE_BOUNDARY_RE = re.compile(
    r"\b(?:do not|don't|must not|not owned|does not own|out of scope|N/A|not applicable|"
    r"proof (?:lives|belongs) in|owned by T\d{3}|handled by T\d{3}|no browser|no frontend)\b"
    r"|\bno\s+(?:runtime|lifecycle|stateful|persistence|persistent|managed\s+resource|resource\s+ownership)\b"
    r"|(?:不|不要|不得|不拥有|不负责|不属于|不适用|证明在|归 T\d{3}|由 T\d{3})",
    re.IGNORECASE,
)


def positive_text(value: Any) -> str:
    raw = flatten_text(value)
    segments = re.split(r"(?<=[.;。；])\s+|[;；。]\s*", raw)
    kept = [segment for segment in segments if segment and not NEGATIVE_BOUNDARY_RE.search(segment)]
    return " ".join(kept)


def carrier_semantic_type_signal(packet: dict[str, Any], patterns: list[str]) -> bool:
    primary_module = packet_primary_module(packet)
    for row in [as_dict(item) for item in as_list(packet.get("semantic_carriers"))]:
        owner_module = text(row.get("owner_module"))
        if owner_module and primary_module and not modules_compatible(owner_module, primary_module):
            continue
        semantic_type_text = flatten_text([row.get("semantic_type"), row.get("carrier"), row.get("copied_to")])
        if matches_any(semantic_type_text, patterns):
            return True
    return False


def surface_type_signal(packet: dict[str, Any], surface_type: str) -> bool:
    return any(as_dict(row).get("surface_type") == surface_type for row in as_list(packet.get("decision_surfaces")))


def yaml_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    value_text = text(value).lower()
    if value_text in {"true", "yes", "y", "1", "required"}:
        return True
    if value_text in {"false", "no", "n", "0", "not required", "n/a", "na", "none"}:
        return False
    return None


def browser_verification_claim_text(packet: dict[str, Any]) -> str:
    """Return only positive browser proof claims, ignoring explicit N/A sections."""
    browser = as_dict(packet.get("browser_verification"))
    if not browser:
        return ""
    required = yaml_bool(browser.get("required"))
    browser_text = flatten_text(browser)
    if required is False:
        return ""
    if required is None and NON_APPLICABLE_PROOF_RE.search(browser_text):
        positive_fields = flatten_text(
            [
                browser.get("steps"),
                browser.get("network_assertions"),
                browser.get("dom_assertions"),
                browser.get("screenshot_or_trace"),
                browser.get("negative_assertions"),
            ]
        )
        if not positive_fields or NON_APPLICABLE_PROOF_RE.search(positive_fields):
            return ""
    return browser_text


def missing_groups(value: str, groups: list[tuple[str, list[str]]]) -> list[str]:
    return [label for label, patterns in groups if not matches_any(value, patterns)]


def is_label_only(value: str) -> bool:
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


def dense_carrier_payload(rows: list[dict[str, Any]]) -> str:
    parts: list[Any] = []
    for row in rows:
        parts.append(row.get("carrier"))
        parts.append(row.get("must_preserve"))
        parts.append(row.get("omission_failure"))
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
    for term in raw_terms:
        lower = term.lower()
        if lower in stop:
            continue
        if lower not in {existing.lower() for existing in terms}:
            terms.append(term)
    return terms


def semantic_item_copied(item: str, packet_payload_text: str) -> bool:
    if item in packet_payload_text:
        return True
    terms = salient_terms(item)
    if not terms:
        return False
    hits = sum(1 for term in terms if re.search(re.escape(term), packet_payload_text, re.IGNORECASE))
    required = min(len(terms), max(4, int(len(terms) * 0.65)))
    return hits >= required


def component_paths(value: Any) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for match in FRONTEND_COMPONENT_PATH_RE.finditer(flatten_text(value)):
        path = match.group(1).strip().strip("`").strip(",.;")
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def packet_declared_file_paths(packet: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for row in as_list(packet.get("files_to_change")):
        row_dict = as_dict(row)
        path = text(row_dict.get("path") if row_dict else row)
        if path:
            paths.append(path)
    return paths


def path_in_declared_files(path: str, declared_files: list[str]) -> bool:
    normalized = path.strip().strip("/")
    for raw in declared_files:
        pattern = text(raw).strip("/")
        if not pattern:
            continue
        if pattern.endswith("/**") and normalized.startswith(pattern[:-3].rstrip("/") + "/"):
            return True
        if pattern.endswith("/") and normalized.startswith(pattern):
            return True
        if normalized == pattern or normalized.startswith(pattern.rstrip("/") + "/"):
            return True
    return False


def declared_files_text(packet: dict[str, Any]) -> str:
    return flatten_text(packet_declared_file_paths(packet))


def declared_files_match(packet: dict[str, Any], patterns: list[str]) -> bool:
    for path in packet_declared_file_paths(packet):
        if matches_any(path, patterns):
            return True
    return False


def packet_execution_text(packet: dict[str, Any]) -> str:
    return flatten_text([
        packet.get("title"),
        packet.get("goal"),
        packet.get("module_responsibility"),
        packet.get("scope"),
        packet.get("semantic_carriers"),
        packet.get("provided_contract_obligations"),
        packet.get("invariant_carryover"),
        packet.get("implementation_steps"),
        packet.get("behavior_details"),
        packet.get("backend_behavior_verification"),
        packet.get("frontend_user_task"),
        packet.get("action_route_component"),
        packet.get("mode_field_display_matrix"),
        packet.get("form_state_matrix"),
        packet.get("mode_negative_assertions"),
        packet.get("browser_verification"),
        packet.get("verification"),
        packet.get("done_criteria"),
    ])


def packet_instruction_text(packet: dict[str, Any]) -> str:
    return flatten_text([
        packet.get("title"),
        packet.get("goal"),
        packet.get("module_responsibility"),
        packet.get("scope"),
        packet.get("behavior_details"),
        packet.get("backend_layer_boundary"),
        packet.get("backend_behavior_verification"),
        packet.get("stateful_behavior"),
        packet.get("frontend_user_task"),
        packet.get("action_route_component"),
        packet.get("mode_field_display_matrix"),
        packet.get("form_state_matrix"),
        packet.get("mode_negative_assertions"),
        packet.get("fixture_needs"),
        packet.get("browser_verification"),
        packet.get("implementation_steps"),
        packet.get("verification"),
        packet.get("prohibited_changes"),
        packet.get("done_criteria"),
    ])


def packet_audit_text(packet: dict[str, Any]) -> str:
    return flatten_text({key: packet.get(key) for key in AUDIT_ONLY_SECTIONS})


def validate_allowlist_feasibility(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not packet_declared_file_paths(packet):
        return errors
    for row in [as_dict(item) for item in as_list(packet.get("files_to_change"))]:
        if ALLOWLIST_CEILING_RE.search(flatten_text(row)):
            errors.append(
                f"{task_id}: files_to_change contains allowlist-ceiling/validator-feasibility wording; "
                "files_to_change is the worker's real write scope, not a validator workaround"
            )
    semantics = positive_text(packet_instruction_text(packet))
    for rule in ALLOWLIST_FEASIBILITY_RULES:
        scope = text(rule.get("scope"))
        if scope == "backend" and not is_backend_packet(packet):
            continue
        if scope == "frontend" and not is_frontend_packet(packet):
            continue
        matcher = rule.get("semantic_matcher")
        if callable(matcher):
            rule_matches = bool(matcher(packet, semantics))
        else:
            rule_matches = matches_any(semantics, list(rule.get("semantic_patterns", [])))
        if not rule_matches:
            continue
        if not declared_files_match(packet, list(rule.get("file_patterns", []))):
            errors.append(
                f"{task_id}: allowlist feasibility gap ({rule['name']}): {rule['explain']}; "
                "do not rely on workaround storage, private adapters, or execution-time file expansion"
            )
    if is_backend_packet(packet):
        behavior_rows = [as_dict(row) for row in as_list(packet.get("backend_behavior_verification"))]
        declared = packet_declared_file_paths(packet)
        for row in behavior_rows:
            code_paths = component_paths(row.get("code_path"))
            for path in code_paths:
                if not path_in_declared_files(path, declared):
                    errors.append(
                        f"{task_id}: backend_behavior_verification {row.get('behavior_id') or '<missing>'} "
                        f"references {path} but files_to_change does not include it"
                    )
    return errors


def validate_row(
    errors: list[str],
    task_id: str,
    section: str,
    row: dict[str, Any],
    fields: list[str],
    min_chars: int = 8,
    reference_fields: set[str] | None = None,
) -> None:
    reference_fields = reference_fields or {"id", "contract", "source", "verification", "upstream"}
    for field in fields:
        checker = is_reference if field in reference_fields else is_meaningful
        if not checker(row.get(field), min_chars=min_chars if field not in reference_fields else 4):
            errors.append(f"{task_id}: {section}.{field} is missing, placeholder, ID-only, or references global docs")
        elif field not in reference_fields and is_generic_packet_text(row.get(field)):
            errors.append(
                f"{task_id}: {section}.{field} is generic placeholder text; copy the concrete field/state/error/resource/action semantics"
            )


def is_frontend_packet(packet: dict[str, Any]) -> bool:
    module_text = flatten_text([packet.get("title"), packet.get("primary_module")])
    file_text = flatten_text(packet.get("files_to_change"))
    return bool(FRONTEND_FILE_RE.search(file_text) or FRONTEND_TASK_RE.search(module_text))


def is_acceptance_packet(packet: dict[str, Any]) -> bool:
    module_text = flatten_text([packet.get("title"), packet.get("primary_module"), packet.get("module_responsibility")])
    file_text = flatten_text(packet.get("files_to_change"))
    return bool(ACCEPTANCE_TASK_RE.search(module_text) or re.search(r"/(?:playground|acceptance|mock|cmp-playground)/", file_text, re.IGNORECASE))


def is_backend_packet(packet: dict[str, Any]) -> bool:
    if is_frontend_packet(packet) or is_acceptance_packet(packet):
        return False
    module_text = flatten_text([packet.get("title"), packet.get("primary_module"), packet.get("module_responsibility")])
    file_text = flatten_text(packet.get("files_to_change"))
    return bool(BACKEND_FILE_RE.search(file_text) or re.search(r"\bbackend|后端|service|manager|controller|runtime|provider\b", module_text, re.IGNORECASE))


def normalized_module_tokens(value: Any) -> set[str]:
    raw = text(value).upper()
    if not raw:
        return set()
    tokens = re.findall(r"[A-Z0-9]+", raw)
    return {token for token in tokens if token and token not in {"MOD", "MODULE", "OWNER", "PRIMARY", "TASK"}}


def modules_compatible(expected: Any, actual: Any) -> bool:
    expected_tokens = normalized_module_tokens(expected)
    actual_tokens = normalized_module_tokens(actual)
    if not expected_tokens or not actual_tokens:
        return False
    if expected_tokens <= actual_tokens or actual_tokens <= expected_tokens:
        return True
    expected_text = text(expected).upper()
    actual_text = text(actual).upper()
    return bool(expected_tokens & actual_tokens) and (expected_text in actual_text or actual_text in expected_text)


def packet_primary_module(packet: dict[str, Any]) -> str:
    return text(packet.get("primary_module"))


def backend_layers(packet: dict[str, Any]) -> set[str]:
    layers: set[str] = set()
    for path in packet_declared_file_paths(packet):
        for layer, pattern in BACKEND_LAYER_PATTERNS.items():
            if pattern.search(path):
                layers.add(layer)
    layers.discard("backend-test")
    return layers


def compile_only_text(value: Any) -> bool:
    value_text = flatten_text(value)
    if not value_text:
        return False
    return bool(BACKEND_COMPILE_ONLY_RE.search(value_text) and not BACKEND_TEST_PROOF_RE.search(value_text))


def validate_backend_packet(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not is_backend_packet(packet):
        return errors

    verification_text = flatten_text(packet.get("verification"))
    browser_text = flatten_text([
        browser_verification_claim_text(packet),
        packet.get("action_route_component"),
        packet.get("mode_field_display_matrix"),
    ])
    if BACKEND_BROWSER_PROOF_RE.search(verification_text + " " + browser_text):
        errors.append(
            f"{task_id}: backend packet must not claim browser/DOM/render proof; "
            "move UI proof to a frontend issue and keep backend verification on API/service/runtime behavior"
        )

    behavior_signal = BACKEND_BEHAVIOR_SIGNAL_RE.search(flatten_text([
        packet.get("title"),
        packet.get("scope"),
        packet.get("sources"),
        packet.get("semantic_carriers"),
        packet.get("behavior_details"),
        packet.get("files_to_change"),
    ]))
    verification_rows = [as_dict(row) for row in as_list(packet.get("verification"))]
    if behavior_signal:
        strong_rows = [
            row for row in verification_rows
            if BACKEND_TEST_PROOF_RE.search(flatten_text(row))
            and not compile_only_text(row.get("command"))
        ]
        if not strong_rows:
            errors.append(
                f"{task_id}: backend behavior-changing packet needs behavior test proof "
                "(unit/integration/API/runtime assertions); compile/build alone cannot close the task"
            )
        if verification_rows and all(compile_only_text(row.get("command")) for row in verification_rows):
            errors.append(f"{task_id}: backend verification is compile-only; add targeted behavior assertions")

    rows = [as_dict(row) for row in as_list(packet.get("backend_behavior_verification"))]
    if behavior_signal and not rows:
        errors.append(
            f"{task_id}: backend_behavior_verification rows are required for backend behavior packets; "
            "map each contract/edge/state/error to a concrete assertion"
        )
    backend_fields = [
        "behavior_id",
        "source",
        "entrypoint",
        "code_path",
        "input_or_fixture",
        "expected_state_or_output",
        "failure_or_edge",
        "command",
        "assertion",
        "proves",
    ]
    for row in rows:
        validate_row(errors, task_id, "backend_behavior_verification", row, backend_fields, reference_fields={"source", "behavior_id"})
        if compile_only_text(row.get("command")):
            errors.append(f"{task_id}: backend_behavior_verification {row.get('behavior_id') or '<missing>'} command is compile-only")
        if not BACKEND_TEST_PROOF_RE.search(flatten_text([row.get("command"), row.get("assertion"), row.get("proves")])):
            errors.append(f"{task_id}: backend_behavior_verification {row.get('behavior_id') or '<missing>'} lacks test/assertion proof")

    layers = backend_layers(packet)
    if len(layers) >= 3:
        boundary = as_dict(packet.get("backend_layer_boundary"))
        for field in ["primary_layer", "touched_layers", "split_decision", "why_not_split", "forbidden_cross_layer_decisions", "verification_boundary"]:
            if not is_meaningful(boundary.get(field), min_chars=8):
                errors.append(
                    f"{task_id}: touches multiple backend layers {', '.join(sorted(layers))}; "
                    f"backend_layer_boundary.{field} is required to prove this is an intentional atomic exception"
                )
    return errors


def validate_frontend_packet(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not is_frontend_packet(packet):
        return errors

    user_task = as_dict(packet.get("frontend_user_task"))
    user_task_fields = [
        "user_task_id",
        "user_goal",
        "entry_points",
        "page_routes",
        "visible_controls",
        "required_data",
        "primary_action",
        "loading_empty_error_states",
        "success_next_state",
        "failure_feedback",
    ]
    for field in user_task_fields:
        if not is_meaningful(user_task.get(field), min_chars=8):
            errors.append(f"{task_id}: frontend_user_task.{field} is required for frontend packets")

    action_rows = [as_dict(row) for row in as_list(packet.get("action_route_component"))]
    declared_files = packet_declared_file_paths(packet)
    if not action_rows:
        errors.append(f"{task_id}: action_route_component requires at least one row for frontend packets")
    action_fields = [
        "action_id",
        "visible_action",
        "source_component",
        "permission_visibility_guard",
        "handler",
        "route_or_api",
        "router_definition",
        "landing_component",
        "mode_branch_required",
        "forbidden_inherited_ui_api",
        "success_feedback",
        "failure_feedback",
        "verification",
    ]
    for row in action_rows:
        validate_row(errors, task_id, "action_route_component", row, action_fields, reference_fields=set())
        action_id = text(row.get("action_id"))
        source_paths = component_paths(row.get("source_component"))
        landing_paths = component_paths(row.get("landing_component"))
        router_paths = component_paths(row.get("router_definition"))
        handler_paths = component_paths(row.get("handler"))
        if not source_paths or not landing_paths:
            errors.append(f"{task_id}: action_route_component {action_id or '<missing>'} must name concrete source and landing component files")
        router_text = flatten_text(row.get("router_definition"))
        if not router_paths and not re.search(
            r"file[- ]?based router|landing component owns route|Next pages router|Next app router|文件路由",
            router_text,
            re.IGNORECASE,
        ):
            errors.append(
                f"{task_id}: action_route_component {action_id or '<missing>'} router_definition must name a concrete router file "
                "or explicitly state file-based routing through the landing component"
            )
        for path in source_paths + landing_paths + router_paths + handler_paths:
            if not path_in_declared_files(path, declared_files):
                errors.append(
                    f"{task_id}: action_route_component {action_id or '<missing>'} references {path} "
                    "but files_to_change does not include it"
                )
        if not ABSENCE_ASSERTION_RE.search(flatten_text(row.get("forbidden_inherited_ui_api"))):
            errors.append(f"{task_id}: action_route_component.forbidden_inherited_ui_api must explicitly forbid old-mode route/page/API leakage")

    packet_reference_signal = FRONTEND_REFERENCE_SIGNAL_RE.search(
        flatten_text(
            [
                packet.get("title"),
                packet.get("scope"),
                packet.get("sources"),
                packet.get("decisions"),
                packet.get("semantic_carriers"),
                packet.get("existing_code_references"),
                user_task,
                action_rows,
                packet.get("behavior_details"),
                packet.get("implementation_steps"),
                packet.get("verification"),
            ]
        )
    )
    reference_rows = [as_dict(row) for row in as_list(packet.get("reference_ui_patterns"))]
    if packet_reference_signal and not reference_rows:
        errors.append(
            f"{task_id}: frontend reference UI signal found, but reference_ui_patterns is missing. "
            "Do not collapse '参考 existing UI' into selector/field semantics; copy concrete reference pattern obligations into the packet."
        )
    reference_fields = [
        "reference_id",
        "target_surface_or_action",
        "reference_source",
        "reference_file_or_component",
        "must_reuse_or_adapt",
        "must_not_inherit",
        "visual_layout_obligation",
        "interaction_state_obligation",
        "browser_visual_proof",
        "verification",
    ]
    declared_files = packet_declared_file_paths(packet)
    for row in reference_rows:
        validate_row(errors, task_id, "reference_ui_patterns", row, reference_fields, reference_fields=set())
        ref_id = text(row.get("reference_id")) or "<missing>"
        reference_paths = component_paths(row.get("reference_file_or_component"))
        if not reference_paths:
            errors.append(f"{task_id}: reference_ui_patterns {ref_id} must name concrete reference page/component file paths")
        if not meaningful_items(row.get("must_reuse_or_adapt"), min_chars=8):
            errors.append(f"{task_id}: reference_ui_patterns {ref_id} must list concrete components/layout/controls to reuse or adapt")
        if not meaningful_items(row.get("must_not_inherit"), min_chars=8):
            errors.append(f"{task_id}: reference_ui_patterns {ref_id} must list concrete reference behavior not to inherit")
        pattern_text = flatten_text(
            [
                row.get("must_reuse_or_adapt"),
                row.get("visual_layout_obligation"),
                row.get("interaction_state_obligation"),
                row.get("browser_visual_proof"),
            ]
        )
        if not re.search(r"layout|section|order|group|spacing|component|control|review|summary|table|tab|布局|分组|顺序|组件|控件|预览|摘要|表格", pattern_text, re.IGNORECASE):
            errors.append(f"{task_id}: reference_ui_patterns {ref_id} must describe visual/layout/component obligations, not only fields or payload")
        if not STRONG_FRONTEND_VERIFICATION_RE.search(flatten_text([row.get("browser_visual_proof"), row.get("verification")])):
            errors.append(f"{task_id}: reference_ui_patterns {ref_id} must include browser/screenshot/DOM/trace visual proof")
        if not any(semantic_item_copied(item, flatten_text([packet.get("behavior_details"), packet.get("implementation_steps"), packet.get("verification"), packet.get("browser_verification")])) for item in meaningful_items(row.get("must_reuse_or_adapt"), min_chars=8)):
            errors.append(
                f"{task_id}: reference_ui_patterns {ref_id} is not materialized in behavior/steps/verification/browser sections; "
                "reference pattern rows cannot live only in appendix-like fields"
            )
        # Reference files are read-only pattern sources. They may be listed in files_to_change
        # if deliberately reused/edited, but they are not required in the write allowlist.
        for path in reference_paths:
            if path_in_declared_files(path, declared_files):
                continue

    field_rows = [
        as_dict(row)
        for row in as_list(packet.get("mode_field_display_matrix") or packet.get("field_display_matrix"))
    ]
    if not field_rows:
        errors.append(f"{task_id}: mode_field_display_matrix requires rows for page/tab mode-specific must-show/must-hide fields")
    field_fields = [
        "surface",
        "mode_or_state",
        "data_source",
        "must_show",
        "must_hide",
        "label_i18n",
        "empty_error_state",
        "fixture_ref",
        "assertion",
    ]
    for row in field_rows:
        validate_row(errors, task_id, "mode_field_display_matrix", row, field_fields, reference_fields=set())
        if not meaningful_items(row.get("must_show"), min_chars=3):
            errors.append(f"{task_id}: mode_field_display_matrix.must_show must list concrete fields/text")
        if not meaningful_items(row.get("must_hide"), min_chars=3):
            errors.append(f"{task_id}: mode_field_display_matrix.must_hide must list concrete old-mode fields/text")
        if not ABSENCE_ASSERTION_RE.search(flatten_text([row.get("must_hide"), row.get("assertion")])):
            errors.append(f"{task_id}: mode_field_display_matrix must include explicit absence/hidden assertion for must_hide fields")

    form_rows = [as_dict(row) for row in as_list(packet.get("form_state_matrix"))]
    if not form_rows:
        errors.append(f"{task_id}: form_state_matrix requires rows for active/inactive fields and submit participation")
    form_fields = [
        "form_or_step",
        "mode_or_state",
        "active_fields",
        "inactive_hidden_fields",
        "default_reset_rule",
        "validation_trigger",
        "submit_participation",
        "error_location",
    ]
    for row in form_rows:
        validate_row(errors, task_id, "form_state_matrix", row, form_fields, reference_fields=set())

    negative_assertions = meaningful_items(packet.get("mode_negative_assertions"), min_chars=12)
    if not negative_assertions:
        errors.append(f"{task_id}: mode_negative_assertions must list old-mode DOM/payload/text leakage checks")
    if negative_assertions and not ABSENCE_ASSERTION_RE.search(flatten_text(negative_assertions)):
        errors.append(f"{task_id}: mode_negative_assertions must explicitly use absence/hidden/not-submit/forbidden semantics")

    fixture_needs = [as_dict(row) for row in as_list(packet.get("fixture_needs"))]
    if not fixture_needs:
        errors.append(f"{task_id}: fixture_needs must declare selector/detail/progress/error fixture data required by browser verification")
    for row in fixture_needs:
        validate_row(
            errors,
            task_id,
            "fixture_needs",
            row,
            ["fixture", "state_needed", "consumer_page_or_action", "contract_source", "required_for_verification"],
            reference_fields={"contract_source"},
        )

    browser = as_dict(packet.get("browser_verification"))
    browser_required = browser.get("required")
    if browser_required is not True:
        errors.append(f"{task_id}: browser_verification.required must be true for frontend packets")
    for field in ["steps", "network_assertions", "dom_assertions", "screenshot_or_trace", "negative_assertions", "failure_meaning"]:
        if not meaningful_items(browser.get(field), min_chars=8):
            errors.append(f"{task_id}: browser_verification.{field} is required")
    browser_text = flatten_text(browser)
    if not STRONG_FRONTEND_VERIFICATION_RE.search(browser_text):
        errors.append(f"{task_id}: browser_verification must include browser/DOM/click/network/screenshot-or-trace proof")
    action_ids = [text(row.get("action_id")) for row in action_rows if text(row.get("action_id"))]
    verification_and_browser_text = flatten_text([packet.get("verification"), browser])
    for action_id in action_ids:
        if action_id not in verification_and_browser_text:
            errors.append(
                f"{task_id}: browser_verification or verification must mention action_id {action_id}; "
                "frontend proof must be row-level, not a generic browser smoke"
            )

    verification_text = flatten_text(packet.get("verification"))
    mutation_signal = FRONTEND_MUTATION_RE.search(flatten_text([packet.get("title"), packet.get("scope"), user_task, action_rows]))
    if mutation_signal and not STRONG_FRONTEND_VERIFICATION_RE.search(verification_text + " " + browser_text):
        errors.append(f"{task_id}: frontend mutation task must verify click/submit -> network/API -> DOM feedback, not just build/lint/payload")
    if WEAK_FRONTEND_VERIFICATION_RE.search(verification_text) and not STRONG_FRONTEND_VERIFICATION_RE.search(verification_text):
        errors.append(f"{task_id}: frontend verification mentions build/lint/payload but lacks browser/DOM/network/action-flow proof")

    rubric = as_dict(packet.get("experience_rubric"))
    rubric_fields = [
        "task_clarity",
        "form_ergonomics",
        "state_completeness",
        "error_readability",
        "mode_separation",
        "route_action_closure",
        "design_consistency",
        "responsive_layout_sanity",
    ]
    for field in rubric_fields:
        value = rubric.get(field)
        value_text = text(value)
        if not value_text:
            errors.append(f"{task_id}: experience_rubric.{field} is required")
            continue
        if re.search(r"\b0\b|score\s*0|评分\s*0", value_text, re.IGNORECASE):
            errors.append(f"{task_id}: experience_rubric.{field} has score 0; frontend issue cannot be executable")
        if re.search(r"\b1\b|score\s*1|评分\s*1", value_text, re.IGNORECASE) and not re.search(
            r"follow[- ]?up|risk|mitigation|后续|风险|修复", value_text, re.IGNORECASE
        ):
            errors.append(f"{task_id}: experience_rubric.{field} has score 1 without follow-up/risk mitigation")

    frontend_terms = flatten_text([
        user_task,
        action_rows,
        form_rows,
        negative_assertions,
        fixture_needs,
        browser,
        rubric,
    ])
    packet_without_frontend = dict(packet)
    for key in [
        "frontend_user_task",
        "action_route_component",
        "reference_ui_patterns",
        "mode_field_display_matrix",
        "field_display_matrix",
        "form_state_matrix",
        "mode_negative_assertions",
        "fixture_needs",
        "browser_verification",
        "experience_rubric",
    ]:
        packet_without_frontend.pop(key, None)
    if frontend_terms and not all(
        semantic_item_copied(item, flatten_text(packet_without_frontend))
        for item in [
            text(user_task.get("user_goal")),
            text(user_task.get("primary_action")),
        ]
        if item
    ):
        errors.append(f"{task_id}: frontend user goal/action must also appear in scope, behavior, steps, verification, or done criteria")
    return errors


def validate_acceptance_packet(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not is_acceptance_packet(packet):
        return errors
    for path in packet_declared_file_paths(packet):
        if PRODUCTION_MAIN_FILE_RE.search(path):
            errors.append(
                f"{task_id}: acceptance/proof packet must not list production business source in files_to_change: {path}. "
                "Move production behavior to its provider owner task and keep acceptance changes in mock/playground/test/evidence files."
            )
    provided_rows = [as_dict(row) for row in as_list(packet.get("provided_contract_obligations"))]
    if provided_rows and not re.search(r"\bMOD-ACCEPTANCE-BOUNDARY\b", flatten_text([packet.get("primary_module"), packet.get("module_responsibility")])):
        errors.append(
            f"{task_id}: acceptance/proof packet declares provided_contract_obligations but is not the canonical "
            "MOD-ACCEPTANCE-BOUNDARY provider; use proof_only/verification rows unless contracts.yaml assigns this provider"
        )
    return errors


def stateful_signal(packet: dict[str, Any]) -> bool:
    if surface_type_signal(packet, "runtime-lifecycle") or carrier_semantic_type_signal(
        packet,
        [r"stateful|runtime[- ]?lifecycle|event|progress|state\s*machine|状态机|生命周期|事件|进度"],
    ):
        return True
    signal_text = positive_text(
        [
            packet.get("title"),
            packet.get("scope"),
            packet.get("provided_contract_obligations"),
            packet.get("behavior_details"),
            packet.get("implementation_steps"),
            packet.get("verification"),
        ]
    )
    return matches_any(
        signal_text,
        [
            r"\b(lifecycle|progress|event|events|terminal|polling|retry|state\s*graph|state\s*machine|task\s*step|change\s*tracking|step\s*graph)\b",
            r"生命周期|进度|事件|状态机|状态图|终态|轮询|重试|任务步骤|变更追踪|状态推进",
        ],
    )


def validate_stateful_packet(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not stateful_signal(packet):
        return errors
    rows = [as_dict(row) for row in as_list(packet.get("stateful_behavior"))]
    if not rows:
        errors.append(f"{task_id}: stateful_behavior rows are required when packet mentions lifecycle/progress/event/status/terminal/polling/retry/state graph")
        return errors
    short_fields = ["row_id", "behavior_id", "source", "operation", "mode_or_variant", "status", "terminal", "verification"]
    long_fields = [
        "from_state",
        "trigger",
        "guard_or_precondition",
        "event_or_step",
        "to_state",
        "failure_event_or_reason",
        "producer",
    ]
    for row in rows:
        for field in short_fields:
            if not is_reference(row.get(field), min_chars=2):
                errors.append(f"{task_id}: stateful_behavior.{field} is required")
        for field in long_fields:
            if not is_meaningful(row.get(field), min_chars=4):
                errors.append(f"{task_id}: stateful_behavior.{field} is required")
        if not meaningful_items(row.get("consumers"), min_chars=4):
            errors.append(f"{task_id}: stateful_behavior.consumers is required")
        if row.get("terminal") not in {True, False, "true", "false", "yes", "no"}:
            errors.append(f"{task_id}: stateful_behavior.{row.get('row_id') or '<missing>'}.terminal must be explicit true/false")
        if not is_meaningful(row.get("frontend_assertion"), min_chars=8) and not is_meaningful(row.get("mock_fixture_ref"), min_chars=4):
            errors.append(f"{task_id}: stateful_behavior.{row.get('row_id') or '<missing>'} must include frontend_assertion or mock_fixture_ref")
        execution_text = flatten_text([
            packet.get("implementation_steps"),
            packet.get("verification"),
            packet.get("provided_contract_obligations"),
            packet.get("behavior_details"),
            packet.get("done_criteria"),
        ])
        required_terms = [text(row.get("event_or_step")), text(row.get("status")), text(row.get("failure_event_or_reason"))]
        if not any(term and semantic_item_copied(term, execution_text) for term in required_terms):
            errors.append(f"{task_id}: stateful_behavior row {row.get('row_id') or '<missing>'} is not copied into implementation/verification/provider/behavior sections")
    return errors


def persistent_mutation_signal(packet: dict[str, Any]) -> bool:
    if not is_backend_packet(packet):
        return False
    if surface_type_signal(packet, "persistent-mutation") or carrier_semantic_type_signal(
        packet,
        [r"persistent[- ]?mutation|persistence|database|repository|mapper|DO\b|dataobject|持久化|落库"],
    ):
        return True
    signal_text = positive_text(
        [
            packet.get("title"),
            packet.get("scope"),
            packet.get("behavior_details"),
            packet.get("implementation_steps"),
            packet.get("verification"),
        ]
    )
    return matches_any(
        signal_text,
        [
            r"\b(?:persist(?:ed|s|ing)?|persistence|insert(?:ed|s|ing)?|update\s+row|delete\s+row|write\s+row|"
            r"repository\s+(?:save|insert|update|delete)|mapper\s+(?:insert|update|delete)|"
            r"(?:resource\s+(?:create|delete|write|owner)|state\s+owner|writer\s+path).{0,80}(?:persist|repository|mapper|DO|dataobject|DB|SQL|readback))\b",
            r"(?:readback|schema)\b.{0,80}\b(?:persist|repository|mapper|DO|dataobject|DB|SQL|state\s+owner|writer\s+path)\b",
            r"持久化|落库|写入.*表|插入.*表|更新.*表|删除.*表|(?:状态所有者|写入路径|读回).{0,40}(?:持久|仓储|数据库|表)",
        ],
    )


def validate_persistent_mutation_packet(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not persistent_mutation_signal(packet):
        return errors
    rows = [as_dict(row) for row in as_list(packet.get("persistent_mutation_proofs"))]
    if not rows:
        errors.append(
            f"{task_id}: persistent_mutation_proofs rows are required for create/update/delete/resize/save/scale/import/bind "
            "or persistence/resource mutation packets"
        )
        return errors
    fields = [
        "mutation",
        "mode_or_variant",
        "state_owner",
        "writer_path",
        "schema_or_resource_constraints",
        "readback_consumers",
        "write_verification",
        "readback_verification",
    ]
    execution_text = flatten_text(
        [
            packet.get("behavior_details"),
            packet.get("backend_behavior_verification"),
            packet.get("implementation_steps"),
            packet.get("verification"),
            packet.get("done_criteria"),
        ]
    )
    for row in rows:
        for field in fields:
            value = row.get(field)
            if field in {"mutation", "mode_or_variant"}:
                if not is_reference(value, min_chars=2):
                    errors.append(f"{task_id}: persistent_mutation_proofs.{field} is required")
            elif field in {"schema_or_resource_constraints", "readback_consumers"}:
                if not meaningful_items(value, min_chars=6):
                    errors.append(f"{task_id}: persistent_mutation_proofs.{field} is required")
            elif not is_meaningful(value, min_chars=8):
                errors.append(f"{task_id}: persistent_mutation_proofs.{field} is required")
        if not matches_any(flatten_text(row.get("write_verification")), [r"\b(assert|test|insert|update|delete|write|HTTP|SQL|repository|resource)\b", r"断言|测试|写入|插入|删除|资源"]):
            errors.append(f"{task_id}: persistent_mutation_proofs.write_verification must prove the real writer succeeds")
        if not matches_any(flatten_text(row.get("readback_verification")), [r"\b(assert|test|read|query|detail|list|get|HTTP|SQL|repository)\b", r"断言|测试|读取|查询|详情|列表"]):
            errors.append(f"{task_id}: persistent_mutation_proofs.readback_verification must prove consumers read the written state")
        materialized_items = [
            text(row.get("state_owner")),
            text(row.get("writer_path")),
            flatten_text(row.get("schema_or_resource_constraints")),
            flatten_text(row.get("readback_consumers")),
        ]
        if not any(item and semantic_item_copied(item, execution_text) for item in materialized_items):
            errors.append(
                f"{task_id}: persistent_mutation_proofs row is not copied into behavior/steps/verification/done criteria; "
                "state owner, writer path, schema/resource constraint, or readback consumer must be executable text"
            )
    return errors


def managed_resource_ownership_signal(packet: dict[str, Any]) -> bool:
    if surface_type_signal(packet, "managed-resource-ownership"):
        return True
    if as_list(packet.get("managed_resource_ownership")):
        return True
    primary_module = packet_primary_module(packet)
    provided_text = flatten_text(packet.get("provided_contract_obligations"))
    if matches_any(
        provided_text,
        [
            r"managed[- ]resource[- ]ownership|managed resource ownership|Resource ownership|资源.*所有权|托管资源",
            r"(?:owned|existing|generated|select[- ]?existing).{0,80}(?:provenance|cleanup|protect|identity)",
            r"(?:已有|现有|自动创建|选择已有).{0,60}(?:归属|所有权|清理|保护|标识)",
        ],
    ):
        return True
    carrier_owner_rows: list[dict[str, Any]] = []
    for row in [as_dict(item) for item in as_list(packet.get("semantic_carriers"))]:
        row_text = flatten_text([row.get("semantic_type"), row.get("carrier"), row.get("copied_to")])
        if not matches_any(row_text, [r"managed[- ]resource[- ]ownership|managed resource ownership|资源.*所有权|托管资源"]):
            continue
        copied_to_text = flatten_text(row.get("copied_to"))
        if copied_to_text and not matches_any(
            copied_to_text,
            [
                r"provided_contract_obligations|managed_resource_ownership|implementation_steps|behavior_details|backend_behavior_verification|verification",
                r"提供|实现|行为|验证|资源所有权",
            ],
        ):
            continue
        owner_module = text(row.get("owner_module"))
        if owner_module and primary_module and not modules_compatible(owner_module, primary_module):
            continue
        carrier_owner_rows.append(
            {
                "source": row.get("source"),
                "projection_id": row.get("projection_id"),
                "owner_module": row.get("owner_module"),
                "semantic_type": row.get("semantic_type"),
                "carrier": row.get("carrier"),
                "must_preserve": row.get("must_preserve"),
                "copied_to": row.get("copied_to"),
                "verification": row.get("verification"),
            }
        )
    carrier_owner_text = flatten_text(carrier_owner_rows)
    if matches_any(carrier_owner_text, [r"managed[- ]resource[- ]ownership|managed resource ownership|资源.*所有权|托管资源"]):
        return True
    owner_module_text = flatten_text([packet.get("primary_module"), packet.get("module_responsibility")])
    if not matches_any(
        owner_module_text,
        [
            r"managed[- ]resources?.{0,40}(?:owner|writer|provider|lifecycle)",
            r"resource owner|resource writer|resource lifecycle owner",
            r"资源.*owner|资源写入|资源所有|托管资源.{0,20}(?:所有|写入|生命周期)",
        ],
    ):
        return False
    signal_text = positive_text(
        [
            packet.get("title"),
            packet.get("scope"),
            packet.get("behavior_details"),
            packet.get("implementation_steps"),
            packet.get("verification"),
            carrier_owner_text,
        ]
    )
    ownership_signal = matches_any(
        signal_text,
        [
            r"(?:auto[- ]?create|default[- ]?created|generated\s+resource|managed\s+resource|select[- ]?existing|existing\s+resource).{0,120}(?:resource|provider|cloud|K8s|Kubernetes|IAM|Role|Profile|Security\s*Group|\bSG\b|Bucket|DNS|VPC|Subnet)",
            r"(?:自动创建|默认创建|生成资源|托管资源|选择已有|已有资源|现有资源).{0,80}(?:资源|云|外部|provider|安全组|角色|K8s|Kubernetes)",
        ],
    )
    positive_owner_signal = matches_any(
        signal_text,
        [
            r"provider[_ -]?writer|create[_ -]?timing|ownership|state owner|cleanup|protect|detach|idempot",
            r"(?:provenance|readback|persist).{0,80}(?:provider|operator|create|delete|cleanup|protect|owned|existing)",
            r"owned\s+(?:resource|resources|cleanup)|existing\s+(?:resource|resources|protect)",
            r"写入|创建时机|归属|所有权|状态所有者|持久|读回|清理|保护|解绑|幂等",
        ],
    )
    negative_only_boundary = matches_any(
        signal_text,
        [
            r"\b(?:do not|don't|must not|not owned|does not own|out of scope|N/A).{0,80}(?:managed\s+resource|resource\s+ownership|create|cleanup|delete)",
            r"(?:不|不要|不得|不拥有|不负责|不属于|不适用).{0,40}(?:托管资源|资源所有权|创建|清理|删除)",
        ],
    )
    return ownership_signal and positive_owner_signal and not (negative_only_boundary and not carrier_owner_text)


def validate_managed_resource_ownership_packet(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not managed_resource_ownership_signal(packet):
        return errors
    rows = [as_dict(row) for row in as_list(packet.get("managed_resource_ownership"))]
    if not rows:
        errors.append(
            f"{task_id}: managed_resource_ownership rows are required when source/contract mentions "
            "auto-create/default-created/generated/select-existing external resources"
        )
        return errors
    fields = [
        "resource_type",
        "selection_mode",
        "create_timing",
        "provider_writer",
        "resource_identity",
        "provenance_state_owner",
        "runtime_consumers",
        "update_rule",
        "delete_cleanup_rule",
        "idempotency_rule",
        "failure_behavior",
        "verification",
    ]
    execution_text = flatten_text(
        [
            packet.get("behavior_details"),
            packet.get("backend_behavior_verification"),
            packet.get("persistent_mutation_proofs"),
            packet.get("implementation_steps"),
            packet.get("verification"),
            packet.get("done_criteria"),
        ]
    )
    for row in rows:
        for field in fields:
            value = row.get(field)
            if field in {"runtime_consumers", "verification"}:
                if not meaningful_items(value, min_chars=6):
                    errors.append(f"{task_id}: managed_resource_ownership.{field} is required")
            elif not is_meaningful(value, min_chars=6):
                errors.append(f"{task_id}: managed_resource_ownership.{field} is required")
        if not matches_any(flatten_text(row.get("provider_writer")), [r"provider|API|operator|writer|resource|调用|写入|创建"]):
            errors.append(f"{task_id}: managed_resource_ownership.provider_writer must name the production provider/API/operator/resource writer")
        if not matches_any(flatten_text(row.get("provenance_state_owner")), [r"owned|existing|generated|derived|provenance|state owner|persist|归属|所有权|来源|状态所有者|持久"]):
            errors.append(f"{task_id}: managed_resource_ownership.provenance_state_owner must explain owned/existing/generated provenance storage")
        if not matches_any(flatten_text(row.get("delete_cleanup_rule")), [r"cleanup|delete|protect|detach|owned|existing|清理|删除|保护|解绑|已有|现有"]):
            errors.append(f"{task_id}: managed_resource_ownership.delete_cleanup_rule must cover owned cleanup and existing protect/detach")
        verification_text = flatten_text(row.get("verification"))
        for label, patterns in [
            ("provider mutation proof", [r"provider|API|operator|create|delete|update|call|调用|创建|删除|更新"]),
            ("ownership readback proof", [r"owned|existing|provenance|readback|persist|query|归属|读回|持久|查询"]),
            ("cleanup/protect proof", [r"cleanup|protect|delete|detach|清理|保护|删除|解绑"]),
        ]:
            if not matches_any(verification_text, patterns):
                errors.append(f"{task_id}: managed_resource_ownership.verification missing {label}")
        materialized_items = [
            text(row.get("provider_writer")),
            text(row.get("resource_identity")),
            text(row.get("provenance_state_owner")),
            flatten_text(row.get("runtime_consumers")),
            text(row.get("delete_cleanup_rule")),
        ]
        if not any(item and semantic_item_copied(item, execution_text) for item in materialized_items):
            errors.append(
                f"{task_id}: managed_resource_ownership row is not copied into execution-facing sections; "
                "provider writer, resource identity, provenance, runtime consumer, or cleanup/protect must be executable text"
            )
    return errors


def validate_decision_surfaces(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = [as_dict(row) for row in as_list(packet.get("decision_surfaces"))]
    if not rows:
        return errors

    execution_text = flatten_text({field: packet.get(field) for field in DECISION_SURFACE_EXECUTION_FIELDS})
    ids_seen: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        surface_id = text(row.get("surface_id"))
        if not SURFACE_ID_RE.match(surface_id):
            errors.append(f"{task_id}: decision_surfaces[{idx}].surface_id must be DS-xxx")
        elif surface_id in ids_seen:
            errors.append(f"{task_id}: duplicate decision surface {surface_id}")
        ids_seen.add(surface_id)

        surface_type = text(row.get("surface_type"))
        if surface_type not in DECISION_SURFACE_ALLOWED_TYPES:
            errors.append(
                f"{task_id}: decision_surfaces[{idx}].surface_type must be one of "
                f"{', '.join(sorted(DECISION_SURFACE_ALLOWED_TYPES))}"
            )

        for field in ["object_capability_action", "decision", "execution_obligation"]:
            if not is_meaningful(row.get(field), min_chars=12):
                errors.append(f"{task_id}: decision_surfaces[{idx}].{field} is required and must be concrete")
        if not is_reference(row.get("verification"), min_chars=4):
            errors.append(f"{task_id}: decision_surfaces[{idx}].verification is required")

        decision_text = flatten_text(row.get("decision"))
        if OPEN_DECISION_SURFACE_RE.search(decision_text):
            errors.append(f"{task_id}: decision surface {surface_id or idx} is still open; backflow before atomic planning")

        copied_to = [text(item) for item in as_list(row.get("copied_to")) if text(item)]
        if not copied_to:
            errors.append(f"{task_id}: decision_surfaces[{idx}].copied_to must name execution-facing packet sections")
        for target in copied_to:
            if target in DECISION_SURFACE_APPENDIX_ONLY_FIELDS:
                errors.append(
                    f"{task_id}: decision surface {surface_id or idx} copied_to={target} is appendix/source-only; "
                    "copy it into executable behavior, matrix, verification, implementation, or done criteria sections"
                )
            elif target not in DECISION_SURFACE_EXECUTION_FIELDS:
                errors.append(
                    f"{task_id}: decision surface {surface_id or idx} copied_to={target} is not a recognized execution-facing packet section"
                )

        payload_items = [
            text(row.get("surface_id")),
            text(row.get("object_capability_action")),
            text(row.get("decision")),
            text(row.get("execution_obligation")),
        ]
        if not any(item and semantic_item_copied(item, execution_text) for item in payload_items):
            errors.append(
                f"{task_id}: decision surface {surface_id or idx} is not materialized in execution-facing packet sections; "
                "source/context appendix alone does not count"
            )

        surface_payload = " ".join(item for item in payload_items if item)
        if is_frontend_packet(packet) and surface_type in {"frontend-action", "mode-consumer", "capability", "post-create-consumer"}:
            if re.search(r"route|page|component|action|button|tab|form|UI|frontend|页面|按钮|操作|表单|前端", surface_payload, re.IGNORECASE):
                if not (
                    semantic_item_copied(text(row.get("execution_obligation")), flatten_text(packet.get("action_route_component")))
                    or semantic_item_copied(text(row.get("execution_obligation")), flatten_text(packet.get("mode_field_display_matrix")))
                    or semantic_item_copied(text(row.get("execution_obligation")), flatten_text(packet.get("form_state_matrix")))
                    or semantic_item_copied(text(row.get("execution_obligation")), flatten_text(packet.get("browser_verification")))
                ):
                    errors.append(
                        f"{task_id}: frontend/action decision surface {surface_id or idx} must be copied into frontend action/field/form/browser sections"
                    )
        if surface_type == "persistent-mutation" and not as_list(packet.get("persistent_mutation_proofs")):
            errors.append(f"{task_id}: persistent-mutation decision surface {surface_id or idx} requires persistent_mutation_proofs rows")
        if surface_type == "managed-resource-ownership" and not as_list(packet.get("managed_resource_ownership")):
            errors.append(f"{task_id}: managed-resource-ownership decision surface {surface_id or idx} requires managed_resource_ownership rows")
        if surface_type == "runtime-lifecycle" and not as_list(packet.get("stateful_behavior")):
            errors.append(f"{task_id}: runtime-lifecycle decision surface {surface_id or idx} requires stateful_behavior rows")

    return errors


def validate_external_capability_facts(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = [as_dict(row) for row in as_list(packet.get("external_capability_facts"))]
    if not rows:
        return errors

    execution_text = flatten_text({field: packet.get(field) for field in EXTERNAL_CAPABILITY_EXECUTION_FIELDS})
    ids_seen: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        fact_id = text(row.get("fact_id"))
        if not EXTERNAL_FACT_ID_RE.match(fact_id):
            errors.append(f"{task_id}: external_capability_facts[{idx}].fact_id must be {EXTERNAL_FACT_ID_LABEL}")
        elif fact_id in ids_seen:
            errors.append(f"{task_id}: duplicate external capability fact {fact_id}")
        ids_seen.add(fact_id)

        for field in ["external_system", "official_fact", "automq_rule", "verification", "if_omitted"]:
            if field == "verification":
                if not is_reference(row.get(field), min_chars=4):
                    errors.append(f"{task_id}: external_capability_facts[{idx}].verification is required")
            elif not is_meaningful(row.get(field), min_chars=12):
                errors.append(f"{task_id}: external_capability_facts[{idx}].{field} is required and must be concrete")
            elif is_generic_packet_text(row.get(field)):
                errors.append(
                    f"{task_id}: external_capability_facts[{idx}].{field} is generic; "
                    "copy the actual official API/resource/state/error/timing fact or mechanism mapping, not an id placeholder"
                )

        copied_to = [text(item) for item in as_list(row.get("copied_to")) if text(item)]
        if not copied_to:
            errors.append(f"{task_id}: external_capability_facts[{idx}].copied_to must name execution-facing packet sections")
        for target in copied_to:
            if target in EXTERNAL_CAPABILITY_APPENDIX_ONLY_FIELDS:
                errors.append(
                    f"{task_id}: external fact {fact_id or idx} copied_to={target} is appendix/research/source-only; "
                    "copy it into executable behavior, matrix, verification, implementation, or done criteria sections"
                )
            elif target not in EXTERNAL_CAPABILITY_EXECUTION_FIELDS:
                errors.append(
                    f"{task_id}: external fact {fact_id or idx} copied_to={target} is not a recognized execution-facing packet section"
                )

        payload_items = [
            text(row.get("fact_id")),
            text(row.get("external_system")),
            text(row.get("official_fact")),
            text(row.get("automq_rule")),
        ]
        factual_text = " ".join(payload_items[1:])
        if not re.search(
            r"\b(?:API|method|endpoint|resource|state|status|error|limit|policy|metric|tag|ARN|ID|"
            r"Auto\s*Scaling|Launch\s*Template|Instance\s*Refresh|Security\s*Group|IAM|CloudWatch|HPA|Kubernetes|K8s)\b"
            r"|接口|方法|资源|状态|错误|限制|策略|指标|标签|伸缩|安全组|角色|实例|模板",
            factual_text,
            re.IGNORECASE,
        ):
            errors.append(
                f"{task_id}: external capability fact {fact_id or idx} lacks concrete external API/resource/state/error terms"
            )
        if not any(item and semantic_item_copied(item, execution_text) for item in payload_items):
            errors.append(
                f"{task_id}: external fact {fact_id or idx} is not materialized in execution-facing packet sections; "
                "research/source appendix alone does not count"
            )

    return errors


def count_words(value: Any) -> int:
    return len(re.findall(r"[A-Za-z0-9_/-]+|[\u3400-\u9fff]", flatten_text(value)))


def normalized_sentence(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip().lower())
    return value


def duplicate_long_items(values: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    duplicates: list[str] = []
    for value in values:
        norm = normalized_sentence(value)
        if len(norm) < 80:
            continue
        seen[norm] = seen.get(norm, 0) + 1
        if seen[norm] == 2:
            duplicates.append(value[:120])
    return duplicates


def has_strong_merge_rationale(value: str) -> bool:
    if not is_meaningful(value, min_chars=24):
        return False
    if WEAK_MERGE_RATIONALE_RE.search(value) and not STRONG_MERGE_RATIONALE_RE.search(value):
        return False
    return bool(STRONG_MERGE_RATIONALE_RE.search(value))


def atomicity_owned_items(value: Any) -> list[str]:
    items = meaningful_items(value, min_chars=4)
    return [item for item in items if not NON_APPLICABLE_ATOMICITY_RE.search(item)]


def validate_atomicity_and_readability(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scope_in = as_list(as_dict(packet.get("scope")).get("in"))
    atomicity = as_dict(packet.get("atomicity_review"))
    steps = as_list(packet.get("implementation_steps"))
    sources = as_list(packet.get("sources"))
    carriers = [as_dict(row) for row in as_list(packet.get("semantic_carriers"))]
    contracts = as_list(packet.get("contract_excerpts"))
    action_rows = as_list(packet.get("action_route_component"))
    field_rows = as_list(packet.get("mode_field_display_matrix") or packet.get("field_display_matrix"))
    form_rows = as_list(packet.get("form_state_matrix"))
    stateful_rows = as_list(packet.get("stateful_behavior"))
    frontend_packet = is_frontend_packet(packet)
    backend_packet = is_backend_packet(packet)
    title = text(packet.get("title"))

    boundary_check = as_dict(atomicity.get("atomic_boundary_check"))
    boundary_required = {
        "zero_decision": "must prove product/architecture/field/error/UI/compatibility decisions are already locked",
        "single_layer_change": "must prove the task owns one layer or one inseparable module-contract closure",
        "self_contained_context": "must prove atomic-issues/Txxx.md plus listed files are sufficient without full proposal/spec/plan",
        "short_verification_loop": "must prove one short command/browser/integration loop closes this task",
        "no_error_propagation": "must prove failure cannot poison downstream inputs or sealed artifacts",
    }
    if not boundary_check:
        errors.append(
            f"{task_id}: atomicity_review.atomic_boundary_check is required; apply full-methodology Atomic Boundary before generating the packet"
        )
    for field, guidance in boundary_required.items():
        value = text(boundary_check.get(field))
        if not is_meaningful(value, min_chars=18):
            errors.append(f"{task_id}: atomicity_review.atomic_boundary_check.{field} is required; {guidance}")
        elif ID_ONLY_RE.match(value) or PLACEHOLDER_RE.match(value):
            errors.append(f"{task_id}: atomicity_review.atomic_boundary_check.{field} must be a concrete proof, not an ID/placeholder")

    for field in [
        "primary_closure",
        "user_action_flows",
        "stateful_operations",
        "provided_contracts",
        "verification_loops",
        "fileset_reason",
        "split_candidates_considered",
        "still_atomic_because",
    ]:
        if not is_meaningful(atomicity.get(field), min_chars=8):
            errors.append(
                f"{task_id}: atomicity_review.{field} is required; prove the task was split by user action/stateful operation/provided contract before generating the packet"
            )
    closure_text = flatten_text(atomicity.get("primary_closure"))
    if not re.search(r"user action|action-flow|stateful operation|provided contract|用户动作|状态机|契约", closure_text, re.IGNORECASE):
        errors.append(f"{task_id}: atomicity_review.primary_closure must name one user action-flow, one stateful operation, or one provided contract")
    action_flow_count = len(atomicity_owned_items(atomicity.get("user_action_flows")))
    stateful_op_count = len(atomicity_owned_items(atomicity.get("stateful_operations")))
    verification_loop_count = len(atomicity_owned_items(atomicity.get("verification_loops")))
    merge_rationale = text(atomicity.get("merge_rationale"))
    if action_flow_count > 1 and not has_strong_merge_rationale(merge_rationale):
        errors.append(
            f"{task_id}: atomicity_review lists {action_flow_count} user action-flows without a strong merge_rationale; "
            "split by action-flow unless they share the same submit/transaction/route/component/verification closure"
        )
    if stateful_op_count > 1 and not has_strong_merge_rationale(merge_rationale):
        errors.append(
            f"{task_id}: atomicity_review lists {stateful_op_count} stateful operations without a strong merge_rationale; "
            "split by operation unless one state transition/writer/verification cannot be separated"
        )
    if verification_loop_count > 1 and not has_strong_merge_rationale(merge_rationale):
        errors.append(
            f"{task_id}: atomicity_review lists {verification_loop_count} verification loops without a strong merge_rationale; "
            "split by verification loop unless the same command/assertion proves the single closure"
        )

    if len(steps) > MAX_EXECUTION_STEPS:
        errors.append(
            f"{task_id}: implementation_steps has {len(steps)} rows; split the issue or move audit details to sidecar "
            f"(max {MAX_EXECUTION_STEPS})"
        )
    if len(sources) > MAX_SOURCE_ROWS_PER_TASK:
        errors.append(f"{task_id}: sources has {len(sources)} rows; task likely aggregates too many upstream semantics")
    if len(contracts) > MAX_CONTRACT_ROWS_PER_TASK:
        errors.append(f"{task_id}: contract_excerpts has {len(contracts)} rows; split provider/consumer obligations")
    if len(carriers) > MAX_CARRIER_ROWS_PER_TASK:
        errors.append(f"{task_id}: semantic_carriers has {len(carriers)} rows; split task instead of carrier dumping")
    for idx, row in enumerate(carriers, start=1):
        preserve = as_list(row.get("must_preserve"))
        if len(preserve) > MAX_CARRIER_PRESERVE_ITEMS_PER_ROW:
            errors.append(
                f"{task_id}: semantic_carriers[{idx}] has {len(preserve)} must_preserve items; "
                "split carriers or assign them to narrower owner issues"
            )
    if len(stateful_rows) > MAX_STATEFUL_ROWS_PER_TASK:
        errors.append(
            f"{task_id}: stateful_behavior has {len(stateful_rows)} rows; split lifecycle/event operations into narrower issues"
        )
    if frontend_packet:
        if len(action_rows) > MAX_ACTION_ROWS_PER_FRONTEND_TASK:
            errors.append(
                f"{task_id}: frontend action_route_component has {len(action_rows)} rows; "
                "frontend issues should usually own one user action-flow; two is allowed only for tightly-coupled open+submit or tab+row proof"
            )
        if len(action_rows) > 1 and not has_strong_merge_rationale(merge_rationale):
            errors.append(
                f"{task_id}: frontend packet owns {len(action_rows)} action rows without a strong atomicity_review.merge_rationale; "
                "split by visible action-flow unless they share the same source/landing/form/browser proof"
            )
        if len(field_rows) > MAX_FIELD_ROWS_PER_FRONTEND_TASK:
            errors.append(
                f"{task_id}: mode_field_display_matrix has {len(field_rows)} rows; split page/tab surfaces by user flow"
            )
        if len(form_rows) > MAX_FORM_ROWS_PER_FRONTEND_TASK:
            errors.append(
                f"{task_id}: form_state_matrix has {len(form_rows)} rows; split create/update/resize forms"
            )
        user_task = as_dict(packet.get("frontend_user_task"))
        visible_controls = meaningful_items(user_task.get("visible_controls"), min_chars=3)
        action_text = flatten_text(action_rows)
        for control in visible_controls:
            if ACTION_WORD_RE.search(control) and not semantic_item_copied(control, action_text):
                errors.append(
                    f"{task_id}: frontend_user_task.visible_controls mentions action/control '{control}' but it is not owned in action_route_component"
                )
        for row in [as_dict(item) for item in action_rows]:
            action_id = text(row.get("action_id"))
            if action_id and not ACTION_ID_RE.match(action_id):
                errors.append(
                    f"{task_id}: action_route_component action_id '{action_id}' must use a stable prefix UI-ACT/FA/MFA/MAC/MB/MES"
                )
    if is_meaningful(title) and re.search(
        r"\b(create|detail|update[-_ ]?config|resize|progress|event|delete)\b.*\b(create|detail|update[-_ ]?config|resize|progress|event|delete)\b",
        title,
        re.IGNORECASE,
    ):
        errors.append(f"{task_id}: title appears to bundle multiple user actions; split by action-flow")
    if BROAD_TASK_TITLE_RE.search(flatten_text([title, packet.get("module_responsibility"), scope_in])) and not has_strong_merge_rationale(merge_rationale):
        errors.append(
            f"{task_id}: broad task title/scope suggests a non-atomic bundle; split before packet generation unless a strong merge_rationale proves one closure"
        )
    if merge_rationale and WEAK_MERGE_RATIONALE_RE.search(merge_rationale) and not STRONG_MERGE_RATIONALE_RE.search(merge_rationale):
        errors.append(
            f"{task_id}: atomicity_review.merge_rationale is weak or validator-oriented; "
            "same module/page/related work is not enough to merge Atomic Issues"
        )

    instruction_text = packet_instruction_text(packet)
    if count_words(instruction_text) > MAX_PACKET_EXECUTION_WORDS:
        errors.append(
            f"{task_id}: execution-facing sections are too long ({count_words(instruction_text)} words/tokens); "
            "do not compress execution semantics. Split the task by provider owner, operation surface, semantic type, "
            "or verification loop, or move only audit-only traceability to sidecar/appendix. Required owner slice, "
            "negative assertions, files_to_change, verification, and failure/backflow semantics must remain execution-facing"
        )
    if MECHANICAL_REWRITE_RE.search(instruction_text):
        errors.append(
            f"{task_id}: execution-facing text contains mechanical rewrite artifacts; "
            "use normal module language instead of synonym games"
        )
    if GAMING_HINT_RE.search(instruction_text):
        errors.append(
            f"{task_id}: execution-facing text mentions validator/gate-copy artifacts; "
            "move machine-audit wording to traceability appendix/sidecar"
        )
    if PLANNED_AS_PROOF_RE.search(instruction_text):
        errors.append(
            f"{task_id}: execution-facing text treats planned rows/rubric as proof; execution tasks must implement/run proof or move planning-only rows to sealed planning artifacts"
        )

    all_items: list[str] = []
    for container in [scope_in, steps, as_list(packet.get("prohibited_changes")), as_list(packet.get("done_criteria"))]:
        all_items.extend(text(item) for item in container if text(item))
    for row in carriers:
        all_items.extend(text(item) for item in as_list(row.get("must_preserve")) if text(item))
    duplicates = duplicate_long_items(all_items)
    if duplicates:
        errors.append(
            f"{task_id}: repeated long semantic text detected; do not duplicate carriers to satisfy validators: {duplicates[0]}"
        )

    if backend_packet and frontend_packet:
        errors.append(f"{task_id}: packet is classified as both backend and frontend; split cross-layer work")
    return errors


def validate_packet(task_id: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not TASK_RE.match(task_id):
        errors.append(f"{task_id}: invalid task id")
    for field in ["title", "issue_path", "primary_module", "module_responsibility"]:
        if not is_meaningful(packet.get(field), min_chars=4):
            errors.append(f"{task_id}: {field} is required")

    scope = as_dict(packet.get("scope"))
    if not as_list(scope.get("in")):
        errors.append(f"{task_id}: scope.in is required")
    if not as_list(scope.get("out")):
        errors.append(f"{task_id}: scope.out is required")

    required_lists = {
        "sources": ["id", "excerpt"],
        "execution_preconditions": ["upstream", "already_true", "evidence", "if_false"],
        "invariant_carryover": ["invariant", "source", "must_remain_true", "regression_check"],
        "preconditions_failure_handling": ["failure", "classification", "required_backflow", "do_not_do"],
        "existing_code_references": ["pattern", "path", "follow", "do_not_inherit"],
        "files_to_change": ["path", "change", "notes"],
        "verification": ["id", "check", "command", "expected_result", "proves", "failure_meaning"],
    }
    for section, fields in required_lists.items():
        rows = [as_dict(row) for row in as_list(packet.get(section))]
        if not rows:
            errors.append(f"{task_id}: {section} requires at least one row")
            continue
        for row in rows:
            validate_row(errors, task_id, section, row, fields)

    for row in [as_dict(row) for row in as_list(packet.get("decisions"))]:
        validate_row(errors, task_id, "decisions", row, ["id", "decision", "why_it_matters"])

    for row in [as_dict(row) for row in as_list(packet.get("contract_excerpts"))]:
        validate_row(
            errors,
            task_id,
            "contract_excerpts",
            row,
            ["id", "trigger", "normal_path", "failure_path", "consistency", "timing", "verification_excerpt"],
        )
    if not as_list(packet.get("contract_excerpts")) and not (
        as_list(packet.get("consumed_contract_snapshots"))
        or any(as_dict(row).get("projection_id") for row in as_list(packet.get("semantic_carriers")))
    ):
        errors.append(
            f"{task_id}: contract_excerpts requires a row unless this is a projection/proof-only packet "
            "with consumed_contract_snapshots or semantic_carriers.projection_id"
        )

    for row in [as_dict(row) for row in as_list(packet.get("provided_contract_obligations"))]:
        validate_row(
            errors,
            task_id,
            "provided_contract_obligations",
            row,
            ["contract", "downstream_consumer", "must_guarantee", "observable_output", "verification"],
        )

    semantic_carriers = [as_dict(row) for row in as_list(packet.get("semantic_carriers"))]
    packet_payload_text = packet_instruction_text(packet)
    source_text = flatten_text(packet.get("sources"))
    task_module_text = flatten_text([packet.get("title"), packet.get("primary_module"), packet.get("module_responsibility")])
    task_file_text = flatten_text(packet.get("files_to_change"))
    carrier_text = dense_carrier_payload(semantic_carriers)
    verification_text = flatten_text(packet.get("verification"))
    if not semantic_carriers:
        errors.append(f"{task_id}: semantic_carriers requires at least one row")
    for rule in DENSE_PACKET_RULES:
        if not matches_any(source_text, rule["source_patterns"]):
            continue
        if not matches_any(carrier_text, rule["source_patterns"]):
            continue
        if rule["name"] == "asg-infra-selector":
            frontend_module = matches_any(task_module_text, [r"\bFrontend\b", r"\bUI\b", r"前端"])
            frontend_files = matches_any(task_file_text, [r"\.tsx\b", r"/pages?/", r"/components?/"])
            if not (frontend_module or frontend_files):
                continue
        missing = missing_groups(carrier_text, rule["required_groups"])
        if missing:
            errors.append(
                f"{task_id}: source context has inferred dense semantics {rule['name']} but semantic_carriers miss {', '.join(missing)}"
            )
        verification_missing = missing_groups(verification_text, rule.get("verification_groups", []))
        if verification_missing:
            errors.append(
                f"{task_id}: verification is too weak for inferred dense semantics {rule['name']}; missing {', '.join(verification_missing)}"
            )
    for idx, row in enumerate(semantic_carriers, start=1):
        validate_row(
            errors,
            task_id,
            "semantic_carriers",
            row,
            ["source", "carrier", "verification", "omission_failure"],
            reference_fields={"source", "verification"},
        )
        must_preserve = meaningful_items(row.get("must_preserve"), min_chars=4)
        copied_to = meaningful_items(row.get("copied_to"), min_chars=4)
        if not must_preserve:
            errors.append(f"{task_id}: semantic_carriers[{idx}].must_preserve requires copied semantic details")
        if any(len(item) < 40 or is_label_only(item) for item in must_preserve):
            errors.append(
                f"{task_id}: semantic_carriers[{idx}].must_preserve is label-only or too thin; "
                "copy concrete field/state/error/default/forbidden details"
            )
        if any(GENERIC_CARRIER_RE.match(item) or is_label_only(item) for item in must_preserve):
            errors.append(f"{task_id}: semantic_carriers[{idx}] is generic; copy concrete field/state/error/default terms")
        if not copied_to:
            errors.append(f"{task_id}: semantic_carriers[{idx}].copied_to must name packet sections that carry this semantics")
        for item in must_preserve:
            if not semantic_item_copied(item, packet_payload_text):
                errors.append(
                    f"{task_id}: semantic_carriers[{idx}].must_preserve item is not materialized in execution-facing sections: {item}. "
                    "Source/contract appendix alone does not count, but do not paste the full carrier; paraphrase it into concrete behavior, steps, verification, or matrix rows."
                )

    consumed = [as_dict(row) for row in as_list(packet.get("consumed_contract_snapshots"))]
    provided = [as_dict(row) for row in as_list(packet.get("provided_contract_obligations"))]
    if not consumed and not provided:
        errors.append(f"{task_id}: consumed_contract_snapshots requires a row unless the task provides at least one contract")
    for row in consumed:
        validate_row(
            errors,
            task_id,
            "consumed_contract_snapshots",
            row,
            ["contract", "provider", "may_assume", "details", "forbidden_interpretation"],
        )

    behavior = as_dict(packet.get("behavior_details"))
    for field in ["inputs", "outputs", "error_behavior", "state_persistence", "compatibility", "boundary_conditions"]:
        if not is_meaningful(behavior.get(field)):
            errors.append(f"{task_id}: behavior_details.{field} is required")

    for idx, step in enumerate(as_list(packet.get("implementation_steps")), start=1):
        if not is_meaningful(step, min_chars=12):
            errors.append(f"{task_id}: implementation_steps[{idx}] is too thin")
    if not as_list(packet.get("implementation_steps")):
        errors.append(f"{task_id}: implementation_steps is required")

    for idx, rule in enumerate(as_list(packet.get("prohibited_changes")), start=1):
        if not is_meaningful(rule, min_chars=8):
            errors.append(f"{task_id}: prohibited_changes[{idx}] is too thin")
    if not as_list(packet.get("prohibited_changes")):
        errors.append(f"{task_id}: prohibited_changes is required")

    for idx, criterion in enumerate(as_list(packet.get("done_criteria")), start=1):
        if not is_meaningful(criterion, min_chars=8):
            errors.append(f"{task_id}: done_criteria[{idx}] is too thin")
    if not as_list(packet.get("done_criteria")):
        errors.append(f"{task_id}: done_criteria is required")

    errors.extend(validate_frontend_packet(task_id, packet))
    errors.extend(validate_backend_packet(task_id, packet))
    errors.extend(validate_acceptance_packet(task_id, packet))
    errors.extend(validate_stateful_packet(task_id, packet))
    errors.extend(validate_persistent_mutation_packet(task_id, packet))
    errors.extend(validate_managed_resource_ownership_packet(task_id, packet))
    errors.extend(validate_decision_surfaces(task_id, packet))
    errors.extend(validate_external_capability_facts(task_id, packet))
    errors.extend(validate_allowlist_feasibility(task_id, packet))
    errors.extend(validate_atomicity_and_readability(task_id, packet))
    return errors


def md_escape(value: Any) -> str:
    value_text = text(value)
    return value_text.replace("|", "\\|").replace("\n", "<br>")


def table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(cell) for cell in row) + " |")
    return "\n".join(lines)


def bullets(values: list[Any]) -> str:
    return "\n".join(f"- {md_escape(value)}" for value in values)


def numbered(values: list[Any]) -> str:
    return "\n".join(f"{idx}. {md_escape(value)}" for idx, value in enumerate(values, start=1))


def render_frontend_sections(packet: dict[str, Any]) -> list[str]:
    if not is_frontend_packet(packet):
        return []
    user_task = as_dict(packet.get("frontend_user_task"))
    action_rows = [as_dict(row) for row in as_list(packet.get("action_route_component"))]
    reference_rows = [as_dict(row) for row in as_list(packet.get("reference_ui_patterns"))]
    field_rows = [
        as_dict(row)
        for row in as_list(packet.get("mode_field_display_matrix") or packet.get("field_display_matrix"))
    ]
    form_rows = [as_dict(row) for row in as_list(packet.get("form_state_matrix"))]
    fixture_rows = [as_dict(row) for row in as_list(packet.get("fixture_needs"))]
    browser = as_dict(packet.get("browser_verification"))
    rubric = as_dict(packet.get("experience_rubric"))
    return [
        "## Frontend User Task Contract",
        table(
            ["Field", "Value"],
            [
                ["User goal", user_task.get("user_goal")],
                ["User task ID", user_task.get("user_task_id")],
                ["Entry points", bullets(as_list(user_task.get("entry_points")))],
                ["Page/routes", bullets(as_list(user_task.get("page_routes")))],
                ["Visible controls", bullets(as_list(user_task.get("visible_controls")))],
                ["Required data", bullets(as_list(user_task.get("required_data")))],
                ["Primary action", user_task.get("primary_action")],
                ["Loading/empty/error states", bullets(as_list(user_task.get("loading_empty_error_states")))],
                ["Success next state", user_task.get("success_next_state")],
                ["Failure feedback", user_task.get("failure_feedback")],
            ],
        ),
        "",
        "## Action-To-Route-To-Component",
        table(
            [
                "Action ID",
                "Visible action",
                "Source component",
                "Permission/visibility guard",
                "Handler",
                "Route/API",
                "Router definition",
                "Landing component",
                "Mode branch required",
                "Forbidden inherited UI/API",
                "Success feedback",
                "Failure feedback",
                "Verification",
            ],
            [[row.get("action_id"), row.get("visible_action"), row.get("source_component"), row.get("permission_visibility_guard"), row.get("handler"), row.get("route_or_api"), row.get("router_definition"), row.get("landing_component"), row.get("mode_branch_required"), bullets(as_list(row.get("forbidden_inherited_ui_api"))), row.get("success_feedback"), row.get("failure_feedback"), row.get("verification")] for row in action_rows],
        ),
        "",
        *(
            [
                "## Reference UI Pattern Obligations",
                table(
                    [
                        "Reference ID",
                        "Target surface/action",
                        "Reference source",
                        "Reference file/component",
                        "Must reuse/adapt",
                        "Must not inherit",
                        "Visual/layout obligation",
                        "Interaction/state obligation",
                        "Browser/visual proof",
                        "Verification",
                    ],
                    [
                        [
                            row.get("reference_id"),
                            row.get("target_surface_or_action"),
                            row.get("reference_source"),
                            row.get("reference_file_or_component"),
                            bullets(as_list(row.get("must_reuse_or_adapt"))),
                            bullets(as_list(row.get("must_not_inherit"))),
                            row.get("visual_layout_obligation"),
                            row.get("interaction_state_obligation"),
                            row.get("browser_visual_proof"),
                            row.get("verification"),
                        ]
                        for row in reference_rows
                    ],
                ),
                "",
            ]
            if reference_rows
            else []
        ),
        "## Mode Field Display Matrix",
        table(
            ["Surface", "Mode/state", "Data source", "Must show", "Must hide", "Label/i18n", "Empty/error state", "Fixture ref", "Assertion"],
            [[row.get("surface"), row.get("mode_or_state"), row.get("data_source"), bullets(as_list(row.get("must_show"))), bullets(as_list(row.get("must_hide"))), row.get("label_i18n"), row.get("empty_error_state"), row.get("fixture_ref"), row.get("assertion")] for row in field_rows],
        ),
        "",
        "## Form State Matrix",
        table(
            ["Form/step", "Mode/state", "Active fields", "Inactive/hidden fields", "Default/reset rule", "Validation trigger", "Submit participation", "Error location"],
            [[row.get("form_or_step"), row.get("mode_or_state"), bullets(as_list(row.get("active_fields"))), bullets(as_list(row.get("inactive_hidden_fields"))), row.get("default_reset_rule"), row.get("validation_trigger"), row.get("submit_participation"), row.get("error_location")] for row in form_rows],
        ),
        "",
        "## Mode Leakage Negative Assertions",
        bullets(as_list(packet.get("mode_negative_assertions"))),
        "",
        "## Fixture Needs",
        table(
            ["Fixture", "State needed", "Consumer page/action", "Contract source", "Required for verification"],
            [[row.get("fixture"), row.get("state_needed"), row.get("consumer_page_or_action"), row.get("contract_source"), row.get("required_for_verification")] for row in fixture_rows],
        ),
        "",
        "## Browser Verification Obligation",
        table(
            ["Item", "Value"],
            [
                ["Required", browser.get("required")],
                ["Steps", bullets(as_list(browser.get("steps")))],
                ["Network assertions", bullets(as_list(browser.get("network_assertions")))],
                ["DOM assertions", bullets(as_list(browser.get("dom_assertions")))],
                ["Screenshot or trace", bullets(as_list(browser.get("screenshot_or_trace")))],
                ["Negative assertions", bullets(as_list(browser.get("negative_assertions")))],
                ["Failure meaning", browser.get("failure_meaning")],
            ],
        ),
        "",
        "## Experience Rubric",
        table(
            ["Dimension", "Score / evidence"],
            [[key, value] for key, value in rubric.items()],
        ),
        "",
    ]


def render_stateful_sections(packet: dict[str, Any]) -> list[str]:
    rows = [as_dict(row) for row in as_list(packet.get("stateful_behavior"))]
    if not rows:
        return []
    return [
        "## Stateful Behavior Matrix",
        table(
            [
                "Row ID",
                "Behavior",
                "Source",
                "Operation",
                "Mode/variant",
                "From state",
                "Trigger",
                "Guard/precondition",
                "Event/step",
                "Status",
                "To state",
                "Terminal",
                "Failure/reason",
                "Producer",
                "Consumers",
                "Frontend assertion",
                "Mock fixture",
                "Verification",
            ],
            [
                [
                    row.get("row_id"),
                    row.get("behavior_id"),
                    row.get("source"),
                    row.get("operation"),
                    row.get("mode_or_variant"),
                    row.get("from_state"),
                    row.get("trigger"),
                    row.get("guard_or_precondition"),
                    row.get("event_or_step"),
                    row.get("status"),
                    row.get("to_state"),
                    row.get("terminal"),
                    row.get("failure_event_or_reason"),
                    row.get("producer"),
                    bullets(as_list(row.get("consumers"))),
                    row.get("frontend_assertion"),
                    row.get("mock_fixture_ref"),
                    row.get("verification"),
                ]
                for row in rows
            ],
        ),
        "",
    ]


def render_decision_surface_sections(packet: dict[str, Any]) -> list[str]:
    rows = [as_dict(row) for row in as_list(packet.get("decision_surfaces"))]
    if not rows:
        return []
    return [
        "## Decision Surface Ownership",
        table(
            [
                "Surface ID",
                "Surface type",
                "Object/capability/action",
                "Locked decision",
                "Execution obligation",
                "Copied into packet sections",
                "Verification",
            ],
            [
                [
                    row.get("surface_id"),
                    row.get("surface_type"),
                    row.get("object_capability_action"),
                    row.get("decision"),
                    row.get("execution_obligation"),
                    bullets(as_list(row.get("copied_to"))),
                    row.get("verification"),
                ]
                for row in rows
            ],
        ),
        "",
    ]


def render_external_capability_sections(packet: dict[str, Any]) -> list[str]:
    rows = [as_dict(row) for row in as_list(packet.get("external_capability_facts"))]
    if not rows:
        return []
    return [
        "## External Capability Facts / Mechanisms",
        table(
            [
                "Fact / Mechanism ID",
                "External system",
                "Official fact / constraint / mechanism",
                "AutoMQ rule",
                "Copied into packet sections",
                "Verification",
                "If omitted",
            ],
            [
                [
                    row.get("fact_id"),
                    row.get("external_system"),
                    row.get("official_fact"),
                    row.get("automq_rule"),
                    bullets(as_list(row.get("copied_to"))),
                    row.get("verification"),
                    row.get("if_omitted"),
                ]
                for row in rows
            ],
        ),
        "",
    ]


def render_persistent_mutation_sections(packet: dict[str, Any]) -> list[str]:
    rows = [as_dict(row) for row in as_list(packet.get("persistent_mutation_proofs"))]
    if not rows:
        return []
    return [
        "## Persistent Mutation Proofs",
        table(
            [
                "Mutation",
                "Mode/variant",
                "State owner",
                "Writer path",
                "Schema/resource constraints",
                "Readback consumers",
                "Write verification",
                "Readback verification",
            ],
            [
                [
                    row.get("mutation"),
                    row.get("mode_or_variant"),
                    row.get("state_owner"),
                    row.get("writer_path"),
                    bullets(as_list(row.get("schema_or_resource_constraints"))),
                    bullets(as_list(row.get("readback_consumers"))),
                    row.get("write_verification"),
                    row.get("readback_verification"),
                ]
                for row in rows
            ],
        ),
        "",
    ]


def render_managed_resource_ownership_sections(packet: dict[str, Any]) -> list[str]:
    rows = [as_dict(row) for row in as_list(packet.get("managed_resource_ownership"))]
    if not rows:
        return []
    return [
        "## Managed Resource Ownership",
        table(
            [
                "Resource",
                "Selection mode",
                "Create timing",
                "Provider writer",
                "Resource identity",
                "Provenance state owner",
                "Runtime consumers",
                "Update rule",
                "Delete cleanup/protect",
                "Idempotency",
                "Failure behavior",
                "Verification",
            ],
            [
                [
                    row.get("resource_type"),
                    row.get("selection_mode"),
                    row.get("create_timing"),
                    row.get("provider_writer"),
                    row.get("resource_identity"),
                    row.get("provenance_state_owner"),
                    bullets(as_list(row.get("runtime_consumers"))),
                    row.get("update_rule"),
                    row.get("delete_cleanup_rule"),
                    row.get("idempotency_rule"),
                    row.get("failure_behavior"),
                    bullets(as_list(row.get("verification"))),
                ]
                for row in rows
            ],
        ),
        "",
    ]


def render_backend_sections(packet: dict[str, Any]) -> list[str]:
    if not is_backend_packet(packet):
        return []
    verification_rows = [as_dict(row) for row in as_list(packet.get("backend_behavior_verification"))]
    boundary = as_dict(packet.get("backend_layer_boundary"))
    parts: list[str] = []
    if boundary:
        parts.extend(
            [
                "## Backend Layer Boundary",
                table(
                    ["Item", "Value"],
                    [
                        ["Primary layer", boundary.get("primary_layer")],
                        ["Touched layers", bullets(as_list(boundary.get("touched_layers")))],
                        ["Split decision", boundary.get("split_decision")],
                        ["Why not split", boundary.get("why_not_split")],
                        ["Forbidden cross-layer decisions", bullets(as_list(boundary.get("forbidden_cross_layer_decisions")))],
                        ["Verification boundary", boundary.get("verification_boundary")],
                    ],
                ),
                "",
            ]
        )
    if verification_rows:
        parts.extend(
            [
                "## Backend Behavior Verification Matrix",
                table(
                    [
                        "Behavior ID",
                        "Source",
                        "Entrypoint",
                        "Code path",
                        "Input/fixture",
                        "Expected state/output",
                        "Failure/edge",
                        "Command",
                        "Assertion",
                        "Proves",
                    ],
                    [
                        [
                            row.get("behavior_id"),
                            row.get("source"),
                            row.get("entrypoint"),
                            row.get("code_path"),
                            row.get("input_or_fixture"),
                            row.get("expected_state_or_output"),
                            row.get("failure_or_edge"),
                            row.get("command"),
                            row.get("assertion"),
                            row.get("proves"),
                        ]
                        for row in verification_rows
                    ],
                ),
                "",
            ]
        )
    return parts


def render_atomicity_review(packet: dict[str, Any]) -> list[str]:
    atomicity = as_dict(packet.get("atomicity_review"))
    if not atomicity:
        return []
    boundary = as_dict(atomicity.get("atomic_boundary_check"))
    return [
        "## Atomicity Review",
        table(
            ["Atomic Boundary", "Proof"],
            [
                ["Zero decision", boundary.get("zero_decision")],
                ["Single-layer change", boundary.get("single_layer_change")],
                ["Self-contained context", boundary.get("self_contained_context")],
                ["Short verification loop", boundary.get("short_verification_loop")],
                ["No error propagation", boundary.get("no_error_propagation")],
            ],
        ),
        "",
        table(
            ["Item", "Value"],
            [
                ["Primary closure", atomicity.get("primary_closure")],
                ["User action-flows", bullets(as_list(atomicity.get("user_action_flows")))],
                ["Stateful operations", bullets(as_list(atomicity.get("stateful_operations")))],
                ["Provided contracts", bullets(as_list(atomicity.get("provided_contracts")))],
                ["Verification loops", bullets(as_list(atomicity.get("verification_loops")))],
                ["Fileset reason", atomicity.get("fileset_reason")],
                ["Split candidates considered", bullets(as_list(atomicity.get("split_candidates_considered")))],
                ["Merge rationale", atomicity.get("merge_rationale")],
                ["Still atomic because", atomicity.get("still_atomic_because")],
                ["If not atomic", atomicity.get("if_not_atomic")],
            ],
        ),
        "",
    ]


def render_issue(task_id: str, packet: dict[str, Any]) -> str:
    scope = as_dict(packet.get("scope"))
    behavior = as_dict(packet.get("behavior_details"))

    sources = [as_dict(row) for row in as_list(packet.get("sources"))]
    semantic_carriers = [as_dict(row) for row in as_list(packet.get("semantic_carriers"))]
    decisions = [as_dict(row) for row in as_list(packet.get("decisions"))]
    contracts = [as_dict(row) for row in as_list(packet.get("contract_excerpts"))]
    preconditions = [as_dict(row) for row in as_list(packet.get("execution_preconditions"))]
    consumed = [as_dict(row) for row in as_list(packet.get("consumed_contract_snapshots"))]
    rendered_consumed = consumed or [
        {
            "contract": "无外部 consumed contract",
            "provider": "Source/Decision packet",
            "may_assume": "本任务只依赖来源上下文、锁定决策和执行前提，不依赖上游 provider contract。",
            "details": "需要的 REQ/DEC 语义已复制到 Source Context、Locked Decisions 和 Execution Preconditions。",
            "forbidden_interpretation": "不得把缺失的上游 contract 当作实现阶段自由决策；发现需要外部 provider guarantee 时必须回流补契约。",
        }
    ]
    provided = [as_dict(row) for row in as_list(packet.get("provided_contract_obligations"))]
    rendered_provided = provided or [
        {
            "contract": "不提供生产 provider contract",
            "downstream_consumer": "本任务的下游只消费或验证已有 provider contract",
            "must_guarantee": (
                "本任务只迁移调用方、前端消费方或验收证明方行为；不得声明自己提供 C-xxx-OBL 生产语义，"
                "发现需要新增 provider guarantee 时必须回流 task-planning。"
            ),
            "observable_output": (
                "可观察输出是当前任务自己的消费、展示、mock evidence 或测试结果；生产 provider 输出仍由 task-dag.yaml "
                "中列出的上游 provider task 负责。"
            ),
            "verification": "本任务的 verification 只证明消费/proof 行为正确，不把 proof 反向解释为 provider ownership。",
        }
    ]
    invariants = [as_dict(row) for row in as_list(packet.get("invariant_carryover"))]
    failures = [as_dict(row) for row in as_list(packet.get("preconditions_failure_handling"))]
    refs = [as_dict(row) for row in as_list(packet.get("existing_code_references"))]
    files = [as_dict(row) for row in as_list(packet.get("files_to_change"))]
    verification = [as_dict(row) for row in as_list(packet.get("verification"))]

    execution_parts = [
        f"# {task_id}: {text(packet.get('title'))}",
        "",
        "> 本文件由 `atomic-issue-packets.yaml` 编译生成。worker 只读取本 issue 和下方列出的文件路径，应能完成实现、运行验证，并且不做新产品/架构/接口决策。",
        "",
        "## 目标",
        text(packet.get("goal")) or f"完成 {task_id}：{text(packet.get('title'))}，并保持本任务声明的 source、decision、contract 和 verification 闭包。",
        "",
        "## Source Context",
        table(["Source", "Required excerpt / meaning"], [[row.get("id"), row.get("excerpt")] for row in sources]),
        "",
        "## 范围",
        table(["In scope", "Out of scope"], [[bullets(as_list(scope.get("in"))), bullets(as_list(scope.get("out")))]]) ,
        "",
        *render_atomicity_review(packet),
        "## 模块契约闭包",
        table(
            ["Item", "Content"],
            [
                ["Primary module", packet.get("primary_module")],
                ["Module responsibility", packet.get("module_responsibility")],
                ["Owned state/data/resources touched", bullets(as_list(packet.get("owned_state_data_resources")))],
                ["Consumed contracts assumed true", bullets([row.get("contract") for row in rendered_consumed])],
                ["Provided contracts implemented/preserved", bullets([row.get("contract") for row in rendered_provided])],
                ["Internal invariants", bullets(as_list(packet.get("internal_invariants")))],
            ],
        ),
        "",
        "## 执行前提",
        table(
            ["Upstream task/contract", "Already true before this task starts", "Evidence / verification that should have passed", "If false"],
            [[row.get("upstream"), row.get("already_true"), row.get("evidence"), row.get("if_false")] for row in preconditions],
        ),
        "",
        "## Consumed Contract Snapshot",
        table(
            ["Contract", "Provider task/module", "This task may assume", "Field/state/error/timing details", "Forbidden interpretation"],
            [[row.get("contract"), row.get("provider"), row.get("may_assume"), row.get("details"), row.get("forbidden_interpretation")] for row in rendered_consumed],
        ),
        "",
        "## Provided Contract Obligation",
        table(
            ["Contract", "Downstream consumer", "This task must guarantee", "Observable output / state", "Verification proving it"],
            [[row.get("contract"), row.get("downstream_consumer"), row.get("must_guarantee"), row.get("observable_output"), row.get("verification")] for row in rendered_provided],
        ),
        "",
        *render_decision_surface_sections(packet),
        *render_external_capability_sections(packet),
        *render_persistent_mutation_sections(packet),
        *render_managed_resource_ownership_sections(packet),
        "## Locked Decisions",
        table(["Decision", "Exact decision", "Why it matters here"], [[row.get("id"), row.get("decision"), row.get("why_it_matters")] for row in decisions]),
        "",
        "## Contract Excerpts",
        table(
            ["Contract", "Trigger", "Normal path", "Failure path", "Consistency", "Timing", "Verification excerpt"],
            [[row.get("id"), row.get("trigger"), row.get("normal_path"), row.get("failure_path"), row.get("consistency"), row.get("timing"), row.get("verification_excerpt")] for row in contracts],
        ),
        "",
        "## Invariant Carryover",
        table(
            ["Invariant", "Source", "Must remain true after this task", "Regression check"],
            [[row.get("invariant"), row.get("source"), row.get("must_remain_true"), row.get("regression_check")] for row in invariants],
        ),
        "",
        "## Preconditions Failure Handling",
        table(
            ["Failure", "Classification", "Required backflow", "Do not do"],
            [[row.get("failure"), row.get("classification"), row.get("required_backflow"), row.get("do_not_do")] for row in failures],
        ),
        "",
        "## Existing Code References",
        table(
            ["Pattern/reference", "Exact path", "What to follow", "What not to inherit"],
            [[row.get("pattern"), row.get("path"), row.get("follow"), row.get("do_not_inherit")] for row in refs],
        ),
        "",
        "## 修改文件",
        table(["Path", "Required change", "Ownership / notes"], [[row.get("path"), row.get("change"), row.get("notes")] for row in files]),
        "",
        "## 行为细节",
        table(
            ["Item", "Detail"],
            [
                ["Inputs", behavior.get("inputs")],
                ["Outputs", behavior.get("outputs")],
                ["Error behavior", behavior.get("error_behavior")],
                ["State / persistence", behavior.get("state_persistence")],
                ["Compatibility", behavior.get("compatibility")],
                ["Boundary conditions", behavior.get("boundary_conditions")],
            ],
        ),
        "",
        *render_stateful_sections(packet),
        *render_backend_sections(packet),
        *render_frontend_sections(packet),
        "## 实现步骤",
        numbered(as_list(packet.get("implementation_steps"))),
        "",
        "## 验证",
        table(
            ["Check", "Command/manual step", "Expected result", "Proves", "Failure meaning / Not Run risk"],
            [[row.get("check"), row.get("command"), row.get("expected_result"), row.get("proves"), row.get("failure_meaning")] for row in verification],
        ),
        "",
        "## 禁止事项",
        bullets(as_list(packet.get("prohibited_changes"))),
        "",
        "## 完成标准",
        "\n".join(f"- [ ] {md_escape(value)}" for value in as_list(packet.get("done_criteria"))),
        "",
    ]
    appendix_parts = [
        "## Traceability Appendix",
        "这部分用于审计和回流，不是实现步骤。实现时以 Execution Brief、修改文件、行为细节、矩阵和验证章节为准。",
        "",
        "### 来源上下文",
        table(["Source", "Required excerpt / meaning"], [[row.get("id"), row.get("excerpt")] for row in sources]),
        "",
        "### 语义载荷",
        table(
            ["Source", "Carrier", "Must preserve", "Copied into packet fields", "Verification", "If omitted"],
            [[row.get("source"), row.get("carrier"), bullets(as_list(row.get("must_preserve"))), bullets(as_list(row.get("copied_to"))), row.get("verification"), row.get("omission_failure")] for row in semantic_carriers],
        ),
        "",
        "### 锁定决策",
        table(["Decision", "Exact decision", "Why it matters here"], [[row.get("id"), row.get("decision"), row.get("why_it_matters")] for row in decisions]),
        "",
        "### 契约摘录",
        table(
            ["Contract", "Trigger", "Normal path", "Failure path", "Consistency", "Timing", "Verification excerpt"],
            [[row.get("id"), row.get("trigger"), row.get("normal_path"), row.get("failure_path"), row.get("consistency"), row.get("timing"), row.get("verification_excerpt")] for row in contracts],
        ),
        "",
        "### Invariant Carryover",
        table(
            ["Invariant", "Source", "Must remain true after this task", "Regression check"],
            [[row.get("invariant"), row.get("source"), row.get("must_remain_true"), row.get("regression_check")] for row in invariants],
        ),
        "",
        "### Preconditions Failure Handling",
        table(
            ["Failure", "Classification", "Required backflow", "Do not do"],
            [[row.get("failure"), row.get("classification"), row.get("required_backflow"), row.get("do_not_do")] for row in failures],
        ),
        "",
        "### 现有代码参考",
        table(
            ["Pattern/reference", "Exact path", "What to follow", "What not to inherit"],
            [[row.get("pattern"), row.get("path"), row.get("follow"), row.get("do_not_inherit")] for row in refs],
        ),
        "",
    ]
    return "\n".join(execution_parts + appendix_parts)


def compile_packets(change_dir: Path, check: bool = False) -> list[str]:
    packet_path = change_dir / "atomic-issue-packets.yaml"
    data = load_yaml(packet_path)
    packets = as_dict(data.get("packets"))
    if not packets:
        return [f"{packet_path}: packets is required"]

    errors: list[str] = []
    rendered: dict[Path, str] = {}
    for task_id, raw in packets.items():
        packet = as_dict(raw)
        task_errors = validate_packet(str(task_id), packet)
        errors.extend(task_errors)
        if task_errors:
            continue
        issue_path = change_dir / text(packet.get("issue_path"))
        if not str(issue_path.resolve()).startswith(str(change_dir.resolve())):
            errors.append(f"{task_id}: issue_path must stay under change directory")
            continue
        rendered[issue_path] = render_issue(str(task_id), packet)

    if errors:
        return errors

    for issue_path, content in rendered.items():
        if check:
            existing = issue_path.read_text(encoding="utf-8") if issue_path.exists() else ""
            if existing != content:
                errors.append(f"{issue_path}: not in sync with atomic-issue-packets.yaml; run atomic_issue_compile.py {change_dir}")
        else:
            issue_path.parent.mkdir(parents=True, exist_ok=True)
            issue_path.write_text(content, encoding="utf-8")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("change_dir", type=Path)
    parser.add_argument("--check", action="store_true", help="validate generated Markdown is up to date without writing")
    args = parser.parse_args()

    try:
        errors = compile_packets(args.change_dir, check=args.check)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.check:
        print("Atomic issue packet Markdown matches packet source; this is not pre-execution admission")
    else:
        print("Atomic issues compiled from packets; run workflowctl validate pre-execution before executing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
