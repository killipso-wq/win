#!/usr/bin/env python3
"""
Build Baseline from nfl_data_py
Creates team and player priors from 2023-2024 historical data
"""

import pandas as pd
import numpy as np
import argparse
import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

# Import nfl_data_py
try:
    import nfl_data_py as nfl
except ImportError:
    print("nfl_data_py not found. Install with: pip install nfl_data_py")
    exit(1)

logger = logging.getLogger(__name__)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Build baseline from nfl_data_py data')
    
    parser.add_argument('--start', type=int, default=2023, help='Start season (default: 2023)')
    parser.add_argument('--end', type=int, default=2024, help='End season (default: 2024)')
    parser.add_argument('--out', type=str, default='data/baseline', help='Output directory')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Create output directory
    os.makedirs(args.out, exist_ok=True)
    
    # Build baseline
    build_baseline(args)

def build_baseline(args):
    """Build complete baseline from nfl_data_py"""
    logger.info(f"Building baseline for {args.start}-{args.end}")
    
    # Load data
    logger.info("Loading nfl_data_py data...")
    weekly_data = load_weekly_data(args.start, args.end)
    
    # Build team priors
    logger.info("Building team priors...")
    team_priors = build_team_priors(weekly_data)
    team_priors.to_csv(os.path.join(args.out, 'team_priors.csv'), index=False)
    
    # Build player priors
    logger.info("Building player priors...")
    player_priors = build_player_priors(weekly_data)
    player_priors.to_csv(os.path.join(args.out, 'player_priors.csv'), index=False)
    
    # Build boom thresholds
    logger.info("Building boom thresholds...")
    boom_thresholds = build_boom_thresholds(weekly_data)
    with open(os.path.join(args.out, 'boom_thresholds.json'), 'w') as f:
        json.dump(boom_thresholds, f, indent=2)
    
    logger.info(f"Baseline complete! Files saved to {args.out}")

def load_weekly_data(start_year: int, end_year: int) -> pd.DataFrame:
    """Load weekly player data from nfl_data_py"""
    all_data = []
    
    for year in range(start_year, end_year + 1):
        logger.info(f"Loading {year} data...")
        try:
            # Load weekly stats
            weekly = nfl.import_weekly_data([year])
            all_data.append(weekly)
        except Exception as e:
            logger.warning(f"Could not load {year} data: {e}")
    
    if not all_data:
        raise ValueError("No data loaded from nfl_data_py")
    
    # Combine all years
    combined = pd.concat(all_data, ignore_index=True)
    
    # Filter for relevant columns and valid data
    required_cols = ['player_id', 'player_name', 'team', 'position', 'season', 'week']
    available_cols = [col for col in required_cols if col in combined.columns]
    
    if len(available_cols) < len(required_cols):
        logger.warning(f"Missing columns: {set(required_cols) - set(available_cols)}")
    
    # Add DK scoring
    combined = add_dk_scoring(combined)
    
    logger.info(f"Loaded {len(combined)} weekly records")
    return combined

def add_dk_scoring(df: pd.DataFrame) -> pd.DataFrame:
    """Add DraftKings scoring to weekly data"""
    # Initialize DK points column
    df['dk_points'] = 0.0
    
    # QB scoring
    qb_mask = df['position'] == 'QB'
    if 'passing_yards' in df.columns:
        df.loc[qb_mask, 'dk_points'] += df.loc[qb_mask, 'passing_yards'] * 0.04
    if 'passing_tds' in df.columns:
        df.loc[qb_mask, 'dk_points'] += df.loc[qb_mask, 'passing_tds'] * 4
    if 'interceptions' in df.columns:
        df.loc[qb_mask, 'dk_points'] += df.loc[qb_mask, 'interceptions'] * -1
    if 'rushing_yards' in df.columns:
        df.loc[qb_mask, 'dk_points'] += df.loc[qb_mask, 'rushing_yards'] * 0.1
    if 'rushing_tds' in df.columns:
        df.loc[qb_mask, 'dk_points'] += df.loc[qb_mask, 'rushing_tds'] * 6
    
    # RB scoring
    rb_mask = df['position'] == 'RB'
    if 'rushing_yards' in df.columns:
        df.loc[rb_mask, 'dk_points'] += df.loc[rb_mask, 'rushing_yards'] * 0.1
    if 'rushing_tds' in df.columns:
        df.loc[rb_mask, 'dk_points'] += df.loc[rb_mask, 'rushing_tds'] * 6
    if 'receiving_yards' in df.columns:
        df.loc[rb_mask, 'dk_points'] += df.loc[rb_mask, 'receiving_yards'] * 1.0
    if 'receiving_tds' in df.columns:
        df.loc[rb_mask, 'dk_points'] += df.loc[rb_mask, 'receiving_tds'] * 6
    if 'receptions' in df.columns:
        df.loc[rb_mask, 'dk_points'] += df.loc[rb_mask, 'receptions'] * 1.0
    
    # WR scoring
    wr_mask = df['position'] == 'WR'
    if 'receiving_yards' in df.columns:
        df.loc[wr_mask, 'dk_points'] += df.loc[wr_mask, 'receiving_yards'] * 1.0
    if 'receiving_tds' in df.columns:
        df.loc[wr_mask, 'dk_points'] += df.loc[wr_mask, 'receiving_tds'] * 6
    if 'receptions' in df.columns:
        df.loc[wr_mask, 'dk_points'] += df.loc[wr_mask, 'receptions'] * 1.0
    if 'rushing_yards' in df.columns:
        df.loc[wr_mask, 'dk_points'] += df.loc[wr_mask, 'rushing_yards'] * 0.1
    if 'rushing_tds' in df.columns:
        df.loc[wr_mask, 'dk_points'] += df.loc[wr_mask, 'rushing_tds'] * 6
    
    # TE scoring
    te_mask = df['position'] == 'TE'
    if 'receiving_yards' in df.columns:
        df.loc[te_mask, 'dk_points'] += df.loc[te_mask, 'receiving_yards'] * 1.0
    if 'receiving_tds' in df.columns:
        df.loc[te_mask, 'dk_points'] += df.loc[te_mask, 'receiving_tds'] * 6
    if 'receptions' in df.columns:
        df.loc[te_mask, 'dk_points'] += df.loc[te_mask, 'receptions'] * 1.0
    if 'rushing_yards' in df.columns:
        df.loc[te_mask, 'dk_points'] += df.loc[te_mask, 'rushing_yards'] * 0.1
    if 'rushing_tds' in df.columns:
        df.loc[te_mask, 'dk_points'] += df.loc[te_mask, 'rushing_tds'] * 6
    
    return df

def build_team_priors(weekly_data: pd.DataFrame) -> pd.DataFrame:
    """Build team-level priors from weekly data"""
    team_stats = []
    
    for team in weekly_data['team'].unique():
        team_data = weekly_data[weekly_data['team'] == team]
        
        # Calculate team-level metrics
        team_stats.append({
            'team': team,
            'plays_per_game': team_data.groupby(['season', 'week']).size().mean(),
            'neutral_xpass': 0.6,  # Placeholder - would need play-by-play data
            'proe_neutral': 0.0,   # Placeholder
            'epa_per_play': team_data['dk_points'].mean() / 10,  # Rough approximation
            'success_rate': 0.5,   # Placeholder
            'games_played': len(team_data.groupby(['season', 'week']))
        })
    
    return pd.DataFrame(team_stats)

def build_player_priors(weekly_data: pd.DataFrame) -> pd.DataFrame:
    """Build player-level priors from weekly data"""
    player_stats = []
    
    for player_id in weekly_data['player_id'].unique():
        player_data = weekly_data[weekly_data['player_id'] == player_id]
        
        if len(player_data) < 3:  # Need minimum games for priors
            continue
        
        position = player_data['position'].iloc[0]
        player_name = player_data['player_name'].iloc[0]
        team = player_data['team'].iloc[0]
        
        # Calculate position-specific priors
        if position == 'QB':
            priors = calculate_qb_priors(player_data)
        elif position in ['RB', 'WR', 'TE']:
            priors = calculate_skill_player_priors(player_data, position)
        else:
            continue  # Skip other positions for now
        
        player_stats.append({
            'player_id': player_id,
            'name': player_name,
            'team': team,
            'position': position,
            'games_played': len(player_data),
            **priors
        })
    
    return pd.DataFrame(player_stats)

def calculate_qb_priors(player_data: pd.DataFrame) -> Dict:
    """Calculate QB-specific priors"""
    return {
        'pass_attempts_per_game': player_data.get('passing_attempts', pd.Series([35])).mean(),
        'pass_yards_per_attempt': (
            player_data.get('passing_yards', pd.Series([0])).sum() / 
            player_data.get('passing_attempts', pd.Series([1])).sum()
        ),
        'pass_td_rate': (
            player_data.get('passing_tds', pd.Series([0])).sum() / 
            player_data.get('passing_attempts', pd.Series([1])).sum()
        ),
        'int_rate': (
            player_data.get('interceptions', pd.Series([0])).sum() / 
            player_data.get('passing_attempts', pd.Series([1])).sum()
        ),
        'rush_attempts_per_game': player_data.get('rushing_attempts', pd.Series([3])).mean(),
        'rush_yards_per_attempt': (
            player_data.get('rushing_yards', pd.Series([0])).sum() / 
            player_data.get('rushing_attempts', pd.Series([1])).sum()
        ),
        'rush_td_rate': (
            player_data.get('rushing_tds', pd.Series([0])).sum() / 
            player_data.get('rushing_attempts', pd.Series([1])).sum()
        ),
        'dk_points_per_game': player_data['dk_points'].mean()
    }

def calculate_skill_player_priors(player_data: pd.DataFrame, position: str) -> Dict:
    """Calculate RB/WR/TE priors"""
    return {
        'targets_per_game': player_data.get('targets', pd.Series([5])).mean(),
        'carries_per_game': player_data.get('rushing_attempts', pd.Series([10])).mean(),
        'yards_per_target': (
            player_data.get('receiving_yards', pd.Series([0])).sum() / 
            player_data.get('targets', pd.Series([1])).sum()
        ),
        'yards_per_carry': (
            player_data.get('rushing_yards', pd.Series([0])).sum() / 
            player_data.get('rushing_attempts', pd.Series([1])).sum()
        ),
        'td_rate': (
            (player_data.get('receiving_tds', pd.Series([0])).sum() + 
             player_data.get('rushing_tds', pd.Series([0])).sum()) / 
            (player_data.get('targets', pd.Series([1])).sum() + 
             player_data.get('rushing_attempts', pd.Series([1])).sum())
        ),
        'dk_points_per_game': player_data['dk_points'].mean()
    }

def build_boom_thresholds(weekly_data: pd.DataFrame) -> Dict:
    """Build position-specific boom thresholds"""
    thresholds = {}
    
    for position in ['QB', 'RB', 'WR', 'TE']:
        pos_data = weekly_data[weekly_data['position'] == position]
        
        if len(pos_data) > 0:
            # Use p90 of DK points as boom threshold
            threshold = pos_data['dk_points'].quantile(0.90)
            thresholds[position] = float(threshold)
        else:
            # Fallback thresholds
            fallback_thresholds = {
                'QB': 25.0,
                'RB': 20.0,
                'WR': 18.0,
                'TE': 15.0
            }
            thresholds[position] = fallback_thresholds.get(position, 15.0)
    
    return thresholds

if __name__ == '__main__':
    main()