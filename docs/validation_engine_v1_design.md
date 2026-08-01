# Operation Commander — Validation Engine V1

## Purpose
Automatically validate every Commander decision against future market behaviour.

## Input
- CommanderContext
- Decision
- Lifecycle
- Evidence
- Snapshot
- Recorder timestamp

## Responsibilities
1. Capture decision snapshot
2. Capture +5m outcome
3. Capture +15m outcome
4. Capture +30m outcome
5. Compare prediction vs outcome
6. Persist validation record
7. Export curated CSV (optional)

## Non-Responsibilities
- No trade generation
- No evidence scoring
- No lifecycle modification
- No strategy changes

## Integration Point
commander_pipeline.py

After:
    context.decision = generate_decision(...)
    context.lifecycle = lifecycle_engine.evaluate(...)

Before:
    return context

## Persistence
New SQLite table:
validation_results

## Version
Validation Engine V1

Status:
DESIGN FROZEN
