"""AIFlow Evaluation Framework - test suites, scorers, and dataset management.

Provides EvalSuite for running evaluation cases against workflows/steps,
built-in scoring functions, and dataset management utilities.
"""
from aiflow.evaluation.datasets import Dataset, DatasetManager
from aiflow.evaluation.framework import EvalCase, EvalResult, EvalSuite
from aiflow.evaluation.scorers import (
    contains,
    exact_match,
    json_field_equals,
    json_valid,
    regex_match,
    threshold_check,
)

__all__ = [
    "EvalCase",
    "EvalResult",
    "EvalSuite",
    "exact_match",
    "contains",
    "json_valid",
    "json_field_equals",
    "threshold_check",
    "regex_match",
    "Dataset",
    "DatasetManager",
]
