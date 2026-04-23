# Minimal Eigen-Lang source used for conformance golden checks.
circuit main {
  qubit q0
  ry(q0, theta=1.570796)
  measure(q0)
}
