"""Graph enricher: infers relationship labels, cardinalities, and entity roles."""

from __future__ import annotations

import re

import networkx as nx


def enrich_graph(G: nx.DiGraph) -> nx.DiGraph:
    """Enrich graph with inferred relationship labels, cardinalities, and entity roles."""
    _infer_relationship_labels(G)
    _infer_cardinalities(G)
    _classify_entity_roles(G)
    return G


def _infer_relationship_labels(G: nx.DiGraph) -> None:
    """Infer semantic relationship labels from FK column names."""
    label_map = {
        "customer": "BELONGS_TO",
        "user": "BELONGS_TO",
        "account": "LINKED_TO",
        "product": "REFERENCES",
        "order": "PART_OF",
        "parent": "CHILD_OF",
        "employee": "ASSIGNED_TO",
        "branch": "LOCATED_AT",
        "portfolio": "MANAGES",
        "transaction": "LINKED_TO",
        "instrument": "REFERENCES",
        "counterparty": "DEALS_WITH",
        "category": "CATEGORIZED_AS",
        "group": "MEMBER_OF",
        "owner": "OWNED_BY",
        "created_by": "CREATED_BY",
        "updated_by": "UPDATED_BY",
    }

    for u, v, data in G.edges(data=True):
        if data.get("relationship") and data["relationship"] != "FK_TO":
            continue

        via = data.get("via", "").lower()
        label = "FK_TO"

        for key, lbl in label_map.items():
            if key in via:
                label = lbl
                break

        data["relationship"] = label


def _infer_cardinalities(G: nx.DiGraph) -> None:
    """Infer cardinalities based on constraints and FK patterns."""
    for u, v, data in G.edges(data=True):
        if data.get("cardinality") and data["cardinality"] != "":
            continue

        u_node = G.nodes.get(u, {})
        v_node = G.nodes.get(v, {})

        u_fks = u_node.get("fks", [])
        via = data.get("via", "")

        # If the FK column is also a PK → likely 1:1
        u_pks = u_node.get("pks", [])
        if via in u_pks:
            data["cardinality"] = "1:1"
        # If FK column has UNIQUE constraint → 1:1
        elif via in u_fks:
            data["cardinality"] = "N:1"
        else:
            data["cardinality"] = "N:1"

    # Check for many-to-many bridge patterns
    for node, ndata in G.nodes(data=True):
        fks = ndata.get("fks", [])
        pks = ndata.get("pks", [])
        attrs = ndata.get("attributes", [])
        if len(pks) >= 2 and len(attrs) <= 5 and len(fks) >= 2:
            ndata["role"] = "bridge"


def _classify_entity_roles(G: nx.DiGraph) -> None:
    """Classify entities as core (has inbound FKs), leaf (no inbound FKs), or bridge."""
    in_degrees = dict(G.in_degree())

    for node, ndata in G.nodes(data=True):
        if ndata.get("role") == "bridge":
            continue
        if in_degrees.get(node, 0) > 0:
            ndata["role"] = "core"
        else:
            ndata["role"] = "leaf"
