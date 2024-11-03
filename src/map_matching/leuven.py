import json
import os
import uuid
from multiprocessing import Pool, cpu_count
from typing import List, Any, Tuple

import networkx as nx
from leuvenmapmatching.map.inmem import InMemMap
from leuvenmapmatching.matcher.distance import DistanceMatcher
from tqdm import tqdm

from src.map_matching import MapMatching
from src.types import Match, Trajectory, TrajectoryIds


def prepare_in_mem_map(graph: nx.Graph, x_key="x", y_key="y") -> InMemMap:
    """
    Prepare an InMemMap object from a graph.

    :param graph: A directed graph
    :param x_key: The key in the node attributes to use as x coordinate
    :param y_key: The key in the node attributes to use as y coordinate
    :return: An InMemMap object
    """

    map_con = InMemMap(
        str(uuid.uuid4()), use_latlon=True, use_rtree=True, index_edges=True
    )

    for node, data in graph.nodes(data=True):
        map_con.add_node(node, (data[x_key], data[y_key]))

    for a, b, *_ in graph.edges:
        try:
            map_con.add_edge(a, b)
            map_con.add_edge(b, a)
        except Exception as e:
            print(a, b, e)
    map_con = map_con.to_xy()

    return map_con


class LeuvenMapMatching(MapMatching):

    def __init__(self, graph: nx.Graph):
        super().__init__(graph)
        self.in_memory_map = None
        self.settings = dict(
            max_dist=100,
            max_dist_init=25,  # meter
            min_prob_norm=0.001,
            non_emitting_length_factor=0.75,
            obs_noise=50,
            obs_noise_ne=75,  # meter
            dist_noise=50,  # meter
            non_emitting_states=True,
            max_lattice_width=5,
        )

    def get_in_memory_map(self) -> InMemMap:
        if self.in_memory_map is None:
            self.in_memory_map = prepare_in_mem_map(self.graph)
        return self.in_memory_map

    def _match(self, trajectory: Trajectory, in_memory_map: InMemMap) -> List[Any]:
        matcher = DistanceMatcher(
            in_memory_map,
            **self.settings,
        )
        path = list(self.in_memory_map.latlon2yx(*coords) for coords in trajectory)
        states, _ = matcher.match(path)
        return list(map(lambda x: x[0], states)) if states else []

    def match_trajectory(self, trajectory: Trajectory) -> List[Any]:
        return self._match(trajectory, self.get_in_memory_map())

    def _match_batch(
        self, batch: Tuple[List[Trajectory], List[TrajectoryIds]]
    ) -> List[Match]:
        in_memory_map = self.get_in_memory_map()
        result = []

        for trajectory, ids in tqdm(
            zip(*batch),
            total=len(
                batch[0],
            ),
        ):
            result.append((ids, trajectory, self._match(trajectory, in_memory_map)))

        del in_memory_map
        json.dump(result, open(f"resources/{uuid.uuid4()}.json", "w"))
        return result

    def match_trajectories(
        self,
        trajectories: List[Trajectory],
        trajectories_ids: List[TrajectoryIds],
        processes: int = max(1, 10),
    ) -> List[Match]:
        all_matches = []

        # Iterate over large batches
        for large_batch in tqdm(range(0, len(trajectories), 1000), desc="Large batch"):
            batch_key = large_batch  # Use the starting index as the identifier
            batch_filename = f"range_{batch_key}.json"

            # Skip this batch if its file already exists
            if os.path.exists(batch_filename):
                # Load existing results from the file
                with open(batch_filename, "r") as file:
                    batch_matches = json.load(file)
                all_matches.extend(batch_matches)
                continue

            large_batch_trajectories = trajectories[large_batch : large_batch + 1000]
            large_batch_trajectories_ids = trajectories_ids[
                large_batch : large_batch + 1000
            ]
            batch_matches = []

            with Pool(processes) as pool:
                # Split the trajectories in smaller batches
                batch_size = len(large_batch_trajectories) // processes
                batches = [
                    (
                        large_batch_trajectories[i : i + batch_size],
                        large_batch_trajectories_ids[i : i + batch_size],
                    )
                    for i in range(0, len(large_batch_trajectories), batch_size)
                ]

                # Process the smaller batches in parallel
                for result in pool.map(self._match_batch, batches):
                    batch_matches.extend(result)

                pool.close()

            # Save the results of this batch to its own JSON file
            with open(batch_filename, "w") as file:
                json.dump(batch_matches, file)

            # Add this batch's matches to the final result
            all_matches.extend(batch_matches)

        return all_matches
