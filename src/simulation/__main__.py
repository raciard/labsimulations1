import os
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Car Sharing Simulation")
    parser.add_argument("--config", "-c", help="Path to YAML config file to use", default=None)
    args = parser.parse_args()

    if args.config:
        os.environ["SIM_CONFIG_FILE"] = os.path.abspath(args.config)

    # Delay import until after env var is set so config.py can pick it up
    from . import simulator
    simulator.run()


if __name__ == "__main__":
    main()
