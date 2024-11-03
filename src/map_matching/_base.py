from abc import ABC, abstractmethod
from typing import List

import networkx as nx

from src.types import Trajectory, Match, TrajectoryIds


class MapMatching(ABC):
    def __init__(self, graph: nx.Graph):
        self.graph = graph

        # Ensure x,y are present in the nodes
        assert all(
            "x" in data and "y" in data for _, data in graph.nodes(data=True)
        ), "All nodes in the graph should have x and y coordinates (graph_a)"

    @abstractmethod
    def match_trajectory(self, trajectory: Trajectory) -> List[Match]:
        """
        Match a trajectory to the graph.

        :param trajectory: A trajectory
        :return: A list of matched nodes
        """
        raise NotImplementedError

    @abstractmethod
    def match_trajectories(
        self,
        trajectories: List[Trajectory],
        trajectories_ids: List[TrajectoryIds],
        processes: int,
    ) -> List[Match]:
        """
        Match multiple trajectories to the graph.

        :param trajectories: A list of trajectories
        :param processes: The number of processes to use
        :return: A generator of matched nodes
        """
        raise NotImplementedError
