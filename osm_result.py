import json
import os

from src.types import ConflationResult


for c in os.listdir("out"):
    if "results_" not in c:
        continue

    results_osm = json.load(open(f"out/{c}", "r"))
    a = [ConflationResult(**b) for b in results_osm]

    score = 0
    bad_score = 1
    for r in a:
        if r.point_b in r.segment_a_id:
            score += 1
        else:
            bad_score += 1
    # full_name = f"{name}_{config['translate_x']}_{config['translate_y']}_{config['noise']}_{config['noise_ratio']}_{config['simplify_ratio']}, f{insert_ratio}"

    config= c.split("_")[1:]

    translate_x = config[0]
    translate_y = config[1]
    noise = config[2]
    noise_ratio = config[3]
    simplify_ratio = config[4]
    insert_ratio = config[5]

    # Write to csv

    print(c, score/(score+bad_score))
