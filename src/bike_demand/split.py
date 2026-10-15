"""Chronological partitions; test targets are never evaluated in Week 1."""

import pandas as pd

WINDOWS = {
    "train": ("2011-01-01", "2011-12-31"),
    "validation": ("2012-01-01", "2012-06-30"),
    "test": ("2012-07-01", "2012-12-31"),
}



def split_data(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    partitions = {}

    # Create each chronological partition
    for name, (start, end) in WINDOWS.items():
        mask = frame["dteday"].between(
            pd.Timestamp(start),
            pd.Timestamp(end)
        )

        partition = frame.loc[mask].copy()

        # Sort chronologically with deterministic tie-breaking
        partition = partition.sort_values(
            by=["dteday", "hr", "instant"]
        ).reset_index(drop=True)

        # Every partition must contain data
        if partition.empty:
            raise ValueError(f"{name}: partition must be nonempty")

        partitions[name] = partition

    # Check that partitions are disjoint
    train_ids = set(partitions["train"]["instant"])
    validation_ids = set(partitions["validation"]["instant"])
    test_ids = set(partitions["test"]["instant"])

    if (
        train_ids & validation_ids
        or train_ids & test_ids
        or validation_ids & test_ids
    ):
        raise ValueError("Partitions must be disjoint")

    # Check that every input row belongs to a partition
    total_rows = sum(len(part) for part in partitions.values())

    if total_rows != len(frame):
        raise ValueError(
            "Partitions must be complete: some rows are missing"
        )

    return partitions



def partition_summary(partitions: dict[str, pd.DataFrame]) -> dict:
    return {
        name: {
            "rows": len(part),
            "date_min": str(part["dteday"].min().date()),
            "date_max": str(part["dteday"].max().date()),
        }
        for name, part in partitions.items()
    }
