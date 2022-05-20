from pfun import Intersection


def test_intersection_is_subscriptable():
    assert Intersection[int] == Intersection
    assert Intersection[int, int] == Intersection
    assert Intersection[int, int, int] == Intersection
