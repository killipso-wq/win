"""
Value Metrics Calculator
Calculates value per $1k salary and ceiling value metrics
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class ValueMetricsCalculator:
    """
    Calculate value metrics for DFS players
    """
    
    def __init__(self):
        logger.info("Value metrics calculator initialized")
    
    def calculate_value_metrics(self, boom_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate value metrics for all players
        
        Args:
            boom_df: DataFrame with boom metrics and salary information
            
        Returns:
            DataFrame with value metrics added
        """
        value_data = []
        
        for _, player in boom_df.iterrows():
            value_metrics = self._calculate_player_value_metrics(player)
            value_data.append(value_metrics)
        
        return pd.DataFrame(value_data)
    
    def _calculate_player_value_metrics(self, player: pd.Series) -> Dict:
        """Calculate value metrics for a single player"""
        sim_mean = player.get('sim_mean', 0)
        p90 = player.get('p90', 0)
        salary = player.get('salary', None)
        site_proj = player.get('site_proj', None)
        
        # Value per $1k salary
        value_per_1k = None
        if salary and salary > 0:
            value_per_1k = sim_mean / (salary / 1000)
        
        # Ceiling value per $1k salary
        ceil_per_1k = None
        if salary and salary > 0:
            ceil_per_1k = p90 / (salary / 1000)
        
        # Site value (if provided)
        site_val = None
        if salary and salary > 0 and site_proj:
            site_val = site_proj / (salary / 1000)
        
        # Value vs site comparison
        value_vs_site = None
        if value_per_1k and site_val:
            value_vs_site = value_per_1k / site_val
        
        return {
            'player_id': player['player_id'],
            'value_per_1k': value_per_1k,
            'ceil_per_1k': ceil_per_1k,
            'site_val': site_val,
            'value_vs_site': value_vs_site
        }