import hashlib
import itertools
import logging

import networkx as nx

from src.enrich.enrich import enrich
from src.graph.plot import plot_graphs_with_results
from src.graph.transform import alter_graph
from src.utils import (
    add_random_speed_valus_to_graph,
    nodes_and_edges_to_int,
    prepare_and_load_osm,
    compute_or_load_matched_ids,
    load_or_conflate,
)


def generate_configs():
    # Define the parameter grid
    translate_values = [0, 3, 5, 10, 20]  # Translation distances
    noise_values = [0, 2, 5, 10, 20, 40, 70]  # Noise magnitudes
    noise_ratios = [0, 0.1, 0.2, 0.5]  # Ratios for noise application
    simplify_ratios = [0, 0.1, 0.2, 0.5]  # Simplification ratios
    insert_ratios = [0, 0.1, 0.2, 0.5]  # Ratios for insertions

    configs = []

    print(len(configs))

    # Base config
    configs.append(
        ( dict(
            translate_x=0,
            translate_y=0,
            noise=0,
            noise_ratio=0,
            simplify_ratio=0,
        ), 0)
    )

    # Generate all combinations of parameters
    for (
        translate_x,
        translate_y,
        noise,
        noise_ratio,
        simplify_ratio,
        insert_ratio,
    ) in itertools.product(
        translate_values,
        translate_values,
        noise_values,
        noise_ratios,
        simplify_ratios,
        insert_ratios,
    ):
        configs.append(
            (dict(
                translate_x=translate_x,
                translate_y=translate_y,
                noise=noise,
                noise_ratio=noise_ratio,
                simplify_ratio=simplify_ratio,
            ), insert_ratio)
        )

    return configs


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)

    configs = generate_configs()

    for  config, insert_ratio in configs:
        full_name = f"all_{config['translate_x']}_{config['translate_y']}_{config['noise']}_{config['noise_ratio']}_{config['simplify_ratio']}, f{insert_ratio}"
        md5_hash = hashlib.md5(full_name.encode()).hexdigest()[:5]
        graph_b = prepare_and_load_osm(f"out/graph_{md5_hash}_a.gml", distance=1500)
        graph_b = alter_graph(graph_b, **config)
        graph_b = graph_b.subgraph(max(nx.connected_components(graph_b), key=len))
        graph_b = nodes_and_edges_to_int(graph_b)
        graph_b = add_random_speed_valus_to_graph(graph_b)
        logging.info("Loaded graph B")

        graph_a = prepare_and_load_osm(f"out/graph_{md5_hash}_b.gml", distance=1500)
        graph_a = alter_graph(graph_a, 0, 0, 0, 0, 0, insert_ratio)
        graph_a = graph_a.subgraph(max(nx.connected_components(graph_a), key=len))
        graph_a = nodes_and_edges_to_int(graph_a)
        logging.info("Loaded graph A")

        matched_ids = compute_or_load_matched_ids(
            graph_a,
            graph_b,
            f"out/matches_{md5_hash}.json",
            f"out/trajectories_id_{md5_hash}.json",
            f"out/trajectories_{md5_hash}.json",
        )
        logging.info("Computed matches")

        results = load_or_conflate(
            graph_a,
            graph_b,
            matched_ids,
            f"out/results_{full_name}.json",
        )

        graph_a = enrich(graph_a, graph_b, results)

        plot_graphs_with_results(graph_a, graph_b, results, f"geojson_{full_name}.html")
