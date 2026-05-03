#!/usr/bin/env python3
"""Semantic Mesh CLI — Universal Data Plane Phase 1.

Usage:
  python cli.py --input schema.sql --output graph.html
  python cli.py --input models.py --type python --output graph.html
  python cli.py --input ./my-repo --output graph.html
  python cli.py --input schema.sql --format json --output graph.json
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from ingestion.repo_scanner import scan_input
from graph.builder import build_graph
from graph.enricher import enrich_graph
from graph.exporter import export_to_json, export_to_cypher
from viz.renderer import render_html


def main():
    parser = argparse.ArgumentParser(
        description="Semantic Mesh — Build a knowledge graph from SQL DDL, code models, or repos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py --input schema.sql --output graph.html
  python cli.py --input models.py --type python --output graph.html
  python cli.py --input ./src --output graph.html
  python cli.py --input schema.sql --format json --output graph.json
  python cli.py --input ./java-project --output graph.html
        """,
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input file (.sql, .py, .js, .ts, .java) or directory (repo scan)",
    )
    parser.add_argument(
        "--type", "-t",
        default=None,
        choices=["sql", "python", "javascript", "typescript", "java", "auto"],
        help="Input type (default: auto-detect from extension). 'auto' scans repo if --input is a directory.",
    )
    parser.add_argument(
        "--output", "-o",
        default="graph.html",
        help="Output file path (default: graph.html)",
    )
    parser.add_argument(
        "--format", "-f",
        default=None,
        choices=["html", "json", "cypher"],
        help="Output format (default: inferred from --output extension)",
    )

    args = parser.parse_args()

    # Validate input exists
    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"Error: Input not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Determine format
    fmt = args.format
    if fmt is None:
        ext = os.path.splitext(args.output)[1].lower()
        fmt_map = {".html": "html", ".json": "json", ".cypher": "cypher", ".cql": "cypher"}
        fmt = fmt_map.get(ext, "html")

    # Resolve type
    file_type = args.type

    print(f"Semantic Mesh — Phase 1")
    print(f"  Input:  {input_path}")
    print(f"  Type:   {file_type or 'auto-detect'}")
    print(f"  Output: {args.output} ({fmt})")
    print()

    # Step 1: Parse / Scan
    print("Scanning and parsing...")
    t0 = time.time()
    schema = scan_input(input_path, file_type)
    t1 = time.time()
    print(f"  Found {len(schema.entities)} entities, {len(schema.relationships)} relationships "
          f"({t1 - t0:.2f}s)")

    if len(schema.entities) == 0:
        print("Warning: No entities found. Check your input files.", file=sys.stderr)
        sys.exit(0)

    # Step 2: Build graph
    print("Building graph...")
    G = build_graph(schema)
    print(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

    # Step 3: Enrich
    print("Enriching graph...")
    G = enrich_graph(G)

    role_counts = {}
    for _nid, ndata in G.nodes(data=True):
        role = ndata.get("role", "leaf")
        role_counts[role] = role_counts.get(role, 0) + 1
    print(f"  Roles: {', '.join(f'{k}={v}' for k, v in sorted(role_counts.items()))}")

    # Step 4: Export / Render
    print(f"Exporting to {fmt}...")
    t2 = time.time()
    if fmt == "html":
        render_html(G, args.output)
    elif fmt == "json":
        export_to_json(G, args.output)
    elif fmt == "cypher":
        export_to_cypher(G, args.output)
    t3 = time.time()

    total = t3 - t0
    print(f"\nDone! Output: {args.output} ({total:.2f}s total)")
    if fmt == "html":
        print(f"Open {args.output} in a browser to explore the graph.")


if __name__ == "__main__":
    main()
