from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable


DEFAULT_NEO4J = {
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "neo4j_password",
    "NEO4J_DATABASE": "neo4j",
}


def env(name: str) -> str:
    if name == "NEO4J_USER":
        # Accept both env names used across scripts/configs.
        return os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or DEFAULT_NEO4J[name]
    return os.getenv(name, DEFAULT_NEO4J[name])


def neo4j_conf() -> Dict[str, str]:
    return {
        "uri": env("NEO4J_URI"),
        "user": env("NEO4J_USER"),
        "password": env("NEO4J_PASSWORD"),
        "database": env("NEO4J_DATABASE"),
    }


@lru_cache(maxsize=1)
def get_driver() -> Any:
    conf = neo4j_conf()
    return GraphDatabase.driver(conf["uri"], auth=(conf["user"], conf["password"]))


def run_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    conf = neo4j_conf()
    with get_driver().session(database=conf["database"]) as session:
        result = session.run(query, **(params or {}))
        return [dict(record) for record in result]


def ping() -> bool:
    rows = run_query("RETURN 1 AS ok")
    return bool(rows and rows[0].get("ok") == 1)


__all__ = [
    "Neo4jError",
    "ServiceUnavailable",
    "ping",
    "run_query",
]
