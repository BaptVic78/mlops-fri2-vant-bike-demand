"""CSV loading and explicit contract checks; never repair the input."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = (
    "season",
    "yr",
    "mnth",
    "hr",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
    "temp",
    "atemp",
    "hum",
    "windspeed",
)
REQUIRED = ("instant", "dteday", *FEATURES, "casual", "registered", "cnt")
DOMAINS = {
    "season": (1, 4),
    "yr": (0, 1),
    "mnth": (1, 12),
    "hr": (0, 23),
    "holiday": (0, 1),
    "weekday": (0, 6),
    "workingday": (0, 1),
    "weathersit": (1, 4),
}
NORMALISED = ("temp", "atemp", "hum", "windspeed")
COUNTS = ("cnt", "casual", "registered")



def check_domains(frame: pd.DataFrame) -> None:
    # Check categorical domains and integer values
    for column, (minimum, maximum) in DOMAINS.items():
        values = frame[column]
        if not (
            np.isfinite(values)
            & (values >= minimum)
            & (values <= maximum)
            & (values % 1 == 0)
        ).all():
            raise ValueError(
                f"{column}: values must be integers between {minimum} and {maximum}"
            )

    # Check normalized weather features
    for column in NORMALISED:
        values = frame[column]
        if not (
            np.isfinite(values)
            & (values >= 0)
            & (values <= 1)
        ).all():
            raise ValueError(
                f"{column}: values must be finite and between 0 and 1"
            )

    # Check nonnegative integer rental counts
    for column in COUNTS:
        values = frame[column]
        if not (
            np.isfinite(values)
            & (values >= 0)
            & (values % 1 == 0)
        ).all():
            raise ValueError(
                f"{column}: values must be nonnegative integers"
            )

    # Check date boundaries
    dates = frame["dteday"]
    if not dates.between(
        pd.Timestamp("2011-01-01"),
        pd.Timestamp("2012-12-31"),
    ).all():
        raise ValueError(
            "dteday: dates must be between 2011-01-01 and 2012-12-31"
        )

    # Check consistency between year and date
    expected_year = dates.dt.year - 2011
    if not (frame["yr"] == expected_year).all():
        raise ValueError("yr: inconsistent with dteday")

    # Check consistency between month and date
    if not (frame["mnth"] == dates.dt.month).all():
        raise ValueError("mnth: inconsistent with dteday")



def load_data(path: Path | str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = sorted(set(REQUIRED) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("data: require at least one row")
    for field in REQUIRED:
        if frame[field].isna().any():
            raise ValueError(f"{field}: missing values are not allowed")
        try:
            if field == "dteday":
                frame[field] = pd.to_datetime(
                    frame[field], format="%Y-%m-%d", errors="raise"
                )
            else:
                frame[field] = pd.to_numeric(frame[field], errors="raise")
        except (ValueError, TypeError) as error:
            raise ValueError(
                f"{field}: invalid {'date' if field == 'dteday' else 'numeric'} values"
            ) from error
    ids = frame["instant"]
    if (
        not (np.isfinite(ids) & (ids > 0) & (ids % 1 == 0)).all()
        or ids.duplicated().any()
    ):
        raise ValueError("instant: require unique positive integers")
    check_domains(frame)
    return frame


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()
    try:
        frame = load_data(args.data)
    except (ValueError, OSError, NotImplementedError) as error:
        parser.exit(1, f"Validation failed: {error}\n")
    print(f"Validated {len(frame)} rows; input bytes unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
