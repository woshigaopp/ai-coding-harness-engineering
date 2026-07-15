#!/usr/bin/env python3
"""Runtime audit for an already-started automqbox/CMP packaged playground.

This script checks the failure modes that are expensive to rediscover during
each feature acceptance:

- HTML freshness and stale main bundle injection.
- JAR/static resource consistency when a repo path is provided.
- JS/CSS resource status and MIME sanity.
- Browser route smoke through Chrome DevTools Protocol.
- Known packaged playground hazards such as Ace raw static requests and
  automq-ui Table undefined api.send() errors.

It does not build or start the playground. Build/start commands remain
environment-specific; this audit is the reusable proof step after startup.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from typing import Any


DEFAULT_ROUTES = [
    "/connect/clusters/create",
    "/connect/clusters",
    "/connect/connectors",
    "/connect/plugins",
    "/instances",
    "/system",
    "/system/user",
    "/system/service-account",
    "/system/maintenance",
]

ACE_RAW_RE = re.compile(
    r"/static/(?:theme-dawn|mode-yaml|mode-properties|ext-language_tools|worker-yaml)\.js"
)
MAIN_RE = re.compile(r"/static/(main-[A-Za-z0-9_.-]+\.js)")
STATIC_REF_RE = re.compile(r"""(?:src|href)=["']([^"']+)["']""")
BAD_CONSOLE_RE = re.compile(
    r"Unexpected token '<'|Cannot read properties of undefined \(reading 'send'\)|"
    r"theme-dawn\.js|mode-yaml\.js|mode-properties\.js|ext-language_tools\.js|"
    r"worker-yaml\.js failed to load|Failed to load worker",
    re.IGNORECASE,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch(url: str, timeout: float = 15.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "cmp-playground-playground-runtime-audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return {
                "url": url,
                "status": resp.status,
                "content_type": resp.headers.get("content-type", ""),
                "body": body,
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        return {
            "url": url,
            "status": exc.code,
            "content_type": exc.headers.get("content-type", "") if exc.headers else "",
            "body": exc.read() if exc.fp else b"",
            "error": str(exc),
        }
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"url": url, "status": 0, "content_type": "", "body": b"", "error": str(exc)}


def join_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def latest_packaged_runtime_jar(repo: pathlib.Path) -> pathlib.Path | None:
    cmp_root = repo / "cmp" if (repo / "cmp" / "cmp-app").exists() else repo
    candidates = sorted(
        (cmp_root / "cmp-app" / "target").glob("cmp-app-*.jar"),
        key=lambda path: path.stat().st_mtime if path.exists() else 0,
        reverse=True,
    )
    return candidates[0] if candidates else None


def jar_static_audit(repo: pathlib.Path, html_main: str | None) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    jar = latest_packaged_runtime_jar(repo)
    result: dict[str, Any] = {
        "repo": str(repo),
        "jar": str(jar) if jar else "",
        "jar_mtime": datetime.fromtimestamp(jar.stat().st_mtime, timezone.utc).isoformat() if jar else "",
        "main_entries": [],
        "asset_entries": [],
        "manifest_entries": [],
    }
    if not jar:
        errors.append(f"no cmp-app playground jar found under {repo}/cmp/cmp-app/target")
        return result, errors
    try:
        with zipfile.ZipFile(jar) as zf:
            names = zf.namelist()
    except Exception as exc:
        errors.append(f"cannot read jar {jar}: {exc}")
        return result, errors

    main_entries = sorted({name for name in names if re.search(r"(^|/)static/main-[^/]+\.js$", name)})
    asset_entries = sorted({name for name in names if re.search(r"(^|/)static/assets/index-[^/]+\.js$", name)})
    manifest_entries = sorted({name for name in names if "manifest" in name.lower() and "/static/" in name})
    result["main_entries"] = main_entries
    result["asset_entries"] = asset_entries
    result["manifest_entries"] = manifest_entries

    basenames = sorted({pathlib.PurePosixPath(name).name for name in main_entries})
    if not basenames:
        errors.append(f"jar {jar} contains no static/main-*.js entry")
    if len(basenames) > 1:
        errors.append(f"jar {jar} contains multiple main bundles {basenames}; run clean package or prove manifest-selected entry")
    if html_main and html_main not in basenames:
        errors.append(f"HTML injects {html_main}, but jar main bundles are {basenames}")
    return result, errors


def html_static_audit(base_url: str, html_route: str) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    html_url = join_url(base_url, html_route)
    html_resp = fetch(html_url)
    body = html_resp.get("body", b"")
    text = body.decode("utf-8", errors="replace")
    main_matches = MAIN_RE.findall(text)
    static_refs = [ref for ref in STATIC_REF_RE.findall(text) if ref.startswith("/static/") or "/static/" in ref]
    result: dict[str, Any] = {
        "html_url": html_url,
        "html_status": html_resp["status"],
        "html_content_type": html_resp["content_type"],
        "has_root": 'id="root"' in text or "id='root'" in text,
        "main_scripts": main_matches,
        "static_refs": static_refs,
        "resource_checks": [],
    }
    if html_resp["status"] >= 400 or html_resp["status"] == 0:
        errors.append(f"HTML route {html_url} failed with status={html_resp['status']} error={html_resp['error']}")
        return result, errors
    if "text/html" not in html_resp["content_type"].lower():
        errors.append(f"HTML route {html_url} returned non-html content-type {html_resp['content_type']}")
    if not result["has_root"]:
        errors.append(f"HTML route {html_url} does not contain #root")
    if not main_matches:
        errors.append(f"HTML route {html_url} does not inject /static/main-*.js")

    for ref in static_refs:
        url = join_url(base_url, ref)
        resp = fetch(url)
        body_prefix = resp.get("body", b"")[:80].decode("utf-8", errors="replace").replace("\n", " ")
        check = {
            "url": url,
            "status": resp["status"],
            "content_type": resp["content_type"],
            "body_prefix": body_prefix,
        }
        result["resource_checks"].append(check)
        if resp["status"] >= 400 or resp["status"] == 0:
            errors.append(f"static resource failed {url}: status={resp['status']} error={resp['error']}")
            continue
        lower_url = url.lower()
        lower_type = resp["content_type"].lower()
        if (lower_url.endswith(".js") or lower_url.endswith(".mjs")) and "text/html" in lower_type:
            errors.append(f"JS resource returned HTML {url}")
        if lower_url.endswith(".css") and "text/html" in lower_type:
            errors.append(f"CSS resource returned HTML {url}")
    return result, errors


def find_chrome(explicit: str = "") -> str:
    candidates = [
        explicit,
        os.environ.get("CHROME_BIN", ""),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
        shutil.which("chrome") or "",
    ]
    for candidate in candidates:
        if candidate and pathlib.Path(candidate).exists():
            return candidate
    return ""


def wait_for_json(url: str, timeout_sec: float = 20.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resp = fetch(url, timeout=2.0)
        if resp["status"] and resp["status"] < 400:
            return True
        time.sleep(0.25)
    return False


def browser_node_script() -> str:
    return r"""
import fs from 'node:fs';
const baseUrl = process.argv[2];
const chromePort = process.argv[3];
const output = process.argv[4];
const routes = JSON.parse(process.argv[5]);
const badConsolePattern = new RegExp("Unexpected token '<'|Cannot read properties of undefined \\(reading 'send'\\)|theme-dawn\\.js|mode-yaml\\.js|mode-properties\\.js|ext-language_tools\\.js|worker-yaml\\.js failed to load|Failed to load worker", "i");
await fetch(`http://127.0.0.1:${chromePort}/json/version`).then(r => r.json());
let nextId = 1;
function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  const pending = new Map();
  const events = [];
  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const {resolve, reject} = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    } else if (msg.method) {
      events.push(msg);
    }
  };
  const ready = new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  return {
    ws,
    ready,
    events,
    send(method, params = {}) {
      const id = nextId++;
      ws.send(JSON.stringify({id, method, params}));
      return new Promise((resolve, reject) => pending.set(id, {resolve, reject}));
    },
  };
}
async function newPage() {
  const target = await fetch(`http://127.0.0.1:${chromePort}/json/new?about:blank`, {method: 'PUT'}).then(r => r.json());
  const c = connect(target.webSocketDebuggerUrl);
  await c.ready;
  await c.send('Runtime.enable');
  await c.send('Page.enable');
  await c.send('Network.enable');
  await c.send('Log.enable');
  return c;
}
function eventText(e) {
  if (e.method === 'Runtime.exceptionThrown') return `${e.params?.exceptionDetails?.text || ''} ${e.params?.exceptionDetails?.exception?.description || ''}`;
  if (e.method === 'Runtime.consoleAPICalled') return (e.params?.args || []).map(a => a.value || a.description || '').join(' ');
  if (e.method === 'Log.entryAdded') return e.params?.entry?.text || '';
  return '';
}
const wait = ms => new Promise(r => setTimeout(r, ms));
const results = [];
for (const route of routes) {
  const c = await newPage();
  await c.send('Page.navigate', {url: baseUrl.replace(/\/$/, '') + route});
  const start = Date.now();
  while (Date.now() - start < 7000) {
    const loaded = c.events.some(e => e.method === 'Page.loadEventFired');
    if (loaded && Date.now() - start > 2500) break;
    await wait(250);
  }
  const evalRes = await c.send('Runtime.evaluate', {
    expression: `(() => ({title: document.title, readyState: document.readyState, bodyText: document.body.innerText.slice(0, 700), rootChildren: document.querySelector('#root')?.children.length || 0}))()`,
    returnByValue: true,
  });
  const requestById = new Map();
  for (const e of c.events) if (e.method === 'Network.requestWillBeSent') requestById.set(e.params.requestId, e.params.request.url);
  const networkBad = c.events
    .filter(e => e.method === 'Network.responseReceived' && e.params?.response?.status >= 400 && !/favicon\.ico$/.test(e.params.response.url))
    .map(e => ({status: e.params.response.status, url: e.params.response.url, mime: e.params.response.mimeType}));
  const networkFailed = c.events
    .filter(e => e.method === 'Network.loadingFailed' && e.params?.errorText !== 'net::ERR_ABORTED')
    .map(e => ({url: requestById.get(e.params.requestId), errorText: e.params?.errorText}));
  const consoleBad = c.events
    .filter(e => {
      const txt = eventText(e);
      return e.method === 'Runtime.exceptionThrown'
        || (e.method === 'Runtime.consoleAPICalled' && ['error', 'assert'].includes(e.params?.type))
        || (e.method === 'Log.entryAdded' && ['error'].includes(e.params?.entry?.level))
        || badConsolePattern.test(txt);
    })
    .map(e => ({method: e.method, level: e.params?.type || e.params?.entry?.level, text: eventText(e).slice(0, 1000)}));
  const allUrls = [...requestById.values()];
  const badAceStaticRequests = allUrls.filter(u => /\/static\/(theme-dawn|mode-yaml|mode-properties|ext-language_tools|worker-yaml)\.js/.test(u));
  const workerAssetRequests = allUrls.filter(u => /worker-yaml-[^/]+\.js/.test(u));
  results.push({route, eval: evalRes.result.value, networkBad, networkFailed, consoleBad, badAceStaticRequests, workerAssetRequests});
  c.ws.close();
}
const failed = results.filter(r => r.networkBad.length || r.networkFailed.length || r.consoleBad.length || r.badAceStaticRequests.length);
const summary = {baseUrl, routes: results, failed};
fs.writeFileSync(output, JSON.stringify(summary, null, 2));
console.log(JSON.stringify({
  baseUrl,
  failedCount: failed.length,
  routes: results.map(r => ({
    route: r.route,
    rootChildren: r.eval.rootChildren,
    badNetwork: r.networkBad.length,
    failedNetwork: r.networkFailed.length,
    consoleBad: r.consoleBad.length,
    badAceStaticRequests: r.badAceStaticRequests,
    workerAssetRequests: r.workerAssetRequests,
  })),
}, null, 2));
if (failed.length) process.exit(2);
"""


def run_browser_audit(base_url: str, routes: list[str], chrome_bin: str, chrome_port: int, work_dir: pathlib.Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if not chrome_bin:
        return {"skipped": False, "error": "Chrome executable not found"}, ["Chrome executable not found; set --chrome-bin or CHROME_BIN"]
    node = shutil.which("node")
    if not node:
        return {"skipped": False, "error": "node executable not found"}, ["node executable not found; browser CDP audit cannot run"]

    work_dir.mkdir(parents=True, exist_ok=True)
    user_data_dir = work_dir / f"chrome-cdp-{chrome_port}"
    output = work_dir / f"browser-route-smoke-{chrome_port}.json"
    script = work_dir / f"browser-route-smoke-{chrome_port}.mjs"
    script.write_text(browser_node_script(), encoding="utf-8")

    chrome_cmd = [
        chrome_bin,
        "--headless=new",
        f"--remote-debugging-port={chrome_port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "about:blank",
    ]
    log_path = work_dir / f"chrome-cdp-{chrome_port}.log"
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(chrome_cmd, stdout=log, stderr=subprocess.STDOUT)
    try:
        if not wait_for_json(f"http://127.0.0.1:{chrome_port}/json/version"):
            errors.append(f"Chrome CDP did not become ready on port {chrome_port}")
            return {"chrome_log": str(log_path), "output": str(output)}, errors
        node_cmd = [node, str(script), base_url, str(chrome_port), str(output), json.dumps(routes)]
        node_proc = subprocess.run(node_cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        result: dict[str, Any] = {
            "chrome_bin": chrome_bin,
            "chrome_port": chrome_port,
            "chrome_log": str(log_path),
            "output": str(output),
            "node_exit_code": node_proc.returncode,
            "node_output": node_proc.stdout,
        }
        if output.exists():
            try:
                result["summary"] = json.loads(output.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"cannot parse browser output {output}: {exc}")
        if node_proc.returncode != 0:
            errors.append(f"browser route smoke failed with exit code {node_proc.returncode}; see {output}")
        return result, errors
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - environment dependent
            proc.kill()


def parse_routes(raw: str) -> list[str]:
    if not raw:
        return DEFAULT_ROUTES
    return [item.strip() for item in raw.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Running packaged playground base URL, e.g. http://127.0.0.1:19083")
    parser.add_argument("--repo", default="", help="Optional automqbox repo root for jar/static consistency checks")
    parser.add_argument("--html-route", default="/connect/clusters/create", help="Route used to fetch packaged HTML and script tags")
    parser.add_argument("--routes", default=",".join(DEFAULT_ROUTES), help="Comma-separated browser routes for CDP smoke")
    parser.add_argument("--out", default="", help="JSON evidence output path")
    parser.add_argument("--chrome-bin", default="", help="Chrome executable path. Defaults to CHROME_BIN or common macOS/Linux paths")
    parser.add_argument("--chrome-port", type=int, default=39224, help="Temporary Chrome DevTools port")
    parser.add_argument("--work-dir", default="", help="Directory for temporary browser evidence")
    parser.add_argument("--skip-browser", action="store_true", help="Run only HTML/static/JAR checks")
    parser.add_argument("--warn-only", action="store_true", help="Print blockers but exit 0")
    args = parser.parse_args()

    errors: list[str] = []
    routes = parse_routes(args.routes)
    work_dir = pathlib.Path(args.work_dir).expanduser().resolve() if args.work_dir else pathlib.Path(tempfile.mkdtemp(prefix="cmp-playground-audit-"))
    result: dict[str, Any] = {
        "generated_at": now(),
        "base_url": args.base_url,
        "html_route": args.html_route,
        "routes": routes,
        "work_dir": str(work_dir),
    }

    html_result, html_errors = html_static_audit(args.base_url, args.html_route)
    result["html_static"] = html_result
    errors.extend(html_errors)
    html_main = html_result.get("main_scripts", [None])[0] if html_result.get("main_scripts") else None

    if args.repo:
        repo = pathlib.Path(args.repo).expanduser().resolve()
        jar_result, jar_errors = jar_static_audit(repo, html_main)
        result["jar_static"] = jar_result
        errors.extend(jar_errors)

    if not args.skip_browser:
        browser_result, browser_errors = run_browser_audit(
            args.base_url,
            routes,
            find_chrome(args.chrome_bin),
            args.chrome_port,
            work_dir,
        )
        result["browser"] = browser_result
        errors.extend(browser_errors)

    result["errors"] = errors
    result["status"] = "PASS" if not errors else "BLOCKED"
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        out = pathlib.Path(args.out).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output + "\n", encoding="utf-8")

    print("# automqbox/CMP Packaged Playground Runtime Audit")
    print()
    print(f"- base_url: `{args.base_url}`")
    print(f"- status: `{result['status']}`")
    print(f"- work_dir: `{work_dir}`")
    if args.out:
        print(f"- evidence: `{pathlib.Path(args.out).expanduser().resolve()}`")
    print()
    if errors:
        print("## Blocking Findings")
        print()
        for error in errors:
            print(f"- {error}")
    else:
        print("No blocking packaged playground findings.")
    print()
    print("## JSON Summary")
    print()
    print("```json")
    print(output[:12000])
    if len(output) > 12000:
        print("... truncated; see --out evidence file ...")
    print("```")

    if errors and not args.warn_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
