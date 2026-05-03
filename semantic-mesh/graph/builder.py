"""NetworkX graph construction from ParsedSchema."""

from __future__ import annotations

import networkx as nx

from ingestion.schema_normalizer import EntityInfo, ParsedSchema, RelationshipInfo


def build_graph(schema: ParsedSchema) -> nx.DiGraph:
    """Build a NetworkX DiGraph from a ParsedSchema."""
    G = nx.DiGraph()

    for entity in schema.entities:
        attrs = [c.name for c in entity.columns]
        attr_types = {c.name: c.data_type for c in entity.columns}
        G.add_node(
            entity.name,
            type="entity",
            source_table=entity.source_name,
            source_files=entity.source_files,
            source_type=entity.source_type,
            attributes=attrs,
            attribute_types=attr_types,
            pks=entity.pks,
            fks=entity.fks,
            attribute_count=len(attrs),
        )

    for rel in schema.relationships:
        if G.has_node(rel.source_entity) and G.has_node(rel.target_entity):
            G.add_edge(
                rel.source_entity,
                rel.target_entity,
                relationship=rel.relationship_type,
                cardinality=rel.cardinality,
                via=rel.via_column,
                source_file=rel.source_file,
            )

    return G
