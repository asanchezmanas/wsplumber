# src/wsplumber/domain/entities/debt.py
"""
DebtUnit Entity - Represents a debt with REAL calculated values.

Part of the Dynamic Debt Calculation System (Phase 3).
This runs in SHADOW MODE alongside the existing hardcoded system.

A DebtUnit represents pips owed from:
- Main+Hedge neutralization (previously hardcoded as 20 pips)
- Recovery failure (previously hardcoded as 40 pips)

The actual value is calculated from real execution prices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid


def generate_debt_id() -> str:
    """Generate a unique debt ID."""
    return f"DEBT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6].upper()}"


@dataclass
class DebtUnit:
    """
    Represents a single debt unit with REAL calculated value.
    
    This replaces the hardcoded 20/40 pip values with actual
    calculated amounts based on execution prices.
    """
    
    # === Identification ===
    id: str
    source_cycle_id: str
    source_operation_ids: List[str] = field(default_factory=list)
    
    # === Value - REAL, not hardcoded ===
    pips_owed: Decimal = Decimal("0")
    
    # === Status ===
    status: str = "active"  # active, partially_paid, liquidated
    
    # === Tracking ===
    created_at: datetime = field(default_factory=datetime.now)
    liquidated_at: Optional[datetime] = None
    
    # === Cost breakdown (for analytics) ===
    slippage_entry: Decimal = Decimal("0")  # Pips lost to entry slippage
    slippage_close: Decimal = Decimal("0")  # Pips lost to close slippage
    spread_cost: Decimal = Decimal("0")     # Pips lost to spread
    
    # === Audit trail ===
    entry_prices: dict = field(default_factory=dict)  # op_id -> entry price
    close_prices: dict = field(default_factory=dict)  # op_id -> close price
    
    # === Metadata ===
    debt_type: str = "main_hedge"  # main_hedge or recovery_failure
    metadata: dict = field(default_factory=dict)
    
    # =========================================
    # Factory Methods
    # =========================================
    
    @classmethod
    def from_neutralization(
        cls,
        cycle_id: str,
        losing_main_id: str,
        losing_main_entry: Decimal,
        losing_main_close: Decimal,
        winning_main_id: str,
        hedge_id: str,
        pair: str,
        slippage: Decimal = Decimal("0"),
        spread: Decimal = Decimal("0")
    ) -> "DebtUnit":
        """
        Create a debt unit from a Main+Hedge neutralization.
        
        The debt is the actual loss of the losing main operation,
        calculated from real execution prices.
        
        Previously this was hardcoded as 20 pips.
        """
        # Calculate real loss in pips
        multiplier = Decimal("100") if "JPY" in pair else Decimal("10000")
        real_loss_pips = abs(losing_main_close - losing_main_entry) * multiplier
        
        return cls(
            id=generate_debt_id(),
            source_cycle_id=cycle_id,
            source_operation_ids=[losing_main_id, winning_main_id, hedge_id],
            pips_owed=real_loss_pips.quantize(Decimal("0.1")),
            debt_type="main_hedge",
            slippage_entry=slippage,
            spread_cost=spread,
            entry_prices={losing_main_id: float(losing_main_entry)},
            close_prices={losing_main_id: float(losing_main_close)},
            metadata={
                "theoretical_debt": 20.0,  # What the hardcoded system would say
                "pair": pair
            }
        )
    
    @classmethod
    def from_recovery_failure(
        cls,
        cycle_id: str,
        recovery_buy_id: str,
        recovery_buy_entry: Decimal,
        recovery_sell_id: str,
        recovery_sell_entry: Decimal,
        pair: str,
        slippage: Decimal = Decimal("0"),
        spread: Decimal = Decimal("0")
    ) -> "DebtUnit":
        """
        Create a debt unit from a recovery failure.
        
        The debt is the distance between the two recovery operations
        that both activated (failure condition).
        
        Previously this was hardcoded as 40 pips.
        """
        # Calculate real distance in pips
        multiplier = Decimal("100") if "JPY" in pair else Decimal("10000")
        distance_pips = abs(recovery_buy_entry - recovery_sell_entry) * multiplier
        
        return cls(
            id=generate_debt_id(),
            source_cycle_id=cycle_id,
            source_operation_ids=[recovery_buy_id, recovery_sell_id],
            pips_owed=distance_pips.quantize(Decimal("0.1")),
            debt_type="recovery_failure",
            slippage_entry=slippage,
            spread_cost=spread,
            entry_prices={
                recovery_buy_id: float(recovery_buy_entry),
                recovery_sell_id: float(recovery_sell_entry)
            },
            metadata={
                "theoretical_debt": 40.0,  # What the hardcoded system would say
                "pair": pair
            }
        )
    
    # =========================================
    # Calculated Properties
    # =========================================
    
    @property
    def total_execution_cost(self) -> Decimal:
        """Total pips lost to execution imperfections."""
        return self.slippage_entry + self.slippage_close + self.spread_cost
    
    @property
    def theoretical_debt(self) -> float:
        """What the hardcoded system would have calculated."""
        return self.metadata.get("theoretical_debt", 20.0 if self.debt_type == "main_hedge" else 40.0)
    
    @property
    def debt_difference(self) -> float:
        """
        Difference between real and theoretical debt.
        
        Positive = real debt is higher (we're losing more than expected)
        Negative = real debt is lower (we're doing better than expected)
        """
        return float(self.pips_owed) - self.theoretical_debt
    
    @property
    def is_active(self) -> bool:
        """True if this debt is still owed."""
        return self.status == "active"
    
    @property
    def is_liquidated(self) -> bool:
        """True if this debt has been fully paid."""
        return self.status == "liquidated"
    
    # =========================================
    # Methods
    # =========================================
    
    def apply_payment(self, pips_paid: Decimal) -> Decimal:
        """
        Apply a payment to this debt.
        
        Returns: Remaining pips after paying this debt (0 if not fully paid)
        """
        if pips_paid >= self.pips_owed:
            # Fully paid
            remaining = pips_paid - self.pips_owed
            self.pips_owed = Decimal("0")
            self.status = "liquidated"
            self.liquidated_at = datetime.now()
            return remaining
        else:
            # Partial payment
            self.pips_owed -= pips_paid
            self.status = "partially_paid"
            return Decimal("0")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "source_cycle_id": self.source_cycle_id,
            "source_operation_ids": self.source_operation_ids,
            "pips_owed": float(self.pips_owed),
            "status": self.status,
            "debt_type": self.debt_type,
            "theoretical_debt": self.theoretical_debt,
            "debt_difference": self.debt_difference,
            "slippage_entry": float(self.slippage_entry),
            "slippage_close": float(self.slippage_close),
            "spread_cost": float(self.spread_cost),
            "total_execution_cost": float(self.total_execution_cost),
            "created_at": self.created_at.isoformat(),
            "liquidated_at": self.liquidated_at.isoformat() if self.liquidated_at else None
        }


@dataclass
class LiquidationResult:
    """Result of liquidating debts with profit."""
    
    debts_liquidated: List[DebtUnit] = field(default_factory=list)
    partial_payment_debt_id: Optional[str] = None
    partial_payment_amount: Decimal = Decimal("0")
    net_profit_pips: Decimal = Decimal("0")
    total_debt_remaining_pips: Decimal = Decimal("0")
    
    @property
    def num_debts_liquidated(self) -> int:
        """Number of debts fully liquidated."""
        return len(self.debts_liquidated)
    
    @property
    def has_remaining_profit(self) -> bool:
        """True if there's profit after paying all debts."""
        return self.net_profit_pips > 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "debts_liquidated": self.num_debts_liquidated,
            "partial_payment": {
                "debt_id": self.partial_payment_debt_id,
                "amount": float(self.partial_payment_amount)
            } if self.partial_payment_debt_id else None,
            "net_profit_pips": float(self.net_profit_pips),
            "total_debt_remaining_pips": float(self.total_debt_remaining_pips)
        }
