"""
Defense Integration for Monte Carlo Simulation
Incorporates defensive matchups into projections
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

class DefenseIntegration:
    """
    Integrates defensive data into player projections
    """
    
    def __init__(self):
        self.defense_df = None
        self.position_impact = {
            'QB': 0.25,
            'RB': 0.30,
            'WR': 0.20,
            'TE': 0.15,
            'DST': 1.00
        }
    
    def _calculate_defensive_metrics(self):
        """Calculate defensive strength metrics"""
        if self.defense_df is None:
            return
        
        # Points allowed projection
        self.defense_df['projected_points_allowed'] = (
            self.defense_df['Points Against'] +
            (self.defense_df['O/U'] / 2) - 
            (self.defense_df['Spread'] / 2)
        )
        
        # Defensive efficiency
        self.defense_df['defensive_efficiency'] = (
            self.defense_df['Yards Against'] /
            self.defense_df['projected_points_allowed'].clip(lower=10)
        )
        
        # Position-specific ratings
        self._calculate_position_ratings()
    
    def _calculate_position_ratings(self):
        """Calculate vs position ratings"""
        for idx, defense in self.defense_df.iterrows():
            # vs QB Rating
            qb_rating = 100 - (
                (defense['Yards Against'] - 300) / 10 +
                defense['Sacks'] * 3 +
                defense['Int'] * 5
            )
            
            # vs RB Rating
            rb_rating = 100 - (
                (defense['projected_points_allowed'] - 20) * 2 +
                (defense['Spread'] * 1.5 if defense['Fav'] == defense['Team'] else 0)
            )
            
            # vs WR Rating
            wr_rating = 100 - (
                (defense['Yards Against'] - 300) / 8 +
                defense['Int'] * 3
            )
            
            # vs TE Rating
            te_rating = 100 + (wr_rating - 100) * 0.5
            
            # Normalize ratings
            self.defense_df.loc[idx, 'vs_QB_rating'] = np.clip(qb_rating, 0, 100)
            self.defense_df.loc[idx, 'vs_RB_rating'] = np.clip(rb_rating, 0, 100)
            self.defense_df.loc[idx, 'vs_RB_rating'] = np.clip(rb_rating, 0, 100)
            self.defense_df.loc[idx, 'vs_WR_rating'] = np.clip(wr_rating, 0, 100)
            self.defense_df.loc[idx, 'vs_TE_rating'] = np.clip(te_rating, 0, 100)
    
    def get_defensive_multiplier(self, team: str, position: str, opponent: str) -> float:
        """Get defensive adjustment multiplier"""
        if self.defense_df is None:
            return 1.0
        
        defense = self.defense_df[self.defense_df['Team'] == opponent]
        if defense.empty:
            return 1.0
        
        defense = defense.iloc[0]
        
        # Get position rating
        position_map = {
            'QB': 'vs_QB_rating',
            'RB': 'vs_RB_rating',
            'WR': 'vs_WR_rating',
            'TE': 'vs_TE_rating'
        }
        
        rating = defense.get(position_map.get(position, 'vs_QB_rating'), 50)
        
        # Convert to multiplier (0.7 to 1.3)
        multiplier = 0.7 + (rating / 100) * 0.6
        
        # Apply position impact
        impact = self.position_impact.get(position, 0.20)
        final_multiplier = 1.0 + (multiplier - 1.0) * impact
        
        return final_multiplier
    
    def enhance_player_projections(self, players_df: pd.DataFrame) -> pd.DataFrame:
        """Add defensive adjustments to projections"""
        players_df = players_df.copy()
        
        # Initialize columns
        players_df['defensive_multiplier'] = 1.0
        players_df['matchup_rating'] = 50
        
        for idx, player in players_df.iterrows():
            opponent = self._get_opponent(player['team'])
            
            if opponent:
                multiplier = self.get_defensive_multiplier(
                    player['team'],
                    player['position'],
                    opponent
                )
                
                players_df.loc[idx, 'defensive_multiplier'] = multiplier
                players_df.loc[idx, 'matchup_rating'] = self._get_matchup_rating(
                    opponent, player['position']
                )
                
                # Adjust projections
                if 'projection' in players_df.columns:
                    players_df.loc[idx, 'adjusted_projection'] = (
                        player['projection'] * multiplier
                    )
                
                if 'boom_score' in players_df.columns:
                    players_df.loc[idx, 'adjusted_boom'] = (
                        player['boom_score'] * multiplier
                    )
        
        return players_df
    
    def _get_opponent(self, team: str) -> Optional[str]:
        """Get opponent for team"""
        if self.defense_df is None:
            return None
        
        # Check home
        game = self.defense_df[self.defense_df['Team'] == team]
        if not game.empty:
            return game.iloc[0]['OPP']
        
        # Check away
        game = self.defense_df[self.defense_df['OPP'] == team]
        if not game.empty:
            return game.iloc[0]['Team']
        
        return None
    
    def _get_matchup_rating(self, opponent: str, position: str) -> float:
        """Get matchup rating (0-100)"""
        defense = self.defense_df[self.defense_df['Team'] == opponent]
        if defense.empty:
            return 50
        
        position_map = {
            'QB': 'vs_QB_rating',
            'RB': 'vs_RB_rating',
            'WR': 'vs_WR_rating',
            'TE': 'vs_TE_rating'
        }
        
        return defense.iloc[0].get(position_map.get(position, 'vs_QB_rating'), 50)
    
    def get_dst_projections(self) -> pd.DataFrame:
        """Get DST projections from defensive data"""
        if self.defense_df is None:
            return pd.DataFrame()
        
        dst_projections = self.defense_df[[
            'Team', 'OPP', 'Spread', 'O/U', 'Points'
        ]].copy()
        
        dst_projections.rename(columns={
            'Team': 'player',
            'Points': 'projection'
        }, inplace=True)
        
        dst_projections['position'] = 'DST'
        dst_projections['team'] = dst_projections['player']
        dst_projections['boom_score'] = dst_projections['projection'] * 1.4
        dst_projections['salary'] = 0  # Will be updated
        dst_projections['Rst%'] = 0    # Will be updated
        
        return dst_projections


class MonteCarloSimulatorWithDefense:
    """
    Enhanced Monte Carlo simulator with defensive adjustments
    """
    
    def __init__(self, defense_integration: DefenseIntegration):
        self.defense = defense_integration
        self.n_simulations = 10000
    
    def simulate_player(self, player: Dict, opponent: str) -> np.ndarray:
        """Simulate player with defensive adjustment"""
        base_proj = player['projection']
        position = player['position']
        
        # Get defensive multiplier
        def_mult = self.defense.get_defensive_multiplier(
            player['team'],
            position,
            opponent
        )
        
        # Adjust mean
        adjusted_mean = base_proj * def_mult
        
        # Position variance
        variance_map = {
            'QB': 0.25,
            'RB': 0.35,
            'WR': 0.40,
            'TE': 0.30,
            'DST': 0.20
        }
        
        std_dev = adjusted_mean * variance_map.get(position, 0.30)
        
        # Run simulations
        simulations = np.random.normal(adjusted_mean, std_dev, self.n_simulations)
        
        # Add TD variance
        if position in ['QB', 'RB', 'WR', 'TE']:
            td_rate = self._get_td_rate(player, def_mult)
            td_sims = np.random.poisson(td_rate, self.n_simulations)
            
            td_points = {'QB': 4, 'RB': 6, 'WR': 6, 'TE': 6}
            simulations += td_sims * td_points.get(position, 6)
        
        return np.maximum(0, simulations)
    
    def _get_td_rate(self, player: Dict, def_mult: float) -> float:
        """Calculate TD rate with defense"""
        base_rates = {
            'QB': 1.8,
            'RB': 0.4,
            'WR': 0.3,
            'TE': 0.25
        }
        
        rate = base_rates.get(player['position'], 0.3)
        return rate * (def_mult ** 1.5)  # TDs more volatile