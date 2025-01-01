import argparse
import csv
import os
from datetime import datetime, timedelta

import requests


# Default GitHub API headers with optional token
def get_headers():
    """Get headers."""
    token = os.getenv("GITHUB_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def get_repo_count(language, min_stars, max_stars, min_forks):
    """Get the total count of repositories matching the query."""
    url = "https://api.github.com/search/repositories"
    params = {
        "q": f"language:{language} stars:{min_stars}..{max_stars} forks:>={min_forks}",
    }

    response = requests.get(url, headers=get_headers(), params=params)
    log_rate_limit_info(response)  # Log rate limit information

    if response.status_code == 200:
        return response.json().get("total_count", 0)
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return 0


def display_final_rate_limit():
    """Display final rate limit information after processing."""
    url = "https://api.github.com/rate_limit"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        rate_limit = response.json().get("rate", {})
        remaining = rate_limit.get("remaining", "unknown")
        limit = rate_limit.get("limit", "unknown")
        reset_time = rate_limit.get("reset")
        if reset_time:
            reset_time = datetime.fromtimestamp(int(reset_time)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        print(f"\nFinal API Rate Limit: {remaining}/{limit} requests remaining.")
        print(f"Rate limit resets at: {reset_time}")
    else:
        print("\nUnable to fetch final rate limit information.")


def log_rate_limit_info(response):
    """Log API rate limit information from response headers."""
    limit = response.headers.get("X-RateLimit-Limit", "unknown")
    remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
    reset_time = response.headers.get("X-RateLimit-Reset")

    if reset_time:
        reset_time = datetime.fromtimestamp(int(reset_time)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    print(
        f"API Rate Limit: {remaining}/{limit} requests remaining. Limit resets at: {reset_time}"  # noqa: E501
    )


def fetch_repositories(language, min_stars, max_stars, min_forks):
    """Fetch all repositories matching the query."""
    url = "https://api.github.com/search/repositories"
    params = {
        "q": f"language:{language} stars:{min_stars}..{max_stars} forks:>={min_forks}",
        "sort": "stars",
        "order": "desc",
        "per_page": 100,  # Max items per page
    }

    all_repos = []
    page = 1

    while True:
        params["page"] = page
        response = requests.get(url, headers=get_headers(), params=params)
        if response.status_code == 200:
            repos = response.json().get("items", [])
            all_repos.extend(repos)
            print(f"Fetched {len(all_repos)} repositories so far...")
            if len(repos) < 100:  # End of pages
                break
            page += 1
        else:
            print(f"Error: {response.status_code} - {response.text}")
            break

    return all_repos


def fetch_additional_details(repo):
    """Fetch additional details (contributors count, recent commits) of repository."""
    headers = get_headers()
    details = {
        "contributors_count": 0,
        "commits_last_3_months": 0,
    }

    # Fetch contributors count
    try:
        contributors_url = repo["contributors_url"]
        contributors_response = requests.get(
            contributors_url, headers=headers, timeout=10
        )
        if contributors_response.status_code == 200:
            details["contributors_count"] = len(contributors_response.json())
    except Exception as e:
        print(f"Error fetching contributors for {repo['name']}: {e}")

    # Fetch recent commits
    try:
        commits_url = repo["commits_url"].replace("{/sha}", "")
        since = (datetime.now() - timedelta(days=90)).isoformat()
        commits_response = requests.get(
            commits_url, headers=headers, params={"since": since}, timeout=10
        )
        if commits_response.status_code == 200:
            details["commits_last_3_months"] = len(commits_response.json())
    except Exception as e:
        print(f"Error fetching commits for {repo['name']}: {e}")

    return details


def save_to_csv(repos, output_file):
    """Save repository data to a CSV file."""
    fieldnames = [
        "name",
        "stars",
        "forks",
        "url",
        "description",
        "archived",
        "contributors_count",
        "commits_last_3_months",
    ]

    with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for repo in repos:
            writer.writerow(repo)


def main():
    """Drive application."""
    parser = argparse.ArgumentParser(description="Fetch and save GitHub repositories.")
    parser.add_argument(
        "--language", required=True, help="Programming language to filter by."
    )
    parser.add_argument(
        "--min-stars", type=int, required=True, help="Minimum stars for repositories."
    )
    parser.add_argument(
        "--max-stars", type=int, required=True, help="Maximum stars for repositories."
    )
    parser.add_argument(
        "--min-forks", type=int, default=0, help="Minimum forks for repositories."
    )
    parser.add_argument(
        "--output",
        help="Output CSV file. If not specified, a file name will be generated.",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Display the total count of repositories matching the query.",
    )

    args = parser.parse_args()

    # Determine the output file name
    if not args.output:
        args.output = (
            f"{args.language}_repos_{args.min_stars}-{args.max_stars}_stars.csv"
        )

    # Step 1: Get repository count if --count is provided
    total_count = get_repo_count(
        args.language, args.min_stars, args.max_stars, args.min_forks
    )
    if args.count:
        print(f"Total repositories matching the query: {total_count}")
        return

    # Step 2: Fetch repositories
    print("Fetching repositories...")
    repos = fetch_repositories(
        args.language, args.min_stars, args.max_stars, args.min_forks
    )
    if not repos:
        print("No repositories found. Exiting...")
        return

    # Step 3: Fetch additional details and process repositories
    print("Processing repositories...")
    detailed_repos = []
    for index, repo in enumerate(repos, start=1):
        details = fetch_additional_details(repo)
        detailed_repo = {
            "name": repo["name"],
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "url": repo["html_url"],
            "description": repo["description"],
            "archived": repo["archived"],
            "contributors_count": details["contributors_count"],
            "commits_last_3_months": details["commits_last_3_months"],
        }
        detailed_repos.append(detailed_repo)
        print(f"Processed {index}/{len(repos)} repositories...", end="\r")

    # Step 4: Save to CSV
    print(f"\nSaving data to {args.output}...")
    save_to_csv(detailed_repos, args.output)
    print("Completed processing. Data saved successfully!")

    # Display final rate limit details
    display_final_rate_limit()


if __name__ == "__main__":
    main()
