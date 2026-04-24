import pytest
from app.projection import normalize, point_to_line_distance, query_projection


def test_normalize_unit():
    assert normalize((3, 0, 0)) == (1.0, 0.0, 0.0)
    assert normalize((0, 4, 0)) == (0.0, 1.0, 0.0)


def test_normalize_diagonal():
    r = normalize((1, 1, 0))
    assert abs(r[0] - 0.7071) < 0.01
    assert abs(r[1] - 0.7071) < 0.01


def test_normalize_zero():
    with pytest.raises(ValueError):
        normalize((0, 0, 0))


def test_point_on_line():
    assert point_to_line_distance((5, 0, 0), (0, 0, 0), (1, 0, 0)) == 0.0


def test_point_perpendicular():
    dist = point_to_line_distance((0, 3, 0), (0, 0, 0), (1, 0, 0))
    assert abs(dist - 3.0) < 1e-9


def test_point_diagonal_line():
    dist = point_to_line_distance((1, 1, 0), (0, 0, 0), normalize((1, 1, 0)))
    assert abs(dist) < 1e-9


def test_query_intersect():
    spheres = [
        {"id": 1, "radius": 1.0, "calculated_x": 5, "calculated_y": 0, "calculated_z": 0},
        {"id": 2, "radius": 1.0, "calculated_x": 0, "calculated_y": 3, "calculated_z": 0},
        {"id": 3, "radius": 1.0, "calculated_x": 0, "calculated_y": 10, "calculated_z": 0},
    ]
    results = query_projection(spheres, (0, 0, 0), (1, 0, 0), 3.0, "intersect")
    ids = [r[0]["id"] for r in results]
    assert 1 in ids
    assert 2 in ids
    assert 3 not in ids


def test_query_contain():
    spheres = [
        {"id": 1, "radius": 0.5, "calculated_x": 5, "calculated_y": 0, "calculated_z": 0},
        {"id": 2, "radius": 1.0, "calculated_x": 0, "calculated_y": 2.5, "calculated_z": 0},
    ]
    results = query_projection(spheres, (0, 0, 0), (1, 0, 0), 3.0, "contain")
    ids = [r[0]["id"] for r in results]
    assert 1 in ids
    assert 2 not in ids


def test_query_both():
    spheres = [
        {"id": 1, "radius": 0.5, "calculated_x": 5, "calculated_y": 0, "calculated_z": 0},
        {"id": 2, "radius": 1.0, "calculated_x": 0, "calculated_y": 2.5, "calculated_z": 0},
    ]
    results = query_projection(spheres, (0, 0, 0), (1, 0, 0), 3.0, "both")
    ids = [r[0]["id"] for r in results]
    types = {r[0]["id"]: r[1] for r in results}
    assert 1 in ids and types[1] == "contain"
    assert 2 in ids and types[2] == "intersect"
