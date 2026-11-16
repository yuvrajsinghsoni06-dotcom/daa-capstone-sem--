"""Mini-Courier Planner: sorting, 0/1 knapsack, Dijkstra and route approximation."""
from __future__ import annotations

import argparse
import csv
import heapq
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Parcel:
    parcel_id: str
    destination: str
    weight: int
    value: int
    deadline: int  # smaller hour value means earlier delivery deadline


def load_data(path: Path) -> tuple[str, int, list[Parcel], dict[str, dict[str, int]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    parcels = [Parcel(**p) for p in data["parcels"]]
    return data["depot"], int(data["capacity"]), parcels, data["graph"]


def prioritize(parcels: list[Parcel]) -> list[Parcel]:
    """Stable merge sort by earliest deadline, then highest value, then ID."""
    def key(p: Parcel) -> tuple[int, int, str]:
        return p.deadline, -p.value, p.parcel_id

    def merge_sort(items: list[Parcel]) -> list[Parcel]:
        if len(items) < 2:
            return items[:]
        mid = len(items) // 2
        left, right = merge_sort(items[:mid]), merge_sort(items[mid:])
        out: list[Parcel] = []
        i = j = 0
        while i < len(left) and j < len(right):
            if key(left[i]) <= key(right[j]):
                out.append(left[i]); i += 1
            else:
                out.append(right[j]); j += 1
        return out + left[i:] + right[j:]
    return merge_sort(parcels)


def choose_parcels(parcels: list[Parcel], capacity: int) -> tuple[list[Parcel], int]:
    """0/1 knapsack DP; tie-breaking retains the earlier DP choice."""
    n = len(parcels)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i, p in enumerate(parcels, 1):
        for cap in range(capacity + 1):
            dp[i][cap] = dp[i - 1][cap]
            if p.weight <= cap:
                dp[i][cap] = max(dp[i][cap], dp[i - 1][cap - p.weight] + p.value)
    selected: list[Parcel] = []
    cap = capacity
    for i in range(n, 0, -1):
        if dp[i][cap] != dp[i - 1][cap]:
            p = parcels[i - 1]
            selected.append(p)
            cap -= p.weight
    selected.reverse()
    return selected, dp[n][capacity]


def dijkstra(graph: dict[str, dict[str, int]], source: str) -> tuple[dict[str, float], dict[str, str | None]]:
    """Return shortest distances and predecessor links for nonnegative edges."""
    distances = {node: float("inf") for node in graph}
    previous: dict[str, str | None] = {node: None for node in graph}
    if source not in graph:
        raise ValueError(f"Unknown graph node: {source}")
    distances[source] = 0
    queue: list[tuple[int, str]] = [(0, source)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances[node]:
            continue
        for neighbor, weight in graph[node].items():
            if weight < 0:
                raise ValueError("Dijkstra requires nonnegative edge weights")
            candidate = distance + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                previous[neighbor] = node
                heapq.heappush(queue, (candidate, neighbor))
    return distances, previous


def path_to(previous: dict[str, str | None], target: str) -> list[str]:
    if target not in previous:
        return []
    path, node = [], target
    while node is not None:
        path.append(node)
        node = previous[node]
    return list(reversed(path))


def nearest_neighbor_route(graph: dict[str, dict[str, int]], depot: str,
                           destinations: list[str]) -> tuple[list[str], int, dict[str, dict[str, Any]]]:
    """Greedy TSP approximation over all-pairs shortest-path distances."""
    nodes = list(dict.fromkeys([depot] + destinations))
    dists, prevs = {}, {}
    for node in nodes:
        dists[node], prevs[node] = dijkstra(graph, node)
    remaining = set(destinations) - {depot}
    route = [depot]
    total = 0
    while remaining:
        here = route[-1]
        reachable = [(dists[here][n], n) for n in remaining if dists[here][n] < float("inf")]
        if not reachable:
            raise ValueError(f"Unreachable destinations from {here}: {sorted(remaining)}")
        distance, next_node = min(reachable)
        total += int(distance)
        route.append(next_node)
        remaining.remove(next_node)
    if route[-1] != depot:
        back = dists[route[-1]][depot]
        if back == float("inf"):
            raise ValueError("Depot is unreachable from the last stop")
        total += int(back)
        route.append(depot)
    legs = {}
    for a, b in zip(route, route[1:]):
        legs[f"{a}->{b}"] = {"distance": int(dists[a][b]), "path": path_to(prevs[a], b)}
    return route, total, legs


def plan(depot: str, capacity: int, parcels: list[Parcel], graph: dict[str, dict[str, int]]) -> dict[str, Any]:
    ordered = prioritize(parcels)
    selected, value = choose_parcels(ordered, capacity)
    destinations = list(dict.fromkeys(p.destination for p in selected))
    route, distance, legs = nearest_neighbor_route(graph, depot, destinations)
    return {"prioritized": ordered, "selected": selected, "value": value,
            "weight": sum(p.weight for p in selected), "route": route,
            "distance": distance, "legs": legs}


def benchmark(path: Path, output_dir: Path) -> None:
    """Measure major algorithm stages over increasing deterministic workloads."""
    depot, capacity, base, base_graph = load_data(path)
    rows = []
    rng = random.Random(42)
    for size in (len(base), max(100, len(base) * 5), max(500, len(base) * 20)):
        # Grow the road network too, so Dijkstra and route measurements are
        # not repeated against the same tiny graph at every parcel count.
        graph = {node: dict(edges) for node, edges in base_graph.items()}
        target_nodes = max(len(graph), min(size, 120))
        previous_node = sorted(graph)[-1]
        while len(graph) < target_nodes:
            node = f"N{len(graph):04}"
            graph[node] = {previous_node: 3}
            graph[previous_node][node] = 3
            previous_node = node
        parcels = [Parcel(f"P{i:05}", rng.choice(list(graph)), rng.randint(1, 20),
                          rng.randint(10, 100), rng.randint(1, 24)) for i in range(size)]
        for name, fn in (
            ("merge_sort", lambda: prioritize(parcels)),
            ("knapsack_dp", lambda: choose_parcels(parcels, capacity)),
            ("dijkstra", lambda: dijkstra(graph, depot)),
            ("route_planning", lambda: nearest_neighbor_route(graph, depot,
                list(dict.fromkeys(p.destination for p in parcels)))),
        ):
            start = time.perf_counter()
            fn()
            elapsed = (time.perf_counter() - start) * 1000
            rows.append({"parcel_count": size, "graph_nodes": len(graph),
                         "algorithm": name, "runtime_ms": f"{elapsed:.4f}"})
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "runtime_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["parcel_count", "graph_nodes", "algorithm", "runtime_ms"])
        writer.writeheader(); writer.writerows(rows)
    chart_path = output_dir / "runtime_chart.svg"
    colors = {"merge_sort": "#2563eb", "knapsack_dp": "#16a34a", "dijkstra": "#ea580c", "route_planning": "#9333ea"}
    max_ms = max(float(row["runtime_ms"]) for row in rows) or 1
    bars = []
    for i, row in enumerate(rows):
        y = 75 + i * 27
        width = max(2, float(row["runtime_ms"]) / max_ms * 380)
        bars.append(f'<text x="15" y="{y+14}" font-size="11">{row["algorithm"]} - n={row["parcel_count"]}, V={row["graph_nodes"]}</text><rect x="255" y="{y}" width="{width:.1f}" height="17" fill="{colors[row["algorithm"]]}"/><text x="{265+width:.1f}" y="{y+13}" font-size="10">{row["runtime_ms"]} ms</text>')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="740" height="%d"><rect width="100%%" height="100%%" fill="white"/><text x="15" y="28" font-size="18" font-family="sans-serif">Measured algorithm runtimes</text>%s</svg>' % (60 + len(rows)*27, "".join(bars))
    chart_path.write_text(svg, encoding="utf-8")
    print(f"Wrote {csv_path} and {chart_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan a capacity-limited courier delivery trip.")
    parser.add_argument("--data", type=Path, default=Path("data/sample_small.json"))
    parser.add_argument("--benchmark", action="store_true", help="measure components and create CSV/SVG evidence")
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    if args.benchmark:
        benchmark(args.data, args.output)
        return
    depot, capacity, parcels, graph = load_data(args.data)
    result = plan(depot, capacity, parcels, graph)
    print("MINI-COURIER PLANNER")
    print(f"Input: {args.data} | depot: {depot} | capacity: {capacity} kg")
    print("\nPriority order (deadline, value):")
    for p in result["prioritized"]:
        print(f"  {p.parcel_id}: {p.destination}, {p.weight} kg, value {p.value}, deadline {p.deadline}h")
    print("\nOptimal packing:")
    print("  Parcels: " + (", ".join(p.parcel_id for p in result["selected"]) or "none"))
    print(f"  Weight: {result['weight']}/{capacity} kg | total value: {result['value']}")
    print("\nDelivery route (nearest-neighbor over Dijkstra distances):")
    for leg, info in result["legs"].items():
        print(f"  {leg}: {' -> '.join(info['path'])} ({info['distance']} km)")
    print(f"  Route: {' -> '.join(result['route'])} | total: {result['distance']} km")


if __name__ == "__main__":
    main()
