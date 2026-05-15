import seaborn as sns
import matplotlib.pyplot as plt

def apply_company_template():
    sns.set_theme(
        context="notebook",
        style="whitegrid",
        font="sans-serif",
        rc={
            "figure.figsize": (10, 6),
            "figure.dpi": 120,

            "axes.titlesize": 16,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "axes.labelweight": "bold",

            "grid.color": "#0C228F",
            "grid.linestyle": "--",
            "grid.linewidth": 0.8,

            "axes.edgecolor": "#333333",
            "axes.linewidth": 1.2,

            "lines.linewidth": 2.5,
            "lines.markersize": 8,

            "legend.frameon": False,
            "legend.fontsize": 11,

            "savefig.bbox": "tight",
            "savefig.dpi": 120,
        }
    )

    # Corporate color palette
    sns.set_palette([
        "#003366",  # Primary blue
        "#0072B2",  # Secondary blue
        "#009E73",  # Green
        "#D55E00",  # Orange
        "#CC79A7"   # Accent
    ])
