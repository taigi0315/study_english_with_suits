import json
import logging
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from langflix.youtube.uploader import YouTubeUploader

logger = logging.getLogger(__name__)


@dataclass
class LastScheduleConfig:
    time_slots: List[str] = None           # e.g. ['00:00','06:00','12:00','18:00']
    slot_capacity: int = 3
    daily_max_total: int = 6
    window_days: int = 14
    cache_file: str = ".cache/last_scheduled_map.json"

    def __post_init__(self):
        if self.time_slots is None:
            # Default to 4 times per day with 6-hour intervals (0, 6, 12, 18)
            self.time_slots = ['00:00', '06:00', '12:00', '18:00']
        if self.slot_capacity <= 0:
            self.slot_capacity = 3  # 3 videos per slot
        if self.daily_max_total <= 0:
            self.daily_max_total = 6
        if self.window_days <= 0:
            self.window_days = 14


class YouTubeLastScheduleService:
    """
    Lightweight scheduling helper that relies on YouTube API (publishAt) only.
    - Builds an in-memory map of scheduled counts per (date, slot)
    - Respects slot_capacity and daily_max_total without needing DB
    """

    def __init__(self, config: Optional[LastScheduleConfig] = None):
        self.config = config or LastScheduleConfig()
        self._uploader = YouTubeUploader()
        self._schedule_map: Dict[str, Dict[str, int]] = {}  # dateISO -> { '08:00': count, ... }
        self._load_cache()

    def _load_cache(self):
        try:
            path = Path(self.config.cache_file)
            if path.exists():
                data = json.loads(path.read_text())
                if isinstance(data, dict):
                    self._schedule_map = data
        except Exception as e:
            logger.warning(f"Failed to load last schedule cache: {e}")

    def _save_cache(self):
        try:
            path = Path(self.config.cache_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._schedule_map, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Failed to save last schedule cache: {e}")

    def refresh_from_youtube(self) -> bool:
        """Fetch scheduled videos from YouTube and rebuild the in-memory map."""
        try:
            items = self._uploader.list_scheduled_videos(max_results=50)  # publishAt in future
            # Reset map
            self._schedule_map = {}
            for item in items:
                publish_at_str = item.get('status', {}).get('publishAt')
                if not publish_at_str:
                    continue
                try:
                    publish_dt = datetime.fromisoformat(publish_at_str.replace('Z', '+00:00'))
                except Exception:
                    continue
                # Convert to local date/slot string based on configured slots (by time component)
                date_key = publish_dt.date().isoformat()
                time_key = publish_dt.strftime('%H:%M')
                self._schedule_map.setdefault(date_key, {})
                self._schedule_map[date_key][time_key] = self._schedule_map[date_key].get(time_key, 0) + 1
            self._save_cache()
            return True
        except Exception as e:
            logger.warning(f"Failed to refresh from YouTube: {e}")
            return False

    def _parse_slots(self) -> List[time]:
        slots: List[time] = []
        for s in self.config.time_slots:
            try:
                h, m = map(int, s.split(':'))
                slots.append(time(h, m))
            except Exception:
                logger.warning(f"Ignoring invalid slot time: {s}")
        return slots

    def _count_day_total(self, d: date) -> int:
        return sum(self._schedule_map.get(d.isoformat(), {}).values())

    def _count_slot(self, d: date, t: time) -> int:
        return self._schedule_map.get(d.isoformat(), {}).get(t.strftime('%H:%M'), 0)

    def get_next_available_slot(self, now: Optional[datetime] = None) -> datetime:
        """Find next available slot using in-memory map only. Refresh from API on first use."""
        if not self._schedule_map:
            self.refresh_from_youtube()

        now = now or datetime.now()
        slots = self._parse_slots()

        for days_ahead in range(self.config.window_days):
            day = (now.date() + timedelta(days=days_ahead))

            # respect daily total cap
            if self._count_day_total(day) >= self.config.daily_max_total:
                continue

            for slot in slots:
                # skip past slots on current day
                if days_ahead == 0 and datetime.combine(day, slot) <= now:
                    continue

                if self._count_slot(day, slot) < self.config.slot_capacity:
                    return datetime.combine(day, slot)

        # fallback: 7 days later at first slot
        fallback = datetime.combine(now.date() + timedelta(days=7), slots[0] if slots else time(8, 0))
        return fallback

    def record_local(self, publish_at: datetime):
        """Increment local counters after assigning a slot so batch scheduling stays consistent."""
        date_key = publish_at.date().isoformat()
        time_key = publish_at.strftime('%H:%M')
        self._schedule_map.setdefault(date_key, {})
        self._schedule_map[date_key][time_key] = self._schedule_map[date_key].get(time_key, 0) + 1
        self._save_cache()


