"""Effective-date scope reads an open-ended validity interval; unknown never matches."""

from qnu.domains.knowledge.metadata import MetadataFilter, matches_metadata


def annotated(**values):
    return {"retrieval_metadata": [{"values": values}]}


def test_from_only_bound_is_open_ended_to_later_dates():
    scope = MetadataFilter(effective_on="2026-11-13")
    assert matches_metadata(annotated(effective_from="2026-01-01"), scope)
    assert not matches_metadata(annotated(effective_from="2027-01-01"), scope)


def test_until_only_bound_is_open_started_from_earlier_dates():
    scope = MetadataFilter(effective_on="2026-11-13")
    assert matches_metadata(annotated(effective_until="2026-12-31"), scope)
    assert not matches_metadata(annotated(effective_until="2026-10-31"), scope)


def test_closed_interval_is_inclusive_at_both_ends():
    scope = MetadataFilter(effective_on="2026-11-13")
    assert matches_metadata(
        annotated(effective_from="2026-11-13", effective_until="2026-11-13"), scope
    )
    assert matches_metadata(
        annotated(effective_from="2026-01-01", effective_until="2026-12-31"), scope
    )
    assert not matches_metadata(
        annotated(effective_from="2025-01-01", effective_until="2026-11-12"), scope
    )
    assert not matches_metadata(
        annotated(effective_from="2026-11-14", effective_until="2027-01-01"), scope
    )


def test_unknown_validity_never_matches_a_date_filter():
    scope = MetadataFilter(effective_on="2026-11-13")
    assert not matches_metadata(annotated(), scope)
    assert not matches_metadata(annotated(effective_from=None), scope)
    assert not matches_metadata(None, scope)


def test_effective_dates_conjoin_with_the_same_annotation_only():
    structure = {
        "retrieval_metadata": [
            {"values": {"program": "A", "effective_from": "2026-01-01"}},
            {"values": {"program": "B"}},
        ]
    }
    assert matches_metadata(structure, MetadataFilter(program="A", effective_on="2026-11-13"))
    assert not matches_metadata(structure, MetadataFilter(program="B", effective_on="2026-11-13"))
