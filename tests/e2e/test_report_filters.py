"""End-to-end: drive the HTML report (filter bar and table layout) in headless Chromium (Playwright)."""

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from src.models import Event, SourceStatus
from src.renderers.html_renderer import render_html

sync_api = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e

DAY = date(2026, 11, 7)


def _event(name: str, city: str | None, category: str | None, source: str, time: str | None) -> Event:
    return Event(name=name, city=city, address=None, time=time, event_date=DAY, source_name=source,
                 source_url="https://example.com/" + name.replace(" ", "-"), category=category)


EVENTS = [
    _event("Midnight Jam", "Vancouver", "music", "ShowHub", "12:30 am"),
    _event("Morning Market", "Vancouver", "community", "Do604", "10 am"),
    _event("Lunch Concert", "Vancouver", "music", "Do604", "1 pm"),
    _event("Jazz Matinee", "Vancouver", "music", "ShowHub", "1:30 pm"),
    _event("Storytime", "Burnaby", "family", "Vancouver Public Library", "3:00 PM"),
    _event("Ballet", "Vancouver", "theatre", "Do604", "6 pm"),
    _event("Late Set", "Surrey", "music", "Eventbrite", "10 pm"),
    _event("Mystery Walk", None, None, "Do604", "varies"),
]
ONE_PM, SIX_PM, TEN_PM, TWO_AM = "780", "1080", "1320", "120"


@pytest.fixture(scope="module")
def report(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("report") / "events.html"
    statuses = [SourceStatus(name=s, count=1, error=None) for s in ("Do604", "ShowHub")]
    path.write_text(render_html(EVENTS, statuses, DAY, DAY), encoding="utf-8")

    return path


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        chromium = p.chromium.launch()
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser, report: Path):
    pg = browser.new_page()
    pg.goto(report.as_uri())
    yield pg
    pg.close()


def _visible_names(page) -> list[str]:
    return page.eval_on_selector_all(
        "#events-table tbody tr:not([hidden])", "rows => rows.map(r => r.children[0].textContent)",
    )


def _is_open(page, group: str) -> bool:
    return page.locator(f"#filter-{group}").evaluate("d => d.open")


def _tick(page, group: str, value: str) -> None:
    if not _is_open(page, group):
        page.click(f"#filter-{group} summary")

    page.check(f'#filter-{group} input[value="{value}"]')


def _pick_time(page, bound: str, value: str) -> None:
    """Choose a start-time bound with real clicks, as a person would."""
    page.click(f"#filter-{bound} summary")
    page.click(f'#filter-{bound} input[value="{value}"]')


def test_shows_every_event_initially(page) -> None:
    # Arrange, Act
    names = _visible_names(page)

    # Assert
    assert len(names) == 8
    assert page.inner_text("#shown-count") == "Showing 8 of 8 events"


def test_city_filter_accepts_several_cities(page) -> None:
    # Arrange, Act
    _tick(page, "city", "Burnaby")
    _tick(page, "city", "Surrey")

    # Assert
    assert _visible_names(page) == ["Storytime", "Late Set"]
    assert "2 selected" in page.inner_text("#filter-city summary")


def test_single_choice_shows_its_label(page) -> None:
    # Arrange, Act
    _tick(page, "city", "Burnaby")

    # Assert
    assert page.inner_text("#filter-city .sel") == "Burnaby"


def test_unknown_city_option_selects_events_without_city(page) -> None:
    # Arrange, Act
    _tick(page, "city", "")

    # Assert
    assert _visible_names(page) == ["Mystery Walk"]


def test_untyped_option_selects_events_without_type(page) -> None:
    # Arrange, Act
    _tick(page, "type", "")

    # Assert
    assert _visible_names(page) == ["Mystery Walk"]


def test_type_and_source_filters_combine(page) -> None:
    # Arrange, Act
    _tick(page, "type", "music")
    _tick(page, "source", "Eventbrite")

    # Assert
    assert _visible_names(page) == ["Late Set"]


def test_time_range_includes_both_bounds(page) -> None:
    # Arrange, Act
    _pick_time(page, "from", ONE_PM)
    _pick_time(page, "to", SIX_PM)

    # Assert
    assert _visible_names(page) == ["Lunch Concert", "Jazz Matinee", "Storytime", "Ballet"]


def test_time_from_alone_keeps_later_events_and_hides_unknown_times(page) -> None:
    # Arrange, Act
    _pick_time(page, "from", SIX_PM)

    # Assert
    assert _visible_names(page) == ["Ballet", "Late Set"]


def test_time_to_alone_keeps_earlier_events_and_hides_unknown_times(page) -> None:
    # Arrange, Act
    _pick_time(page, "to", ONE_PM)

    # Assert
    assert _visible_names(page) == ["Midnight Jam", "Morning Market", "Lunch Concert"]


def test_time_range_wraps_past_midnight(page) -> None:
    # Arrange, Act
    _pick_time(page, "from", TEN_PM)
    _pick_time(page, "to", TWO_AM)

    # Assert
    assert _visible_names(page) == ["Midnight Jam", "Late Set"]


def test_no_match_shows_message(page) -> None:
    # Arrange, Act
    _tick(page, "city", "Surrey")
    _tick(page, "type", "family")

    # Assert
    assert _visible_names(page) == []
    assert page.is_visible("#no-matches")


def test_reset_clears_every_filter(page) -> None:
    # Arrange
    _tick(page, "city", "Burnaby")
    _pick_time(page, "from", ONE_PM)
    _pick_time(page, "to", SIX_PM)

    # Act
    page.click("#reset-filters")

    # Assert
    assert len(_visible_names(page)) == 8
    assert page.eval_on_selector_all("#filters input[type=checkbox]:checked", "els => els.length") == 0
    assert page.is_checked('#filter-from input[value=""]')
    assert page.inner_text("#filter-from .sel") == "any time"
    assert page.is_checked('#filter-to input[value=""]')
    assert page.inner_text("#filter-to .sel") == "any time"


def test_sorting_keeps_hidden_rows_hidden(page) -> None:
    # Arrange
    _tick(page, "city", "Burnaby")
    _tick(page, "city", "Surrey")
    page.keyboard.press("Escape")

    # Act
    page.click('th[data-col="0"]')

    # Assert
    assert _visible_names(page) == ["Late Set", "Storytime"]


def test_sorting_by_time_puts_events_without_time_first(page) -> None:
    # Arrange, Act
    page.click('th[data-col="5"]')

    # Assert
    assert _visible_names(page)[0] == "Mystery Walk"
    assert _visible_names(page)[1:3] == ["Midnight Jam", "Morning Market"]


def test_opening_one_dropdown_closes_the_others(page) -> None:
    # Arrange
    page.click("#filter-city summary")

    # Act
    page.click("#filter-type summary")

    # Assert
    assert (_is_open(page, "city"), _is_open(page, "type")) == (False, True)


def test_escape_closes_dropdown_and_returns_focus_to_it(page) -> None:
    # Arrange
    _tick(page, "city", "Burnaby")

    # Act
    page.keyboard.press("Escape")

    # Assert
    assert _is_open(page, "city") is False
    assert page.evaluate("document.activeElement.closest('#filter-city') !== null")


def test_click_outside_closes_dropdown(page) -> None:
    # Arrange
    page.click("#filter-source summary")

    # Act
    page.click("h1")

    # Assert
    assert _is_open(page, "source") is False


def test_visible_rows_alternate_shading_after_filtering(page) -> None:
    # Arrange, Act
    _tick(page, "city", "Vancouver")

    # Assert
    shading = page.eval_on_selector_all(
        "#events-table tbody tr:not([hidden])", "rows => rows.map(r => r.classList.contains('alt'))",
    )
    assert shading == [False, True, False, True, False]


def test_picking_a_time_shows_it_and_closes_the_dropdown(page) -> None:
    # Arrange, Act
    _pick_time(page, "from", ONE_PM)

    # Assert
    assert page.inner_text("#filter-from .sel") == "1 PM"
    assert _is_open(page, "from") is False


def test_clicking_a_time_label_picks_it_and_returns_focus_to_the_dropdown(page) -> None:
    # Arrange
    page.click("#filter-from summary")

    # Act
    page.click(f'#filter-from label:has(input[value="{ONE_PM}"])')

    # Assert
    assert page.inner_text("#filter-from .sel") == "1 PM"
    assert _is_open(page, "from") is False
    assert page.evaluate("document.activeElement === document.querySelector('#filter-from summary')")


def test_time_dropdown_is_announced_with_its_name_and_choice(page) -> None:
    # Arrange
    _pick_time(page, "from", ONE_PM)

    # Act
    summary = page.get_by_role("group", name="Start time").locator("#filter-from summary")

    # Assert
    assert summary.inner_text().strip().startswith("Starts from")
    assert "1 PM" in summary.inner_text()
    assert page.get_by_role("radiogroup", name="Starts by", include_hidden=True).count() == 1


def test_restored_choices_are_applied_when_returning_to_the_page(page, report: Path) -> None:
    # Arrange
    _pick_time(page, "from", SIX_PM)
    _tick(page, "city", "Surrey")
    page.goto("about:blank")

    # Act
    page.go_back()

    # Assert
    if not page.is_checked(f'#filter-from input[value="{SIX_PM}"]'):
        pytest.skip("browser did not restore form state")
    assert page.inner_text("#filter-from .sel") == "6 PM"
    assert _visible_names(page) == ["Late Set"]


def test_arrow_keys_change_the_time_without_closing(page) -> None:
    # Arrange
    page.click("#filter-to summary")
    page.focus('#filter-to input[value=""]')

    # Act
    page.keyboard.press("ArrowDown")

    # Assert
    assert page.inner_text("#filter-to .sel") == "1 AM"
    assert _is_open(page, "to") is True
    assert _visible_names(page) == ["Midnight Jam"]


@pytest.mark.parametrize("group", ["city", "type", "source", "from", "to"])
def test_open_dropdown_fits_a_phone_screen(browser, report: Path, group: str) -> None:
    # Arrange
    phone = browser.new_page(viewport={"width": 375, "height": 812})
    phone.goto(report.as_uri())

    # Act
    phone.click(f"#filter-{group} summary")

    # Assert
    box = phone.locator(f"#filter-{group} .options").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 375
    assert phone.evaluate("document.documentElement.scrollWidth") <= 375
    phone.close()


WIDE_EVENT = Event(
    name="Fall Improvisation Workshop: Lisa Cay Miller with a much longer title " * 3, city="Langley (Township)",
    address="8EAST, 8 East Pender Street, a long location that takes room " * 2, time="1 pm - 1:45 pm",
    event_date=DAY, source_name="Rhythm Changes", source_url="https://example.com/a", category="theatre",
)
CROWDED_EVENT = Event(
    name="Supercalifragilisticexpialidocious-Extravaganza-Festival-2026 night", city="North Vancouver",
    address="Gordon-Smith-Gallery-of-Canadian-Art-and-Sculpture-Garden, 2121 Lonsdale Avenue",
    time="Saturday - 10:am - 5 pm", event_date=DAY, source_name="Vancouver Public Library",
    source_url="https://example.com/a", category="theatre",
)
OVERFLOWS = "(() => { const t = document.querySelector('.table-wrap'); return t.scrollWidth > t.clientWidth; })()"
TIGHT = "document.querySelector('.table-wrap').classList.contains('tight')"


def _write_report(tmp_path: Path, events: list[Event]) -> Path:
    path = tmp_path / "layout.html"
    path.write_text(render_html(events, [], DAY, DAY), encoding="utf-8")

    return path


@pytest.fixture
def sized_page(browser):
    """Open a page at a given width; every page opened is closed even when the test fails."""
    pages = []

    def open_page(width: int, path: Path):
        pg = browser.new_page(viewport={"width": width, "height": 800})
        pages.append(pg)
        pg.goto(path.as_uri())
        return pg

    yield open_page
    for pg in pages:
        pg.close()


@pytest.mark.parametrize("column", [2, 3, 5, 6, 8])
def test_type_city_date_time_and_source_cells_stay_on_one_line(sized_page, tmp_path: Path, column: int) -> None:
    # Arrange
    pg = sized_page(1280, _write_report(tmp_path, [WIDE_EVENT]))

    # Act
    lines = pg.evaluate(
        """col => { const td = document.querySelector(`#events-table tbody td:nth-child(${col})`);
                    const r = document.createRange(); r.selectNodeContents(td);
                    return new Set(Array.from(r.getClientRects()).map(x => Math.round(x.top))).size; }""",
        column,
    )

    # Assert
    assert lines == 1


def test_too_wide_table_scrolls_inside_its_box_on_a_phone(sized_page, tmp_path: Path) -> None:
    # Arrange, Act
    pg = sized_page(375, _write_report(tmp_path, [CROWDED_EVENT]))

    # Assert
    assert pg.evaluate(OVERFLOWS) is True
    assert pg.evaluate("document.documentElement.scrollWidth") <= 375


@pytest.mark.parametrize(("width", "tight"), [(900, True), (1024, True), (1920, False)])
def test_table_fits_the_window_without_cutting_off_columns(sized_page, tmp_path: Path, width: int, tight: bool) -> None:
    # Arrange, Act
    pg = sized_page(width, _write_report(tmp_path, [CROWDED_EVENT]))

    # Assert
    assert pg.evaluate(OVERFLOWS) is False
    assert pg.evaluate(TIGHT) is tight


@pytest.mark.parametrize("width", [390, 1920])
def test_page_is_centered_with_side_margins_relative_to_the_window(sized_page, report: Path, width: int) -> None:
    # Arrange
    pg = sized_page(width, report)

    # Act
    box = pg.locator(".container").bounding_box()
    page_width = pg.evaluate("document.documentElement.clientWidth")

    # Assert
    left, right = box["x"], page_width - box["x"] - box["width"]
    assert abs(left - right) <= 1
    assert left >= 0.05 * page_width


def test_columns_rewrap_when_the_window_is_resized(sized_page, tmp_path: Path) -> None:
    # Arrange
    pg = sized_page(1920, _write_report(tmp_path, [CROWDED_EVENT]))

    # Act
    pg.set_viewport_size({"width": 1024, "height": 800})
    pg.wait_for_function(TIGHT, timeout=2000)
    pg.set_viewport_size({"width": 1920, "height": 800})
    pg.wait_for_function(f"!({TIGHT})", timeout=2000)

    # Assert
    assert pg.evaluate(OVERFLOWS) is False


def test_header_stays_visible_while_scrolling_the_page(sized_page, tmp_path: Path) -> None:
    # Arrange
    many = [replace(WIDE_EVENT, name=f"Event {i}") for i in range(80)]
    pg = sized_page(1280, _write_report(tmp_path, many))

    # Act
    pg.evaluate("window.scrollTo(0, 2000)")

    # Assert
    assert abs(pg.locator("#events-table thead").bounding_box()["y"]) <= 1
