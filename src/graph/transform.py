import logging
import random
from typing import Tuple

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from shapely.geometry import LineString


def split_edges(
    edges_gdf: gpd.GeoDataFrame,
    nodes_gdf: gpd.GeoDataFrame,
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Split edges into smaller edges with only two nodes. The function returns
    a new edges GeoDataFrame and a new nodes GeoDataFrame. The new ids are
    generated by incrementing the maximum id in the nodes GeoDataFrame.
    :param edges_gdf: The edges GeoDataFrame
    :param nodes_gdf: The nodes GeoDataFrame
    :return: A tuple with the new edges and nodes GeoDataFrames
    """
    new_nodes = []
    new_edges = []
    base_id = nodes_gdf["node_id"].max() + 1

    for _, edge in edges_gdf.iterrows():
        geometry = edge["geometry"]
        if isinstance(geometry, LineString):
            coords = list(geometry.coords)
            prev_node = edge["u"]

            for i in range(1, len(coords)):
                new_node = {
                    "node_id": base_id,
                    "x": coords[i][0],
                    "y": coords[i][1],
                }
                new_nodes.append(new_node)

                new_edges.append(
                    {
                        "u": prev_node,
                        "v": base_id,
                        "geometry": LineString([coords[i - 1], coords[i]]),
                    }
                )
                prev_node = base_id
                base_id += 1

            # Add the last edge from the last new node to the original end node
            new_edges.append(
                {
                    "u": prev_node,
                    "v": edge["v"],
                    "geometry": LineString([coords[-2], coords[-1]]),
                }
            )

    return gpd.GeoDataFrame(new_edges), gpd.GeoDataFrame(
        pd.concat([nodes_gdf, gpd.GeoDataFrame(new_nodes)], ignore_index=True)
    )


def bounding_box_from_graph(graph: nx.Graph) -> Tuple[float, float, float, float]:
    """
    Compute the bounding box of a graph.
    :param graph: A NetworkX graph
    :return: A tuple with the bounding box coordinates (min_x, min_y, max_x, max_y)
    """
    min_x, min_y, max_x, max_y = (
        float("inf"),
        float("inf"),
        float("-inf"),
        float("-inf"),
    )
    for node in graph.nodes(data=True):
        x, y = node[1]["x"], node[1]["y"]
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)

    return min_x, min_y, max_x, max_y


def reduce_bounding_box(
    graph: nx.Graph, factor: float = 0.1
) -> Tuple[float, float, float, float]:
    """
    Reduce the bounding box of a graph by a factor.
    :param graph: A NetworkX graph
    :param factor: The factor to reduce the bounding box
    :return: A tuple with the reduced bounding box coordinates (min_x, min_y, max_x, max_y)
    """
    min_x, min_y, max_x, max_y = bounding_box_from_graph(graph)
    width = max_x - min_x
    height = max_y - min_y
    min_x += width * factor
    min_y += height * factor
    max_x -= width * factor
    max_y -= height * factor

    return min_x, min_y, max_x, max_y


def crop_graph(
    graph: nx.Graph, min_x: float, min_y: float, max_x: float, max_y: float
) -> nx.Graph:
    """
    Crop a graph to a bounding box.
    :param graph: A NetworkX graph
    :param min_x: The minimum x coordinate
    :param min_y: The minimum y coordinate
    :param max_x: The maximum x coordinate
    :param max_y: The maximum y coordinate
    :return: A new NetworkX graph
    """
    cropped_graph = nx.Graph()
    for node in graph.nodes(data=True):
        x, y = node[1]["x"], node[1]["y"]
        if min_x <= x <= max_x and min_y <= y <= max_y:
            cropped_graph.add_node(node[0], x=x, y=y)

    for edge in graph.edges(data=True):
        u, v = edge[0], edge[1]
        if u in cropped_graph and v in cropped_graph:
            cropped_graph.add_edge(u, v)

    return cropped_graph

def noise_graph(
    graph: ox.graph_from_point, noise: float = 0.1, noise_ratio: float = 0.1
) -> ox.graph_from_point:
    """
    Add noise to the graph node coordinates.

    :param graph: A graph
    :param noise: The noise to add in meters
    :param noise_ratio: The ratio of nodes to add noise to
    :return: A new graph with noisy coordinates
    """

    noise = 0.0000089 * noise  # Convert noise to degrees

    # Copy the graph
    graph = graph.copy()
    nodes = list(graph.nodes())
    random.shuffle(nodes)

    for node in nodes[: int(len(nodes) * noise_ratio)]:
        graph.nodes[node]["x"] += random.uniform(-noise, noise)
        graph.nodes[node]["y"] += random.uniform(-noise, noise)

    return graph



def random_simplify_edges(
    graph: ox.graph_from_point, simplify_ratio: float = 0.1
) -> ox.graph_from_point:
    """
    Randomly picks two adjacent edges and simplifies them by removing the node in between.

    :param graph: A graph
    :param simplify_ratio: The ratio of nodes to remove
    :return: A new graph with some nodes removed
    """

    # Copy the graph
    graph = graph.copy()

    count = graph.number_of_edges() * simplify_ratio

    nodes_with_connectivity_2 = [node for node in graph.nodes() if len(list(graph.neighbors(node))) == 2]
    random.shuffle(nodes_with_connectivity_2)

    for _ in range(int(count)):
        node = nodes_with_connectivity_2.pop()
        neighbors = list(graph.neighbors(node))
        if len(neighbors) != 2:
            continue
        graph.add_edge(neighbors[0], neighbors[1])
        # Remove all edges connected to the node
        for neighbor in neighbors:
            graph.remove_edge(node, neighbor)
        graph.remove_node(node)

    return graph

def random_insert_edges(
    graph: ox.graph_from_point, insert_ratio: float = 0.1
) -> ox.graph_from_point:
    """
    Increase number of edges in the graph by inserting new edges. The procedure is as follow, pick a random edge,
    linearly interpolate the coordinates of the two nodes of the edge, and add a new edge between the two interpolated
    at a random position.
    """
    edges = list(graph.edges())
    random.shuffle(edges)

    for edge in edges[: int(len(edges) * insert_ratio)]:
        node_a, node_b = edge
        x_a, y_a = graph.nodes[node_a]["x"], graph.nodes[node_a]["y"]
        x_b, y_b = graph.nodes[node_b]["x"], graph.nodes[node_b]["y"]
        ratio = random.random()
        x = x_a + ratio * (x_b - x_a)
        y = y_a + ratio * (y_b - y_a)

        new_node = len(graph.nodes) * 1000
        graph.add_node(new_node, x=x, y=y)
        graph.add_edge(node_a, new_node)
        graph.add_edge(new_node, node_b)
        # remove the original edge
        graph.remove_edge(node_a, node_b)

    return graph


def translate_graph(
    graph: ox.graph_from_point, meters_x: float, meters_y: float
) -> ox.graph_from_point:
    """
    Translate the graph by a certain amount of meters in the x and y directions.

    :param graph: A graph
    :param meters_x: The amount of meters to translate in the x direction
    :param meters_y: The amount of meters to translate in the y direction
    :return: A new graph translated by the given amount
    """

    # Copy the graph
    graph = graph.copy()

    for node, data in graph.nodes(data=True):
        data["x"] += 0.0000089 * meters_x
        data["y"] += 0.0000089 * meters_y

    return graph



def alter_graph(
        graph: ox.graph_from_point,
        translate_x: float = 0,
        translate_y: float = 0,
        noise: float = 0,
        noise_ratio: float = 0,
        simplify_ratio: float = 0,
        insert_ratio: float = 0,
) -> ox.graph_from_point:
    """
    Alter a graph by translating, adding noise, simplifying, and inserting edges.

    :param graph: A graph
    :param translate_x: The amount of meters to translate in the x direction
    :param translate_y: The amount of meters to translate in the y direction
    :param noise: The noise to add in meters
    :param noise_ratio: The ratio of nodes to add noise to
    :param simplify_ratio: The ratio of nodes to remove
    :param insert_ratio: The ratio of edges to insert
    :return: A new graph with the specified alterations
    """

    graph = translate_graph(graph, translate_x, translate_y)
    logging.info("Translated graph")
    graph = noise_graph(graph, noise, noise_ratio)
    logging.info("Added noise to graph")
    graph = random_simplify_edges(graph, simplify_ratio)
    logging.info("Simplified graph")
    graph = random_insert_edges(graph, insert_ratio)
    logging.info("Inserted edges in graph")

    return graph