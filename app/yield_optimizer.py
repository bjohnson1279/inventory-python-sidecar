from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/pricing", tags=["pricing"])

class LiquidationRuleInput(BaseModel):
    rule_id: str
    days_to_expiration: int
    markdown_percentage: float
    department: Optional[str] = None
    sku: Optional[str] = None

class LotInput(BaseModel):
    variant_id: str
    sku: str
    department: str
    current_price_cents: int
    expiration_date: str # ISO format

class MarkdownSuggestion(BaseModel):
    variant_id: str
    rule_id: str
    original_price_cents: int
    suggested_price_cents: int
    reason: str

class OptimizeYieldRequest(BaseModel):
    rules: List[LiquidationRuleInput]
    lots: List[LotInput]

@router.post("/optimize-yield", response_model=List[MarkdownSuggestion])
def optimize_yield(req: OptimizeYieldRequest):
    suggestions = []
    now = datetime.now(timezone.utc)
    
    # Simple evaluation engine
    for lot in req.lots:
        try:
            exp_dt = datetime.fromisoformat(lot.expiration_date.replace("Z", "+00:00"))
            days_until_exp = (exp_dt - now).days
        except Exception:
            continue # skip unparseable
            
        if days_until_exp < 0:
            continue # Already expired, handled by FEFO quarantine
            
        best_rule = None
        
        for rule in req.rules:
            # Rule applies if days_to_expiration threshold is met
            if days_until_exp <= rule.days_to_expiration:
                # Check optional filters
                if rule.department and rule.department != lot.department:
                    continue
                if rule.sku and rule.sku != lot.sku:
                    continue
                
                # Use the rule with the highest markdown (most aggressive)
                if not best_rule or rule.markdown_percentage > best_rule.markdown_percentage:
                    best_rule = rule
                    
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
