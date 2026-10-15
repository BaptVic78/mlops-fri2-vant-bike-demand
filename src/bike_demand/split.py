"""Chronological partitions; test targets are never evaluated in Week 1."""

import pandas as pd

WINDOWS = {
    "train": ("2011-01-01", "2011-12-31"),
    "validation": ("2012-01-01", "2012-06-30"),
    "test": ("2012-07-01", "2012-12-31"),
}


def split_data(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    partitions = {}
    train = frame.loc[frame["dteday"].between("2011-01-01", "2011-12-31")]
    partitions["train"] = train.sort_values(["dteday", "hr", "instant"])
    validation = frame.loc[frame["dteday"].between("2012-01-01", "2012-06-30")]
    partitions["validation"] = validation.sort_values(["dteday", "hr", "instant"])
    test = frame.loc[frame["dteday"].between("2012-07-01", "2012-12-31")]
    partitions["test"] = test.sort_values(["dteday", "hr", "instant"])

    # checks for nonempty and complete partitions
    if any(part.empty for part in partitions.values()):
        raise ValueError("partitions: require nonempty partitions")
    if sum(len(part) for part in partitions.values()) != len(frame):
        raise ValueError("partitions: require complete coverage")

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
