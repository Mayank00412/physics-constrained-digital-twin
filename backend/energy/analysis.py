class Energy:
    def __init__(self): self.excess_wh=self.input_wh=self.output_wh=0.
    def update(self,s,dt):
        residual=s['power']-s['expected_power']
        self.excess_wh+=max(residual,0)*dt/3600
        self.input_wh+=max(s['power'],0)*dt/3600
        self.output_wh+=max(s['mechanical_power'],0)*dt/3600
        return dict(actual_power=s['power'],expected_power=s['expected_power'],residual=residual,
            relative_deviation=residual/max(s['expected_power'],1),excess_wh=self.excess_wh,
            efficiency=self.output_wh/max(self.input_wh,1e-9),baseline_notice='Positive residual energy is not verified recoverable savings.')
