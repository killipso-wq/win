"""
Flask API Backend for DFS Championship System
"""

from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
from datetime import datetime
import json
import logging

# Import our modules
from dfs_championship_system import DFSChampionshipSystem
from dk_lineup_exporter import DKLineupExporter
from self_learning_analyzer import IntelligentGPPLearner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Global system instance
system = None
exporter = None
learner = None

def initialize_system():
    """Initialize the DFS system with data"""
    global system, exporter, learner
    
    try:
        # Create system instance
        system = DFSChampionshipSystem()
        
        # Load data files
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data')
        system.load_all_data(
            os.path.join(data_path, 'players.csv'),
            os.path.join(data_path, 'correlations.csv'),
            os.path.join(data_path, 'defense.csv')
        )
        
        # Initialize subsystems
        exporter = DKLineupExporter(system)
        learner = IntelligentGPPLearner(system)
        
        logger.info("System initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {str(e)}")
        return False

# Routes
@app.route('/')
def index():
    """Serve the main UI"""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """Check system status"""
    return jsonify({
        'status': 'ready' if system is not None else 'not_initialized',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/slate-analysis')
def slate_analysis():
    """Get comprehensive slate analysis"""
    if not system:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        analysis = system.analyze_slate_edge()
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Slate analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/build-lineup', methods=['POST'])
def build_lineup():
    """Build a single lineup"""
    if not system:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        data = request.json
        strategy = data.get('strategy', 'balanced')
        
        lineup = system.build_gpp_lineup(strategy)
        return jsonify(lineup)
        
    except Exception as e:
        logger.error(f"Lineup build error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/find-stacks/<qb_name>')
def find_stacks(qb_name):
    """Find stacking options for a QB"""
    if not system:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        stacks = system.find_correlation_stacks(qb_name)
        return jsonify(stacks)
    except Exception as e:
        logger.error(f"Stack finding error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-portfolio', methods=['POST'])
def generate_portfolio():
    """Generate multiple lineups"""
    if not system:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        data = request.json
        n_lineups = int(data.get('count', 20))
        
        portfolio = system.generate_tournament_portfolio(n_lineups)
        return jsonify(portfolio)
        
    except Exception as e:
        logger.error(f"Portfolio generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-lineups', methods=['POST'])
def export_lineups():
    """Export lineups to DraftKings CSV"""
    if not system or not exporter:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        data = request.json
        n_lineups = int(data.get('count', 20))
        strategy = data.get('strategy', 'mixed')
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dk_upload_{n_lineups}_{timestamp}.csv"
        filepath = os.path.join('exports', filename)
        
        # Ensure exports directory exists
        os.makedirs('exports', exist_ok=True)
        
        # Export lineups
        exporter.export_top_lineups(
            n_lineups=n_lineups,
            strategy=strategy,
            filename=filepath
        )
        
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-winners', methods=['POST'])
def analyze_winners():
    """Analyze winning lineups for learning"""
    if not system or not learner:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        data = request.json
        week = data.get('week')
        lineups = data.get('lineups', [])
        
        # Convert lineup format
        winning_lineups = []
        for lineup in lineups:
            winning_lineups.append({
                'place': lineup['place'],
                'players': [
                    {'name': p, 'position': pos}
                    for p, pos in zip(lineup['players'], lineup['positions'])
                ]
            })
        
        # Run analysis
        analysis = learner.analyze_winning_lineups(
            week=week,
            winning_lineups=winning_lineups,
            my_lineups=[],  # Would need to load your lineups
            slate_context={}  # Would need slate results
        )
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Winner analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Initialize on startup
@app.before_first_request
def startup():
    """Initialize system on first request"""
    initialize_system()

if __name__ == '__main__':
    app.run(debug=True, port=5000)