# Windsurf Credit Throttle

A Streamlit application for managing Windsurf add-on credit caps.

## Features

- **Verify Credit Caps**: Check team-level and individual user credit configurations
- **Set Team Cap**: Configure organization-wide add-on credit limits
- **Set Individual Caps**: Set custom caps for specific users or bulk import from CSV

## Installation

### Using uvx (recommended)

```bash
# Run directly from GitHub
uvx --from git+https://github.com/PFPT-Internal/windsurf-throttle windsurf-throttle

# Or from PyPI (when published)
uvx windsurf-throttle
```

### Using pip

```bash
pip install windsurf-throttle
windsurf-throttle
```

### From source

```bash
git clone https://github.com/PFPT-Internal/windsurf-throttle.git
cd windsurf-throttle
uv sync
uv run windsurf-throttle
```

## Configuration

Set your Windsurf service key as an environment variable:

```bash
export WINDSURF_SERVICE_KEY=your_service_key_here
```

Or create a `.env` file in your working directory:

```
WINDSURF_SERVICE_KEY=your_service_key_here
```

### Optional Configuration

```bash
# Override the API base URL (default: https://server.codeium.com)
export WINDSURF_BASE_URL=https://custom.server.com
```

## Usage

### Running the App

```bash
# Using the CLI
windsurf-throttle

# Or run Streamlit directly
streamlit run src/windsurf_throttle/app.py
```

### Credit Cap Strategy

The app implements the following strategy:

1. **Base Credits**: Each user gets 500 base credits
2. **Organization Cap**: Set a default add-on cap for all users (e.g., 1000)
3. **Individual Caps**: For high-usage users, set individual caps = current add-on usage + buffer

Example:
- User with 1200 total credits used → 700 add-on credits used
- Individual cap = 700 + 500 buffer = 1200 add-on credits
- Total available = 500 base + 1200 add-on = 1700 credits

### Bulk CSV Import

Upload a CSV with these columns:
- `email` (required): User email address
- `credits_used` (required): Current total credit usage
- `name` (optional): User display name

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/PFPT-Internal/windsurf-throttle.git
cd windsurf-throttle
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run ruff check src tests
uv run mypy src

# Install pre-commit hooks
uv run pre-commit install
```

## License

MIT
