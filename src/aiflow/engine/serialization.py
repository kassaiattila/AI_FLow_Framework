"""Workflow serialization to/from YAML format.

Inspired by Haystack's pipeline YAML serialization.
Allows workflows to be saved, versioned, and shared as config files.
"""

from typing import Any

import structlog
import yaml

from aiflow.engine.dag import DAG

__all__ = ["serialize_workflow", "deserialize_dag_structure"]

logger = structlog.get_logger(__name__)


def serialize_workflow(
    name: str,
    version: str,
    dag: DAG,
    *,
    skill: str | None = None,
    description: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Serialize a workflow to YAML string.

    Args:
        name: Workflow name
        version: Workflow version
        dag: The workflow DAG
        skill: Optional skill name
        description: Optional description
        metadata: Optional extra metadata

    Returns:
        YAML string representation
    """
    data: dict[str, Any] = {
        "workflow": {
            "name": name,
            "version": version,
        }
    }

    if skill:
        data["workflow"]["skill"] = skill
    if description:
        data["workflow"]["description"] = description
    if metadata:
        data["workflow"]["metadata"] = metadata

    # Serialize nodes
    nodes = []
    for node_name in dag.nodes:
        node = dag.get_node(node_name)
        node_data: dict[str, Any] = {"name": node.name}
        if node.is_terminal:
            node_data["terminal"] = True
        if node.max_iterations > 1:
            node_data["max_iterations"] = node.max_iterations
        if node.metadata:
            # Exclude non-serializable items
            serializable_meta = {
                k: v
                for k, v in node.metadata.items()
                if isinstance(v, (str, int, float, bool, list, dict, type(None)))
            }
            if serializable_meta:
                node_data["metadata"] = serializable_meta
        nodes.append(node_data)
    data["steps"] = nodes

    # Serialize edges
    edges = []
    for edge in dag._edges:
        edge_data: dict[str, Any] = {
            "from": edge.from_node,
            "to": edge.to_node,
        }
        if edge.condition:
            edge_data["condition"] = edge.condition.expression
        edges.append(edge_data)
    data["edges"] = edges

    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def deserialize_dag_structure(yaml_str: str) -> dict[str, Any]:
    """Deserialize a YAML string into a DAG structure dict.

    Returns a dict with 'workflow', 'steps', and 'edges' keys
    that can be used to reconstruct a DAG.

    Note: This returns the structure only, not executable step functions.
    Step functions must be resolved separately from the skill's module.
    """
    data = yaml.safe_load(yaml_str)

    if not isinstance(data, dict) or "workflow" not in data:
        raise ValueError("Invalid workflow YAML: missing 'workflow' key")

    if "steps" not in data:
        raise ValueError("Invalid workflow YAML: missing 'steps' key")

    return {
        "workflow": data["workflow"],
        "steps": data.get("steps", []),
        "edges": data.get("edges", []),
    }
