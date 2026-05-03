"""Java JPA/Hibernate entity parser using regex-based extraction."""

from __future__ import annotations

import re

from .schema_normalizer import ColumnInfo, EntityInfo, ParsedSchema, RelationshipInfo

# Regex patterns for Java JPA/Hibernate entities
_CLASS_DECL_RE = re.compile(
    r"(?:@Entity[^\n]*\n(?:\s*@\w+[^\n]*\n)*)?\s*(?:public\s+)?class\s+(\w+)",
    re.MULTILINE,
)
_FIELD_RE = re.compile(
    r"@(?:Id|Column|JoinColumn|ManyToOne|OneToMany|OneToOne|ManyToMany)[^\n]*\n"
    r"\s*(?:private|protected|public)\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*;",
    re.MULTILINE,
)
_TABLE_ANNOTATION_RE = re.compile(r'@Table\s*\(\s*name\s*=\s*"(\w+)"')
_ENTITY_ANNOTATION_RE = re.compile(r"@Entity")
_ID_ANNOTATION_RE = re.compile(r"@Id")
_JOIN_COLUMN_RE = re.compile(r'@JoinColumn\s*\(\s*name\s*=\s*"(\w+)"')
_MANY_TO_ONE_RE = re.compile(r"@ManyToOne")
_ONE_TO_MANY_RE = re.compile(r"@OneToMany\s*\(\s*mappedBy\s*=\s*\"(\w+)\"")
_ONE_TO_ONE_RE = re.compile(r"@OneToOne")
_MANY_TO_MANY_RE = re.compile(r"@ManyToMany")


def parse_java_file(filepath: str, source_code: str) -> ParsedSchema:
    """Parse a Java file for JPA/Hibernate entities."""
    entities: list[EntityInfo] = []
    relationships: list[RelationshipInfo] = []

    # Remove block comments and line comments for cleaner parsing
    clean = re.sub(r"/\*.*?\*/", "", source_code, flags=re.DOTALL)
    clean = re.sub(r"//[^\n]*", "", clean)

    # Find all class declarations with @Entity
    class_matches = list(_CLASS_DECL_RE.finditer(clean))
    if not class_matches:
        return ParsedSchema()

    for cm in class_matches:
        class_name = cm.group(1)
        # Find the class body - extract from class decl to next class or EOF
        start = cm.end()
        next_class = re.search(r"\s(?:public\s+)?class\s+\w+", clean[start:])
        body_end = start + next_class.start() if next_class else len(clean)
        class_body = clean[start:body_end]

        table_name = class_name.lower()
        table_match = _TABLE_ANNOTATION_RE.search(clean[max(0, cm.start() - 200):cm.start()])
        if table_match:
            table_name = table_match.group(1)

        columns: list[ColumnInfo] = []
        class_rels: list[RelationshipInfo] = []

        # Find fields with annotations
        field_matches = list(_FIELD_RE.finditer(class_body))
        if not field_matches:
            # Try simpler pattern without annotations
            simple_field_re = re.compile(
                r"(?:private|protected|public)\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*;",
                re.MULTILINE,
            )
            field_matches = list(simple_field_re.finditer(class_body))

        for fm in field_matches:
            java_type = fm.group(1)
            field_name = fm.group(2)

            # Check for annotations before this field
            field_start_in_class = fm.start()
            prefix = class_body[max(0, field_start_in_class - 300):field_start_in_class]

            is_pk = bool(_ID_ANNOTATION_RE.search(prefix))
            is_many_to_one = bool(_MANY_TO_ONE_RE.search(prefix))
            is_one_to_many = bool(_ONE_TO_MANY_RE.search(prefix))
            is_one_to_one = bool(_ONE_TO_ONE_RE.search(prefix))
            is_many_to_many = bool(_MANY_TO_MANY_RE.search(prefix))
            is_relationship = is_many_to_one or is_one_to_many or is_one_to_one or is_many_to_many

            fk_refs = None
            is_fk = False

            join_match = _JOIN_COLUMN_RE.search(prefix)
            if is_many_to_one or is_one_to_one:
                is_fk = True
                # FK references the related entity
                target_table = java_type.lower() + "s"  # naive pluralization
                fk_col = join_match.group(1) if join_match else field_name
                fk_refs = (target_table, "id")
                class_rels.append(RelationshipInfo(
                    source_entity=_to_pascal_case(class_name),
                    target_entity=_to_pascal_case(java_type),
                    relationship_type="BELONGS_TO" if is_many_to_one else "HAS_ONE",
                    cardinality="N:1" if is_many_to_one else "1:1",
                    via_column=fk_col,
                    source_file=filepath,
                ))
            elif is_one_to_many:
                one_to_many_match = _ONE_TO_MANY_RE.search(prefix)
                mapped_by = one_to_many_match.group(1) if one_to_many_match else ""
                class_rels.append(RelationshipInfo(
                    source_entity=_to_pascal_case(class_name),
                    target_entity=_to_pascal_case(java_type.replace("List<", "").replace("Set<", "").replace(">", "")),
                    relationship_type="HAS_MANY",
                    cardinality="1:N",
                    via_column=mapped_by,
                    source_file=filepath,
                ))
            elif is_many_to_many:
                class_rels.append(RelationshipInfo(
                    source_entity=_to_pascal_case(class_name),
                    target_entity=_to_pascal_case(java_type.replace("List<", "").replace("Set<", "").replace(">", "")),
                    relationship_type="MANY_TO_MANY",
                    cardinality="M:N",
                    via_column="",
                    source_file=filepath,
                ))

            sql_type = _java_type_to_sql(java_type)
            columns.append(ColumnInfo(
                name=field_name,
                data_type=sql_type,
                is_pk=is_pk,
                is_fk=is_fk or is_relationship,
                fk_references=fk_refs,
            ))

        entities.append(EntityInfo(
            name=_to_pascal_case(class_name),
            source_name=class_name,
            source_files=[filepath],
            columns=columns,
            source_type="java",
        ))
        relationships.extend(class_rels)

        # Fallback: generate relationships from FK columns not covered by annotations
        entity_name = _to_pascal_case(class_name)
        covered = {(r.source_entity, r.via_column) for r in class_rels}
        for col in columns:
            if col.is_fk and col.fk_references and (entity_name, col.name) not in covered:
                relationships.append(RelationshipInfo(
                    source_entity=entity_name,
                    target_entity=_to_pascal_case(col.fk_references[0]),
                    relationship_type="FK_TO",
                    cardinality="N:1",
                    via_column=col.name,
                    source_file=filepath,
                ))

    return ParsedSchema(entities=entities, relationships=relationships)


def _java_type_to_sql(java_type: str) -> str:
    mapping = {
        "String": "VARCHAR",
        "Integer": "INTEGER",
        "int": "INTEGER",
        "Long": "BIGINT",
        "long": "BIGINT",
        "Double": "DOUBLE",
        "double": "DOUBLE",
        "Float": "FLOAT",
        "float": "FLOAT",
        "Boolean": "BOOLEAN",
        "boolean": "BOOLEAN",
        "UUID": "UUID",
        "LocalDateTime": "TIMESTAMP",
        "LocalDate": "DATE",
        "BigDecimal": "DECIMAL",
        "Date": "TIMESTAMP",
        "byte[]": "BLOB",
    }
    # Handle generic types like List<Foo>, Set<Bar>
    clean_type = re.sub(r"<(?:List|Set)<([^>]+)>>", r"\1", java_type)
    return mapping.get(clean_type, clean_type.upper())


def _to_pascal_case(name: str) -> str:
    parts = name.replace("-", "_").split("_")
    return "".join(p.capitalize() for p in parts if p)
