"""Guard the remote-execution configuration against silent local fallback."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ACTION = (REPO / ".github/actions/generate-bst-ci-config/action.yml").read_text()
WORKFLOW = (REPO / ".github/workflows/build-and-publish-xfce-linux.yml").read_text()


def test_remote_execution_uses_mtls_for_every_service():
    assert ACTION.count("url: https://cache.projectbluefin.io:11002") >= 5
    assert "client-key: /src/client.key" in ACTION
    assert "client-cert: /src/client.crt" in ACTION
    for service in ("execution-service:", "storage-service:", "action-cache-service:"):
        assert service in ACTION


def test_remote_execution_fails_closed():
    assert "remote execution was requested but CASD client credentials are missing" in ACTION
    assert "Remote Execution Configuration" in WORKFLOW
    assert "remote execution requested but not engaged" in WORKFLOW


def test_credentials_are_removed_even_after_failure():
    cleanup = re.search(
        r"- name: Remove CASD client credentials\n(?P<body>(?:\s+.*\n)+)", WORKFLOW
    )
    assert cleanup
    assert "if: always()" in cleanup.group("body")
    assert "rm -f client.key client.crt" in cleanup.group("body")



def test_local_only_config_keeps_runner_defaults():
    assert "BUILDERS=12" in ACTION
    assert "logdir: /src/logs" in ACTION
