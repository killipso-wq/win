"""
NFL GPP Simulator - Streamlit App
Main UI for uploading players.csv and running Monte Carlo simulations
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

# Import our modules
from src.sim.game_simulator import GameSimulator
from src.projections.boom_score import BoomScoreCalculator
from src.projections.value_metrics import ValueMetricsCalculator
from src.projections.diagnostics import DiagnosticsCalculator

# Page config
st.set_page_config(
    page_title="NFL GPP Simulator",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'sim_results' not in st.session_state:
    st.session_state.sim_results = None
if 'players_df' not in st.session_state:
    st.session_state.players_df = None

def main():
    """Main Streamlit app"""
    st.title("🏈 NFL GPP Simulator")
    st.markdown("Monte Carlo simulation for NFL DFS projections")
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        
        # Simulation parameters
        n_sims = st.slider("Number of Simulations", 1000, 50000, 10000, 1000)
        seed = st.number_input("Random Seed", value=42, min_value=1, max_value=999999)
        
        # Load baseline data
        st.subheader("Baseline Data")
        baseline_path = st.text_input("Baseline Path", value="data/baseline")
        
        if st.button("Load Baseline"):
            load_baseline_data(baseline_path)
        
        # Clear cache
        if st.button("Clear Cached Results"):
            st.session_state.sim_results = None
            st.session_state.players_df = None
            st.success("Cache cleared!")
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["📊 Simulator", "📈 Analysis", "📁 Downloads"])
    
    with tab1:
        simulator_tab(n_sims, seed, baseline_path)
    
    with tab2:
        analysis_tab()
    
    with tab3:
        downloads_tab()

def simulator_tab(n_sims, seed, baseline_path):
    """Simulator tab with file upload and run controls"""
    st.header("Monte Carlo Simulator")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload players.csv", 
        type=['csv'],
        help="Upload your site players.csv file with PLAYER, POS, TEAM, OPP columns"
    )
    
    if uploaded_file is not None:
        # Load and validate data
        players_df = load_and_validate_players(uploaded_file)
        
        if players_df is not None:
            st.session_state.players_df = players_df
            
            # Show column mapping
            show_column_mapping(players_df)
            
            # Show data preview
            show_data_preview(players_df)
            
            # Run simulation button
            if st.button("🚀 Run Simulation", type="primary"):
                with st.spinner("Running Monte Carlo simulation..."):
                    run_simulation(players_df, n_sims, seed, baseline_path)

def load_and_validate_players(uploaded_file):
    """Load and validate uploaded players.csv"""
    try:
        df = pd.read_csv(uploaded_file)
        
        # Validate required columns
        required_cols = ['PLAYER', 'POS', 'TEAM', 'OPP']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"Missing required columns: {missing_cols}")
            return None
        
        # Normalize position column
        df['POS'] = df['POS'].str.upper()
        df.loc[df['POS'] == 'D', 'POS'] = 'DST'
        
        # Normalize ownership if present
        if 'RST%' in df.columns:
            if df['RST%'].max() <= 1:
                df['RST%'] = df['RST%'] * 100
        
        # Handle missing values
        df['FPTS'] = pd.to_numeric(df.get('FPTS', 0), errors='coerce')
        df['SAL'] = pd.to_numeric(df.get('SAL', 0), errors='coerce')
        df['RST%'] = pd.to_numeric(df.get('RST%', 0), errors='coerce')
        df['O/U'] = pd.to_numeric(df.get('O/U', 44), errors='coerce')
        df['SPRD'] = pd.to_numeric(df.get('SPRD', 0), errors='coerce')
        
        st.success(f"✅ Loaded {len(df)} players successfully!")
        return df
        
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

def show_column_mapping(df):
    """Show detected column mapping"""
    st.subheader("📋 Column Mapping")
    
    mapping_data = []
    for col in df.columns:
        mapping_data.append({
            'Column': col,
            'Type': str(df[col].dtype),
            'Non-Null': df[col].count(),
            'Sample Values': ', '.join(str(x) for x in df[col].dropna().head(3).tolist())
        })
    
    mapping_df = pd.DataFrame(mapping_data)
    st.dataframe(mapping_df, use_container_width=True)

def show_data_preview(df):
    """Show data preview with filters"""
    st.subheader("📊 Data Preview")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        position_filter = st.multiselect(
            "Position", 
            options=df['POS'].unique(),
            default=df['POS'].unique()
        )
    
    with col2:
        team_filter = st.multiselect(
            "Team",
            options=df['TEAM'].unique(),
            default=df['TEAM'].unique()
        )
    
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            options=['PLAYER', 'POS', 'TEAM', 'FPTS', 'SAL', 'RST%']
        )
    
    # Filter data
    filtered_df = df[
        (df['POS'].isin(position_filter)) &
        (df['TEAM'].isin(team_filter))
    ].sort_values(sort_by)
    
    st.dataframe(filtered_df, use_container_width=True)

def load_baseline_data(baseline_path):
    """Load baseline data from files"""
    try:
        # Check if baseline files exist
        team_priors_path = os.path.join(baseline_path, 'team_priors.csv')
        player_priors_path = os.path.join(baseline_path, 'player_priors.csv')
        boom_thresholds_path = os.path.join(baseline_path, 'boom_thresholds.json')
        
        if not all(os.path.exists(p) for p in [team_priors_path, player_priors_path, boom_thresholds_path]):
            st.error("Baseline files not found. Please run the baseline builder first.")
            st.info("Run: python scripts/build_baseline.py --start 2023 --end 2024 --out data/baseline")
            return False
        
        # Load data
        team_priors = pd.read_csv(team_priors_path)
        player_priors = pd.read_csv(player_priors_path)
        
        with open(boom_thresholds_path, 'r') as f:
            boom_thresholds = json.load(f)
        
        # Store in session state
        st.session_state.team_priors = team_priors
        st.session_state.player_priors = player_priors
        st.session_state.boom_thresholds = boom_thresholds
        
        st.success(f"✅ Loaded baseline data: {len(team_priors)} teams, {len(player_priors)} players")
        return True
        
    except Exception as e:
        st.error(f"Error loading baseline: {str(e)}")
        return False

def run_simulation(players_df, n_sims, seed, baseline_path):
    """Run the Monte Carlo simulation"""
    try:
        # Load baseline if not already loaded
        if 'team_priors' not in st.session_state:
            if not load_baseline_data(baseline_path):
                return
        
        # Initialize simulator
        simulator = GameSimulator(
            team_priors=st.session_state.team_priors,
            player_priors=st.session_state.player_priors,
            boom_thresholds=st.session_state.boom_thresholds,
            n_sims=n_sims,
            seed=seed
        )
        
        # Run simulation
        sim_results = simulator.simulate_week(players_df)
        
        # Calculate metrics
        boom_calculator = BoomScoreCalculator(st.session_state.boom_thresholds)
        value_calculator = ValueMetricsCalculator()
        diagnostics_calculator = DiagnosticsCalculator()
        
        boom_df = boom_calculator.calculate_boom_metrics(sim_results, players_df)
        value_df = value_calculator.calculate_value_metrics(boom_df)
        diagnostics = diagnostics_calculator.calculate_diagnostics(boom_df, value_df)
        
        # Store results
        st.session_state.sim_results = sim_results
        st.session_state.boom_df = boom_df
        st.session_state.value_df = value_df
        st.session_state.diagnostics = diagnostics
        
        st.success("🎉 Simulation complete!")
        
        # Show summary
        show_simulation_summary(diagnostics)
        
    except Exception as e:
        st.error(f"Simulation failed: {str(e)}")

def show_simulation_summary(diagnostics):
    """Show simulation summary"""
    st.subheader("📈 Simulation Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Players", diagnostics.get('total_players', 0))
    
    with col2:
        st.metric("Non-Rookie Players", diagnostics.get('non_rookie_count', 0))
    
    with col3:
        mae = diagnostics.get('overall_mae', 0)
        st.metric("Overall MAE", f"{mae:.2f}")
    
    with col4:
        correlation = diagnostics.get('overall_correlation', 0)
        st.metric("Correlation", f"{correlation:.3f}")

def analysis_tab():
    """Analysis tab with detailed results"""
    st.header("📈 Analysis Results")
    
    if st.session_state.sim_results is None:
        st.info("Run a simulation first to see analysis results.")
        return
    
    # Tabs for different analysis views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Compare", "🎯 Boom Scores", "💰 Value", "📋 Diagnostics"])
    
    with tab1:
        show_compare_analysis()
    
    with tab2:
        show_boom_analysis()
    
    with tab3:
        show_value_analysis()
    
    with tab4:
        show_diagnostics_analysis()

def show_compare_analysis():
    """Show comparison analysis"""
    st.subheader("Site vs Simulation Comparison")
    
    # Create comparison dataframe
    compare_df = create_compare_dataframe()
    
    if compare_df is not None:
        # Filters
        col1, col2 = st.columns(2)
        
        with col1:
            position_filter = st.multiselect(
                "Position",
                options=compare_df['POS'].unique(),
                default=compare_df['POS'].unique(),
                key="compare_pos"
            )
        
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                options=['delta_mean', 'pct_delta', 'sim_mean', 'site_fpts'],
                key="compare_sort"
            )
        
        # Filter and display
        filtered_df = compare_df[compare_df['POS'].isin(position_filter)].sort_values(sort_by, ascending=False)
        st.dataframe(filtered_df, use_container_width=True)

def show_boom_analysis():
    """Show boom score analysis"""
    st.subheader("🎯 Boom Score Analysis")
    
    if 'boom_df' in st.session_state:
        boom_df = st.session_state.boom_df
        
        # Top boom scores
        st.write("**Top Boom Scores by Position:**")
        
        for position in boom_df['position'].unique():
            pos_data = boom_df[boom_df['position'] == position].nlargest(5, 'boom_score')
            
            st.write(f"**{position}:**")
            for _, player in pos_data.iterrows():
                st.write(f"- {player['player']}: {player['boom_score']:.0f} score, {player['boom_prob']:.1%} boom prob")
        
        # Dart throws
        darts = boom_df[boom_df['dart_flag'] == True]
        if len(darts) > 0:
            st.write("**🎯 Dart Throws (≤5% owned, ≥70 boom score):**")
            for _, player in darts.iterrows():
                st.write(f"- {player['player']} ({player['position']}): {player['boom_score']:.0f} score, {player['ownership']:.1f}% owned")

def show_value_analysis():
    """Show value analysis"""
    st.subheader("💰 Value Analysis")
    
    if 'value_df' in st.session_state and 'boom_df' in st.session_state:
        value_df = st.session_state.value_df
        boom_df = st.session_state.boom_df
        
        # Merge data
        analysis_df = boom_df.merge(value_df, on='player_id', how='left')
        
        # Top value plays
        st.write("**Top Value Plays (points per $1k salary):**")
        
        for position in analysis_df['position'].unique():
            pos_data = analysis_df[analysis_df['position'] == position]
            pos_data = pos_data[pos_data['value_per_1k'].notna()].nlargest(3, 'value_per_1k')
            
            st.write(f"**{position}:**")
            for _, player in pos_data.iterrows():
                st.write(f"- {player['player']}: {player['value_per_1k']:.2f} pts/$1k")

def show_diagnostics_analysis():
    """Show diagnostics analysis"""
    st.subheader("📋 Diagnostics")
    
    if 'diagnostics' in st.session_state:
        diagnostics = st.session_state.diagnostics
        
        # Overall metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("MAE", f"{diagnostics.get('overall_mae', 0):.2f}")
        
        with col2:
            st.metric("RMSE", f"{diagnostics.get('overall_rmse', 0):.2f}")
        
        with col3:
            st.metric("Correlation", f"{diagnostics.get('overall_correlation', 0):.3f}")
        
        # Position-specific metrics
        st.write("**Position-Specific Metrics:**")
        
        positions = ['QB', 'RB', 'WR', 'TE']
        for pos in positions:
            pos_mae = diagnostics.get(f'{pos.lower()}_mae', 0)
            pos_corr = diagnostics.get(f'{pos.lower()}_correlation', 0)
            pos_count = diagnostics.get(f'{pos.lower()}_count', 0)
            
            if pos_count > 0:
                st.write(f"**{pos}:** MAE={pos_mae:.2f}, Corr={pos_corr:.3f}, Count={pos_count}")

def create_compare_dataframe():
    """Create comparison dataframe"""
    if (st.session_state.players_df is not None and 
        'boom_df' in st.session_state and 
        'value_df' in st.session_state):
        
        players_df = st.session_state.players_df
        boom_df = st.session_state.boom_df
        value_df = st.session_state.value_df
        
        # Merge data
        compare_df = players_df.merge(boom_df, on=['PLAYER', 'POS', 'TEAM', 'OPP'], how='left')
        compare_df = compare_df.merge(value_df, on='player_id', how='left')
        
        # Add comparison fields
        compare_df['site_fpts'] = compare_df['FPTS']
        compare_df['delta_mean'] = compare_df['sim_mean'] - compare_df['site_fpts']
        compare_df['pct_delta'] = compare_df['delta_mean'] / compare_df['site_fpts'].clip(lower=1)
        
        return compare_df
    
    return None

def downloads_tab():
    """Downloads tab with file export options"""
    st.header("📁 Downloads")
    
    if st.session_state.sim_results is None:
        st.info("Run a simulation first to download results.")
        return
    
    # Individual file downloads
    st.subheader("Individual Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Download sim_players.csv"):
            download_sim_players()
        
        if st.button("📈 Download compare.csv"):
            download_compare()
    
    with col2:
        if st.button("📋 Download diagnostics.csv"):
            download_diagnostics()
        
        if st.button("🚩 Download flags.csv"):
            download_flags()
    
    # ZIP bundle
    st.subheader("📦 Complete Bundle")
    if st.button("📦 Download All Files (ZIP)", type="primary"):
        download_zip_bundle()

def download_sim_players():
    """Download sim_players.csv"""
    if st.session_state.players_df is not None and st.session_state.sim_results is not None:
        sim_players = create_sim_players_output()
        csv = sim_players.to_csv(index=False)
        st.download_button(
            label="Click to download",
            data=csv,
            file_name="sim_players.csv",
            mime="text/csv"
        )

def download_compare():
    """Download compare.csv"""
    compare_df = create_compare_dataframe()
    if compare_df is not None:
        csv = compare_df.to_csv(index=False)
        st.download_button(
            label="Click to download",
            data=csv,
            file_name="compare.csv",
            mime="text/csv"
        )

def download_diagnostics():
    """Download diagnostics.csv"""
    if 'diagnostics' in st.session_state:
        diagnostics_df = pd.DataFrame([st.session_state.diagnostics])
        csv = diagnostics_df.to_csv(index=False)
        st.download_button(
            label="Click to download",
            data=csv,
            file_name="diagnostics_summary.csv",
            mime="text/csv"
        )

def download_flags():
    """Download flags.csv"""
    compare_df = create_compare_dataframe()
    if compare_df is not None:
        flags_df = create_flags_output(compare_df)
        csv = flags_df.to_csv(index=False)
        st.download_button(
            label="Click to download",
            data=csv,
            file_name="flags.csv",
            mime="text/csv"
        )

def download_zip_bundle():
    """Download ZIP bundle"""
    # Create temporary files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create all output files
        sim_players = create_sim_players_output()
        sim_players.to_csv(os.path.join(temp_dir, 'sim_players.csv'), index=False)
        
        compare_df = create_compare_dataframe()
        if compare_df is not None:
            compare_df.to_csv(os.path.join(temp_dir, 'compare.csv'), index=False)
        
        if 'diagnostics' in st.session_state:
            diagnostics_df = pd.DataFrame([st.session_state.diagnostics])
            diagnostics_df.to_csv(os.path.join(temp_dir, 'diagnostics_summary.csv'), index=False)
        
        if compare_df is not None:
            flags_df = create_flags_output(compare_df)
            flags_df.to_csv(os.path.join(temp_dir, 'flags.csv'), index=False)
        
        # Create metadata
        metadata = create_metadata()
        with open(os.path.join(temp_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create ZIP
        zip_path = os.path.join(temp_dir, 'simulator_outputs.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename in os.listdir(temp_dir):
                if filename != 'simulator_outputs.zip':
                    zipf.write(os.path.join(temp_dir, filename), filename)
        
        # Download
        with open(zip_path, 'rb') as f:
            st.download_button(
                label="Click to download ZIP",
                data=f.read(),
                file_name="simulator_outputs.zip",
                mime="application/zip"
            )

def create_sim_players_output():
    """Create sim_players.csv output"""
    players_df = st.session_state.players_df
    sim_results = st.session_state.sim_results
    
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
    
    return pd.DataFrame(sim_data)

def create_flags_output(compare_df):
    """Create flags.csv output"""
    flags = []
    
    # Top deltas
    top_deltas = compare_df.nlargest(10, 'delta_mean')[['PLAYER', 'POS', 'delta_mean', 'pct_delta']]
    for _, row in top_deltas.iterrows():
        flags.append({
            'type': 'high_delta',
            'player': row['PLAYER'],
            'position': row['POS'],
            'value': row['delta_mean'],
            'description': f"High positive delta: {row['delta_mean']:.1f} points"
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

def create_metadata():
    """Create metadata.json"""
    return {
        'run_id': f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'timestamp': datetime.now().isoformat(),
        'player_count': len(st.session_state.players_df) if st.session_state.players_df is not None else 0,
        'simulations': 10000,  # Default
        'seed': 42  # Default
    }

def get_player_id(player):
    """Generate stable player ID"""
    from slugify import slugify
    
    name = slugify(player['PLAYER'].upper(), separator='_')
    team = player['TEAM']
    pos = player['POS']
    
    return f"{team}_{pos}_{name}"

if __name__ == "__main__":
    main()
