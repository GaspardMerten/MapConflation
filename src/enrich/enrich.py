import logging

import networkx as nx


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
    if new_node_id in graph.nodes:
        return graph
    # Find shortest path between the two nodes
    shortest_path = nx.shortest_path(graph, edge[0], edge[1])
    # Find where to insert the new node (between which two nodes) (MINIMUM DISTANCE)
    min_distance = float("inf")
    min_distance_index = 0
    for i in range(len(shortest_path) - 1):
        u, v = shortest_path[i], shortest_path[i + 1]
        mid_x = (graph.nodes[u]["x"] + graph.nodes[v]["x"]) / 2
        mid_y = (graph.nodes[u]["y"] + graph.nodes[v]["y"]) / 2

        distance = (mid_x - x) ** 2 + (mid_y - y) ** 2

        if distance < min_distance:
            min_distance = distance
            min_distance_index = i

    # Insert the new node
    graph.add_node(new_node_id, x=x, y=y)
    graph.add_edge(shortest_path[min_distance_index], new_node_id)
    graph.add_edge(new_node_id, shortest_path[min_distance_index + 1])
    # remove the original edge
    graph.remove_edge(
        shortest_path[min_distance_index], shortest_path[min_distance_index + 1]
    )
    return graph


def enrich(graph_a, graph_b, results):
    results_map = {result.point_b: result for result in results}

    for edge in graph_b.edges:
        if edge[0] not in results_map or edge[1] not in results_map:
            logging.warning(f"Edge {edge} not in results")
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
            shortest_path = nx.shortest_path(
                graph_a, new_node_id_start, new_node_id_end
            )

            for i in range(len(shortest_path) - 1):
                u, v = shortest_path[i], shortest_path[i + 1]
                graph_a[u][v]["speed"] = graph_b[edge[0]][edge[1]]["speed"]
        except Exception as e:
            logging.error(e)

    return graph_a
