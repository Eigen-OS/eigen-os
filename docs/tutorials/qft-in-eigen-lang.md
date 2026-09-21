# QFT in Eigen-Lang: from job.yaml to results

## 1. Source

The complete circuit is in `examples/quantum/qft/program.eigen.py`. Eigen-Lang
supports statically bounded `for` loops over `range`, integer constant folding,
`pi`, native `h`, `cp`/`crz`, and `swap`.

## 2. Submit

```bash
eigen submit -f examples/quantum/qft/job.yaml
```

## 3. Watch

```bash
eigen watch <job_id>
```

The expected terminal state is `DONE`.

## 4. Results

```bash
eigen results <job_id>
```

For 16 qubits and 16,384 shots, the regression summary checks at least 14,000
nonzero bitstrings, no dominant state above six shots, and a chi-square p-value
above 0.01 against the uniform 65,536-state distribution.

## Logical operation accounting

- `range(16)` emits 16 `H` operations.
- The triangular inner loop emits `16*15/2 = 120` `CP` operations.
- `range(16 // 2)` emits 8 `SWAP` operations.
- The logical operation count is therefore `144`; backend decomposition is not
  reflected in the compiler's logical count.
