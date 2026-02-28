"""Training pipeline for the dummy linear regression model."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from src.model import fit_linear_regression, predict_linear

DATA_PATH = Path("data") / "sample_data.csv"
MODEL_PATH = Path("model") / "linear_model.npz"


def load_training_data(data_path: Path = DATA_PATH) -> tuple[np.ndarray, np.ndarray]:
    """Load (x, y) arrays from a CSV file with columns: x,y."""
    if not data_path.exists():
        raise FileNotFoundError(f"Training data not found at '{data_path}'.")

    data = np.loadtxt(data_path, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] != 2:
        raise ValueError("Training data must contain exactly two columns: x,y.")

    x = data[:, 0].astype(float)
    y = data[:, 1].astype(float)
    return x, y


def train_and_save_model(
    data_path: Path = DATA_PATH, model_path: Path = MODEL_PATH
) -> dict[str, float]:
    """Train the model from data and save learned parameters to disk."""
    x, y = load_training_data(data_path=data_path)
    weight, bias = fit_linear_regression(x=x, y=y)

    predictions = predict_linear(x=x, weight=weight, bias=bias)
    mse = float(np.mean((predictions - y) ** 2))

    model_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(model_path, weight=weight, bias=bias)

    metrics = {
        "samples": float(len(x)),
        "weight": weight,
        "bias": bias,
        "mse": mse,
    }
    return metrics


def main() -> None:
    """Run training and log model metrics."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    metrics = train_and_save_model()
    logging.info("Training complete.")
    logging.info("Samples: %.0f", metrics["samples"])
    logging.info("Weight: %.6f", metrics["weight"])
    logging.info("Bias: %.6f", metrics["bias"])
    logging.info("MSE: %.6f", metrics["mse"])
    logging.info("Saved model to '%s'", MODEL_PATH)


if __name__ == "__main__":
    main()
