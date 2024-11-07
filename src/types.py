from dataclasses import dataclass
from typing import List, Tuple

TrajectoryIds = List[int]
Trajectory = List[Tuple[float, float]]
Match = Tuple[TrajectoryIds, Trajectory, TrajectoryIds]


@dataclass(frozen=True, slots=True)
class ConflationResult:
    segment_a_id: Tuple[int, int]
    segment_a_coords: Tuple[Tuple[float, float], Tuple[float, float]]
    point_b: int
    point_b_coords: Tuple[float, float]
    point_b_on_segment_a: Tuple[float, float]
    number_of_votes: int

    def to_json(self):
        return {
            "segment_a_id": self.segment_a_id,
            "segment_a_coords": self.segment_a_coords,
            "point_b": self.point_b,
            "point_b_coords": self.point_b_coords,
            "point_b_on_segment_a": self.point_b_on_segment_a,
            "number_of_votes": self.number_of_votes
        }

    def from_json(self, json_data):
        return ConflationResult(
            segment_a_id=json_data["segment_a_id"],
            segment_a_coords=json_data["segment_a_coords"],
            point_b=json_data["point_b"],
            point_b_coords=json_data["point_b_coords"],
            point_b_on_segment_a=json_data["point_b_on_segment_a"],
            number_of_votes=json_data["number_of_votes"]
        )
