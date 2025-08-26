"""
Boom Score Calculator
Implements boom_prob, boom_score (1-100), and dart_flag calculations
"""

import numpy as np
import pandas as pd
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class BoomScoreCalculator:
    """
    Calculate boom scores and related metrics for DFS players
    """
    
    def __init__(self, boom_thresholds: Dict):
        """
        Initialize with position-specific boom thresholds
        
        Args:
            boom_thresholds: Dict with position -> threshold mapping
        """
        self.boom_thresholds = boom_thresholds
        logger.info("Boom score calculator initialized")
    
    def calculate_boom_metrics(self, sim_results: Dict, players_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate boom metrics for all players
        
        Args:
            sim_results: Dict of simulation results from GameSimulator
            players_df: Original players DataFrame with site projections
            
        Returns:
            DataFrame with boom metrics added
        """
        boom_data = []
        
        for _, player in players_df.iterrows():
            player_id = self._get_player_id(player)
            
            if player_id in sim_results:
                sim_data = sim_results[player_id]
                boom_metrics = self._calculate_player_boom_metrics(player, sim_data)
                boom_data.append(boom_metrics)
            else:
                # Fallback for players without simulation data
                boom_metrics = self._calculate_fallback_boom_metrics(player)
                boom_data.append(boom_metrics)
        
        boom_df = pd.DataFrame(boom_data)
        
        # Calculate position-normalized boom scores
        boom_df = self._normalize_boom_scores(boom_df)
        
        # Add dart flags
        boom_df['dart_flag'] = self._calculate_dart_flags(boom_df)
        
        return boom_df
    
    def _calculate_player_boom_metrics(self, player: pd.Series, sim_data: Dict) -> Dict:
        """Calculate boom metrics for a single player"""
        position = player['POS']
        site_proj = player.get('FPTS', None)
        salary = player.get('SAL', None)
        ownership = player.get('RST%', None)
        
        # Boom probability from simulation
        boom_prob = sim_data['boom_prob']
        
        # Beat site probability
        beat_site_prob = sim_data.get('beat_site_prob', 0.5)  # Default to 50% if no site projection
        
        # Value metrics
        sim_mean = sim_data['sim_mean']
        p90 = sim_data['p90']
        
        value_per_1k = None
        ceil_per_1k = None
        
        if salary and salary > 0:
            value_per_1k = sim_mean / (salary / 1000)
            ceil_per_1k = p90 / (salary / 1000)
        
        # Boom threshold used
        boom_threshold = self.boom_thresholds.get(position, p90)
        
        return {
            'player_id': self._get_player_id(player),
            'player': player['PLAYER'],
            'position': position,
            'team': player['TEAM'],
            'opponent': player['OPP'],
            'sim_mean': sim_mean,
            'p90': p90,
            'boom_prob': boom_prob,
            'beat_site_prob': beat_site_prob,
            'boom_threshold': boom_threshold,
            'value_per_1k': value_per_1k,
            'ceil_per_1k': ceil_per_1k,
            'site_proj': site_proj,
            'salary': salary,
            'ownership': ownership,
            'rookie_fallback': False
        }
    
    def _calculate_fallback_boom_metrics(self, player: pd.Series) -> Dict:
        """Calculate fallback boom metrics for players without simulation data"""
        position = player['POS']
        site_proj = player.get('FPTS', 10.0)
        salary = player.get('SAL', None)
        ownership = player.get('RST%', None)
        
        # Use site projection as base
        sim_mean = site_proj
        p90 = site_proj * 1.5  # Conservative ceiling estimate
        
        # Estimate boom probability based on position
        position_boom_rates = {
            'QB': 0.15,
            'RB': 0.12,
            'WR': 0.10,
            'TE': 0.08,
            'DST': 0.05
        }
        boom_prob = position_boom_rates.get(position, 0.10)
        
        # Beat site probability (50% for fallback)
        beat_site_prob = 0.5
        
        # Value metrics
        value_per_1k = None
        ceil_per_1k = None
        
        if salary and salary > 0:
            value_per_1k = sim_mean / (salary / 1000)
            ceil_per_1k = p90 / (salary / 1000)
        
        return {
            'player_id': self._get_player_id(player),
            'player': player['PLAYER'],
            'position': position,
            'team': player['TEAM'],
            'opponent': player['OPP'],
            'sim_mean': sim_mean,
            'p90': p90,
            'boom_prob': boom_prob,
            'beat_site_prob': beat_site_prob,
            'boom_threshold': p90,
            'value_per_1k': value_per_1k,
            'ceil_per_1k': ceil_per_1k,
            'site_proj': site_proj,
            'salary': salary,
            'ownership': ownership,
            'rookie_fallback': True
        }
    
    def _normalize_boom_scores(self, boom_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate position-normalized boom scores (1-100)"""
        boom_scores = []
        
        for position in boom_df['position'].unique():
            pos_data = boom_df[boom_df['position'] == position].copy()
            
            # Calculate composite score
            composite_scores = []
            
            for _, player in pos_data.iterrows():
                # Base composite: 60% boom_prob + 40% beat_site_prob
                composite = (
                    0.6 * player['boom_prob'] + 
                    0.4 * player['beat_site_prob']
                )
                
                # Ownership boost
                ownership = player.get('ownership', 50)
                if ownership <= 5:
                    own_boost = 0.20
                elif ownership <= 10:
                    own_boost = 0.10
                elif ownership <= 20:
                    own_boost = 0.05
                else:
                    own_boost = 0.0
                
                # Value boost
                value_boost = 0.0
                if player['value_per_1k'] is not None:
                    pos_median = pos_data['value_per_1k'].median()
                    if pos_median > 0:
                        value_ratio = player['value_per_1k'] / pos_median
                        if value_ratio > 1.0:
                            value_boost = min(0.15, (value_ratio - 1.0) * 0.15)
                
                # Apply boosts
                final_composite = composite * (1 + own_boost) * (1 + value_boost)
                composite_scores.append(final_composite)
            
            # Normalize to percentile rank within position
            composite_scores = np.array(composite_scores)
            percentile_ranks = np.argsort(np.argsort(composite_scores)) / len(composite_scores)
            boom_scores.extend(percentile_ranks * 100)
        
        boom_df['boom_score'] = boom_scores
        return boom_df
    
    def _calculate_dart_flags(self, boom_df: pd.DataFrame) -> List[bool]:
        """Calculate dart flags: low ownership + high boom score"""
        dart_flags = []
        
        for _, player in boom_df.iterrows():
            ownership = player.get('ownership', 50)
            boom_score = player.get('boom_score', 0)
            
            # Dart flag: ownership <= 5% AND boom_score >= 70
            is_dart = (ownership <= 5) and (boom_score >= 70)
            dart_flags.append(is_dart)
        
        return dart_flags
    
    def _get_player_id(self, player: pd.Series) -> str:
        """Generate stable player ID"""
        from slugify import slugify
        
        name = slugify(player['PLAYER'].upper(), separator='_')
        team = player['TEAM']
        pos = player['POS']
        
        return f"{team}_{pos}_{name}"
    
    def get_boom_thresholds(self, players_df: pd.DataFrame) -> Dict:
        """Get position-specific boom thresholds"""
        thresholds = {}
        
        for position in players_df['POS'].unique():
            pos_data = players_df[players_df['POS'] == position]
            
            # Use p90 from simulation or fallback to position average
            if 'p90' in pos_data.columns:
                threshold = pos_data['p90'].median()
            else:
                # Fallback thresholds based on position
                fallback_thresholds = {
                    'QB': 25.0,
                    'RB': 20.0,
                    'WR': 18.0,
                    'TE': 15.0,
                    'DST': 12.0
                }
                threshold = fallback_thresholds.get(position, 15.0)
            
            thresholds[position] = threshold
        
        return thresholds