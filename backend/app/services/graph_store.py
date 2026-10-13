
"""
CodeInsight AI - Knowledge Graph Store

Primary backend: Neo4j.
Fallback backend: NetworkX.

Graph schema:
Nodes: File, Class, Interface, Method, Function
Relationships: CONTAINS, DEFINED_IN, CALLS, EXTENDS, IMPLEMENTS

Neo4j writes are batched using UNWIND to reduce database round trips.
"""

import re
from typing import List, Dict, Any, Set

from ..config import settings
from .code_parser import CodeEntity

_networkx_graphs: Dict[str, Any] = {}
_neo4j_driver = None
_neo4j_available = None

# Number of nodes/relationships sent per database transaction.
NEO4J_BATCH_SIZE = 500


def _try_neo4j():
    global _neo4j_driver, _neo4j_available

    if _neo4j_available is not None:
        return _neo4j_available

    try:
        from neo4j import GraphDatabase

        _neo4j_driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        _neo4j_driver.verify_connectivity()
        _neo4j_available = True

    except Exception:
        _neo4j_available = False

    return _neo4j_available


def _use_neo4j() -> bool:
    if settings.graph_backend == "networkx":
        return False
    return _try_neo4j()


def _batches(items, batch_size=NEO4J_BATCH_SIZE):
    """Yield fixed-size batches without copying the entire input."""
    for start in range(0, len(items), batch_size):
        yield items[start:start + batch_size]


def _run_batched(session, query, rows):
    """Execute a parameterized Cypher query for each batch."""
    for batch in _batches(rows):
        session.execute_write(
            lambda tx, data=batch: tx.run(query, rows=data).consume()
        )


# --------------------------------------------------------------------------
# Reset
# --------------------------------------------------------------------------

def reset_repo_graph(repo_id: str):
    if _use_neo4j():
        with _neo4j_driver.session() as session:
            session.run(
                "MATCH (n {repo_id: $repo_id}) DETACH DELETE n",
                repo_id=repo_id,
            ).consume()
    else:
        import networkx as nx
        _networkx_graphs[repo_id] = nx.DiGraph()


# --------------------------------------------------------------------------
# Build graph
# --------------------------------------------------------------------------

def build_graph(repo_id: str, entities: List[CodeEntity]):
    reset_repo_graph(repo_id)

    name_to_ids: Dict[str, List[str]] = {}
    for entity in entities:
        name_to_ids.setdefault(entity.name, []).append(entity.id)

    if _use_neo4j():
        _build_graph_neo4j(repo_id, entities, name_to_ids)
    else:
        _build_graph_networkx(repo_id, entities, name_to_ids)


def _build_graph_neo4j(repo_id, entities, name_to_ids):
    """
    Create nodes and relationships in batches.

    Node labels come from parsed entity types and are validated before
    being interpolated into Cypher. All property values are parameters.
    """

    # Group entities by label so each query uses a fixed, safe label.
    entities_by_type: Dict[str, list] = {}

    for entity in entities:
        label = entity.type or "CodeEntity"

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", label):
            raise ValueError(f"Invalid Neo4j node label: {label!r}")

        entities_by_type.setdefault(label, []).append({
            "id": entity.id,
            "repo_id": repo_id,
            "name": entity.name,
            "file_path": entity.file_path,
            "start_line": entity.start_line,
            "end_line": entity.end_line,
            "language": entity.language,
            "signature": entity.signature or "",
        })

    with _neo4j_driver.session() as session:

        # 1. Create nodes in batches.
        for label, rows in entities_by_type.items():
            query = f"""
                UNWIND $rows AS row
                CREATE (n:{label} {{
                    id: row.id,
                    repo_id: row.repo_id,
                    name: row.name,
                    file_path: row.file_path,
                    start_line: row.start_line,
                    end_line: row.end_line,
                    language: row.language,
                    signature: row.signature
                }})
            """
            _run_batched(session, query, rows)

        # Prepare relationship rows for batch insertion.
        relationships = {
            "CONTAINS": [],
            "DEFINED_IN": [],
            "EXTENDS": [],
            "IMPLEMENTS": [],
            "CALLS": [],
        }

        for entity in entities:

            # Parent/child relationships.
            if entity.parent_id:
                relationships["CONTAINS"].append({
                    "source": entity.parent_id,
                    "target": entity.id,
                    "repo_id": repo_id,
                })
                relationships["DEFINED_IN"].append({
                    "source": entity.id,
                    "target": entity.parent_id,
                    "repo_id": repo_id,
                })

            # Inheritance relationships.
            for base in entity.extends:
                for target_id in name_to_ids.get(base, []):
                    relationships["EXTENDS"].append({
                        "source": entity.id,
                        "target": target_id,
                        "repo_id": repo_id,
                    })

            # Interface implementation relationships.
            for interface in entity.implements:
                for target_id in name_to_ids.get(interface, []):
                    relationships["IMPLEMENTS"].append({
                        "source": entity.id,
                        "target": target_id,
                        "repo_id": repo_id,
                    })

            # Function/method call relationships.
            for called_name in set(entity.calls):
                for target_id in name_to_ids.get(called_name, []):
                    if target_id != entity.id:
                        relationships["CALLS"].append({
                            "source": entity.id,
                            "target": target_id,
                            "repo_id": repo_id,
                        })

        # 2. Create each relationship type in batches.
        relationship_queries = {
            "CONTAINS": """
                UNWIND $rows AS row
                MATCH (source {id: row.source, repo_id: row.repo_id})
                MATCH (target {id: row.target, repo_id: row.repo_id})
                CREATE (source)-[:CONTAINS]->(target)
            """,
            "DEFINED_IN": """
                UNWIND $rows AS row
                MATCH (source {id: row.source, repo_id: row.repo_id})
                MATCH (target {id: row.target, repo_id: row.repo_id})
                CREATE (source)-[:DEFINED_IN]->(target)
            """,
            "EXTENDS": """
                UNWIND $rows AS row
                MATCH (source {id: row.source, repo_id: row.repo_id})
                MATCH (target {id: row.target, repo_id: row.repo_id})
                CREATE (source)-[:EXTENDS]->(target)
            """,
            "IMPLEMENTS": """
                UNWIND $rows AS row
                MATCH (source {id: row.source, repo_id: row.repo_id})
                MATCH (target {id: row.target, repo_id: row.repo_id})
                CREATE (source)-[:IMPLEMENTS]->(target)
            """,
            "CALLS": """
                UNWIND $rows AS row
                MATCH (source {id: row.source, repo_id: row.repo_id})
                MATCH (target {id: row.target, repo_id: row.repo_id})
                CREATE (source)-[:CALLS]->(target)
            """,
        }

        for relationship_type, rows in relationships.items():
            if rows:
                _run_batched(
                    session,
                    relationship_queries[relationship_type],
                    rows,
                )


def _build_graph_networkx(repo_id, entities, name_to_ids):
    import networkx as nx

    graph = nx.DiGraph()

    for entity in entities:
        graph.add_node(
            entity.id,
            type=entity.type,
            name=entity.name,
            file_path=entity.file_path,
            start_line=entity.start_line,
            end_line=entity.end_line,
            language=entity.language,
            signature=entity.signature or "",
        )

    for entity in entities:
        if entity.parent_id and graph.has_node(entity.parent_id):
            graph.add_edge(entity.parent_id, entity.id, rel="CONTAINS")
            graph.add_edge(entity.id, entity.parent_id, rel="DEFINED_IN")

        for base in entity.extends:
            for target_id in name_to_ids.get(base, []):
                graph.add_edge(entity.id, target_id, rel="EXTENDS")

        for interface in entity.implements:
            for target_id in name_to_ids.get(interface, []):
                graph.add_edge(entity.id, target_id, rel="IMPLEMENTS")

        for called_name in set(entity.calls):
            for target_id in name_to_ids.get(called_name, []):
                if target_id != entity.id:
                    graph.add_edge(entity.id, target_id, rel="CALLS")

    _networkx_graphs[repo_id] = graph


# --------------------------------------------------------------------------
# Traversal for hybrid retrieval
# --------------------------------------------------------------------------

def find_entity_ids_by_name_or_file(
    repo_id: str,
    names: List[str],
    file_paths: List[str],
) -> Set[str]:

    ids = set()

    if _use_neo4j():
        with _neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (n {repo_id: $repo_id})
                WHERE n.name IN $names OR n.file_path IN $files
                RETURN n.id AS id
                """,
                repo_id=repo_id,
                names=names,
                files=file_paths,
            )
            ids.update(record["id"] for record in result)

    else:
        graph = _networkx_graphs.get(repo_id)

        if graph:
            for node_id, data in graph.nodes(data=True):
                if (
                    data.get("name") in names
                    or data.get("file_path") in file_paths
                ):
                    ids.add(node_id)

    return ids


def expand_neighbors(
    repo_id: str,
    seed_ids: Set[str],
    hops: int = None,
) -> List[Dict[str, Any]]:

    hops = hops or settings.graph_hops
    related = []

    if _use_neo4j():
        with _neo4j_driver.session() as session:
            result = session.run(
                f"""
                MATCH (a)
                WHERE a.id IN $ids AND a.repo_id = $repo_id
                MATCH (a)-[r*1..{int(hops)}]-(b)
                WHERE b.repo_id = $repo_id
                RETURN DISTINCT
                    b.id AS id,
                    b.name AS name,
                    b.file_path AS file_path,
                    b.start_line AS start_line,
                    b.end_line AS end_line,
                    labels(b)[0] AS type,
                    b.signature AS signature
                LIMIT 25
                """,
                ids=list(seed_ids),
                repo_id=repo_id,
            )

            for record in result:
                related.append(dict(record))

    else:
        graph = _networkx_graphs.get(repo_id)

        if graph:
            seen = set()
            frontier = set(seed_ids)

            for _ in range(hops):
                next_frontier = set()

                for node_id in frontier:
                    if node_id in graph:
                        next_frontier |= (
                            set(graph.successors(node_id))
                            | set(graph.predecessors(node_id))
                        )

                next_frontier -= seen
                seen |= frontier
                frontier = next_frontier

            for node_id in list(seen | frontier)[:25]:
                if node_id in graph.nodes and node_id not in seed_ids:
                    data = graph.nodes[node_id]
                    related.append({
                        "id": node_id,
                        "name": data.get("name"),
                        "file_path": data.get("file_path"),
                        "start_line": data.get("start_line"),
                        "end_line": data.get("end_line"),
                        "type": data.get("type"),
                        "signature": data.get("signature"),
                    })

    return related


def get_stats(repo_id: str) -> Dict[str, int]:

    if _use_neo4j():
        with _neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (n {repo_id: $repo_id})
                RETURN labels(n)[0] AS type, count(*) AS cnt
                """,
                repo_id=repo_id,
            )

            counts = {
                record["type"]: record["cnt"]
                for record in result
            }

            relationship_result = session.run(
                """
                MATCH (a {repo_id: $repo_id})-[r]->(b {repo_id: $repo_id})
                RETURN count(r) AS cnt
                """,
                repo_id=repo_id,
            )

            relationship_count = relationship_result.single()["cnt"]

    else:
        graph = _networkx_graphs.get(repo_id)
        counts = {}
        relationship_count = graph.number_of_edges() if graph else 0

        if graph:
            for _, data in graph.nodes(data=True):
                node_type = data.get("type", "Unknown")
                counts[node_type] = counts.get(node_type, 0) + 1

    return {
        "num_files": counts.get("File", 0),
        "num_classes": counts.get("Class", 0) + counts.get("Interface", 0),
        "num_functions": counts.get("Function", 0) + counts.get("Method", 0),
        "num_relationships": relationship_count,
    }


def backend_name() -> str:
    return (
        "neo4j"
        if _use_neo4j()
        else "networkx (fallback - Neo4j unavailable)"
    )
