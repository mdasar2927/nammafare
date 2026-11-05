from datetime import datetime, timedelta
from typing import Tuple

class ETAService:
    """Independent Travel Time & ETA calculation service tailored to Chennai traffic."""

    # Average operating speeds in km/h across Chennai corridors
    SPEED_KMH = {
        "walking": 4.5,
        "bus": 18.0,
        "metro": 32.0,
        "suburban_train": 35.0,
        "auto": 24.0,
        "share_auto": 22.0,
        "taxi": 26.0,
    }

    # Typical transfer/boarding buffer in minutes
    TRANSFER_BUFFER_MINUTES = {
        "walking": 0,
        "bus": 8,
        "metro": 5,
        "suburban_train": 10,
        "auto": 3,
        "share_auto": 5,
        "taxi": 5,
    }

    @classmethod
    def calculate_duration_minutes(cls, distance_meters: int, mode: str) -> int:
        """Calculate transit leg duration in minutes based on distance and mode."""
        speed = cls.SPEED_KMH.get(mode.lower(), 18.0)
        km = distance_meters / 1000.0
        # Travel time in minutes
        raw_minutes = (km / speed) * 60.0
        # Minimum durations for realistic transit
        if mode == "walking":
            return max(1, int(round(raw_minutes)))
        elif mode in ("metro", "suburban_train"):
            return max(3, int(round(raw_minutes)))
        else:
            return max(2, int(round(raw_minutes)))

    @classmethod
    def calculate_departure_and_arrival(
        cls, base_time_iso: str, total_duration_minutes: int
    ) -> Tuple[str, str]:
        """Format ISO departure and arrival timestamps."""
        try:
            # Parse departure time or use current time
            dt = datetime.fromisoformat(base_time_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            dt = datetime.now()

        arr = dt + timedelta(minutes=total_duration_minutes)
        return (dt.strftime("%I:%M %p"), arr.strftime("%I:%M %p"))
