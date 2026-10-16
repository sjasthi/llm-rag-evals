"""Create searchable descriptions from simple Mermaid flowcharts."""

from __future__ import annotations

import re


NODE_PATTERN = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\[([^\]]+)\]|\{([^}]+)\}|\(([^)]+)\))?"
)

EDGE_PATTERN = re.compile(
    r"^\s*(.+?)\s*-->\s*(?:\|([^|]+)\|\s*)?(.+?)\s*$"
)


def _parse_node(value: str) -> tuple[str, str]:
    """Return the node identifier and its readable label."""
    match = NODE_PATTERN.fullmatch(value.strip())

    if not match:
        return value.strip(), value.strip()

    node_id = match.group(1)
    label = next(
        (group for group in match.groups()[1:] if group is not None),
        node_id,
    )

    return node_id, label.strip()


def describe_mermaid_flowchart(source: str) -> str:
    """Describe supported Mermaid flowchart edges in natural language."""
    nodes: dict[str, str] = {}
    edges: list[tuple[str, str, str | None]] = []

    for line in source.splitlines():
        line = line.strip()

        if not line or line.startswith("```") or line.startswith("~~~"):
            continue

        if line.lower().startswith(("flowchart ", "graph ")):
            continue

        match = EDGE_PATTERN.match(line)

        if not match:
            continue

        source_id, source_label = _parse_node(match.group(1))
        target_id, target_label = _parse_node(match.group(3))

        # Preserve an existing descriptive label when a node is
        # referenced later using only its identifier.
        if source_id not in nodes or source_label != source_id:
            nodes[source_id] = source_label

        if target_id not in nodes or target_label != target_id:
            nodes[target_id] = target_label

        edges.append(
            (source_id, target_id, match.group(2))
        )

    descriptions: list[str] = []

    for source_id, target_id, branch in edges:
        source_label = nodes[source_id]
        target_label = nodes[target_id]

        if branch:
            descriptions.append(
                f'From "{source_label}", the "{branch.strip()}" '
                f'branch leads to "{target_label}".'
            )
        else:
            descriptions.append(
                f'"{source_label}" leads to "{target_label}".'
            )

    # Describe connected pairs of edges to make multi-step
    # workflows easier to retrieve using natural-language questions.
    for first_source, first_target, first_branch in edges:
        for second_source, second_target, second_branch in edges:
            if first_target != second_source:
                continue

            first_label = nodes[first_source]
            middle_label = nodes[first_target]
            final_label = nodes[second_target]

            if first_branch:
                descriptions.append(
                    f'When the "{first_branch.strip()}" branch is taken '
                    f'at "{first_label}", the workflow proceeds to '
                    f'"{middle_label}", then to "{final_label}".'
                )
            else:
                descriptions.append(
                    f'The workflow proceeds from "{first_label}" '
                    f'to "{middle_label}", then to "{final_label}".'
                )

    if not descriptions:
        return ""

    return (
        "Mermaid flowchart relationships:\n"
        + "\n".join(descriptions)
    )