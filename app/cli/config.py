from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from services.extract import LangExtractConfig


@dataclass
class RepoConfig:
    id: str
    url: str
    size: str = "small"
    adr_dir: str = "docs/adr"
    adr_repo: str | None = None


@dataclass
class GlobalConfig:
    repos: list[RepoConfig] = field(default_factory=list)
    langextract: LangExtractConfig = field(default_factory=LangExtractConfig)

    def get_repo(self, repo_id: str) -> RepoConfig:
        for repo in self.repos:
            if repo.id == repo_id:
                return repo
        raise ValueError(f"Unknown repo: {repo_id!r}. Available: {[r.id for r in self.repos]}")


def load_config(path: Path | None = None) -> GlobalConfig:
    if path is None:
        path = Path(__file__).resolve().parents[2] / "repos" / "repos.yaml"

    with open(path) as f:
        data = yaml.safe_load(f)

    repos = [
        RepoConfig(
            id=repo["id"],
            url=repo.get("url", f"./{repo['id']}"),
            size=repo.get("size", "small"),
            adr_dir=repo.get("adr_dir", "docs/adr"),
            adr_repo=repo.get("adr_repo"),
        )
        for repo in data.get("repos", [])
    ]

    langextract_data = data.get("langextract", {})
    langextract_config = LangExtractConfig.from_dict(langextract_data or {})

    return GlobalConfig(
        repos=repos,
        langextract=langextract_config,
    )