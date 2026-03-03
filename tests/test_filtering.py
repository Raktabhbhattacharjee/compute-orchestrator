import httpx

BASE_URL = "http://127.0.0.1:8000"


def log(msg):
    print(f"\n{'='*40}")
    print(msg)
    print("="*40)


def main():
    # Test 1 - No filter, default pagination
    response = httpx.get(f"{BASE_URL}/jobs")
    jobs = response.json()
    log(f"No filter | got {len(jobs)} jobs (limit 10 default)")

    # Test 2 - Filter by status
    response = httpx.get(f"{BASE_URL}/jobs?status=queued")
    jobs = response.json()
    log(f"Filter status=queued | got {len(jobs)} jobs")
    for job in jobs:
        print(f"  id: {job['id']} | status: {job['status']}")

    # Test 3 - Filter by succeeded
    response = httpx.get(f"{BASE_URL}/jobs?status=succeeded")
    jobs = response.json()
    log(f"Filter status=succeeded | got {len(jobs)} jobs")

    # Test 4 - Pagination
    response = httpx.get(f"{BASE_URL}/jobs?page=1&limit=3")
    jobs = response.json()
    log(f"Page 1, limit 3 | got {len(jobs)} jobs")
    for job in jobs:
        print(f"  id: {job['id']}")

    response = httpx.get(f"{BASE_URL}/jobs?page=2&limit=3")
    jobs = response.json()
    log(f"Page 2, limit 3 | got {len(jobs)} jobs")
    for job in jobs:
        print(f"  id: {job['id']}")


if __name__ == "__main__":
    main()