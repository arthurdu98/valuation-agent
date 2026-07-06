from datetime import date

import pandas as pd

from src.backend.schemas import DCFAssumptions
from src.backend.valuation.dcf import DCFCalculator
from src.backend.valuation.dupont import DuPontAnalyzer
from src.backend.valuation.graham import GrahamCalculator
from src.backend.valuation.monte_carlo import MonteCarloValuation
from src.backend.valuation.pe_band import PEBandCalculator


def test_pe_band_quantiles():
    series = pd.Series(
        range(1, 101),
        index=pd.date_range("2020-01-01", periods=100, freq="W"),
    )
    result = PEBandCalculator().calculate(series, current_pe=50, years=10)
    assert result.quantiles["p50"] == 50.5
    assert 0.45 <= result.current_quantile_position <= 0.55


def test_dcf_and_sensitivity_matrix():
    assumptions = DCFAssumptions(
        growth_rate=0.05,
        terminal_growth_rate=0.02,
        wacc=0.1,
        projection_years=5,
    )
    result = DCFCalculator().calculate([100], assumptions)
    assert result.intrinsic_value > 0
    assert len(result.sensitivity_matrix) == 5


def test_dupont_and_graham():
    dupont = DuPontAnalyzer().analyze(
        revenue=1000, net_profit=200, total_assets=2000, total_liabilities=500
    )
    assert round(dupont.roe, 4) == round(200 / 1500, 4)

    graham = GrahamCalculator()
    number = graham.graham_number(eps=10, bvps=50)
    assert number > 0
    assert graham.safety_margin(current_price=80, intrinsic_value=100) == 0.2


def test_monte_carlo_percentiles():
    result = MonteCarloValuation(n_simulations=100, seed=1).simulate(
        base_fcf=100,
        growth_rate_mean=0.05,
        growth_rate_std=0.01,
        wacc_mean=0.1,
        wacc_std=0.01,
    )
    assert result.simulations > 0
    assert {"p10", "p25", "p50", "p75", "p90"}.issubset(result.percentiles)
