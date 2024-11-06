import math
from collections import defaultdict
from typing import Generator, Tuple, List

from shapely import LineString, Point
from tqdm import tqdm

from src.conflate._base import Conflater
from src.types import Match, ConflationResult


def point_to_segment_distance(P, A, B):
    Px, Py = P
    Ax, Ay = A
    Bx, By = B

    # Calculate the squared length of the segment (A to B)
    segment_length_squared = (Bx - Ax) ** 2 + (By - Ay) ** 2

    # If A and B are the same point, return the distance from P to A
    if segment_length_squared == 0:
        return math.sqrt((Px - Ax) ** 2 + (Py - Ay) ** 2)

    # Projection factor of P onto the line AB, normalized by the segment length
    t = max(0, min(1, ((Px - Ax) * (Bx - Ax) + (Py - Ay) * (By - Ay)) / segment_length_squared))

    # Find the closest point on the segment to P
    closest_x = Ax + t * (Bx - Ax)
    closest_y = Ay + t * (By - Ay)

    # Calculate the distance from P to this closest point
    distance = math.sqrt((Px - closest_x) ** 2 + (Py - closest_y) ** 2)

    return distance


class SimpleConflater(Conflater):
    def __init__(self, *args, trace_b_min_length=50, **kwargs):
        """
        :param trace_b_min_length: The minimum length of trace_b
        """
        super().__init__(*args, **kwargs)
        self.trace_b_min_length = trace_b_min_length

    def filtered_match(self) -> Generator[Match, None, None]:
        skipped = 0
        not_skipped = 0
        for match in self.matches:
            _, trace_b = match[0], match[2]
            if len(trace_b) < self.trace_b_min_length:
                skipped += 1
                continue
            not_skipped += 1
            print(f"Skipped: {skipped}, Not Skipped: {not_skipped}")
            yield match

    def _coord_from_node_a(self, node_a) -> Tuple[float, float]:
        return self.graph_a.nodes[node_a]["x"], self.graph_a.nodes[node_a]["y"]

    def _coord_from_node_b(self, node_b) -> Tuple[float, float]:
        return self.graph_b.nodes[node_b]["x"], self.graph_b.nodes[node_b]["y"]

    def _distance_node_a_node_b(self, node_a, node_b) -> float:
        x_a, y_a = self._coord_from_node_a(node_a)
        x_b, y_b = self._coord_from_node_b(node_b)
        return (x_a - x_b) ** 2 + (y_a - y_b) ** 2

    def _find_closest_node(self, id_b, sub_path_a) -> Tuple[int, float, int, list]:
        smallest_distance = float("inf")
        closest_node = None
        closest_next_node = None
        id_b_point = self._coord_from_node_b(id_b)

        for index, (node, next_node) in enumerate(zip(sub_path_a[:-1], sub_path_a[1:])):
            # Compute perpendicular distance
            x1, y1 = self._coord_from_node_a(node)
            x2, y2 = self._coord_from_node_a(next_node)
            x, y = id_b_point

            distance = point_to_segment_distance((x, y), (x1, y1), (x2, y2))

            if distance < smallest_distance:
                smallest_distance = distance
                closest_node = node
                closest_next_node = next_node

        return closest_node, smallest_distance, closest_next_node, sub_path_a

    def _project_point(self, segment, point) -> Tuple[float, float]:
        x1, y1 = self._coord_from_node_a(segment[0])
        x2, y2 = self._coord_from_node_a(segment[1])
        x, y = self._coord_from_node_b(point)

        p1 = Point(x1, y1)
        p2 = Point(x2, y2)

        p = Point(x, y)

        result = p.project(LineString([p1, p2]))

        return result.x, result.y

    def conflate(self) -> List[ConflationResult]:
        match_count = defaultdict(lambda: defaultdict(int))

        for match in self.filtered_match():
            trace_a, _, trace_b = match
            trace_b = list(map(lambda x: x, trace_b))[5:-5]

            for point in trace_b:
                closest_node, closest_distance, closest_next_node, _ = (
                    self._find_closest_node(point, trace_a)
                )

                if closest_node is None:
                    continue

                print(closest_node,closest_next_node)
                match_count[point][(closest_node, closest_next_node)] += 1

        # Majority voting
        match = []

        for point, closest_nodes in tqdm(list(match_count.items())):
            segment = max(closest_nodes, key=closest_nodes.get)
            match.append(
                ConflationResult(
                    segment,
                    (
                        self._coord_from_node_a(segment[0]),
                        self._coord_from_node_a(segment[1]),
                    ),
                    point,
                    self._coord_from_node_b(point),
                    self._project_point(segment, point),
                    closest_nodes[segment],
                )
            )

        return match
