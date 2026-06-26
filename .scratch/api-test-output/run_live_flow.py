from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class FlowConfig:
    base_url: str
    output_dir: Path
    log_path: Path
    username: str
    password: str
    request_timeout_s: int
    progress_interval_s: int
    run_id: str | None


def parse_args() -> FlowConfig:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--output-dir", default=".scratch/api-test-output")
    parser.add_argument("--username", default="teacher1")
    parser.add_argument("--password", default="dev")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--progress-interval", type=int, default=10)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    return FlowConfig(
        base_url=args.base_url.rstrip("/"),
        output_dir=output_dir,
        log_path=output_dir / "run_live_flow.log",
        username=args.username,
        password=args.password,
        request_timeout_s=args.timeout,
        progress_interval_s=args.progress_interval,
        run_id=args.run_id,
    )


def log(config: FlowConfig, message: str) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    with config.log_path.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


def request_json(
    config: FlowConfig,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{config.base_url}{path}", data=body, headers=headers, method=method)
    started = time.monotonic()
    log(config, f"HTTP {method} {path} started")
    gateway_log = config.output_dir / "gateway.log"
    progress_note = f"watch gateway log: {gateway_log}"
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_read_response, request, config.request_timeout_s)
            while True:
                elapsed = time.monotonic() - started
                if elapsed >= config.request_timeout_s:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise RuntimeError(
                        f"{method} {path} timed out after {elapsed:.1f}s; {progress_note}"
                    )
                try:
                    wait_s = min(
                        config.progress_interval_s,
                        max(0.1, config.request_timeout_s - elapsed),
                    )
                    data = future.result(timeout=wait_s)
                    break
                except concurrent.futures.TimeoutError:
                    elapsed = time.monotonic() - started
                    log(
                        config,
                        f"HTTP {method} {path} still running after {elapsed:.1f}s; "
                        f"{progress_note}",
                    )
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"{method} {path} failed: {error}") from error
    elapsed = time.monotonic() - started
    log(config, f"HTTP {method} {path} completed in {elapsed:.1f}s")
    if not data:
        return {}
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{method} {path} returned non-object JSON")
    return parsed


def _read_response(request: Request, timeout_s: int) -> bytes:
    with urlopen(request, timeout=timeout_s) as response:
        return response.read()


def login(config: FlowConfig) -> str:
    response = request_json(
        config,
        "POST",
        "/auth/login",
        {"username": config.username, "password": config.password},
    )
    token = response.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("login response did not include access_token")
    return token


def create_run(config: FlowConfig, token: str) -> dict[str, Any]:
    return request_json(
        config,
        "POST",
        "/run",
        {
        "raw_request": (
            "Tạo một lesson Toán lớp 5 bằng tiếng Việt về phân số tương đương, "
            "dùng rich UI components và HTML templates."
        ),
            "artifact_types": ["lesson"],
            "class_info": {
                "grade": 5,
                "subject": "math",
                "student_count": 32,
                "language": "vi",
            },
            "teacher_id": "t-001",
        },
        token,
    )


def approve(config: FlowConfig, token: str, run_id: str) -> dict[str, Any]:
    return request_json(config, "POST", f"/run/{run_id}/approve", {"action": "approve"}, token)


def get_run(config: FlowConfig, token: str, run_id: str) -> dict[str, Any]:
    return request_json(config, "GET", f"/run/{run_id}", token=token)


def write_outputs(
    config: FlowConfig,
    run: dict[str, Any],
    snapshots: dict[str, Any],
) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    state = run.get("state")
    if not isinstance(state, dict):
        raise RuntimeError("run response did not include state")
    artifacts_value = state.get("artifacts")
    artifacts: list[Any] = artifacts_value if isinstance(artifacts_value, list) else []
    exported_files_value = state.get("exported_files")
    exported_files: list[Any] = (
        exported_files_value if isinstance(exported_files_value, list) else []
    )
    (config.output_dir / "live_run_snapshots.json").write_text(
        json.dumps(
            snapshots, ensure_ascii=False, indent=2, default=str,
        ),
        encoding="utf-8",
    )
    (config.output_dir / "run_state.json").write_text(
        json.dumps(
            state, ensure_ascii=False, indent=2, default=str,
        ),
        encoding="utf-8",
    )
    (config.output_dir / "artifacts.json").write_text(
        json.dumps(artifacts, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    summary: dict[str, Any] = {
        "run_id": run.get("run_id"),
        "status": run.get("status"),
        "current_step": run.get("current_step"),
        "artifact_count": len(artifacts),
        "export_count": len(exported_files),
        "quality_scores": state.get("quality_scores"),
        "judge_score": state.get("judge_score"),
        "fail_context": state.get("fail_context"),
        "exported_files": [],
    }
    for index, exported_file in enumerate(exported_files):
        if not isinstance(exported_file, dict):
            continue
        artifact_type = str(exported_file.get("artifact_type") or f"artifact-{index}")
        content = str(exported_file.get("content") or "")
        path = config.output_dir / f"artifact-{index}-{artifact_type}.html"
        path.write_text(content, encoding="utf-8")
        summary["exported_files"].append({
            "artifact_id": exported_file.get("artifact_id"),
            "artifact_type": artifact_type,
            "title": exported_file.get("title"),
            "path": str(path),
            "bytes": len(content.encode("utf-8")),
            "contains_oh_my_class": "oh-my-class" in content,
            "contains_external_http": "http://" in content or "https://" in content,
        })
    (config.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    config = parse_args()
    if config.run_id is None:
        config.log_path.write_text("", encoding="utf-8")
    log(config, "live flow runner started")
    token = login(config)
    log(config, "login ok")
    if config.run_id is None:
        created = create_run(config, token)
        run_id = created.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("create run response did not include run_id")
        log(config, f"run created: {run_id} status={created.get('status')}")
        snapshots: dict[str, Any] = {"created": created}
    else:
        run_id = config.run_id
        created = get_run(config, token, run_id)
        log(config, f"run resumed: {run_id} status={created.get('status')}")
        snapshots = {"resumed": created}
    if created.get("status") == "awaiting_approval":
        log(config, "approving blueprint gate")
        snapshots["blueprint_approval"] = approve(config, token, run_id)
    after_blueprint = get_run(config, token, run_id)
    snapshots["after_blueprint"] = after_blueprint
    log(config, f"after blueprint status={after_blueprint.get('status')}")
    if after_blueprint.get("status") == "awaiting_content_approval":
        log(config, "approving content gate")
        snapshots["content_approval"] = approve(config, token, run_id)
    final_run = get_run(config, token, run_id)
    snapshots["final"] = final_run
    summary = write_outputs(config, final_run, snapshots)
    log(config, f"final status={summary.get('status')} exports={summary.get('export_count')}")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        fallback_config = parse_args()
        log(fallback_config, f"runner failed: {error}")
        raise
