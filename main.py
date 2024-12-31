# gh-top-projects/main.py
import argparse
import csv
import os

import requests


def search_github_repos(
    language, min_stars, max_stars, min_forks=0, per_page=100, token=None
):
    """Search github repos."""
    url = "https://api.github.com/search/repositories"
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    params = {
        "q": f"language:{language} stars:{min_stars}..{max_stars} forks:>{min_forks}",
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        repos = response.json().get("items", [])
        return [
            {
                "name": repo["name"],
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "url": repo["html_url"],
                "description": repo["description"],
            }
            for repo in repos
        ]
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []


def save_repos_to_csv(repos, output_file):
    """Save repos to csv."""
    with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=["name", "stars", "forks", "url", "description"]
        )
        writer.writeheader()
        writer.writerows(repos)


def main():
    """Driver module."""
    parser = argparse.ArgumentParser(
        description="Search GitHub repositories by language, stars, and forks."
    )
    parser.add_argument(
        "--language", required=True, help="Programming language to filter by."
    )
    parser.add_argument(
        "--min-stars", type=int, required=True, help="Minimum number of stars."
    )
    parser.add_argument(
        "--max-stars", type=int, required=True, help="Maximum number of stars."
    )
    parser.add_argument(
        "--min-forks", type=int, default=0, help="Minimum number of forks (default: 0)."
    )
    parser.add_argument(
        "--output",
        default="github_repos.csv",
        help="Output CSV file (default: github_repos.csv).",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub Personal Access Token (optional).",
    )
    args = parser.parse_args()

    repos = search_github_repos(
        language=args.language,
        min_stars=args.min_stars,
        max_stars=args.max_stars,
        min_forks=args.min_forks,
        token=args.token,
    )

    if repos:
        save_repos_to_csv(repos, args.output)
        print(f"Saved {len(repos)} repositories to {args.output}.")
    else:
        print("No repositories found.")


if __name__ == "__main__":
    main()
