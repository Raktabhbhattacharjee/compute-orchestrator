import httpx

BASE_URL = "http://127.0.0.1:8000"
WORKER_ID = "chef-priority"


def log(msg):
    print(f"\n{'='*40}")
    print(msg)
    print("=" * 40)


def create_job(name: str, priority: int) -> dict:
    response = httpx.post(f"{BASE_URL}/jobs", json={"name": name, "priority": priority})
    return response.json()


def claim_job() -> dict | None:
    response = httpx.post(f"{BASE_URL}/jobs/claim", headers={"X-Worker-Id": WORKER_ID})
    if response.status_code == 204:
        return None
    return response.json()


def reap() -> int:
    response = httpx.post(f"{BASE_URL}/jobs/reap")
    return response.json()["recovered"]


def complete_job(job_id: int) -> None:
    httpx.patch(
        f"{BASE_URL}/jobs/{job_id}/status",
        json={"status": "succeeded"},
        headers={"X-Worker-Id": WORKER_ID},
    )


def main():
    # Step 1 - Clean up any stuck running jobs first
    recovered = reap()
    log(f"🧹 Cleaned up {recovered} stuck jobs before test")

    # Step 2 - Create 3 jobs in random priority order
    log("Creating 3 jobs in random priority order...")
    test_jobs = [
        {"name": "low-priority-job", "priority": 1},
        {"name": "high-priority-job", "priority": 10},
        {"name": "medium-priority-job", "priority": 5},
    ]

    created = []
    for job_data in test_jobs:
        job = create_job(job_data["name"], job_data["priority"])
        created.append(job)
        print(
            f"  Created → {job['name']} | priority: {job['priority']} | id: {job['id']}"
        )

    # Step 3 - Claim jobs and check order
    log("Claiming jobs — should come out highest priority first...")
    expected_order = ["high-priority-job", "medium-priority-job", "low-priority-job"]
    actual_order = []
    claimed_ids = []

    for i in range(1, 4):
        job = claim_job()
        if job is None:
            print(f"  Claim {i}: ❌ No queued jobs available — something went wrong")
            break
        actual_order.append(job["name"])
        claimed_ids.append(job["id"])
        print(
            f"  Claim {i}: {job['name']} | priority: {job['priority']} | id: {job['id']}"
        )

    # Step 4 - Complete all claimed jobs (clean up)
    for job_id in claimed_ids:
        complete_job(job_id)

    # Step 5 - Verify order
    log("Results:")
    if actual_order == expected_order:
        print("✅ Priority queue works correctly!")
        print(f"   Order: {' → '.join(actual_order)}")
    else:
        print("❌ Priority queue order is wrong")
        print(f"   Expected: {' → '.join(expected_order)}")
        print(f"   Got:      {' → '.join(actual_order)}")


if __name__ == "__main__":
    main()
