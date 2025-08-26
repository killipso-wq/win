"""
DraftKings Lineup Exporter
Exports optimized lineups in DK CSV format
"""

import pandas as pd
import csv
from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DKLineupExporter:
    """
    Export lineups in DraftKings upload format
    """
    
    def __init__(self, championship_system):
        self.system = championship_system
        self.dk_positions = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST']
    
    def export_top_lineups(self, 
                          n_lineups: int = 20,
                          strategy: str = 'mixed',
                          filename: str = None,
                          ranking_method: str = 'win_probability') -> str:
        """
        Export top N lineups to DraftKings CSV
        
        Args:
            n_lineups: Number of lineups to export (1-150)
            strategy: 'mixed', 'balanced', 'leverage', 'contrarian'
            filename: Output filename
            ranking_method: 'win_probability' or 'ceiling'
        
        Returns:
            Path to exported CSV file
        """
        logger.info(f"Exporting {n_lineups} lineups with {strategy} strategy")
        
        # Generate lineups
        if strategy == 'mixed':
            lineups = self._generate_mixed_lineups(n_lineups)
        else:
            lineups = self._generate_strategy_lineups(n_lineups, strategy)
        
        # Rank lineups
        if ranking_method == 'win_probability' and hasattr(self.system, 'win_probability_ranker'):
            logger.info("Ranking by win probability")
            ranked_lineups = self.system.win_probability_ranker.rank_lineups_for_first(lineups)
        else:
            # Fallback to ceiling
            ranked_lineups = sorted(
                lineups,
                key=lambda x: x['stats']['projected_ceiling'],
                reverse=True
            )
        
        # Take top N
        top_lineups = ranked_lineups[:n_lineups]
        
        # Generate filename
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dk_upload_{n_lineups}_lineups_{timestamp}.csv"
        
        # Write CSV
        self._write_dk_csv(top_lineups, filename)
        
        # Print summary
        self._print_export_summary(top_lineups, filename)
        
        return filename
    
    def _generate_mixed_lineups(self, n_lineups: int) -> List[Dict]:
        """Generate lineups with mixed strategies"""
        lineups = []
        
        # Strategy distribution
        distributions = {
            'balanced': int(n_lineups * 0.35),
            'leverage': int(n_lineups * 0.35),
            'contrarian': int(n_lineups * 0.25),
            'stars_scrubs': int(n_lineups * 0.05)
        }
        
        # Ensure exact count
        total = sum(distributions.values())
        if total < n_lineups:
            distributions['balanced'] += n_lineups - total
        
        # Generate lineups
        for strategy, count in distributions.items():
            for i in range(count):
                lineup = self.system.build_gpp_lineup(strategy)
                if lineup['valid']:
                    lineups.append(lineup)
                
                if len(lineups) % 10 == 0:
                    logger.info(f"Generated {len(lineups)} lineups")
        
        return lineups
    
    def _generate_strategy_lineups(self, n_lineups: int, strategy: str) -> List[Dict]:
        """Generate lineups with single strategy"""
        lineups = []
        attempts = 0
        max_attempts = n_lineups * 3
        
        while len(lineups) < n_lineups and attempts < max_attempts:
            lineup = self.system.build_gpp_lineup(strategy)
            
            if lineup['valid'] and self._is_unique_enough(lineup, lineups):
                lineups.append(lineup)
            
            attempts += 1
        
        return lineups
    
    def _is_unique_enough(self, new_lineup: Dict, existing: List[Dict]) -> bool:
        """Check lineup uniqueness"""
        if not existing:
            return True
        
        new_players = set()
        for players in new_lineup['lineup'].values():
            new_players.update(players)
        
        for lineup in existing[-5:]:  # Check last 5
            existing_players = set()
            for players in lineup['lineup'].values():
                existing_players.update(players)
            
            if len(new_players & existing_players) > 6:
                return False
        
        return True
    
    def _write_dk_csv(self, lineups: List[Dict], filename: str):
        """Write lineups to DraftKings CSV format"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(self.dk_positions)
            
            # Write each lineup
            for lineup_data in lineups:
                lineup = lineup_data['lineup']
                row = []
                
                # Map positions
                row.append(lineup['QB'][0] if lineup['QB'] else '')
                
                # RBs
                rbs = lineup['RB']
                row.append(rbs[0] if len(rbs) > 0 else '')
                row.append(rbs[1] if len(rbs) > 1 else '')
                
                # WRs
                wrs = lineup['WR']
                row.append(wrs[0] if len(wrs) > 0 else '')
                row.append(wrs[1] if len(wrs) > 1 else '')
                row.append(wrs[2] if len(wrs) > 2 else '')
                
                # TE
                row.append(lineup['TE'][0] if lineup['TE'] else '')
                
                # FLEX
                row.append(lineup['FLEX'][0] if lineup['FLEX'] else '')
                
                # DST
                row.append(lineup['DST'][0] if lineup['DST'] else '')
                
                writer.writerow(row)
    
    def _print_export_summary(self, lineups: List[Dict], filename: str):
        """Print export summary"""
        print(f"\n📊 EXPORT SUMMARY")
        print(f"File: {filename}")
        print(f"Lineups: {len(lineups)}")
        
        if lineups:
            # Strategy breakdown
            strategies = {}
            for lineup in lineups:
                strategy = lineup.get('strategy', 'unknown')
                strategies[strategy] = strategies.get(strategy, 0) + 1
            
            print(f"Strategy breakdown:")
            for strategy, count in strategies.items():
                print(f"  {strategy}: {count}")
            
            # Performance stats
            avg_ownership = sum(l['stats']['total_ownership'] for l in lineups) / len(lineups)
            avg_ceiling = sum(l['stats']['projected_ceiling'] for l in lineups) / len(lineups)
            
            print(f"Avg ownership: {avg_ownership:.1f}%")
            print(f"Avg ceiling: {avg_ceiling:.1f}")
            
            # Top players by exposure
            player_exposure = {}
            for lineup in lineups:
                for players in lineup['lineup'].values():
                    for player in players:
                        player_exposure[player] = player_exposure.get(player, 0) + 1
            
            top_exposure = sorted(
                player_exposure.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            print(f"Top exposures:")
            for player, count in top_exposure:
                pct = (count / len(lineups)) * 100
                print(f"  {player}: {pct:.1f}%")
        
        print(f"\n✅ Ready for DraftKings upload!")
    
    def export_with_metadata(self, lineups: List[Dict], filename: str):
        """Export lineups with metadata for analysis"""
        # Create detailed export
        export_data = []
        
        for i, lineup_data in enumerate(lineups):
            lineup = lineup_data['lineup']
            stats = lineup_data['stats']
            
            # Get all players
            all_players = []
            for players in lineup.values():
                all_players.extend(players)
            
            # Create row with metadata
            row = {
                'lineup_id': i + 1,
                'strategy': lineup_data.get('strategy', 'unknown'),
                'win_probability_score': lineup_data.get('win_probability_score', 0),
                'gpp_rank': lineup_data.get('gpp_rank', 0),
                'total_ownership': stats['total_ownership'],
                'projected_ceiling': stats['projected_ceiling'],
                'avg_leverage': stats['avg_leverage'],
                'salary_used': stats['salary_used'],
                'has_stack': stats['has_qb_stack'],
                'stack_correlation': stats.get('stack_correlation', 0),
                'players': ' | '.join(all_players)
            }
            
            export_data.append(row)
        
        # Save to CSV
        df = pd.DataFrame(export_data)
        df.to_csv(filename, index=False)
        
        return filename