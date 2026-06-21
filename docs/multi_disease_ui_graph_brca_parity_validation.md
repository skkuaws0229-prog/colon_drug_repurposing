# Multi-Disease UI Graph BRCA Parity Validation

- Generated (UTC): 2026-05-24T18:59:34.370287+00:00
- Target app: `api.main:app`
- Endpoint registered: `True`
- Endpoint methods: `GET`

## Summary

- Diseases tested: 7
- HTTP 200 responses: 7
- PostgreSQL fallback used: 0
- `NO_GRAPH_DATA` responses: 7
- Missing `edges` key responses: 7
- Missing `count` key responses: 7
- Fabricated drug-node issues: 0

## Per-Disease Results

### BRCA

- HTTP status: `200`
- Nodes: `0`, Edges (from `links`): `0`
- Has keys disease/nodes/edges/count/warnings: `True/True/False/False/True`
- PostgreSQL fallback used: `False`
- `GRAPH_FALLBACK_FROM_POSTGRES_CANDIDATES` present: `False`
- Fallback structure valid (Disease + DrugCandidate + HAS_CANDIDATE): `None`
- `NO_GRAPH_DATA` only when empty graph: `True`
- No fabricated drug nodes: `True`
- Warnings: ["Neo4j projection unavailable: ServiceUnavailable: Couldn't connect to 127.0.0.1:7687 (resolved to ()): Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다)", 'Neo4j Bolt connection failure detected. Check Neo4j service status and NEO4J_URI.', 'PostgreSQL candidate fallback unavailable: OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs the server running on that host and accepting TCP/IP connections? connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs...', 'NO_GRAPH_DATA']

### COAD

- HTTP status: `200`
- Nodes: `0`, Edges (from `links`): `0`
- Has keys disease/nodes/edges/count/warnings: `True/True/False/False/True`
- PostgreSQL fallback used: `False`
- `GRAPH_FALLBACK_FROM_POSTGRES_CANDIDATES` present: `False`
- Fallback structure valid (Disease + DrugCandidate + HAS_CANDIDATE): `None`
- `NO_GRAPH_DATA` only when empty graph: `True`
- No fabricated drug nodes: `True`
- Warnings: ["Neo4j projection unavailable: ServiceUnavailable: Couldn't connect to 127.0.0.1:7687 (resolved to ()): Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다)", 'Neo4j Bolt connection failure detected. Check Neo4j service status and NEO4J_URI.', 'PostgreSQL candidate fallback unavailable: OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs the server running on that host and accepting TCP/IP connections? connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs...', 'NO_GRAPH_DATA']

### LUAD

- HTTP status: `200`
- Nodes: `0`, Edges (from `links`): `0`
- Has keys disease/nodes/edges/count/warnings: `True/True/False/False/True`
- PostgreSQL fallback used: `False`
- `GRAPH_FALLBACK_FROM_POSTGRES_CANDIDATES` present: `False`
- Fallback structure valid (Disease + DrugCandidate + HAS_CANDIDATE): `None`
- `NO_GRAPH_DATA` only when empty graph: `True`
- No fabricated drug nodes: `True`
- Warnings: ["Neo4j projection unavailable: ServiceUnavailable: Couldn't connect to 127.0.0.1:7687 (resolved to ()): Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다)", 'Neo4j Bolt connection failure detected. Check Neo4j service status and NEO4J_URI.', 'PostgreSQL candidate fallback unavailable: OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs the server running on that host and accepting TCP/IP connections? connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs...', 'NO_GRAPH_DATA']

### LIHC

- HTTP status: `200`
- Nodes: `0`, Edges (from `links`): `0`
- Has keys disease/nodes/edges/count/warnings: `True/True/False/False/True`
- PostgreSQL fallback used: `False`
- `GRAPH_FALLBACK_FROM_POSTGRES_CANDIDATES` present: `False`
- Fallback structure valid (Disease + DrugCandidate + HAS_CANDIDATE): `None`
- `NO_GRAPH_DATA` only when empty graph: `True`
- No fabricated drug nodes: `True`
- Warnings: ["Neo4j projection unavailable: ServiceUnavailable: Couldn't connect to 127.0.0.1:7687 (resolved to ()): Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다)", 'Neo4j Bolt connection failure detected. Check Neo4j service status and NEO4J_URI.', 'PostgreSQL candidate fallback unavailable: OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs the server running on that host and accepting TCP/IP connections? connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs...', 'NO_GRAPH_DATA']

### STAD

- HTTP status: `200`
- Nodes: `0`, Edges (from `links`): `0`
- Has keys disease/nodes/edges/count/warnings: `True/True/False/False/True`
- PostgreSQL fallback used: `False`
- `GRAPH_FALLBACK_FROM_POSTGRES_CANDIDATES` present: `False`
- Fallback structure valid (Disease + DrugCandidate + HAS_CANDIDATE): `None`
- `NO_GRAPH_DATA` only when empty graph: `True`
- No fabricated drug nodes: `True`
- Warnings: ["Neo4j projection unavailable: ServiceUnavailable: Couldn't connect to 127.0.0.1:7687 (resolved to ()): Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다)", 'Neo4j Bolt connection failure detected. Check Neo4j service status and NEO4J_URI.', 'PostgreSQL candidate fallback unavailable: OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs the server running on that host and accepting TCP/IP connections? connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs...', 'NO_GRAPH_DATA']

### PAAD

- HTTP status: `200`
- Nodes: `0`, Edges (from `links`): `0`
- Has keys disease/nodes/edges/count/warnings: `True/True/False/False/True`
- PostgreSQL fallback used: `False`
- `GRAPH_FALLBACK_FROM_POSTGRES_CANDIDATES` present: `False`
- Fallback structure valid (Disease + DrugCandidate + HAS_CANDIDATE): `None`
- `NO_GRAPH_DATA` only when empty graph: `True`
- No fabricated drug nodes: `True`
- Warnings: ["Neo4j projection unavailable: ServiceUnavailable: Couldn't connect to 127.0.0.1:7687 (resolved to ()): Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다)", 'Neo4j Bolt connection failure detected. Check Neo4j service status and NEO4J_URI.', 'PostgreSQL candidate fallback unavailable: OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs the server running on that host and accepting TCP/IP connections? connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs...', 'NO_GRAPH_DATA']

### HNSC

- HTTP status: `200`
- Nodes: `0`, Edges (from `links`): `0`
- Has keys disease/nodes/edges/count/warnings: `True/True/False/False/True`
- PostgreSQL fallback used: `False`
- `GRAPH_FALLBACK_FROM_POSTGRES_CANDIDATES` present: `False`
- Fallback structure valid (Disease + DrugCandidate + HAS_CANDIDATE): `None`
- `NO_GRAPH_DATA` only when empty graph: `True`
- No fabricated drug nodes: `True`
- Warnings: ["Neo4j projection unavailable: ServiceUnavailable: Couldn't connect to 127.0.0.1:7687 (resolved to ()): Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다)", 'Neo4j Bolt connection failure detected. Check Neo4j service status and NEO4J_URI.', 'PostgreSQL candidate fallback unavailable: OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs the server running on that host and accepting TCP/IP connections? connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061) \tIs...', 'NO_GRAPH_DATA']
