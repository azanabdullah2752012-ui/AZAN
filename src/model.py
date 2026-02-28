"""Minimal linear regression model utilities."""

from __future__ import annotations

import numpy as np


def fit_linear_regression(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Fit a 1D linear regression model and return (weight, bias)."""
    if x.ndim != 1 or y.ndim != 1:
        raise ValueError("x and y must be 1D arrays.")
    if len(x) != len(y):
        raise ValueError("x and y must have the same length.")
    if len(x) < 2:
        raise ValueError("At least two samples are required for training.")

    weight, bias = np.polyfit(x, y, deg=1)
    return float(weight), float(bias)


def predict_linear(x: np.ndarray | float, weight: float, bias: float) -> np.ndarray:
    """Run prediction for input x using the linear model parameters."""
    x_arr = np.asarray(x, dtype=float)
    return (weight * x_arr) + bias
