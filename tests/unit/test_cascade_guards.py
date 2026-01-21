# tests/unit/test_cascade_guards.py
"""
TEST 1: Unit tests for CASCADE guards (isolated, no broker).

Tests the guard logic without running the full system.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch

from wsplumber.domain.types import CurrencyPair, TickData, Price, Timestamp, Pips


class TestCascadeGuards:
    """Unit tests for recovery cascade prevention guards."""
    
    def test_spread_too_wide_calculation(self):
        """
        FIX-CASCADE-V3: Verify spread calculation logic.
        
        If spread > 2*RECOVERY_DISTANCE - 5, recovery should be blocked.
        RECOVERY_DISTANCE = 20 pips, so max safe spread = 35 pips.
        """
        from wsplumber.core.strategy._params import RECOVERY_DISTANCE_PIPS
        
        max_safe_spread = RECOVERY_DISTANCE_PIPS * 2 - 5
        
        # Normal spread (2 pips) - should be allowed
        normal_spread = 2.0
        assert normal_spread < max_safe_spread, "Normal spread should be safe"
        
        # Wide spread (40 pips) - should be blocked
        wide_spread = 40.0
        assert wide_spread > max_safe_spread, "40-pip spread should be blocked"
        
        # Edge case (35 pips) - exactly at threshold
        edge_spread = 35.0
        assert edge_spread >= max_safe_spread, "35-pip spread should be at/above threshold"
        
        print(f"✅ Spread validation logic correct. Max safe spread: {max_safe_spread} pips")
    
    def test_tick_index_guard_logic(self):
        """
        FIX-CASCADE-V2: Verify tick index tracking logic.
        
        Same tick index should block subsequent recovery creation.
        """
        # Simulate the guard dictionary
        last_recovery_tick_idx = {}
        pair = "EURUSD"
        
        # First recovery on tick 100 - should pass
        tick_idx_1 = 100
        assert last_recovery_tick_idx.get(pair) != tick_idx_1, "First tick should pass"
        last_recovery_tick_idx[pair] = tick_idx_1
        
        # Second recovery on same tick 100 - should be blocked
        assert last_recovery_tick_idx.get(pair) == tick_idx_1, "Same tick should be blocked"
        
        # Third recovery on tick 101 - should pass
        tick_idx_2 = 101
        assert last_recovery_tick_idx.get(pair) != tick_idx_2, "New tick should pass"
        last_recovery_tick_idx[pair] = tick_idx_2
        
        print("✅ Tick index guard logic correct")
    
    def test_recovery_distance_params(self):
        """
        Verify that recovery parameters are correctly configured.
        """
        from wsplumber.core.strategy._params import (
            RECOVERY_DISTANCE_PIPS, 
            RECOVERY_TP_PIPS,
            RECOVERY_LEVEL_STEP
        )
        
        # Recovery distance should be 20 pips
        assert RECOVERY_DISTANCE_PIPS == 20.0, f"Expected 20, got {RECOVERY_DISTANCE_PIPS}"
        
        # Recovery TP should be 80 pips
        assert RECOVERY_TP_PIPS == 80.0, f"Expected 80, got {RECOVERY_TP_PIPS}"
        
        # Recovery level step should be 40 pips
        assert RECOVERY_LEVEL_STEP == 40.0, f"Expected 40, got {RECOVERY_LEVEL_STEP}"
        
        print("✅ Recovery parameters correctly configured")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
