from src.simulation.simulator import Simulator
from src.simulation.metrics import Metrics
from src.simulation import config

# Short run for inspection
END_TIME = 24 * 60  # one day in minutes
config.SIMULATION_END_TIME = END_TIME
config.BIN_INTERVAL = 60  # hourly bins

sim = Simulator()
sim.simulate(END_TIME)

bins = Metrics.get_bins()
print(f"Collected {len(bins)} bins")
for i, b in enumerate(bins[:50]):
    print(i, b['time'], b['bin_successful_reservations'], b['bin_failed_reservations'], f"sr={b['bin_success_rate']:.2f}")
