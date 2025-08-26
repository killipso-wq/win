"""
Flask Application for MonteCarloNFLSIM with Championship Features
"""

from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import csv
import io
from datetime import datetime
from enhanced_championship_system import EnhancedChampionshipSystem

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Initialize system
system = EnhancedChampionshipSystem()

# Load data on startup
try:
    system.load_all_data('players.csv', 'defense.csv')
    print("✅ Data loaded successfully!")
except Exception as e:
    print(f"⚠️ Warning: Could not load data: {e}")

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """System status check"""
    return jsonify({
        'status': 'ready' if system.players_df is not None else 'not_initialized',
        'players_loaded': len(system.players_df) if system.players_df is not None else 0,
        'defense_loaded': len(system.defense_df) if system.defense_df is not None else 0
    })

@app.route('/api/analyze')
def analyze():
    """Analyze current slate"""
    try:
        analysis = system.analyze_slate_edge()
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/build', methods=['POST'])
def build():
    """Build a lineup"""
    try:
        data = request.json or {}
        strategy = data.get('strategy', 'balanced')
        lineup = system.build_gpp_lineup(strategy)
        return jsonify(lineup)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio', methods=['POST'])
def portfolio():
    """Generate portfolio of lineups"""
    try:
        data = request.json or {}
        count = int(data.get('count', 20))
        portfolio_data = system.generate_tournament_portfolio(count)
        return jsonify(portfolio_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export', methods=['POST'])
def export():
    """Export lineups to CSV"""
    try:
        data = request.json or {}
        count = int(data.get('count', 20))
        
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
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏆 MONTECARLO NFL SIMULATOR - CHAMPIONSHIP EDITION 🏆")
    print("="*60)
    print("\n📊 System Status:")
    print(f"   Players Loaded: {len(system.players_df) if system.players_df is not None else 0}")
    print(f"   Defense Data: {len(system.defense_df) if system.defense_df is not None else 0}")
    print("\n🌐 Access the system at: http://localhost:5000")
    print("\n   Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
