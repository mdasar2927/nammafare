from datetime import datetime, timedelta
from typing import Tuple

class ETAService:
    """Travel Time & ETA calculation service based on actual transit operating speeds."""

    # Real-world commercial operating speeds in km/h across Chennai corridors
    OPERATIONAL_SPEED_KMH = {
        "walking": 4.5,
        "bus": 18.0,
        "metro": 32.0,
        "suburban_train": 35.0,
    }

    # Station dwell and boarding buffers in minutes
    TRANSFER_BUFFER_MINUTES = {
        "walking": 0,
        "bus": 5,
        "metro": 4,
        "suburban_train": 8,
    }

    @classmethod
    def calculate_duration_minutes(cls, distance_meters: int, mode: str) -> int:
        """Calculate transit leg duration in minutes based on actual route distance and mode speed."""
        speed = cls.OPERATIONAL_SPEED_KMH.get(mode.lower(), 18.0)
        km = distance_meters / 1000.0
        raw_minutes = (km / speed) * 60.0
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
        """Format departure and arrival times."""
        try:
            dt = datetime.fromisoformat(base_time_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            dt = datetime.now()

        arr = dt + timedelta(minutes=total_duration_minutes)
        return (dt.strftime("%I:%M %p"), arr.strftime("%I:%M %p"))
