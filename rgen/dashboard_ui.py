"""
Dashboard UI — Real-time routing metrics visualization.

Uses Rich library to render terminal UI with:
- Top panel: routing summary (scenarios, keywords, status)
- Middle panel: scenario usage table (frequency, trend, confidence)
- Bottom panel: footer with hotkeys and refresh timestamp

Entry point: DashboardUI.run()
"""

from __future__ import annotations

import sys
from datetime import datetime
from threading import Thread, Event
from time import sleep

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from rgen.metrics_collector import RouterMetricsCollector


class DashboardUI:
    """
    Terminal UI for router metrics using Rich library.

    Displays real-time metrics from RouterMetricsCollector:
    - Confidence trend
    - Scenario usage distribution
    - Agent overlap detection
    - Dead zones identification
    - Error rate
    """

    def __init__(
        self,
        metrics_collector: RouterMetricsCollector,
        refresh_interval: float = 1.0,
        is_tty: bool | None = None,
    ):
        """
        Initialize dashboard UI.

        Args:
            metrics_collector: RouterMetricsCollector instance
            refresh_interval: seconds between refresh cycles (default 1.0)
            is_tty: override TTY detection (for testing)
        """
        self.metrics = metrics_collector
        self.refresh_interval = refresh_interval
        self.console = Console()
        self.running = False
        self._stop_event = Event()

        # TTY detection
        if is_tty is not None:
            self._is_tty = is_tty
        else:
            self._is_tty = sys.stdout.isatty()

    def _build_layout(self, snapshot: dict) -> Layout:
        """
        Build the complete dashboard layout.

        Args:
            snapshot: output from metrics_collector.full_snapshot()

        Returns:
            Rich Layout with 3 sections: top, middle, bottom
        """
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )

        # Header: routing summary
        layout["header"].update(self._render_header(snapshot))

        # Body: main metrics table
        layout["body"].update(self._render_body(snapshot))

        # Footer: hotkeys and timestamp
        layout["footer"].update(self._render_footer(snapshot))

        return layout

    def _render_header(self, snapshot: dict) -> Panel:
        """
        Render top panel: routing summary and status.

        Shows:
        - Scenario count, keyword count, overlap %
        - Router overall status (OK/WARN/ERROR)
        - Dead zone count (if > 0)
        """
        confidence_data = snapshot.get("confidence", {})
        scenario_data = snapshot.get("scenario_usage", {})
        dead_zones = snapshot.get("dead_zones", {})
        error_rate = snapshot.get("error_rate", {})

        # Styling
        status_icon = "✅"
        status_text = "OK"
        status_color = "green"

        # Determine status from metrics
        if dead_zones.get("dead_zone_count", 0) > 0:
            status_icon = "⚠️"
            status_text = "WARN"
            status_color = "yellow"

        if error_rate.get("error_rate", 0) > 0.3:
            status_icon = "❌"
            status_text = "ERROR"
            status_color = "red"

        metrics_text = Text()
        metrics_text.append("Routing: ", style="bold cyan")
        metrics_text.append(f"{scenario_data.get('total_unique', 0)} scenarios", style="cyan")
        metrics_text.append(" | ", style="dim")
        metrics_text.append(f"Confidence: {confidence_data.get('mean', 0)}", style="cyan")
        metrics_text.append(" | ", style="dim")
        metrics_text.append(f"Success rate: {error_rate.get('success_rate', 0) * 100:.0f}%", style="cyan")
        metrics_text.append("\n")
        metrics_text.append(f"{status_icon} Status: ", style=f"bold {status_color}")
        metrics_text.append(status_text, style=status_color)

        if dead_zones.get("dead_zone_count", 0) > 0:
            metrics_text.append(
                f" | Dead zones: {dead_zones['dead_zone_count']}",
                style="yellow",
            )

        return Panel(metrics_text, title="[bold cyan]Router Dashboard[/bold cyan]", border_style="cyan")

    def _render_body(self, snapshot: dict) -> Panel:
        """
        Render middle panel: scenario usage table.

        Shows top scenarios with:
        - Usage count
        - Trend (improving/stable/degrading)
        - Average confidence
        """
        scenario_data = snapshot.get("scenario_usage", {})
        confidence_data = snapshot.get("confidence", {})

        table = Table(title="[bold]Scenario Usage[/bold]", show_header=True, header_style="bold magenta")
        table.add_column("Scenario", style="cyan")
        table.add_column("Count", justify="right", style="green")
        table.add_column("Confidence", justify="right", style="yellow")
        table.add_column("Trend", justify="center")

        top_scenarios = scenario_data.get("top_scenarios", [])
        mean_confidence = confidence_data.get("mean", 0.75)
        trend_indicator = confidence_data.get("trend", "stable")

        # Trend emoji
        trend_emoji = {"improving": "📈", "degrading": "📉", "stable": "➡️", "unknown": "❓"}

        for scenario_info in top_scenarios[:10]:  # Show top 10
            scenario_name = scenario_info.get("scenario", "unknown")[:30]  # truncate
            count = scenario_info.get("count", 0)

            # Color confidence by score
            conf_score = mean_confidence
            if conf_score >= 0.8:
                conf_color = "green"
                conf_indicator = "✓"
            elif conf_score >= 0.6:
                conf_color = "yellow"
                conf_indicator = "⚠"
            else:
                conf_color = "red"
                conf_indicator = "✗"

            table.add_row(
                scenario_name,
                str(count),
                f"[{conf_color}]{conf_score:.2f} {conf_indicator}[/{conf_color}]",
                trend_emoji.get(trend_indicator, "?"),
            )

        # Add dead zones if any
        dead_zones = snapshot.get("dead_zones", {})
        if dead_zones.get("dead_zone_count", 0) > 0:
            table.add_row(
                "[bold red][unknown?][/bold red]",
                str(dead_zones["dead_zone_count"]),
                "[red]0.15 ✗[/red]",
                "📉",
            )

        return Panel(table, border_style="magenta", padding=(1, 1))

    def _render_footer(self, snapshot: dict) -> Panel:
        """
        Render bottom panel: footer with hotkeys and timestamp.

        Shows:
        - Last refresh time
        - Hotkey hints
        """
        timestamp = snapshot.get("timestamp", datetime.now().isoformat())
        footer_text = Text()
        footer_text.append("Last refresh: ", style="dim")
        footer_text.append(timestamp[-19:-1], style="cyan")  # HH:MM:SS format
        footer_text.append(" | ", style="dim")
        footer_text.append("[r]", style="bold yellow")
        footer_text.append("efresh ", style="dim")
        footer_text.append("[e]", style="bold yellow")
        footer_text.append("xport ", style="dim")
        footer_text.append("[q]", style="bold yellow")
        footer_text.append("uit", style="dim")

        return Panel(footer_text, border_style="blue", padding=(0, 1))

    def render(self, snapshot: dict | None = None) -> Layout:
        """
        Render the dashboard layout with current metrics.

        Args:
            snapshot: metrics snapshot (auto-fetched if None)

        Returns:
            Rich Layout object
        """
        if snapshot is None:
            snapshot = self.metrics.full_snapshot()

        return self._build_layout(snapshot)

    def run(self, max_iterations: int | None = None):
        """
        Run the interactive dashboard loop.

        Displays live-updating metrics. Press 'q' to quit.

        Args:
            max_iterations: limit iterations (for testing), None = infinite
        """
        if not self._is_tty:
            # Fallback: just print stats once and exit
            snapshot = self.metrics.full_snapshot()
            self.console.print(self.render(snapshot))
            return

        self.running = True
        iteration = 0

        try:
            with Live(self.render(), console=self.console, refresh_per_second=1) as live:
                while self.running:
                    if max_iterations and iteration >= max_iterations:
                        break

                    # Update display
                    snapshot = self.metrics.full_snapshot()
                    live.update(self.render(snapshot))

                    # Check for quit signal
                    if self._stop_event.is_set():
                        break

                    # Wait for refresh interval
                    sleep(self.refresh_interval)
                    iteration += 1

        except KeyboardInterrupt:
            self.console.print("\n[dim]Dashboard stopped[/dim]")
        finally:
            self.running = False

    def stop(self):
        """Signal the dashboard to stop running."""
        self._stop_event.set()

    def export_snapshot(self, filepath: str):
        """
        Export current metrics snapshot to JSON file.

        Args:
            filepath: path to write JSON
        """
        import json

        snapshot = self.metrics.full_snapshot()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)


# ─── CLI Entry Point ───


def main():
    """CLI entry point for standalone dashboard."""
    from rgen.metrics_collector import RouterMetricsCollector

    try:
        collector = RouterMetricsCollector()
        ui = DashboardUI(collector)
        ui.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
