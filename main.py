import json
import logging
import os
import random

import geopandas as gpd
import networkx as nx

from src.conflate.simple import SimpleConflater
from src.graph.io import (
    load_graph_from_edges_and_nodes_df,
    save_graph_to_gml,
    load_graph_from_gml,
    load_graph_from_osm,
)
from src.graph.plot import plot_graphs_with_results
from src.graph.transform import reduce_bounding_box, crop_graph
from src.map_matching.leuven import LeuvenMapMatching
from src.trajectory.generate import generate_trajectories_new
from src.types import ConflationResult


def load_or_create(path: str):
    if os.path.exists(path):
        graph = load_graph_from_gml(path)
    else:
        edges_gdf = gpd.read_file("resources/edges.geojson")
        nodes_gdf = gpd.read_file("resources/nodes.geojson")

        graph = load_graph_from_edges_and_nodes_df(
            edges_gdf,
            nodes_gdf,
            start_node_key="start_node",
            end_node_key="end_node",
            node_id_key="gml_id",
            node_x_key=lambda x: x["geometry"].x,
            node_y_key=lambda x: x["geometry"].y,
            edge_geometry_key=lambda x: x["geometry"],
        )

        save_graph_to_gml(path, graph)

    return graph


def prepare_and_load_graph_a(path: str):
    if os.path.exists(path):
        graph_a = load_graph_from_gml(path)
    else:
        graph_a = load_graph_from_osm(
            (50.8477, 4.3572),
            7000,
        )
        graph_b_reduced_bounding_box = reduce_bounding_box(graph_b, 0.1)
        graph_a = crop_graph(graph_a, *graph_b_reduced_bounding_box)
        save_graph_to_gml(path, graph_a)
    return graph_a


def cache_generate_trajectories_id(graph, path):
    if os.path.exists(path):
        trajectories = json.load(open(path, "r"))
    else:
        trajectories = []
        for _ in range(3):
            print("Trajectory", _)
            trajectories += generate_trajectories_new(graph)
        json.dump(trajectories, open(path, "w"))
    return trajectories


def cache_trajectories(graph_a, trajectories_ids, path):
    if os.path.exists(path):
        trajectories = json.load(open(path, "r"))
    else:
        trajectories = [
            [
                (graph_a.nodes[node_id]["x"], graph_a.nodes[node_id]["y"])
                for node_id in trajectory
            ]
            for trajectory in trajectories_ids
        ]
        json.dump(trajectories, open(path, "w"))
    return trajectories


def nodes_and_edges_to_int(graph):
    mapping = {node: int(float(node)) for node in graph.nodes}
    graph = nx.relabel_nodes(graph, mapping)
    return graph


def insert_node_at_edge(graph, edge, new_node_id, x, y):
    """
    Insert a node in the edge (u, v) of the graph.
    :param graph: The graph to insert the node
    :param edge: The edge to insert the node
    :param new_node_id: The new node to insert
    :param x: The x coordinate of the new node
    :param y: The y coordinate of the new node
    :return: The new graph with the node inserted
    """

    if not graph.has_edge(edge[0], edge[1]):
        return graph
    graph.add_node(new_node_id, x=x, y=y)
    graph.add_edge(edge[0], new_node_id)
    graph.add_edge(new_node_id, edge[1])
    # remove the original edge
    graph.remove_edge(edge[0], edge[1])

    return graph


def make_edge_both_directions(graph):
    for u, v, data in list(graph.edges(data=True)):
        graph.add_edge(v, u, **data)
    return graph


def compute_or_load_matched_ids(
    path: str,
    graph_b: nx.Graph,
):
    if os.path.exists(path):
        matches = json.load(open(path, "r"))
    else:
        trajectories_ids = cache_generate_trajectories_id(
            graph_a, "out/trajectories_id.json"
        )

        a = len(trajectories_ids) // 10
        logging.info("Generated trajectories ids")

        trajectories = cache_trajectories(
            graph_a, trajectories_ids, "out/trajectories.json"
        )

        logging.info("Generated trajectories")
        map_matching = LeuvenMapMatching(graph_b)
        matches = map_matching.match_trajectories(
            trajectories,
            trajectories_ids,
        )
        json.dump(matches, open(path, "w"))
    return matches


def add_random_speed_valus_to_graph(graph):
    for u, v, data in graph.edges(data=True):
        data["speed"] = random.randint(1, 10)
    return graph


def insert_node_at_edge(graph, edge, new_node_id, x, y):
    """
    Insert a node in the edge (u, v) of the graph.
    :param graph: The graph to insert the node
    :param edge: The edge to insert the node
    :param new_node_id: The new node to insert
    :param x: The x coordinate of the new node
    :param y: The y coordinate of the new node
    :return: The new graph with the node inserted
    """

    if not graph.has_edge(edge[0], edge[1]):
        return graph
    graph.add_node(new_node_id, x=x, y=y)
    graph.add_edge(edge[0], new_node_id)
    graph.add_edge(new_node_id, edge[1])
    # remove the original edge
    graph.remove_edge(edge[0], edge[1])

    return graph


def load_or_conflate(graph_a, graph_b, matched_ids, path):
    if os.path.exists(path):
        results = json.load(open(path, "r"))
        return [ConflationResult.from_json(result) for result in results]
    else:
        conflater = SimpleConflater(graph_a, graph_b, matched_ids)
        results = conflater.conflate()

        json.dump([
            result.to_json() for result in results
        ], open(path, "w"))
        return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    graph_b = load_or_create("out/graph_b.gml")
    graph_b = graph_b.subgraph(max(nx.connected_components(graph_b), key=len))
    graph_b = nodes_and_edges_to_int(graph_b)
    graph_b = add_random_speed_valus_to_graph(graph_b)
    logging.info("Loaded graph B")

    graph_a = prepare_and_load_graph_a("out/graph_a.gml")
    graph_a = graph_a.subgraph(max(nx.connected_components(graph_a), key=len))
    graph_a = nodes_and_edges_to_int(graph_a)
    logging.info("Loaded graph A")

    matched_ids = compute_or_load_matched_ids(f"out/matches.json", graph_b)
    logging.info("Computed matches")

    results = load_or_conflate(
        graph_a,
        graph_b,
        matched_ids[:5000],
        "out/results.json",
    )

    results_map = {result.point_b: result for result in results}

    for edge in graph_b.edges:
        # Check if both start and end nodes are in the results
        if edge[0] not in results_map or edge[1] not in results_map:
            continue

        node_b_start = results_map[edge[0]]
        node_b_end = results_map[edge[1]]
        new_node_id_start = f"graph_b_{node_b_start.point_b}"
        new_node_id_end = f"graph_b_{node_b_end.point_b}"

        insert_node_at_edge(
            graph_a,
            node_b_start.segment_a_id,
            new_node_id_start,
            node_b_start.point_b_on_segment_a[0],
            node_b_start.point_b_on_segment_a[1],
        )

        insert_node_at_edge(
            graph_a,
            node_b_end.segment_a_id,
            new_node_id_end,
            node_b_end.point_b_on_segment_a[0],
            node_b_end.point_b_on_segment_a[1],
        )

        try:
            shortest_path = nx.shortest_path(graph_a, new_node_id_start, new_node_id_end)

            for i in range(len(shortest_path) - 1):
                u, v = shortest_path[i], shortest_path[i + 1]
                graph_a[u][v]["speed"] = graph_b[edge[0]][edge[1]]["speed"]
        except Exception:
            print("No path")
    plot_graphs_with_results(graph_a, graph_b, results, "graphs.html")
