# 🏈 NFL GPP Simulator

A sophisticated Monte Carlo simulation system for NFL DFS projections, built with nfl_data_py integration and advanced boom scoring algorithms.

## 🎯 Overview

This system provides end-to-end NFL DFS analysis:

- **Monte Carlo Simulator**: 10,000+ simulations per player with correlation modeling
- **Boom Score Algorithm**: Position-normalized scoring (1-100) with ownership/value boosts
- **Value Metrics**: Points per $1k salary and ceiling value calculations
- **Diagnostics**: MAE/RMSE/correlation vs site projections
- **Streamlit UI**: Interactive web interface with file upload and analysis

## 🚀 Features

### Core Simulation
- **Game Environment Modeling**: Pace, scoring, pass rates with Vegas adjustments
- **Team Correlation**: Shared efficiency shocks across teammates
- **Position-Specific Logic**: QB, RB, WR, TE, DST with DK scoring
- **Rookie Fallback**: Site projection centering for new players

### Advanced Analytics
- **Boom Probability**: P(X ≥ position_threshold)
- **Beat Site Probability**: P(X ≥ site_projection)
- **Dart Throw Detection**: ≤5% owned + ≥70 boom score
- **Value Optimization**: Points per $1k salary analysis

### Data Integration
- **nfl_data_py Baseline**: 2023-2024 historical data for priors
- **Site File Support**: Upload players.csv with projections/ownership
- **Column Mapping**: Auto-detection with validation warnings

## 📁 Project Structure

```
├── app.py                          # Streamlit main application
├── requirements.txt                # Python dependencies
├── Procfile                       # Render deployment config
├── scripts/
│   └── build_baseline.py          # nfl_data_py baseline builder
├── src/
│   ├── sim/
│   │   └── game_simulator.py      # Core Monte Carlo engine
│   ├── projections/
│   │   ├── boom_score.py          # Boom score calculator
│   │   ├── value_metrics.py       # Value metrics calculator
│   │   ├── diagnostics.py         # Accuracy diagnostics
│   │   └── run_week_from_site_players.py  # CLI runner
│   ├── ingest/                    # Data ingestion modules
│   └── metrics/                   # Metrics warehouse
├── data/
│   ├── baseline/                  # Generated priors
│   └── sim_week/                  # Simulation outputs
└── docs/                          # Documentation
```

## 🛠️ Installation

### Local Development

1. **Clone and setup**:
```bash
git clone <repository>
cd nfl-gpp-simulator
pip install -r requirements.txt
```

2. **Build baseline** (one-time setup):
```bash
python scripts/build_baseline.py --start 2023 --end 2024 --out data/baseline
```

3. **Run Streamlit app**:
```bash
streamlit run app.py
```

### Render Deployment

1. **Connect repository** to Render
2. **Set build command**: `pip install -r requirements.txt`
3. **Set start command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. **Deploy** and access via Render URL

## 📊 Usage

### 1. Web Interface (Recommended)

1. **Access Streamlit app** at `http://localhost:8501`
2. **Load baseline data** (one-time)
3. **Upload players.csv** with your site data
4. **Configure simulation** (sims, seed)
5. **Run simulation** and analyze results
6. **Download outputs** (individual files or ZIP bundle)

### 2. Command Line

```bash
# Run simulation from CLI
python -m src.projections.run_week_from_site_players \
    --season 2025 --week 1 \
    --players-site path/to/players.csv \
    --team-priors data/baseline/team_priors.csv \
    --player-priors data/baseline/player_priors.csv \
    --boom-thresholds data/baseline/boom_thresholds.json \
    --sims 10000 --out data/sim_week
```

## 📋 Input Format

### players.csv Requirements

**Required columns:**
- `PLAYER`: Player name
- `POS`: Position (QB, RB, WR, TE, DST)
- `TEAM`: Player team
- `OPP`: Opponent team

**Optional columns:**
- `FPTS`: Site projection (for comparison)
- `SAL`: Salary (for value metrics)
- `RST%`: Projected ownership (0-100)
- `O/U`: Game total (Vegas)
- `SPRD`: Spread (Vegas)

### Example players.csv:
```csv
PLAYER,POS,TEAM,OPP,FPTS,SAL,RST%,O/U,SPRD
Patrick Mahomes,QB,KAN,BUF,24.5,8500,15.2,52.5,-3.0
Josh Allen,QB,BUF,KAN,23.8,8200,18.7,52.5,3.0
```

## 📈 Outputs

### Primary Files

1. **sim_players.csv**: Our projections
   - `sim_mean`, `floor_p10`, `p75`, `ceiling_p90`, `p95`
   - `boom_prob`, `rookie_fallback`

2. **compare.csv**: Site vs simulation comparison
   - `delta_mean`, `pct_delta`, `beat_site_prob`
   - `value_per_1k`, `ceil_per_1k`, `boom_score`, `dart_flag`

3. **diagnostics_summary.csv**: Accuracy metrics
   - `overall_mae`, `overall_rmse`, `overall_correlation`
   - Position-specific metrics

4. **flags.csv**: Notable discrepancies
   - High deltas, dart throws, data issues

5. **metadata.json**: Run information
   - Configuration, timestamps, counts

### ZIP Bundle
Download all files together with `simulator_outputs.zip`

## 🧮 Algorithm Details

### Monte Carlo Simulation

**Game Environment:**
- Base pace from team priors
- Vegas adjustments (O/U, spread)
- Game-level shocks (pace, pass rate)

**Player Simulation:**
- Usage shares (targets, carries)
- Efficiency rates (yards/touch)
- TD allocation (Poisson/binomial)
- Team correlation shocks

**Position Logic:**
- **QB**: Pass attempts, yards, TDs, INTs, rush
- **RB/WR/TE**: Targets, carries, yards, TDs
- **DST**: Sacks, turnovers, points allowed

### Boom Score Algorithm

**Base Score:**
```
composite = 0.6 × boom_prob + 0.4 × beat_site_prob
```

**Boosts:**
- **Ownership**: +20% (≤5%), +10% (≤10%), +5% (≤20%)
- **Value**: Up to +15% if above position median

**Final Score:**
```
boom_score = 100 × percentile_rank(composite) × (1 + own_boost) × (1 + value_boost)
```

### Value Metrics

**Value per $1k:**
```
value_per_1k = sim_mean / (salary / 1000)
```

**Ceiling Value:**
```
ceil_per_1k = p90 / (salary / 1000)
```

## 🔧 Configuration

### Simulation Parameters
- **Number of Sims**: 1,000 - 50,000 (default: 10,000)
- **Random Seed**: For reproducibility
- **Baseline Path**: Location of priors data

### Boom Thresholds
Position-specific p90 thresholds from 2023-2024 data:
- QB: ~25.0 points
- RB: ~20.0 points  
- WR: ~18.0 points
- TE: ~15.0 points

## 📊 Diagnostics

### Accuracy Metrics
- **MAE**: Mean Absolute Error vs site projections
- **RMSE**: Root Mean Square Error
- **Correlation**: Pearson correlation coefficient
- **Coverage**: % of site projections in [p10, p90] range

### Position Performance
Individual metrics for QB, RB, WR, TE positions

### Rookie Handling
- Excluded from accuracy metrics
- Site projection centering
- Position variance scaling

## 🚀 Performance

### Simulation Speed
- **10,000 sims**: ~30-60 seconds for 100 players
- **50,000 sims**: ~2-5 minutes for 100 players
- **Caching**: Results cached for identical inputs

### Memory Usage
- **Baseline data**: ~50MB (team/player priors)
- **Simulation results**: ~100MB per 10k sims
- **Streamlit session**: ~200MB typical

## 🔄 Updates & Maintenance

### Baseline Updates
```bash
# Rebuild baseline with new seasons
python scripts/build_baseline.py --start 2023 --end 2024 --out data/baseline
```

### Model Improvements
- Enhanced correlation modeling
- Weather/dome adjustments
- Opponent-specific priors
- Hierarchical shrinkage

## 📝 License

This project is for educational and research purposes. Please ensure compliance with DFS site terms of service.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## 📞 Support

For issues and questions:
- Check the documentation
- Review error logs
- Open GitHub issue with details

---

**Built with ❤️ for the DFS community**