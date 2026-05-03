"""pyvis renderer: generates interactive HTML visualization of the knowledge graph."""

from __future__ import annotations

import json
import os

import networkx as nx
from pyvis.network import Network

# Read template relative to this file
_TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))

# Color palette per entity role
ROLE_COLORS = {
    "core": "#7F77DD",    # Purple — entities with inbound FKs
    "leaf": "#1D9E75",    # Teal — no inbound FKs
    "bridge": "#BA7517",  # Amber — junction/bridge tables
}


def render_html(G: nx.DiGraph, output_path: str) -> None:
    """Render the graph as an interactive self-contained HTML file."""
    net = Network(
        height="100%",
        width="100%",
        directed=True,
        notebook=False,
        bgcolor="#1a1a2e",
        font_color="#e0e0e0",
    )

    # Physics layout
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=200,
        spring_strength=0.001,
        damping=0.09,
        overlap=0,
    )

    # Configure node defaults
    for node_id, ndata in G.nodes(data=True):
        role = ndata.get("role", "leaf")
        color = ROLE_COLORS.get(role, "#1D9E75")
        attr_count = ndata.get("attribute_count", len(ndata.get("attributes", [])))
        size = max(15, min(50, 15 + attr_count * 3))

        # Build tooltip
        pks = ndata.get("pks", [])
        fks = ndata.get("fks", [])
        source_type = ndata.get("source_type", "")
        source_files = ndata.get("source_files", [])

        title = f"<b>{node_id}</b><br>"
        title += f"Type: {source_type}<br>"
        title += f"Attributes: {attr_count}<br>"
        if pks:
            title += f"PKs: {', '.join(pks)}<br>"
        if fks:
            title += f"FKs: {', '.join(fks)}<br>"
        if source_files:
            files = ", ".join(os.path.basename(f) for f in source_files[:3])
            title += f"Sources: {files}"

        role_label = {"core": "Core", "leaf": "Leaf", "bridge": "Bridge"}.get(role, role)

        net.add_node(
            node_id,
            label=node_id,
            title=title,
            color=color,
            size=size,
            shape="dot",
            borderWidth=2,
            borderWidthSelected=4,
            group=role_label,
        )

    for u, v, edata in G.edges(data=True):
        rel_label = edata.get("relationship", "FK_TO")
        via = edata.get("via", "")
        cardinality = edata.get("cardinality", "")

        label = f"{rel_label}"
        if via:
            label += f" ({via})"

        title = f"{rel_label}<br>Cardinality: {cardinality}<br>Via: {via}"

        net.add_edge(
            u, v,
            label=label,
            title=title,
            arrows="to",
            color={"color": "#5a5a8a", "highlight": "#8a8aff"},
            font={"color": "#888888", "size": 10, "background": "#1a1a2e"},
        )

    # Generate base HTML
    html = net.generate_html()

    # Inject sidebar + filters + custom JS
    custom_html = _build_custom_html(G)

    # Insert custom HTML right after <body> and custom JS before </body>
    html = html.replace("<body>", f"<body>\n{custom_html['sidebar']}\n{custom_html['filters']}")
    html = html.replace("</body>", f"{custom_html['scripts']}\n</body>")
    html = html.replace("</head>", f"{custom_html['styles']}\n</head>")

    with open(output_path, "w") as f:
        f.write(html)


def _build_custom_html(G: nx.DiGraph) -> dict[str, str]:
    """Build sidebar, filter controls, and interactive JS for the visualization."""
    node_data_json = {}
    for nid, ndata in G.nodes(data=True):
        node_data_json[nid] = {
            "type": ndata.get("type", "entity"),
            "sourceTable": ndata.get("source_table", nid),
            "sourceType": ndata.get("source_type", ""),
            "sourceFiles": [os.path.basename(f) for f in ndata.get("source_files", [])],
            "attributes": ndata.get("attributes", []),
            "attributeTypes": ndata.get("attribute_types", {}),
            "pks": ndata.get("pks", []),
            "fks": ndata.get("fks", []),
            "role": ndata.get("role", "leaf"),
        }

    entity_types = sorted(set(
        ndata.get("source_type", "") for _nid, ndata in G.nodes(data=True) if ndata.get("source_type")
    ))
    roles = ["core", "leaf", "bridge"]

    styles = """
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; overflow: hidden; }
#mynetwork { width: 100vw; height: 100vh; position: absolute; top: 0; left: 0; z-index: 1; }
#sidebar {
  position: absolute; top: 0; right: -380px; width: 380px; height: 100vh;
  background: #16213e; color: #e0e0e0; z-index: 10; transition: right 0.3s ease;
  padding: 20px; overflow-y: auto; box-shadow: -4px 0 15px rgba(0,0,0,0.4);
}
#sidebar.open { right: 0; }
#sidebar h2 { color: #7F77DD; margin-bottom: 12px; font-size: 1.2em; }
#sidebar h3 { color: #1D9E75; margin-top: 16px; margin-bottom: 8px; font-size: 0.95em; }
#sidebar .attr-row { display: flex; justify-content: space-between; padding: 4px 0;
  border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 0.85em; }
#sidebar .attr-row .attr-name { font-weight: 600; color: #ccc; }
#sidebar .attr-row .attr-type { color: #888; font-family: monospace; }
#sidebar .attr-row .attr-pk { color: #f0c040; font-size: 0.7em; margin-left: 4px; }
#sidebar .attr-row .attr-fk { color: #40c0f0; font-size: 0.7em; margin-left: 4px; }
#sidebar .close-btn { position: absolute; top: 10px; right: 10px;
  background: none; border: none; color: #888; font-size: 1.5em; cursor: pointer; }
#sidebar .close-btn:hover { color: #fff; }
#sidebar .meta { font-size: 0.8em; color: #888; }
#sidebar .badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: 0.7em; margin: 2px; }
.badge-core { background: #7F77DD33; color: #7F77DD; }
.badge-leaf { background: #1D9E7533; color: #1D9E75; }
.badge-bridge { background: #BA751733; color: #BA7517; }
#filters {
  position: absolute; top: 16px; left: 16px; z-index: 10;
  background: #16213ecc; backdrop-filter: blur(8px); border-radius: 12px;
  padding: 14px 18px; color: #e0e0e0; font-size: 0.8em;
  display: flex; flex-direction: column; gap: 8px; min-width: 220px;
}
#filters label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
#filters select { background: #1a1a2e; color: #e0e0e0; border: 1px solid #444;
  border-radius: 6px; padding: 4px 8px; }
#filters button { background: #7F77DD; color: #fff; border: none; border-radius: 6px;
  padding: 6px 12px; cursor: pointer; font-size: 0.85em; }
#filters button:hover { background: #6a61cc; }
#filters .toggle-row { display: flex; gap: 8px; align-items: center; }
</style>
"""

    sidebar = """
<div id="filters">
  <div style="font-weight:700; color:#7F77DD; margin-bottom:4px;">Semantic Mesh</div>
  <select id="role-filter" onchange="applyFilters()">
    <option value="all">All Roles</option>
    <option value="core">Core</option>
    <option value="leaf">Leaf</option>
    <option value="bridge">Bridge</option>
  </select>
  <div class="toggle-row">
    <label><input type="checkbox" id="show-labels" checked onchange="toggleLabels()"> Edge Labels</label>
  </div>
  <div class="toggle-row">
    <label><input type="checkbox" id="physics-toggle" checked onchange="togglePhysics()"> Physics</label>
  </div>
  <button onclick="resetView()">Reset View</button>
</div>
<div id="sidebar">
  <button class="close-btn" onclick="closeSidebar()">&times;</button>
  <div id="sidebar-content"><em>Click a node to see details</em></div>
</div>
"""

    scripts = f"""
<script>
const nodeData = {json.dumps(node_data_json, indent=2)};
let _network = null;

function getNetwork() {{
  if (!_network) {{
    const container = document.getElementById('mynetwork');
    _network = container ? vis.Network.getInstance(container) : null;
  }}
  return _network;
}}

// Wait for network to be ready, then attach click handler
document.addEventListener('DOMContentLoaded', function() {{
  setTimeout(function() {{
    const net = getNetwork();
    if (net) {{
      net.on('click', function(params) {{
        if (params.nodes.length > 0) {{
          const nodeId = params.nodes[0];
          showNodeDetails(nodeId);
        }}
      }});
      net.on('doubleClick', function(params) {{
        if (params.nodes.length > 0) {{
          const nodeId = params.nodes[0];
          net.focus(nodeId, {{scale: 1.5, animation: true}});
        }}
      }});
    }}
  }}, 500);
}});

function showNodeDetails(nodeId) {{
  const data = nodeData[nodeId];
  if (!data) return;

  const roleBadge = '<span class="badge badge-' + data.role + '">' + data.role + '</span>';
  let html = '<h2>' + nodeId + ' ' + roleBadge + '</h2>';

  html += '<div class="meta">';
  html += 'Source: ' + (data.sourceTable || nodeId) + '<br>';
  html += 'Type: ' + data.sourceType + '<br>';
  html += 'Files: ' + (data.sourceFiles || []).join(', ') + '<br>';
  html += '</div>';

  html += '<h3>Attributes (' + data.attributes.length + ')</h3>';
  data.attributes.forEach(function(attr) {{
    const type = data.attributeTypes[attr] || 'unknown';
    const isPk = data.pks.includes(attr);
    const isFk = data.fks.includes(attr);
    let badges = '';
    if (isPk) badges += '<span class="attr-pk">PK</span>';
    if (isFk) badges += '<span class="attr-fk">FK</span>';
    html += '<div class="attr-row">';
    html += '<span class="attr-name">' + attr + badges + '</span>';
    html += '<span class="attr-type">' + type + '</span>';
    html += '</div>';
  }});

  document.getElementById('sidebar-content').innerHTML = html;
  document.getElementById('sidebar').classList.add('open');
}}

function closeSidebar() {{
  document.getElementById('sidebar').classList.remove('open');
}}

function applyFilters() {{
  const net = getNetwork();
  if (!net) return;
  const role = document.getElementById('role-filter').value;

  const allNodes = net.body.data.nodes;
  const updates = [];
  allNodes.forEach(function(node) {{
    const data = nodeData[node.id];
    if (!data) return;
    if (role === 'all' || data.role === role) {{
      updates.push({{id: node.id, hidden: false}});
    }} else {{
      updates.push({{id: node.id, hidden: true}});
    }}
  }});
  net.body.data.nodes.update(updates);

  // Also hide edges connected to hidden nodes
  const allEdges = net.body.data.edges;
  const edgeUpdates = [];
  allEdges.forEach(function(edge) {{
    const srcData = nodeData[edge.from];
    const tgtData = nodeData[edge.to];
    const srcHidden = (role !== 'all' && srcData && srcData.role !== role);
    const tgtHidden = (role !== 'all' && tgtData && tgtData.role !== role);
    edgeUpdates.push({{id: edge.id, hidden: srcHidden || tgtHidden}});
  }});
  net.body.data.edges.update(edgeUpdates);
}}

function toggleLabels() {{
  // Toggle edge label visibility via font size
  const show = document.getElementById('show-labels').checked;
  const net = getNetwork();
  if (!net) return;
  const edges = net.body.data.edges;
  const updates = [];
  edges.forEach(function(edge) {{
    updates.push({{id: edge.id, font: {{size: show ? 10 : 0}}}});
  }});
  net.body.data.edges.update(updates);
}}

function togglePhysics() {{
  const on = document.getElementById('physics-toggle').checked;
  const net = getNetwork();
  if (!net) return;
  net.setOptions({{physics: {{enabled: on}}}});
}}

function resetView() {{
  const net = getNetwork();
  if (!net) return;
  net.fit({{animation: true}});
}}
</script>
"""

    return {"sidebar": sidebar, "filters": "", "styles": styles, "scripts": scripts}
