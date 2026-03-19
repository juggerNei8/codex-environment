import time
from simulator_ws_client import subscribe_to_live_updates

# ------------------------------------------------------------
# ADJUSTED VALUES FOR YOUR CURRENT SETUP
# ------------------------------------------------------------
# What this is:
#   The WebSocket base URL of your running analytics API.
#
# Why it is "ws://" and not "http://":
#   HTTP endpoints use http://
#   WebSocket endpoints use ws://
#
# Your current API server is running locally on:
#   http://127.0.0.1:8000
#
# Therefore the WebSocket base URL must be:
#   ws://127.0.0.1:8000
# ------------------------------------------------------------
WS_BASE_URL = "ws://127.0.0.1:8000"

# What this is:
#   The match/video job ID you already tested successfully.
#
# Your current working match ID is:
#   video_demo
MATCH_ID = "video_demo"


def handle_live_message(payload: dict) -> None:
    """
    Called every time the simulator receives a JSON live update.
    """
    message_type = payload.get("type", "unknown")
    match_id = payload.get("match_id", "unknown")

    print("\n[live-update]")
    print(f"match_id: {match_id}")
    print(f"type: {message_type}")
    print(f"payload: {payload}")

    # --------------------------------------------------------
    # PUT YOUR REAL SIMULATOR UI UPDATE CODE HERE
    # --------------------------------------------------------
    # Example ideas:
    # dashboard_status_label.config(text=message_type)
    # refresh_status_panel(match_id)
    # refresh_video_status(match_id)
    # refresh_prediction_view(match_id)
    # --------------------------------------------------------


def handle_ws_status(status: str) -> None:
    """
    Called when the WebSocket connection changes state.
    """
    print(f"[ws-status] {status}")


def main():
    print("Starting simulator live update subscriber...")
    print(f"WS_BASE_URL = {WS_BASE_URL}")
    print(f"MATCH_ID    = {MATCH_ID}")

    client = subscribe_to_live_updates(
        ws_base_url=WS_BASE_URL,
        match_id=MATCH_ID,
        on_message=handle_live_message,
        on_status=handle_ws_status,
    )

    print("Subscriber started.")
    print("Leave this running and trigger tracking/pitch-map events from the API.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        client.stop()
        print("Stopped.")


if __name__ == "__main__":
    main()