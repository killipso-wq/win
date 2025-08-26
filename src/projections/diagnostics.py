"""
Diagnostics Calculator
Calculates MAE/RMSE/correlation metrics vs site projections
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging
from scipy.stats import pearsonr

logger = logging.getLogger(__name__)

class DiagnosticsCalculator:
    """
    Calculate diagnostic metrics for simulation accuracy
    """
    
    def __init__(self):
        logger.info("Diagnostics calculator initialized")
    
    def calculate_diagnostics(self, boom_df: pd.DataFrame, value_df: pd.DataFrame) -> Dict:
        """
        Calculate diagnostic metrics for all players
        
        Args:
            boom_df: DataFrame with boom metrics
            value_df: DataFrame with value metrics
            
        Returns:
            Dict with diagnostic metrics
        """
        # Merge data
        diagnostics_df = boom_df.merge(value_df, on='player_id', how='left')
        
        # Filter out rookie fallbacks for accuracy metrics
        non_rookie_df = diagnostics_df[~diagnostics_df['rookie_fallback']]
        
        diagnostics = {
            'total_players': len(diagnostics_df),
            'rookie_fallback_count': len(diagnostics_df[diagnostics_df['rookie_fallback']]),
            'non_rookie_count': len(non_rookie_df)
        }
        
        # Overall accuracy metrics (excluding rookies)
        if len(non_rookie_df) > 0:
            overall_metrics = self._calculate_accuracy_metrics(non_rookie_df)
            diagnostics.update(overall_metrics)
        
        # Position-specific metrics
        position_metrics = self._calculate_position_metrics(non_rookie_df)
        diagnostics.update(position_metrics)
        
        # Coverage metrics
        coverage_metrics = self._calculate_coverage_metrics(non_rookie_df)
        diagnostics.update(coverage_metrics)
        
        return diagnostics
    
    def _calculate_accuracy_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate overall accuracy metrics"""
        if len(df) == 0:
            return {}
        
        # Filter players with site projections
        valid_df = df[df['site_proj'].notna() & (df['site_proj'] > 0)]
        
        if len(valid_df) == 0:
            return {}
        
        sim_means = valid_df['sim_mean'].values
        site_projs = valid_df['site_proj'].values
        
        # Calculate metrics
        mae = np.mean(np.abs(sim_means - site_projs))
        rmse = np.sqrt(np.mean((sim_means - site_projs) ** 2))
        
        # Correlation
        try:
            correlation, p_value = pearsonr(sim_means, site_projs)
        except:
            correlation = 0.0
            p_value = 1.0
        
        return {
            'overall_mae': mae,
            'overall_rmse': rmse,
            'overall_correlation': correlation,
            'overall_correlation_p_value': p_value,
            'players_with_site_proj': len(valid_df)
        }
    
    def _calculate_position_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate position-specific accuracy metrics"""
        position_metrics = {}
        
        for position in df['position'].unique():
            pos_df = df[df['position'] == position]
            pos_df = pos_df[pos_df['site_proj'].notna() & (pos_df['site_proj'] > 0)]
            
            if len(pos_df) == 0:
                continue
            
            sim_means = pos_df['sim_mean'].values
            site_projs = pos_df['site_proj'].values
            
            # Calculate metrics
            mae = np.mean(np.abs(sim_means - site_projs))
            rmse = np.sqrt(np.mean((sim_means - site_projs) ** 2))
            
            try:
                correlation, p_value = pearsonr(sim_means, site_projs)
            except:
                correlation = 0.0
                p_value = 1.0
            
            position_metrics[f'{position.lower()}_mae'] = mae
            position_metrics[f'{position.lower()}_rmse'] = rmse
            position_metrics[f'{position.lower()}_correlation'] = correlation
            position_metrics[f'{position.lower()}_count'] = len(pos_df)
        
        return position_metrics
    
    def _calculate_coverage_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate coverage metrics (p10-p90 range)"""
        if len(df) == 0:
            return {}
        
        # Filter players with site projections
        valid_df = df[df['site_proj'].notna() & (df['site_proj'] > 0)]
        
        if len(valid_df) == 0:
            return {}
        
        coverage_count = 0
        total_count = len(valid_df)
        
        for _, player in valid_df.iterrows():
            site_proj = player['site_proj']
            p10 = player.get('p10', 0)
            p90 = player.get('p90', 0)
            
            # Check if site projection falls within p10-p90 range
            if p10 <= site_proj <= p90:
                coverage_count += 1
        
        coverage_rate = coverage_count / total_count if total_count > 0 else 0
        
        return {
            'coverage_p10_p90': coverage_rate,
            'coverage_count': coverage_count,
            'coverage_total': total_count
        }