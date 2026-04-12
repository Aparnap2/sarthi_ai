"""Insight Builder — prepares DSPy inputs for GuardianInsight."""
from __future__ import annotations
from typing import Any
from src.guardian.watchlist import SeedStageBlindspot


class InsightBuilder:
    """Builds structured DSPy inputs from a matched blindspot + signals."""

    def build(
        self,
        blindspot: SeedStageBlindspot,
        signals: dict[str, Any],
        context: str = "",
        metric_value: str = "",
        implied_at_scale: str = "",
    ) -> dict[str, str]:
        """Return kwargs for GuardianInsight DSPy call."""
        return {
            "context": context or "No prior context available.",
            "blindspot_name": blindspot.name,
            "why_it_matters": blindspot.why_it_matters,
            "what_founder_doesnt_know": blindspot.what_founder_doesnt_know,
            "urgency_horizon": blindspot.urgency_horizon,
            "historical_precedent": blindspot.historical_precedent,
            "one_action": blindspot.one_action,
            "current_metric": metric_value or "Data unavailable.",
            "implied_at_scale": implied_at_scale or "Scale impact unknown.",
        }

    def format_metric_value(
        self, blindspot: SeedStageBlindspot, signals: dict
    ) -> str:
        """Extract the key metric value for the current detection."""
        formatters = {
            "FG-01": lambda s: f"Monthly churn: {s.get('monthly_churn_pct',0)*100:.1f}%",
            "FG-02": lambda s: f"Burn multiple: {s.get('net_burn',0)/max(s.get('net_new_arr',1),1):.1f}x",
            "FG-03": lambda s: f"Top customer: {s.get('top_customer_mrr',0)/max(s.get('total_mrr',1),1)*100:.0f}% of MRR",
            "FG-04": lambda s: f"Burn growth: {s.get('burn_rate',0)/max(s.get('prev_burn_rate',1),1)*100:.0f}% of prior, runway: {s.get('runway_days',0)}d",
            "FG-05": lambda s: f"Failed payments: {s.get('failed_payments_7d',0)} in 7 days",
            "FG-06": lambda s: f"Payroll/MRR ratio: {s.get('payroll_monthly',0)/max(s.get('mrr',1),1)*100:.0f}%",
            "BG-01": lambda s: f"Activation rate: {s.get('activation_rate',0)*100:.0f}% with {s.get('new_signups',0)} new signups",
            "BG-02": lambda s: f"Top 10% generate {s.get('top_10pct_mrr',0)/max(s.get('total_mrr',1),1)*100:.0f}% of MRR",
            "BG-03": lambda s: f"{blindspot.name}: adoption dropped to {s.get('adoption_post_deploy',0)/max(s.get('adoption_pre_deploy',1),1)*100:.0f}% of pre-deploy",
            "BG-04": lambda s: f"Cohort retention: {s.get('cohort_retention_30d_recent',0)*100:.0f}% vs prior {s.get('cohort_retention_30d_prior',0)*100:.0f}%",
            "BG-05": lambda s: f"NRR: {s.get('nrr',100):.0f}%",
            "BG-06": lambda s: f"Trial wall detected at {s.get('trial_step_dropoffs',[])}",
            "OG-01": lambda s: f"Error rate in segment: {max(seg['error_pct'] for seg in s.get('errors_by_segment',[{'error_pct':0}]))*100:.0f}%",
            "OG-02": lambda s: f"Support growth {s.get('support_tickets_growth_pct',0):.0f}% vs user growth {s.get('user_growth_pct',0):.0f}%",
            "OG-03": lambda s: f"Bug reported across {sum(1 for v in s.get('bug_mentions_by_channel',{}).values() if v>0)} channels",
            "OG-04": lambda s: f"Deploys: {s.get('deploys_this_month',0)} this month vs {s.get('deploys_last_month',0)} last",
            "OG-05": lambda s: f"AWS growth {s.get('aws_cost_growth_pct',0):.0f}% vs user growth {s.get('user_growth_pct',0):.0f}%",
        }
        try:
            return formatters.get(blindspot.id, lambda s: "Metric unavailable")(signals)
        except Exception:
            return "Metric value unavailable."
