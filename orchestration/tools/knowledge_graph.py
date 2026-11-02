# Read C2C issue categories, scenarios and linked checks from Neo4j.
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

ISSUE_IDS = {
    "C2C Access Issue": "CI001",
    "Course Launch Issue": "CI002",
    "Course Completion Issue": "CI003",
}


# Read the matching issue and scenario names from Neo4j.
def lookup_issue(category: str) -> dict | None:
    """Read the matching issue and scenario names from Neo4j."""
    issue_id = ISSUE_IDS.get(category)
    if issue_id is None:
        return None

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE")
    if not all((uri, username, password, database)):
        raise RuntimeError("Neo4j connection settings are incomplete")

    # Match the connection behavior used by seed_neo4j.py on this machine.
    if uri.startswith("neo4j+s://"):
        uri = uri.replace("neo4j+s://", "neo4j+ssc://", 1)
    elif uri.startswith("bolt+s://"):
        uri = uri.replace("bolt+s://", "bolt+ssc://", 1)

    query = """
    MATCH (root:Issue {id: 'C2C'})-[:HAS_ISSUE]->(issue:Issue {id: $issue_id})
    RETURN root.id AS root_id, root.name AS root_name,
           issue.id AS id, issue.name AS name
    """
    with GraphDatabase.driver(
        uri,
        auth=(username, password),
        connection_timeout=5,
        connection_acquisition_timeout=5,
        max_transaction_retry_time=1,
    ) as driver:
        with driver.session(database=database) as session:
            record = session.execute_read(
                lambda tx: tx.run(query, issue_id=issue_id).single()
            )
    if record is None:
        return None
    return {
        "root_id": record["root_id"],
        "root_name": record["root_name"],
        "id": record["id"],
        "name": record["name"],
    }


# Fetch one issue's scenarios and linked checks, causes and resolutions.
def diagnosis_scenarios(category: str) -> dict | None:
    """Fetch one issue's scenarios and linked checks, causes and resolutions."""
    issue_id = ISSUE_IDS.get(category)
    if issue_id is None:
        return None
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE")
    if not all((uri, username, password, database)):
        raise RuntimeError("Neo4j connection settings are incomplete")
    if uri.startswith("neo4j+s://"):
        uri = uri.replace("neo4j+s://", "neo4j+ssc://", 1)
    elif uri.startswith("bolt+s://"):
        uri = uri.replace("bolt+s://", "bolt+ssc://", 1)
    query = """
    MATCH (:Issue {id:'C2C'})-[:HAS_ISSUE]->(i:Issue {id:$issue_id})
    MATCH (i)-[:HAS_SCENARIO]->(s:Scenario)
    OPTIONAL MATCH (s)-[:REQUIRES_VALIDATION]->(v:Validation)
    OPTIONAL MATCH (v)-[:USES_API]->(a:API)
    OPTIONAL MATCH (s)-[:HAS_ROOT_CAUSE]->(r:RootCause)
    OPTIONAL MATCH (s)-[:HAS_RESOLUTION]->(p:Resolution)
    RETURN i.id AS issue_id, s.id AS scenario_id, s.name AS scenario_name,
           collect(DISTINCT v.id) AS validation_ids,
           collect(DISTINCT a.id) AS api_ids,
           collect(DISTINCT v{.id, .name}) AS validations,
           collect(DISTINCT a{.id, .name}) AS apis,
           collect(DISTINCT r.id) AS root_cause_ids,
           collect(DISTINCT p.id) AS resolution_ids
    ORDER BY scenario_id
    """
    with GraphDatabase.driver(uri, auth=(username, password), connection_timeout=5,
                              connection_acquisition_timeout=5, max_transaction_retry_time=1) as driver:
        with driver.session(database=database) as session:
            records = session.execute_read(lambda tx: list(tx.run(query, issue_id=issue_id)))
    return {"issue_id": issue_id, "scenarios": [dict(record) for record in records]} if records else None
