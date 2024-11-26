import logging
from datetime import datetime

import networkx as nx

from src.enrich.enrich import enrich
from src.graph.plot import plot_graphs_with_results
from src.utils import (
    load_or_create_geojson_graph,
    add_random_speed_valus_to_graph,
    nodes_and_edges_to_int,
    prepare_and_load_osm,
    compute_or_load_matched_ids,
    load_or_conflate,
)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    graph_b = load_or_create_geojson_graph("out/graph_b.gml")
    graph_b = graph_b.subgraph(max(nx.connected_components(graph_b), key=len))
    graph_b = nodes_and_edges_to_int(graph_b)
    graph_b = add_random_speed_valus_to_graph(graph_b)
    logging.info("Loaded graph B")

    graph_a = prepare_and_load_osm("out/graph_a.gml")
    graph_a = graph_a.subgraph(max(nx.connected_components(graph_a), key=len))
    graph_a = nodes_and_edges_to_int(graph_a)
    logging.info("Loaded graph A")

    matched_ids = compute_or_load_matched_ids(graph_a, graph_b, "out/matches.json")
    logging.info("Computed matches")

    results = load_or_conflate(
        graph_a,
        graph_b,
        matched_ids,
        "out/results.json",
    )

    graph_a = enrich(graph_a, graph_b, results)

    plot_graphs_with_results(
        graph_a,
        graph_b,
        results,
        f"geojson_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.html",
    )
