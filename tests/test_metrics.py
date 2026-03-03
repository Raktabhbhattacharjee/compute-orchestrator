import httpx

BASE_URL = "http://127.0.0.1:8000"

def main():
    response = httpx.get(f"{BASE_URL}/jobs/metrics")
    metrics = response.json()

    print("\n" + "="*40)
    print("Kitchen Dashboard")
    print("="*40)
    print(f"Queued:    {metrics['queued']}")
    print(f"Running:   {metrics['running']}")
    print(f"Succeeded: {metrics['succeeded']}")
    print(f"Failed:    {metrics['failed']}")
    print(f"Exhausted: {metrics['exhausted']}")
    print(f"Total:     {metrics['total']}")
    print(f"Avg Time:  {metrics['avg_processing_time_seconds']}s")
    print("="*40)

if __name__ == "__main__":
    main()