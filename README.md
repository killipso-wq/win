# 🏆 DFS Championship System

Advanced GPP (Guaranteed Prize Pool) optimization system for Daily Fantasy Sports tournaments. This system integrates defensive matchups, correlation analysis, and win probability ranking to generate tournament-winning lineups.

## 🚀 Features

- **GPP Optimization**: Tournament-winning strategies with ownership leverage
- **Defense Integration**: Matchup-based player projection adjustments
- **Correlation Stacking**: QB-WR-TE game stacks and bring-back plays
- **Win Probability Ranking**: Optimizes for first place, not median finish
- **Portfolio Generation**: Multi-lineup strategies with exposure management
- **DraftKings Export**: Ready-to-upload CSV format
- **Modern Web UI**: File upload, real-time analysis, and export functionality

## 📋 Requirements

- Python 3.8+
- Flask 2.3.3
- Pandas 2.0.3
- NumPy 1.25.2

## 🛠️ Installation & Deployment

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dfs-championship-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the system**
   - Open your browser to `http://localhost:5000`
   - Upload your `players.csv` and `defense.csv` files
   - Start building optimized lineups!

### Render Deployment

1. **Create a new Web Service on Render**
   - Connect your GitHub repository
   - Choose Python as the runtime
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `gunicorn app:app`

2. **Environment Variables** (optional)
   - `PORT`: Render will set this automatically
   - `SECRET_KEY`: Set a secure secret key for Flask

3. **Deploy**
   - Render will automatically deploy your application
   - Access your live URL provided by Render

## 📁 Data Files

The system requires two CSV files:

### players.csv
Required columns:
- `player`: Player name
- `position`: Position (QB, RB, WR, TE, DST)
- `team`: Team abbreviation
- `salary`: DraftKings salary
- `projection`: Projected fantasy points
- `boom_score`: Ceiling projection
- `Rst%`: Ownership percentage

### defense.csv
Required columns:
- `Team`: Team abbreviation
- `OPP`: Opponent abbreviation
- `O/U`: Game over/under total
- `Spread`: Point spread
- `Points Against`: Points allowed per game
- `Yards Against`: Yards allowed per game
- `Sacks`: Sacks per game
- `Int`: Interceptions per game

## 🎯 Usage

1. **Upload Data**: Upload your `players.csv` and `defense.csv` files
2. **Slate Analysis**: Analyze the current slate for key edges
3. **Build Lineups**: Generate single lineups with different strategies
4. **Portfolio Generation**: Create multiple lineups for tournaments
5. **Export**: Download DraftKings-ready CSV files

## 🏗️ System Architecture

### Core Components

- **`dfs_championship_system.py`**: Main system with GPP optimization
- **`gpp_win_probability.py`**: Tournament win probability ranking
- **`defense_integration.py`**: Defensive matchup integration
- **`dk_lineup_exporter.py`**: DraftKings CSV export functionality
- **`app.py`**: Flask web application
- **`templates/index.html`**: Modern web interface

### Key Features

- **Ownership Leverage**: Identifies low-owned high-upside plays
- **Correlation Analysis**: QB-WR-TE stacking and game stacks
- **Defensive Adjustments**: Position-specific matchup ratings
- **Portfolio Diversity**: Exposure management and lineup uniqueness
- **Win Probability**: Optimizes for tournament wins, not median finish

## 📊 Strategies

- **Balanced**: Mix of chalk and leverage plays
- **Leverage**: Focus on low-owned upside plays
- **Contrarian**: Alternative game narratives
- **Stars & Scrubs**: Pay up for stars, punt on value plays

## 🔧 API Endpoints

- `GET /api/status`: System status check
- `POST /api/upload`: Upload data files
- `GET /api/analyze`: Slate analysis
- `POST /api/build`: Build single lineup
- `POST /api/portfolio`: Generate portfolio
- `POST /api/export`: Export to CSV
- `GET /api/stacks/<qb_name>`: Find stacking options

## 📈 Performance

The system is optimized for:
- **Speed**: Efficient algorithms for quick lineup generation
- **Accuracy**: Advanced correlation and defensive modeling
- **Scalability**: Handles large player pools and multiple lineups
- **Reliability**: Robust error handling and validation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This system is for educational and entertainment purposes only. Please ensure compliance with all applicable laws and terms of service for your jurisdiction and DFS platform.

## 🆘 Support

For issues or questions:
1. Check the documentation
2. Review the error logs
3. Create an issue in the repository

---

**Built with ❤️ for the DFS community**