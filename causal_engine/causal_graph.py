"""Initial causal graph for the Criteo advertising experiment.

This graph is a working hypothesis. Verify the timing and meaning
of each variable against the dataset documentation before estimation.
"""

import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

graph = nx.DiGraph()

graph.add_edges_from([
    ("Treatment assignment", "Ad exposure"),
    ("Treatment assignment", "Conversion"),
    ("Ad exposure", "Conversion"),
    ("Treatment assignment", "Visit"),
    ("Ad exposure", "Visit"),
])

positions = {
    "Treatment assignment": (0, 1),
    "Ad exposure": (1, 1),
    "Conversion": (2, 1.5),
    "Visit": (2, 0.5),
}

plt.figure(figsize=(10, 5))
nx.draw_networkx(
    graph,
    pos=positions,
    node_size=3500,
    node_color="lightblue",
    font_size=9,
    arrows=True,
    arrowsize=20,
)
plt.title("Initial Criteo Treatment Causal Graph")
plt.axis("off")

output = Path("reports/criteo_causal_graph.png")
output.parent.mkdir(parents=True, exist_ok=True)
plt.tight_layout()
plt.savefig(output, dpi=160, bbox_inches="tight")
print(f"Saved causal graph to {output}")
plt.close()
