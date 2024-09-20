import requests
from typing import Tuple, Optional, Dict, Any
import json
import asyncio
from aiohttp import ClientSession
from dotenv import load_dotenv
import os

load_dotenv()
APIKEY = os.getenv("APIKEY")
BASEURL = os.getenv("BASEURL")


async def get_repo_data(BASEURL: str) -> dict:
    async with ClientSession() as session:
        async with session.get(BASEURL) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(
                    f"Failed to retrieve repository data. Status code: {response.status}"
                )
                return None


# Async requests with aiohttp, as introduced in
# https://towardsdev.com/multithreaded-http-requests-in-python-453f07db98e1
async def http_get_with_aiohttp(
    session, params, url, headers={}, proxy=None, timeout=10
) -> Tuple[Optional[int], Optional[Dict[str, Any]], Optional[bytes]]:
    try:
        response = await session.get(
            url=url, params=params, headers=headers, proxy=proxy, timeout=timeout
        )
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return (response.status, None, None)

    if response.status == 200:
        response_json = None

        try:
            response_json = await response.json(content_type=None)
        except json.decoder.JSONDecodeError as e:
            print(f"JSON decode error for {url}: {e}")

        response_content = None

        try:
            response_content = await response.read()
        except Exception as e:
            print(f"Failed to read content for {url}: {e}")

        return (response.status, response_json, response_content)
    else:
        print(f"Failed to retrieve data. Status code: {response.status}")
        return (response.status, None, None)


# Parallel data fetching for muh effieciency
async def get_entries_of_type_parallel(
    session: ClientSession, BASEURL, type, state=None
) -> list:
    url = f"{BASEURL}/{type}"
    all_entries = []
    pages = 1

    headers = {
        "Authorization": f"Bearer {APIKEY}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Github-Scraper",
    }

    empty_page_found = False

    while True:
        urls = []

        for i in range(pages, pages + 10):
            params = {"page": i}
            if state:
                params["state"] = state
            urls.append((url, params))

        result_pages = await asyncio.gather(
            *[
                http_get_with_aiohttp(
                    session=session, url=url, headers=headers, params=params
                )
                for url, params in urls
            ]
        )

        for page in result_pages:
            if page[0] != 200 or not page[1]:
                empty_page_found = True
            else:
                all_entries.extend(page[1])

        if not empty_page_found:
            pages += 10
        else:
            break

    return all_entries


# Non-parallel function for data retrieval
async def get_entries_of_type(BASEURL, type, state=None):
    url = f"{BASEURL}/{type}"
    all_entries = []
    page = 1

    headers = {
        "Authorization": f"Bearer {APIKEY}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Github-Scraper",
    }

    while True:
        params = {"page": page}

        if state:
            params["state"] = state

        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()

            if not data:
                break

            all_entries.extend(data)
            page += 1
        else:
            print(
                f"Failed to retrieve {type} data. HTTP Status code: {response.status_code}"
            )
            break

    return all_entries


async def main():
    repo_data = await get_repo_data(BASEURL)

    if repo_data:
        print("Repository Info:")
        print(f"ID: {repo_data['id']}")
        print(f"Node ID: {repo_data['node_id']}")
        print(f"Name: {repo_data['name']}")
        print(f"Full name: {repo_data['full_name']}")
        print(f"Language: {repo_data['language']}")
        print(f"Private: {repo_data['private']}")

    async with ClientSession() as session:
        all_commits = await get_entries_of_type_parallel(session, BASEURL, "commits")

        open_issues = await get_entries_of_type_parallel(
            session, BASEURL, "issues", state="open"
        )

        closed_issues = await get_entries_of_type_parallel(
            session, BASEURL, "issues", state="closed"
        )

        contributors = await get_entries_of_type_parallel(
            session, BASEURL, "contributors"
        )

        if contributors:
            print(f"No. of contributors: {len(contributors)}")

        if open_issues:
            print(f"Open issues: {len(open_issues)}")

        if closed_issues:
            print(f"Closed issues: {len(closed_issues)}")

        if all_commits:
            print(f"Total commits: {len(all_commits)}\n")


asyncio.run(main())
