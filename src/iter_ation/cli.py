import argparse
from dotenv import load_dotenv
from iter_ation.tui.app import IterApp


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="iter-ation",
        description="ITER-ATION: Tokamak Disruption Monitor",
    )
    parser.add_argument(
        "--mode", choices=["observation", "interactive", "ai"],
        default="ai",
        help="Start mode: ai (default), observation, or interactive",
    )
    parser.add_argument(
        "--speed", type=int, default=100,
        help="Simulation speed multiplier (default: 100)",
    )
    args = parser.parse_args()
    IterApp(speed=args.speed, interactive=(args.mode == "interactive")).run()
