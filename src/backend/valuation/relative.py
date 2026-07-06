from dataclasses import dataclass, field


@dataclass
class RelativeValResult:
    """Result of relative valuation comparison."""
    target_ticker: str
    peers: list[str]
    metrics: dict[str, dict[str, float]]  # {metric_name: {ticker: value}}
    premiums: dict[str, float] = field(default_factory=dict)  # {metric: premium_pct vs peer avg}
    rankings: dict[str, int] = field(default_factory=dict)    # {metric: rank (1=best/cheapest)}


class RelativeValuation:
    """Compare target company valuation multiples against peers."""

    VALUATION_METRICS = ["pe", "pb", "ps", "ev_ebitda"]

    def compare(
        self,
        target_ticker: str,
        target_metrics: dict[str, float],
        peer_metrics: dict[str, dict[str, float]],
    ) -> RelativeValResult:
        """Compare target metrics against peers.

        Args:
            target_ticker: The company being valued.
            target_metrics: {metric_name: value} for target (e.g., {"pe": 25, "pb": 8}).
            peer_metrics: {ticker: {metric_name: value}} for each peer.

        Returns:
            RelativeValResult with premiums and rankings.
        """
        peers = list(peer_metrics.keys())
        all_metrics = {}  # {metric: {ticker: value}}
        premiums = {}
        rankings = {}

        for metric in self.VALUATION_METRICS:
            if metric not in target_metrics:
                continue

            target_val = target_metrics[metric]
            peer_vals = {t: m.get(metric) for t, m in peer_metrics.items() if m.get(metric) is not None}

            if not peer_vals:
                continue

            # Build full comparison dict
            all_metrics[metric] = {target_ticker: target_val, **peer_vals}

            # Calculate premium vs peer average
            peer_avg = sum(peer_vals.values()) / len(peer_vals)
            if peer_avg > 0:
                premiums[metric] = (target_val - peer_avg) / peer_avg
            else:
                premiums[metric] = 0.0

            # Calculate ranking (1 = lowest/cheapest for valuation multiples)
            all_vals = [(target_ticker, target_val)] + list(peer_vals.items())
            sorted_vals = sorted(all_vals, key=lambda x: x[1])
            for rank, (ticker, _) in enumerate(sorted_vals, 1):
                if ticker == target_ticker:
                    rankings[metric] = rank
                    break

        return RelativeValResult(
            target_ticker=target_ticker,
            peers=peers,
            metrics=all_metrics,
            premiums=premiums,
            rankings=rankings,
        )

    def valuation_summary(self, result: RelativeValResult) -> str:
        """Generate a human-readable valuation summary."""
        lines = [f"Relative Valuation: {result.target_ticker} vs {', '.join(result.peers)}"]
        lines.append("-" * 60)
        for metric, premium in result.premiums.items():
            rank = result.rankings.get(metric, 0)
            total = len(result.peers) + 1
            direction = "premium" if premium > 0 else "discount"
            lines.append(f"  {metric.upper()}: {abs(premium):.1%} {direction} vs peers (rank {rank}/{total})")
        return "\n".join(lines)
