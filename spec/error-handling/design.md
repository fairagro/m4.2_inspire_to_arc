# Harvester Error Handling — Design

## Exception Hierarchy

- `Exception`
  - `HarvesterError` (Core Harvester errors)
    - `RecordProcessingError` (Global standard for record-level failures)
    - `InspireError` (Base plugin error)
      - `SemanticError`

## Key Decisions

1. **Centralized `HarvesterError` root class**
   — By defining a single root Exception, the project enforces a type-safe boundary between domain exceptions and raw system faults (`KeyError`, `MemoryError`).

2. **Yielding Errors over Raising them**
   — Since plugins operate as `AsyncGenerator`s, `raise`ing an exception terminates the execution loop instantly, thereby violating the "Failure isolation" principle. We chose to have plugins `yield` instances of `HarvesterError` to the orchestrator over logging them locally. This centralizes logging inside the core orchestrator and cleanly delegates the decision of "how to report failures" entirely away from individual plugins.
