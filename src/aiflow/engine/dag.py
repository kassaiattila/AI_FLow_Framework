"""Directed Acyclic Graph for workflow step ordering.

Supports: node management, edge management with conditions, topological sort,
cycle detection (loops allowed only via max_iterations), step readiness check,
and comprehensive validation.
"""
from collections import defaultdict, deque
from typing import Any

from pydantic import BaseModel

import structlog

from aiflow.engine.conditions import Condition

__all__ = ["DAG", "DAGNode", "DAGEdge", "DAGValidationError"]

logger = structlog.get_logger(__name__)


class DAGValidationError(Exception):
    """Raised when DAG validation fails."""
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"DAG validation failed: {'; '.join(errors)}")


class DAGNode(BaseModel):
    """A node in the DAG representing a workflow step."""
    name: str
    step_func: Any = None  # The decorated step function
    is_terminal: bool = False
    max_iterations: int = 1  # >1 allows controlled loops
    metadata: dict[str, Any] = {}

    model_config = {"arbitrary_types_allowed": True}


class DAGEdge(BaseModel):
    """An edge connecting two DAG nodes, optionally with a condition."""
    from_node: str
    to_node: str
    condition: Condition | None = None

    model_config = {"arbitrary_types_allowed": True}


class DAG:
    """Directed Acyclic Graph with step ordering and validation.

    Supports controlled loops via max_iterations on nodes.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, DAGNode] = {}
        self._edges: list[DAGEdge] = []
        self._adjacency: dict[str, list[str]] = defaultdict(list)
        self._reverse_adjacency: dict[str, list[str]] = defaultdict(list)

    def add_node(self, name: str, step_func: Any = None, *,
                 is_terminal: bool = False, max_iterations: int = 1,
                 metadata: dict[str, Any] | None = None) -> None:
        """Add a step node to the DAG."""
        if name in self._nodes:
            raise ValueError(f"Node '{name}' already exists in DAG")
        self._nodes[name] = DAGNode(
            name=name,
            step_func=step_func,
            is_terminal=is_terminal,
            max_iterations=max_iterations,
            metadata=metadata or {},
        )
        logger.debug("dag_node_added", node=name)

    def add_edge(self, from_node: str, to_node: str, *,
                 condition: Condition | None = None) -> None:
        """Add a directed edge between two nodes."""
        if from_node not in self._nodes:
            raise ValueError(f"Source node '{from_node}' not found in DAG")
        if to_node not in self._nodes:
            raise ValueError(f"Target node '{to_node}' not found in DAG")

        edge = DAGEdge(from_node=from_node, to_node=to_node, condition=condition)
        self._edges.append(edge)
        self._adjacency[from_node].append(to_node)
        self._reverse_adjacency[to_node].append(from_node)

    def get_node(self, name: str) -> DAGNode:
        """Get a node by name."""
        if name not in self._nodes:
            raise KeyError(f"Node '{name}' not found in DAG")
        return self._nodes[name]

    @property
    def nodes(self) -> list[str]:
        """All node names."""
        return list(self._nodes.keys())

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def get_successors(self, node: str) -> list[str]:
        """Get nodes that come after the given node."""
        return self._adjacency.get(node, [])

    def get_predecessors(self, node: str) -> list[str]:
        """Get nodes that come before the given node."""
        return self._reverse_adjacency.get(node, [])

    def get_edges_from(self, node: str) -> list[DAGEdge]:
        """Get all edges originating from a node."""
        return [e for e in self._edges if e.from_node == node]

    def get_root_nodes(self) -> list[str]:
        """Get nodes with no predecessors (entry points)."""
        return [n for n in self._nodes if not self._reverse_adjacency.get(n)]

    def get_terminal_nodes(self) -> list[str]:
        """Get terminal nodes or nodes with no successors."""
        terminals = []
        for name, node in self._nodes.items():
            if node.is_terminal or not self._adjacency.get(name):
                terminals.append(name)
        return terminals

    def topological_sort(self) -> list[str]:
        """Return nodes in topological order (Kahn's algorithm).

        Ignores back-edges from nodes with max_iterations > 1 (controlled loops).
        Raises DAGValidationError if true cycle detected.
        """
        # Build in-degree map, ignoring loop-back edges
        loop_edges = set()
        for edge in self._edges:
            if self._nodes[edge.to_node].max_iterations > 1 and \
               edge.to_node in self._reverse_adjacency.get(edge.from_node, []):
                # This might be a loop-back edge
                loop_edges.add((edge.from_node, edge.to_node))

        in_degree: dict[str, int] = {n: 0 for n in self._nodes}
        for edge in self._edges:
            if (edge.from_node, edge.to_node) not in loop_edges:
                in_degree[edge.to_node] += 1

        queue = deque([n for n, d in in_degree.items() if d == 0])
        result: list[str] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for successor in self._adjacency.get(node, []):
                if (node, successor) not in loop_edges:
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        queue.append(successor)

        if len(result) != len(self._nodes):
            missing = set(self._nodes.keys()) - set(result)
            raise DAGValidationError([f"Cycle detected involving nodes: {missing}"])

        return result

    def get_ready_steps(self, completed: set[str]) -> list[str]:
        """Get steps that are ready to execute (all predecessors completed)."""
        ready = []
        for name in self._nodes:
            if name in completed:
                continue
            predecessors = self.get_predecessors(name)
            if not predecessors or all(p in completed for p in predecessors):
                ready.append(name)
        return ready

    def validate(self) -> list[str]:
        """Validate the DAG structure. Returns list of error messages."""
        errors: list[str] = []

        # Must have at least one node
        if not self._nodes:
            errors.append("DAG has no nodes")
            return errors

        # Must have root nodes
        roots = self.get_root_nodes()
        if not roots:
            errors.append("DAG has no root nodes (no entry point)")

        # Check for unreachable nodes
        reachable = set()
        queue = deque(roots)
        while queue:
            node = queue.popleft()
            if node in reachable:
                continue
            reachable.add(node)
            for successor in self.get_successors(node):
                queue.append(successor)
        unreachable = set(self._nodes.keys()) - reachable
        if unreachable:
            errors.append(f"Unreachable nodes: {unreachable}")

        # Check edges reference existing nodes
        for edge in self._edges:
            if edge.from_node not in self._nodes:
                errors.append(f"Edge references missing source: {edge.from_node}")
            if edge.to_node not in self._nodes:
                errors.append(f"Edge references missing target: {edge.to_node}")

        # Try topological sort (catches true cycles)
        try:
            self.topological_sort()
        except DAGValidationError as e:
            errors.extend(e.errors)

        return errors

    def __repr__(self) -> str:
        return f"DAG(nodes={len(self._nodes)}, edges={len(self._edges)})"
