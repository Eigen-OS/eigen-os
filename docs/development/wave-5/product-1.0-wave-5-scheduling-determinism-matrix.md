# Product 1.0 Wave 5 Scheduling Determinism Matrix

| Scenario | Input stability | Expected output stability | Notes |
|---|---:|---:|---|
| identical inventory snapshot | yes | same ranking / decision | policy version fixed |
| same job, same queue pressure | yes | same placement | fairness rules stable |
| same job, changed deadline | no | permitted change | must be versioned |
| same job, changed policy version | no | permitted change | migration notes required |
| replay of recorded decision | yes | identical rationale | audit lineage required |
