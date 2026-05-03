"""Graph exporter: exports to JSON and Cypher formats."""

from __future__ import annotations

import json

import networkx as nx


def export_to_json(G: nx.DiGraph, output_path: str) -> None:
    """Export graph to JSON format compatible with future Neo4j import."""
    nodes = []
    for node_id, ndata in G.nodes(data=True):
        nodes.append({
            "id": node_id,
            "type": ndata.get("type", "entity"),
            "source_table": ndata.get("source_table", node_id),
            "source_files": ndata.get("source_files", []),
            "source_type": ndata.get("source_type", ""),
            "attributes": ndata.get("attributes", []),
            "attribute_types": ndata.get("attribute_types", {}),
            "primary_keys": ndata.get("pks", []),
            "foreign_keys": ndata.get("fks", []),
            "role": ndata.get("role", "leaf"),
        })

    edges = []
    for u, v, edata in G.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "relationship": edata.get("relationship", ""),
            "cardinality": edata.get("cardinality", ""),
            "via_column": edata.get("via", ""),
            "source_file": edata.get("source_file", ""),
        })

    export = {
        "graph": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }
    }

    with open(output_path, "w") as f:
        json.dump(export, f, indent=2)


def export_to_cypher(G: nx.DiGraph, output_path: str) -> None:
    """Export graph to Neo4j Cypher script."""
    lines = []

    lines.append("// Auto-generated Cypher script for Neo4j import")
    lines.append("")

    for node_id, ndata in G.nodes(data=True):
        label = _sanitize(node_id)
        props = []
        for attr in ndata.get("attributes", []):
            val = "null"
            props.append(f"{attr}: {val}")
        prop_str = ", ".join(props)
        lines.append(f"CREATE (:{label} {{{prop_str}}});")

    for u, v, edata in G.edges(data=True):
        u_label, v_label = _sanitize(u), _sanitize(v)
        rel = edata.get("relationship", "RELATED_TO")
        via = edata.get("via", "")
        lines.append(
            f"MATCH (a:{u_label}), (b:{v_label}) "
            f"CREATE (a)-[:{rel} {{via: '{via}'}}]->(b);"
        )

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def _sanitize(name: str) -> str:
    """Remove/replace characters not valid in Neo4j labels."""
    return name.replace("-", "_").replace(" ", "_").replace(".", "_")
