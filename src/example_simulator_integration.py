import json
import time
from simulator_ws_client import subscribe_to_live_updates


def handle_live_message(payload):
    message_type = payload.get("type", "unknown")
    match_id = payload.get("match_id", "unknown")

    print(f"\n[dashboard] update for {match_id}: {message_type}")
    print(json.dumps(payload, indent=2))

    # What to do here:
    # - update your dashboard labels
    # - trigger feature refresh calls
    # - trigger report refresh calls
    # - log pipeline progress


def handle_status(status: str):
    print(f"[dashboard-status] {status}")


if __name__ == "__main__":
    # Where to change it:
    # - ws_base_url should point to your running simvision_api server
    # - match_id should match the video or match job you are monitoring
    client = subscribe_to_live_updates(
        ws_base_url="ws://127.0.0.1:8000",
        match_id="video_demo",
        on_message=handle_live_message,
        on_status=handle_status,
    )

    print("Client started. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping client...")
        client.stop()
