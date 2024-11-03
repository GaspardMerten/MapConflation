import json
import logging
import os
from typing import List

import geopandas as gpd
import networkx as nx
import pyproj
from shapely import LineString

from src.conflate.simple import SimpleConflater
from src.graph.io import (
    load_graph_from_edges_and_nodes_df,
    save_graph_to_gml,
    load_graph_from_gml,
    load_graph_from_osm,
)
from src.graph.plot import plot_graphs, plot_graphs_with_results
from src.graph.transform import reduce_bounding_box, crop_graph
from src.map_matching.leuven import LeuvenMapMatching
from src.trajectory.generate import generate_trajectories_new
from src.types import TrajectoryIds, Trajectory


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
        for _ in range(10):
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


def insert_edge_geometry(graph):
    for u, v, data in graph.edges(data=True):
        node_u = graph.nodes[u]
        node_v = graph.nodes[v]
        data["geometry"] = LineString(
            [(node_u["x"], node_u["y"]), (node_v["x"], node_v["y"])]
        )
    # Ensure geometry are crs aware
    graph.graph["crs"] = pyproj.CRS("EPSG:4326")
    return graph


def make_edge_both_directions(graph):
    for u, v, data in list(graph.edges(data=True)):
        graph.add_edge(v, u, **data)
    return graph


def compute_or_load_matched_ids(
    path: str,
    graph_b: nx.Graph,
    trajectories: List[Trajectory],
    trajectories_ids: List[TrajectoryIds],
):
    if os.path.exists(path):
        matches = json.load(open(path, "r"))
    else:
        map_matching = LeuvenMapMatching(graph_b)
        matches = map_matching.match_trajectories(
            trajectories,
            trajectories_ids,
        )
        json.dump(matches, open(path, "w"))
    return matches


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    graph_b = load_or_create("out/graph_b.gml")
    graph_b = graph_b.subgraph(max(nx.connected_components(graph_b), key=len))
    graph_b = nodes_and_edges_to_int(graph_b)
    logging.info("Loaded graph B")

    graph_a = prepare_and_load_graph_a("out/graph_a.gml")
    graph_a = graph_a.subgraph(max(nx.connected_components(graph_a), key=len))
    graph_a = nodes_and_edges_to_int(graph_a)
    logging.info("Loaded graph A")

    trajectories_ids = cache_generate_trajectories_id(
        graph_a, "out/trajectories_id.json"
    )

    a = len(trajectories_ids) // 10
    logging.info("Generated trajectories ids")

    trajectories = cache_trajectories(
        graph_a, trajectories_ids, "out/trajectories.json"
    )

    logging.info("Generated trajectories")

    matched_ids = compute_or_load_matched_ids(
        f"out/matches.json", graph_b, trajectories, trajectories_ids
    )

    conflater = SimpleConflater(graph_a, graph_b, matched_ids)
    results = conflater.conflate()

    plot_graphs(graph_a, graph_b, "graphs.html")
    plot_graphs_with_results(graph_a, graph_b, results, "graphs.html")
