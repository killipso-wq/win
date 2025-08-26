"""
DFS GPP Championship System - Complete Build
Integrates all components for tournament domination
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class DFSChampionshipSystem:
    """
    Complete DFS GPP System with all features integrated
    """
    
    def __init__(self):
        """Initialize the championship system"""
        # Data storage
        self.players_df = None
        self.correlations_df = None
        self.defense_df = None
        
        # Roster requirements
        self.roster_requirements = {
            'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'FLEX': 1, 'DST': 1
        }
        self.salary_cap = 50000
        
        # GPP Strategy Parameters (from proven blueprint)
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
            'QB-OppWR': 0.15,  # Game stack
            'RB-DST': 0.18,
            'QB-RB': -0.10     # Negative correlation
        }
        
        # Initialize components
        self.defense_integration = None
        self.win_probability_ranker = None
        self.learning_system = None
        
        logger.info("DFS Championship System initialized")
    
    def load_all_data(self, players_path: str, defense_path: str):
        """Load all required data files"""
        try:
            # Load players
            self.players_df = pd.read_csv(players_path)
            logger.info(f"Loaded {len(self.players_df)} players")
            
            # Load defense
            self.defense_df = pd.read_csv(defense_path)
            logger.info(f"Loaded {len(self.defense_df)} defensive matchups")
            
            # Create correlations from defense data
            self._create_correlations_from_defense()
            
            # Process and enhance data
            self._process_player_data()
            self._integrate_defensive_matchups()
            
            # Initialize subsystems
            self._initialize_subsystems()
            
            logger.info("All data loaded and processed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return False
    
    def _create_correlations_from_defense(self):
        """Create correlations data from defense data"""
        if self.defense_df is None:
            return
        
        correlations = []
        for _, game in self.defense_df.iterrows():
            # Create correlation entry for each team
            correlations.append({
                'team': game['Team'],
                'opponent': game['OPP'],
                'game': f"{game['Team']} vs {game['OPP']}",
                'over_under': game.get('O/U', 45),
                'spread': game.get('Spread', 0),
                'home_team': game['Team'],
                'away_team': game['OPP']
            })
        
        self.correlations_df = pd.DataFrame(correlations)
        logger.info(f"Created {len(self.correlations_df)} game correlations")
    
    def _process_player_data(self):
        """Process player data with all calculations"""
        # Calculate leverage scores
        self.players_df['leverage_score'] = (
            self.players_df['boom_score'] / 
            self.players_df['Rst%'].clip(lower=0.1)
        )
        
        # Flag high leverage plays
        self.players_df['high_leverage'] = self.players_df['leverage_score'] > 10
        
        # Flag dart throws (<5% owned with boom potential)
        self.players_df['dart_throw'] = (
            (self.players_df['Rst%'] < 5) & 
            (self.players_df['boom_score'] > 40)
        )
        
        # Add value rating (points per $1000 salary)
        self.players_df['value_rating'] = (
            self.players_df['projection'] / (self.players_df['salary'] / 1000)
        )
        
        logger.info(f"Found {len(self.players_df[self.players_df['high_leverage']])} high leverage plays")
        logger.info(f"Found {len(self.players_df[self.players_df['dart_throw']])} dart throws")
    
    def _integrate_defensive_matchups(self):
        """Integrate defensive data with player projections"""
        from defense_integration import DefenseIntegration
        
        self.defense_integration = DefenseIntegration()
        self.defense_integration.defense_df = self.defense_df
        
        # Calculate defensive metrics
        self.defense_integration._calculate_defensive_metrics()
        
        # Enhance player projections
        self.players_df = self.defense_integration.enhance_player_projections(
            self.players_df
        )
        
        # Add DST projections
        dst_projections = self.defense_integration.get_dst_projections()
        if not dst_projections.empty:
            self.players_df = pd.concat([self.players_df, dst_projections], ignore_index=True)
        
        logger.info("Defensive matchups integrated")
    
    def _initialize_subsystems(self):
        """Initialize all subsystems"""
        from gpp_win_probability import GPPWinProbabilityRanker
        
        self.win_probability_ranker = GPPWinProbabilityRanker()
        
        logger.info("All subsystems initialized")
    
    def analyze_slate_edge(self) -> Dict:
        """
        Comprehensive slate analysis to find key edges
        """
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'slate_overview': {},
            'key_stacks': [],
            'leverage_plays': [],
            'contrarian_narratives': [],
            'bad_chalk': [],
            'game_environments': []
        }
        
        # Vegas game environments
        game_totals = self.correlations_df.groupby('game').agg({
            'over_under': 'first',
            'spread': 'first'
        }).reset_index()
        
        # Calculate implied team totals
        for idx, game in game_totals.iterrows():
            game_totals.loc[idx, 'favorite_total'] = (game['over_under'] / 2) + (abs(game['spread']) / 2)
            game_totals.loc[idx, 'dog_total'] = (game['over_under'] / 2) - (abs(game['spread']) / 2)
        
        # Find shootout games
        shootout_games = game_totals[game_totals['over_under'] > 50]
        analysis['slate_overview']['shootout_count'] = len(shootout_games)
        analysis['slate_overview']['avg_total'] = game_totals['over_under'].mean()
        analysis['slate_overview']['highest_total'] = game_totals['over_under'].max()
        
        # Top leverage plays
        leverage_plays = self.players_df.nlargest(10, 'leverage_score')
        analysis['leverage_plays'] = leverage_plays[[
            'player', 'position', 'team', 'salary', 
            'boom_score', 'Rst%', 'leverage_score'
        ]].to_dict('records')
        
        # Contrarian game stacks
        for _, game in shootout_games.iterrows():
            teams = self.correlations_df[
                self.correlations_df['game'] == game['game']
            ]['team'].unique()
            
            avg_ownership = self.players_df[
                self.players_df['team'].isin(teams)
            ]['Rst%'].mean()
            
            if avg_ownership < 12:
                analysis['contrarian_narratives'].append({
                    'game': game['game'],
                    'total': game['over_under'],
                    'avg_ownership': avg_ownership,
                    'narrative': f"Vegas loves it ({game['over_under']} O/U) but field ignoring"
                })
        
        # Bad chalk identification
        bad_chalk = self.players_df[
            (self.players_df['Rst%'] > 20) & 
            (self.players_df['leverage_score'] < 3) &
            (self.players_df['matchup_rating'] < 50)
        ]
        analysis['bad_chalk'] = bad_chalk[[
            'player', 'position', 'Rst%', 'leverage_score', 'matchup_rating'
        ]].to_dict('records')
        
        return analysis
    
    def find_correlation_stacks(self, qb_name: str) -> Dict[str, List[Dict]]:
        """Find all correlated stacking options for a QB"""
        qb_data = self.players_df[self.players_df['player'] == qb_name].iloc[0]
        team = qb_data['team']
        
        # Get game info
        game_info = self.correlations_df[self.correlations_df['team'] == team].iloc[0]
        opponent = game_info['opponent']
        game_total = game_info['over_under']
        
        stacks = {
            'double_stack': [],
            'game_stack': [],
            'leverage_stack': [],
            'skinny_stack': []
        }
        
        # Get teammates
        teammates = self.players_df[
            (self.players_df['team'] == team) & 
            (self.players_df['position'].isin(['WR', 'TE', 'RB']))
        ].copy()
        
        # Get opponents for bring-back
        opponents = self.players_df[
            (self.players_df['team'] == opponent) & 
            (self.players_df['position'].isin(['WR', 'TE', 'QB']))
        ].copy()
        
        # Build different stack types
        # 1. Double stacks (QB + 2 teammates)
        for i, tm1 in teammates.iterrows():
            for j, tm2 in teammates.iterrows():
                if i < j and tm1['position'] != 'RB' and tm2['position'] != 'RB':
                    stack_data = self._evaluate_stack(
                        [qb_data, tm1, tm2], 
                        stack_type='double'
                    )
                    stacks['double_stack'].append(stack_data)
        
        # 2. Game stacks (QB + teammate + opponent)
        for _, tm in teammates.iterrows():
            if tm['position'] in ['WR', 'TE']:
                for _, opp in opponents.iterrows():
                    stack_data = self._evaluate_stack(
                        [qb_data, tm, opp],
                        stack_type='game',
                        game_total=game_total
                    )
                    stacks['game_stack'].append(stack_data)
        
        # 3. Skinny stacks (QB + 1 pass catcher)
        for _, tm in teammates.iterrows():
            if tm['position'] in ['WR', 'TE']:
                stack_data = self._evaluate_stack(
                    [qb_data, tm],
                    stack_type='skinny'
                )
                stacks['skinny_stack'].append(stack_data)
        
        # 4. Leverage stacks (low combined ownership)
        all_stacks = stacks['double_stack'] + stacks['game_stack']
        stacks['leverage_stack'] = [
            s for s in all_stacks 
            if s['total_ownership'] < 25 and s['correlation_score'] > 70
        ]
        
        # Sort each type by correlation score
        for stack_type in stacks:
            stacks[stack_type] = sorted(
                stacks[stack_type], 
                key=lambda x: x['correlation_score'], 
                reverse=True
            )[:5]  # Keep top 5 of each type
        
        return stacks
    
    def _evaluate_stack(self, players: List, stack_type: str, game_total: float = 0) -> Dict:
        """Evaluate a stack's quality"""
        player_names = [p['player'] for p in players]
        
        # Calculate ownership
        total_ownership = sum(p['Rst%'] for p in players)
        max_ownership = max(p['Rst%'] for p in players)
        
        # Calculate salary
        total_salary = sum(p['salary'] for p in players)
        
        # Calculate correlation score
        correlation_score = 100  # Base score
        
        # Apply correlation boosts
        positions = [p['position'] for p in players[1:]]  # Exclude QB
        
        if 'WR' in positions:
            wr_count = positions.count('WR')
            correlation_score *= (1 + self.correlation_boosts['QB-WR1'] * wr_count)
        
        if 'TE' in positions:
            correlation_score *= (1 + self.correlation_boosts['QB-TE'])
        
        # Game stack bonus
        if stack_type == 'game':
            correlation_score *= (1 + self.correlation_boosts['QB-OppWR'])
            if game_total > 50:
                correlation_score *= 1.15  # Shootout bonus
        
        # Calculate leverage
        total_leverage = sum(p.get('leverage_score', 0) for p in players)
        avg_leverage = total_leverage / len(players)
        
        return {
            'players': player_names,
            'type': stack_type,
            'correlation_score': round(correlation_score, 1),
            'total_ownership': round(total_ownership, 1),
            'max_ownership': round(max_ownership, 1),
            'total_salary': total_salary,
            'avg_leverage': round(avg_leverage, 1),
            'game_total': game_total
        }
    
    def build_gpp_lineup(self, strategy: str = 'balanced', 
                        existing_exposure: Dict[str, int] = None) -> Dict:
        """
        Build a single GPP-optimized lineup
        
        Strategies:
        - balanced: Mix of chalk and leverage
        - leverage: Focus on low-owned plays
        - contrarian: Alternative narratives
        - stars_scrubs: Pay up + punt plays
        """
        lineup = {pos: [] for pos in self.roster_requirements}
        used_players = set()
        total_salary = 0
        
        logger.info(f"Building {strategy} lineup")
        
        # Step 1: Select primary stack
        stack = self._select_primary_stack(strategy, existing_exposure)
        
        # Add stack players to lineup
        for player_name in stack['players']:
            player = self.players_df[self.players_df['player'] == player_name].iloc[0]
            pos = self._get_lineup_position(player['position'], lineup)
            if pos:
                lineup[pos].append(player_name)
                used_players.add(player_name)
                total_salary += player['salary']
        
        # Step 2: Fill remaining roster spots
        remaining_salary = self.salary_cap - total_salary
        remaining_spots = self._count_remaining_spots(lineup)
        
        # Get position priority based on strategy
        position_order = self._get_position_priority(strategy)
        
        for position in position_order:
            if not self._position_needs_filled(position, lineup):
                continue
            
            candidates = self._get_position_candidates(
                position, used_players, remaining_salary, 
                remaining_spots, strategy
            )
            
            if candidates.empty:
                continue
            
            # Select based on strategy
            selected = self._select_player(candidates, strategy, existing_exposure)
            
            # Add to lineup
            lineup_pos = self._get_lineup_position(selected['position'], lineup)
            if lineup_pos:
                lineup[lineup_pos].append(selected['player'])
                used_players.add(selected['player'])
                total_salary += selected['salary']
                remaining_salary = self.salary_cap - total_salary
                remaining_spots = self._count_remaining_spots(lineup)
        
        # Step 3: Validate and score lineup
        lineup_data = {
            'lineup': lineup,
            'salary_used': total_salary,
            'strategy': strategy,
            'stack': stack
        }
        
        # Calculate lineup stats
        lineup_data['stats'] = self._calculate_lineup_stats(lineup)
        
        # Check if valid GPP lineup
        lineup_data['valid'] = self._validate_gpp_lineup(lineup_data['stats'])
        
        # Calculate win probability
        if hasattr(self, 'win_probability_ranker') and self.win_probability_ranker:
            lineup_data['win_probability_score'] = (
                self.win_probability_ranker.calculate_win_probability_score(lineup_data)
            )
        
        return lineup_data
    
    def _select_primary_stack(self, strategy: str, 
                             existing_exposure: Dict[str, int] = None) -> Dict:
        """Select primary stack based on strategy"""
        # Get top QBs based on strategy
        if strategy == 'leverage':
            qb_pool = self.players_df[
                (self.players_df['position'] == 'QB') &
                (self.players_df['Rst%'] < 15)
            ].nlargest(5, 'boom_score')
        elif strategy == 'contrarian':
            qb_pool = self.players_df[
                (self.players_df['position'] == 'QB') &
                (self.players_df['Rst%'] < 10) &
                (self.players_df['matchup_rating'] > 60)
            ].nlargest(5, 'boom_score')
        else:  # balanced or stars_scrubs
            qb_pool = self.players_df[
                self.players_df['position'] == 'QB'
            ].nlargest(10, 'boom_score')
        
        best_stack = None
        best_score = -1
        
        # Evaluate stacks for each QB
        for _, qb in qb_pool.iterrows():
            # Check exposure limits
            if existing_exposure and existing_exposure.get(qb['player'], 0) > 50:
                continue
            
            stacks = self.find_correlation_stacks(qb['player'])
            
            # Pick best stack type for strategy
            if strategy == 'leverage':
                stack_candidates = stacks.get('leverage_stack', [])
            elif strategy == 'contrarian':
                stack_candidates = stacks.get('game_stack', [])
            else:
                stack_candidates = (
                    stacks.get('double_stack', []) + 
                    stacks.get('game_stack', [])
                )
            
            for stack in stack_candidates:
                score = self._score_stack_for_strategy(stack, strategy)
                
                if score > best_score:
                    best_score = score
                    best_stack = stack
        
        return best_stack or {'players': [], 'correlation_score': 0}
    
    def _score_stack_for_strategy(self, stack: Dict, strategy: str) -> float:
        """Score a stack based on strategy preferences"""
        base_score = stack['correlation_score']
        
        if strategy == 'leverage':
            # Prioritize low ownership
            ownership_factor = max(0, 40 - stack['total_ownership']) / 40
            base_score *= (1 + ownership_factor)
        
        elif strategy == 'contrarian':
            # Extreme leverage
            if stack['total_ownership'] < 20:
                base_score *= 1.5
        
        elif strategy == 'balanced':
            # Optimal ownership range
            if 20 <= stack['total_ownership'] <= 35:
                base_score *= 1.2
        
        # Game environment bonus
        if stack.get('game_total', 0) > 50:
            base_score *= 1.1
        
        return base_score
    
    def _get_position_candidates(self, position: str, used_players: set, 
                               remaining_salary: int, remaining_spots: int,
                               strategy: str) -> pd.DataFrame:
        """Get candidate players for a position"""
        # Filter available players
        candidates = self.players_df[
            (self.players_df['position'] == position) &
            (~self.players_df['player'].isin(used_players))
        ].copy()
        
        if candidates.empty:
            return candidates
        
        # Salary constraints
        max_salary = remaining_salary - (remaining_spots - 1) * 3000
        candidates = candidates[candidates['salary'] <= max_salary]
        
        # Strategy-specific filters
        if strategy == 'leverage':
            # Prioritize low ownership
            candidates = candidates[candidates['Rst%'] < 20]
        
        elif strategy == 'contrarian':
            # Ultra low ownership
            candidates = candidates[candidates['Rst%'] < 15]
        
        elif strategy == 'stars_scrubs':
            # Either expensive or cheap
            candidates = candidates[
                (candidates['salary'] > 8000) | 
                (candidates['salary'] < 5000)
            ]
        
        # Sort by strategy preference
        if strategy in ['leverage', 'contrarian']:
            candidates = candidates.sort_values('leverage_score', ascending=False)
        else:
            candidates = candidates.sort_values('boom_score', ascending=False)
        
        return candidates.head(10)
    
    def _select_player(self, candidates: pd.DataFrame, strategy: str,
                      existing_exposure: Dict[str, int] = None) -> pd.Series:
        """Select a player from candidates based on strategy"""
        # Apply exposure limits if provided
        if existing_exposure:
            for idx, player in candidates.iterrows():
                if existing_exposure.get(player['player'], 0) > 60:
                    candidates = candidates.drop(idx)
        
        if candidates.empty:
            return None
        
        # Selection logic by strategy
        if strategy == 'leverage':
            # Highest leverage score
            return candidates.iloc[0]
        
        elif strategy == 'contrarian':
            # Balance of low ownership and upside
            candidates['contrarian_score'] = (
                candidates['boom_score'] / candidates['Rst%'].clip(lower=0.1)
            )
            return candidates.nlargest(1, 'contrarian_score').iloc[0]
        
        elif strategy == 'stars_scrubs':
            # Alternate between stars and scrubs
            if len(candidates) > 1:
                # If we have expensive options, take the best
                expensive = candidates[candidates['salary'] > 7000]
                if not expensive.empty:
                    return expensive.iloc[0]
            return candidates.iloc[0]
        
        else:  # balanced
            # Best projection with reasonable ownership
            balanced = candidates[candidates['Rst%'] < 30]
            if not balanced.empty:
                return balanced.iloc[0]
            return candidates.iloc[0]
    
    def _calculate_lineup_stats(self, lineup: Dict) -> Dict:
        """Calculate comprehensive lineup statistics"""
        all_players = []
        for players in lineup.values():
            all_players.extend(players)
        
        player_data = self.players_df[self.players_df['player'].isin(all_players)]
        
        stats = {
            # Ownership metrics
            'total_ownership': player_data['Rst%'].sum(),
            'max_ownership': player_data['Rst%'].max(),
            'min_ownership': player_data['Rst%'].min(),
            
            # Player distribution
            'high_owned_players': len(player_data[player_data['Rst%'] > 20]),
            'low_owned_players': len(player_data[player_data['Rst%'] < 10]),
            'dart_throws': len(player_data[player_data['dart_throw']]),
            
            # Performance metrics
            'projected_points': player_data['projection'].sum(),
            'projected_ceiling': player_data['boom_score'].sum(),
            'avg_leverage': player_data['leverage_score'].mean(),
            
            # Salary metrics
            'salary_used': player_data['salary'].sum(),
            'avg_salary': player_data['salary'].mean(),
            
            # Correlation metrics
            'has_qb_stack': self._has_correlation_stack(lineup),
            'stack_correlation': self._calculate_stack_correlation(lineup),
            
            # Matchup metrics
            'avg_matchup_rating': player_data['matchup_rating'].mean() 
                if 'matchup_rating' in player_data.columns else 50
        }
        
        # Additional calculated metrics
        stats['salary_remaining'] = self.salary_cap - stats['salary_used']
        stats['ownership_concentration'] = (
            stats['max_ownership'] / stats['total_ownership'] * 100 
            if stats['total_ownership'] > 0 else 0
        )
        
        return stats
    
    def _validate_gpp_lineup(self, stats: Dict) -> bool:
        """Validate lineup meets GPP best practices"""
        checks = {
            'ownership_range': (
                self.ownership_targets['min_cumulative'] <= 
                stats['total_ownership'] <= 
                self.ownership_targets['max_cumulative']
            ),
            'has_leverage': (
                stats['low_owned_players'] >= 
                self.ownership_targets['min_leverage_plays']
            ),
            'has_dart': (
                stats['dart_throws'] >= 
                self.ownership_targets['min_dart_throws']
            ),
            'has_stack': stats['has_qb_stack'],
            'salary_efficiency': (
                stats['salary_used'] >= 
                self.ownership_targets['min_salary_used']
            ),
            'not_too_chalky': (
                stats['high_owned_players'] <= 3
            )
        }
        
        return all(checks.values())
    
    def _has_correlation_stack(self, lineup: Dict) -> bool:
        """Check if lineup has correlated stack"""
        qb_list = lineup.get('QB', [])
        if not qb_list:
            return False
        
        qb = qb_list[0]
        qb_team = self.players_df[
            self.players_df['player'] == qb
        ]['team'].iloc[0]
        
        # Check for teammates
        all_players = []
        for players in lineup.values():
            all_players.extend(players)
        
        player_teams = self.players_df[
            self.players_df['player'].isin(all_players)
        ]['team'].tolist()
        
        # Need at least 2 from same team (including QB)
        return player_teams.count(qb_team) >= 2
    
    def _calculate_stack_correlation(self, lineup: Dict) -> float:
        """Calculate total correlation score for lineup"""
        correlation_score = 0
        
        # Get QB and team
        qb_list = lineup.get('QB', [])
        if not qb_list:
            return 0
        
        qb = qb_list[0]
        qb_data = self.players_df[self.players_df['player'] == qb].iloc[0]
        qb_team = qb_data['team']
        
        # Get opponent
        game = self.correlations_df[self.correlations_df['team'] == qb_team]
        if not game.empty:
            opponent = game.iloc[0]['opponent']
        else:
            return correlation_score
        
        # Check all players for correlations
        all_players = []
        for players in lineup.values():
            all_players.extend(players)
        
        for player in all_players:
            if player == qb:
                continue
            
            player_data = self.players_df[
                self.players_df['player'] == player
            ].iloc[0]
            
            # Same team correlation
            if player_data['team'] == qb_team:
                if player_data['position'] == 'WR':
                    correlation_score += self.correlation_boosts['QB-WR1'] * 100
                elif player_data['position'] == 'TE':
                    correlation_score += self.correlation_boosts['QB-TE'] * 100
                elif player_data['position'] == 'RB':
                    correlation_score += self.correlation_boosts['QB-RB'] * 100
            
            # Game stack correlation
            elif player_data['team'] == opponent:
                if player_data['position'] in ['WR', 'TE']:
                    correlation_score += self.correlation_boosts['QB-OppWR'] * 100
        
        return correlation_score
    
    def generate_tournament_portfolio(self, n_lineups: int = 150) -> Dict:
        """
        Generate a complete tournament portfolio
        """
        portfolio = []
        player_exposure = {}
        
        # Strategy distribution
        strategy_distribution = self._get_strategy_distribution(n_lineups)
        
        logger.info(f"Generating {n_lineups} lineup portfolio")
        
        for strategy, count in strategy_distribution.items():
            logger.info(f"Building {count} {strategy} lineups")
            
            for i in range(count):
                # Build lineup with exposure limits
                lineup_data = self.build_gpp_lineup(strategy, player_exposure)
                
                # Check diversity requirements
                if self._meets_diversity_requirements(
                    lineup_data, portfolio, player_exposure
                ):
                    portfolio.append(lineup_data)
                    
                    # Update exposure
                    for players in lineup_data['lineup'].values():
                        for player in players:
                            player_exposure[player] = (
                                player_exposure.get(player, 0) + 1
                            )
                
                # Progress update
                if len(portfolio) % 10 == 0:
                    logger.info(f"Generated {len(portfolio)} lineups")
        
        # Calculate portfolio statistics
        portfolio_stats = self._calculate_portfolio_stats(portfolio, player_exposure)
        
        return {
            'lineups': portfolio,
            'stats': portfolio_stats,
            'exposure': player_exposure
        }
    
    def _get_strategy_distribution(self, n_lineups: int) -> Dict[str, int]:
        """Get optimal strategy distribution"""
        if n_lineups == 1:
            return {'balanced': 1}
        
        elif n_lineups <= 5:
            return {
                'balanced': max(1, n_lineups // 2),
                'leverage': n_lineups - max(1, n_lineups // 2)
            }
        
        elif n_lineups <= 20:
            return {
                'balanced': int(n_lineups * 0.4),
                'leverage': int(n_lineups * 0.4),
                'contrarian': n_lineups - int(n_lineups * 0.8)
            }
        
        else:  # 20+ lineups
            base_distribution = {
                'balanced': int(n_lineups * 0.35),
                'leverage': int(n_lineups * 0.35),
                'contrarian': int(n_lineups * 0.25),
                'stars_scrubs': int(n_lineups * 0.05)
            }
            
            # Ensure we hit exact count
            total = sum(base_distribution.values())
            if total < n_lineups:
                base_distribution['balanced'] += n_lineups - total
            
            return base_distribution
    
    def _meets_diversity_requirements(self, new_lineup: Dict, 
                                     portfolio: List[Dict],
                                     exposure: Dict[str, int]) -> bool:
        """Check if lineup meets diversity requirements"""
        # Get all players in new lineup
        new_players = set()
        for players in new_lineup['lineup'].values():
            new_players.update(players)
        
        # Check max exposure (40% for core, 20% for others)
        max_lineups = len(portfolio) + 1
        for player in new_players:
            current_exposure = exposure.get(player, 0)
            player_data = self.players_df[
                self.players_df['player'] == player
            ].iloc[0]
            
            # Core plays can have higher exposure
            if player_data['Rst%'] > 20:
                max_allowed = max_lineups * 0.4
            else:
                max_allowed = max_lineups * 0.2
            
            if current_exposure >= max_allowed:
                return False
        
        # Check overlap with existing lineups
        for existing in portfolio[-10:]:  # Check last 10 lineups
            existing_players = set()
            for players in existing['lineup'].values():
                existing_players.update(players)
            
            overlap = len(new_players & existing_players)
            if overlap > 6:  # Max 6 shared players
                return False
        
        return True
    
    def _calculate_portfolio_stats(self, portfolio: List[Dict], 
                                  exposure: Dict[str, int]) -> Dict:
        """Calculate comprehensive portfolio statistics"""
        n_lineups = len(portfolio)
        
        # Aggregate statistics
        ownership_totals = [l['stats']['total_ownership'] for l in portfolio]
        leverage_scores = [l['stats']['avg_leverage'] for l in portfolio]
        ceilings = [l['stats']['projected_ceiling'] for l in portfolio]
        
        # Player exposure stats
        max_exposure_pct = (
            max(exposure.values()) / n_lineups * 100 
            if exposure else 0
        )
        
        # Get most exposed players
        top_exposures = sorted(
            exposure.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        return {
            'total_lineups': n_lineups,
            'unique_players': len(exposure),
            
            # Ownership metrics
            'avg_ownership': np.mean(ownership_totals),
            'ownership_std': np.std(ownership_totals),
            'ownership_distribution': {
                '<100%': len([o for o in ownership_totals if o < 100]),
                '100-120%': len([o for o in ownership_totals if 100 <= o < 120]),
                '120-140%': len([o for o in ownership_totals if 120 <= o < 140]),
                '>140%': len([o for o in ownership_totals if o >= 140])
            },
            
            # Performance metrics
            'avg_leverage': np.mean(leverage_scores),
            'avg_ceiling': np.mean(ceilings),
            'ceiling_range': (min(ceilings), max(ceilings)),
            
            # Diversity metrics
            'max_exposure_pct': max_exposure_pct,
            'avg_exposure_pct': sum(exposure.values()) / (n_lineups * 9) * 100,
            'top_exposures': [
                {'player': p, 'exposure': e / n_lineups * 100} 
                for p, e in top_exposures
            ],
            
            # Strategy breakdown
            'strategy_counts': {
                strategy: len([l for l in portfolio if l['strategy'] == strategy])
                for strategy in ['balanced', 'leverage', 'contrarian', 'stars_scrubs']
            }
        }
    
    # Helper methods
    def _get_lineup_position(self, player_position: str, lineup: Dict) -> Optional[str]:
        """Get the lineup slot for a player position"""
        # Direct position match
        if player_position in lineup and len(lineup[player_position]) < self.roster_requirements.get(player_position, 1):
            return player_position
        
        # FLEX eligibility
        if player_position in ['RB', 'WR', 'TE'] and len(lineup['FLEX']) < self.roster_requirements['FLEX']:
            # Check if primary positions are filled
            if player_position == 'RB' and len(lineup['RB']) >= self.roster_requirements['RB']:
                return 'FLEX'
            elif player_position == 'WR' and len(lineup['WR']) >= self.roster_requirements['WR']:
                return 'FLEX'
            elif player_position == 'TE' and len(lineup['TE']) >= self.roster_requirements['TE']:
                return 'FLEX'
        
        return None
    
    def _position_needs_filled(self, position: str, lineup: Dict) -> bool:
        """Check if a position still needs players"""
        current = len(lineup.get(position, []))
        required = self.roster_requirements.get(position, 0)
        return current < required
    
    def _count_remaining_spots(self, lineup: Dict) -> int:
        """Count remaining roster spots"""
        filled = sum(len(players) for players in lineup.values())
        total = sum(self.roster_requirements.values())
        return total - filled
    
    def _get_position_priority(self, strategy: str) -> List[str]:
        """Get position fill order based on strategy"""
        if strategy == 'stars_scrubs':
            # Fill expensive positions first
            return ['WR', 'RB', 'TE', 'QB', 'FLEX', 'DST']
        elif strategy == 'leverage':
            # Fill low-owned positions first
            return ['TE', 'DST', 'RB', 'WR', 'FLEX', 'QB']
        else:
            # Standard order
            return ['RB', 'WR', 'TE', 'FLEX', 'DST', 'QB']