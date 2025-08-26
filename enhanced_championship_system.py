"""
Enhanced Championship System for MonteCarloNFLSIM
Integrates all new features with your existing Monte Carlo simulator
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedChampionshipSystem:
    """
    Complete DFS GPP System integrated with your Monte Carlo simulator
    """
    
    def __init__(self):
        # Data storage
        self.players_df = None
        self.defense_df = None
        self.correlations_df = None
        self.simulation_cache = {}
        
        # DraftKings roster requirements
        self.roster_requirements = {
            'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'FLEX': 1, 'DST': 1
        }
        self.salary_cap = 50000
        
        # GPP winning strategy parameters
        self.ownership_targets = {
            'min_cumulative': 100,
            'max_cumulative': 140,
            'max_player': 40,
            'min_leverage_plays': 3,
            'max_leverage_plays': 5,
            'min_dart_throws': 1,
            'min_salary_used': 49500
        }
        
        # Correlation boosts for stacking
        self.correlation_boosts = {
            'QB-WR1': 0.35,
            'QB-WR2': 0.25,
            'QB-TE': 0.20,
            'QB-OppWR': 0.15,
            'RB-DST': 0.18,
            'QB-RB': -0.10
        }
        
        logger.info("Enhanced Championship System initialized")
    
    def load_all_data(self, players_path='players.csv', defense_path='defense.csv', 
                     correlations_path=None):
        """Load all data files including defense.csv"""
        try:
            # Load players
            self.players_df = pd.read_csv(players_path)
            logger.info(f"Loaded {len(self.players_df)} players")
            
            # Load defense data from your defense.csv
            self.defense_df = pd.read_csv(defense_path, encoding='utf-8-sig')
            logger.info(f"Loaded {len(self.defense_df)} defensive matchups")
            
            # Load correlations if provided
            if correlations_path:
                self.correlations_df = pd.read_csv(correlations_path)
                logger.info(f"Loaded correlation data")
            
            # Process all data
            self._process_player_data()
            self._integrate_defense_data()
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return False
    
    def _process_player_data(self):
        """Process player data with all calculations"""
        # Add required columns if missing
        if 'Rst%' not in self.players_df.columns:
            self.players_df['Rst%'] = np.random.uniform(5, 35, len(self.players_df))
            logger.info("Generated ownership projections")
        
        if 'boom_score' not in self.players_df.columns:
            self.players_df['boom_score'] = self.players_df['projection'] * 1.5
            logger.info("Generated boom scores")
        
        # Calculate leverage scores
        self.players_df['leverage_score'] = (
            self.players_df['boom_score'] / 
            self.players_df['Rst%'].clip(lower=0.1)
        )
        
        # Flag high leverage plays
        self.players_df['high_leverage'] = self.players_df['leverage_score'] > 10
        
        # Flag dart throws
        self.players_df['dart_throw'] = (
            (self.players_df['Rst%'] < 5) & 
            (self.players_df['boom_score'] > 40)
        )
        
        # Add value rating
        self.players_df['value_rating'] = (
            self.players_df['projection'] / (self.players_df['salary'] / 1000)
        )
    
    def _integrate_defense_data(self):
        """Integrate your defense.csv data"""
        # Process defense data from your CSV
        if self.defense_df is not None:
            # Map teams and calculate defensive matchup ratings
            for idx, player in self.players_df.iterrows():
                matchup_rating = self._calculate_matchup_rating(
                    player.get('team', ''),
                    player.get('position', '')
                )
                self.players_df.loc[idx, 'matchup_rating'] = matchup_rating
            
            logger.info("Defense data integrated")
    
    def _calculate_matchup_rating(self, team, position):
        """Calculate matchup rating using defense.csv data"""
        # Find opponent for this team
        defense_row = self.defense_df[
            (self.defense_df['Team'] == team) | (self.defense_df['OPP'] == team)
        ]
        
        if defense_row.empty:
            return 50  # Neutral rating
        
        defense_row = defense_row.iloc[0]
        
        # Calculate rating based on defensive stats
        if position == 'DST':
            # Use fantasy points directly for DST
            return defense_row.get('Points', 7) * 10
        else:
            # Calculate based on points allowed and other factors
            base_rating = 50
            points_against = defense_row.get('Points Against', 20)
            
            # Better matchup = higher rating
            if points_against > 25:
                base_rating = 70  # Good matchup
            elif points_against < 18:
                base_rating = 30  # Tough matchup
            
            return base_rating
    
    def run_monte_carlo_simulation(self, lineup: Dict, n_sims=10000) -> Dict:
        """Run Monte Carlo simulation on a lineup"""
        results = []
        
        for _ in range(n_sims):
            sim_score = 0
            for position, players in lineup.items():
                for player_name in players:
                    player_row = self.players_df[
                        self.players_df['player'] == player_name
                    ]
                    if not player_row.empty:
                        player = player_row.iloc[0]
                        # Simulate performance with variance
                        mean = player['projection']
                        std = mean * 0.3  # 30% standard deviation
                        score = np.random.normal(mean, std)
                        sim_score += max(0, score)
            
            results.append(sim_score)
        
        return {
            'mean': np.mean(results),
            'median': np.median(results),
            'ceiling': np.percentile(results, 95),
            'floor': np.percentile(results, 5),
            'boom_probability': sum(1 for r in results if r > 180) / n_sims
        }
    
    def analyze_slate_edge(self) -> Dict:
        """Comprehensive slate analysis"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'slate_overview': {},
            'leverage_plays': [],
            'contrarian_narratives': [],
            'bad_chalk': [],
            'defensive_matchups': []
        }
        
        # Analyze defense data
        if self.defense_df is not None:
            # Find best defensive matchups
            best_matchups = self.defense_df.nlargest(5, 'Points')[
                ['Team', 'OPP', 'Points', 'Spread', 'O/U']
            ].to_dict('records')
            analysis['defensive_matchups'] = best_matchups
        
        # Top leverage plays
        leverage_plays = self.players_df.nlargest(10, 'leverage_score')
        analysis['leverage_plays'] = leverage_plays[[
            'player', 'position', 'team', 'salary', 
            'boom_score', 'Rst%', 'leverage_score'
        ]].to_dict('records')
        
        # Bad chalk identification
        bad_chalk = self.players_df[
            (self.players_df['Rst%'] > 20) & 
            (self.players_df['leverage_score'] < 3)
        ]
        analysis['bad_chalk'] = bad_chalk[[
            'player', 'position', 'Rst%', 'leverage_score'
        ]].head(10).to_dict('records')
        
        return analysis
    
    def build_gpp_lineup(self, strategy='balanced') -> Dict:
        """Build a single GPP-optimized lineup"""
        lineup = {pos: [] for pos in self.roster_requirements}
        used_players = set()
        total_salary = 0
        total_ownership = 0
        
        logger.info(f"Building {strategy} lineup")
        
        # Strategy-specific player pool filters
        if strategy == 'leverage':
            player_pool = self.players_df[self.players_df['Rst%'] < 20].copy()
        elif strategy == 'contrarian':
            player_pool = self.players_df[self.players_df['Rst%'] < 15].copy()
        else:
            player_pool = self.players_df.copy()
        
        # Build lineup by position
        for position in ['QB', 'RB', 'WR', 'TE', 'DST']:
            needed = self.roster_requirements[position]
            position_pool = player_pool[
                (player_pool['position'] == position) &
                (~player_pool['player'].isin(used_players))
            ].copy()
            
            # Sort by strategy preference
            if strategy == 'leverage':
                position_pool = position_pool.sort_values('leverage_score', ascending=False)
            else:
                position_pool = position_pool.sort_values('projection', ascending=False)
            
            # Select players
            for i in range(min(needed, len(position_pool))):
                player = position_pool.iloc[i]
                
                # Check salary constraint
                if total_salary + player['salary'] <= self.salary_cap - 1000:
                    lineup[position].append(player['player'])
                    used_players.add(player['player'])
                    total_salary += player['salary']
                    total_ownership += player['Rst%']
        
        # Fill FLEX
        flex_pool = player_pool[
            (player_pool['position'].isin(['RB', 'WR', 'TE'])) &
            (~player_pool['player'].isin(used_players))
        ].sort_values('projection', ascending=False)
        
        if len(flex_pool) > 0:
            flex_player = flex_pool.iloc[0]
            if total_salary + flex_player['salary'] <= self.salary_cap:
                lineup['FLEX'].append(flex_player['player'])
                total_salary += flex_player['salary']
                total_ownership += flex_player['Rst%']
        
        # Run simulation
        simulation_results = self.run_monte_carlo_simulation(lineup)
        
        return {
            'lineup': lineup,
            'salary_used': total_salary,
            'total_ownership': round(total_ownership, 1),
            'strategy': strategy,
            'simulation': simulation_results,
            'valid': self._validate_lineup(lineup, total_salary)
        }
    
    def _validate_lineup(self, lineup: Dict, salary: int) -> bool:
        """Validate lineup meets requirements"""
        # Check positions filled
        for pos, required in self.roster_requirements.items():
            if len(lineup.get(pos, [])) != required:
                return False
        
        # Check salary
        if salary > self.salary_cap or salary < self.ownership_targets['min_salary_used']:
            return False
        
        return True
    
    def generate_tournament_portfolio(self, n_lineups=20) -> Dict:
        """Generate multiple diverse lineups"""
        portfolio = []
        strategies = ['balanced'] * (n_lineups // 2) + \
                    ['leverage'] * (n_lineups // 3) + \
                    ['contrarian'] * (n_lineups - n_lineups // 2 - n_lineups // 3)
        
        for i, strategy in enumerate(strategies):
            lineup = self.build_gpp_lineup(strategy)
            lineup['lineup_number'] = i + 1
            portfolio.append(lineup)
            
            if (i + 1) % 5 == 0:
                logger.info(f"Generated {i + 1} lineups")
        
        return {
            'lineups': portfolio,
            'count': len(portfolio),
            'avg_ownership': np.mean([l['total_ownership'] for l in portfolio]),
            'avg_ceiling': np.mean([l['simulation']['ceiling'] for l in portfolio])
        }