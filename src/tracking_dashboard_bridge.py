from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class TrackingDashboardBridge:
    """
    What this does:
      Reads SimVision tracking artifacts from disk for one match/job id.

    Where it reads from:
      <project_root>/outputs/video/jobs/<match_id>/

    Why it matters:
      Lets the simulator dashboard show tracking, pitch-map, and calibration state
      without needing to parse raw files in multiple places.
    """

    def __init__(self, project_root: str | Path, match_id: str):
        self.project_root = Path(project_root)
        self.match_id = match_id
        self.job_dir = self.project_root / "outputs" / "video" / "jobs" / self.match_id

    # ------------------------------------------------
    # PATH HELPERS
    # ------------------------------------------------

    @property
    def tracking_output_path(self) -> Path:
        return self.job_dir / "tracking_output.json"

    @property
    def pitch_map_path(self) -> Path:
        return self.job_dir / "pitch_map.json"

    @property
    def calibration_points_path(self) -> Path:
        return self.job_dir / "calibration_points.json"

    @property
    def calibration_preview_path(self) -> Path:
        return self.job_dir / "calibration_preview.jpg"

    @property
    def frames_dir(self) -> Path:
        return self.job_dir / "frames"

    # ------------------------------------------------
    # FILE HELPERS
    # ------------------------------------------------

    def _read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _count_exported_frames(self) -> int:
        if not self.frames_dir.exists():
            return 0
        return len(list(self.frames_dir.glob("frame_*.jpg")))

    # ------------------------------------------------
    # SUMMARIES
    # ------------------------------------------------

    def get_tracking_summary(self) -> Dict[str, Any]:
        payload = self._read_json(self.tracking_output_path)
        if not payload:
            return {
                "available": False,
                "processor": "unknown",
                "frames_processed": 0,
                "player_tracks": 0,
                "ball_tracks": 0,
                "home_team_tracks": 0,
                "away_team_tracks": 0,
                "official_tracks": 0,
                "goalkeeper_candidates": 0,
                "status": "missing",
            }

        return {
            "available": True,
            "processor": payload.get("processor", "unknown"),
            "frames_processed": payload.get("frames_processed", 0),
            "player_tracks": payload.get("player_tracks", 0),
            "ball_tracks": payload.get("ball_tracks", 0),
            "home_team_tracks": payload.get("home_team_tracks", 0),
            "away_team_tracks": payload.get("away_team_tracks", 0),
            "official_tracks": payload.get("official_tracks", 0),
            "goalkeeper_candidates": payload.get("goalkeeper_candidates", 0),
            "status": payload.get("status", "unknown"),
        }

    def get_pitch_map_summary(self) -> Dict[str, Any]:
        payload = self._read_json(self.pitch_map_path)
        if not payload:
            return {
                "available": False,
                "method": "unknown",
                "calibration_used": False,
                "orientation_confidence": 0.0,
                "mapped_points": 0,
            }

        return {
            "available": True,
            "method": payload.get("method", "unknown"),
            "calibration_used": payload.get("calibration_used", False),
            "orientation_confidence": payload.get("orientation", {}).get("confidence", 0.0),
            "mapped_points": payload.get("mapped_points", 0),
        }

    def get_calibration_summary(self) -> Dict[str, Any]:
        payload = self._read_json(self.calibration_points_path)
        return {
            "available": bool(payload),
            "frame_path": payload.get("frame_path", ""),
            "preview_path": payload.get("preview_path", ""),
            "preview_exists": self.calibration_preview_path.exists(),
        }

    def get_export_summary(self) -> Dict[str, Any]:
        return {
            "frames_exported": self._count_exported_frames(),
            "frames_dir": str(self.frames_dir),
        }

    def get_headline_metrics(self) -> Dict[str, Any]:
        tracking = self.get_tracking_summary()
        pitch = self.get_pitch_map_summary()
        calibration = self.get_calibration_summary()
        export = self.get_export_summary()

        readiness_score = 0
        readiness_score += 30 if tracking["available"] else 0
        readiness_score += 30 if pitch["available"] else 0
        readiness_score += 20 if calibration["available"] else 0
        readiness_score += 20 if export["frames_exported"] > 0 else 0

        return {
            "match_id": self.match_id,
            "readiness_score": readiness_score,
            "tracking_ready": tracking["available"],
            "pitch_map_ready": pitch["available"],
            "calibration_ready": calibration["available"],
            "frames_exported": export["frames_exported"],
        }

    def as_dashboard_lines(self) -> List[str]:
        tracking = self.get_tracking_summary()
        pitch = self.get_pitch_map_summary()
        calibration = self.get_calibration_summary()
        export = self.get_export_summary()
        headline = self.get_headline_metrics()

        return [
            f"Match ID: {headline['match_id']}",
            f"Readiness Score: {headline['readiness_score']}/100",
            "",
            f"Tracking Ready: {headline['tracking_ready']}",
            f"Pitch Map Ready: {headline['pitch_map_ready']}",
            f"Calibration Ready: {headline['calibration_ready']}",
            f"Frames Exported: {headline['frames_exported']}",
            "",
            f"Tracking Processor: {tracking['processor']}",
            f"Tracking Status: {tracking['status']}",
            f"Frames Processed: {tracking['frames_processed']}",
            f"Player Tracks: {tracking['player_tracks']}",
            f"Ball Tracks: {tracking['ball_tracks']}",
            f"Home Team Tracks: {tracking['home_team_tracks']}",
            f"Away Team Tracks: {tracking['away_team_tracks']}",
            f"Official Tracks: {tracking['official_tracks']}",
            f"Goalkeeper Candidates: {tracking['goalkeeper_candidates']}",
            "",
            f"Pitch Map Method: {pitch['method']}",
            f"Calibration Used: {pitch['calibration_used']}",
            f"Orientation Confidence: {pitch['orientation_confidence']}",
            f"Mapped Points: {pitch['mapped_points']}",
            "",
            f"Calibration Preview Exists: {calibration['preview_exists']}",
            f"Calibration Frame: {calibration['frame_path']}",
            f"Calibration Preview: {calibration['preview_path']}",
            "",
            f"Frames Folder: {export['frames_dir']}",
        ]
