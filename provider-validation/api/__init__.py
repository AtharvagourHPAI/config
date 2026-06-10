"""FastAPI layer for the Provider Contract Change Validation Engine.

A THIN adapter over ``engine.decision_engine.decide()``. No decision, tag, or rule
logic lives here; every endpoint imports from ``engine`` and serializes its results.
"""
