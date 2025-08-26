"""
Main CLI for running week simulation from site players.csv
Orchestrates the entire pipeline: load data -> simulate -> calculate metrics -> output results
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

# Import our modules
from src.sim.game_simulator import GameSimulator
from src.projections.boom_score import BoomScoreCalculator
from src.projections.value_metrics import ValueMetricsCalculator
from src.projections.diagnostics import DiagnosticsCalculator

logger = logging.getLogger(__name__)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Run NFL DFS simulation from site players.csv')
    
    # Required arguments
    parser.add_argument('--season', type=int, required=True, help='Season (e.g., 2025)')
    parser.add_argument('--week', type=int, required=True, help='Week number')
    parser.add_argument('--players-site', type=str, required=True, help='Path to site players.csv')
    parser.add_argument('--team-priors', type=str, required=True, help='Path to team priors CSV')
    parser.add_argument('--player-priors', type=str, required=True, help='Path to player priors CSV')
    parser.add_argument('--boom-thresholds', type=str, required=True, help='Path to boom thresholds JSON')
    parser.add_argument('--out', type=str, required=True, help='Output directory')
    
    # Optional arguments
    parser.add_argument('--sims', type=int, default=10000, help='Number of simulations (default: 10000)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed (default: 42)')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Create output directory
    os.makedirs(args.out, exist_ok=True)
    
    # Run simulation
    run_simulation(args)

def run_simulation(args):
    """Run the complete simulation pipeline"""
    logger.info(f"Starting simulation for {args.season} Week {args.week}")
    
    # Load data
    logger.info("Loading data...")
    players_df = load_site_players(args.players_site)
    team_priors = pd.read_csv(args.team_priors)
    player_priors = pd.read_csv(args.player_priors)
    
    with open(args.boom_thresholds, 'r') as f:
        boom_thresholds = json.load(f)
    
    # Initialize components
    logger.info("Initializing simulation components...")
    simulator = GameSimulator(
        team_priors=team_priors,
        player_priors=player_priors,
        boom_thresholds=boom_thresholds,
        n_sims=args.sims,
        seed=args.seed
    )
    
    boom_calculator = BoomScoreCalculator(boom_thresholds)
    value_calculator = ValueMetricsCalculator()
    diagnostics_calculator = DiagnosticsCalculator()
    
    # Run simulation
    logger.info(f"Running {args.sims} simulations...")
    sim_results = simulator.simulate_week(players_df)
    
    # Calculate metrics
    logger.info("Calculating boom metrics...")
    boom_df = boom_calculator.calculate_boom_metrics(sim_results, players_df)
    
    logger.info("Calculating value metrics...")
    value_df = value_calculator.calculate_value_metrics(boom_df)
    
    logger.info("Calculating diagnostics...")
    diagnostics = diagnostics_calculator.calculate_diagnostics(boom_df, value_df)
    
    # Generate outputs
    logger.info("Generating output files...")
    generate_outputs(args, players_df, boom_df, value_df, diagnostics, sim_results)
    
    logger.info(f"Simulation complete! Outputs saved to {args.out}")

def load_site_players(filepath: str) -> pd.DataFrame:
    """Load and validate site players.csv"""
    df = pd.read_csv(filepath)
    
    # Validate required columns
    required_cols = ['PLAYER', 'POS', 'TEAM', 'OPP']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Normalize position column
    df['POS'] = df['POS'].str.upper()
    df.loc[df['POS'] == 'D', 'POS'] = 'DST'
    
    # Normalize ownership if present
    if 'RST%' in df.columns:
        # Convert to percentage if needed
        if df['RST%'].max() <= 1:
            df['RST%'] = df['RST%'] * 100
    
    # Handle missing values
    df['FPTS'] = pd.to_numeric(df.get('FPTS', 0), errors='coerce')
    df['SAL'] = pd.to_numeric(df.get('SAL', 0), errors='coerce')
    df['RST%'] = pd.to_numeric(df.get('RST%', 0), errors='coerce')
    df['O/U'] = pd.to_numeric(df.get('O/U', 44), errors='coerce')
    df['SPRD'] = pd.to_numeric(df.get('SPRD', 0), errors='coerce')
    
    logger.info(f"Loaded {len(df)} players from {filepath}")
    return df

def generate_outputs(args, players_df: pd.DataFrame, boom_df: pd.DataFrame, 
                    value_df: pd.DataFrame, diagnostics: Dict, sim_results: Dict):
    """Generate all output files"""
    
    # 1. sim_players.csv - Our projections
    sim_players = create_sim_players_output(players_df, sim_results)
    sim_players.to_csv(os.path.join(args.out, 'sim_players.csv'), index=False)
    
    # 2. compare.csv - Joined with site fields
    compare_df = create_compare_output(players_df, boom_df, value_df)
    compare_df.to_csv(os.path.join(args.out, 'compare.csv'), index=False)
    
    # 3. diagnostics_summary.csv
    diagnostics_df = pd.DataFrame([diagnostics])
    diagnostics_df.to_csv(os.path.join(args.out, 'diagnostics_summary.csv'), index=False)
    
    # 4. flags.csv - Notable discrepancies
    flags_df = create_flags_output(compare_df)
    flags_df.to_csv(os.path.join(args.out, 'flags.csv'), index=False)
    
    # 5. metadata.json
    metadata = create_metadata(args, players_df, sim_results)
    with open(os.path.join(args.out, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # 6. ZIP bundle
    create_zip_bundle(args.out)

def create_sim_players_output(players_df: pd.DataFrame, sim_results: Dict) -> pd.DataFrame:
    """Create sim_players.csv with our projections"""
    sim_data = []
    
    for _, player in players_df.iterrows():
        player_id = get_player_id(player)
        
        if player_id in sim_results:
            sim = sim_results[player_id]
            sim_data.append({
                'player_id': player_id,
                'PLAYER': player['PLAYER'],
                'POS': player['POS'],
                'TEAM': player['TEAM'],
                'OPP': player['OPP'],
                'sim_mean': sim['sim_mean'],
                'floor_p10': sim['p10'],
                'p75': sim['p75'],
                'ceiling_p90': sim['p90'],
                'p95': sim['p95'],
                'boom_prob': sim['boom_prob'],
                'rookie_fallback': False,
                'SAL': player.get('SAL', None)
            })
        else:
            # Fallback for players without simulation
            sim_data.append({
                'player_id': player_id,
                'PLAYER': player['PLAYER'],
                'POS': player['POS'],
                'TEAM': player['TEAM'],
                'OPP': player['OPP'],
                'sim_mean': player.get('FPTS', 10.0),
                'floor_p10': player.get('FPTS', 10.0) * 0.6,
                'p75': player.get('FPTS', 10.0) * 1.2,
                'ceiling_p90': player.get('FPTS', 10.0) * 1.5,
                'p95': player.get('FPTS', 10.0) * 1.8,
                'boom_prob': 0.1,
                'rookie_fallback': True,
                'SAL': player.get('SAL', None)
            })
    
    return pd.DataFrame(sim_data)

def create_compare_output(players_df: pd.DataFrame, boom_df: pd.DataFrame, 
                         value_df: pd.DataFrame) -> pd.DataFrame:
    """Create compare.csv with site vs sim comparison"""
    # Merge all data
    compare_df = players_df.merge(boom_df, on=['PLAYER', 'POS', 'TEAM', 'OPP'], how='left')
    compare_df = compare_df.merge(value_df, on='player_id', how='left')
    
    # Add comparison fields
    compare_df['site_fpts'] = compare_df['FPTS']
    compare_df['delta_mean'] = compare_df['sim_mean'] - compare_df['site_fpts']
    compare_df['pct_delta'] = compare_df['delta_mean'] / compare_df['site_fpts'].clip(lower=1)
    
    # Reorder columns
    columns = [
        'player_id', 'PLAYER', 'POS', 'TEAM', 'OPP',
        'site_fpts', 'sim_mean', 'delta_mean', 'pct_delta',
        'beat_site_prob', 'value_per_1k', 'ceil_per_1k',
        'boom_score', 'dart_flag', 'SAL', 'RST%'
    ]
    
    return compare_df[columns].fillna(0)

def create_flags_output(compare_df: pd.DataFrame) -> pd.DataFrame:
    """Create flags.csv with notable discrepancies"""
    flags = []
    
    # Top absolute deltas
    top_deltas = compare_df.nlargest(10, 'delta_mean')[['PLAYER', 'POS', 'delta_mean', 'pct_delta']]
    for _, row in top_deltas.iterrows():
        flags.append({
            'type': 'high_delta',
            'player': row['PLAYER'],
            'position': row['POS'],
            'value': row['delta_mean'],
            'description': f"High positive delta: {row['delta_mean']:.1f} points"
        })
    
    # Top negative deltas
    top_neg_deltas = compare_df.nsmallest(10, 'delta_mean')[['PLAYER', 'POS', 'delta_mean', 'pct_delta']]
    for _, row in top_neg_deltas.iterrows():
        flags.append({
            'type': 'low_delta',
            'player': row['PLAYER'],
            'position': row['POS'],
            'value': row['delta_mean'],
            'description': f"High negative delta: {row['delta_mean']:.1f} points"
        })
    
    # Dart throws
    darts = compare_df[compare_df['dart_flag'] == True]
    for _, row in darts.iterrows():
        flags.append({
            'type': 'dart_throw',
            'player': row['PLAYER'],
            'position': row['POS'],
            'value': row['boom_score'],
            'description': f"Dart throw: {row['boom_score']:.0f} boom score, {row['RST%']:.1f}% owned"
        })
    
    return pd.DataFrame(flags)

def create_metadata(args, players_df: pd.DataFrame, sim_results: Dict) -> Dict:
    """Create metadata.json with run information"""
    return {
        'run_id': f"{args.season}_week_{args.week}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'season': args.season,
        'week': args.week,
        'sims': args.sims,
        'seed': args.seed,
        'timestamp': datetime.now().isoformat(),
        'player_count': len(players_df),
        'positions': players_df['POS'].value_counts().to_dict(),
        'teams': players_df['TEAM'].nunique(),
        'games': players_df.groupby(['TEAM', 'OPP']).size().shape[0],
        'rookie_fallback_count': len([p for p in sim_results.values() if p.get('rookie_fallback', False)])
    }

def create_zip_bundle(output_dir: str):
    """Create ZIP bundle of all outputs"""
    import zipfile
    
    zip_path = os.path.join(output_dir, 'simulator_outputs.zip')
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for filename in ['sim_players.csv', 'compare.csv', 'diagnostics_summary.csv', 'flags.csv', 'metadata.json']:
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                zipf.write(filepath, filename)
    
    logger.info(f"Created ZIP bundle: {zip_path}")

def get_player_id(player: pd.Series) -> str:
    """Generate stable player ID"""
    from slugify import slugify
    
    name = slugify(player['PLAYER'].upper(), separator='_')
    team = player['TEAM']
    pos = player['POS']
    
    return f"{team}_{pos}_{name}"

if __name__ == '__main__':
    main()