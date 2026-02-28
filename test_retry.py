import httpx
import time

BASE_URL = "http://127.0.0.1:8000"
WORKER_ID = "chef-retry"
WAIT_SECONDS = 35  # slightly over 30 to be safe


def log(msg):
    print(f"\n{'='*40}")
    print(msg)
    print("="*40)


def main():
    # Step 1 - Create fresh job
    response = httpx.post(f"{BASE_URL}/jobs", json={"name": "exhaust-me-auto"})
    job = response.json()
    job_id = job["id"]
    log(f"✅ Created job {job_id} | retry_count: {job['retry_count']} | status: {job['status']}")

    # Rounds - claim, wait, reap, check
    for round_num in range(1, 5):
        log(f"🔄 Round {round_num} starting...")

        # Claim
        response = httpx.post(
            f"{BASE_URL}/jobs/claim",
            headers={"X-Worker-Id": WORKER_ID}
        )
        claimed = response.json()

        if claimed.get("id") != job_id:
            print(f"⚠️  Got job {claimed.get('id')} instead of {job_id} — another job jumped the queue")

        log(f"👨‍🍳 Claimed | status: {claimed.get('status')} | retry_count: {claimed.get('retry_count')}")

        # Wait
        print(f"⏱️  Waiting {WAIT_SECONDS} seconds with no heartbeat...")
        time.sleep(WAIT_SECONDS)

        # Reap
        response = httpx.post(f"{BASE_URL}/jobs/reap")
        log(f"🔍 Reaped | recovered: {response.json()['recovered']}")

        # Check job
        response = httpx.get(f"{BASE_URL}/jobs/{job_id}")
        job = response.json()
        log(f"📋 Job {job_id} | retry_count: {job['retry_count']} | status: {job['status']}")

        # Check if exhausted
        if job["status"] == "exhausted":
            print(f"\n🏁 Job exhausted after {round_num} rounds. Retry mechanism works!")
            break

        if job["status"] == "queued":
            print(f"♻️  Requeued — {job['max_retries'] - job['retry_count']} retries remaining")


if __name__ == "__main__":
    main()