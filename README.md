# Mini-Courier Planner

A Python capstone prototype integrating merge sort, 0/1 knapsack dynamic programming, Dijkstra shortest paths, and a nearest-neighbor TSP approximation.

## Run

Requires Python 3.10 or later; there are no third-party dependencies.

```bash
python main.py
python main.py --data data/sample_small.json
python main.py --benchmark --data data/sample_small.json --output results
```

The benchmark command creates `results/runtime_results.csv` and `results/runtime_chart.svg` from measured runs on the machine executing it. It grows both parcel count and graph size (up to 120 nodes), and records both in the CSV. Keep those generated artifacts with the submission. Timings vary by computer and should not be treated as universal performance claims.

## Input format

JSON contains a depot name, vehicle capacity in kg, parcels (`parcel_id`, `destination`, positive integer `weight`, `value`, and `deadline` hour), and an adjacency-list graph. Edge weights are nonnegative distances in km. The graph is undirected in the supplied example (both directions are listed); Dijkstra itself supports directed adjacency lists. Parcel destinations must be graph nodes. The route visits each selected destination once, then returns to the depot.

## Algorithms and complexity

| Component | Method | Time | Auxiliary space |
|---|---|---:|---:|
| Prioritization | Merge sort by deadline, then descending value, then ID | O(n log n) | O(n log n) recursion/copies |
| Packing | 0/1 knapsack DP over parcel count and integer capacity W | O(nW) | O(nW) |
| Individual paths | Dijkstra with binary heap | O((V+E) log V) | O(V+E) |
| Delivery order | Nearest neighbor using shortest-path distances | O(k²) after all-pairs runs | O(k²) |

Here n is parcel count, W is capacity, V/E are graph nodes/edges, and k is the number of selected delivery locations. The knapsack implementation assumes integer weights and capacity. The TSP method is a heuristic and does not guarantee a globally shortest tour.

## Design and phase mapping

1. **Problem design:** depot, weighted road graph, parcel attributes, and vehicle capacity are defined in JSON.
2. **Prioritize and pack:** merge sort creates an explainable urgency order; DP maximizes total parcel value without exceeding capacity.
3. **Route and graph:** Dijkstra finds each leg's actual road path; nearest neighbor chooses the next stop by shortest-path distance and closes the tour at the depot.
4. **Performance:** benchmark mode measures sorting, packing, shortest path, and route planning at increasing parcel counts; it writes CSV and SVG evidence.
5. **Demonstration:** console output includes sorted parcels, selected packing plan, every road path, and total route length.

```text
Parcel and graph JSON
        |
        v
Deadline merge sort --> 0/1 knapsack --> selected destinations
                                            |
                                            v
                               Dijkstra paths + nearest neighbor
                                            |
                                            v
                                   Ordered tour + depot return
```

The greedy delivery order uses the destinations chosen by the packing stage. Multiple parcels at one address require only one stop. If no parcels are selected, the route is just the depot and has length zero.

## Sample run trace

For `data/sample_small.json`, the optimal packing is **P4 + P3 + P5**, weighing 10 kg for value 52. The priority ordering is P4 (deadline 2), P2 (3), P3 (4), P1 (5), P6 (6), P5 (8). Their destinations produce the nearest-neighbor route Depot -> A -> C -> D -> Depot. The shortest legs are 4 km, 4 km (A -> B -> C), 3 km, and 8 km, totaling **19 km**. These expected values can be checked by hand from the supplied graph and parcel list.

## Testing and runtime evidence

Use both supplied JSON datasets and benchmark mode:

```bash
python main.py --data data/sample_small.json
python main.py --data data/sample_large.json
python main.py --benchmark --data data/sample_small.json --output results
```

Check that selected weight never exceeds capacity, knapsack value is maximal for the tested data, each path's edges exist, and the final route returns to the depot. Save terminal screenshots alongside generated benchmark CSV/SVG for the Zosima upload. For a fair comparison, run benchmarks on the same computer and close to idle; report the computer and Python version with results.

## Phase completion checklist

| Phase | Project coverage | Evidence to include in final upload |
|---|---|---|
| 1. Design and planning | Parcel schema, capacity, graph format, algorithm flow and complexity documented above | This README and both JSON datasets |
| 2. Prioritization and packing | Merge sort and knapsack DP implemented; run prints order and selected parcels | Small and large dataset console output |
| 3. Route and graph | Dijkstra leg paths and nearest-neighbor closed tour implemented | Console output showing legs, route and distance |
| 4. Performance | Benchmark mode measures four components over increasing parcel and graph sizes | Generated `runtime_results.csv` and `runtime_chart.svg`, plus machine/Python details |
| 5. Report and demonstration | Run instructions, trace, complexity, limitations, and demonstration output are documented | Capture terminal screenshots after running; add them to the submission folder |

The code and documentation cover all five phases. Machine-specific runtime files and screenshots are generated/captured when you run the project; they are not prefilled with invented measurements.

## Limitations and possible improvements

The value objective treats all parcel value equally; add a deadline penalty or lexicographic urgency objective if late deliveries must be avoided. Knapsack scales with numeric capacity, so use value/weight scaling or approximation for very large capacities. Nearest neighbor can produce a suboptimal tour; compare against 2-opt or exact enumeration on small instances. Real deployments would need travel-time updates, time windows, vehicle fleets, and route constraints.
