#!/usr/bin/env -S python3
# Run via: tools/.venv/bin/python3 tools/chart.py ...
"""
chart.py — Generate charts/visualizations from wiki data, saved to outputs/
Called by Claude as a CLI tool during Q&A and report generation.

Usage:
  python3 tools/chart.py --type timeline --data '{"2017":"Transformer","2020":"GPT-3"}' --title "LLM Timeline" --out timeline
  python3 tools/chart.py --type bar --data '{"Concept A":5,"Concept B":3}' --title "Comparison" --out compare
  python3 tools/chart.py --type network --data '{"nodes":["A","B"],"edges":[["A","B"]]}' --title "Concept Map" --out network
  python3 tools/chart.py --type heatmap --data '{"rows":["A"],"cols":["X"],"values":[[1]]}' --title "Matrix" --out matrix
  python3 tools/chart.py --list-types
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "outputs" / "charts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHART_TYPES = ["timeline", "bar", "horizontal-bar", "network", "heatmap", "pie", "scatter"]

def save(fig, name: str) -> Path:
    import matplotlib.pyplot as plt
    out = OUT_DIR / f"{name}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"✅ Saved: {out.relative_to(ROOT)}")
    return out

def chart_timeline(data: dict, title: str, name: str):
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    items = sorted(data.items(), key=lambda x: str(x[0]))
    years = [str(k) for k, v in items]
    labels = [str(v) for k, v in items]

    fig, ax = plt.subplots(figsize=(12, max(4, len(items) * 0.6)))
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

    for i, (year, label) in enumerate(zip(years, labels)):
        ax.plot([0, 1], [i, i], "b-", linewidth=1.5, alpha=0.3)
        ax.plot(0.5, i, "bo", markersize=8)
        ax.text(0.55, i, f"  {year}  —  {label}", va="center", fontsize=10)

    ax.set_xlim(0, 2)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.spines[:].set_visible(False)
    ax.axvline(x=0.5, color="steelblue", linewidth=2)
    return save(fig, name)

def chart_bar(data: dict, title: str, name: str, horizontal=False):
    import matplotlib.pyplot as plt

    labels = list(data.keys())
    values = [float(v) for v in data.values()]
    colors = plt.cm.Blues([0.4 + 0.4 * (v / max(values)) for v in values])

    fig, ax = plt.subplots(figsize=(10, max(4, len(labels) * 0.5)))
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

    if horizontal:
        bars = ax.barh(labels, values, color=colors)
        ax.bar_label(bars, fmt="%.1f", padding=4)
        ax.set_xlabel("Value")
    else:
        bars = ax.bar(labels, values, color=colors)
        ax.bar_label(bars, fmt="%.1f", padding=4)
        ax.set_ylabel("Value")
        plt.xticks(rotation=30, ha="right")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save(fig, name)

def chart_network(data: dict, title: str, name: str):
    """Concept network / knowledge graph visualization"""
    try:
        import networkx as nx
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
    except ImportError:
        print("⚠️  networkx not installed. Run: pip3 install networkx")
        sys.exit(1)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    node_sizes = data.get("sizes", {})   # optional: {"NodeA": 2000}
    node_groups = data.get("groups", {}) # optional: {"NodeA": "domain-ai"}

    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from([tuple(e) for e in edges])

    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

    pos = nx.spring_layout(G, k=2, seed=42)
    sizes = [node_sizes.get(n, 800) for n in G.nodes()]

    # Color by group
    group_list = list(set(node_groups.values())) if node_groups else ["default"]
    color_map = {g: cm.Set2(i / max(len(group_list), 1)) for i, g in enumerate(group_list)}
    colors = [color_map.get(node_groups.get(n, "default"), "steelblue") for n in G.nodes()]

    nx.draw_networkx(G, pos, ax=ax, node_size=sizes, node_color=colors,
                     font_size=9, font_weight="bold", edge_color="#aaa",
                     width=1.5, with_labels=True)
    ax.axis("off")
    return save(fig, name)

def chart_heatmap(data: dict, title: str, name: str):
    import matplotlib.pyplot as plt
    import numpy as np

    rows = data["rows"]
    cols = data["cols"]
    values = np.array(data["values"])

    fig, ax = plt.subplots(figsize=(max(6, len(cols)), max(4, len(rows) * 0.6)))
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

    im = ax.imshow(values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=30, ha="right")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows)

    for i in range(len(rows)):
        for j in range(len(cols)):
            ax.text(j, i, f"{values[i,j]:.1f}", ha="center", va="center",
                    color="white" if values[i,j] > values.max()*0.6 else "black", fontsize=9)

    plt.colorbar(im, ax=ax, shrink=0.8)
    return save(fig, name)

def chart_pie(data: dict, title: str, name: str):
    import matplotlib.pyplot as plt

    labels = list(data.keys())
    values = [float(v) for v in data.values()]

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    wedges, texts, autotexts = ax.pie(values, labels=labels, autopct="%1.1f%%",
                                       colors=plt.cm.Set2.colors, startangle=90)
    for t in autotexts:
        t.set_fontsize(9)
    return save(fig, name)

def chart_scatter(data: dict, title: str, name: str):
    import matplotlib.pyplot as plt

    points = data.get("points", [])  # [{"x":1,"y":2,"label":"A"}]
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    labels = [p.get("label", "") for p in points]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.scatter(xs, ys, s=80, color="steelblue", alpha=0.7)

    for x, y, label in zip(xs, ys, labels):
        if label:
            ax.annotate(label, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)

    ax.set_xlabel(data.get("xlabel", "X"))
    ax.set_ylabel(data.get("ylabel", "Y"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save(fig, name)

# --- Wiki network auto-generator ---
def chart_wiki_network(title: str, name: str):
    """Auto-generate concept network from wiki backlinks"""
    import re
    import matplotlib.pyplot as plt
    try:
        import networkx as nx
    except ImportError:
        print("⚠️  networkx not installed. Run: pip3 install networkx")
        sys.exit(1)

    wiki = ROOT / "wiki"
    G = nx.Graph()
    link_pattern = re.compile(r'\[\[([^\]|#]+)')

    for md_file in wiki.rglob("*.md"):
        src = md_file.stem
        G.add_node(src)
        content = md_file.read_text(errors="ignore")
        for match in link_pattern.finditer(content):
            target = match.group(1).strip().split("/")[-1]
            if target and target != src:
                G.add_edge(src, target)

    # Remove isolated utility nodes
    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)

    import matplotlib.cm as cm
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_title(title or "Wiki Knowledge Graph", fontsize=16, fontweight="bold", pad=20)

    pos = nx.spring_layout(G, k=3, seed=42)
    degrees = dict(G.degree())
    sizes = [max(300, degrees[n] * 200) for n in G.nodes()]
    colors = [cm.Blues(min(0.9, 0.3 + degrees[n] * 0.1)) for n in G.nodes()]

    nx.draw_networkx(G, pos, ax=ax, node_size=sizes, node_color=colors,
                     font_size=7, font_weight="bold", edge_color="#ccc",
                     width=1, with_labels=True, alpha=0.9)
    ax.axis("off")

    out = save(fig, name)
    print(f"   {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return out

def main():
    parser = argparse.ArgumentParser(description="Wiki chart generator")
    parser.add_argument("--type", choices=CHART_TYPES + ["wiki-network"], help="Chart type")
    parser.add_argument("--data", help="JSON data string")
    parser.add_argument("--title", default="Chart", help="Chart title")
    parser.add_argument("--out", default="chart", help="Output filename (no extension)")
    parser.add_argument("--list-types", action="store_true")
    args = parser.parse_args()

    if args.list_types:
        print("Available chart types:")
        for t in CHART_TYPES + ["wiki-network"]:
            print(f"  {t}")
        return

    if not args.type:
        parser.print_help()
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
    except ImportError:
        print("⚠️  matplotlib not installed. Run: pip3 install matplotlib")
        sys.exit(1)

    data = json.loads(args.data) if args.data else {}

    if args.type == "timeline":
        chart_timeline(data, args.title, args.out)
    elif args.type == "bar":
        chart_bar(data, args.title, args.out)
    elif args.type == "horizontal-bar":
        chart_bar(data, args.title, args.out, horizontal=True)
    elif args.type == "network":
        chart_network(data, args.title, args.out)
    elif args.type == "heatmap":
        chart_heatmap(data, args.title, args.out)
    elif args.type == "pie":
        chart_pie(data, args.title, args.out)
    elif args.type == "scatter":
        chart_scatter(data, args.title, args.out)
    elif args.type == "wiki-network":
        chart_wiki_network(args.title, args.out)

if __name__ == "__main__":
    main()
