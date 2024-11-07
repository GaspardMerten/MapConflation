from typing import List

import networkx as nx
import pydeck as pdk
from pydeck.bindings.base_map_provider import BaseMapProvider

from src.types import ConflationResult

BLUE = [0, 0, 255]
GREEN = [0, 255, 0]
SPEED = "[25*speed, 0, 0]"


def create_layer(
    graph: nx.Graph, layer_type: str, color: list | str, radius=0.5, width=0.25
):
    """
    Create a Pydeck layer for nodes or edges in the graph.

    :param graph: A NetworkX graph
    :param layer_type: "ScatterplotLayer" for nodes, "PathLayer" for edges
    :param color: Color of the layer
    :param radius: Radius of the node points (only for ScatterplotLayer)
    :param width: Width of the edges (only for PathLayer)
    :return: A Pydeck Layer
    """
    if layer_type == "ScatterplotLayer":
        return pdk.Layer(
            layer_type,
            data=list(
                map(
                    lambda x: {"id": x[0], "x": x[1]["x"], "y": x[1]["y"]},
                    graph.nodes(data=True),
                ),
            ),
            get_position="[x, y]",
            get_radius=radius,
            get_fill_color=color,
            pickable=True,
        )
    elif layer_type == "PathLayer":
        return pdk.Layer(
            layer_type,
            data=[
                {
                    "path": [
                        [graph.nodes[u]["x"], graph.nodes[u]["y"]],
                        [graph.nodes[v]["x"], graph.nodes[v]["y"]],
                    ],
                    **data,
                }
                for u, v,data in graph.edges(data=True)
            ],
            get_color=color,
            get_width=width,
            pickable=True,
        )


def get_view_state(graph: nx.Graph, zoom=16):
    """
    Get the initial view state of the graph based on the first node.

    :param graph: A NetworkX graph
    :param zoom: Zoom level for the view state
    :return: A Pydeck ViewState
    """
    first_node = list(graph.nodes)[0]
    return pdk.ViewState(
        latitude=graph.nodes[first_node]["y"],
        longitude=graph.nodes[first_node]["x"],
        zoom=zoom,
    )


def plot_graph(graph: nx.Graph, save_path: str):
    """
    Plot a single graph using Pydeck.

    :param graph: A NetworkX graph
    :param save_path: The path to save the plot to
    :return: None
    """
    node_layer = create_layer(graph, "ScatterplotLayer", BLUE)
    edge_layer = create_layer(graph, "PathLayer", GREEN)

    view_state = get_view_state(graph, zoom=14)

    deck_map = pdk.Deck(
        layers=[node_layer, edge_layer],
        initial_view_state=view_state,
    )

    deck_map.to_html(save_path)



def plot_graphs_with_results(
    graph_a: nx.Graph,
    graph_b: nx.Graph,
    results: List[ConflationResult],
    save_path="graphs.html",
):
    """
    Plot two graphs side by side using Pydeck.

    :param graph_a: A NetworkX graph
    :param graph_b: A NetworkX graph
    :param save_path: The path to save the plot to
    :return: None
    """
    node_layer_a = create_layer(graph_a, "ScatterplotLayer", BLUE)
    node_layer_b = create_layer(graph_b, "ScatterplotLayer", GREEN)
    edge_layer_a = create_layer(graph_a, "PathLayer", SPEED)
    edge_layer_b = create_layer(graph_b, "PathLayer", SPEED)

    paths_from_point_b_to_segment_a = []
    paths_from_point_b_to_interpolated_a = []
    points_b_on_a = []

    for result in results:
        initial_point_b = result.point_b_coords
        segment_a_start, segment_a_end = result.segment_a_coords
        interpolated_b_on_a = result.point_b_on_segment_a
        points_b_on_a.append(
            {
                "id": result.point_b,
                "x": interpolated_b_on_a[0],
                "y": interpolated_b_on_a[1],
                "votes": result.number_of_votes,
            }
        )
        paths_from_point_b_to_segment_a.append(
            {
                "path": [
                    [initial_point_b[0], initial_point_b[1]],
                    [segment_a_start[0], segment_a_start[1]],
                ]
            }
        )
        paths_from_point_b_to_segment_a.append(
            {
                "path": [
                    [initial_point_b[0], initial_point_b[1]],
                    [segment_a_end[0], segment_a_end[1]],
                ]
            }
        )
        paths_from_point_b_to_interpolated_a.append(
            {
                "path": [
                    [initial_point_b[0], initial_point_b[1]],
                    [interpolated_b_on_a[0], interpolated_b_on_a[1]],
                ]
            }
        )

    node_layer_points_b_on_a = pdk.Layer(
        "ScatterplotLayer",
        data=points_b_on_a,
        get_position="[x, y]",
        get_radius=0.5,
        pickable=True,
    )

    interpolated_path_layer = pdk.Layer(
        "PathLayer",
        data=paths_from_point_b_to_interpolated_a,
        get_color=[255, 255, 0],
        get_width=0.1,
        pickable=True,
    )

    view_state_a = get_view_state(graph_a)

    deck_map = pdk.Deck(
        map_provider=BaseMapProvider.MAPBOX.value,
        api_keys={
            "mapbox": "pk.eyJ1IjoiZ2FzcGFyZG0iLCJhIjoiY2xlNGV2Ymk4MDJlbDN4dnp1d3ptd3JuMiJ9.sib6JobIMGz00INoFpWpbg"
        },
        layers=[
            node_layer_a,
            node_layer_b,
            edge_layer_a,
            edge_layer_b,
            node_layer_points_b_on_a,
            interpolated_path_layer,
        ],
        initial_view_state=view_state_a,
        tooltip=True,
        map_style="road",
    )

    deck_map.to_html(save_path)
