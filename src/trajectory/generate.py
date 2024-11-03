import itertools
import logging
import random
from multiprocessing import Pool, cpu_count
from typing import Any, List

import networkx as nx
import numpy as np
from scipy.spatial import ConvexHull


def _nodes_on_the_edge_of_convex_hull(graph: nx.Graph) -> List[Any]:
    """
    Find the nodes that are on the edge of the convex hull of the graph.

    :param graph: A NetworkX graph
    :return: A list of nodes that are on the edge of the convex hull
    """
    node_id = []
    coordinates = []

    for node in graph.nodes(data=True):
        node_id.append(node[0])
        coordinates.append((node[1]["x"], node[1]["y"]))

    hull = ConvexHull(np.array(coordinates))

    return [node_id[i] for i in hull.vertices]


def _generate_path(graph: nx.Graph, source: Any, target: Any) -> List[Any]:
    """
    Find the shortest path between two nodes using a greedy algorithm, use the
    euclidean distance as the heuristic.
    """

    path = [source]

    while path[-1] != target:
        current_node = path[-1]
        neighbors = list(graph.neighbors(current_node))
        best_neighbor = None
        best_distance = float("inf")

        for neighbor in neighbors:
            if neighbor in path:
                continue
            distance = np.linalg.norm(
                np.array(
                    [
                        graph.nodes[current_node]["x"] - graph.nodes[neighbor]["x"],
                        graph.nodes[current_node]["y"] - graph.nodes[neighbor]["y"],
                    ]
                )
            )
            if distance < best_distance:
                best_distance = distance
                best_neighbor = neighbor

        if best_neighbor is None:
            break

        path.append(best_neighbor)

    return path


def process_node(args):
    graph, random_node, boundary, min_path_length = args
    path = _generate_path(graph, random_node, boundary)

    # Check if path length is smaller than minimum, try shortest path
    if len(path) < min_path_length:
        path = nx.shortest_path(graph, source=random_node, target=boundary)

    # If still shorter, discard the path
    if len(path) < min_path_length:
        return None  # Signal to discard this path

    logging.debug(f"Path from {random_node} to {boundary}: length {len(path)}")
    return path


def parallel_path_computation(graph, unvisited_nodes, edge_nodes, min_path_length):
    all_nodes = list(graph.nodes())
    paths = []

    # Create a multiprocessing pool
    processes = max(1, cpu_count() - 4)

    logging.debug(f"Using {processes} processes")

    with Pool(processes=processes) as pool:
        while unvisited_nodes:
            logging.debug(
                f"Computing path from random node to edge, still {len(unvisited_nodes)} nodes to visit, {len(paths)} paths"
            )

            tasks = []

            # Prepare the tasks for parallel processing
            for _ in range(min(len(unvisited_nodes), cpu_count() * 100)):
                random_node = random.choice(list(unvisited_nodes))
                other_node = random.choice(all_nodes)
                tasks.append((graph, random_node, other_node, min_path_length))

            # Process the tasks in parallel
            results = pool.map(process_node, tasks)

            # Collect paths and remove visited nodes
            for path in results:
                if path:
                    unvisited_nodes -= set(path)
                    paths.append(path)

    return paths


def generate_trajectories_new(
    graph: nx.Graph,
    min_path_length: int = 100,
):
    logging.info("Generating trajectories")
    unvisited_nodes = set(graph.nodes())
    edge_nodes = _nodes_on_the_edge_of_convex_hull(graph)
    # For each combination of two edge nodes, find the shortest path between them
    paths = []

    for i, j in itertools.combinations(edge_nodes, 2):
        logging.debug(f"Computing path between {i} and {j}")
        path = nx.shortest_path(graph, source=i, target=j, method="dijkstra")
        unvisited_nodes -= set(path)
        paths.append(path)

    paths += parallel_path_computation(
        graph, unvisited_nodes, edge_nodes, min_path_length
    )

    logging.info(f"Generated {len(paths)} trajectories")

    return paths
