"""
Currency conversion and budget calculation utilities.

Provides helper functions for currency conversion, budget tracking,
and financial calculations in travel planning.
"""

from decimal import Decimal
from typing import Dict, Optional

from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class CurrencyRate(BaseModel):
    """Exchange rate information."""
    
    from_currency: str = Field(description="Source currency code")
    to_currency: str = Field(description="Target currency code")
    rate: Decimal = Field(description="Exchange rate")
    timestamp: str = Field(description="Rate timestamp")


class ConversionResult(BaseModel):
    """Result of currency conversion."""
    
    original_amount: Decimal = Field(description="Original amount")
    original_currency: str = Field(description="Original currency")
    converted_amount: Decimal = Field(description="Converted amount")
    target_currency: str = Field(description="Target currency")
    rate: Decimal = Field(description="Exchange rate used")


class BudgetCalculator:
    """
    Calculator for budget and currency operations.
    
    NOTE: This is a stub implementation. In production:
    1. Integrate with a currency API (e.g., exchangerate-api.com, fixer.io)
    2. Cache exchange rates with TTL
    3. Handle rate updates and historical data
    """
    
    # Mock exchange rates (relative to USD)
    MOCK_RATES: Dict[str, Decimal] = {
        "USD": Decimal("1.0"),
        "EUR": Decimal("0.85"),
        "GBP": Decimal("0.73"),
        "JPY": Decimal("110.0"),
        "CAD": Decimal("1.25"),
        "AUD": Decimal("1.35"),
        "CHF": Decimal("0.92"),
        "CNY": Decimal("6.45"),
        "INR": Decimal("74.5"),
    }
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize budget calculator.
        
        Args:
            api_key: Currency API key (optional, stub implementation)
        """
        self.api_key = api_key
        self.default_currency = "USD"
    
    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> CurrencyRate:
        """
        Get exchange rate between two currencies.
        
        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            
        Returns:
            Exchange rate information
        """
        # TODO: Implement real API call to currency service
        logger.info(f"Getting exchange rate: {from_currency} -> {to_currency}")
        
        if not self.api_key or self.api_key.startswith("placeholder"):
            logger.warning("Using mock exchange rates")
            from_rate = self.MOCK_RATES.get(from_currency, Decimal("1.0"))
            to_rate = self.MOCK_RATES.get(to_currency, Decimal("1.0"))
            rate = to_rate / from_rate
        else:
            # Real API call would go here
            rate = Decimal("1.0")
        
        return CurrencyRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            timestamp="2025-11-18T00:00:00Z",
        )
    
    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
    ) -> ConversionResult:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Conversion result
        """
        if from_currency == to_currency:
            return ConversionResult(
                original_amount=amount,
                original_currency=from_currency,
                converted_amount=amount,
                target_currency=to_currency,
                rate=Decimal("1.0"),
            )
        
        rate_info = await self.get_exchange_rate(from_currency, to_currency)
        converted = amount * rate_info.rate
        
        # Round to 2 decimal places for currency
        converted = converted.quantize(Decimal("0.01"))
        
        logger.info(
            f"Converted {amount} {from_currency} to {converted} {to_currency}",
            extra={
                "amount": str(amount),
                "from": from_currency,
                "to": to_currency,
                "rate": str(rate_info.rate),
            }
        )
        
        return ConversionResult(
            original_amount=amount,
            original_currency=from_currency,
            converted_amount=converted,
            target_currency=to_currency,
            rate=rate_info.rate,
        )
    
    def calculate_total(
        self,
        amounts: Dict[str, Decimal],
        target_currency: Optional[str] = None,
    ) -> Decimal:
        """
        Calculate total from multiple amounts in different currencies.
        
        Args:
            amounts: Dictionary of {currency: amount}
            target_currency: Target currency (uses default if not provided)
            
        Returns:
            Total in target currency
        """
        if target_currency is None:
            target_currency = self.default_currency
        
        # Note: This should be async in production to fetch rates
        total = Decimal("0.0")
        for currency, amount in amounts.items():
            if currency == target_currency:
                total += amount
            else:
                # Simplified conversion using mock rates
                from_rate = self.MOCK_RATES.get(currency, Decimal("1.0"))
                to_rate = self.MOCK_RATES.get(target_currency, Decimal("1.0"))
                rate = to_rate / from_rate
                total += amount * rate
        
        return total.quantize(Decimal("0.01"))
    
    def is_within_budget(
        self,
        total_cost: Decimal,
        budget: Decimal,
        threshold: Optional[float] = None,
    ) -> tuple[bool, float]:
        """
        Check if total cost is within budget.
        
        Args:
            total_cost: Total cost
            budget: Budget limit
            threshold: Alert threshold (0.0-1.0)
            
        Returns:
            Tuple of (is_within_budget, utilization_percentage)
        """
        settings = get_settings()
        if threshold is None:
            threshold = settings.budget_alert_threshold
        
        utilization = float(total_cost / budget) if budget > 0 else 0.0
        is_within = total_cost <= budget
        
        if utilization >= threshold:
            logger.warning(
                f"Budget utilization at {utilization:.1%}",
                extra={"total_cost": str(total_cost), "budget": str(budget)}
            )
        
        return is_within, utilization
