# Eigen-Lang API Reference

Eigen-Lang is a declarative domain-specific language for hybrid quantum-classical programming.

## Quick Start
```python
import eigen_lang as el

# Basic types
qr = el.QubitRegister(5)
cr = el.ClassicalRegister(5, "results")
theta = el.Param("θ", bounds=(0, 2*math.pi))

# Create a hybrid program
@el.hybrid_program(target="simulator")
def solve_problem():
    # Program logic here
    return result
```
# Core Types

## QubitRegister
```python
class QubitRegister(n_qubits: int)
```
Attributes: *.size, .id*

## ClassicalRegister
```python
class ClassicalRegister(n_bits: int, name: str | None = None)
```
Methods: *update(), reset()*

## Param
```python
class Param(name: str, bounds: tuple[float, float] | None = None)
```
Attributes: *.name, .bounds, .value*

## Observable
```python
class Observable(pauli_string: str | None = None, coeff: float = 1.0)
```
Methods: *__add__(), __mul__(), expectation()*

## Ansatz (Base Class)
```python
class Ansatz(n_qubits: int, params: list[Param] | None = None)
```
Attributes: *.n_qubits, .num_params, .depth*
Abstract Method: *_build_circuit()*

# Decorators

## @hybrid_program

Main decorator for hybrid quantum-classical programs.
```python
@hybrid_program(
    compiler: str = "eigen",
    target: str = "simulator",
    shots: int = 1024,
    optimization_level: int = 2
)
```

## @quantum_circuit

Decorator for static quantum circuits.
```python
@quantum_circuit(
    name: str | None = None,
    compile: bool = True,
    optimize: bool = True
)
```

## @ansatz

Decorator for parameterized quantum circuits.
```python
@ansatz(
    n_qubits: int,
    name: str | None = None,
    param_names: list[str] | None = None,
    symmetric: bool = False
)
```

## @cost_function

Decorator for cost functions (expectation values).
```python
@cost_function
```

# Constructors

## minimize()

Optimization task constructor.
```python
def minimize(
    objective: Callable[[list[float]], ExpectationValue | float],
    initial_guess: list[float],
    method: str = "gradient_descent",
    bounds: list[tuple[float, float]] | None = None,
    max_iter: int = 100
) -> OptimizationResult
```

## ExpectationValue()

Creates expectation value computations
```python
def ExpectationValue(
    circuit_or_ansatz: QuantumCircuit | Ansatz,
    observable: Observable,
    shots: int | None = None,
    use_parameter_shift: bool = True
) -> ExpectationValue
```

## QuantumModel()

Quantum machine learning model constructor.
```python
def QuantumModel(
    feature_map: str | Callable | QuantumCircuit,
    ansatz: str | Ansatz | Callable,
    objective: str = "mse",
    task_type: str = "regression"
) -> QuantumModel
```

## SupervisedTask()

Supervised learning task constructor.
```python
def SupervisedTask(
    model: QuantumModel,
    data: tuple[list, list],
    task_type: str = "classification"
) -> SupervisedTask
```

# Standard Library Functions

## Circuit Creation
```python
# Hardware-efficient ansatz
create_hea_ansatz(
    n_qubits: int,
    depth: int = 3,
    entanglement: str = "linear",
    rotations: str = "ry"
) -> Ansatz

# Ising model Hamiltonian
create_ising_model_hamiltonian(
    n_spins: int,
    J: float | list[list[float]] = 1.0,
    h: float | list[float] = 1.0,
    periodic: bool = True
) -> Observable

# Molecular Hamiltonian
make_molecular_hamiltonian(
    molecule: str,
    basis: str = "sto-3g",
    charge: int = 0,
    spin: int = 0
) -> Observable
```

## Compilation
```python
# Compile to QASM
compile_to_qasm(
    circuit: QuantumCircuit | Callable,
    optimization_level: int = 2,
    target_backend: str | None = None
) -> str
```

## Utilities
```python
# Load datasets
load_dataset(
    name: str,
    n_samples: int | None = None,
    test_size: float = 0.2
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]

# Get program AST
get_program_ast(
    program_func: Callable,
    include_metadata: bool = True,
    format: str = "dict"
) -> dict | str

# Visualize circuits
visualize_circuit(
    circuit: QuantumCircuit | Ansatz | Callable,
    params: list[float] | None = None,
    style: str = "iqx"
) -> None
```

# Examples Directory

See `examples/` for complete programs:

    *examples/basic/vqe_cycle/* - Variational Quantum Eigensolver

    *examples/basic/bell_state/* - Bell state creation and measurement

    *examples/basic/hello_quantum/* - Simple quantum program

    *examples/advanced/hybrid_workflow/* - Complex quantum-classical workflows

    *examples/advanced/custom_driver/* - Custom hardware driver examples
