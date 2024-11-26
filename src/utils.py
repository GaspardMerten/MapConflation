import json
import logging
import os
import random

import geopandas as gpd
import networkx as nx

from src.conflate.simple import SimpleConflater
from src.enrich.enrich import enrich
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


def load_or_create_geojson_graph(
    path: str,
    edges_gdf_path: str = "resources/edges.geojson",
    nodes_gdf_path: str = "resources/nodes.geojson",
):
    if os.path.exists(path):
        graph = load_graph_from_gml(path)
    else:
        edges_gdf = gpd.read_file(edges_gdf_path)
        nodes_gdf = gpd.read_file(nodes_gdf_path)

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


def prepare_and_load_osm(path: str,graph_b=None,distance=7000):
    if os.path.exists(path):
        graph_a = load_graph_from_gml(path)
    else:
        graph_a = load_graph_from_osm(
            (50.8477, 4.3572),
            distance,
        )
        # Transform to non-directed graph
        graph_a = nx.Graph(graph_a)
        if graph_b is not None:
            graph_b_reduced_bounding_box = reduce_bounding_box(graph_b, 0.1)
            graph_a = crop_graph(graph_a, *graph_b_reduced_bounding_box)
        save_graph_to_gml(path, graph_a)
    return graph_a


def cache_generate_trajectories_id(graph, path):
    if os.path.exists(path):
        trajectories = json.load(open(path, "r"))
    else:
        trajectories = []
        for _ in range(1):
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


def compute_or_load_matched_ids(
    graph_a: nx.Graph,
    graph_b: nx.Graph,
    path: str,
    trajectories_id_path: str = "out/trajectories_id.json",
    trajectories_path: str = "out/trajectories.json",
):
    """
    Compute or load the matched ids between two graphs.
    :param graph_a:
    :param graph_b:
    :param path:
    :return:
    """
    if os.path.exists(path):
        matches = json.load(open(path, "r"))
    else:
        trajectories_ids = cache_generate_trajectories_id(
            graph_a, trajectories_id_path
        )

        logging.info("Generated trajectories ids")

        trajectories = cache_trajectories(
            graph_a, trajectories_ids, trajectories_path
        )

        logging.info("Generated trajectories")
        map_matching = LeuvenMapMatching(graph_b)
        matches = map_matching.match_trajectories(
            trajectories,
            trajectories_ids,
            8
        )

        json.dump(matches, open(path, "w"))

    return matches


def add_random_speed_valus_to_graph(graph):
    for u, v, data in graph.edges(data=True):
        data["speed"] = random.randint(1, 10)
    return graph


def nodes_and_edges_to_int(graph):
    mapping = {node: int(float(node)) for node in graph.nodes}
    graph = nx.relabel_nodes(graph, mapping)
    return graph


def load_or_conflate(graph_a, graph_b, matched_ids, path):
    if os.path.exists(path):
        results = json.load(open(path, "r"))
        return [ConflationResult.from_json(result) for result in results]
    else:
        conflater = SimpleConflater(graph_a, graph_b, matched_ids)
        results = conflater.conflate()

        json.dump([result.to_json() for result in results], open(path, "w"))
        return results
