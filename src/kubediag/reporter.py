from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import List
from .models import Incident

console = Console()

def report_incidents(incidents: List[Incident]):
    if not incidents:
        console.print("[green]No incidents found! Cluster looks healthy.[/green]")
        return

    console.print(f"[bold red]Found {len(incidents)} incident(s):[/bold red]\n")
    
    for inc in incidents:
        color = "red" if inc.severity == "High" else "yellow"
        
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value")
        
        ev = inc.evidence
        table.add_row("Namespace", ev.namespace)
        table.add_row("Resource", f"{ev.kind}/{ev.name}")
        if ev.container_name:
            table.add_row("Container", ev.container_name)
        if ev.phase:
            table.add_row("Phase", ev.phase)
        if ev.state:
            table.add_row("State", ev.state)
        if ev.restart_count is not None:
            table.add_row("Restarts", str(ev.restart_count))
        if ev.exit_code is not None:
            table.add_row("Exit Code", str(ev.exit_code))
        if ev.termination_reason:
            table.add_row("Term Reason", ev.termination_reason)
        if ev.requests or ev.limits:
            table.add_row("Resources", f"Req: {ev.requests}, Lim: {ev.limits}")
            
        if ev.events:
            event_strs = [f"- {e.get('reason')}: {e.get('message')}" for e in ev.events[:3]]
            table.add_row("Recent Events", "\n".join(event_strs))
            
        if ev.node_conditions:
            cond_strs = [f"- {c.get('type')}: {c.get('status')} ({c.get('reason')})" for c in ev.node_conditions if c.get("status") != "Unknown"]
            table.add_row("Node Conditions", "\n".join(cond_strs))

        if ev.logs:
            table.add_row("Logs snippet", f"...\n{ev.logs.strip()}")
            
        panel = Panel(table, title=f"[{color}]{inc.type}: {inc.description}[/{color}]", border_style=color)
        console.print(panel)
