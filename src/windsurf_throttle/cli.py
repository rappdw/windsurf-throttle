"""CLI entry point to launch the Streamlit app."""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    return Path.home() / ".windsurf-throttle"


def ensure_api_key() -> None:
    """Ensure WINDSURF_SERVICE_KEY is available, prompting user if not found."""
    config_dir = get_config_dir()
    env_path = config_dir / ".env"

    load_dotenv(env_path)

    if os.getenv("WINDSURF_SERVICE_KEY"):
        return

    print("=" * 60)
    print("WINDSURF_SERVICE_KEY not found in environment or .env file.")
    print("=" * 60)
    print()
    print("You can get your service key from the Windsurf admin panel.")
    print()

    api_key = input("Enter your Windsurf service key: ").strip()

    if not api_key:
        print("No key entered. Exiting.")
        sys.exit(1)

    config_dir.mkdir(parents=True, exist_ok=True)

    existing_content = ""
    if env_path.exists():
        existing_content = env_path.read_text()
        if not existing_content.endswith("\n"):
            existing_content += "\n"

    with env_path.open("a") as f:
        if not existing_content:
            f.write("# Windsurf Credit Throttle Configuration\n")
        f.write(f"WINDSURF_SERVICE_KEY={api_key}\n")

    print(f"\nAPI key saved to {env_path}")
    print("This will be loaded automatically on future runs.\n")

    os.environ["WINDSURF_SERVICE_KEY"] = api_key


def main() -> None:
    """Launch the Streamlit application."""
    ensure_api_key()

    app_path = Path(__file__).parent / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path), "--server.headless=false"])


if __name__ == "__main__":
    main()
