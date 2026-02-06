"""Network analysis commands using NetworkX."""

from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import deeptrace.state as _state
from deeptrace.console import console, err_console
from deeptrace.db import CaseDatabase

app = typer.Typer(no_args_is_help=True)


def _open_case_db(case: str) -> CaseDatabase:
    case_dir = _state.CASES_DIR / case
    if not case_dir.exists():
        err_console.print(f"[bold red]Error:[/] Case '{case}' not found.")
        raise typer.Exit(1)
    db = CaseDatabase(case_dir / "case.db")
    db.open()
    return db


def _check_networkx():
    try:
        import networkx  # noqa: F401
    except ImportError:
        err_console.print(
            "[bold red]Error:[/] networkx is required for network analysis.\n"
            "Install with: pip install networkx"
        )
        raise typer.Exit(1) from None


def _check_pyvis():
    try:
        import pyvis  # noqa: F401
    except ImportError:
        err_console.print(
            "[bold red]Error:[/] pyvis is required for HTML visualization.\n"
            "Install with: pip install pyvis"
        )
        raise typer.Exit(1) from None


def _truncate(text: str, length: int = 60) -> str:
    return (text[:length] + "...") if len(text) > length else text


def _build_graph(db: CaseDatabase):
    """Build a NetworkX graph from all case data.

    Node types: entity, evidence, event, hypothesis, suspect_pool, source
    Edges represent relationships found in data (explicit relationships table,
    shared source links, hypothesis-evidence scores, etc.)
    """
    import networkx as nx

    G = nx.Graph()

    # --- Nodes ---

    # Entities
    for row in db.fetchall("SELECT * FROM entities"):
        G.add_node(
            f"entity:{row['id']}",
            label=row["name"],
            node_type="entity",
            entity_type=row["entity_type"],
            confidence=row["confidence"],
            db_id=row["id"],
        )

    # Evidence items
    for row in db.fetchall("SELECT * FROM evidence_items"):
        G.add_node(
            f"evidence:{row['id']}",
            label=row["name"],
            node_type="evidence",
            evidence_type=row["evidence_type"],
            status=row["status"],
            db_id=row["id"],
        )

    # Events
    for row in db.fetchall("SELECT * FROM events ORDER BY timestamp_start"):
        G.add_node(
            f"event:{row['id']}",
            label=_truncate(row["description"]),
            node_type="event",
            timestamp=row["timestamp_start"],
            confidence=row["confidence"],
            db_id=row["id"],
        )

    # Hypotheses
    for row in db.fetchall("SELECT * FROM hypotheses"):
        G.add_node(
            f"hypothesis:{row['id']}",
            label=_truncate(row["description"]),
            node_type="hypothesis",
            tier=row["tier"],
            db_id=row["id"],
        )

    # Suspect pools
    for row in db.fetchall("SELECT * FROM suspect_pools"):
        G.add_node(
            f"suspect:{row['id']}",
            label=row["category"],
            node_type="suspect_pool",
            priority=row["priority"],
            db_id=row["id"],
        )

    # Sources
    for row in db.fetchall("SELECT * FROM sources"):
        G.add_node(
            f"source:{row['id']}",
            label=f"Source {row['id']} ({row['source_type']})",
            node_type="source",
            source_type=row["source_type"],
            db_id=row["id"],
        )

    # --- Edges ---

    # Explicit relationships between entities
    for row in db.fetchall("SELECT * FROM relationships"):
        a = f"entity:{row['entity_a_id']}"
        b = f"entity:{row['entity_b_id']}"
        if G.has_node(a) and G.has_node(b):
            G.add_edge(
                a, b,
                edge_type="relationship",
                relationship_type=row["relationship_type"],
                strength=row["strength"],
                confirmed=bool(row["confirmed"]),
            )

    # Entity -> canonical entity (alias/resolution links)
    for row in db.fetchall("SELECT id, canonical_id FROM entities WHERE canonical_id IS NOT NULL"):
        a = f"entity:{row['id']}"
        b = f"entity:{row['canonical_id']}"
        if G.has_node(a) and G.has_node(b):
            G.add_edge(a, b, edge_type="alias")

    # Evidence -> source
    for row in db.fetchall("SELECT id, source_id FROM evidence_items WHERE source_id IS NOT NULL"):
        G.add_edge(
            f"evidence:{row['id']}",
            f"source:{row['source_id']}",
            edge_type="sourced_from",
        )

    # Event -> source
    for row in db.fetchall("SELECT id, source_id FROM events WHERE source_id IS NOT NULL"):
        ev = f"event:{row['id']}"
        src = f"source:{row['source_id']}"
        if G.has_node(ev) and G.has_node(src):
            G.add_edge(ev, src, edge_type="sourced_from")

    # Entity -> source
    for row in db.fetchall("SELECT id, source_id FROM entities WHERE source_id IS NOT NULL"):
        ent = f"entity:{row['id']}"
        src = f"source:{row['source_id']}"
        if G.has_node(ent) and G.has_node(src):
            G.add_edge(ent, src, edge_type="sourced_from")

    # Hypothesis <-> evidence (ACH matrix)
    for row in db.fetchall("SELECT * FROM hypothesis_evidence_scores"):
        h = f"hypothesis:{row['hypothesis_id']}"
        e = f"evidence:{row['evidence_id']}"
        if G.has_node(h) and G.has_node(e):
            G.add_edge(
                h, e,
                edge_type="ach_score",
                consistency=row["consistency"],
                diagnostic_weight=row["diagnostic_weight"],
            )

    return G


@app.command()
def summary(
    case: Annotated[str, typer.Option(help="Case slug")] = "",
) -> None:
    """Show network statistics for the case graph."""
    _check_networkx()
    import networkx as nx

    db = _open_case_db(case)
    try:
        G = _build_graph(db)

        if G.number_of_nodes() == 0:
            console.print("[dim]No data in case to analyze.[/]")
            return

        # Node counts by type
        type_counts: dict[str, int] = {}
        for _, data in G.nodes(data=True):
            t = data.get("node_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        table = Table(title="Network Summary", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="white")
        table.add_column("Value", style="bold green", justify="right")

        table.add_row("Total nodes", str(G.number_of_nodes()))
        table.add_row("Total edges", str(G.number_of_edges()))
        table.add_row("Connected components", str(nx.number_connected_components(G)))

        for node_type, count in sorted(type_counts.items()):
            table.add_row(f"  {node_type} nodes", str(count))

        # Edge counts by type
        edge_counts: dict[str, int] = {}
        for _, _, data in G.edges(data=True):
            t = data.get("edge_type", "unknown")
            edge_counts[t] = edge_counts.get(t, 0) + 1

        for edge_type, count in sorted(edge_counts.items()):
            table.add_row(f"  {edge_type} edges", str(count))

        # Density
        if G.number_of_nodes() > 1:
            table.add_row("Graph density", f"{nx.density(G):.4f}")

        console.print(table)

        # Isolated nodes (no connections)
        isolated = list(nx.isolates(G))
        if isolated:
            console.print(
                f"\n[bold yellow]Isolated nodes ({len(isolated)}):[/] "
                "These have no connections to other case data."
            )
            for node_id in isolated:
                data = G.nodes[node_id]
                ntype = data.get("node_type", "?")
                label = data.get("label", node_id)
                console.print(f"  [dim]{ntype}[/] {label}")
    finally:
        db.close()


@app.command()
def connections(
    case: Annotated[str, typer.Option(help="Case slug")] = "",
    node: Annotated[str | None, typer.Option(help="Node ID (e.g. evidence:3, entity:1)")] = None,
    node_type: Annotated[str | None, typer.Option("--type", help="Filter by node type")] = None,
) -> None:
    """Show connections for a specific node or most-connected nodes."""
    _check_networkx()

    db = _open_case_db(case)
    try:
        G = _build_graph(db)

        if G.number_of_nodes() == 0:
            console.print("[dim]No data in case to analyze.[/]")
            return

        if node:
            # Show connections for a specific node
            if node not in G:
                err_console.print(f"[bold red]Error:[/] Node '{node}' not found.")
                raise typer.Exit(1)

            data = G.nodes[node]
            console.print(Panel(
                f"Type: {data.get('node_type', '?')}\nLabel: {data.get('label', '?')}",
                title=f"[bold cyan]{node}[/]",
            ))

            neighbors = list(G.neighbors(node))
            if not neighbors:
                console.print("[dim]No connections.[/]")
                return

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Connected To", style="white")
            table.add_column("Type", style="dim", width=14)
            table.add_column("Edge Type", style="green", width=16)
            table.add_column("Details", style="dim")

            for neighbor in sorted(neighbors):
                ndata = G.nodes[neighbor]
                edata = G.edges[node, neighbor]
                details = ""
                if edata.get("relationship_type"):
                    details = edata["relationship_type"]
                elif edata.get("consistency"):
                    weight = edata.get("diagnostic_weight", "?")
                    details = f"ACH: {edata['consistency']} (weight: {weight})"

                table.add_row(
                    ndata.get("label", neighbor),
                    ndata.get("node_type", "?"),
                    edata.get("edge_type", "?"),
                    details,
                )
            console.print(table)
        else:
            # Show most-connected nodes
            nodes = list(G.nodes(data=True))
            if node_type:
                nodes = [(n, d) for n, d in nodes if d.get("node_type") == node_type]

            if not nodes:
                console.print("[dim]No matching nodes.[/]")
                return

            # Sort by degree (number of connections)
            ranked = sorted(nodes, key=lambda x: G.degree(x[0]), reverse=True)

            table = Table(
                title="Most Connected Nodes",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Node", style="white")
            table.add_column("Type", style="dim", width=14)
            table.add_column("Connections", style="bold green", justify="right", width=12)
            table.add_column("Label", style="white")

            for node_id, data in ranked[:20]:
                degree = G.degree(node_id)
                if degree == 0:
                    continue
                table.add_row(
                    node_id,
                    data.get("node_type", "?"),
                    str(degree),
                    data.get("label", ""),
                )
            console.print(table)
    finally:
        db.close()


@app.command()
def clusters(
    case: Annotated[str, typer.Option(help="Case slug")] = "",
) -> None:
    """Identify connected components (clusters) in the case graph."""
    _check_networkx()
    import networkx as nx

    db = _open_case_db(case)
    try:
        G = _build_graph(db)

        if G.number_of_nodes() == 0:
            console.print("[dim]No data in case to analyze.[/]")
            return

        components = sorted(nx.connected_components(G), key=len, reverse=True)

        if len(components) <= 1:
            console.print("[green]All nodes are in a single connected component.[/]")
            return

        console.print(
            f"[bold yellow]Found {len(components)} separate clusters.[/] "
            "Disconnected clusters may indicate missing links.\n"
        )

        for i, component in enumerate(components, 1):
            type_counts: dict[str, int] = {}
            labels: list[str] = []
            for node_id in component:
                data = G.nodes[node_id]
                t = data.get("node_type", "unknown")
                type_counts[t] = type_counts.get(t, 0) + 1
                labels.append(f"  [{t}] {data.get('label', node_id)}")

            type_summary = ", ".join(f"{count} {t}" for t, count in sorted(type_counts.items()))
            content = f"[dim]{type_summary}[/]\n" + "\n".join(labels[:15])
            if len(labels) > 15:
                content += f"\n  [dim]... and {len(labels) - 15} more[/]"

            console.print(Panel(
                content,
                title=f"[bold cyan]Cluster {i}[/] ({len(component)} nodes)",
                border_style="cyan",
            ))
    finally:
        db.close()


@app.command()
def bridges(
    case: Annotated[str, typer.Option(help="Case slug")] = "",
) -> None:
    """Find bridge nodes and edges whose removal would disconnect parts of the graph.

    Bridge edges are single points of failure in the network — if removed, they
    split the graph into disconnected components. Bridge nodes (articulation points)
    are similar: removing them disconnects the graph.
    """
    _check_networkx()
    import networkx as nx

    db = _open_case_db(case)
    try:
        G = _build_graph(db)

        if G.number_of_nodes() < 3:
            console.print("[dim]Need at least 3 nodes for bridge analysis.[/]")
            return

        # Articulation points (nodes)
        art_points = list(nx.articulation_points(G))

        if art_points:
            console.print(
                f"[bold yellow]Articulation points ({len(art_points)}):[/] "
                "Removing these nodes would disconnect parts of the graph.\n"
            )
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Node", style="white")
            table.add_column("Type", style="dim", width=14)
            table.add_column("Connections", justify="right", width=12)
            table.add_column("Label", style="white")

            for node_id in sorted(art_points, key=lambda n: G.degree(n), reverse=True):
                data = G.nodes[node_id]
                table.add_row(
                    node_id,
                    data.get("node_type", "?"),
                    str(G.degree(node_id)),
                    data.get("label", ""),
                )
            console.print(table)
        else:
            console.print("[green]No articulation points — the network is well-connected.[/]")

        # Bridge edges
        bridge_edges = list(nx.bridges(G))
        if bridge_edges:
            console.print(
                f"\n[bold yellow]Bridge edges ({len(bridge_edges)}):[/] "
                "Single connections between otherwise separate clusters.\n"
            )
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("From", style="white")
            table.add_column("To", style="white")
            table.add_column("Edge Type", style="green")

            for a, b in bridge_edges[:20]:
                a_label = G.nodes[a].get("label", a)
                b_label = G.nodes[b].get("label", b)
                edge_data = G.edges[a, b]
                table.add_row(a_label, b_label, edge_data.get("edge_type", "?"))

            if len(bridge_edges) > 20:
                console.print(f"  [dim]... and {len(bridge_edges) - 20} more[/]")
            console.print(table)
        else:
            console.print("\n[green]No bridge edges — multiple paths exist between all nodes.[/]")
    finally:
        db.close()


@app.command()
def paths(
    case: Annotated[str, typer.Option(help="Case slug")] = "",
    source: Annotated[str, typer.Option(help="Start node (e.g. entity:1)")] = "",
    target: Annotated[str, typer.Option(help="End node (e.g. suspect:3)")] = "",
) -> None:
    """Find shortest path between two nodes in the case graph."""
    _check_networkx()
    import networkx as nx

    db = _open_case_db(case)
    try:
        G = _build_graph(db)

        if source not in G:
            err_console.print(f"[bold red]Error:[/] Node '{source}' not found.")
            raise typer.Exit(1)
        if target not in G:
            err_console.print(f"[bold red]Error:[/] Node '{target}' not found.")
            raise typer.Exit(1)

        try:
            path = nx.shortest_path(G, source, target)
        except nx.NetworkXNoPath:
            console.print("[bold red]No path exists[/] between these nodes.")
            return

        console.print(
            f"[bold green]Path found[/] ({len(path) - 1} hops):\n"
        )

        for i, node_id in enumerate(path):
            data = G.nodes[node_id]
            prefix = "  " if i > 0 else ""
            connector = "-> " if i > 0 else "   "
            label = data.get("label", node_id)
            ntype = data.get("node_type", "?")

            if i > 0:
                edge_data = G.edges[path[i - 1], node_id]
                edge_label = edge_data.get("edge_type", "?")
                console.print(f"{prefix}  [dim]|  ({edge_label})[/]")

            console.print(f"{prefix}{connector}[bold]{label}[/] [dim]({ntype})[/]")
    finally:
        db.close()


# -- Color maps shared by visualize and inspect --

NODE_COLORS = {
    "entity": "#3498db",
    "evidence": "#e74c3c",
    "event": "#2ecc71",
    "hypothesis": "#f39c12",
    "suspect_pool": "#9b59b6",
    "source": "#95a5a6",
}

NODE_SHAPES = {
    "entity": "dot",
    "evidence": "triangle",
    "event": "square",
    "hypothesis": "diamond",
    "suspect_pool": "star",
    "source": "database",
}

EDGE_COLORS = {
    "relationship": "#3498db",
    "alias": "#95a5a6",
    "sourced_from": "#2ecc71",
    "ach_score": "#f39c12",
}

RICH_NODE_STYLES = {
    "entity": "bold blue",
    "evidence": "bold red",
    "event": "bold green",
    "hypothesis": "bold yellow",
    "suspect_pool": "bold magenta",
    "source": "dim",
}


def _node_tooltip(node_id: str, data: dict) -> str:
    """Build a multi-line HTML tooltip for a graph node."""
    lines = [f"<b>{data.get('label', node_id)}</b>"]
    lines.append(f"ID: {node_id}")
    lines.append(f"Type: {data.get('node_type', '?')}")

    if data.get("entity_type"):
        lines.append(f"Entity type: {data['entity_type']}")
    if data.get("evidence_type"):
        lines.append(f"Evidence type: {data['evidence_type']}")
    if data.get("status"):
        lines.append(f"Status: {data['status']}")
    if data.get("tier"):
        lines.append(f"Tier: {data['tier']}")
    if data.get("priority"):
        lines.append(f"Priority: {data['priority']}")
    if data.get("confidence"):
        lines.append(f"Confidence: {data['confidence']}")
    if data.get("timestamp"):
        lines.append(f"Time: {data['timestamp']}")
    if data.get("source_type"):
        lines.append(f"Source type: {data['source_type']}")

    return "<br>".join(lines)


@app.command()
def visualize(
    case: Annotated[str, typer.Option(help="Case slug")] = "",
    output: Annotated[
        str | None,
        typer.Option(help="Output HTML file path"),
    ] = None,
    no_open: Annotated[
        bool,
        typer.Option("--no-open", help="Don't auto-open in browser"),
    ] = False,
) -> None:
    """Generate an interactive HTML network graph and open in browser."""
    _check_networkx()
    _check_pyvis()
    from pyvis.network import Network

    db = _open_case_db(case)
    try:
        G = _build_graph(db)

        if G.number_of_nodes() == 0:
            console.print("[dim]No data in case to visualize.[/]")
            return

        out_path = output or f"{case}-network.html"

        net = Network(
            height="100vh",
            width="100%",
            bgcolor="#1a1a2e",
            font_color="white",
            directed=False,
        )

        # Add nodes with styling
        for node_id, data in G.nodes(data=True):
            ntype = data.get("node_type", "unknown")
            degree = G.degree(node_id)
            net.add_node(
                node_id,
                label=_truncate(data.get("label", node_id), 30),
                title=_node_tooltip(node_id, data),
                color=NODE_COLORS.get(ntype, "#cccccc"),
                shape=NODE_SHAPES.get(ntype, "dot"),
                size=max(10, 8 + degree * 4),
            )

        # Add edges with styling
        for a, b, edata in G.edges(data=True):
            etype = edata.get("edge_type", "unknown")
            edge_label = etype
            if edata.get("relationship_type"):
                edge_label = edata["relationship_type"]
            elif edata.get("consistency"):
                edge_label = f"ACH:{edata['consistency']}"

            net.add_edge(
                a, b,
                title=edge_label,
                color=EDGE_COLORS.get(etype, "#666666"),
                dashes=etype == "alias",
                width=2 if etype in ("relationship", "ach_score") else 1,
            )

        # Physics config for readable layout
        net.set_options("""
        {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -30000,
              "centralGravity": 0.3,
              "springLength": 150,
              "springConstant": 0.04,
              "damping": 0.09
            },
            "minVelocity": 0.75
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "navigationButtons": true
          }
        }
        """)

        net.save_graph(out_path)

        # Inject a legend into the HTML
        _inject_legend(out_path)

        console.print(
            f"Saved interactive graph to [bold cyan]{out_path}[/] "
            f"({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)"
        )

        if not no_open:
            import webbrowser

            webbrowser.open(f"file://{Path(out_path).resolve()}")
    finally:
        db.close()


def _inject_legend(html_path: str) -> None:
    """Inject a floating legend div into the pyvis HTML output."""
    legend_items = "".join(
        f'<div style="display:flex;align-items:center;margin:4px 0">'
        f'<span style="display:inline-block;width:14px;height:14px;'
        f"background:{color};border-radius:3px;margin-right:8px\"></span>"
        f"{ntype}</div>"
        for ntype, color in NODE_COLORS.items()
    )

    legend_html = (
        '<div id="dt-legend" style="'
        "position:fixed;top:12px;right:12px;background:rgba(26,26,46,0.92);"
        "border:1px solid #444;border-radius:8px;padding:14px 18px;"
        "color:white;font-family:sans-serif;font-size:13px;z-index:9999;"
        'box-shadow:0 2px 12px rgba(0,0,0,0.4)">'
        "<div style=\"font-weight:bold;margin-bottom:8px;font-size:14px\">"
        "DeepTrace Network</div>"
        f"{legend_items}</div>"
    )

    path = Path(html_path)
    content = path.read_text()
    content = content.replace("</body>", f"{legend_html}</body>")
    path.write_text(content)


@app.command()
def inspect(
    case: Annotated[str, typer.Option(help="Case slug")] = "",
    focus: Annotated[
        str | None,
        typer.Option(help="Node ID to inspect (e.g. evidence:3)"),
    ] = None,
) -> None:
    """Inspect nodes interactively in the terminal."""
    _check_networkx()
    import networkx as nx

    db = _open_case_db(case)
    try:
        G = _build_graph(db)

        if G.number_of_nodes() == 0:
            console.print("[dim]No data in case to inspect.[/]")
            return

        if focus:
            _inspect_node(G, focus, case)
        else:
            _inspect_overview(G, nx, case)
    finally:
        db.close()


def _inspect_node(G, node_id: str, case: str) -> None:
    """Show detailed info for a single node and its neighbors."""
    if node_id not in G:
        err_console.print(f"[bold red]Error:[/] Node '{node_id}' not found.")
        raise typer.Exit(1)

    data = G.nodes[node_id]
    ntype = data.get("node_type", "?")
    style = RICH_NODE_STYLES.get(ntype, "white")

    # Build detail lines
    details = Text()
    details.append("Type: ", style="dim")
    details.append(f"{ntype}\n", style=style)
    details.append("Label: ", style="dim")
    details.append(f"{data.get('label', '?')}\n")
    details.append("Connections: ", style="dim")
    details.append(f"{G.degree(node_id)}\n")

    for key in ("entity_type", "evidence_type", "status", "tier",
                "priority", "confidence", "timestamp", "source_type"):
        if data.get(key):
            display_key = key.replace("_", " ").title()
            details.append(f"{display_key}: ", style="dim")
            details.append(f"{data[key]}\n")

    console.print(Panel(
        details,
        title=f"[{style}]{node_id}[/]",
        border_style="cyan",
    ))

    # Neighbors
    neighbors = list(G.neighbors(node_id))
    if not neighbors:
        console.print("[dim]No connections to other nodes.[/]")
        return

    table = Table(
        title=f"Connections ({len(neighbors)})",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Node", style="cyan", width=20)
    table.add_column("Type", width=14)
    table.add_column("Label", style="white")
    table.add_column("Via", style="green", width=14)

    for neighbor in sorted(neighbors):
        ndata = G.nodes[neighbor]
        edata = G.edges[node_id, neighbor]
        n_ntype = ndata.get("node_type", "?")
        n_style = RICH_NODE_STYLES.get(n_ntype, "white")

        table.add_row(
            neighbor,
            Text(n_ntype, style=n_style),
            _truncate(ndata.get("label", ""), 40),
            edata.get("edge_type", "?"),
        )

    console.print(table)

    # Navigation hints
    console.print(
        "\n[dim]Drill deeper:[/]"
    )
    for neighbor in sorted(neighbors)[:5]:
        console.print(
            f"  [dim]deeptrace network inspect"
            f" --case {case} --focus {neighbor}[/]"
        )
    if len(neighbors) > 5:
        console.print(f"  [dim]... and {len(neighbors) - 5} more[/]")


def _inspect_overview(G, nx, case: str) -> None:
    """Show a high-level overview of the case network."""
    # Header stats
    n_components = nx.number_connected_components(G)
    console.print(Panel(
        f"[bold]{G.number_of_nodes()}[/] nodes  |  "
        f"[bold]{G.number_of_edges()}[/] edges  |  "
        f"[bold]{n_components}[/] clusters",
        title="[bold cyan]Network Overview[/]",
        border_style="cyan",
    ))

    # Node counts by type with color coding
    type_counts: dict[str, int] = {}
    for _, data in G.nodes(data=True):
        t = data.get("node_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    type_table = Table(
        title="Nodes by Type",
        show_header=True,
        header_style="bold cyan",
    )
    type_table.add_column("Type", width=16)
    type_table.add_column("Count", justify="right", width=8)
    type_table.add_column("", width=30)

    for ntype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        style = RICH_NODE_STYLES.get(ntype, "white")
        bar = "#" * min(count, 30)
        type_table.add_row(
            Text(ntype, style=style),
            str(count),
            Text(bar, style=style),
        )
    console.print(type_table)

    # Top connected nodes
    ranked = sorted(G.nodes(data=True), key=lambda x: G.degree(x[0]), reverse=True)
    connected = [(n, d) for n, d in ranked if G.degree(n) > 0]

    if connected:
        top_table = Table(
            title="Most Connected (top 10)",
            show_header=True,
            header_style="bold cyan",
        )
        top_table.add_column("Node", style="cyan", width=20)
        top_table.add_column("Type", width=14)
        top_table.add_column("Edges", justify="right", width=8)
        top_table.add_column("Label", style="white")

        for node_id, data in connected[:10]:
            ntype = data.get("node_type", "?")
            style = RICH_NODE_STYLES.get(ntype, "white")
            top_table.add_row(
                node_id,
                Text(ntype, style=style),
                str(G.degree(node_id)),
                _truncate(data.get("label", ""), 40),
            )
        console.print(top_table)

    # Isolated nodes grouped by type
    isolated = list(nx.isolates(G))
    if isolated:
        iso_by_type: dict[str, list[str]] = {}
        for node_id in isolated:
            data = G.nodes[node_id]
            ntype = data.get("node_type", "unknown")
            iso_by_type.setdefault(ntype, []).append(
                data.get("label", node_id)
            )

        lines = []
        for ntype, labels in sorted(iso_by_type.items()):
            style = RICH_NODE_STYLES.get(ntype, "white")
            lines.append(f"[{style}]{ntype}[/] ({len(labels)}):")
            for label in labels[:5]:
                lines.append(f"  {_truncate(label, 50)}")
            if len(labels) > 5:
                lines.append(f"  [dim]... and {len(labels) - 5} more[/]")

        console.print(Panel(
            "\n".join(lines),
            title=f"[bold yellow]Isolated Nodes ({len(isolated)})[/]",
            border_style="yellow",
        ))

    # Navigation hints
    console.print("\n[dim]Inspect a node:[/]")
    if connected:
        top_id = connected[0][0]
        console.print(
            f"  [dim]deeptrace network inspect"
            f" --case {case} --focus {top_id}[/]"
        )
    console.print(
        f"  [dim]deeptrace network visualize"
        f" --case {case}[/]"
    )
