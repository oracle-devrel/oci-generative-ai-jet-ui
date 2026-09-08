from __future__ import annotations

import json
from typing import Iterable


def build_canvas_nodes(
    topic_title: str,
    concept_labels: list[str],
    secondary_topic: str | None = None,
    secondary_concepts: list[str] | None = None,
) -> list[dict]:
    nodes: list[dict] = []
    nodes.append(
        {
            "id": "topic-main",
            "type": "file",
            "file": f"10 Topics/{topic_title}.md",
            "x": -140,
            "y": 60,
            "width": 320,
            "height": 120,
            "color": "2",
        }
    )
    for index, label in enumerate(concept_labels):
        nodes.append(
            {
                "id": f"concept-main-{index}",
                "type": "file",
                "file": f"20 Concepts/{label}.md",
                "x": -520 + (index * 260),
                "y": 320,
                "width": 240,
                "height": 110,
                "color": "4",
            }
        )
    if secondary_topic:
        nodes.append(
            {
                "id": "topic-secondary",
                "type": "file",
                "file": f"10 Topics/{secondary_topic}.md",
                "x": 520,
                "y": 120,
                "width": 280,
                "height": 110,
                "color": "5",
            }
        )
    for index, label in enumerate(secondary_concepts or []):
        nodes.append(
            {
                "id": f"concept-secondary-{index}",
                "type": "file",
                "file": f"20 Concepts/{label}.md",
                "x": 420 + (index * 220),
                "y": 340,
                "width": 210,
                "height": 100,
                "color": "6",
            }
        )
    return nodes


def build_canvas_edges(nodes: list[dict]) -> list[dict]:
    node_ids = {node["file"]: node["id"] for node in nodes if node["type"] == "file"}
    edges: list[dict] = []
    main_topic_id = node_ids.get("10 Topics/Agent Memory.md")
    secondary_topic_id = node_ids.get("10 Topics/Agent Loop.md")

    for file_path, node_id in node_ids.items():
        if file_path.startswith("20 Concepts/") and main_topic_id and file_path in {
            "20 Concepts/Episodic Memory.md",
            "20 Concepts/Semantic Memory.md",
            "20 Concepts/Procedural Memory.md",
        }:
            edges.append(
                {
                    "id": f"edge-{main_topic_id}-{node_id}",
                    "fromNode": main_topic_id,
                    "fromSide": "bottom",
                    "toNode": node_id,
                    "toSide": "top",
                    "color": "2",
                }
            )
        if file_path.startswith("20 Concepts/") and secondary_topic_id and file_path in {
            "20 Concepts/Goal.md",
            "20 Concepts/Context Retrieval.md",
            "20 Concepts/Tool Selection.md",
            "20 Concepts/Execution.md",
            "20 Concepts/Evaluation.md",
            "20 Concepts/Memory Update.md",
        }:
            edges.append(
                {
                    "id": f"edge-{secondary_topic_id}-{node_id}",
                    "fromNode": secondary_topic_id,
                    "fromSide": "bottom",
                    "toNode": node_id,
                    "toSide": "top",
                    "color": "5",
                }
            )

    bridge_pairs = [
        ("20 Concepts/Semantic Memory.md", "20 Concepts/Context Retrieval.md"),
        ("20 Concepts/Procedural Memory.md", "20 Concepts/Tool Selection.md"),
        ("20 Concepts/Procedural Memory.md", "20 Concepts/Execution.md"),
        ("20 Concepts/Episodic Memory.md", "20 Concepts/Evaluation.md"),
        ("20 Concepts/Episodic Memory.md", "20 Concepts/Memory Update.md"),
    ]
    for left, right in bridge_pairs:
        if left in node_ids and right in node_ids:
            edges.append(
                {
                    "id": f"bridge-{node_ids[left]}-{node_ids[right]}",
                    "fromNode": node_ids[left],
                    "fromSide": "right",
                    "toNode": node_ids[right],
                    "toSide": "left",
                    "color": "4",
                    "label": "bridge",
                }
            )
    return edges


def build_knowledge_map_canvas(nodes: list[dict], edges: list[dict]) -> str:
    return json.dumps({"nodes": nodes, "edges": edges}, indent=2)
