# DijkstraBot — Instagram Influencer Intelligence

DijkstraBot is a production-grade Python CLI application designed for discovering, enriching, and scoring Instagram influencers at scale. It uses licensed data APIs to provide deep insights without violating Instagram's Terms of Service.

The system features a custom weighted algorithm called the **DijkstraScore**, which evaluates creators based on engagement, authenticity, niche relevance, and more. It is built to process over 50,000 profiles per run, delivering structured data to Google Sheets and local XLSX files.

## Prerequisites

- Python 3.11+
- Phyllo API Credentials ([Sign up here](https://getphyllo.com))
- RapidAPI Key (for Instagram Data API fallback)
- Google Service Account JSON (for Google Sheets export)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/dijkstrabot.git
   cd dijkstrabot
   ```

2. Run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Configuration

Edit `config.yaml` to define your search and filter criteria:

- `audience`: Set follower ranges and target locations.
- `creator`: Specify niche categories, bio keywords, and hashtags.
- `performance`: Define minimum engagement rates and DijkstraScore thresholds.
- `output`: Configure result limits and export settings.

## Usage Examples

### End-to-End Discovery
```bash
python main.py --config my_campaign.yaml --max-results 10000
```

### Dry Run (Mock Data)
```bash
python main.py --dry-run
```

### Scheduled Daily Run
```bash
python main.py --schedule "0 6 * * *"
```

## Output Reference

| Column | Description |
|--------|-------------|
| username | Instagram handle |
| profile_url | Link to profile |
| follower_count | Total followers |
| engagement_rate | (Likes + Comments) / Followers * 100 |
| location | Extracted city/country |
| category | Detected niche (fitness, beauty, etc.) |
| dijkstra_score | Weighted quality score (0-100) |

## Troubleshooting

- **Rate Limits**: If you hit 429 errors, the built-in rate limiter will handle backoff automatically.
- **Auth Errors**: Ensure your `.env` keys are correct and the Google Service Account has access to the target folder.
- **spaCy Model**: If NLP fails, ensure `en_core_web_sm` is downloaded via `python -m spacy download en_core_web_sm`.

## Architecture Diagram

```
[Phyllo API] <───┐
                 ├── [Discovery Module] ──> [Raw Profiles]
[RapidAPI]   <───┘           │
                             v
                    [Enrichment Module] (spaCy NLP)
                             │
                             v
                    [Scoring Module] (DijkstraScore)
                             │
                             v
                    [Filtering Module]
                             │
            ┌────────────────┴────────────────┐
            v                                 v
    [Google Sheets]                    [Local XLSX File]
```
