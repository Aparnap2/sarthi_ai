"""Guardian Watchlist tests — pure Python, zero infra dependencies."""
from src.guardian.watchlist import (
    SEED_STAGE_WATCHLIST,
    FG_01_SILENT_CHURN_DEATH, FG_02_BURN_MULTIPLE_CREEP,
    FG_03_CUSTOMER_CONCENTRATION, FG_04_RUNWAY_COMPRESSION,
    FG_05_FAILED_PAYMENT_CLUSTER, FG_06_PAYROLL_REVENUE_RATIO,
    BG_01_LEAKY_BUCKET, BG_02_POWER_USER_MASKING,
    BG_03_FEATURE_DROP, BG_04_COHORT_RETENTION,
    BG_05_NRR_BELOW_100, BG_06_TRIAL_WALL,
    OG_01_ERROR_SEGMENT, OG_02_SUPPORT_GROWTH,
    OG_03_CROSS_CHANNEL_BUG, OG_04_DEPLOY_COLLAPSE,
    OG_05_INFRA_UNIT_ECON,
)
from src.guardian.detector import GuardianDetector
from src.guardian.insight_builder import InsightBuilder


class TestWatchlistStructure:
    def test_17_patterns_total(self):
        assert len(SEED_STAGE_WATCHLIST) == 17  # 6 finance + 6 bi + 5 ops

    def test_all_have_required_fields(self):
        for item in SEED_STAGE_WATCHLIST:
            assert item.id and isinstance(item.id, str)
            assert item.name and isinstance(item.name, str)
            assert item.domain in ("finance", "bi", "ops")
            assert len(item.signals_required) > 0
            assert item.why_it_matters
            assert item.what_founder_doesnt_know
            assert item.urgency_horizon
            assert item.historical_precedent
            assert item.one_action
            assert item.severity in ("info", "warning", "critical")

    def test_unique_ids(self):
        ids = [item.id for item in SEED_STAGE_WATCHLIST]
        assert len(ids) == len(set(ids))

    def test_domain_counts(self):
        domains = {item.domain for item in SEED_STAGE_WATCHLIST}
        assert domains == {"finance", "bi", "ops"}


class TestFinanceDetections:
    def test_FG01_churn_above_3pct(self):
        assert FG_01_SILENT_CHURN_DEATH.detection_logic(
            {"monthly_churn_pct": 0.04})
        assert not FG_01_SILENT_CHURN_DEATH.detection_logic(
            {"monthly_churn_pct": 0.02})

    def test_FG02_burn_multiple_above_2x(self):
        assert FG_02_BURN_MULTIPLE_CREEP.detection_logic(
            {"net_burn": 50000, "net_new_arr": 20000})
        assert not FG_02_BURN_MULTIPLE_CREEP.detection_logic(
            {"net_burn": 10000, "net_new_arr": 20000})

    def test_FG03_customer_concentration(self):
        assert FG_03_CUSTOMER_CONCENTRATION.detection_logic(
            {"top_customer_mrr": 4000, "total_mrr": 10000})
        assert not FG_03_CUSTOMER_CONCENTRATION.detection_logic(
            {"top_customer_mrr": 2000, "total_mrr": 10000})

    def test_FG04_runway_compression(self):
        assert FG_04_RUNWAY_COMPRESSION.detection_logic(
            {"burn_rate": 60000, "prev_burn_rate": 40000, "runway_days": 200})
        assert not FG_04_RUNWAY_COMPRESSION.detection_logic(
            {"burn_rate": 44000, "prev_burn_rate": 40000, "runway_days": 200})

    def test_FG05_failed_payments(self):
        assert FG_05_FAILED_PAYMENT_CLUSTER.detection_logic(
            {"failed_payments_7d": 5})
        assert not FG_05_FAILED_PAYMENT_CLUSTER.detection_logic(
            {"failed_payments_7d": 1})

    def test_FG06_payroll_ratio(self):
        assert FG_06_PAYROLL_REVENUE_RATIO.detection_logic(
            {"payroll_monthly": 7000, "mrr": 10000})
        assert not FG_06_PAYROLL_REVENUE_RATIO.detection_logic(
            {"payroll_monthly": 4000, "mrr": 10000})


class TestBIDetections:
    def test_BG01_leaky_bucket(self):
        assert BG_01_LEAKY_BUCKET.detection_logic({
            "new_signups": 100, "activation_rate": 0.30, "mrr_growth_pct": 5.0})
        assert not BG_01_LEAKY_BUCKET.detection_logic({
            "new_signups": 100, "activation_rate": 0.50, "mrr_growth_pct": 5.0})

    def test_BG02_power_user_masking(self):
        assert BG_02_POWER_USER_MASKING.detection_logic({
            "top_10pct_mrr": 7000, "total_mrr": 10000,
            "avg_mrr_new_customers": 50, "avg_mrr_all_customers": 100})
        assert not BG_02_POWER_USER_MASKING.detection_logic({
            "top_10pct_mrr": 4000, "total_mrr": 10000,
            "avg_mrr_new_customers": 90, "avg_mrr_all_customers": 100})

    def test_BG03_feature_drop(self):
        assert BG_03_FEATURE_DROP.detection_logic({
            "adoption_pre_deploy": 100, "adoption_post_deploy": 50})
        assert not BG_03_FEATURE_DROP.detection_logic({
            "adoption_pre_deploy": 100, "adoption_post_deploy": 80})

    def test_BG04_cohort_retention(self):
        assert BG_04_COHORT_RETENTION.detection_logic({
            "cohort_retention_30d_recent": 0.35, "cohort_retention_30d_prior": 0.50})
        assert not BG_04_COHORT_RETENTION.detection_logic({
            "cohort_retention_30d_recent": 0.48, "cohort_retention_30d_prior": 0.50})

    def test_BG05_nrr_below_100(self):
        assert BG_05_NRR_BELOW_100.detection_logic({"nrr": 95})
        assert not BG_05_NRR_BELOW_100.detection_logic({"nrr": 105})

    def test_BG06_trial_wall(self):
        assert BG_06_TRIAL_WALL.detection_logic({
            "trial_step_dropoffs": [{"drop_pct": 0.60}]})
        assert not BG_06_TRIAL_WALL.detection_logic({
            "trial_step_dropoffs": [{"drop_pct": 0.30}]})


class TestOpsDetections:
    def test_OG01_error_segment(self):
        assert OG_01_ERROR_SEGMENT.detection_logic({
            "errors_by_segment": [{"error_pct": 0.15}]})
        assert not OG_01_ERROR_SEGMENT.detection_logic({
            "errors_by_segment": [{"error_pct": 0.05}]})

    def test_OG02_support_growth(self):
        assert OG_02_SUPPORT_GROWTH.detection_logic({
            "support_tickets_growth_pct": 50, "user_growth_pct": 20})
        assert not OG_02_SUPPORT_GROWTH.detection_logic({
            "support_tickets_growth_pct": 20, "user_growth_pct": 20})

    def test_OG03_cross_channel(self):
        assert OG_03_CROSS_CHANNEL_BUG.detection_logic({
            "bug_mentions_by_channel": {"slack": 3, "email": 2, "twitter": 1}})
        assert not OG_03_CROSS_CHANNEL_BUG.detection_logic({
            "bug_mentions_by_channel": {"slack": 3, "email": 0, "twitter": 0}})

    def test_OG04_deploy_collapse(self):
        assert OG_04_DEPLOY_COLLAPSE.detection_logic({
            "deploys_this_month": 5, "deploys_last_month": 20})
        assert not OG_04_DEPLOY_COLLAPSE.detection_logic({
            "deploys_this_month": 15, "deploys_last_month": 20})

    def test_OG05_infra_divergence(self):
        assert OG_05_INFRA_UNIT_ECON.detection_logic({
            "aws_cost_growth_pct": 40, "user_growth_pct": 10})
        assert not OG_05_INFRA_UNIT_ECON.detection_logic({
            "aws_cost_growth_pct": 15, "user_growth_pct": 10})


class TestHealthyState:
    def test_no_false_positives_on_healthy_signals(self):
        healthy = {
            "monthly_churn_pct": 0.01,
            "net_burn": 5000, "net_new_arr": 15000,
            "top_customer_mrr": 2000, "total_mrr": 10000,
            "burn_rate": 30000, "prev_burn_rate": 29000,
            "runway_days": 365,
            "failed_payments_7d": 0,
            "payroll_monthly": 3000, "mrr": 10000,
            "new_signups": 50, "activation_rate": 0.60,
            "mrr_growth_pct": 8.0,
            "top_10pct_mrr": 3000,
            "avg_mrr_new_customers": 90, "avg_mrr_all_customers": 100,
            "adoption_pre_deploy": 100, "adoption_post_deploy": 95,
            "cohort_retention_30d_recent": 0.50,
            "cohort_retention_30d_prior": 0.48,
            "nrr": 110,
            "trial_step_dropoffs": [{"drop_pct": 0.20}],
            "errors_by_segment": [{"error_pct": 0.02}],
            "support_tickets_growth_pct": 10, "user_growth_pct": 15,
            "bug_mentions_by_channel": {"slack": 0, "email": 0},
            "deploys_this_month": 18, "deploys_last_month": 20,
            "aws_cost_growth_pct": 10, "user_growth_pct": 15,
        }
        detector = GuardianDetector()
        results = detector.run(healthy)
        assert results == [], f"False positives: {[r.id for r in results]}"


class TestDetector:
    def test_returns_matches_on_triggered_signals(self):
        signals = {"monthly_churn_pct": 0.05}
        detector = GuardianDetector()
        results = detector.run(signals)
        assert any(r.id == "FG-01" for r in results)

    def test_run_by_domain_filters(self):
        signals = {"monthly_churn_pct": 0.05}
        detector = GuardianDetector()
        finance = detector.run_by_domain(signals, "finance")
        bi = detector.run_by_domain(signals, "bi")
        assert len(finance) > 0
        assert len(bi) == 0


class TestInsightBuilder:
    def test_build_returns_dict_with_required_keys(self):
        builder = InsightBuilder()
        result = builder.build(FG_01_SILENT_CHURN_DEATH, {})
        for key in ["context", "blindspot_name", "why_it_matters",
                     "what_founder_doesnt_know", "urgency_horizon",
                     "historical_precedent", "one_action",
                     "current_metric", "implied_at_scale"]:
            assert key in result, f"Missing key: {key}"

    def test_format_metric_value_churn(self):
        builder = InsightBuilder()
        val = builder.format_metric_value(
            FG_01_SILENT_CHURN_DEATH, {"monthly_churn_pct": 0.032})
        assert "3.2%" in val

    def test_format_metric_value_burn_multiple(self):
        builder = InsightBuilder()
        val = builder.format_metric_value(
            FG_02_BURN_MULTIPLE_CREEP, {"net_burn": 50000, "net_new_arr": 20000})
        assert "2.5x" in val

    def test_format_metric_value_handles_missing(self):
        builder = InsightBuilder()
        val = builder.format_metric_value(
            FG_01_SILENT_CHURN_DEATH, {})
        assert val  # Should not crash, return fallback string
