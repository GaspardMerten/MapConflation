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
