# Research methodology and limits

## Physical model

All internal quantities use SI units; reported rotational speed uses rpm. `ω=2πN/60`, `P=τω`, and `P=√3 VI PF` describe a balanced sinusoidal supply. A first-order ideal speed servo has a two-second time constant; torque is computed from `J Δω/Δt + τ_resistive`, with equivalent inertia 0.8 kg m². Midpoint angular velocity makes the kinetic energy balance exact for each step. Gear ratio is 15 and pulley radius is 0.12 m. Gear input power is belt output / transmission efficiency plus viscous friction power. Friction heat is assigned to the gearbox. A 90 W auxiliary loss is included in motor heat. Efficiency depends on speed and torque, and motor faults reduce that efficiency. These are research assumptions rather than calibrated plant parameters.

First-order thermal nodes integrate loss heat minus ambient cooling, using 8000/5000 J/K heat capacities and 12/9 W/K cooling conductances. Measurement noise is separate from energy-balance ground truth. Abnormal load represents unmeasured additional belt loading; the load sensor reports the commanded/nominal load. Sensor failure initially targets the power meter. Vibration is a phenomenological RMS proxy, not an acceleration waveform.

## Learning and evaluation

Only the explicit `FEATURES` allowlist enters models. Hidden faults, labels, efficiencies, and severity are excluded. Expected power is computed from measured speed/load/acceleration and healthy equations. Train and healthy validation rows come from separate simulation runs; test and OOD runs are disjoint. OOD uses speeds 450/1750 rpm, loads 150/180 kg, and severity 0.9, outside training choices.

Isolation Forest and autoencoders train only on healthy training rows. All thresholds use the 99th percentile of healthy validation scores. The physics baseline combines normalized power and three-phase consistency residuals. The hybrid is an actual neural reconstruction model trained with `MSE + λ L_physics`. Physics terms enforce reconstructed three-phase power and healthy expected input power, both normalized by 1000 W. A λ=0 network with identical initialization is the ablation. Residual-score fusion averages threshold-normalized physics and autoencoder scores. Online alerts require three consecutive hybrid threshold crossings; reported offline point metrics intentionally omit persistence.

The supervised random forest trains on simulated faulty training rows and reports component macro-F1 separately from rule localization. Rules use electrical consistency, load-conditioned torque, vibration, and residual power. Ambiguous rule evidence returns unknown. Rule scores and raw classifier outputs are not calibrated causal probabilities. A component confusion matrix and per-class report are exported.

Evaluate precision, recall, F1, PR-AUC, ROC-AUC, false positive rate, component macro-F1, baseline energy prediction MAE/RMSE (W), reconstructed three-phase constraint violation (W), and inference latency. Each model's score computation is timed on its evaluation batch, excluding shared scaling; fusion timing sums its two underlying model computations. Full-suite latency is recorded separately. These amortized batch timings are not real-time single-sample deployment benchmarks. Repeated-seed results report sample SD, not a confidence interval. Synthetic seeds vary measurements and operating conditions; they are not independent physical machines.

## Interpretation

Positive power residuals are accumulated as Wh using dt/3600 and clipped at zero. They quantify excess relative to a healthy reference, not recoverable savings. Healthy noise also contributes positive residuals. Operating efficiency is integrated useful mechanical output / positive electrical input. Faulty power-meter readings can make this estimate unreliable.

The simulation's healthy equations also appear in the hybrid loss, creating favorable structural knowledge unavailable in an unknown real plant. Synthetic model comparison cannot establish external validity. Thermal residuals, uncertainty-aware constraints, λ selection over multiple validation candidates, more detailed electrical motor dynamics, and robust waveform domain transfer remain research extensions. Hybrid superiority must be assessed from saved results rather than assumed.
