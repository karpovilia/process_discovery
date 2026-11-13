# Truth-only operating regime calibration, version 1

Written before running calibration.py. No fitted-model action costs are inspected in generator calibration. Technical execution checks use development seeds and are excluded.

Reference per structure: 4 fixed-world episodes, rate 0.30 times analytical fixed-world bottleneck throughput, arrivals to time 2000, horizon 6000. Reference S = max(2, ceiling of the 95th percentile of sampled unique-case WIP between 200 and 2000)). T = mean completed cycle time, rounded up to the next integer (minimum 2). S and T are common across the four feedback worlds of that structure. Reference seed 70000000000 + process number*1000000 + episode*100, operation seed +1. Samples every 1 unit.

Stability grid: 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85 times analytical throughput; 4 episodes each, combined feedback, arrivals until 100*T, simulation to 400*T. A point qualifies if all cases finish, no sampled WIP >= 10*S lasts at least 20*T, and the mean WIP over [75*T,100*T) exceeds that over [50*T,75*T) by no more than S. Select the largest contiguous qualifying point from the bottom. If the bottom fails, record calibration failure, do not tune it using method performance. Stability seeds 71000000000+process*1000000+grid_index*1000+episode*10, operation seed+1.

Normal/pre-crisis calibration later uses rates [0.4,0.6,0.8,1.0] times this safe rate, twice each, arrivals until 40*T and drain to 300*T. Validation rates [0.5,0.7,0.9], same duration and drain. Any violations are recorded for every fit and no fit is replaced or excluded for decision performance.

Policy thresholds = [2*S,4*S,8*S], two consecutive observations dt=0.5*T. Severe event = WIP>=10*S continuously on sampled observations for 20*T. P0 untouched. Intervention prices remain 2 per unit time for one worker and 0.5 per unit time for rework reduction. The horizon cost includes terminal unfinished cases through WIP but no new terminal penalty.

Planning: baselines [0.7,0.9]*safe rate; no pulse, pulse [20*T,30*T) at 1.1*nominal throughput, pulse [20*T,40*T) at 1.5*nominal throughput; horizon 140*T, two repeats per condition.
Testing: baselines [0.75,0.95]*safe rate; no pulse, pulse [35*T,50*T) at 1.35*nominal throughput, pulse [35*T,60*T) at 1.65*nominal throughput; horizon 180*T, eight repeats per condition. Truth-only stress characterization uses separate seeds 72000000000+process*1000000+world*10000+condition*100+repeat*10, four repeats, also checks drainage after arrivals cease by 600*T. All characterization outcomes are retained. They do not determine which methods or structures are reported. If a structure produces no severe events, report that rather than adjusting its generator after seeing method decisions.

P4 process streams have independent Poisson draws, equal mixture and shared observed pools. P2 additional case-mix robustness uses fraction 0.65 complex instead of 0.35 with frozen main policies, separately labeled. No method is selected by stress characterization.
