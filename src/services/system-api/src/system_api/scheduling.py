from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DagResolutionResult:
    ok: bool
    order: tuple[str, ...]
    reason_code: str
    detail: str


_REASON_OK = "DAG_RESOLVE_OK"
_REASON_UNKNOWN_NODE = "DAG_UNKNOWN_NODE"
_REASON_SELF_DEP = "DAG_SELF_DEPENDENCY"
_REASON_CYCLE = "DAG_CYCLE_DETECTED"


def resolve_dag(nodes: list[str], dependencies: dict[str, list[str]]) -> DagResolutionResult:
    ordered_nodes = sorted(dict.fromkeys(nodes))
    node_set = set(ordered_nodes)

    for node in sorted(dependencies):
        if node not in node_set:
            return DagResolutionResult(False, tuple(), _REASON_UNKNOWN_NODE, f"unknown node: {node}")
        for dep in sorted(dependencies[node]):
            if dep not in node_set:
                return DagResolutionResult(False, tuple(), _REASON_UNKNOWN_NODE, f"unknown dependency: {node}->{dep}")
            if dep == node:
                return DagResolutionResult(False, tuple(), _REASON_SELF_DEP, f"self dependency: {node}")

    indegree = {n: 0 for n in ordered_nodes}
    outgoing = {n: [] for n in ordered_nodes}
    for node in sorted(dependencies):
        for dep in sorted(dict.fromkeys(dependencies[node])):
            outgoing[dep].append(node)
            indegree[node] += 1

    ready = sorted([n for n in ordered_nodes if indegree[n] == 0])
    result: list[str] = []
    while ready:
        current = ready.pop(0)
        result.append(current)
        for nxt in sorted(outgoing[current]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
                ready.sort()

    if len(result) != len(ordered_nodes):
        cycle_nodes = sorted([n for n, degree in indegree.items() if degree > 0])
        return DagResolutionResult(False, tuple(result), _REASON_CYCLE, f"cycle nodes: {','.join(cycle_nodes)}")

    return DagResolutionResult(True, tuple(result), _REASON_OK, "resolved")
