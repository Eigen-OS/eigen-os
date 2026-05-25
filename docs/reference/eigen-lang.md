# Eigen-Lang Reference Guide (Version 1.0)

**Eigen-Lang** is a declarative, domain-specific language based on Python for describing hybrid quantum-classical problems. Programs written in Eigen-Lang describe *what* must be computed and *which results* are required, rather than *how* quantum and classical operations should be arranged. Eigen-Lang compiles to **AQO** (Abstract Quantum Operations) and interacts with the operating system kernel to execute the task on a quantum/classical backend.

- **Specification completeness:** This guide defines the full syntax, semantics, and standard library of Eigen-Lang version 1.0, and aligns with the requirements of the technical specification (version 1.3.0).

- **Contracts:** It defines input structures and the expected behavior of the compiler, validation layer, and type system. Special attention is given to security and determinism: dynamic Python constructs are prohibited, and compilation is always deterministic.

- **Tooling:** Eigen-Lang implementations are supported by a conformance test suite and specification versioning mechanisms. Any language changes must go through an RFC process and an updated test suite.

## 1. Syntax

Eigen-Lang version 1.0 uses Python syntax. A program is a file, preferably with the extension `.eigen.py`, containing exactly one function decorated with `@hybrid_program`. All instructions are executed in the context of this function. Example of a valid file:

```python
from eigen_lang import hybrid_program, Param, rx, ry, rz, cx

@hybrid_program(compiler="eigen", target="simulator", shots=1024, optimization_level=2)
def main():
    theta = Param("theta", 0.1)
    rx(0, theta)
    ry(1, 0.2)
    cx(0, 1)
    rz(1, theta)
    return {"result": ExpectationValue(Observable(Z=0), shots=None)}
```

### Main syntax rules

- **Single entrypoint:** A program must contain exactly one `@hybrid_program(...)` decorator. If there are zero or more than one entrypoints, compilation fails with a validation error.

- **Naming:** The entrypoint function name must be a valid Python identifier. Function arguments are optional and may be used in `Param`.

- **Imports:** Only safe imports from the `eigen_lang` package are allowed (see the “Standard Library” section). All other imports are forbidden.

- **Literals:** Numeric literals (`int`, `float`) and string literals are allowed. Dynamic code execution is not permitted.

- **Control flow:** All control-flow constructs (`if`, `for`, `while`, `match`, etc.) are prohibited in the MVP version of the language. The compiler rejects them as nondeterministic. There is a possibility of allowing statically resolvable loops/conditions in the future, but they are not supported in version 1.0.

- **Allowed AST nodes:** Only the AST nodes required for declarative description of circuits and parameters are allowed: function definitions, `return`, assignments, function calls, literals, names, and permitted binary operations. Fixed-size containers (`list`, `tuple`, `dict`) with constant elements are supported for defining fixed parameter sets, dimensions, and similar constructs.

- **Resource limits:** Source code is limited by size and AST depth (for example, no more than 262,144 bytes and AST depth up to 200 nodes) to prevent compiler DoS attacks. These limits are strictly enforced during parsing.

### Errors and diagnostics

When syntax or language rules are violated, the compiler returns a structured error:

```json
{
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "Validation of Eigen-Lang source failed",
    "details": [
      {
        "field": "function",
        "message": "Missing @hybrid_program entrypoint"
      }
    ]
  }
}
```

- The `INVALID_ARGUMENT` code is used for all validation errors in source code.

- The `details` field contains objects with `field` (the syntax construct name) and `message` (the error description).

- Error messages and codes are stable across releases.

## 2. Semantics

Eigen-Lang defines a **hybrid DAG** (directed acyclic graph) of computation, consisting of quantum and classical nodes:

- **Quantum nodes:** describe quantum circuits (sequences of gates and measurements). In version 1.0, the compiler generates an equivalent circuit on quantum hardware from the declared description.

- **Classical nodes:** represent classical computations (functions, optimization steps, target-function evaluation). Python expressions (for example, matrix multiplication or optimization) are executed on the host.

- **Boundaries:** The connection between quantum and classical nodes is expressed through special markers and functions. For example, `ExpectationValue` defines a measurement request, and `minimize` defines an optimization loop.

### Execution model

1. **Parsing and analysis:** Source code is transformed into an AST and checked against the syntax rules in section 1. Semantic validation is performed (for example, verifying that all used identifiers are either declared or imported).

2. **Intermediate representation generation:** All valid language constructs (gates, registers, parameters, `Observable`, etc.) are translated into a unified internal representation (AQO)

3. **Quantum core:** Optimizations and backend mapping are applied to the generated AQO, after which the circuit is executed on a quantum device or simulator.

4. **Feedback:** Measurement results are returned to the client and also stored in the system journal and knowledge base.

### Determinism guarantees

- **Identical output:** For completely identical source code and settings (pseudo-random seed, target device, etc.), compilation always produces the same output data (AQO, hashes, etc.).

- **No hidden side effects:** The compiler does not execute arbitrary user Python code; it only analyzes its syntax. Therefore, there must be no hidden side effects or environment dependencies.

- **Stable errors:** Compilation and validation errors are deterministic — the same input always produces the same error.

### Language and environment boundaries

- **Job meta-fields:** Compilation parameters (job name, target device, number of shots, optimization level, noise model, etc.) are provided through the `@hybrid_program` decorator and additional function arguments. These data form a `JobSpec`, which is passed to the OS kernel.

- **Results:** The entrypoint function returns either structured data (`dict` with numeric values) or `ExpectationValue` objects that declare metrics to be computed. These values are collected by the OS kernel after execution.

- **Execution modes:** Classical and quantum parts may coexist within one script without explicit transitions; the system analyzes dependencies and constructs the execution DAG.

## 3. Allowed AST subset and constructs

To ensure compiler security and determinism, a strict allowlist of permitted constructs is defined. Below is what is supported in version 1.0, along with additional capabilities planned for the future.

### Allowed AST nodes (current implementation)

- `Module`, `FunctionDef`, `arguments`, `Return` — the basic program structure.

- `ImportFrom` — imports only from the official `eigen_lang` package and its standard-library subpackages.

- `Assign`, `AnnAssign` — simple assignments.

- `Expr` — a function call or standalone expression.

- `Name`, `Constant` — identifiers and literals.

- `Call` — function or constructor calls.

- Literal containers: `List`, `Tuple`, `Dict` — with supported elements (numbers, strings, `Param`, etc., without dynamic references).

- Arithmetic operations `BinOp`, `UnaryOp` — only with numeric literals and variables (for coefficients, indices, and similar values).

### Forbidden AST nodes

- **Dynamic code:** `exec`, `eval`, `compile` — usage is rejected.

- **Unsafe modules:** Access to system Python modules (`os`, `sys`, `subprocess`, etc.) is forbidden.

- **Control constructs:** Flow-control constructs (`If`, `For`, `While`, `Match`, etc.) are not supported, even though they may be allowed in a limited form in the future. Their use currently triggers a compilation error.

- Undeclared identifiers: Any identifier not imported from `eigen_lang` and not explicitly declared is treated as an error.

- Dynamic imports: The `__import__` operator and imports through variables are forbidden.

### Allowed calls

In version 0.x, the compiler allowed only a small set of functions (`rx`, `ry`, `rz`, `cx`, and parameter handlers). In version 1.0, the official set of allowed functions is significantly expanded (see the “Standard Library” section). Key entries include:

- **Gates and transformations:** `rx(qubit, theta)`, `ry(qubit, theta)`, `rz(qubit, theta)`, `cx(control, target)`, as well as additional future gates (for example, `h`, `cz`, `swap` when needed).

- **Register operations:** `QubitRegister(n)`, `ClassicalRegister(n)` — creation of quantum/classical registers (new capability).

- **Parameters:** `Param(name, init)` — declaration of a circuit parameter. Used to bind circuit parameters to internal names.

- **Ansatze:** `Ansatz([...])` — a template for building a parameterized block (gates will later be applied to it).

- **Annotated entrypoints:** `@quantum_circuit`, `@ansatz`, `@cost_function`, `@benchmark` — special decorators for auxiliary functions (currently used as helpers or to prepare tasks for the kernel).

- **Optimizers:** Built-in optimization methods and wrappers for SciPy/PyTorch (for example, `minimize` with different methods) — define the configuration for classical optimization.

- **Data loaders:** `load_dataset(source, format, split, cache)` — a unified interface for loading and preparing data from S3, HuggingFace, and other sources.

- **Standard functions:** `make_molecular_hamiltonian(molecule, basis)`, `create_ising_model_hamiltonian(params)`, `create_hea_ansatz(n_qubits, depth)`, `visualize_circuit(circuit)`, `profile_execution(job)`, and more. See the “Standard Library” section.

### Limits and validation

All of the above constructs and calls are strictly checked during compilation. On violation (for example, calling a forbidden function or exceeding numeric bounds), `INVALID_ARGUMENT` is raised. The reason is always explained with a message indicating the symbol and context.

## 4. Eigen-Lang Standard Library

Below are the key elements of the standard library (the current contractual implementation and purpose). They are imported from the `eigen_lang` package and are required for describing hybrid tasks.

### Decorators

- `@hybrid_program(compiler, target, shots, optimization_level, noise_model, ...)` — the mandatory main decorator. It defines task properties: compiler (usually `"eigen"`), backend, number of shots, optimization level, noise model, etc. The decorator parameters form the `JobSpec`.

- `@quantum_circuit` — decorator for an auxiliary function without optimization; used to define fixed circuits.

- `@ansatz` — marks a function as a parameterized circuit template.

- `@cost_function` — marks a function that computes the target function (`ExpectationValue`) for optimization.

- `@benchmark(dataset, model, metrics, target_backend, repetitions, ...)` — declaratively defines a parameterized benchmark run.

### Types and constructors

- `QubitRegister(n)` — creates a quantum register of `n` qubits (in the future this will influence physical-qubit allocation).

- `ClassicalRegister(n)` — creates a classical register of `n` bits.

- `Param(name, init)` — declares a circuit parameter with the given name and initial value.

- `Observable(**ops)` — defines an observable (Hamiltonian) as a sum of operators over qubits, for example `Observable(Z=0, X=1)`.

- `Ansatz(name, *args)` — describes a parameterized circuit (a state-preparation variant), for example `Ansatz("hea", depth=3)`.

- `QuantumModel(...)` and `SupervisedTask(...)` — types for more complex hybrid models (for future releases).

- `DatasetHandle` — the return type of dataset loading (see below).

### Quantum functions and gates

- `rx(qubit_index, theta)` — rotation around X.

- `ry(qubit_index, theta)` — rotation around Y.

- `rz(qubit_index, theta)` — rotation around Z.

- `cx(control_index, target_index)` — CNOT.

- *(Planned: `h`, `cz`, `swap`, `toffoli`, etc.)*

### Hybrid constructs

- `ExpectationValue(circuit, observable, shots=None)` — returns an expression denoting the computation of the expected value of an observable when the given circuit is run on a quantum device.

- `minimize(cost_function, initial_params, method, options)` — standard optimization (for example, COBYLA, L-BFGS) of the supplied target function. Returns the minimum value and the optimal parameters.

- `load_dataset(source, format="parquet", split="train", cache=True)` — loads a dataset from the specified source (for example, HuggingFace Hub, S3) and returns a `DatasetHandle` compatible with PyTorch `DataLoader`.

- `profile_execution(job_handle)` — profiles a previously submitted job.

- `visualize_circuit(circuit)` — renders a graphical representation of a quantum circuit.

### Built-in tools

- `make_molecular_hamiltonian(mol, basis)` — builds the Hamiltonian of a molecule in the specified basis.

- `create_ising_model_hamiltonian(params)` — builds the Hamiltonian of an Ising model with the given parameters.

- `create_hea_ansatz(n_qubits, depth)` — returns a standard Hartree-exponential ansatz.

- `wrap_optimizer(scipy_method)` — wrapper for connecting an external optimizer (SciPy, PyTorch, JAX, etc.).

These capabilities allow users to describe complex tasks without dealing with qubit layout details and quantum-device transaction management.

## 5. Mapping Eigen-Lang to AQO

During compilation, Eigen-Lang elements are translated into **AQO** (Abstract Quantum Operations), the intermediate representation of the quantum circuit. In version 1.0, the following mappings are implemented:

- **Gates and operations:** `rx`, `ry`, `rz`, `cx` are converted into AQO elements with fields `{op, q, params}`. For example:

    - `rx(0, theta)` → `{ "op": "RX", "q": [0], "params": {"theta": theta} }`

    - `cx(1, 2)` → `{ "op": "CX", "q": [1, 2] }`

- **Measurements:** After all gates, the compiler automatically appends a terminal `MEASURE` operation to all `QubitRegisters` (or after each ansatz, depending on strategy).

- **Parameters:** `Param("θ")` declarations bind parameter names to internal identifiers. Parameter values are substituted into AQO, or remain symbolic during optimization.

- **Observables:** `ExpectationValue` and `Observable` are not yet directly translated into quantum operators in the current version, but they are marked as requirements for the kernel: the system knows which Hamiltonian evaluation must be collected.

- **Ansatze:** Templates marked with `@ansatz` may be expanded into a sequence of gates during compilation. In the MVP version, this is partially implemented: ready-made ansatze from the standard library can be used.

The final AQO JSON contains the full instructions for the OS kernel: which gates to execute, in what order, and with what parameters.

### Encoding details

- The AQO format is specified in `docs/reference/formats/aqo.md` (which defines the JSON structure and fields).

- After AQO generation, checksums (`aqo_sha256`) are computed and metadata is added (program name, author, ansatz version, etc.).

- For distributed compilation, the sections `distributed_execution` and `topology_hints` are added (field versions are governed by `metadata.distributed.execution_metadata_version`).

- **Important:** AQO JSON is a coherent contract. Any format changes must be accompanied by a contract version update (see `versioning.md`).

## 6. Conformance Suite

The conformance test suite ensures that the compiler implementation follows the language specification.

- **Golden tests:** For typical `program.eigen.py` examples, expected AQO JSON outputs are defined. Any change in AQO output must be intentionally confirmed by updating test fixtures.

- **Negative tests:** Every forbidden language element (for example, a dynamic loop or unsupported syntax) has its own test expecting a specific `INVALID_ARGUMENT` error code and a textual description of the problematic field.

- **Migration scenarios:** New features (for example, a new decorator or gate) must have tests so that regressions are detected as the language evolves.

### Supported cases (v1.0)

- **Deterministic compilation:** Recompiling the same code produces identical AQO output (byte-for-byte equality).

- **Hashes:** The `aqo_sha256` field in metadata must exactly match the SHA-256 of the AQO bytes.

- **No “hidden” gates:** The compiler must not add extra quantum operations. For example, an empty function `def f(): pass` produces only `MEASURE` in AQO.

- **Defined validations:** Missing input data, invalid `JobSpec` structure, or invalid parameter values are all tested.

### Gaps and tasks (to-do)

Some aspects of the language are not yet covered by tests:

- Full mapping of new constructs (`ExpectationValue`, `minimize`, imports from external modules, etc.).

- Distributed options (`distributed_execution` sections) are only partially covered.

- Performance/limit tests (maximum program size) need to be added.

- Real integration scenarios (from `SubmitJob` to `GetJobResults`) are outside the scope of this suite for now.

Any language update is accompanied by a **Golden update process:** test rebuilds and an explicit description of fixture changes in the pull request.

## 7. Versioning and Compatibility

Eigen-Lang stores a specification version of the form `eigen-lang-spec: 1.0.` Compatibility policy:

- **Major versions (1.0 → 2.0):** incompatible changes are allowed (new major capabilities or removal of old constructs). Major updates must be accompanied by migration documentation and backward-compatibility support.

- **Minor versions (1.x → 1.x+1):** extensions that do not break existing programs are allowed (new optional functions, fields, or simplifications of options). Existing functionality must remain operational.

- **Patch (1.0.x):** only bug fixes and specification clarifications; backward compatibility must be preserved.

Distributed compilation metadata: every element passed in `distributed_execution` or `topology_hints` includes a version. This allows new fields to be introduced gradually without breaking compatibility.

Change process: Any language changes must go through the RFC procedure: proposal, code review, test updates. Before public release, backward compatibility is conformance-tested in CI.
