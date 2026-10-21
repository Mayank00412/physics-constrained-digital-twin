import math

def diagnose(s,detected):
    electrical=math.sqrt(3)*s['voltage']*s['current']*s['power_factor']
    consistency=abs(s['power']-electrical)/max(electrical,100)
    residual=(s['power']-s['expected_power'])/max(s['expected_power'],100)
    scores=dict(sensor=min(1,consistency*8),gearbox=min(1,max(0,s['vibration']-.35)),
        motor=min(1,max(0,residual)*2),conveyor=min(1,max(0,s['gearbox_output_torque']-(25+.035*s['load']*9.81+3*s['conveyor_speed'])*.12)/15))
    order=sorted(scores,key=scores.get,reverse=True)
    likely=order[0] if detected and scores[order[0]]>.3 else 'unknown'
    if detected and scores[order[0]]-scores[order[1]]<.12: likely='unknown'
    return dict(component=likely if detected else 'healthy',scores=scores,diagnostic_score=max(scores.values()),
        candidate_fault={'motor':'efficiency degradation','gearbox':'friction or degradation','conveyor':'resistance or loading','sensor':'measurement inconsistency'}.get(likely,'ambiguous'),
        explanation='Rule scores are uncalibrated evidence, not causal probabilities. Motor and transmission losses may be indistinguishable.',
        evidence=dict(power_residual_w=s['power']-s['expected_power'],electrical_consistency=consistency,vibration=s['vibration']))
