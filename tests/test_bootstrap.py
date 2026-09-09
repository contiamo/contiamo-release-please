"""Tests for the bootstrap command's file generation."""

import os

import pytest
import yaml

from contiamo_release_please.bootstrap import bootstrap_flavour


def test_bootstrap_bitbucket_creates_files(tmp_path):
    created, instructions = bootstrap_flavour("bitbucket", base_path=tmp_path)

    expected = {
        tmp_path / "contiamo-release-please.yaml",
        tmp_path / "bitbucket-pipelines.yml",
        tmp_path / ".bitbucket" / "scripts" / "validate-pr-title.sh",
        tmp_path / ".bitbucket" / "README-CI-SETUP.md",
    }
    assert set(created) == expected
    for path in expected:
        assert path.exists(), path

    script = tmp_path / ".bitbucket" / "scripts" / "validate-pr-title.sh"
    assert os.access(script, os.X_OK)
    assert script.read_text().startswith("#!/bin/sh")

    assert "BITBUCKET_TOKEN" in instructions
    assert "repository:write" in instructions
    assert "pullrequest:write" in instructions


def test_bootstrap_bitbucket_pipelines_yaml_is_valid(tmp_path):
    bootstrap_flavour("bitbucket", base_path=tmp_path)
    content = (tmp_path / "bitbucket-pipelines.yml").read_text()
    data = yaml.safe_load(content)

    assert data["clone"]["depth"] == "full"
    assert "main" in data["pipelines"]["branches"]
    assert "**" in data["pipelines"]["pull-requests"]

    release_script = "\n".join(data["pipelines"]["branches"]["main"][0]["step"]["script"])
    assert "--git-host bitbucket" in release_script
    assert "tag-release" in release_script
    assert "x-token-auth:${BITBUCKET_TOKEN}" in release_script
    assert "Merged in release-please--branches--main" in release_script

    pr_script = "\n".join(data["pipelines"]["pull-requests"]["**"][0]["step"]["script"])
    assert ".bitbucket/scripts/validate-pr-title.sh" in pr_script


def test_bootstrap_bitbucket_dry_run_writes_nothing(tmp_path):
    created, _ = bootstrap_flavour("bitbucket", base_path=tmp_path, dry_run=True)
    assert len(created) == 4
    assert list(tmp_path.iterdir()) == []


def test_bootstrap_config_template_mentions_bitbucket(tmp_path):
    bootstrap_flavour("github", base_path=tmp_path)
    config = (tmp_path / "contiamo-release-please.yaml").read_text()
    assert "BITBUCKET_TOKEN" in config
    # Generated config must still load as YAML
    assert yaml.safe_load(config)["release-rules"]["minor"] == ["feat"]


def test_bootstrap_unknown_flavour(tmp_path):
    with pytest.raises(ValueError, match="Unknown flavour"):
        bootstrap_flavour("svn", base_path=tmp_path)  # type: ignore[arg-type]
