import argparse
from functools import partial
from typing import Dict

import pandas as pd
from sklearn import metrics


def get_confusion_matrix_unraveled(
    y_true: pd.Series, y_pred: pd.Series, which_rate: str
):
    columns = ["tnr", "fpr", "fnr", "tpr"]
    output = list(metrics.confusion_matrix(y_true, y_pred).ravel())
    assert len(output) == 4
    assert sum(output) == len(y_true)
    tn, fp, fn, tp = tuple(output)
    tpr = tp / (tp + fn)
    tnr = tn / (tn + fp)
    fpr = fp / (tn + fp)
    fnr = fn / (tp + fn)
    output = [tnr, fpr, fnr, tpr]
    return output[columns.index(which_rate)]


fpr = partial(get_confusion_matrix_unraveled, which_rate="fpr")
fnr = partial(get_confusion_matrix_unraveled, which_rate="fnr")
tpr = partial(get_confusion_matrix_unraveled, which_rate="tpr")
tnr = partial(get_confusion_matrix_unraveled, which_rate="tnr")

stats = {
    "Accuracy": (
        lambda df: metrics.accuracy_score(df["y_true"], df["y_pred"])
    ),
    "Balanced-Accuracy": (
        lambda df: metrics.balanced_accuracy_score(df["y_true"], df["y_pred"])
    ),
    "TPR": (lambda df: tpr(df["y_true"], df["y_pred"])),
    "TNR": (lambda df: tnr(df["y_true"], df["y_pred"])),
    "FPR": (lambda df: fpr(df["y_true"], df["y_pred"])),
    "FNR": (lambda df: fnr(df["y_true"], df["y_pred"])),
    "Precision": (
        lambda df: metrics.precision_score(df["y_true"], df["y_pred"])
    ),
    "Recall": (lambda df: metrics.recall_score(df["y_true"], df["y_pred"])),
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


def print_latex(
    df: pd.DataFrame, highlight_min_max: bool = False, num_decimals: int = 3
) -> None:
    def format_min_max(
        x,
        min_value: float,
        max_value: float,
        num_decimals: int = 3,
        invert: bool = False,
    ) -> str:
        if isinstance(x, str):
            return x
        # if round(x, num_decimals) == round(min_value, num_decimals):
        if x == min_value:
            if not invert:
                return f"\\textOrange{{{x:.{num_decimals}f}}}"
            else:
                return f"\\textBlue{{{x:.{num_decimals}f}}}"
        # elif round(x, num_decimals) == round(max_value, num_decimals):
        elif x == max_value:
            if not invert:
                return f"\\textBlue{{{x:.{num_decimals}f}}}"
            else:
                return f"\\textOrange{{{x:.{num_decimals}f}}}"
        else:
            return f"{x:.{num_decimals}f}"

    def should_invert(colnames: str):
        invert = False
        if isinstance(colnames, tuple):
            if "std" in colnames:
                invert = True
            if colnames[0] in ["FPR", "FNR"]:
                invert = not invert
        return invert

    formatters = {
        colname: partial(
            format_min_max,
            min_value=df[colname].min(),
            max_value=df[colname].max(),
            num_decimals=num_decimals,
            invert=should_invert(colname),
        )
        for colname in df.columns
        if colname != ("feature_set", "")
    }

    # Columns are in two levels, each column is a tuple of two values
    # Get rid of some columns that we don't want to print
    df = df[
        [
            c
            for c in df.columns
            if (
                not isinstance(c, tuple)
                or c[0] not in ["Balanced-Accuracy", "Accuracy"]
            )
        ]
    ]
    df = df[
        [
            c
            for c in df.columns
            if c not in [("Precision", "std"), ("Recall", "std")]
        ]
    ]
    df = df[
        [
            c
            for c in df.columns
            if not (c[0] in ["FPR", "TPR", "FNR", "TNR"] and c[1] == "std")
        ]
    ]

    for c in df.columns:
        print(c, type(c))

    print()
    if highlight_min_max:
        df_str = df.to_latex(
            formatters=formatters, escape=False, index_names=False
        )
    else:
        df_str = df.to_latex(index_names=False)
    print(df_str)
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, required=True)
    parser.add_argument(
        "-tl", "--to-latex", action="store_true", default=False
    )
    parser.add_argument(
        "-hm", "--highlight-min-max", action="store_true", default=False
    )
    parser.add_argument("-nd", "--num-decimals", type=int, default=3)
    args = parser.parse_args()

    df = pd.read_csv(args.file)
    comparisons = get_metrics_comparisons(df)
    print("COMBINED")
    print("-" * len("COMBINED"))
    print(comparisons["combined_stats"].round(3).reset_index(drop=True))
    if args.to_latex:
        print_latex(
            comparisons["combined_stats"].reset_index(drop=True),
            args.highlight_min_max,
            args.num_decimals,
        )
    print("\n\n\nGROUPED")
    print("-" * len("GROUPED"))
    print(comparisons["grouped_stats"].round(3).reset_index(drop=True))
    if args.to_latex:
        print_latex(
            comparisons["grouped_stats"].reset_index(drop=True),
            args.highlight_min_max,
            args.num_decimals,
        )


if "__main__" == __name__:
    main()
