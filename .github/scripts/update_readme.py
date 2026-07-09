import json
import os
import urllib.request

START_MARKER = "<!-- START:REPO-CARDS -->"
END_MARKER = "<!-- END:REPO-CARDS -->"
README_PATH = "README.md"

DESCRIPTION_OVERRIDES = {
    "azure-firewall-policy-export-rollback": "Azure Firewall Policy export, backup, validation, and rollback tooling for safer policy changes.",
}


def should_skip_repo(name: str, full_name: str, user: str) -> bool:
    # Never list profile infrastructure repos in the portfolio section.
    skip_names = {
        user.lower(),
        f"{user.lower()}.github.io",
    }
    skip_full_names = {
        f"{user.lower()}/{user.lower()}",
        f"{user.lower()}/{user.lower()}.github.io",
    }

    return name.lower() in skip_names or full_name.lower() in skip_full_names


def fetch_public_repos(user: str, token: str | None) -> list[dict]:
    repos: list[dict] = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{user}/repos"
            f"?type=public&sort=updated&direction=desc&per_page=100&page={page}"
        )
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")

        if token:
            req.add_header("Authorization", f"Bearer {token}")

        with urllib.request.urlopen(req) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not payload:
            break

        repos.extend(payload)
        page += 1

    return repos


def render_repo_cards(repos: list[dict], user: str) -> str:
    lines: list[str] = [START_MARKER, ""]

    for repo in repos:
        name = repo.get("name", "")
        if not name:
            continue

        full_name = repo.get("full_name", f"{user}/{name}")

        if should_skip_repo(name, full_name, user):
            continue

        url = repo.get("html_url", f"https://github.com/{user}/{name}")
        description = (
            DESCRIPTION_OVERRIDES.get(name)
            or (repo.get("description") or "Public repository.")
        ).strip()
        description = " ".join(description.split())

        lines.append(f"### [{name}]({url})")
        lines.append(description)
        lines.append("")

    # Remove trailing blank line before the end marker.
    if lines and lines[-1] == "":
        lines.pop()

    lines.append(END_MARKER)
    return "\n".join(lines)


def update_readme(readme_text: str, replacement_block: str) -> str:
    start = readme_text.find(START_MARKER)
    end = readme_text.find(END_MARKER)

    if start == -1 or end == -1 or end < start:
        raise ValueError("README markers not found or out of order")

    end += len(END_MARKER)
    return readme_text[:start] + replacement_block + readme_text[end:]


def main() -> int:
    user = (
        os.getenv("GH_PROFILE_USER")
        or os.getenv("GITHUB_REPOSITORY_OWNER")
        or "colinweiner111"
    )
    if not user:
        raise ValueError("Unable to determine GitHub username")

    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")

    repos = fetch_public_repos(user, token)
    block = render_repo_cards(repos, user)

    with open(README_PATH, "r", encoding="utf-8") as f:
        original = f.read()

    updated = update_readme(original, block)

    if updated != original:
        with open(README_PATH, "w", encoding="utf-8", newline="\n") as f:
            f.write(updated)
        print("README updated")
    else:
        print("README already up to date")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
