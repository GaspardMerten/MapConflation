from typing import Tuple

import networkx as nx
import osmnx as ox
import pandas as pd

from src.graph.transform import split_edges


def load_graph_from_osm(
    center: Tuple[float, float],
    distance: int,
    network_type: str = "drive",
    simplify: bool = False,
) -> nx.Graph:
    """
    Create a graph from OpenStreetMap data.

    :param center: The center of the area to download
    :param distance: The distance in meters from the center
    :param network_type: The type of network to download
    :param simplify: Whether to simplify the graph
    :return: A NetworkX graph
    """
    return ox.graph_from_point(
        center, distance, network_type=network_type, simplify=simplify
    )


def load_graph_from_edges_and_nodes_df(
    edges_gdf: pd.DataFrame,
    nodes_gdf: pd.DataFrame,
    start_node_key: str = "u",
    end_node_key: str = "v",
    node_id_key: str = "node_id",
    node_x_key: callable = lambda x: x["geometry"].x,
    node_y_key: callable = lambda x: x["geometry"].y,
    edge_geometry_key: callable = None,
) -> nx.Graph:
    """
    Create a graph from edges and nodes GeoDataFrames.

    :param edges_gdf: GeoDataFrame with edges
    :param nodes_gdf: GeoDataFrame with nodes
    :param start_node_key: Key in the edges GeoDataFrame for the start node
    :param end_node_key: Key in the edges GeoDataFrame for the end node
    :param node_id_key: Key in the nodes GeoDataFrame for the node id
    :param node_x_key: Key in the nodes GeoDataFrame for the x coordinate
    :param node_y_key: Key in the nodes GeoDataFrame for the y coordinate
    :param edge_geometry_key: Key in the edges GeoDataFrame for the edge geometry
    :return: A NetworkX graph
    """

    graph = nx.Graph()

    transformed_nodes_df = nodes_gdf.apply(
        lambda x: pd.Series(
            {
                "node_id": x[node_id_key],
                "x": node_x_key(x),
                "y": node_y_key(x),
            }
        ),
        axis=1,
    )

    transformed_edges_df = edges_gdf.apply(
        lambda x: pd.Series(
            {
                "u": x[start_node_key],
                "v": x[end_node_key],
                "geometry": (
                    edge_geometry_key(x) if edge_geometry_key is not None else None
                ),
            }
        ),
        axis=1,
    )

    if edge_geometry_key is not None:
        transformed_edges_df, transformed_nodes_df = split_edges(
            transformed_edges_df, transformed_nodes_df
        )

    graph.add_nodes_from(
        transformed_nodes_df.set_index("node_id").to_dict("index").items()
    )

    for _, edge in transformed_edges_df.iterrows():
        if edge["u"] in graph.nodes and edge["v"] in graph.nodes:
            graph.add_edge(edge["u"], edge["v"], geometry=edge.get("geometry"))

    return graph


def save_graph_to_gml(output_path: str, graph: nx.Graph):
    """
    Save a graph to a file.

    :param output_path: Path to the output file
    :param graph: A NetworkX graph
    """
    # Transform edge geometry to a string
    for u, v, data in graph.edges(data=True):
        if "geometry" in data:
            data["geometry"] = str(data["geometry"])
    nx.write_gml(graph, output_path)


def load_graph_from_gml(input_path: str) -> nx.Graph:
    """
    Load a graph from a file.

    :param input_path: Path to the input file
    :return: A NetworkX graph
    """
    return nx.read_gml(input_path)
