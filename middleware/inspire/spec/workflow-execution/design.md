# Workflow Execution — Design

## Key Decisions

1. **Sequential fetch-map-upload loop with no internal parallelism**
   — The workflow is a simple loop: fetch a record, map it, yield it. Complex
   parallelization, async queues, or chunking would add significant complexity
   before any performance bottleneck has been observed. Simplicity is preferred
   until a concrete need is demonstrated.
