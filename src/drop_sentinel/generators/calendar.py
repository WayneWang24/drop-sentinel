"""Release calendar generator (iCal + HTML)."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from textwrap import dedent

from drop_sentinel.models import Platform, ReleaseInfo

logger = logging.getLogger(__name__)


class CalendarGenerator:
    """Generate release calendar in iCal and HTML formats."""

    def __init__(self, data_dir: str | Path = "data", output_dir: str | Path = "docs"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.calendar_dir = self.data_dir / "calendar"
        self.calendar_dir.mkdir(parents=True, exist_ok=True)

    def add_release(self, release: ReleaseInfo) -> None:
        """Add a release to the calendar data."""
        releases = self._load_releases()
        # Deduplicate by title + platform
        key = f"{release.title}_{release.platform.value}"
        existing_keys = {f"{r.title}_{r.platform.value}" for r in releases}
        if key not in existing_keys:
            releases.append(release)
            self._save_releases(releases)

    def add_releases(self, releases: list[ReleaseInfo]) -> None:
        """Add multiple releases to the calendar."""
        for r in releases:
            self.add_release(r)

    def generate_ical(self) -> Path:
        """Generate iCal (.ics) file for calendar subscription."""
        releases = self._load_releases()
        output = self.output_dir / "calendar"
        output.mkdir(parents=True, exist_ok=True)
        ics_path = output / "releases.ics"

        events = []
        for r in releases:
            if r.release_time is None:
                continue
            uid = f"{hash(f'{r.title}{r.platform.value}') % 10**10}@drop-sentinel"
            dt_start = r.release_time.strftime("%Y%m%dT%H%M%SZ")
            dt_end = (r.release_time + timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")
            summary = r.title.replace(",", "\\,").replace(";", "\\;")
            description = f"Platform: {r.platform.value}\\nSource: {r.source}"
            if r.url:
                description += f"\\nLink: {r.url}"

            events.append(dedent(f"""\
                BEGIN:VEVENT
                UID:{uid}
                DTSTART:{dt_start}
                DTEND:{dt_end}
                SUMMARY:{summary}
                DESCRIPTION:{description}
                URL:{r.url}
                END:VEVENT"""))

        ical_content = dedent(f"""\
            BEGIN:VCALENDAR
            VERSION:2.0
            PRODID:-//Drop Sentinel//Release Calendar//EN
            CALSCALE:GREGORIAN
            METHOD:PUBLISH
            X-WR-CALNAME:Drop Sentinel Releases
            X-WR-TIMEZONE:UTC
            {chr(10).join(events)}
            END:VCALENDAR""")

        ics_path.write_text(ical_content, encoding="utf-8")
        logger.info(f"iCal generated: {ics_path}")
        return ics_path

    def generate_html(self) -> Path:
        """Generate HTML calendar page."""
        releases = self._load_releases()
        output = self.output_dir / "calendar"
        output.mkdir(parents=True, exist_ok=True)
        html_path = output / "index.html"

        # Group releases by date
        now = datetime.now(UTC)
        upcoming = [r for r in releases if r.release_time and r.release_time > now]
        past = [r for r in releases if r.release_time and r.release_time <= now]
        no_date = [r for r in releases if r.release_time is None]

        upcoming.sort(key=lambda r: r.release_time)
        past.sort(key=lambda r: r.release_time, reverse=True)

        html = self._render_calendar_html(upcoming, past[:20], no_date, now)
        html_path.write_text(html, encoding="utf-8")
        logger.info(f"Calendar HTML generated: {html_path}")
        return html_path

    def generate(self) -> None:
        """Generate both iCal and HTML."""
        self.generate_ical()
        self.generate_html()

        # Also generate JSON API
        releases = self._load_releases()
        api_dir = self.output_dir / "api"
        api_dir.mkdir(exist_ok=True)
        calendar_data = [
            {
                "title": r.title,
                "platform": r.platform.value,
                "release_time": r.release_time.isoformat() if r.release_time else None,
                "url": r.url,
                "source": r.source,
            }
            for r in releases
        ]
        (api_dir / "calendar.json").write_text(
            json.dumps(calendar_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_releases(self) -> list[ReleaseInfo]:
        """Load releases from calendar data file."""
        path = self.calendar_dir / "releases.json"
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [ReleaseInfo.model_validate(r) for r in data]
        except Exception as e:
            logger.warning(f"Failed to load releases: {e}")
            return []

    def _save_releases(self, releases: list[ReleaseInfo]) -> None:
        """Save releases to calendar data file."""
        path = self.calendar_dir / "releases.json"
        data = [r.model_dump(mode="json") for r in releases]
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def _render_calendar_html(
        self,
        upcoming: list[ReleaseInfo],
        past: list[ReleaseInfo],
        no_date: list[ReleaseInfo],
        now: datetime,
    ) -> str:
        """Render the calendar HTML page."""
        def format_release(r: ReleaseInfo) -> dict:
            return {
                "title": r.title,
                "platform": r.platform.value,
                "time": r.release_time.strftime("%Y-%m-%d %H:%M UTC") if r.release_time else "TBD",
                "url": r.url,
                "source": r.source,
                "description": r.description[:200] if r.description else "",
                "countdown": self._countdown(r.release_time, now) if r.release_time and r.release_time > now else "",
            }

        upcoming_data = [format_release(r) for r in upcoming]
        past_data = [format_release(r) for r in past]

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Release Calendar - Drop Sentinel</title>
    <style>
        :root {{
            --bg: #0d1117; --surface: #161b22; --border: #30363d;
            --text: #e6edf3; --text-muted: #8b949e; --accent: #58a6ff;
            --green: #3fb950; --red: #f85149; --yellow: #d29922;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 24px; }}
        header {{ display: flex; align-items: center; justify-content: space-between; padding: 16px 0; border-bottom: 1px solid var(--border); margin-bottom: 24px; }}
        header h1 {{ font-size: 24px; }} header h1 span {{ color: var(--accent); }}
        .nav {{ display: flex; gap: 16px; }}
        .nav a {{ color: var(--accent); text-decoration: none; font-size: 14px; }}
        .nav a:hover {{ text-decoration: underline; }}
        .section-title {{ font-size: 18px; font-weight: 600; margin: 24px 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}
        .ical-link {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 24px; display: flex; align-items: center; gap: 8px; }}
        .ical-link a {{ color: var(--accent); text-decoration: none; }}
        .release-list {{ list-style: none; }}
        .release-item {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; display: flex; align-items: center; gap: 12px; }}
        .release-time {{ color: var(--yellow); font-weight: 600; min-width: 160px; font-size: 14px; }}
        .release-info {{ flex: 1; }}
        .release-title {{ font-weight: 600; }}
        .release-meta {{ color: var(--text-muted); font-size: 13px; }}
        .countdown {{ color: var(--green); font-weight: 600; font-size: 13px; white-space: nowrap; }}
        .release-link {{ color: var(--accent); text-decoration: none; font-size: 14px; }}
        .empty {{ color: var(--text-muted); text-align: center; padding: 48px; }}
        footer {{ text-align: center; padding: 24px; color: var(--text-muted); font-size: 13px; border-top: 1px solid var(--border); margin-top: 32px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><span>Drop</span> Sentinel — Calendar</h1>
            <div class="nav">
                <a href="../index.html">Dashboard</a>
                <a href="releases.ics">Subscribe (iCal)</a>
            </div>
        </header>
        <div class="ical-link">
            <a href="releases.ics">Subscribe to release calendar</a> — add to Google Calendar, Apple Calendar, or Outlook
        </div>
        <h2 class="section-title">Upcoming Releases ({len(upcoming_data)})</h2>
        {''.join(f"""<div class="release-item">
            <div class="release-time">{r["time"]}</div>
            <div class="release-info">
                <div class="release-title">{r["title"]}</div>
                <div class="release-meta">{r["platform"]} &middot; {r["source"]}</div>
            </div>
            {f'<span class="countdown">{r["countdown"]}</span>' if r["countdown"] else ''}
            {f'<a class="release-link" href="{r["url"]}" target="_blank">View</a>' if r["url"] else ''}
        </div>""" for r in upcoming_data) if upcoming_data else '<div class="empty">No upcoming releases found yet.</div>'}

        <h2 class="section-title">Recent Past Releases</h2>
        {''.join(f"""<div class="release-item">
            <div class="release-time">{r["time"]}</div>
            <div class="release-info">
                <div class="release-title">{r["title"]}</div>
                <div class="release-meta">{r["platform"]} &middot; {r["source"]}</div>
            </div>
        </div>""" for r in past_data) if past_data else '<div class="empty">No past releases recorded.</div>'}
    </div>
    <footer>Drop Sentinel — Release Calendar. Updated: {now.strftime("%Y-%m-%d %H:%M UTC")}</footer>
    <script>setTimeout(() => location.reload(), 5 * 60 * 1000);</script>
</body>
</html>"""

    @staticmethod
    def _countdown(release_time: datetime, now: datetime) -> str:
        """Generate human-readable countdown string."""
        delta = release_time - now
        if delta.total_seconds() <= 0:
            return ""
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        if days > 0:
            return f"in {days}d {hours}h"
        elif hours > 0:
            return f"in {hours}h {minutes}m"
        else:
            return f"in {minutes}m"
