"""
GPP Win Probability Ranking System
Optimizes for tournament wins, not median finish
"""

import numpy as np
from typing import Dict, List

class GPPWinProbabilityRanker:
    """
    Ranks lineups by probability of winning GPP tournaments
    """
    
    def __init__(self):
        # Winning lineup characteristics from analysis
        self.winning_profile = {
            'ownership_range': (100, 140),
            'optimal_ownership': 120,
            'leverage_plays_range': (3, 5),
            'dart_throw_min': 1,
            'correlation_min': 70,
            'salary_min': 49500
        }
        
        # Component weights for scoring
        self.scoring_weights = {
            'ceiling_score': 0.25,
            'ownership_optimality': 0.20,
            'leverage_quality': 0.20,
            'correlation_strength': 0.15,
            'uniqueness_factor': 0.10,
            'narrative_strength': 0.10
        }
    
    def calculate_win_probability_score(self, lineup_data: Dict) -> float:
        """Calculate lineup's probability of winning first place"""
        scores = {}
        stats = lineup_data['stats']
        
        # 1. Ceiling Component
        scores['ceiling_score'] = self._score_ceiling(stats)
        
        # 2. Ownership Optimality
        scores['ownership_optimality'] = self._score_ownership(stats)
        
        # 3. Leverage Quality
        scores['leverage_quality'] = self._score_leverage(stats)
        
        # 4. Correlation Strength
        scores['correlation_strength'] = self._score_correlations(stats, lineup_data)
        
        # 5. Uniqueness Factor
        scores['uniqueness_factor'] = self._score_uniqueness(stats)
        
        # 6. Narrative Strength
        scores['narrative_strength'] = self._score_narrative(lineup_data)
        
        # Calculate weighted total
        total_score = sum(
            scores[component] * self.scoring_weights[component]
            for component in scores
        )
        
        # Store component breakdown
        lineup_data['win_probability_components'] = scores
        lineup_data['win_probability_score'] = total_score
        
        return total_score
    
    def _score_ceiling(self, stats: Dict) -> float:
        """Score based on projected ceiling"""
        ceiling = stats['projected_ceiling']
        
        # Normalize (assuming 200 is elite ceiling)
        normalized = min(ceiling / 200 * 100, 100)
        
        # Non-linear scaling - ceiling matters more at high end
        if normalized > 80:
            return normalized * 1.1
        elif normalized > 60:
            return normalized
        else:
            return normalized * 0.8
    
    def _score_ownership(self, stats: Dict) -> float:
        """Score based on ownership optimality"""
        total_ownership = stats['total_ownership']
        
        # Perfect score at 120%
        if 100 <= total_ownership <= 140:
            distance_from_optimal = abs(total_ownership - 120)
            score = 100 - (distance_from_optimal * 1.5)
        else:
            # Heavy penalty outside range
            if total_ownership < 100:
                score = max(20, 70 - (100 - total_ownership) * 2)
            else:  # > 140
                score = max(10, 60 - (total_ownership - 140) * 3)
        
        return max(0, score)
    
    def _score_leverage(self, stats: Dict) -> float:
        """Score based on leverage play quality"""
        low_owned = stats['low_owned_players']
        avg_leverage = stats['avg_leverage']
        dart_throws = stats['dart_throws']
        
        # Count score (3-5 is optimal)
        if 3 <= low_owned <= 5:
            count_score = 100
        elif low_owned < 3:
            count_score = (low_owned / 3) * 80
        else:  # > 5
            count_score = max(70, 100 - (low_owned - 5) * 10)
        
        # Leverage quality
        leverage_score = min(avg_leverage * 5, 100)
        
        # Dart throw bonus
        dart_bonus = min(dart_throws * 15, 30)
        
        return (count_score * 0.4 + leverage_score * 0.4 + dart_bonus * 0.2)
    
    def _score_correlations(self, stats: Dict, lineup_data: Dict) -> float:
        """Score based on correlation strength"""
        if not stats['has_qb_stack']:
            return 20  # Severe penalty
        
        correlation_score = stats.get('stack_correlation', 0)
        base_score = min(80 + correlation_score / 10, 100)
        
        # Bonus for game stacks
        if lineup_data.get('stack', {}).get('type') == 'game':
            base_score = min(base_score + 10, 100)
        
        return base_score
    
    def _score_uniqueness(self, stats: Dict) -> float:
        """Score based on differentiation potential"""
        ownership = stats['total_ownership']
        low_owned = stats['low_owned_players']
        
        # Base from ownership level
        if ownership < 110:
            base = 85
        elif ownership < 125:
            base = 70
        else:
            base = 55
        
        # Boost for differentiation pieces
        boost = min(low_owned * 7, 15)
        
        return min(100, base + boost)
    
    def _score_narrative(self, lineup_data: Dict) -> float:
        """Score based on narrative strength"""
        strategy = lineup_data.get('strategy', 'balanced')
        
        narrative_scores = {
            'leverage': 85,
            'contrarian': 90,
            'balanced': 70,
            'stars_scrubs': 75
        }
        
        base = narrative_scores.get(strategy, 70)
        
        # Boost for strong narratives
        if lineup_data['stats'].get('avg_leverage', 0) > 15:
            base += 10
        
        return min(100, base)
    
    def rank_lineups_for_first(self, lineups: List[Dict]) -> List[Dict]:
        """Rank lineups by win probability"""
        # Calculate scores
        for lineup in lineups:
            self.calculate_win_probability_score(lineup)
        
        # Sort by score
        ranked = sorted(
            lineups,
            key=lambda x: x['win_probability_score'],
            reverse=True
        )
        
        # Add rankings
        for rank, lineup in enumerate(ranked):
            lineup['gpp_rank'] = rank + 1
            lineup['win_percentile'] = (len(ranked) - rank) / len(ranked) * 100
        
        return ranked