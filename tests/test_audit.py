import httpx
import time

BASE_URL = "http://127.0.0.1:8000"
WORKER_ID = "chef-audit"


def log(msg):
    print(f"\n{'='*40}")
    print(msg)
    print("="*40)


def main():
    # Step 1 - Create a fresh job with high priority so it gets claimed first
    response = httpx.post(
        f"{BASE_URL}/jobs",
        json={"name": "audit-test", "priority": 99}
    )
    job = response.json()
    job_id = job["id"]
    log(f"✅ Created job {job_id} with priority 99")

    # Step 2 - Claim it — priority 99 guarantees this job gets picked
    response = httpx.post(
        f"{BASE_URL}/jobs/claim",
        headers={"X-Worker-Id": WORKER_ID}
    )
    claimed = response.json()
    claimed_id = claimed["id"]
    log(f"👨‍🍳 Claimed job {claimed_id} by {WORKER_ID}")

    if claimed_id != job_id:
        print(f"⚠️  Warning: claimed job {claimed_id} instead of {job_id}")

    # Step 3 - Complete it
    httpx.patch(
        f"{BASE_URL}/jobs/{claimed_id}/status",
        json={"status": "succeeded"},
        headers={"X-Worker-Id": WORKER_ID}
    )
    log(f"✅ Marked job {claimed_id} succeeded")

    time.sleep(1)

    # Step 4 - Get full history
    response = httpx.get(f"{BASE_URL}/jobs/{claimed_id}/history")
    events = response.json()

    log(f"📋 Full history of job {claimed_id}:")
    if not events:
        print("  ❌ No events found")
    for event in events:
        print(f"  {event['created_at']} | {event['from_status']} → {event['to_status']} | actor: {event['actor']}")

    # Step 5 - Verify we got all 3 events
    print(f"\n{'='*40}")
    if len(events) == 3:
        print("✅ Audit trail works — 3 events recorded correctly")
    else:
        print(f"❌ Expected 3 events, got {len(events)}")
    print("="*40)


if __name__ == "__main__":
    main()