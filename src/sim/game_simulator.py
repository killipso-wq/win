"""
Core Monte Carlo Game Simulator
Handles environment, team/player sampling, and correlation modeling
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from scipy import stats
from scipy.stats import beta, dirichlet, poisson, binom

logger = logging.getLogger(__name__)

class GameSimulator:
    """
    Monte Carlo simulator for NFL DFS projections
    """
    
    def __init__(self, team_priors: pd.DataFrame, player_priors: pd.DataFrame, 
                 boom_thresholds: Dict, n_sims: int = 10000, seed: int = 42):
        """
        Initialize simulator with priors and configuration
        
        Args:
            team_priors: Team-level priors from 2023-2024 baseline
            player_priors: Player-level priors from 2023-2024 baseline  
            boom_thresholds: Position-specific boom thresholds
            n_sims: Number of Monte Carlo trials
            seed: Random seed for reproducibility
        """
        self.team_priors = team_priors
        self.player_priors = player_priors
        self.boom_thresholds = boom_thresholds
        self.n_sims = n_sims
        self.seed = seed
        
        # Set random seed
        np.random.seed(seed)
        
        # DK scoring function
        self.scoring = {
            'QB': {
                'pass_yd': 0.04,
                'pass_td': 4,
                'int': -1,
                'rush_yd': 0.1,
                'rush_td': 6,
                'bonus_300': 3,
                'bonus_400': 3
            },
            'RB': {
                'rush_yd': 0.1,
                'rush_td': 6,
                'rec_yd': 1.0,
                'rec_td': 6,
                'rec': 1.0,
                'bonus_100': 3
            },
            'WR': {
                'rec_yd': 1.0,
                'rec_td': 6,
                'rec': 1.0,
                'rush_yd': 0.1,
                'rush_td': 6,
                'bonus_100': 3
            },
            'TE': {
                'rec_yd': 1.0,
                'rec_td': 6,
                'rec': 1.0,
                'rush_yd': 0.1,
                'rush_td': 6,
                'bonus_100': 3
            },
            'DST': {
                'sack': 1.0,
                'int': 2.0,
                'fum_rec': 2.0,
                'td': 6.0,
                'safety': 2.0,
                'block': 2.0,
                'pa_0': 10.0,
                'pa_1_6': 7.0,
                'pa_7_13': 4.0,
                'pa_14_20': 1.0,
                'pa_21_27': 0.0,
                'pa_28_34': -1.0,
                'pa_35_plus': -4.0
            }
        }
        
        logger.info(f"Game simulator initialized with {n_sims} simulations")
    
    def simulate_week(self, players_df: pd.DataFrame) -> Dict:
        """
        Run full week simulation for all players
        
        Args:
            players_df: DataFrame with player info (PLAYER, POS, TEAM, OPP, etc.)
            
        Returns:
            Dict with simulation results for each player
        """
        results = {}
        
        # Group by game for correlation modeling
        games = self._group_players_by_game(players_df)
        
        for game_id, game_players in games.items():
            logger.info(f"Simulating game: {game_id}")
            
            # Simulate game environment
            game_env = self._simulate_game_environment(game_players)
            
            # Simulate team-level shocks
            team_shocks = self._simulate_team_shocks(game_players)
            
            # Simulate each player in the game
            for _, player in game_players.iterrows():
                player_id = self._get_player_id(player)
                
                # Get player priors
                player_prior = self._get_player_prior(player)
                
                # Simulate player performance
                sim_results = self._simulate_player(
                    player, player_prior, game_env, team_shocks
                )
                
                results[player_id] = sim_results
        
        return results
    
    def _group_players_by_game(self, players_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Group players by game for correlation modeling"""
        games = {}
        
        for _, player in players_df.iterrows():
            game_id = f"{player['OPP']}@{player['TEAM']}"
            if game_id not in games:
                games[game_id] = []
            games[game_id].append(player)
        
        return {game_id: pd.DataFrame(players) for game_id, players in games.items()}
    
    def _simulate_game_environment(self, game_players: pd.DataFrame) -> Dict:
        """Simulate game-level environment (pace, scoring, etc.)"""
        # Get game info from first player
        first_player = game_players.iloc[0]
        home_team = first_player['TEAM']
        away_team = first_player['OPP']
        
        # Get team priors
        home_prior = self.team_priors[self.team_priors['team'] == home_team].iloc[0]
        away_prior = self.team_priors[self.team_priors['team'] == away_team].iloc[0]
        
        # Base environment from team priors
        avg_pace = (home_prior['plays_per_game'] + away_prior['plays_per_game']) / 2
        avg_pass_rate = (home_prior['neutral_xpass'] + away_prior['neutral_xpass']) / 2
        
        # Adjust for game total if available
        game_total = first_player.get('O/U', 44.0)
        spread = first_player.get('SPRD', 0.0)
        
        # Environment adjustments
        total_factor = game_total / 44.0  # Normalize to league average
        pace_adjustment = 1.0 + (total_factor - 1.0) * 0.3  # 30% of total variance
        
        # Simulate game-level shocks
        pace_shock = np.random.normal(0, 0.1, self.n_sims)  # 10% pace variance
        pass_rate_shock = np.random.normal(0, 0.05, self.n_sims)  # 5% pass rate variance
        
        # Final environment
        sim_pace = avg_pace * pace_adjustment * (1 + pace_shock)
        sim_pass_rate = avg_pass_rate * (1 + pass_rate_shock)
        
        return {
            'pace': sim_pace,
            'pass_rate': sim_pass_rate,
            'game_total': game_total,
            'spread': spread,
            'home_team': home_team,
            'away_team': away_team
        }
    
    def _simulate_team_shocks(self, game_players: pd.DataFrame) -> Dict:
        """Simulate team-level efficiency shocks for correlation"""
        teams = game_players['TEAM'].unique()
        
        shocks = {}
        for team in teams:
            # Team efficiency shock (affects all players on team)
            efficiency_shock = np.random.normal(0, 0.15, self.n_sims)  # 15% efficiency variance
            
            # Position-specific shocks
            qb_shock = np.random.normal(0, 0.2, self.n_sims)  # QB-specific variance
            rb_shock = np.random.normal(0, 0.25, self.n_sims)  # RB-specific variance
            wr_shock = np.random.normal(0, 0.3, self.n_sims)   # WR-specific variance
            te_shock = np.random.normal(0, 0.25, self.n_sims)  # TE-specific variance
            
            shocks[team] = {
                'efficiency': efficiency_shock,
                'qb': qb_shock,
                'rb': rb_shock,
                'wr': wr_shock,
                'te': te_shock
            }
        
        return shocks
    
    def _simulate_player(self, player: pd.Series, player_prior: Dict, 
                        game_env: Dict, team_shocks: Dict) -> Dict:
        """Simulate individual player performance"""
        position = player['POS']
        team = player['TEAM']
        
        # Get team shock for this player
        team_shock = team_shocks[team]
        
        # Base simulation based on position
        if position == 'QB':
            return self._simulate_qb(player, player_prior, game_env, team_shock)
        elif position in ['RB', 'WR', 'TE']:
            return self._simulate_skill_player(player, player_prior, game_env, team_shock)
        elif position == 'DST':
            return self._simulate_dst(player, player_prior, game_env, team_shock)
        else:
            # Unknown position - use fallback
            return self._simulate_fallback(player, game_env)
    
    def _simulate_qb(self, player: pd.Series, player_prior: Dict, 
                    game_env: Dict, team_shock: Dict) -> Dict:
        """Simulate QB performance"""
        # Get priors
        pass_attempts_mean = player_prior.get('pass_attempts_per_game', 35)
        pass_yards_per_attempt = player_prior.get('pass_yards_per_attempt', 7.0)
        pass_td_rate = player_prior.get('pass_td_rate', 0.05)
        int_rate = player_prior.get('int_rate', 0.02)
        rush_attempts_mean = player_prior.get('rush_attempts_per_game', 3)
        rush_yards_per_attempt = player_prior.get('rush_yards_per_attempt', 5.0)
        rush_td_rate = player_prior.get('rush_td_rate', 0.1)
        
        # Adjust for game environment
        pace_factor = game_env['pace'] / 65.0  # Normalize to league average
        pass_rate_factor = game_env['pass_rate'] / 0.6  # Normalize to league average
        
        # Simulate attempts
        pass_attempts = np.random.poisson(pass_attempts_mean * pace_factor * pass_rate_factor, self.n_sims)
        rush_attempts = np.random.poisson(rush_attempts_mean * pace_factor * (2 - pass_rate_factor), self.n_sims)
        
        # Simulate efficiency with team shock
        pass_efficiency = pass_yards_per_attempt * (1 + team_shock['efficiency'] + team_shock['qb'])
        rush_efficiency = rush_yards_per_attempt * (1 + team_shock['efficiency'] + team_shock['qb'])
        
        # Simulate yards
        pass_yards = np.random.normal(pass_attempts * pass_efficiency, pass_attempts * pass_efficiency * 0.3)
        rush_yards = np.random.normal(rush_attempts * rush_efficiency, rush_attempts * rush_efficiency * 0.4)
        
        # Simulate TDs
        pass_tds = np.random.binomial(pass_attempts, pass_td_rate)
        rush_tds = np.random.binomial(rush_attempts, rush_td_rate)
        
        # Simulate interceptions
        ints = np.random.binomial(pass_attempts, int_rate)
        
        # Calculate DK points
        dk_points = (
            pass_yards * self.scoring['QB']['pass_yd'] +
            pass_tds * self.scoring['QB']['pass_td'] +
            ints * self.scoring['QB']['int'] +
            rush_yards * self.scoring['QB']['rush_yd'] +
            rush_tds * self.scoring['QB']['rush_td']
        )
        
        # Add bonuses
        dk_points += np.where(pass_yards >= 300, self.scoring['QB']['bonus_300'], 0)
        dk_points += np.where(pass_yards >= 400, self.scoring['QB']['bonus_400'], 0)
        
        # Clamp at zero
        dk_points = np.maximum(dk_points, 0)
        
        return self._calculate_summary_stats(dk_points, player)
    
    def _simulate_skill_player(self, player: pd.Series, player_prior: Dict,
                              game_env: Dict, team_shock: Dict) -> Dict:
        """Simulate RB/WR/TE performance"""
        position = player['POS']
        
        # Get priors
        targets_mean = player_prior.get('targets_per_game', 5)
        carries_mean = player_prior.get('carries_per_game', 10)
        yards_per_target = player_prior.get('yards_per_target', 8.0)
        yards_per_carry = player_prior.get('yards_per_carry', 4.0)
        td_rate = player_prior.get('td_rate', 0.05)
        
        # Adjust for game environment
        pace_factor = game_env['pace'] / 65.0
        
        # Position-specific adjustments
        if position == 'RB':
            pass_rate_factor = 1 - game_env['pass_rate']  # RBs benefit from run-heavy games
            targets_mean *= 0.3  # RBs get fewer targets
        else:  # WR/TE
            pass_rate_factor = game_env['pass_rate']  # WRs/TEs benefit from pass-heavy games
            carries_mean *= 0.1  # WRs/TEs get fewer carries
        
        # Simulate touches
        targets = np.random.poisson(targets_mean * pace_factor * pass_rate_factor, self.n_sims)
        carries = np.random.poisson(carries_mean * pace_factor * (1 - pass_rate_factor), self.n_sims)
        
        # Simulate efficiency with team shock
        pos_shock = team_shock[position.lower()]
        target_efficiency = yards_per_target * (1 + team_shock['efficiency'] + pos_shock)
        carry_efficiency = yards_per_carry * (1 + team_shock['efficiency'] + pos_shock)
        
        # Simulate yards
        rec_yards = np.random.normal(targets * target_efficiency, targets * target_efficiency * 0.4)
        rush_yards = np.random.normal(carries * carry_efficiency, carries * carry_efficiency * 0.5)
        
        # Simulate TDs
        total_touches = targets + carries
        tds = np.random.binomial(total_touches, td_rate)
        
        # Calculate DK points
        dk_points = (
            rec_yards * self.scoring[position]['rec_yd'] +
            targets * self.scoring[position]['rec'] +
            tds * self.scoring[position]['rec_td'] +
            rush_yards * self.scoring[position]['rush_yd']
        )
        
        # Add bonuses
        total_yards = rec_yards + rush_yards
        dk_points += np.where(total_yards >= 100, self.scoring[position]['bonus_100'], 0)
        
        # Clamp at zero
        dk_points = np.maximum(dk_points, 0)
        
        return self._calculate_summary_stats(dk_points, player)
    
    def _simulate_dst(self, player: pd.Series, player_prior: Dict,
                     game_env: Dict, team_shock: Dict) -> Dict:
        """Simulate DST performance"""
        # Get priors
        sacks_mean = player_prior.get('sacks_per_game', 2.0)
        ints_mean = player_prior.get('ints_per_game', 0.8)
        fum_rec_mean = player_prior.get('fum_rec_per_game', 0.5)
        td_rate = player_prior.get('def_td_rate', 0.1)
        
        # Adjust for opponent strength (simplified)
        opponent = player['OPP']
        opp_prior = self.team_priors[self.team_priors['team'] == opponent]
        
        if not opp_prior.empty:
            opp_epa = opp_prior.iloc[0].get('epa_per_play', 0.0)
            # Better offenses = fewer sacks/ints, more points allowed
            efficiency_factor = 1.0 - opp_epa * 0.5
        else:
            efficiency_factor = 1.0
        
        # Simulate defensive stats
        sacks = np.random.poisson(sacks_mean * efficiency_factor, self.n_sims)
        ints = np.random.poisson(ints_mean * efficiency_factor, self.n_sims)
        fum_rec = np.random.poisson(fum_rec_mean * efficiency_factor, self.n_sims)
        
        # Simulate TDs
        total_turnovers = ints + fum_rec
        def_tds = np.random.binomial(total_turnovers, td_rate)
        
        # Simulate points allowed (simplified)
        base_points = game_env['game_total'] / 2  # Assume 50/50 split
        points_allowed = np.random.normal(base_points, base_points * 0.3, self.n_sims)
        
        # Calculate DK points
        dk_points = (
            sacks * self.scoring['DST']['sack'] +
            ints * self.scoring['DST']['int'] +
            fum_rec * self.scoring['DST']['fum_rec'] +
            def_tds * self.scoring['DST']['td']
        )
        
        # Points allowed scoring
        for points, bonus in [
            (0, self.scoring['DST']['pa_0']),
            (7, self.scoring['DST']['pa_1_6']),
            (14, self.scoring['DST']['pa_7_13']),
            (21, self.scoring['DST']['pa_14_20']),
            (28, self.scoring['DST']['pa_21_27']),
            (35, self.scoring['DST']['pa_28_34'])
        ]:
            dk_points += np.where(points_allowed <= points, bonus, 0)
        
        # Clamp at zero
        dk_points = np.maximum(dk_points, 0)
        
        return self._calculate_summary_stats(dk_points, player)
    
    def _simulate_fallback(self, player: pd.Series, game_env: Dict) -> Dict:
        """Fallback simulation for unknown positions"""
        # Use site projection if available, otherwise random
        site_proj = player.get('FPTS', 10.0)
        
        # Simple normal distribution around site projection
        sim_points = np.random.normal(site_proj, site_proj * 0.4, self.n_sims)
        sim_points = np.maximum(sim_points, 0)
        
        return self._calculate_summary_stats(sim_points, player)
    
    def _calculate_summary_stats(self, sim_points: np.ndarray, player: pd.Series) -> Dict:
        """Calculate summary statistics from simulation draws"""
        # Percentiles
        p10 = np.percentile(sim_points, 10)
        p25 = np.percentile(sim_points, 25)
        p50 = np.percentile(sim_points, 50)
        p75 = np.percentile(sim_points, 75)
        p90 = np.percentile(sim_points, 90)
        p95 = np.percentile(sim_points, 95)
        
        # Mean and standard deviation
        mean = np.mean(sim_points)
        std = np.std(sim_points)
        
        # Boom probability
        position = player['POS']
        boom_threshold = self.boom_thresholds.get(position, p90)
        boom_prob = np.mean(sim_points >= boom_threshold)
        
        # Beat site probability
        site_proj = player.get('FPTS', None)
        if site_proj is not None:
            beat_site_prob = np.mean(sim_points >= site_proj)
        else:
            beat_site_prob = None
        
        return {
            'sim_mean': mean,
            'sim_std': std,
            'p10': p10,
            'p25': p25,
            'p50': p50,
            'p75': p75,
            'p90': p90,
            'p95': p95,
            'boom_prob': boom_prob,
            'beat_site_prob': beat_site_prob,
            'sim_draws': sim_points
        }
    
    def _get_player_id(self, player: pd.Series) -> str:
        """Generate stable player ID"""
        from slugify import slugify
        
        name = slugify(player['PLAYER'].upper(), separator='_')
        team = player['TEAM']
        pos = player['POS']
        
        return f"{team}_{pos}_{name}"
    
    def _get_player_prior(self, player: pd.Series) -> Dict:
        """Get player priors from baseline data"""
        player_id = self._get_player_id(player)
        
        # Look for exact match
        prior = self.player_priors[self.player_priors['player_id'] == player_id]
        
        if not prior.empty:
            return prior.iloc[0].to_dict()
        
        # Look for name match
        name_match = self.player_priors[
            self.player_priors['name'].str.contains(player['PLAYER'], case=False, na=False)
        ]
        
        if not name_match.empty:
            return name_match.iloc[0].to_dict()
        
        # Return empty prior (will use fallback)
        return {}