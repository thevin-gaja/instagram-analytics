import json
from github import Github


def get_repo(token: str, repo_name: str):
    """Return a PyGithub Repository object."""
    return Github(token).get_repo(repo_name)


def load_cache(repo) -> tuple[dict, str]:
    """Read metrics_cache.json from GitHub. Returns (data, sha)."""
    contents = repo.get_contents("metrics_cache.json")
    data = json.loads(contents.decoded_content.decode())
    return data, contents.sha


def save_cache(repo, data: dict, sha: str, message: str) -> None:
    """Write metrics_cache.json to GitHub as a new commit."""
    repo.update_file(
        "metrics_cache.json",
        message,
        json.dumps(data, indent=2),
        sha,
    )
