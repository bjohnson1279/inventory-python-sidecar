from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/pricing", tags=["pricing"])

class LiquidationRuleInput(BaseModel):
    rule_id: str = Field(..., max_length=255)
    days_to_expiration: int = Field(..., ge=0)
    markdown_percentage: float = Field(..., ge=0.0, le=100.0)
    department: Optional[str] = Field(None, max_length=255)
    sku: Optional[str] = Field(None, max_length=255)

class LotInput(BaseModel):
    variant_id: str = Field(..., max_length=255)
    sku: str = Field(..., max_length=255)
    department: str = Field(..., max_length=255)
    current_price_cents: int = Field(..., ge=0)
    expiration_date: str = Field(..., max_length=255) # ISO format

class MarkdownSuggestion(BaseModel):
    variant_id: str
    rule_id: str
    original_price_cents: int
    suggested_price_cents: int
    reason: str

class OptimizeYieldRequest(BaseModel):
    rules: List[LiquidationRuleInput] = Field(..., max_length=10000)
    lots: List[LotInput] = Field(..., max_length=10000)

@router.post("/optimize-yield", response_model=List[MarkdownSuggestion])
def optimize_yield(req: OptimizeYieldRequest):
    suggestions = []
    now = datetime.now(timezone.utc)
    
    # Optimization: Cache datetime parsing to avoid expensive repeated fromisoformat calls
    expiration_cache = {}

    # Optimization: Pre-sort rules by markdown percentage descending to find the best rule faster
    # with an early exit
    sorted_rules = sorted(req.rules, key=lambda x: x.markdown_percentage, reverse=True)

    # Simple evaluation engine
    for lot in req.lots:
        days_until_exp = expiration_cache.get(lot.expiration_date)
        if days_until_exp is None:
            try:
                exp_dt = datetime.fromisoformat(lot.expiration_date.replace("Z", "+00:00"))
                days_until_exp = (exp_dt - now).days
                expiration_cache[lot.expiration_date] = days_until_exp
            except Exception:
                expiration_cache[lot.expiration_date] = -1 # Cache failed parse as expired to skip
                continue # skip unparseable

        if days_until_exp < 0:
            continue # Already expired, handled by FEFO quarantine
            
        best_rule = None
        
        for rule in sorted_rules:
            # Rule applies if days_to_expiration threshold is met
            if days_until_exp <= rule.days_to_expiration:
                # Check optional filters
                if rule.department and rule.department != lot.department:
                    continue
                if rule.sku and rule.sku != lot.sku:
                    continue
                
                # Since rules are sorted by markdown descending, the first match is the best
                best_rule = rule
                break
                    
        if best_rule:
            discount_multiplier = (100.0 - best_rule.markdown_percentage) / 100.0
            new_price = int(lot.current_price_cents * discount_multiplier)
            
            # Suggest Markdown
            suggestions.append(MarkdownSuggestion(
                variant_id=lot.variant_id,
                rule_id=best_rule.rule_id,
                original_price_cents=lot.current_price_cents,
                suggested_price_cents=new_price,
                reason=f"FEFO Proximity: {days_until_exp} days until expiration (Rule: {best_rule.markdown_percentage}% off)"
            ))

    return suggestions
