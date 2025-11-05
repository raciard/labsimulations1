import json
import os
import math
import matplotlib.pyplot as plt
from .config import format_time, format_distance, logger, format_duration

class Metrics:
    # Reservation metrics
    _successful_reservations = 0
    _failed_reservations = 0
    
    # Waiting time metrics
    _total_wait_time = 0.0  # total time users waited between reservation and pickup
    _total_waiting_users = 0  # number of users who completed waiting

    # Walking time metrics (time between successful reservation and pickup)
    _total_walking_time = 0.0
    _total_walking_users = 0
    
    # Trip metrics
    _total_trips = 0
    _total_trip_distance = 0.0

    # Attempts before success metrics
    _total_attempts_before_success = 0  # sum of attempts (including the successful one)
    
    # Car utilization metrics
    _total_car_time = 0.0  # total time tracked across all cars
    _total_in_use_time = 0.0  # time cars spent being used
    _total_charging_time = 0.0  # time cars spent charging
    
    # Charging station metrics
    _total_charging_sessions = 0
    _total_queue_length = 0  # sum of queue lengths sampled
    _total_queue_samples = 0  # number of times queue was sampled
    
    # Binning support for transient detection and confidence intervals
    _bins = []  # List of snapshots: [{time, successful_reservations, failed_reservations, ...}]
    _last_bin_snapshot = None  # Snapshot state at last bin boundary
    
    @staticmethod
    def record_successful_reservation():
        Metrics._successful_reservations += 1
    
    @staticmethod
    def record_failed_reservation():
        Metrics._failed_reservations += 1
    
    @staticmethod
    def record_wait_time(wait_time):
        """Record the time a user waited from first reservation attempt until successful reservation"""
        Metrics._total_wait_time += wait_time
        Metrics._total_waiting_users += 1

    @staticmethod
    def record_walking_time(walking_time):
        """Record the time a user walked from successful reservation to pickup"""
        Metrics._total_walking_time += walking_time
        Metrics._total_walking_users += 1
    
    @staticmethod
    def record_trip(distance):
        """Record a completed trip and its distance"""
        Metrics._total_trips += 1
        Metrics._total_trip_distance += distance

    @staticmethod
    def record_attempts_before_success(attempts: int):
        """Record the number of attempts (failed attempts + 1 successful) before reservation success"""
        try:
            Metrics._total_attempts_before_success += int(attempts)
        except Exception:
            pass
    
    @staticmethod
    def record_car_state_time(state, duration):
        """DEPRECATED: Car state time is now tracked directly in Car objects.
        This method is kept for backward compatibility but does nothing."""
        pass
    
    @staticmethod
    def record_station_queue(queue_length):
        """Record a charging station queue sample"""
        Metrics._total_queue_length += queue_length
        Metrics._total_queue_samples += 1
    
    @staticmethod
    def record_charging_session():
        """Record that a car started charging"""
        Metrics._total_charging_sessions += 1
    
    @staticmethod
    def snapshot_bin(time):
        """Capture a snapshot of current metrics for bin analysis.
        Stores the delta from the last snapshot to get per-bin statistics."""
        from .Entities.Car import Car
        
        # Aggregate car utilization times from all cars
        total_in_use_time = sum(car.in_use_time for car in Car.cars)
        total_charging_time = sum(car.charging_time for car in Car.cars)
        total_idle_time = sum(car.idle_time for car in Car.cars)
        total_car_time = total_in_use_time + total_charging_time + total_idle_time
        
        current_state = {
            'successful_reservations': Metrics._successful_reservations,
            'failed_reservations': Metrics._failed_reservations,
            'total_wait_time': Metrics._total_wait_time,
            'total_waiting_users': Metrics._total_waiting_users,
            'total_walking_time': Metrics._total_walking_time,
            'total_walking_users': Metrics._total_walking_users,
            'total_trips': Metrics._total_trips,
            'total_trip_distance': Metrics._total_trip_distance,
            'total_attempts': Metrics._total_attempts_before_success,
            'total_car_time': total_car_time,
            'total_in_use_time': total_in_use_time,
            'total_charging_time': total_charging_time,
            'total_charging_sessions': Metrics._total_charging_sessions,
        }
        
        if Metrics._last_bin_snapshot is None:
            # First bin: delta is the current state itself
            delta = {k: v for k, v in current_state.items()}
        else:
            # Compute delta since last snapshot
            delta = {k: current_state[k] - Metrics._last_bin_snapshot[k] 
                    for k in current_state.keys()}
        
        # Compute derived metrics for this bin
        bin_data = {
            'time': time,
            'bin_successful_reservations': delta['successful_reservations'],
            'bin_failed_reservations': delta['failed_reservations'],
            'bin_total_trips': delta['total_trips'],
            'bin_total_distance': delta['total_trip_distance'],
            'bin_attempts': delta['total_attempts'],
            'bin_in_use_time': delta['total_in_use_time'],
            'bin_car_time': delta['total_car_time'],
            'bin_charging_time': delta['total_charging_time'],
        }
        
        # Compute per-bin averages
        total_res = delta['successful_reservations'] + delta['failed_reservations']
        bin_data['bin_success_rate'] = (delta['successful_reservations'] / total_res 
                                         if total_res > 0 else 0.0)
        bin_data['bin_avg_attempts'] = (delta['total_attempts'] / delta['successful_reservations']
                                         if delta['successful_reservations'] > 0 else 0.0)
        bin_data['bin_avg_trip_distance'] = (delta['total_trip_distance'] / delta['total_trips']
                                              if delta['total_trips'] > 0 else 0.0)
        bin_data['bin_utilization_rate'] = (delta['total_in_use_time'] / delta['total_car_time']
                                             if delta['total_car_time'] > 0 else 0.0)
        
        Metrics._bins.append(bin_data)
        Metrics._last_bin_snapshot = current_state
        
        logger.debug(f"[{format_time(time)}] Bin {len(Metrics._bins)} collected: "
                    f"{bin_data['bin_total_trips']} trips, "
                    f"success_rate={bin_data['bin_success_rate']*100:.1f}%")

    
    @staticmethod
    def get_bins():
        """Return the list of collected bins"""
        return Metrics._bins
    
    @staticmethod
    def detect_transient_welch(metric_key='bin_success_rate', window_fraction=0.25, min_valid_bins=10):
        """Detect end of transient phase using truncated mean method with knee detection.
        
        Computes:
        1. Truncated mean x_k = (1/(n-k)) * sum(x_j for j=k+1 to n)
        2. Overall mean x̄ = (1/n) * sum(x_j for j=1 to n)
        3. Relative variation R_k = |x_k - x̄| / x̄
        
        Identifies the knee point in R_k curve automatically.
        
        Args:
            metric_key: Which bin metric to analyze (e.g., 'bin_success_rate', 'bin_avg_attempts')
            window_fraction: Not used (kept for API compatibility)
            min_valid_bins: Minimum number of non-zero bins needed for analysis
        
        Returns:
            (transient_end_bin, steady_state_mean, steady_state_std, num_steady_bins) or (None, None, None, 0)
            - transient_end_bin: The bin index where transient phase ends
            - steady_state_mean: Mean of the metric in steady state
            - steady_state_std: Standard deviation in steady state  
            - num_steady_bins: Number of bins used for steady-state statistics
        """
        if len(Metrics._bins) < min_valid_bins:
            return None, None, None, 0
        
        # Exclude the last bin as it may be incomplete (simulation ended mid-interval)
        bins_to_analyze = Metrics._bins[:-1] if len(Metrics._bins) > 1 else Metrics._bins
        
        # Filter out bins with no activity
        valid_bins = []
        valid_indices = []
        for i, b in enumerate(bins_to_analyze):
            if b['bin_successful_reservations'] + b['bin_failed_reservations'] > 0:
                valid_bins.append(b)
                valid_indices.append(i)
        
        if len(valid_bins) < min_valid_bins:
            return None, None, None, 0
        
        values = [b[metric_key] for b in valid_bins]
        n = len(values)
        
        # Need at least 20 bins for reliable detection
        if n < 20:
            mean_val = sum(values) / n
            var_val = sum((x - mean_val)**2 for x in values) / n if n > 1 else 0.0
            std_val = math.sqrt(var_val) if var_val > 0 else 0.0
            return valid_indices[0] if valid_indices else 0, mean_val, std_val, n
        
        # IMPORTANT: Only analyze the first portion of the simulation for transient detection
        # Transient phases typically occur early. Looking at the entire simulation 
        # can mistake later variations for transient behavior.
        # We'll analyze the first 50% of bins to find where transient ends
        analysis_length = min(n, max(50, n // 2))  # Use first half, but at least 50 bins
        values_for_analysis = values[:analysis_length]
        n_analysis = len(values_for_analysis)
        
        # Step 1: Compute overall mean x̄ using the FULL dataset (for comparison)
        overall_mean = sum(values) / n
        
        # Avoid division by zero in relative variation
        if abs(overall_mean) < 1e-10:
            overall_mean = 1e-10
        
        # Step 2: Compute truncated means x_k and relative variations R_k
        # Only for the analysis portion (early bins)
        truncated_means = []
        relative_variations = []
        
        # We compute for k from 0 to n_analysis-min_valid_bins
        max_k = n_analysis - min_valid_bins
        
        for k in range(max_k):
            # Truncated mean: average from k+1 to END OF FULL DATASET
            # This way we're asking "if we skip the first k bins, what's the mean of the rest?"
            truncated_data = values[k:]
            x_k = sum(truncated_data) / len(truncated_data)
            truncated_means.append(x_k)
            
            # Relative variation R_k = |x_k - x̄| / |x̄|
            R_k = abs(x_k - overall_mean) / abs(overall_mean)
            relative_variations.append(R_k)
        
        # Step 3: Find the knee point in R_k curve
        # Use the "maximum distance from line" method (perpendicular distance)
        knee_index = Metrics._find_knee_point(relative_variations)
        
        # knee_index is within the range [0, max_k)
        # It represents the index k in the truncated mean formula
        # This corresponds to values[knee_index] being the last point of transient
        # and values[knee_index+1:] being steady-state
        
        if knee_index is not None and 0 <= knee_index < len(valid_indices):
            # Map to the original bin index
            # valid_indices[knee_index] gives us the actual bin number
            transient_end = valid_indices[knee_index]
            
            # Compute steady-state statistics from knee point onward
            steady_values = values[knee_index:]
            num_steady_bins = len(steady_values)
            
            if steady_values:
                steady_mean = sum(steady_values) / len(steady_values)
                steady_var = sum((x - steady_mean)**2 for x in steady_values) / len(steady_values) if len(steady_values) > 1 else 0.0
                steady_std = math.sqrt(steady_var) if steady_var > 0 else 0.0
                return transient_end, steady_mean, steady_std, num_steady_bins
        
        # Fallback: if no clear knee detected, use entire series
        mean_val = sum(values) / n
        var_val = sum((x - mean_val)**2 for x in values) / n if n > 1 else 0.0
        std_val = math.sqrt(var_val) if var_val > 0 else 0.0
        return valid_indices[0] if valid_indices else 0, mean_val, std_val, n
    
    @staticmethod
    def _find_knee_point(curve):
        """Find the knee/elbow point in a curve using perpendicular distance method.
        
        The knee is the point with maximum perpendicular distance from the line
        connecting the first and last points of the curve.
        
        Args:
            curve: List of y-values (x is assumed to be indices 0, 1, 2, ...)
        
        Returns:
            Index of the knee point, or None if curve is too short
        """
        if len(curve) < 3:
            return 0  # Return start if too short
        
        n = len(curve)
        
        # First point (0, curve[0]) and last point (n-1, curve[-1])
        x1, y1 = 0, curve[0]
        x2, y2 = n - 1, curve[-1]
        
        # Compute perpendicular distance for each point to the line
        max_distance = -1
        knee_idx = 0
        
        # Line equation: (y2-y1)*x - (x2-x1)*y + (x2-x1)*y1 - (y2-y1)*x1 = 0
        # Distance = |ax + by + c| / sqrt(a^2 + b^2)
        a = y2 - y1
        b = -(x2 - x1)
        c = (x2 - x1) * y1 - (y2 - y1) * x1
        
        denominator = math.sqrt(a*a + b*b)
        if denominator < 1e-10:
            # Line is horizontal or degenerate, no clear knee
            return 0
        
        # Find point with maximum distance
        for i in range(1, n - 1):  # Skip first and last points
            x, y = i, curve[i]
            distance = abs(a * x + b * y + c) / denominator
            
            if distance > max_distance:
                max_distance = distance
                knee_idx = i
        
        # If the maximum distance is very small, the curve is nearly linear
        # In this case, consider the transient to be very short
        if max_distance < 0.01:  # Threshold for "nearly linear"
            return min(5, n // 10)  # Use first 10% or 5 bins, whichever is smaller
        
        return knee_idx
    
    @staticmethod
    def _find_max_change_point(curve):
        """Fallback method: find point with maximum rate of change decrease.
        
        Args:
            curve: List of values
        
        Returns:
            Index where the rate of change stabilizes most
        """
        if len(curve) < 3:
            return 0
        
        # Compute second derivative (rate of change of rate of change)
        second_derivative = []
        for i in range(1, len(curve) - 1):
            d2 = curve[i+1] - 2*curve[i] + curve[i-1]
            second_derivative.append(abs(d2))
        
        if not second_derivative:
            return 0
        
        # Find maximum change in curvature
        max_idx = second_derivative.index(max(second_derivative))
        return max_idx + 1  # Adjust for offset
    
    @staticmethod
    def plot_transient_detection(metric_key='bin_success_rate', metric_name='Success Rate', 
                                  save_path=None):
        """Plot metric over time with detected transient phase marked.
        
        Args:
            metric_key: Which bin metric to plot (e.g., 'bin_success_rate')
            metric_name: Human-readable name for the metric
            save_path: Path to save the plot (if None, displays interactive plot)
        """
        # Filter valid bins
        valid_bins = []
        valid_indices = []
        for i, b in enumerate(Metrics._bins):
            if b['bin_successful_reservations'] + b['bin_failed_reservations'] > 0:
                valid_bins.append(b)
                valid_indices.append(i)
        
        if len(valid_bins) < 10:
            logger.warning(f"Insufficient data to plot transient detection ({len(valid_bins)} bins)")
            return
        
        # Get metric values and time
        values = [b[metric_key] for b in valid_bins]
        times_hours = [b['time'] / 60.0 for b in valid_bins]  # Convert minutes to hours
        
        # Detect transient phase
        transient_end, steady_mean, steady_std, num_steady = Metrics.detect_transient_welch(metric_key)
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot 1: Raw metric over time
        ax1.plot(times_hours, values, 'b-', alpha=0.6, linewidth=1, label='Observed values')
        
        if transient_end is not None:
            # Find the index in valid_bins that corresponds to transient_end
            transient_idx = valid_indices.index(transient_end) if transient_end in valid_indices else None
            
            if transient_idx is not None and transient_idx < len(times_hours):
                # Mark transient region
                ax1.axvspan(0, times_hours[transient_idx], alpha=0.2, color='red', 
                           label=f'Transient phase ({times_hours[transient_idx]:.1f}h)')
                
                # Mark steady-state region
                if transient_idx < len(times_hours) - 1:
                    ax1.axvspan(times_hours[transient_idx], times_hours[-1], alpha=0.2, color='green',
                               label=f'Steady-state ({num_steady} bins)')
                
                # Plot steady-state mean
                ax1.axhline(y=steady_mean, color='darkgreen', linestyle='--', linewidth=2,
                           label=f'Steady-state mean: {steady_mean:.4f}')
                
                # Plot confidence bands (mean ± std)
                ax1.axhline(y=steady_mean + steady_std, color='green', linestyle=':', alpha=0.5)
                ax1.axhline(y=steady_mean - steady_std, color='green', linestyle=':', alpha=0.5)
        
        ax1.set_xlabel('Simulation Time (hours)', fontsize=11)
        ax1.set_ylabel(metric_name, fontsize=11)
        ax1.set_title(f'{metric_name} Over Time - Transient Detection', fontsize=13, fontweight='bold')
        ax1.legend(loc='best', fontsize=9)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Relative variation curve (used for knee detection)
        if transient_end is not None:
            # Recompute the relative variations EXACTLY as done in detection
            n = len(values)
            overall_mean = sum(values) / n
            if abs(overall_mean) < 1e-10:
                overall_mean = 1e-10
            
            # IMPORTANT: Match the detection algorithm - only analyze first portion
            analysis_length = min(n, max(50, n // 2))
            
            min_valid_bins = 10
            max_k = analysis_length - min_valid_bins
            
            relative_variations = []
            for k in range(max_k):
                # Use full dataset for truncated mean (just like detection)
                truncated_data = values[k:]
                x_k = sum(truncated_data) / len(truncated_data)
                R_k = abs(x_k - overall_mean) / abs(overall_mean)
                relative_variations.append(R_k)
            
            # Find knee point
            knee_index = Metrics._find_knee_point(relative_variations)
            
            # Plot relative variation
            ax2.plot(range(len(relative_variations)), relative_variations, 'b-', linewidth=2,
                    label='Relative variation R_k')
            
            # Mark the analyzed region (first half)
            ax2.axvspan(0, len(relative_variations), alpha=0.1, color='blue',
                       label=f'Analyzed region (first {analysis_length} bins)')
            
            # Mark the knee point
            if knee_index is not None and knee_index < len(relative_variations):
                ax2.axvline(x=knee_index, color='red', linestyle='--', linewidth=2,
                           label=f'Detected knee at k={knee_index}')
                ax2.plot(knee_index, relative_variations[knee_index], 'ro', markersize=10,
                        label=f'R_k = {relative_variations[knee_index]:.4f}')
            
            ax2.set_xlabel('Truncation Index k (first bins only)', fontsize=11)
            ax2.set_ylabel('Relative Variation |x_k - x̄| / |x̄|', fontsize=11)
            ax2.set_title('Knee Detection in Relative Variation Curve (Early Phase Analysis)', fontsize=13, fontweight='bold')
            ax2.legend(loc='best', fontsize=9)
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Transient detection plot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    @staticmethod
    def plot_all_metrics_transient(save_dir='plots'):
        """Generate transient detection plots for all key metrics.
        
        Args:
            save_dir: Directory to save plots
        """
        os.makedirs(save_dir, exist_ok=True)
        
        metrics_to_plot = [
            ('bin_success_rate', 'Reservation Success Rate'),
            ('bin_avg_attempts', 'Average Attempts Before Success'),
            ('bin_utilization_rate', 'Car Utilization Rate'),
            ('bin_avg_trip_distance', 'Average Trip Distance (km/10)')
        ]
        
        for metric_key, metric_name in metrics_to_plot:
            save_path = os.path.join(save_dir, f'transient_{metric_key}.png')
            Metrics.plot_transient_detection(metric_key, metric_name, save_path)
        
        logger.info(f"All transient detection plots saved to {save_dir}/")
    
    @staticmethod
    def detect_stationary_windows(metric_key='bin_success_rate', window_size=5, 
                                   variance_threshold=0.15):
        """Detect time windows where metric appears locally stationary.
        
        For non-stationary systems, identifies periods where the metric is slowly varying
        and can be treated as stationary within that window.
        
        Args:
            metric_key: Which bin metric to analyze
            window_size: Size of moving window to check for stationarity
            variance_threshold: Maximum normalized variance to consider stationary
        
        Returns:
            List of (start_bin, end_bin, mean, std) tuples for stationary windows
        """
        valid_bins = [b for b in Metrics._bins 
                     if b['bin_successful_reservations'] + b['bin_failed_reservations'] > 0]
        
        if len(valid_bins) < window_size:
            return []
        
        values = [b[metric_key] for b in valid_bins]
        windows = []
        
        i = 0
        while i <= len(values) - window_size:
            # Check if this window is stationary
            window = values[i:i+window_size]
            mean = sum(window) / len(window)
            variance = sum((x - mean)**2 for x in window) / len(window)
            std = math.sqrt(variance) if variance > 0 else 0.0
            
            # Normalized variance (coefficient of variation squared)
            norm_var = (std / mean) if mean > 0.01 else variance
            
            if norm_var <= variance_threshold:
                # This window is stationary, try to extend it
                end = i + window_size
                while end < len(values):
                    # Try adding next bin
                    extended = values[i:end+1]
                    ext_mean = sum(extended) / len(extended)
                    ext_var = sum((x - ext_mean)**2 for x in extended) / len(extended)
                    ext_std = math.sqrt(ext_var) if ext_var > 0 else 0.0
                    ext_norm_var = (ext_std / ext_mean) if ext_mean > 0.01 else ext_var
                    
                    if ext_norm_var <= variance_threshold:
                        end += 1
                    else:
                        break
                
                # Store window
                window_vals = values[i:end]
                win_mean = sum(window_vals) / len(window_vals)
                win_var = sum((x - win_mean)**2 for x in window_vals) / len(window_vals)
                win_std = math.sqrt(win_var) if win_var > 0 else 0.0
                windows.append((i, end-1, win_mean, win_std))
                
                i = end  # Jump to end of stationary window
            else:
                i += 1
        
        return windows

    @staticmethod
    def compute_confidence_interval(metric_key='bin_success_rate', confidence=0.95, 
                                     start_bin=0, end_bin=None, min_valid_bins=5):
        """Compute confidence interval using batch means method.
        
        Args:
            metric_key: Which bin metric to analyze
            confidence: Confidence level (e.g., 0.95 for 95%)
            start_bin: Start analysis from this bin (to exclude transient)
            end_bin: End at this bin (None = use all available)
            min_valid_bins: Minimum number of non-zero bins needed
        
        Returns:
            (mean, half_width, lower, upper) or (None, None, None, None)
        """
        bins_slice = Metrics._bins[start_bin:end_bin]
        
        # Filter out bins with no activity
        valid_bins = [b for b in bins_slice 
                     if b['bin_successful_reservations'] + b['bin_failed_reservations'] > 0]
        
        if len(valid_bins) < min_valid_bins:
            return None, None, None, None
        
        values = [b[metric_key] for b in valid_bins]
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean)**2 for x in values) / (n - 1) if n > 1 else 0.0
        std_err = math.sqrt(variance / n) if n > 0 else 0.0
        
        # Use t-distribution for small samples
        # Approximate critical value for common confidence levels
        if confidence == 0.95:
            t_critical = 1.96 if n >= 30 else 2.0 + (30 - n) * 0.1 / 30  # rough approximation
        elif confidence == 0.90:
            t_critical = 1.645 if n >= 30 else 1.8
        elif confidence == 0.99:
            t_critical = 2.576 if n >= 30 else 3.0
        else:
            t_critical = 2.0  # fallback
        
        half_width = t_critical * std_err
        lower = mean - half_width
        upper = mean + half_width
        
        return mean, half_width, lower, upper
    
    @staticmethod
    def compute_cycle_stationary_intervals(metric_key='bin_success_rate', 
                                           cycle_length_minutes=1440, confidence=0.95):
        """Compute confidence intervals for cycle-stationary (time-of-day varying) systems.
        
        Groups bins by their position in the daily cycle and computes separate CIs
        for each phase, assuming the system repeats daily but varies within the day.
        
        Args:
            metric_key: Which bin metric to analyze
            cycle_length_minutes: Length of one cycle (default 1440 = 1 day)
            confidence: Confidence level
        
        Returns:
            Dict mapping cycle_phase -> (mean, hw, lower, upper, n_samples)
        """
        from .config import BIN_INTERVAL
        
        # Group bins by their phase in the cycle
        bins_per_cycle = max(1, cycle_length_minutes // BIN_INTERVAL)
        
        # Organize bins by cycle phase
        phase_bins = {}  # phase_index -> [bin_data]
        
        for b in Metrics._bins:
            if b['bin_successful_reservations'] + b['bin_failed_reservations'] > 0:
                # Determine which phase of the cycle this bin belongs to
                bin_time = b['time']
                phase = int((bin_time % cycle_length_minutes) // BIN_INTERVAL) % bins_per_cycle
                
                if phase not in phase_bins:
                    phase_bins[phase] = []
                phase_bins[phase].append(b)
        
        # Compute CI for each phase
        results = {}
        for phase, bins_in_phase in sorted(phase_bins.items()):
            if len(bins_in_phase) >= 3:  # Need at least 3 samples
                values = [b[metric_key] for b in bins_in_phase]
                n = len(values)
                mean = sum(values) / n
                variance = sum((x - mean)**2 for x in values) / (n - 1) if n > 1 else 0.0
                std_err = math.sqrt(variance / n) if n > 0 else 0.0
                
                # t-critical value
                if confidence == 0.95:
                    t_critical = 1.96 if n >= 30 else 2.0 + (30 - n) * 0.1 / 30
                elif confidence == 0.90:
                    t_critical = 1.645 if n >= 30 else 1.8
                elif confidence == 0.99:
                    t_critical = 2.576 if n >= 30 else 3.0
                else:
                    t_critical = 2.0
                
                half_width = t_critical * std_err
                lower = mean - half_width
                upper = mean + half_width
                
                # Store phase time for reporting
                phase_time_minutes = phase * BIN_INTERVAL
                results[phase] = {
                    'phase_time_minutes': phase_time_minutes,
                    'mean': mean,
                    'half_width': half_width,
                    'lower': lower,
                    'upper': upper,
                    'n_samples': n,
                    'std': math.sqrt(variance) if variance > 0 else 0.0
                }
        
        return results
    
    @staticmethod
    def get_reservation_success_rate():
        total = Metrics._successful_reservations + Metrics._failed_reservations
        if total == 0:
            return 0.0
        return Metrics._successful_reservations / total
    
    @staticmethod
    def get_average_wait_time():
        """Average time from first reservation attempt until successful reservation"""
        if Metrics._total_waiting_users == 0:
            return 0.0
        return Metrics._total_wait_time / Metrics._total_waiting_users

    @staticmethod
    def get_average_walking_time():
        """Average time from successful reservation to pickup"""
        if Metrics._total_walking_users == 0:
            return 0.0
        return Metrics._total_walking_time / Metrics._total_walking_users
    
    @staticmethod
    def get_average_trip_distance():
        """Get average distance per trip"""
        if Metrics._total_trips == 0:
            return 0.0
        return Metrics._total_trip_distance / Metrics._total_trips

    @staticmethod
    def get_average_attempts_before_success():
        """Average number of attempts users make before successfully reserving a car.
        Counts the successful attempt as well (i.e., 1 means success on first try)."""
        if Metrics._successful_reservations == 0:
            return 0.0
        return Metrics._total_attempts_before_success / Metrics._successful_reservations
    
    @staticmethod
    @staticmethod
    def get_car_utilization_rate():
        """Get fraction of time cars spent being used vs total time"""
        from .Entities.Car import Car
        
        total_in_use = 0.0
        total_time = 0.0
        for car in Car.cars:
            total_in_use += car.in_use_time
            total_time += car.in_use_time + car.charging_time + car.idle_time

        if total_time == 0:
            return 0.0
        return total_in_use / total_time

    @staticmethod
    def get_charging_rate():
        """Get fraction of time cars spent charging vs total time"""
        from .Entities.Car import Car
        
        total_charging = 0.0
        total_time = 0.0
        for car in Car.cars:
            total_charging += car.charging_time
            total_time += car.in_use_time + car.charging_time + car.idle_time
        
        if total_time == 0:
            return 0.0
        return total_charging / total_time
    
    @staticmethod
    def get_average_queue_length():
        """Get average charging station queue length"""
        if Metrics._total_queue_samples == 0:
            return 0.0
        return Metrics._total_queue_length / Metrics._total_queue_samples
    
    @staticmethod
    def print_metrics():
        """Print a comprehensive metrics report"""
        logger.info("\nSIMULATION METRICS REPORT")
        logger.info("=" * 40)
        logger.info(f"Reservation Success Rate: {Metrics.get_reservation_success_rate()*100:.1f}%")
        logger.info(f"Total Reservations: {Metrics._successful_reservations + Metrics._failed_reservations}")
        logger.info(f"Average Walking Time: {format_duration(Metrics.get_average_walking_time())}")
        logger.info(f"Average Attempts Before Success: {Metrics.get_average_attempts_before_success():.2f}")
        logger.info(f"\nTrip Statistics:")
        logger.info(f"Total Trips: {Metrics._total_trips}")
        logger.info(f"Average Trip Distance: {format_distance(Metrics.get_average_trip_distance())}")
        logger.info(f"Total Distance Traveled: {format_distance(Metrics._total_trip_distance)}")
        logger.info(f"\nCar Utilization:")
        logger.info(f"In-Use Rate: {Metrics.get_car_utilization_rate()*100:.1f}%")
        logger.info(f"Charging Rate: {Metrics.get_charging_rate()*100:.1f}%")
        logger.info(f"Idle Rate: {(1-Metrics.get_car_utilization_rate()-Metrics.get_charging_rate())*100:.1f}%")
        logger.info(f"\nCharging Statistics:")
        logger.info(f"Total Charging Sessions: {Metrics._total_charging_sessions}")
        logger.info(f"Average Queue Length: {Metrics.get_average_queue_length():.2f}")
        
        # Print binning analysis if bins were collected
        if Metrics._bins:
            # Exclude the last bin as it may be incomplete (simulation ended mid-interval)
            bins_to_analyze = Metrics._bins[:-1] if len(Metrics._bins) > 1 else Metrics._bins
            
            # Count valid bins (those with activity)
            valid_bins = [b for b in bins_to_analyze 
                         if b['bin_successful_reservations'] + b['bin_failed_reservations'] > 0]
            
            logger.info(f"\n" + "=" * 40)
            logger.info(f"STATISTICAL ANALYSIS ({len(bins_to_analyze)} bins analyzed, {len(valid_bins)} with activity, 1 incomplete bin excluded)")
            logger.info("=" * 40)
            
            if len(valid_bins) < 10:
                logger.info("⚠ Warning: Insufficient bins with activity for reliable statistical analysis")
                logger.info(f"  Recommendation: Increase simulation time or user arrival rate")
            else:
                # Import config to check system type
                from . import config
                system_type = getattr(config, 'SYSTEM_TYPE', 'STATIONARY')
                
                if system_type == 'STATIONARY':
                    # STATIONARY SYSTEM: Focus on transient detection
                    logger.info(f"\n🔍 STATIONARY SYSTEM ANALYSIS")
                    logger.info(f"Focus: Automated transient phase detection")
                    logger.info("-" * 40)
                    
                    for metric_key, metric_name in [
                        ('bin_success_rate', 'Reservation Success Rate'),
                        ('bin_avg_attempts', 'Average Attempts Before Success'),
                        ('bin_utilization_rate', 'Car Utilization Rate'),
                        ('bin_avg_trip_distance', 'Average Trip Distance')
                    ]:
                        transient_end, steady_mean, steady_std, steady_bins = Metrics.detect_transient_welch(metric_key)
                        if transient_end is not None:
                            transient_time = Metrics._bins[transient_end]['time'] if transient_end < len(Metrics._bins) else 0
                            logger.info(f"\n{metric_name}:")
                            logger.info(f"  ⏱ Transient phase: bins 0-{transient_end} "
                                       f"({format_duration(transient_time)})")
                            logger.info(f"  📊 Steady-state mean: {steady_mean:.4f}")
                            logger.info(f"  📈 Steady-state std: {steady_std:.4f}")
                            logger.info(f"  ✓ Steady-state bins: {steady_bins}")
                        else:
                            logger.info(f"\n{metric_name}: Insufficient data for transient detection")
                    
                    # Generate transient detection plots
                    logger.info(f"\n📊 Generating transient detection plots...")
                    Metrics.plot_all_metrics_transient(save_dir='transient_plots')
                
                elif system_type == 'CYCLE_STATIONARY':
                    # CYCLE-STATIONARY SYSTEM: Focus on confidence intervals
                    logger.info(f"\n📈 CYCLE-STATIONARY SYSTEM ANALYSIS")
                    logger.info(f"Focus: Confidence intervals for time-varying metrics")
                    logger.info("-" * 40)
                    
                    for metric_key, metric_name, display_multiplier in [
                        ('bin_success_rate', 'Success Rate', 100),  # Display as percentage
                        ('bin_avg_attempts', 'Avg Attempts', 1),
                        ('bin_utilization_rate', 'Utilization', 100)
                    ]:
                        cycle_intervals = Metrics.compute_cycle_stationary_intervals(metric_key)
                        
                        if cycle_intervals:
                            logger.info(f"\n{metric_name} by Time-of-Day (24h cycle):")
                            for phase in sorted(cycle_intervals.keys()):
                                data = cycle_intervals[phase]
                                phase_time = data['phase_time_minutes']
                                hours = int(phase_time // 60)
                                
                                if display_multiplier == 100:
                                    mean_disp = data['mean'] * 100
                                    lower_disp = data['lower'] * 100
                                    upper_disp = data['upper'] * 100
                                    unit = '%'
                                else:
                                    mean_disp = data['mean']
                                    lower_disp = data['lower']
                                    upper_disp = data['upper']
                                    unit = ''
                                
                                logger.info(f"  Phase {phase} (~{hours:02d}:00): "
                                           f"mean={mean_disp:.2f}{unit}, "
                                           f"95% CI=[{lower_disp:.2f}, {upper_disp:.2f}]{unit}, "
                                           f"n={data['n_samples']}")
                        else:
                            logger.info(f"\n{metric_name}: Insufficient samples for cycle analysis")
        
        logger.info("=" * 40)

    @staticmethod
    def get_summary_dict():
        """Return a machine-readable summary of metrics with both raw and formatted fields."""
        success_rate = Metrics.get_reservation_success_rate()
        avg_trip_km = Metrics.get_average_trip_distance()
        total_trip_km = Metrics._total_trip_distance
        in_use_rate = Metrics.get_car_utilization_rate()
        charging_rate = Metrics.get_charging_rate()
        idle_rate = max(0.0, 1 - in_use_rate - charging_rate)
        avg_queue = Metrics.get_average_queue_length()
        avg_attempts = Metrics.get_average_attempts_before_success()

        return {
            # raw values
            "reservation_success_rate": success_rate,  # 0..1
            "total_reservations": Metrics._successful_reservations + Metrics._failed_reservations,
            "total_trips": Metrics._total_trips,
            # Output-only scaling: divide reported km by 10 (logic/internal values unchanged)
            "average_trip_distance_km": avg_trip_km / 10.0,
            "total_distance_traveled_km": total_trip_km / 10.0,
            "average_walking_time_minutes": Metrics.get_average_walking_time(),
            "average_attempts_before_success": avg_attempts,
            "in_use_rate": in_use_rate,  # 0..1
            "charging_rate": charging_rate,  # 0..1
            "idle_rate": idle_rate,  # 0..1
            "total_charging_sessions": Metrics._total_charging_sessions,
            "average_queue_length": avg_queue,

            # formatted strings (for display)
            "reservation_success_rate_pct_str": f"{success_rate*100:.1f}%",
            "average_trip_distance_str": format_distance(avg_trip_km),
            "total_distance_traveled_str": format_distance(total_trip_km),
            "average_walking_time_str": format_duration(Metrics.get_average_walking_time()),
            "average_attempts_before_success_str": f"{avg_attempts:.2f}",
            "in_use_rate_pct_str": f"{in_use_rate*100:.1f}%",
            "charging_rate_pct_str": f"{charging_rate*100:.1f}%",
            "idle_rate_pct_str": f"{idle_rate*100:.1f}%",
            "average_queue_length_str": f"{avg_queue:.2f}",
        }

    @staticmethod
    def export_summary_json(path: str | None = None):
        """Write the summary JSON to a file.
        If path is None, uses SIM_SUMMARY_JSON env var if set. No-op if both missing.
        Also logs a single-line JSON with a recognizable prefix for easy scraping.
        """
        target = path or os.environ.get("SIM_SUMMARY_JSON")
        summary = Metrics.get_summary_dict()

        # Log a single-line machine-readable entry
        try:
            logger.info("METRICS_JSON %s", json.dumps(summary, separators=(",", ":")))
        except Exception:
            pass

        if not target:
            return
        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write summary JSON to {target}: {e}")
