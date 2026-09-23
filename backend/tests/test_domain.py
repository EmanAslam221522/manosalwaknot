from decimal import Decimal

from app.domain import distance_km, pagination


def test_pagination_uses_ceiling_and_handles_empty_results() -> None:
    assert pagination(41, 2, 20).model_dump() == {
        "page": 2,
        "page_size": 20,
        "total_items": 41,
        "total_pages": 3,
    }
    assert pagination(0, 1, 20).total_pages == 0


def test_distance_is_stable_for_haripur_area_coordinates() -> None:
    distance = distance_km(33.9946, 72.9106, Decimal("34.0040"), Decimal("72.9200"))
    assert 1.2 <= distance <= 1.5
