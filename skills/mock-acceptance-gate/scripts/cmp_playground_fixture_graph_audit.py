#!/usr/bin/env python3
"""Fixture graph audit for automqbox/CMP playground acceptance.

Current packaged playground is a real product-code runtime with no-cloud adapters for
physical external interfaces. This audit checks the reusable foundation pieces
that must exist before a feature-specific runtime scenario can be trusted.
It does not treat product mocks as acceptance evidence.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import sys
from collections.abc import Iterable
from typing import Any


@dataclasses.dataclass(frozen=True)
class Finding:
    fixture_object: str
    required_reference: str
    producer_source: str
    consumer_path: str
    check_result: str
    blocks_acceptance: str


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def load_json(path: pathlib.Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def markdown_row(cols: Iterable[object]) -> str:
    return "| " + " | ".join(str(col).replace("\n", " ").replace("|", "\\|") for col in cols) + " |"


def add(findings: list[Finding], obj: str, ref: str, source: str, consumer: str, result: str, blocks: bool) -> None:
    findings.append(Finding(obj, ref, source, consumer, result, "yes" if blocks else "no"))


def cmp_root(repo: pathlib.Path) -> pathlib.Path:
    return repo / "cmp" if (repo / "cmp" / "cmp-playground").exists() else repo


def java_root(root: pathlib.Path) -> pathlib.Path:
    return root / "cmp-playground" / "src" / "main" / "java"


def resource_mock_dir(root: pathlib.Path) -> pathlib.Path:
    return root / "cmp-playground" / "src" / "main" / "resources" / "mock"


def nocloud_file(root: pathlib.Path, name: str) -> pathlib.Path:
    return java_root(root) / "com" / "automq" / "cmp" / "playground" / "nocloud" / name


def read_mock_json(mock_dir: pathlib.Path, name: str) -> list[Any]:
    path = mock_dir / name
    if not path.exists():
        return []
    try:
        return [item for item in as_list(load_json(path)) if isinstance(item, dict)]
    except Exception:
        return []


def require_tokens(
    findings: list[Finding],
    obj: str,
    source: str,
    consumer: str,
    text: str,
    tokens: list[tuple[str, str]],
) -> None:
    for token, label in tokens:
        add(
            findings,
            obj,
            label,
            source,
            consumer,
            "present" if token in text else "missing",
            token not in text,
        )


def audit_nocloud_foundation(root: pathlib.Path, findings: list[Finding]) -> bool:
    files = {
        "NoCloudInfraProvider.java": nocloud_file(root, "NoCloudInfraProvider.java"),
        "NoCloudKubernetesApiServer.java": nocloud_file(root, "NoCloudKubernetesApiServer.java"),
        "NoCloudInstanceOperator.java": nocloud_file(root, "NoCloudInstanceOperator.java"),
        "NoCloudConnectRestClient.java": nocloud_file(root, "NoCloudConnectRestClient.java"),
        "NoCloudMetricsServer.java": nocloud_file(root, "NoCloudMetricsServer.java"),
        "NoCloudRuntimeSimulator.java": nocloud_file(root, "NoCloudRuntimeSimulator.java"),
        "NoCloudPlaygroundProperties.java": nocloud_file(root, "NoCloudPlaygroundProperties.java"),
        "PlaygroundDatabaseSeeder.java": nocloud_file(root, "PlaygroundDatabaseSeeder.java"),
    }
    foundation_present = all(path.exists() for path in files.values())
    for name, path in files.items():
        add(
            findings,
            name,
            "no-cloud foundation source file",
            str(path.relative_to(root)) if path.exists() else str(path),
            "Real controller/service/task path consumes no-cloud external adapters",
            "present" if path.exists() else "missing",
            not path.exists(),
        )
    if not foundation_present:
        return False

    infra = read_text(files["NoCloudInfraProvider.java"])
    require_tokens(findings, "NoCloudInfraProvider.java", "NoCloudInfraProvider.java", "Provider selectors and ASG/K8s create dependencies", infra, [
        ("vpc-playground", "VPC fixture"),
        ("subnet-playground-a", "Subnet A fixture"),
        ("subnet-playground-b", "Subnet B fixture"),
        ("sg-playground", "Security Group fixture"),
        ("automq-playground-connect", "IAM role fixture"),
        ("listVpcs", "VPC selector API"),
        ("listSubnets", "Subnet selector API"),
        ("listSecurityGroupRules", "Security group rule API"),
        ("listRoles", "IAM role selector API"),
        ("m7i.large", "Instance type/node group fixture"),
    ])

    k8s = read_text(files["NoCloudKubernetesApiServer.java"])
    require_tokens(findings, "NoCloudKubernetesApiServer.java", "NoCloudKubernetesApiServer.java", "K8s deployment/pod/log APIs consumed by real Connect runtime code", k8s, [
        ("/api/v1/namespaces", "namespace API"),
        ("/api/v1/namespaces/[^/]+/pods", "pod list API"),
        ("/log", "pod log API"),
        ("applyDeployment", "deployment create/update"),
        ("deleteDeployment", "deployment delete"),
        ("serviceaccounts", "service account API"),
    ])

    connect_rest = read_text(files["NoCloudConnectRestClient.java"])
    require_tokens(findings, "NoCloudConnectRestClient.java", "NoCloudConnectRestClient.java", "Kafka Connect REST API consumed by real Connector service", connect_rest, [
        ("/connector-plugins", "connector plugins endpoint"),
        ("/connectors", "connector list/create endpoint"),
        ("/connectors/[^/]+/status", "connector status endpoint"),
        ("/connectors/[^/]+/config", "connector config endpoint"),
        ("pause|resume|stop|restart", "pause/resume/stop/restart endpoints"),
        ("DELETE", "delete connector endpoint"),
    ])

    runtime = read_text(files["NoCloudRuntimeSimulator.java"])
    require_tokens(findings, "NoCloudRuntimeSimulator.java", "NoCloudRuntimeSimulator.java", "No-cloud domain graph behind external adapters", runtime, [
        ("recoverCluster", "recover created ConnectCluster from real DB"),
        ("recoverConnectorsFromDb", "recover created Connector from real DB"),
        ("127.0.0.1:8083", "Connect worker id preserves port 8083"),
        ("metricsText", "Connect /metrics endpoint data"),
        ("podLog", "K8s pod log data"),
        ("metricsMode", "metrics available/empty/error/unavailable switch"),
        ("logsMode", "logs available/empty/error/unavailable switch"),
        ("connector", "metrics/log labels include connector"),
        ("client_id", "metrics labels include client_id"),
        ("tasks.max", "connector task count derived from real config"),
    ])
    add(
        findings,
        "NoCloudRuntimeSimulator.java",
        "Prometheus metrics text has no explicit timestamp",
        "NoCloudRuntimeSimulator.metric/metricsText",
        "Real PrometheusMetricsParser compatibility",
        "no timestamp-like metric append observed" if ".append(' ')" not in runtime and '.append(" ")' not in runtime else "manual review needed",
        False,
    )

    instance = read_text(files["NoCloudInstanceOperator.java"])
    require_tokens(findings, "NoCloudInstanceOperator.java", "NoCloudInstanceOperator.java", "Kafka instance API fixture consumed by real ConnectCluster/Connector flows", instance, [
        ("kf-playground", "Kafka instance id fixture"),
        ("listNodes", "Kafka node list API"),
        ("describeBrokerNodes", "Kafka broker node detail API"),
        ("metrics", "Kafka instance metrics support"),
    ])

    properties = read_text(files["NoCloudPlaygroundProperties.java"])
    require_tokens(findings, "NoCloudPlaygroundProperties.java", "NoCloudPlaygroundProperties.java", "No-cloud runtime configuration", properties, [
        ("kubeApiPort", "K8s API port"),
        ("connectRestPort", "Connect REST API port"),
        ("metricsPort", "metrics endpoint port"),
        ("metricsMode", "metrics mode"),
        ("logsMode", "logs mode"),
        ("kf-playground", "Kafka instance id"),
    ])

    seeder = read_text(files["PlaygroundDatabaseSeeder.java"])
    require_tokens(findings, "PlaygroundDatabaseSeeder.java", "PlaygroundDatabaseSeeder.java", "Seeded DB graph consumed by real repositories/services", seeder, [
        ("seedInfraProfile", "infra profile seed"),
        ("seedKafkaInstance", "Kafka instance seed"),
        ("seedConnectVersion", "Connect version seed"),
        ("seedConnectPlugins", "Connect plugin seed"),
        ("normalizeConnectClusterPodEndpoints", "created cluster pod endpoint normalization"),
        ("connect_plugin", "plugin table"),
        ("connect_version", "version table"),
        ("instance_table", "instance table"),
    ])
    return True


def audit_resource_fixtures(root: pathlib.Path, findings: list[Finding]) -> None:
    mock_dir = resource_mock_dir(root)
    instances = read_mock_json(mock_dir, "instances.json")
    connectors = read_mock_json(mock_dir, "connectors.json")
    plugins = read_mock_json(mock_dir, "connector-plugins.json")
    add(findings, "instances.json", "Kafka instance support fixture", "cmp-playground resources/mock", "seeded-world cross-check", f"{len(instances)} row(s)" if instances else "missing/empty; acceptable only if DB seeder owns instance graph", False)
    add(findings, "connector-plugins.json", "connector plugin support fixture", "cmp-playground resources/mock", "seeded-world cross-check", f"{len(plugins)} row(s)" if plugins else "missing/empty; acceptable only if DB seeder owns plugin graph", False)
    add(findings, "connectors.json", "connector support fixture", "cmp-playground resources/mock", "created connector graph cross-check", f"{len(connectors)} row(s)" if connectors else "missing/empty; acceptable when real create path seeds connectors", False)


def audit_smoke_script(root: pathlib.Path, findings: list[Finding]) -> None:
    smoke = root / "cmp-playground" / "scripts" / "runtime-smoke.js"
    text = read_text(smoke)
    add(
        findings,
        "runtime-smoke.js",
        "packaged golden smoke script",
        str(smoke.relative_to(root)) if smoke.exists() else str(smoke),
        "Representative packaged ConnectCluster/Connector acceptance after fast matrices pass",
        "present" if smoke.exists() else "missing",
        not smoke.exists(),
    )
    if not smoke.exists():
        return
    require_tokens(findings, "runtime-smoke.js", "runtime-smoke.js", "Packaged golden flow evidence", text, [
        ("PACKAGED_RUNTIME_PLAYGROUND_STRICT_MOCK_MODE", "strict mode enabled"),
        ("PACKAGED_RUNTIME_PLAYGROUND_K8S_API_PORT", "K8s API port isolated"),
        ("PACKAGED_RUNTIME_PLAYGROUND_CONNECT_REST_PORT", "Connect REST port isolated"),
        ("PACKAGED_RUNTIME_PLAYGROUND_METRICS_PORT", "metrics port isolated"),
        ("POST\", \"/api/v1/connect/clusters/check", "cluster check"),
        ("POST\", \"/api/v1/connect/clusters\"", "cluster create"),
        ("/last-change", "change/progress API"),
        ("/workers", "workers API"),
        ("/metrics", "metrics API"),
        ("/logs", "logs API"),
        ("POST\", \"/api/v1/connect/connectors/check", "connector check"),
        ("POST\", \"/api/v1/connect/connectors\"", "connector create"),
        ("/tasks", "connector tasks API"),
        ("FINISH_CREATE", "real task/change step assertion"),
    ])


def run(repo: pathlib.Path, fail_on_warning: bool) -> int:
    root = cmp_root(repo)
    if not (root / "cmp-playground").exists():
        print(f"Cannot find cmp-playground under {repo}", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    audit_nocloud_foundation(root, findings)
    audit_resource_fixtures(root, findings)
    audit_smoke_script(root, findings)

    blocking = [finding for finding in findings if finding.blocks_acceptance == "yes"]
    print("# Packaged Runtime Fixture Graph Audit")
    print()
    print(markdown_row(["Fixture object", "Required reference", "Producer/source", "Consumer path/page", "Check result", "Blocks acceptance"]))
    print(markdown_row(["---", "---", "---", "---", "---", "---:"]))
    for finding in findings:
        print(markdown_row(dataclasses.astuple(finding)))
    print()
    print(f"Summary: {len(blocking)} blocking finding(s), {len(findings)} checked edge(s).")
    return 1 if blocking and fail_on_warning else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Path to automqbox repository root")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Print findings but exit 0. Use only for exploratory archaeology, not acceptance.",
    )
    args = parser.parse_args()
    repo = pathlib.Path(args.repo).expanduser().resolve()
    if not repo.exists():
        print(f"Repository root does not exist: {repo}", file=sys.stderr)
        return 2
    return run(repo, fail_on_warning=not args.warn_only)


if __name__ == "__main__":
    raise SystemExit(main())
