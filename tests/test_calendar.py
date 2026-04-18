"""Tests for calendar generator."""
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from drop_sentinel.generators.calendar import CalendarGenerator
from drop_sentinel.models import Platform, ReleaseInfo


def _make_release(title: str, hours_from_now: int = 24) -> ReleaseInfo:
    return ReleaseInfo(
        title=title,
        platform=Platform.POPMART,
        release_time=datetime.now(UTC) + timedelta(hours=hours_from_now),
        url="https://example.com",
        source="test",
    )


def test_add_and_generate():
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        output_dir = Path(tmpdir) / "docs"
        gen = CalendarGenerator(data_dir=data_dir, output_dir=output_dir)

        gen.add_release(_make_release("LABUBU Drop"))
        gen.add_release(_make_release("DIMOO Drop", hours_from_now=48))
        gen.generate()

        # Check iCal
        ics_path = output_dir / "calendar" / "releases.ics"
        assert ics_path.exists()
        ics_content = ics_path.read_text()
        assert "BEGIN:VCALENDAR" in ics_content
        assert "LABUBU Drop" in ics_content
        assert "DIMOO Drop" in ics_content

        # Check HTML
        html_path = output_dir / "calendar" / "index.html"
        assert html_path.exists()
        html_content = html_path.read_text()
        assert "LABUBU Drop" in html_content

        # Check JSON API
        json_path = output_dir / "api" / "calendar.json"
        assert json_path.exists()


def test_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = CalendarGenerator(data_dir=Path(tmpdir) / "data", output_dir=Path(tmpdir) / "docs")

        release = _make_release("LABUBU Drop")
        gen.add_release(release)
        gen.add_release(release)  # Same title + platform = duplicate

        releases = gen._load_releases()
        assert len(releases) == 1


def test_past_and_upcoming_separation():
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = CalendarGenerator(data_dir=Path(tmpdir) / "data", output_dir=Path(tmpdir) / "docs")

        gen.add_release(_make_release("Future Drop", hours_from_now=24))
        gen.add_release(_make_release("Past Drop", hours_from_now=-24))
        gen.generate()

        html = (Path(tmpdir) / "docs" / "calendar" / "index.html").read_text()
        assert "Future Drop" in html
        assert "Past Drop" in html
