from pathlib import Path

from scripts.check_d0019_materialization_readiness import (
    namespace_fingerprint,
    readiness,
)


def test_valid_secret_fingerprint_is_deterministic_and_not_secret():
    secret=b"0123456789abcdef0123456789ABCDEF"
    first=namespace_fingerprint(secret)
    second=namespace_fingerprint(secret)
    assert first==second
    assert len(first)==64
    assert secret.decode() not in first


def test_readiness_never_emits_secret_and_accepts_external_local_output(tmp_path):
    repo=Path(".").resolve()
    secret=b"correct-horse-battery-staple-ARS-2026"
    output=tmp_path/"restricted_materialization"
    result=readiness(repo_root=repo,output_dir=output,secret=secret)
    assert result["checks"]["secret_configured"] is True
    assert result["checks"]["secret_minimum_bytes"] is True
    assert result["checks"]["output_outside_repository"] is True
    assert result["checks"]["output_not_common_sync_folder"] is True
    assert result["secret_value_emitted"] is False
    assert secret.decode() not in str(result)


def test_missing_or_short_secret_holds(tmp_path):
    repo=Path(".").resolve()
    result=readiness(repo_root=repo,output_dir=tmp_path/"safe",secret=b"short")
    assert result["ready"] is False
    assert result["state"]=="HELD_MATERIALIZATION_READINESS"
    assert result["checks"]["secret_minimum_bytes"] is False


def test_output_inside_repo_is_rejected():
    repo=Path(".").resolve()
    result=readiness(
        repo_root=repo,
        output_dir=repo/"build"/"restricted",
        secret=b"0123456789abcdef0123456789ABCDEF",
    )
    assert result["ready"] is False
    assert result["checks"]["output_outside_repository"] is False


def test_common_cloud_sync_output_is_rejected(tmp_path):
    repo=Path(".").resolve()
    result=readiness(
        repo_root=repo,
        output_dir=tmp_path/"GoogleDrive"/"restricted",
        secret=b"0123456789abcdef0123456789ABCDEF",
    )
    assert result["ready"] is False
    assert result["checks"]["output_not_common_sync_folder"] is False


def test_obvious_low_diversity_secret_is_rejected(tmp_path):
    repo=Path(".").resolve()
    result=readiness(
        repo_root=repo,
        output_dir=tmp_path/"safe",
        secret=b"A"*32,
    )
    assert result["ready"] is False
    assert result["checks"]["secret_obvious_placeholder"] is True
