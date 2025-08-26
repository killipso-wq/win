"""
Flask Application for DFS Championship System
Deployed on Render
"""

from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import csv
import io
import os
from datetime import datetime
import logging

# Import our modules
from dfs_championship_system import DFSChampionshipSystem
from dk_lineup_exporter import DKLineupExporter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Global system instance
system = None
exporter = None

def initialize_system():
    """Initialize the DFS system with data"""
    global system, exporter
    
    try:
        # Create system instance
        system = DFSChampionshipSystem()
        
        # Check if data files exist
        players_path = 'players.csv'
        defense_path = 'defense.csv'
        
        if os.path.exists(players_path) and os.path.exists(defense_path):
            # Load data files
            system.load_all_data(players_path, defense_path)
            
            # Initialize exporter
            exporter = DKLineupExporter(system)
            
            logger.info("System initialized successfully")
            return True
        else:
            logger.info("Data files not found - system ready for upload")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize system: {str(e)}")
        return False

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """System status check"""
    return jsonify({
        'status': 'ready' if system is not None else 'not_initialized',
        'players_loaded': len(system.players_df) if system and system.players_df is not None else 0,
        'defense_loaded': len(system.defense_df) if system and system.defense_df is not None else 0
    })

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Upload players.csv and defense.csv files"""
    global system, exporter
    
    try:
        # Check if files were uploaded
        if 'players' not in request.files or 'defense' not in request.files:
            return jsonify({'error': 'Both players.csv and defense.csv are required'}), 400
        
        players_file = request.files['players']
        defense_file = request.files['defense']
        
        # Save files
        players_file.save('players.csv')
        defense_file.save('defense.csv')
        
        # Initialize system with new data
        if initialize_system():
            return jsonify({
                'success': True,
                'message': 'Files uploaded and system initialized successfully',
                'players_count': len(system.players_df),
                'defense_count': len(system.defense_df)
            })
        else:
            return jsonify({'error': 'Failed to initialize system with uploaded data'}), 500
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze')
def analyze():
    """Analyze current slate"""
    if not system:
        return jsonify({'error': 'System not initialized. Please upload data files first.'}), 500
    
    try:
        analysis = system.analyze_slate_edge()
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/build', methods=['POST'])
def build():
    """Build a lineup"""
    if not system:
        return jsonify({'error': 'System not initialized. Please upload data files first.'}), 500
    
    try:
        data = request.json or {}
        strategy = data.get('strategy', 'balanced')
        lineup = system.build_gpp_lineup(strategy)
        return jsonify(lineup)
    except Exception as e:
        logger.error(f"Lineup build error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio', methods=['POST'])
def portfolio():
    """Generate portfolio of lineups"""
    if not system:
        return jsonify({'error': 'System not initialized. Please upload data files first.'}), 500
    
    try:
        data = request.json or {}
        count = int(data.get('count', 20))
        portfolio_data = system.generate_tournament_portfolio(count)
        return jsonify(portfolio_data)
    except Exception as e:
        logger.error(f"Portfolio generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export', methods=['POST'])
def export():
    """Export lineups to CSV"""
    if not system or not exporter:
        return jsonify({'error': 'System not initialized. Please upload data files first.'}), 500
    
    try:
        data = request.json or {}
        count = int(data.get('count', 20))
        strategy = data.get('strategy', 'mixed')
        
        # Generate lineups
        portfolio_data = system.generate_tournament_portfolio(count)
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # DraftKings header
        writer.writerow(['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST'])
        
        # Write each lineup
        for lineup_data in portfolio_data['lineups']:
            lineup = lineup_data['lineup']
            row = []
            row.append(lineup.get('QB', [''])[0])
            row.extend(lineup.get('RB', ['', ''])[:2])
            row.extend(lineup.get('WR', ['', '', ''])[:3])
            row.append(lineup.get('TE', [''])[0])
            row.append(lineup.get('FLEX', [''])[0])
            row.append(lineup.get('DST', [''])[0])
            writer.writerow(row)
        
        # Prepare file
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'dk_lineups_{count}_{timestamp}.csv'
        )
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stacks/<qb_name>')
def find_stacks(qb_name):
    """Find stacking options for a QB"""
    if not system:
        return jsonify({'error': 'System not initialized. Please upload data files first.'}), 500
    
    try:
        stacks = system.find_correlation_stacks(qb_name)
        return jsonify(stacks)
    except Exception as e:
        logger.error(f"Stack finding error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏆 DFS CHAMPIONSHIP SYSTEM 🏆")
    print("="*60)
    print("\n📊 System Status:")
    
    # Try to initialize with existing data
    if initialize_system():
        print(f"   Players Loaded: {len(system.players_df) if system.players_df is not None else 0}")
        print(f"   Defense Data: {len(system.defense_df) if system.defense_df is not None else 0}")
    else:
        print("   No data files found - ready for upload")
    
    print("\n🌐 Access the system at: http://localhost:5000")
    print("\n   Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
