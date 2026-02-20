#!/usr/bin/env python3
"""Load testing harness for ai-resume chat endpoint.

Simulates concurrent chat sessions to validate:
- Stability under load (no 5xx errors)
- Response latency (P50/P95/P99)
- Rate limiting behavior (429 responses)

Usage:
    python scripts/load-test.py [--base-url http://localhost:8000] [--sessions 10] [--messages 5]
"""
import argparse
import json
import statistics
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed


def send_chat_message(base_url: str, message: str, session_id: str | None = None) -> dict:
    """Send a chat message and return timing + status info."""
    url = f"{base_url}/api/v1/chat"
    payload = json.dumps({"message": message, "session_id": session_id}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
            elapsed = time.monotonic() - start
            return {
                "status": resp.status,
                "elapsed": elapsed,
                "session_id": body.get("session_id"),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - start
        return {
            "status": e.code,
            "elapsed": elapsed,
            "session_id": session_id,
            "error": str(e),
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "status": 0,
            "elapsed": elapsed,
            "session_id": session_id,
            "error": str(e),
        }


def run_session(base_url: str, session_num: int, num_messages: int) -> list[dict]:
    """Simulate a single chat session with multiple messages."""
    questions = [
        "What programming languages does the candidate know?",
        "Describe their most recent work experience.",
        "What are their strongest technical skills?",
        "Have they worked with cloud infrastructure?",
        "What leadership experience do they have?",
    ]

    results = []
    session_id = None
    for i in range(num_messages):
        msg = questions[i % len(questions)]
        result = send_chat_message(base_url, msg, session_id)
        if result["session_id"]:
            session_id = result["session_id"]
        result["session_num"] = session_num
        result["message_num"] = i
        results.append(result)
    return results


def percentile(data: list[float], p: int) -> float:
    """Calculate the p-th percentile of a list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])


def wait_for_health(base_url: str, timeout: int = 30) -> bool:
    """Poll service health endpoint until ready or timeout."""
    url = f"{base_url}/api/v1/health"
    start = time.monotonic()
    print(f"Waiting for {url} to become healthy...", end="", flush=True)
    while time.monotonic() - start < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    elapsed = time.monotonic() - start
                    print(f" ready ({elapsed:.0f}s)")
                    return True
        except Exception:
            pass
        time.sleep(2)
    elapsed = time.monotonic() - start
    print(f" TIMEOUT after {elapsed:.0f}s")
    return False


def main():
    parser = argparse.ArgumentParser(description="Load test ai-resume chat endpoint")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--sessions", type=int, default=10, help="Number of concurrent sessions")
    parser.add_argument("--messages", type=int, default=5, help="Messages per session")
    args = parser.parse_args()

    print(f"=== Load Test: {args.sessions} sessions x {args.messages} messages ===")
    print(f"Target: {args.base_url}")
    print()

    # Health-gate: verify service is reachable before load testing
    if not wait_for_health(args.base_url):
        print("FATAL: Service is not healthy. Start the service first.")
        sys.exit(1)
    print()

    all_results = []
    start_time = time.monotonic()

    with ThreadPoolExecutor(max_workers=args.sessions) as executor:
        futures = {
            executor.submit(run_session, args.base_url, i, args.messages): i
            for i in range(args.sessions)
        }
        for future in as_completed(futures):
            results = future.result()
            all_results.extend(results)

    total_time = time.monotonic() - start_time

    # Analyze results
    latencies = [r["elapsed"] for r in all_results if r["status"] == 200]
    errors_5xx = [r for r in all_results if 500 <= r["status"] < 600]
    errors_429 = [r for r in all_results if r["status"] == 429]
    errors_other = [r for r in all_results if r["status"] not in (200, 429) and r["status"] >= 400]

    print("=== Results ===")
    print(f"Total requests: {len(all_results)}")
    print(f"Successful (200): {len(latencies)}")
    print(f"Rate limited (429): {len(errors_429)}")
    print(f"Server errors (5xx): {len(errors_5xx)}")
    print(f"Other errors: {len(errors_other)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Requests/sec: {len(all_results) / total_time:.1f}")
    print()

    if latencies:
        print("=== Latency (successful requests) ===")
        print(f"P50: {percentile(latencies, 50)*1000:.0f}ms")
        print(f"P95: {percentile(latencies, 95)*1000:.0f}ms")
        print(f"P99: {percentile(latencies, 99)*1000:.0f}ms")
        print(f"Max: {max(latencies)*1000:.0f}ms")
        print(f"Min: {min(latencies)*1000:.0f}ms")

    # Exit code based on results
    if errors_5xx:
        print("\nFAIL: Server errors detected!")
        sys.exit(1)

    print("\nPASS: No server errors")


if __name__ == "__main__":
    main()
