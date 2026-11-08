"""Tests for src/dedup.py: deterministic cross-source duplicate removal."""

from datetime import date

from src.dedup import dedupe, normalize_name
from src.models import Event


def _event(
    name: str,
    venue: str | None = None,
    time: str | None = None,
    day: int = 7,
    source: str = "Do604",
    **extra: str | None,
) -> Event:
    return Event(
        name=name, city=extra.get("city"), address=extra.get("address"), time=time,
        event_date=date(2026, 3, day), source_name=source, source_url=f"https://{source}/{name}",
        venue=venue, category=extra.get("category"), price=extra.get("price"),
    )


def test_normalize_name_strips_noise_tokens() -> None:
    # Arrange, Act
    result = normalize_name("The 37th Annual Festival du Bois!")

    # Assert
    assert result == "festival du bois"


def test_dedupe_returns_empty_result_for_empty_input() -> None:
    # Arrange, Act
    result = dedupe([])

    # Assert
    assert (result.events, result.removed, result.candidates) == ([], 0, [])


def test_dedupe_keeps_single_event() -> None:
    # Arrange
    events = [_event("Solo Show")]

    # Act
    result = dedupe(events)

    # Assert
    assert result.events == events and result.removed == 0


def test_dedupe_merges_same_name_same_date_across_sources() -> None:
    # Arrange
    a = _event("Christie Lenée", venue="The Fox Cabaret", time="7 pm", source="Do604", category="music")
    b = _event("Christie Lenée", venue="Fox Cabaret", time="7:00 PM", source="ShowHub",
               city="Vancouver", address="2321 Main St")

    # Act
    result = dedupe([a, b])

    # Assert
    assert result.removed == 1
    merged = result.events[0]
    assert (merged.city, merged.address, merged.category) == ("Vancouver", "2321 Main St", "music")


def test_dedupe_treats_annual_prefix_variants_as_duplicates() -> None:
    # Arrange
    events = [_event("Festival du Bois", venue="Mackin Park"),
              _event("37th Annual Festival du Bois", venue="Mackin Park", source="Daily Hive")]

    # Act
    result = dedupe(events)

    # Assert
    assert result.removed == 1


def test_dedupe_keeps_same_name_at_different_times() -> None:
    # Arrange
    events = [_event("Comedy Night", venue="Yuk Yuks", time="7:00 PM"),
              _event("Comedy Night", venue="Yuk Yuks", time="9:30 PM", source="Eventbrite")]

    # Act
    result = dedupe(events)

    # Assert
    assert result.removed == 0 and len(result.events) == 2


def test_dedupe_keeps_same_name_on_different_dates() -> None:
    # Arrange
    events = [_event("Market", venue="Plaza", day=7), _event("Market", venue="Plaza", day=8)]

    # Act
    result = dedupe(events)

    # Assert
    assert result.removed == 0


def test_dedupe_keeps_same_name_at_different_venues() -> None:
    # Arrange
    events = [_event("Jazz Jam", venue="Frankie's"), _event("Jazz Jam", venue="Guilt & Co", source="ShowHub")]

    # Act
    result = dedupe(events)

    # Assert
    assert result.removed == 0


def test_dedupe_merges_subset_name_at_same_venue() -> None:
    # Arrange
    events = [_event("Delhi 2 Dublin", venue="Hollywood Theatre", time="7 pm"),
              _event("Delhi 2 Dublin with Special Guests", venue="The Hollywood Theatre", source="ShowHub")]

    # Act
    result = dedupe(events)

    # Assert
    assert result.removed == 1


def test_dedupe_flags_similar_names_without_venue_as_candidates() -> None:
    # Arrange
    events = [_event("Jazz Jam Session", venue=None), _event("Jazz Jam Sessions", venue="Frankie's", source="ShowHub")]

    # Act
    result = dedupe(events)

    # Assert
    assert result.removed == 0
    assert result.candidates == [(1, 2)]


def test_dedupe_merges_chains_of_duplicates() -> None:
    # Arrange
    events = [
        _event("Aterciopelados", venue="Vogue Theatre", source="Do604"),
        _event("Aterciopelados", venue="Vogue Theatre", source="ShowHub"),
        _event("Aterciopelados", venue="The Vogue Theatre", source="Eventbrite"),
    ]

    # Act
    result = dedupe(events)

    # Assert
    assert result.removed == 2 and len(result.events) == 1


def test_dedupe_preserves_input_order_of_survivors() -> None:
    # Arrange
    events = [_event("B Show", venue="X"), _event("A Show", venue="Y"), _event("B Show", venue="X", source="ShowHub")]

    # Act
    result = dedupe(events)

    # Assert
    assert [e.name for e in result.events] == ["B Show", "A Show"]


def test_dedupe_does_not_mutate_input_events() -> None:
    # Arrange
    a = _event("Show", venue="Hall", source="Do604")
    b = _event("Show", venue="Hall", source="ShowHub", city="Vancouver")

    # Act
    dedupe([a, b])

    # Assert
    assert a.city is None


def test_dedupe_keeps_same_name_in_different_cities() -> None:
    # Arrange
    events = [_event("Samsung Consultations", venue="Best Buy", city="Vancouver"),
              _event("Samsung Consultations", venue="Best Buy", city="Burnaby", source="ShowHub")]

    # Act
    result = dedupe(events)

    # Assert
    assert (result.removed, result.candidates) == (0, [])


def test_dedupe_keeps_same_venue_name_at_different_addresses() -> None:
    # Arrange
    events = [_event("Samsung Consultations", venue="Best Buy", address="2220 Cambie Street"),
              _event("Samsung Consultations", venue="Best Buy", address="798 Granville Street", source="ShowHub")]

    # Act
    result = dedupe(events)

    # Assert
    assert (result.removed, result.candidates) == (0, [])


def test_dedupe_matches_city_variants() -> None:
    # Arrange
    events = [_event("Big Show", venue="Hall", city="Langley Township"),
              _event("Big Show", venue="Hall", city="Langley", source="ShowHub")]

    # Act
    result = dedupe(events)

    # Assert
    assert result.removed == 1


def test_dedupe_flags_candidates_only_across_sources() -> None:
    # Arrange
    events = [_event("Writers Workshop with Kevin", venue=None),
              _event("Writers Workshop with Daniel", venue=None)]

    # Act
    result = dedupe(events)

    # Assert
    assert result.candidates == []


def test_dedupe_does_not_chain_distinct_shows_through_unknown_time() -> None:
    # Arrange
    events = [
        _event("Dracula", venue="Lindsay Stage", time="1:30 pm", source="Do604"),
        _event("Dracula", venue="Lindsay Stage", time="varies", source="Kids Out and About"),
        _event("Dracula", venue="Lindsay Stage", time="7:30 pm", source="Do604"),
    ]

    # Act
    result = dedupe(events)

    # Assert
    assert sorted(e.time for e in result.events) == ["1:30 pm", "7:30 pm"]


def test_dedupe_is_deterministic() -> None:
    # Arrange
    events = [_event(f"Show {i % 3}", venue="Hall", source=f"S{i}") for i in range(9)]

    # Act
    runs = {tuple(e.source_name for e in dedupe(events).events) for _ in range(5)}

    # Assert
    assert len(runs) == 1


def test_dedupe_prefers_clock_time_over_vague_time() -> None:
    # Arrange
    events = [
        _event("Dracula", venue="Lindsay Stage", time="varies", source="Kids Out and About",
               city="Vancouver", address="1585 Johnston St", category="theatre", price="$40"),
        _event("Dracula", venue="Lindsay Stage", time="7:30 pm", source="Do604"),
    ]

    # Act
    result = dedupe(events)

    # Assert
    assert result.events[0].time == "7:30 pm"


def test_dedupe_does_not_chain_different_places_through_placeless_listing() -> None:
    # Arrange
    events = [
        _event("Open Mic Night", venue="Fox Cabaret", time="8 pm", city="Vancouver", source="Do604"),
        _event("Open Mic Night", source="Eventbrite"),
        _event("Open Mic Night", venue="Studio 1", time="8 pm", city="Burnaby", source="Daily Hive"),
    ]

    # Act
    result = dedupe(events)

    # Assert
    assert {e.city for e in result.events} == {"Vancouver", "Burnaby"}


def test_dedupe_does_not_chain_different_venues_through_placeless_listing() -> None:
    # Arrange
    events = [
        _event("Live Music Saturday", venue="Pub A", source="Do604"),
        _event("Live Music Saturday", source="Do604"),
        _event("Live Music Saturday", venue="Pub B", source="Do604"),
    ]

    # Act
    result = dedupe(events)

    # Assert
    assert {e.venue for e in result.events} >= {"Pub A", "Pub B"}


def test_dedupe_compares_venues_by_words_not_characters() -> None:
    # Arrange
    events = [_event("Jazz", venue="The Pat", time="8 pm", source="A"),
              _event("Jazz", venue="Pattullo Bistro", time="8 pm", source="B")]

    # Act
    result = dedupe(events)

    # Assert
    assert result.removed == 0


def test_normalize_name_treats_curly_and_straight_apostrophes_alike() -> None:
    # Arrange, Act, Assert
    assert normalize_name("Apollo’s Jam") == normalize_name("Apollo's Jam") == "apollos jam"


def test_dedupe_prefers_the_timed_copy_when_both_are_equally_complete() -> None:
    # Arrange
    events = [
        _event("Jazz Night", venue="Hall", time="varies", source="Do604"),
        _event("Jazz Night", venue="Hall", time="8 pm", source="ShowHub"),
    ]

    # Act
    result = dedupe(events)

    # Assert
    assert [(e.source_name, e.time) for e in result.events] == [("ShowHub", "8 pm")]
