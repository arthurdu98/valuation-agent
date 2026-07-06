"""Company CRUD endpoints backed by CompanyManager (in-memory)."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.deps import get_company_manager
from src.api.schemas_api import CompanyCreate, CompetitorsUpdate, DeleteResult
from src.data.company_manager import CompanyManager
from src.schemas import Company

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=list[Company])
def list_companies(
    industry: str | None = Query(default=None),
    market: str | None = Query(default=None),
    cm: CompanyManager = Depends(get_company_manager),
) -> list[Company]:
    companies = cm.get_tracked_companies()
    if industry:
        companies = [c for c in companies if c.industry == industry]
    if market:
        companies = [c for c in companies if c.market.value == market]
    return companies


@router.get("/grouped")
def companies_grouped(
    cm: CompanyManager = Depends(get_company_manager),
) -> dict[str, list[Company]]:
    """Companies grouped by industry — for the home page."""
    grouped: dict[str, list[Company]] = defaultdict(list)
    for c in cm.get_tracked_companies():
        grouped[c.industry].append(c)
    return grouped


@router.get("/{ticker}", response_model=Company)
def get_company(
    ticker: str,
    cm: CompanyManager = Depends(get_company_manager),
) -> Company:
    company = next((c for c in cm.get_tracked_companies() if c.ticker == ticker), None)
    if company is None:
        raise HTTPException(status_code=404, detail=f"未追踪的公司: {ticker}")
    return company


@router.post("", response_model=Company, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    cm: CompanyManager = Depends(get_company_manager),
) -> Company:
    return cm.add_company(
        ticker=payload.ticker,
        name=payload.name,
        market=payload.market.value,
        industry=payload.industry,
        competitors=payload.competitors,
    )


@router.delete("/{ticker}", response_model=DeleteResult)
def delete_company(
    ticker: str,
    cm: CompanyManager = Depends(get_company_manager),
) -> DeleteResult:
    return DeleteResult(success=cm.remove_company(ticker))


@router.patch("/{ticker}/competitors", response_model=Company)
def update_competitors(
    ticker: str,
    payload: CompetitorsUpdate,
    cm: CompanyManager = Depends(get_company_manager),
) -> Company:
    try:
        cm.update_competitors(ticker, payload.competitors)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未追踪的公司: {ticker}")
    return next(c for c in cm.get_tracked_companies() if c.ticker == ticker)
