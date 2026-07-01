"""Valuation pipeline orchestration with LangGraph."""

import logging

from src.agents.analysts.fundamentals import FundamentalsAnalyst
from src.agents.analysts.industry_analyst import IndustryAnalyst
from src.agents.analysts.sentiment import SentimentAnalyst
from src.agents.analysts.valuation_analyst import ValuationAnalyst
from src.agents.debate.engine import DebateEngine
from src.agents.final.estimator import FinalEstimator
from src.agents.llm.router import LLMRouter
from src.agents.masters.base import CompanyAnalysisData, MasterAgent
from src.agents.masters.buffett import BuffettAgent
from src.agents.masters.damodaran import DamodaranAgent
from src.agents.masters.fisher import FisherAgent
from src.agents.masters.graham import GrahamAgent
from src.agents.masters.munger import MungerAgent
from src.agents.risk.falsifier import RiskAssessment, RiskFalsifier
from src.graph.state import RunConfig, ValuationState
from src.schemas import DebateResult, MasterSignal, Signal

logger = logging.getLogger(__name__)


class ValuationPipeline:
    """Orchestrates the L1-L5 valuation pipeline."""

    def __init__(self, llm_router: LLMRouter | None = None, run_config: RunConfig | None = None):
        self._llm = llm_router
        self._run_config = run_config or RunConfig()
        # L1 Analysts
        self._fundamentals = FundamentalsAnalyst()
        self._valuation = ValuationAnalyst()
        self._sentiment = SentimentAnalyst()
        self._industry = IndustryAnalyst()
        # L2 Masters
        self._masters: list[MasterAgent] = [
            BuffettAgent(llm_router=llm_router),
            GrahamAgent(llm_router=llm_router),
            DamodaranAgent(llm_router=llm_router),
            MungerAgent(llm_router=llm_router),
            FisherAgent(llm_router=llm_router),
        ]
        # L3 Debate
        self._debate = DebateEngine(
            llm_router=llm_router, max_rounds=self._run_config.debate_rounds
        )
        # L4 Risk
        self._risk = RiskFalsifier(llm_router=llm_router)
        # L5 Final
        self._final = FinalEstimator(llm_router=llm_router)

    def run(self, state: ValuationState, config: RunConfig | None = None) -> ValuationState:
        """Run the full L1-L5 pipeline through a compiled LangGraph."""
        active_config = config or self._run_config
        graph = self.build_graph(active_config)
        runnable_config = {"configurable": {"thread_id": active_config.thread_id}}
        return graph.invoke(state, runnable_config)

    def resume(self, thread_id: str, feedback: str) -> ValuationState:
        """Resume a human-review interrupt with user feedback."""
        from langgraph.types import Command

        graph = self.build_graph(self._run_config)
        runnable_config = {"configurable": {"thread_id": thread_id}}
        return graph.invoke(Command(resume=feedback), runnable_config)

    def build_graph(self, config: RunConfig | None = None):
        """Build and compile the LangGraph StateGraph."""
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import END, START, StateGraph

        active_config = config or self._run_config
        graph = StateGraph(ValuationState)
        graph.add_node("l1_analysts", self._run_l1_analysts)
        graph.add_node("l2_masters", self._run_l2_masters)
        graph.add_node("l3_debate", self._run_l3_debate)
        graph.add_node("l4_risk", self._run_l4_risk)
        graph.add_node("l5_final", self._run_l5_final)
        graph.add_node("human_review", self._human_review)

        graph.add_edge(START, "l1_analysts")
        graph.add_edge("l1_analysts", "l2_masters")
        graph.add_edge("l2_masters", "l3_debate")
        graph.add_edge("l3_debate", "l4_risk")
        graph.add_edge("l4_risk", "l5_final")
        if active_config.require_human_approval:
            graph.add_edge("l5_final", "human_review")
            graph.add_edge("human_review", END)
        else:
            graph.add_edge("l5_final", END)
        return graph.compile(checkpointer=InMemorySaver())

    def run_sequential(self, state: ValuationState) -> ValuationState:
        """Run the full L1-L5 pipeline without LangGraph, useful for tests."""
        logger.info(f"Starting pipeline for {state.get('ticker', 'unknown')}")

        try:
            state = self._run_l1_analysts(state)
            state = self._run_l2_masters(state)
            state = self._run_l3_debate(state)
            state = self._run_l4_risk(state)
            state = self._run_l5_final(state)
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            state["error"] = str(e)

        return state

    def _human_review(self, state: ValuationState) -> ValuationState:
        """Pause for human approval after final report generation."""
        if state.get("human_approved"):
            return state
        try:
            from langgraph.types import interrupt
        except ImportError:
            state["human_approved"] = False
            return state
        feedback = interrupt(
            {
                "instruction": "Review final valuation report",
                "final_report": state.get("final_report", {}),
            }
        )
        state["user_feedback"] = str(feedback)
        state["human_approved"] = True
        return state

    def _run_l1_analysts(self, state: ValuationState) -> ValuationState:
        """Run L1 analyst layer: fundamentals, valuation, sentiment, industry."""
        logger.info("Running L1 Analysts...")
        from src.schemas import FinancialStatements, DCFAssumptions
        from src.valuation.dcf import DCFCalculator
        from src.valuation.monte_carlo import MonteCarloValuation

        financials = []
        for f_dict in state.get("financial_data", []):
            try:
                financials.append(FinancialStatements(**f_dict))
            except Exception:
                pass

        state["fundamentals_report"] = self._fundamentals.analyze(
            financials, state.get("industry_metrics", {})
        )
        state["valuation_report_data"] = self._valuation.analyze(financials)
        state["sentiment_report"] = self._sentiment.analyze()
        state["industry_report"] = self._industry.analyze(
            state.get("ticker", ""),
            state.get("industry", ""),
            state.get("competitors", []),
        )

        # Calculate valuation numbers to pass to L5
        state["pe_quantile"] = None
        state["dcf_value"] = None
        state["monte_carlo_percentiles"] = None

        if financials:
            # Prefer annual report (period month == 12); fall back to latest
            annual = next((f for f in financials if f.period.month == 12), financials[0])
            try:
                ocf_raw = float(annual.operating_cashflow) if annual.operating_cashflow else 0.0
                # Convert raw yuan → 亿元 for human-readable output
                # AKShare returns values in yuan; normalise to 亿 (1e8)
                OCF_UNIT = 1e8
                ocf = ocf_raw / OCF_UNIT if abs(ocf_raw) > OCF_UNIT else ocf_raw

                if ocf > 0:
                    assumptions = DCFAssumptions(
                        growth_rate=0.08,
                        terminal_growth_rate=0.03,
                        wacc=0.09,
                        projection_years=5,
                    )
                    dcf_result = DCFCalculator().calculate([ocf], assumptions)
                    state["dcf_value"] = float(dcf_result.intrinsic_value)

                    mc_result = MonteCarloValuation(n_simulations=1000).simulate(
                        base_fcf=ocf,
                        growth_rate_mean=0.08,
                        growth_rate_std=0.03,
                        wacc_mean=0.09,
                        wacc_std=0.01,
                    )
                    state["monte_carlo_percentiles"] = mc_result.percentiles
                    logger.info(
                        f"DCF={state['dcf_value']:.1f}亿, "
                        f"MC p50={mc_result.percentiles.get('p50', 0):.1f}亿  "
                        f"(OCF base={ocf:.1f}亿, period={annual.period})"
                    )
            except Exception as e:
                logger.warning(f"Valuation calc failed: {e}")

        return state

    def _run_l2_masters(self, state: ValuationState) -> ValuationState:
        """Run L2 master layer: investment philosophy agents."""
        logger.info("Running L2 Masters...")
        from src.schemas import FinancialStatements

        financials = []
        for f_dict in state.get("financial_data", []):
            try:
                financials.append(FinancialStatements(**f_dict))
            except Exception:
                pass

        analysis_data = CompanyAnalysisData(
            ticker=state.get("ticker", ""),
            name=state.get("company", {}).get("name", state.get("ticker", "")),
            industry=state.get("industry", ""),
            financials=financials,
            industry_metrics=state.get("industry_metrics", {}),
            competitor_data=state.get("competitor_comparison", {}),
        )

        signals = []
        for master in self._masters:
            try:
                signal = master.analyze(analysis_data)
                signals.append(signal.model_dump())
            except Exception as e:
                logger.warning(f"Master {master.name} failed: {e}")
                signals.append(
                    MasterSignal(
                        signal=Signal.NEUTRAL,
                        confidence=0,
                        reasoning=f"{master.name} unavailable",
                    ).model_dump()
                )

        state["master_signals"] = signals
        return state

    def _run_l3_debate(self, state: ValuationState) -> ValuationState:
        """Run L3 debate layer: bull vs bear argumentation."""
        logger.info("Running L3 Debate...")
        signals = [MasterSignal(**s) for s in state.get("master_signals", [])]

        bull_evidence = [s.reasoning for s in signals if s.signal == Signal.BULLISH]
        bear_evidence = [s.reasoning for s in signals if s.signal == Signal.BEARISH]

        if not bull_evidence:
            bull_evidence = ["No strong bullish signals from masters."]
        if not bear_evidence:
            bear_evidence = ["No strong bearish signals from masters."]

        result = self._debate.run_debate(
            company_name=state.get("company", {}).get("name", ""),
            ticker=state.get("ticker", ""),
            industry=state.get("industry", ""),
            bull_evidence=bull_evidence,
            bear_evidence=bear_evidence,
        )
        state["debate_result"] = result.model_dump()
        return state

    def _run_l4_risk(self, state: ValuationState) -> ValuationState:
        """Run L4 risk layer: adversarial falsification."""
        logger.info("Running L4 Risk...")
        debate = DebateResult(**state.get("debate_result", {}))
        signals = [MasterSignal(**s) for s in state.get("master_signals", [])]

        assessment = self._risk.assess(
            ticker=state.get("ticker", ""),
            company_name=state.get("company", {}).get("name", ""),
            industry=state.get("industry", ""),
            debate_conclusion=debate.final_stance,
            debate_confidence=debate.confidence,
            bull_arguments=[s.reasoning for s in signals if s.signal == Signal.BULLISH],
            bear_arguments=[s.reasoning for s in signals if s.signal == Signal.BEARISH],
        )
        state["risk_assessment"] = {
            "risk_level": assessment.risk_level,
            "risks": assessment.risks,
            "falsification_result": assessment.falsification_result,
            "confidence_adjustment": assessment.confidence_adjustment,
        }
        return state

    def _run_l5_final(self, state: ValuationState) -> ValuationState:
        """Run L5 final layer: synthesis and report generation."""
        logger.info("Running L5 Final Estimation...")

        signals = [MasterSignal(**s) for s in state.get("master_signals", [])]
        debate = DebateResult(**state.get("debate_result", {}))
        risk_data = state.get("risk_assessment", {})
        risk = RiskAssessment(
            risk_level=risk_data.get("risk_level", "medium"),
            risks=risk_data.get("risks", []),
            falsification_result=risk_data.get("falsification_result", ""),
            confidence_adjustment=risk_data.get("confidence_adjustment", 0),
        )

        report = self._final.estimate(
            ticker=state.get("ticker", ""),
            company_name=state.get("company", {}).get("name", state.get("ticker", "")),
            industry=state.get("industry", ""),
            master_signals=signals,
            debate_result=debate,
            risk_assessment=risk,
            pe_quantile=state.get("pe_quantile"),
            dcf_value=state.get("dcf_value"),
            monte_carlo_percentiles=state.get("monte_carlo_percentiles"),
            competitor_comparison=state.get("competitor_comparison", {}),
        )
        state["final_report"] = report.model_dump(mode="json")
        state["human_approved"] = False
        return state
