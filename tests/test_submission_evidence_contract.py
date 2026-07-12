from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SPEC = ROOT / "SPEC.md"
SPEC_PROCESS = ROOT / "SPEC_PROCESS.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_readme_records_latest_ci_and_public_registry_evidence() -> None:
    text = read(README)

    assert "76fb6ed" in text
    assert "https://github.com/alex-guth/coding_agent/actions/runs/29190758993" in text
    assert "docker-publish" in text
    assert "ghcr.io/alex-guth/coding_agent:latest" in text
    assert "sha256:87fec731548672e54279e63dd6f91a2e19e059503580e242a7bcf1bdd4192819" in text


def test_spec_process_no_longer_lists_public_registry_as_pending() -> None:
    text = read(SPEC_PROCESS)

    assert "public docker registry publication still requires" not in text
    assert "ghcr.io/alex-guth/coding_agent:latest" in text
    assert "29190758993" in text


def test_spec_scopes_real_provider_credential_cli_as_post_mvp() -> None:
    text = read(SPEC)

    assert "safe-repair credentials status" in text
    assert "safe-repair credentials set" in text
    assert "safe-repair credentials clear" in text
    assert "post-mvp real-provider credential cli" in text
    assert "mock/demo delivery does not require these credential cli commands" in text
