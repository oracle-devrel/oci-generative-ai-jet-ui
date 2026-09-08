from __future__ import annotations


def build_concept_tracker_base() -> str:
    return """
filters:
  and:
    - file.inFolder("20 Concepts")
properties:
  topic:
    displayName: Topic
  score:
    displayName: Score
  band:
    displayName: Band
  delta:
    displayName: Delta
  trend:
    displayName: Trend
  last_reviewed:
    displayName: Last Reviewed
views:
  - type: table
    name: Agent Memory
    filters:
      and:
        - 'topic == "agent-memory"'
    order:
      - score
      - delta
  - type: table
    name: Weakest Systemwide
    order:
      - score
      - delta
""".lstrip()
