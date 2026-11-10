"""Render a GitHub stats card (light + dark SVG) from the GraphQL API.

Usage: GITHUB_TOKEN=... python scripts/stats.py <username> <out_dir>
"""
import json
import os
import sys
import urllib.request

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount }
    }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
  }
}
"""

THEMES = {
    "stats.svg": {"bg": "#FFFFFF", "accent": "#0969DA", "text": "#1F2328"},
    "stats-dark.svg": {"bg": "#0D1117", "accent": "#58A6FF", "text": "#C9D1D9"},
}


def gql(token, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as res:
        body = json.load(res)
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


def fetch(token, login):
    stars, after = 0, None
    while True:
        user = gql(token, {"login": login, "after": after})
        repos = user["repositories"]
        stars += sum(r["stargazerCount"] for r in repos["nodes"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]
    cc = user["contributionsCollection"]
    return [
        ("Total stars", stars),
        ("Commits (last year)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("Pull requests", user["pullRequests"]["totalCount"]),
        ("Issues", user["issues"]["totalCount"]),
        ("Contributed to", user["repositoriesContributedTo"]["totalCount"]),
    ]


def render(rows, t):
    lines = "".join(
        f'<text x="25" y="{70 + i * 25}" class="label">{label}:</text>'
        f'<text x="300" y="{70 + i * 25}" class="value">{value:,}</text>'
        for i, (label, value) in enumerate(rows)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-label="GitHub stats">
<style>
  text {{ font-family: 'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif; }}
  .title {{ font-size: 18px; font-weight: 600; fill: {t['accent']}; }}
  .label {{ font-size: 14px; font-weight: 600; fill: {t['text']}; }}
  .value {{ font-size: 14px; font-weight: 700; fill: {t['text']}; }}
</style>
<rect width="495" height="195" rx="4.5" fill="{t['bg']}"/>
<text x="25" y="35" class="title">GitHub Stats</text>
{lines}
</svg>
"""


def main():
    login, out_dir = sys.argv[1], sys.argv[2]
    rows = fetch(os.environ["GITHUB_TOKEN"], login)
    os.makedirs(out_dir, exist_ok=True)
    for name, theme in THEMES.items():
        with open(os.path.join(out_dir, name), "w") as f:
            f.write(render(rows, theme))


if __name__ == "__main__":
    main()
