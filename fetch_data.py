"""Fetch data from Litter-Robot API and save computed stats to JSON."""

import asyncio
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pylitterbot import Account

# Configure your local timezone
LOCAL_TZ = ZoneInfo("America/Los_Angeles")

# Configuration from environment variables
USERNAME = os.environ.get("LITTERBOT_USERNAME")
PASSWORD = os.environ.get("LITTERBOT_PASSWORD")
CAT_NAME = os.environ.get("CAT_NAME", "Kitty")


@dataclass
class CatVisit:
    """Represents a single cat visit to the litter box."""
    timestamp: datetime
    weight_lbs: float | None = None
    clean_cycle_duration_seconds: float | None = None


def parse_activity_history(activities: list) -> dict:
    """Parse raw activity history into structured data."""
    visits: list[CatVisit] = []
    weights: list[float] = []
    clean_cycles_completed = 0
    sensor_interruptions = 0

    current_visit: CatVisit | None = None
    cycle_start_time: datetime | None = None

    for activity in reversed(activities):
        action = activity.action
        timestamp = activity.timestamp
        action_str = str(action)

        if "CAT_DETECTED" in action_str or action_str == "CD":
            current_visit = CatVisit(timestamp=timestamp)

        elif "Pet Weight Recorded" in action_str:
            match = re.search(r"([\d.]+)\s*lbs", action_str)
            if match:
                weight = float(match.group(1))
                weights.append(weight)
                if current_visit:
                    current_visit.weight_lbs = weight

        elif "CLEAN_CYCLE:" in action_str or action_str == "CCP":
            cycle_start_time = timestamp

        elif "CLEAN_CYCLE_COMPLETE" in action_str or action_str == "CCC":
            clean_cycles_completed += 1
            if cycle_start_time and current_visit:
                duration = (timestamp - cycle_start_time).total_seconds()
                current_visit.clean_cycle_duration_seconds = duration
            if current_visit:
                visits.append(current_visit)
                current_visit = None
            cycle_start_time = None

        elif "CAT_SENSOR_INTERRUPTED" in action_str or action_str == "CSI":
            sensor_interruptions += 1

    # Compute stats
    if activities:
        date_range_start = min(a.timestamp for a in activities)
        date_range_end = max(a.timestamp for a in activities)
        days_covered = (date_range_end - date_range_start).total_seconds() / 86400
    else:
        date_range_start = date_range_end = None
        days_covered = 0

    # Visits by hour (local time)
    visits_by_hour = defaultdict(int)
    for visit in visits:
        local_time = visit.timestamp.astimezone(LOCAL_TZ)
        visits_by_hour[local_time.hour] += 1

    # Visits by date
    visits_by_date: dict[str, dict] = {}
    for visit in visits:
        local_time = visit.timestamp.astimezone(LOCAL_TZ)
        date_key = local_time.strftime("%Y-%m-%d")
        if date_key not in visits_by_date:
            visits_by_date[date_key] = {
                "count": 0,
                "weekday": local_time.weekday(),
                "weekday_name": local_time.strftime("%a"),
                "display": local_time.strftime("%m/%d"),
            }
        visits_by_date[date_key]["count"] += 1

    # Visit gaps
    visit_gaps: list[timedelta] = []
    for i in range(1, len(visits)):
        gap = visits[i].timestamp - visits[i - 1].timestamp
        visit_gaps.append(gap)

    longest_gap = max(visit_gaps) if visit_gaps else None
    shortest_gap = min(visit_gaps) if visit_gaps else None

    # Weight trend
    weight_trend = None
    weight_change = None
    if len(weights) >= 4:
        mid = len(weights) // 2
        first_half_avg = sum(weights[:mid]) / mid
        second_half_avg = sum(weights[mid:]) / (len(weights) - mid)
        weight_change = second_half_avg - first_half_avg
        if weight_change > 0.1:
            weight_trend = "gaining"
        elif weight_change < -0.1:
            weight_trend = "losing"
        else:
            weight_trend = "stable"

    # Personality traits
    personality_traits = []

    if visits_by_hour:
        night_visits = sum(visits_by_hour.get(h, 0) for h in range(0, 6))
        morning_visits = sum(visits_by_hour.get(h, 0) for h in range(6, 12))
        afternoon_visits = sum(visits_by_hour.get(h, 0) for h in range(12, 18))
        evening_visits = sum(visits_by_hour.get(h, 0) for h in range(18, 24))

        periods = [
            (night_visits, "Night Owl"),
            (morning_visits, "Early Bird"),
            (afternoon_visits, "Afternoon Aristocat"),
            (evening_visits, "Evening Eliminator"),
        ]
        dominant_period = max(periods, key=lambda x: x[0])
        if dominant_period[0] > 0:
            personality_traits.append(dominant_period[1])

    if visit_gaps:
        avg_gap = sum((g.total_seconds() for g in visit_gaps)) / len(visit_gaps)
        gap_variance = sum((g.total_seconds() - avg_gap) ** 2 for g in visit_gaps) / len(visit_gaps)
        std_dev_hours = (gap_variance ** 0.5) / 3600
        if std_dev_hours < 2:
            personality_traits.append("Creature of Habit")
        elif std_dev_hours > 6:
            personality_traits.append("Chaotic Pooper")

    if visits_by_date:
        weekend_visits = sum(d["count"] for d in visits_by_date.values() if d["weekday"] >= 5)
        weekday_visits = sum(d["count"] for d in visits_by_date.values() if d["weekday"] < 5)
        weekend_days = sum(1 for d in visits_by_date.values() if d["weekday"] >= 5) or 1
        weekday_days = sum(1 for d in visits_by_date.values() if d["weekday"] < 5) or 1
        weekend_rate = weekend_visits / weekend_days
        weekday_rate = weekday_visits / weekday_days
        if weekend_rate > weekday_rate * 1.3:
            personality_traits.append("Weekend Warrior")
        elif weekday_rate > weekend_rate * 1.3:
            personality_traits.append("Weekday Regular")

    return {
        "visits": visits,
        "weights": weights,
        "clean_cycles_completed": clean_cycles_completed,
        "sensor_interruptions": sensor_interruptions,
        "date_range": (date_range_start, date_range_end),
        "days_covered": days_covered,
        "visits_by_hour": dict(visits_by_hour),
        "visits_by_date": visits_by_date,
        "longest_gap": longest_gap,
        "shortest_gap": shortest_gap,
        "weight_trend": weight_trend,
        "weight_change": weight_change,
        "personality_traits": personality_traits,
    }


def format_duration(td: timedelta) -> str:
    """Format a timedelta into a human-readable string."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def build_data_json(stats: dict, robot_name: str, cat_name: str) -> dict:
    """Build the data structure for the frontend."""
    start, end = stats["date_range"]
    local_start = start.astimezone(LOCAL_TZ) if start else None
    local_end = end.astimezone(LOCAL_TZ) if end else None

    total_visits = len(stats["visits"])
    days = stats["days_covered"] or 1
    visits_per_day = total_visits / days

    weights = stats["weights"]
    avg_weight = sum(weights) / len(weights) if weights else 0
    min_weight = min(weights) if weights else 0
    max_weight = max(weights) if weights else 0

    by_hour = stats["visits_by_hour"]
    peak_hour = max(by_hour, key=by_hour.get) if by_hour else 0
    peak_count = by_hour.get(peak_hour, 0)

    visits_by_date = stats["visits_by_date"]
    sorted_dates = sorted(visits_by_date.keys())
    chart_data = [
        {
            "weekday": visits_by_date[d]["weekday_name"],
            "display": visits_by_date[d]["display"],
            "count": visits_by_date[d]["count"],
        }
        for d in sorted_dates
    ]

    busiest_date = None
    if visits_by_date:
        busiest_date_key = max(visits_by_date.keys(), key=lambda k: visits_by_date[k]["count"])
        busiest_info = visits_by_date[busiest_date_key]
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        busiest_date = {
            "day_name": day_names[busiest_info["weekday"]],
            "display": busiest_info["display"],
            "count": busiest_info["count"],
            "is_weekend": busiest_info["weekday"] >= 5,
        }

    return {
        "cat_name": cat_name,
        "robot_name": robot_name,
        "generated_at": datetime.now(LOCAL_TZ).isoformat(),
        "date_range": {
            "start": local_start.strftime("%b %d") if local_start else None,
            "end": local_end.strftime("%b %d, %Y") if local_end else None,
            "display": f"{local_start.strftime('%b %d')} - {local_end.strftime('%b %d, %Y')}" if local_start else "",
        },
        "personality_traits": stats["personality_traits"],
        "total_visits": total_visits,
        "visits_per_day": round(visits_per_day, 1),
        "chart_data": chart_data,
        "timing": {
            "longest_gap": format_duration(stats["longest_gap"]) if stats["longest_gap"] else "N/A",
            "shortest_gap": format_duration(stats["shortest_gap"]) if stats["shortest_gap"] else "N/A",
        },
        "weight": {
            "average": round(avg_weight, 1),
            "min": round(min_weight, 1),
            "max": round(max_weight, 1),
            "trend": stats.get("weight_trend", "stable"),
            "change": round(stats.get("weight_change", 0) or 0, 2),
        },
        "peak_hour": {
            "hour": peak_hour,
            "count": peak_count,
            "display": f"{peak_hour % 12 or 12}:00 {'AM' if peak_hour < 12 else 'PM'}",
        },
        "busiest_date": busiest_date,
        "robot_stats": {
            "clean_cycles": stats["clean_cycles_completed"],
            "interruptions": stats["sensor_interruptions"],
        },
        "output": {
            "oz": round(total_visits * 2.5, 0),
            "lbs": round(total_visits * 2.5 / 16, 1),
        },
    }


async def main():
    if not USERNAME or not PASSWORD:
        print("Error: Missing required environment variables!")
        print("Please set:")
        print("  LITTERBOT_USERNAME - Your Litter-Robot account email")
        print("  LITTERBOT_PASSWORD - Your Litter-Robot account password")
        print("  CAT_NAME - Your cat's name (optional, defaults to 'Kitty')")
        return False

    account = Account()

    try:
        await account.connect(username=USERNAME, password=PASSWORD, load_robots=True)

        if not account.robots:
            print("No robots found on this account!")
            return False

        robot = account.robots[0]
        print(f"Fetching activity for: {robot.name}")
        print(f"Cat name: {CAT_NAME}")

        activity_history = await robot.get_activity_history(limit=1000)

        # Ensure site directory exists
        site_dir = Path("site")
        site_dir.mkdir(exist_ok=True)

        # Parse and compute stats
        stats = parse_activity_history(activity_history)

        # Build and save data JSON
        data = build_data_json(stats, robot.name, CAT_NAME)
        data_path = site_dir / "data.json"
        data_path.write_text(json.dumps(data, indent=2))
        print(f"Data saved to: {data_path}")

        return True

    finally:
        await account.disconnect()


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
