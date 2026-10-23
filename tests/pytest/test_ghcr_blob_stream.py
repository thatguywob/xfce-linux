"""Unit tests for the resumable GHCR blob downloader."""

import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts" / "ghcr-blob-stream.py"


def _load_stream():
    spec = importlib.util.spec_from_file_location("ghcr_blob_stream", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def stream():
    return _load_stream()


class Response:
    def __init__(self, body, *, status=200):
        self._body = io.BytesIO(body)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        return self._body.read(size)


def _run_main(stream, monkeypatch, argv, *, stdout=None, stderr=None):
    output = stdout or io.BytesIO()
    errors = stderr or io.StringIO()
    monkeypatch.setattr(stream.sys, "argv", argv)
    monkeypatch.setattr(
        stream.sys,
        "stdout",
        SimpleNamespace(buffer=output),
    )
    monkeypatch.setattr(stream.sys, "stderr", errors)
    return output, errors


def test_basic_auth_reads_explicit_docker_config(stream, monkeypatch, tmp_path):
    config_dir = tmp_path / "docker"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps({"auths": {"https://ghcr.io": {"auth": "encoded"}}})
    )
    monkeypatch.setenv("DOCKER_CONFIG", str(config_dir))
    monkeypatch.setattr(stream.os.path, "expanduser", lambda _: str(tmp_path / "missing"))

    assert stream.basic_auth("ghcr.io") == "encoded"


def test_basic_auth_skips_invalid_config_and_uses_runtime_fallback(stream, monkeypatch, tmp_path):
    config_dir = tmp_path / "docker"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("not-json")
    runtime_dir = tmp_path / "runtime"
    (runtime_dir / "containers").mkdir(parents=True)
    (runtime_dir / "containers" / "auth.json").write_text(
        json.dumps({"auths": {"ghcr.io": {"auth": "runtime-auth"}}})
    )
    monkeypatch.setenv("DOCKER_CONFIG", str(config_dir))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))
    monkeypatch.setattr(stream.os.path, "expanduser", lambda _: str(tmp_path / "missing"))

    assert stream.basic_auth("ghcr.io") == "runtime-auth"


def test_bearer_requests_token_with_basic_auth(stream, monkeypatch):
    response = Response(b'{"token": "bearer-token"}')
    request_seen = {}

    def fake_urlopen(request, timeout):
        request_seen["request"] = request
        request_seen["timeout"] = timeout
        return response

    monkeypatch.setattr(stream, "basic_auth", lambda registry: "basic-token")
    monkeypatch.setattr(stream.urllib.request, "urlopen", fake_urlopen)

    assert stream.bearer("ghcr.io", "tuna-os/xfce-linux") == "bearer-token"
    request = request_seen["request"]
    assert request.full_url == (
        "https://ghcr.io/token?service=ghcr.io&scope=repository:tuna-os/xfce-linux:pull"
    )
    assert request.get_header("Authorization") == "Basic basic-token"
    assert request_seen["timeout"] == 60


def test_main_rejects_wrong_argument_count(stream, monkeypatch, capsys):
    monkeypatch.setattr(stream.sys, "argv", ["ghcr-blob-stream.py"])

    assert stream.main() == 2
    assert "Usage: ghcr-blob-stream.py" in capsys.readouterr().err


def test_main_streams_blob_and_verifies_digest(stream, monkeypatch):
    payload = b"blob payload"
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    response = Response(payload)
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return response

    monkeypatch.setattr(stream, "bearer", lambda registry, repo: "token")
    monkeypatch.setattr(stream.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(stream.time, "sleep", mock.Mock())
    output, _ = _run_main(
        stream,
        monkeypatch,
        [
            "ghcr-blob-stream.py",
            "ghcr.io/tuna-os/xfce-linux/cache:latest",
            digest,
            str(len(payload)),
        ],
    )

    assert stream.main() == 0
    assert output.getvalue() == payload
    request, timeout = requests[0]
    assert request.full_url == f"https://ghcr.io/v2/tuna-os/xfce-linux/cache/blobs/{digest}"
    assert request.unredirected_hdrs["Authorization"] == "Bearer token"
    assert timeout == 120


def test_main_resumes_after_connection_cut_with_range(stream, monkeypatch):
    payload = b"resumable payload"
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()

    class CutResponse(Response):
        def __init__(self):
            super().__init__(payload[:8])
            self._cut = False

        def read(self, size=-1):
            if not self._cut:
                self._cut = True
                return super().read(size)
            raise OSError("connection reset")

    requests = []
    responses = [CutResponse(), Response(payload[8:], status=206)]

    def fake_urlopen(request, timeout):
        requests.append(request)
        return responses.pop(0)

    monkeypatch.setattr(stream, "bearer", lambda registry, repo: "token")
    monkeypatch.setattr(stream.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(stream.time, "sleep", mock.Mock())
    output, errors = _run_main(
        stream,
        monkeypatch,
        ["ghcr-blob-stream.py", "ghcr.io/tuna-os/xfce-linux/cache:latest", digest, str(len(payload))],
    )

    assert stream.main() == 0
    assert output.getvalue() == payload
    assert requests[1].get_header("Range") == "bytes=8-"
    assert "connection cut" in errors.getvalue()


def test_main_refreshes_token_after_unauthorized_response(stream, monkeypatch):
    payload = b"authorized after refresh"
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    requests = []
    responses = [stream.urllib.error.HTTPError("url", 401, "expired", {}, None), Response(payload)]
    tokens = iter(["stale", "fresh"])

    def fake_urlopen(request, timeout):
        requests.append(request)
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(stream, "bearer", lambda registry, repo: next(tokens))
    monkeypatch.setattr(stream.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(stream.time, "sleep", mock.Mock())
    output, _ = _run_main(
        stream,
        monkeypatch,
        ["ghcr-blob-stream.py", "ghcr.io/tuna-os/xfce-linux/cache:latest", digest, str(len(payload))],
    )

    assert stream.main() == 0
    assert output.getvalue() == payload
    assert requests[0].unredirected_hdrs["Authorization"] == "Bearer stale"
    assert requests[1].unredirected_hdrs["Authorization"] == "Bearer fresh"


def test_main_rejects_server_that_ignores_resume_range(stream, monkeypatch):
    payload = b"partial"
    digest = "sha256:" + hashlib.sha256(payload + b" tail").hexdigest()
    responses = [Response(payload[:3]), Response(payload[3:], status=200)]

    def fake_urlopen(request, timeout):
        return responses.pop(0)

    monkeypatch.setattr(stream, "bearer", lambda registry, repo: "token")
    monkeypatch.setattr(stream.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(stream.time, "sleep", mock.Mock())
    output, errors = _run_main(
        stream,
        monkeypatch,
        ["ghcr-blob-stream.py", "ghcr.io/tuna-os/xfce-linux/cache:latest", digest, "10"],
    )

    assert stream.main() == 1
    assert output.getvalue() == payload[:3]
    assert "server ignored Range" in errors.getvalue()


def test_main_returns_failure_for_digest_mismatch(stream, monkeypatch):
    payload = b"wrong payload"
    digest = "sha256:" + hashlib.sha256(b"expected payload").hexdigest()
    monkeypatch.setattr(stream, "bearer", lambda registry, repo: "token")
    monkeypatch.setattr(stream.urllib.request, "urlopen", lambda request, timeout: Response(payload))
    output, errors = _run_main(
        stream,
        monkeypatch,
        ["ghcr-blob-stream.py", "ghcr.io/tuna-os/xfce-linux/cache:latest", digest, str(len(payload))],
    )

    assert stream.main() == 1
    assert output.getvalue() == payload
    assert "digest mismatch" in errors.getvalue()


def test_main_stops_after_max_attempts(stream, monkeypatch):
    payload = b"payload"
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(stream, "MAX_ATTEMPTS", 1)
    monkeypatch.setattr(stream, "bearer", lambda registry, repo: "token")
    monkeypatch.setattr(
        stream.urllib.request,
        "urlopen",
        mock.Mock(side_effect=OSError("network down")),
    )
    monkeypatch.setattr(stream.time, "sleep", mock.Mock())
    _, errors = _run_main(
        stream,
        monkeypatch,
        ["ghcr-blob-stream.py", "ghcr.io/tuna-os/xfce-linux/cache:latest", digest, str(len(payload))],
    )

    assert stream.main() == 1
    assert "giving up after 1 attempts" in errors.getvalue()
