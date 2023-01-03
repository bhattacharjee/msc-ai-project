import argparse
from typing import Dict

import pandas as pd
from sklearn import metrics

stats = {
    "Accuracy": (
        lambda df: metrics.accuracy_score(df["y_true"], df["y_pred"])
    ),
    "Balanced-Accuracy": (
        lambda df: metrics.balanced_accuracy_score(df["y_true"], df["y_pred"])
    ),
    "Precision": (
        lambda df: metrics.precision_score(df["y_true"], df["y_pred"])
    ),
    "Recall": (
        lambda df: metrics.recall_score(df["y_true"], df["y_pred"])
    ),
    "F1-Score": (lambda df: metrics.f1_score(df["y_true"], df["y_pred"])),
    "AUROC": (
        lambda df: metrics.roc_auc_score(df["y_true"], df["y_pred_proba"])
    ),
}


def get_order_number(name: str) -> int:
    order_of_columns = [
        "baseline-only",
        "advanced-only",
        "fourier-only",
        "baseline-and-advanced",
        "baseline-and-fourier",
        "advanced-and-fourier",
        "baseline-advanced-and-fourier",
    ]

    for i, n in enumerate(order_of_columns):
        if name == n:
            return i
    return -1


def get_combined_stats(df: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            fnname: df.groupby(["feature_set"])[
                ["y_true", "y_pred", "y_pred_proba"]
            ].apply(fn)
            for fnname, fn in stats.items()
        }
    ).reset_index()
    df["order"] = df["feature_set"].map(get_order_number)
    df = df.sort_values(by="order", ignore_index=True)
    df.drop("order", axis=1, inplace=True)
    return df


def get_grouped_stats(df: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            fnname: df.groupby(["feature_set", "run_name"])[
                ["y_true", "y_pred", "y_pred_proba"]
            ].apply(fn)
            for fnname, fn in stats.items()
        }
    ).reset_index()
    columns = [k for k, _ in stats.items()]
    df = df.groupby("feature_set")[columns].agg(["mean", "std"]).reset_index()
    df["order"] = df["feature_set"].map(get_order_number)
    df = df.sort_values(by="order", ignore_index=True)
    df = df.set_index("feature_set")
    df.drop("order", axis=1, inplace=True)
    return df.reset_index()


def get_metrics_comparisons(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    combined_stats = get_combined_stats(df)
    grouped_stats = get_grouped_stats(df)
    return {"combined_stats": combined_stats, "grouped_stats": grouped_stats}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.file)
    comparisons = get_metrics_comparisons(df)
    print("COMBINED")
    print("-" * len("COMBINED"))
    print(comparisons["combined_stats"].round(3).reset_index(drop=True))
    print("\n\n\nGROUPED")
    print("-" * len("GROUPED"))
    print(comparisons["grouped_stats"].round(3).reset_index(drop=True))


if "__main__" == __name__:
    main()