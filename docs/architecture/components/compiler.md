# Eigen Compiler Frontend

## Responsibility

The **Eigen Compiler Frontend** is the input module of the Eigen OS neuro-symbolic compiler, responsible for transforming high-level Eigen-Lang programs into structured intermediate representations (AST) for subsequent processing. Its primary responsibilities include:

- **Syntactic Analysis**: Parsing Eigen-Lang source code (Python DSL) into tokens and abstract syntax trees

- **Semantic Validation**: Type checking, scope resolution, and validation of quantum-specific constructs

- **AST Generation**: Creating annotated abstract syntax trees with complete metadata

- **Type System Integration**: Managing quantum and classical type systems with compatibility checking

- **Error Diagnostics**: Providing detailed error messages with source context

- **Integration Preparation**: Preparing AST for neuro-symbolic compiler backend processing

- **Plugin System**: Supporting extensible syntax through plugin architecture

- **Incremental Compilation**: Supporting partial recompilation for development environments

## Interfaces

### Public API (RPC - RFC 0004)
```protobuf
service CompilationService {
  rpc CompileCircuit(CompileCircuitRequest) returns (CompileCircuitResponse);
  rpc OptimizeCircuit(OptimizeCircuitRequest) returns (OptimizeCircuitResponse);
  rpc ValidateCircuit(ValidateCircuitRequest) returns (ValidateCircuitResponse);
}
```

### Internal APIs (Within Frontend)

**Lexer Interface:**
```python
class EigenLexer:
    def tokenize(self, source_code: str) -> List[Token]:
        """Convert source code to tokens with source positions"""
```

### Parser Interface:
```python
class EigenParser:
    def parse(self, source_code: str) -> ProgramNode:
        """Parse source code into AST"""
    
    def parse_decorator(self, decorator_token: Token) -> DecoratorNode:
        """Parse @hybrid_program, @quantum_circuit, @ansatz decorators"""
```

### Semantic Analyzer Interface:
```python
class SemanticAnalyzer:
    def analyze(self, ast: ProgramNode) -> AnnotatedAST:
        """Perform semantic analysis and type checking"""
    
    def infer_type(self, node: ASTNode) -> Type:
        """Type inference for expressions"""
```

### Type System Interface:
```python
class TypeSystem:
    def is_compatible(self, source: Type, target: Type) -> bool:
        """Check type compatibility with quantum type rules"""
    
    def is_quantum_type(self, type_: Type) -> bool:
        """Check if type is quantum (Qubit, Observable, etc.)"""
```

### Error Handler Interface:
```python
class ErrorHandler:
    def add_error(self, error: CompilationError):
        """Record compilation error"""
    
    def report(self) -> str:
        """Generate formatted error report with source context"""
```

### Plugin System Interface:
```python
class FrontendPlugin:
    def extend_parser(self, parser: EigenParser):
        """Add custom parsing rules"""
    
    def extend_semantic(self, analyzer: SemanticAnalyzer):
        """Add custom semantic analysis rules"""
```

### Knowledge Base Integration:
```python
class KnowledgeBaseIntegration:
    def augment_ast_with_knowledge(self, ast: ASTNode) -> EnhancedAST:
        """Enrich AST with information from compiler knowledge base"""
```

### File Interfaces

- **Configuration**: `configs/default/frontend.yaml` - Frontend behavior configuration

- **Grammar Definitions**: Internal grammar specifications for Eigen-Lang

- **Type Definitions**: Built-in type definitions (quantum and classical)

## Inputs / Outputs

### Inputs

1. **Source Code**: Eigen-Lang program as UTF-8 encoded string

    - Syntax: Python DSL with quantum extensions

    - Decorators: `@hybrid_program`, `@quantum_circuit`, `@ansatz`, `@cost_function`

    - Types: `Qubit`, `QubitRegister`, `Observable`, `Ansatz`, `Param`

    - Constructs: `ExpectationValue`, `minimize`, quantum gate operations

2. **Configuration**: YAML configuration file controlling:

    - Parsing options (max AST depth, allowed dynamic types)

    - Semantic analysis settings (strict mode, implicit conversions)

    - Quantum extensions (supported gates, custom gates)

    - Optimization flags (constant folding, dead code elimination)

    - Integration settings (neuro-compiler endpoint, knowledge base cache)

3. **Integration Context**:

    - Knowledge base connection for gate information and patterns

    - Neuro-compiler endpoint for advanced compilation

    - Target device characteristics for optimization hints

### Outputs

1. **Annotated AST**: Rich syntax tree with:
```python
@dataclass
class AnnotatedAST:
    ast: ProgramNode                    # Base AST structure
    symbol_table: SymbolTable           # Resolved symbols and scopes
    type_annotations: Dict[ASTNode, Type]  # Type information per node
    metadata: Dict[str, Any]            # Compilation metadata
    errors: List[CompilationError]      # Any compilation errors
    warnings: List[CompilationWarning]  # Non-fatal warnings
```

2. **Intermediate Representation**: AQO (Abstract Quantum Operations) format
```json
{
  "version": "1.0",
  "metadata": {
    "quantum_operations": 42,
    "parameter_count": 8,
    "circuit_depth": 12,
    "resource_estimates": {...}
  },
  "operations": [
    {
      "type": "GATE",
      "name": "RX",
      "qubits": [0],
      "parameters": ["theta_0"],
      "conditions": null
    }
  ],
  "symbol_table": {...},
  "type_info": {...}
}
```

3. **Error Reports**: Structured error information with source context
```text
ERROR at line 10, col 15: Unknown quantum gate: 'FTL'

    9 |     H(q[0])
    10|     FTL(q[0])  <-- Error here
       |     ^
    11|     CX(q[0], q[1])
```

4. **Performance Metrics**: Cache statistics, parsing times, memory usage

5. **Export Formats** (optional):

- JSON: For debugging and external tool integration

- Protobuf: For efficient serialization and transmission

- Graphviz: For visualization of AST and data flow

## Storage / State

### In-Memory State

1. **AST Cache** (LRU cache):
```python
class ASTCache:
    def __init__(self, max_size: int = 100):
        self.cache = LRUCache(max_size)  # Key: source_hash -> Value: ASTNode
        self.stats = CacheStats()        # hits, misses, evictions
```

- Caches parsed ASTs by source code hash

- Configurable maximum size (default: 100 entries)

- Statistics for performance monitoring

2. **Symbol Tables:**
```python
class SymbolTable:
    def __init__(self):
        self.scopes: List[Dict[str, Symbol]] = []  # Stack of scopes
        self.globals: Dict[str, Symbol] = {}       # Global symbols
```

- Hierarchical scope management during semantic analysis

- Tracks variables, functions, quantum registers, parameters

3. **Type Information:**
```python
class TypeInfo:
    def __init__(self):
        self.node_types: Dict[ASTNode, Type] = {}  # Type for each AST node
        self.type_constraints: List[Constraint] = []  # Type constraints to solve
```

4. **Plugin Registry:**
```python
class PluginRegistry:
    def __init__(self):
        self.plugins: Dict[str, FrontendPlugin] = {}
        self.extended_syntax: Dict[str, SyntaxExtension] = {}
```

### File System Storage

1. **Configuration Files:**

    - `configs/default/frontend.yaml`: Default configuration

    - User-specific overrides: `~/.config/eigen/frontend.yaml`

2. **Cache Directory:**

    - Location: `~/.cache/eigen/frontend/`

    - Contents: Serialized ASTs, precomputed type information

    - Management: Automatic cleanup based on LRU policy

3. **Log Files:**

    - Location: `logs/frontend/`

    - Formats: JSON logs for structured processing

    - Rotation: Daily rotation with compression

### QFS Integration (CircuitFS)

1. **Temporary Storage** during compilation:
```text
circuit_fs/<job_id>/frontend/
├── raw_source.eigen.py           # Original source
├── tokens.json                   # Token stream (debug)
├── ast_initial.json              # Initial AST before analysis
├── ast_annotated.json            # Final annotated AST
├── symbol_table.json             # Complete symbol table
└── type_analysis.json            # Type inference results
```

2. **Cache in QFS** (optional):

- Shared AST cache across multiple compilation jobs

- Keyed by source hash for deduplication

- Configurable TTL and eviction policies

## State Transitions

1. **Initialization → Parsing → Semantic Analysis → Output Generation**

2. **Error Recovery States:**

    - Continue after non-fatal errors

    - Fallback to simplified parsing on resource exhaustion

    - Graceful degradation when integrations fail

## Failure Modes

### 1. Syntax Errors

- **Cause**: Malformed Eigen-Lang source code

- **Detection**: Parser fails to match grammar rules

- **Recovery**: Attempt error recovery by skipping tokens, continue parsing

- **User Impact**: Compilation fails with detailed error location

- **Example**: ``SyntaxError: Unexpected token '}' at line 5, column 10``

### 2. Semantic Errors

- **Type Errors:**

    - Cause: Type mismatches (e.g., classical value used as qubit)

    - Detection: Type system compatibility check fails

    - Example: ``TypeError: Expected Qubit, got int``

- **Scope Errors:**

    - Cause: Undefined variables, duplicate declarations

    - Detection: Symbol table lookup fails

    - Example: ``NameError: Variable 'theta' not defined``

- **Quantum-Specific Errors:**

    - Cause: Invalid quantum operations (wrong number of qubits, unsupported gates)

    - Detection: Knowledge base validation fails

    - Example: ``QuantumError: Gate 'RX' requires 1 parameter, got 0``

### 3. Resource Exhaustion

- **AST Depth Limit:**

    - Cause: Program exceeds `max_ast_depth` configuration

    - Detection: Recursion depth counter

    - Recovery: Fail early with clear message

    - Mitigation: Increase limit in configuration

- **Memory Limits:**

    - Cause: Very large programs or complex type inference

    - Detection: Memory monitoring

    - Recovery: Garbage collection, partial compilation

    - Mitigation: Stream processing for large files

### 4. Integration Failures

- **Knowledge Base Unavailable:**

    - Cause: Network issues, service down

    - Detection: Connection timeout or error response

    - Recovery: Use cached data, continue without enhancements

    - Fallback: Built-in gate definitions only

- **Neuro-Compiler Unavailable:**

    - Cause: gRPC connection failure

    - Detection: Connection timeout

    - Recovery: Classical compilation fallback

    - Impact: Loss of neuro-symbolic optimizations

### 5. Configuration Errors

- **Invalid Configuration:**

    - Cause: Malformed YAML, unsupported options

    - Detection: Configuration validation

    - Recovery: Use default configuration with warning

    - Logging: Detailed validation errors

### 6. Plugin Failures

- **Plugin Loading Errors:**

    - Cause: Missing dependencies, version conflicts

    - Detection: Import errors during plugin registration

    - Recovery: Skip failing plugin, continue with others

    - Logging: Plugin load errors with stack traces

- **Plugin Runtime Errors:**

    - Cause: Bugs in plugin code during parsing/semantic analysis

    - Detection: Exception during plugin execution

    - Recovery: Disable plugin for current compilation

    - Isolation: Plugin sandboxing (optional)

### 7. Performance Degradation

- **Slow Parsing:**

    - Cause: Pathological source code patterns

    - Detection: Timeout monitoring

    - Recovery: Abort compilation, suggest simplifications

    - Monitoring: Performance metrics collection

### 8. Data Corruption

- **Cache Corruption:**

    - Cause: Disk errors, version mismatches

    - Detection: Checksum validation on cache load

    - Recovery: Clear cache, reparse from source

    - Prevention: Regular cache validation

## Error Classification
```python
class ErrorSeverity(Enum):
    INFO = "info"           # Informational messages
    WARNING = "warning"     # Non-fatal issues
    ERROR = "error"         # Compilation stops
    FATAL = "fatal"         # Internal error, bug report needed

class ErrorCategory(Enum):
    SYNTAX = "syntax"       # Parser errors
    SEMANTIC = "semantic"   # Type/scope errors
    RESOURCE = "resource"   # Memory/time limits
    INTEGRATION = "integration"  # External service failures
    CONFIG = "configuration"  # Configuration issues
    PLUGIN = "plugin"       # Plugin-related errors
```

### Error Recovery Strategies

1. **Best Effort Parsing**: Continue after syntax errors when possible

2. **Partial Compilation**: Compile valid parts, report errors for invalid parts

3. **Graceful Degradation**: Fallback to simpler compilation paths

4. **Cached Results**: Use previous successful compilations when safe

5. **User Feedback**: Suggest fixes based on common error patterns

### Monitoring and Alerting

- **Error Rate Alerts**: High frequency of specific error types

- **Performance Alerts**: Significant slowdown in compilation

- **Integration Health**: Knowledge base/neuro-compiler availability

- **Resource Usage**: Memory/CPU thresholds exceeded

## Observability

### Metrics

**Compilation Metrics:**
```text
# Compilation success/failure rates
eigen_compiler_frontend_compilations_total{status="success"} 1234
eigen_compiler_frontend_compilations_total{status="failure"} 56
eigen_compiler_frontend_compilations_total{status="partial"} 12

# Compilation duration
eigen_compiler_frontend_compilation_duration_seconds_bucket{le="0.1"} 1000
eigen_compiler_frontend_compilation_duration_seconds_bucket{le="0.5"} 1500
eigen_compiler_frontend_compilation_duration_seconds_bucket{le="1.0"} 1800

# Error type distribution
eigen_compiler_frontend_errors_total{category="syntax"} 25
eigen_compiler_frontend_errors_total{category="semantic"} 18
eigen_compiler_frontend_errors_total{category="type"} 42

# Cache performance
eigen_compiler_frontend_cache_hits_total 850
eigen_compiler_frontend_cache_misses_total 150
eigen_compiler_frontend_cache_hit_ratio 0.85

# Resource usage
eigen_compiler_frontend_memory_bytes 256000000
eigen_compiler_frontend_ast_nodes_total 12500
```

**Performance Metrics:**

- Parsing phase duration

- Semantic analysis duration

- Type inference duration

- AST traversal counts

- Memory allocation patterns

## Logging

**Structured Log Format** (JSON):
```json
{
  "timestamp": "2024-01-10T10:30:00Z",
  "level": "INFO",
  "service": "eigen-compiler-frontend",
  "component": "parser",
  "trace_id": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01",
  "span_id": "00f067aa0ba902b7",
  "job_id": "job_123456",
  "event": "parse_complete",
  "duration_ms": 45,
  "source_lines": 150,
  "ast_nodes": 1200,
  "tokens": 4500,
  "cache_hit": true
}
```

**Log Categories:**

1. **Debug Logs**: Detailed parsing steps, token streams, AST transformations

2. **Info Logs**: Compilation milestones, configuration changes, cache operations

3. **Warning Logs**: Non-fatal issues, deprecated features, performance hints

4. **Error Logs**: Compilation failures with full context

5. **Audit Logs**: Configuration changes, plugin loading, security events

**Log Configuration:**
```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "json"  # json, text, structured
  destination: "file"  # file, stdout, syslog
  file:
    path: "/var/log/eigen/frontend.log"
    max_size: "100MB"
    backup_count: 10
  structured_fields:  # Always include these fields
    - "trace_id"
    - "job_id"
    - "component"
    - "duration_ms"
```

## Tracing

### OpenTelemetry Integration:

- **Trace Propagation**: W3C TraceContext via traceparent header

- **Span Creation**: Each compilation phase creates a span

- **Span Attributes**:

    - `source.size_bytes`: Size of source code

    - `ast.node_count`: Number of AST nodes generated

    - `error.count`: Number of errors encountered

    - `cache.status`: Hit/miss status

- **Span Events**: Key milestones (parse_start, semantic_start, etc.)

### Trace Sampling:

- Always sample traces for failed compilations

- Sample rate for successful compilations configurable (default: 10%)

- Head-based sampling for distributed context

## Health Checks

### Readiness Probe:
```python
class FrontendHealth:
    def check_ready(self) -> HealthStatus:
        return HealthStatus(
            healthy=True,
            components={
                "parser": self.parser.ready(),
                "type_system": self.type_system.initialized(),
                "cache": self.cache.available(),
                "knowledge_base": self.kb_conn.connected()
            }
        )
```

### Liveness Probe:

- Memory usage below threshold

- No deadlocks in parsing threads

- Responsive to simple compilation requests

## Dashboards and Visualization

### Grafana Dashboards:

1. Compilation Overview:

    - Success rate over time

    - Average compilation duration

    - Error rate by category

    - Cache hit ratio

2. Performance Analysis:

    - Phase duration breakdown

    - Memory usage over time

    - AST complexity metrics

    - Token/line processing rates

3. Error Analysis:

    - Error frequency by type

    - Common error patterns

    - Source lines with frequent errors

    - User impact analysis

4. Resource Monitoring:

    - CPU usage during compilation

    - Memory allocation patterns

    - Cache efficiency metrics

    - Disk I/O for large compilations

### AST Visualization (Optional):

- Graphviz export for AST structure

- Interactive web visualization for debugging

- Highlighting of type-annotated nodes

- Dependency graph visualization

## Alerting Rules

**Critical Alerts** (PagerDuty/Slack):

- Compilation success rate < 95% for 5 minutes

- Memory usage > 90% for 2 minutes

- Knowledge base unavailable for 1 minute

- Multiple consecutive compilation failures

**Warning Alerts** (Email/Slack):

- Cache hit ratio < 80% for 10 minutes

- Average compilation time increased by 50%

- Warning count increased significantly

- Plugin loading failures

## Integration with Eigen OS Observability Stack

1. **Metrics Endpoint**: `:9091/metrics` (Prometheus format)

2. **Log Aggregation**: Forward to Loki/Fluentd

3. **Trace Export**: Export to Jaeger/Tempo

4. **Correlation**: Use `trace_id` and `job_id` for cross-service correlation

## Debugging Support

1. **Verbose Mode**: Detailed logging for specific compilation jobs

2. **AST Inspection**: Export AST at various stages for debugging

3. **Profile Generation**: Performance profiles for slow compilations

4. **Error Reproduction**: Capture and replay problematic compilations

5. **Interactive Debugger**: Step-through debugging of parsing process (development)

## Audit Trail

1. **Configuration Changes**: Log all configuration modifications

2. **Plugin Management**: Track plugin loading/unloading

3. **Security Events**: Authentication/authorization for privileged operations

4. **Data Access**: Log access to sensitive source code or compilation results

## Performance Monitoring

**Key Performance Indicators:**

- **Throughput**: Compilations per second

- **Latency**: P50, P90, P99 compilation times

- **Efficiency**: Memory per AST node, CPU per line of code

- **Scalability**: Performance under concurrent load

**Resource Utilization:**

- Memory usage patterns during different phases

- CPU utilization during parsing vs semantic analysis

- Disk I/O for cache operations

- Network I/O for knowledge base integration