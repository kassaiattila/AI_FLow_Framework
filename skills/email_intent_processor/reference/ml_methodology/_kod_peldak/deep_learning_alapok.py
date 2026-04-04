"""
Deep Learning Alapok - Kod Peldak
==================================
13. fejezet: Deep Learning Alapok

Tartalom:
    1. Perceptron modell (sklearn.linear_model.Perceptron)
    2. Multi-Layer Perceptron - MLPClassifier
    3. Rejtett retegek es neuronok szamanak hatasa
    4. Multi-Label Classification
    5. Aktivalasi fuggvenyek vizualizacioja
    6. Overfitting demonstracio es regularizacio

Forras: Cubix ML Engineer - Deep Learning alapok tananyag (8. het)

Futtatas:
    python deep_learning_alapok.py

Fuggosegek: numpy, scikit-learn, matplotlib (pandas opcionalis)
"""

import warnings

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification, make_multilabel_classification
from sklearn.linear_model import Perceptron
from sklearn.metrics import accuracy_score, hamming_loss
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

try:
    import pandas as pd  # noqa: F401
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

warnings.filterwarnings("ignore")


# =============================================================================
# Segédfuggvenyek
# =============================================================================

def make_scaled_data(n_samples=1000, n_features=20, n_classes=2,
                     random_state=42):
    """Adathalmaz generalasa, szetvalasztasa es skalazasa."""
    kw = dict(n_samples=n_samples, n_features=n_features,
              random_state=random_state)
    if n_classes > 2:
        kw.update(n_classes=n_classes, n_informative=12,
                  n_redundant=3, n_clusters_per_class=1)
    else:
        kw.update(n_informative=15, n_redundant=3)
    X, y = make_classification(**kw)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                               random_state=random_state)
    sc = StandardScaler()
    return sc.fit_transform(X_tr), sc.transform(X_te), y_tr, y_te


def sep(title):
    """Szekciocim kiirasa."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# =============================================================================
# 1. Perceptron -- linearis osztalyozas
# =============================================================================

def demo_perceptron():
    """Perceptron vs MLP osszehasonlitas 2D dontesi hatarral."""
    sep("1. Perceptron - Linearis osztalyozas")

    X_tr, X_te, y_tr, y_te = make_scaled_data(n_samples=800, n_features=2)

    # Perceptron tanitasa
    perc = Perceptron(max_iter=100, tol=1e-3, random_state=42)
    perc.fit(X_tr, y_tr)
    perc_acc = accuracy_score(y_te, perc.predict(X_te))
    print(f"\n  Perceptron pontossag: {perc_acc:.4f}")
    print(f"  Sulyok: {perc.coef_[0]},  Bias: {perc.intercept_[0]:.4f}")

    # MLP osszehasonlitasul
    mlp = MLPClassifier(hidden_layer_sizes=(50,), max_iter=500, random_state=42)
    mlp.fit(X_tr, y_tr)
    mlp_acc = accuracy_score(y_te, mlp.predict(X_te))
    print(f"  MLP pontossag:        {mlp_acc:.4f}")

    # Dontesi hatar vizualizacio
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, model, name in [(axes[0], perc, "Perceptron"),
                             (axes[1], mlp, "MLP (50 neuron)")]:
        h = 0.05
        xx, yy = np.meshgrid(
            np.arange(X_te[:, 0].min() - 1, X_te[:, 0].max() + 1, h),
            np.arange(X_te[:, 1].min() - 1, X_te[:, 1].max() + 1, h))
        Z = model.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
        ax.contourf(xx, yy, Z, alpha=0.3, cmap="RdBu")
        ax.scatter(X_te[:, 0], X_te[:, 1], c=y_te, cmap="RdBu",
                   edgecolors="k", s=30)
        acc = accuracy_score(y_te, model.predict(X_te))
        ax.set_title(f"{name}\nPontossag: {acc:.4f}", fontweight="bold")
        ax.set_xlabel("Feature 1"); ax.set_ylabel("Feature 2")
    plt.suptitle("Perceptron vs MLP - Dontesi hatar", fontsize=14,
                 fontweight="bold")
    plt.tight_layout(); plt.show()


# =============================================================================
# 2. MLP architekturak osszehasonlitasa
# =============================================================================

def demo_mlp_architectures():
    """Kulonbozo rejtett reteg konfiguraciok hatasa a pontossagra."""
    sep("2. MLP architekturak osszehasonlitasa")

    X_tr, X_te, y_tr, y_te = make_scaled_data(
        n_samples=2000, n_features=20, n_classes=5)

    archs = {
        "(25,)": (25,),
        "(100,)": (100,),
        "(100,50)": (100, 50),
        "(200,100,50)": (200, 100, 50),
        "(100,50,25)": (100, 50, 25),
        "(50,50,50,50)": (50, 50, 50, 50),
    }

    print(f"\n  {'Architektura':<20s} | Pontossag | Epochok")
    print("  " + "-" * 50)
    results = []
    for name, layers in archs.items():
        mlp = MLPClassifier(hidden_layer_sizes=layers, activation="relu",
                            solver="adam", max_iter=500, random_state=42)
        mlp.fit(X_tr, y_tr)
        acc = accuracy_score(y_te, mlp.predict(X_te))
        results.append((name, acc, mlp.n_iter_, mlp.loss_curve_))
        print(f"  {name:<20s} | {acc:.4f}    | {mlp.n_iter_}")

    # Vizualizacio
    fig, axes = plt.subplots(1, 2, figsize=(16, 5))

    # Pontossag oszlopdiagram
    names = [r[0] for r in results]
    accs = [r[1] for r in results]
    bars = axes[0].barh(names, accs, color=plt.cm.viridis(
        np.linspace(0.2, 0.8, len(results))), edgecolor="k")
    axes[0].set_xlabel("Pontossag"); axes[0].set_xlim(0.5, 1.0)
    axes[0].set_title("MLP architekturak", fontweight="bold")
    for bar, a in zip(bars, accs, strict=False):
        axes[0].text(bar.get_width() + 0.005,
                     bar.get_y() + bar.get_height() / 2,
                     f"{a:.4f}", va="center", fontsize=9)

    # Tanulasi gorbe a legjobb modellre
    best = results[int(np.argmax(accs))]
    axes[1].plot(best[3], "b-", linewidth=2)
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("Loss")
    axes[1].set_title(f"Tanulasi gorbe - {best[0]}", fontweight="bold")
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout(); plt.show()


# =============================================================================
# 3. Multi-Label Classification
# =============================================================================

def demo_multilabel():
    """Multi-label osztalyozas MLPClassifier-rel."""
    sep("3. Multi-Label Classification")

    label_names = ["Akcio", "Drama", "Thriller", "Vigjatek", "Sci-Fi"]
    X, y = make_multilabel_classification(
        n_samples=1500, n_features=20, n_classes=5,
        n_labels=2, random_state=42)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                               random_state=42)
    sc = StandardScaler()
    X_tr_s, X_te_s = sc.fit_transform(X_tr), sc.transform(X_te)

    print(f"\n  Adathalmaz: {X.shape[0]} minta, {len(label_names)} cimke")
    print(f"  y alakja: {y.shape} (binaris matrix)")
    print(f"  Atlagos cimkek/minta: {y.sum(axis=1).mean():.2f}")

    mlp = MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=500,
                        random_state=42)
    mlp.fit(X_tr_s, y_tr)
    y_pred = mlp.predict(X_te_s)

    print(f"\n  Hamming Loss:    {hamming_loss(y_te, y_pred):.4f}")
    print(f"  Subset Accuracy: {accuracy_score(y_te, y_pred):.4f}")
    print("\n  Cimkenkenti pontossag:")
    per_label = []
    for i, name in enumerate(label_names):
        a = accuracy_score(y_te[:, i], y_pred[:, i])
        per_label.append(a)
        print(f"    {name:12s}: {a:.4f}")

    # Vizualizacio
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].bar(label_names, y.sum(axis=0), color="steelblue", edgecolor="k")
    axes[0].set_ylabel("Elofordulasok"); axes[0].set_title("Cimke gyakorisag",
                                                            fontweight="bold")
    colors = ["green" if a > 0.85 else "orange" if a > 0.75 else "red"
              for a in per_label]
    axes[1].bar(label_names, per_label, color=colors, edgecolor="k")
    axes[1].set_ylabel("Pontossag"); axes[1].set_ylim(0.5, 1.0)
    axes[1].set_title("Cimkenkenti pontossag", fontweight="bold")
    axes[1].axhline(y=0.85, color="gray", linestyle="--", alpha=0.5)
    plt.suptitle("Multi-Label Classification", fontsize=14, fontweight="bold")
    plt.tight_layout(); plt.show()


# =============================================================================
# 4. Aktivalasi fuggvenyek vizualizacioja
# =============================================================================

def demo_activation_functions():
    """Sigmoid, ReLU, Tanh, Leaky ReLU vizualizacio + Softmax demo."""
    sep("4. Aktivalasi fuggvenyek vizualizacioja")

    x = np.linspace(-6, 6, 300)
    funcs = [
        ("Sigmoid",    "f(x)=1/(1+e^(-x))", 1/(1+np.exp(-x)),
         lambda s: s*(1-s), "blue"),
        ("ReLU",       "f(x)=max(0,x)",      np.maximum(0, x),
         (x > 0).astype(float), "red"),
        ("Tanh",       "f(x)=tanh(x)",       np.tanh(x),
         1 - np.tanh(x)**2, "green"),
        ("Leaky ReLU", "f(x)=max(0.01x,x)",  np.where(x > 0, x, 0.01*x),
         np.where(x > 0, 1.0, 0.01), "purple"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, (name, formula, val, deriv, color) in zip(axes.flat, funcs, strict=False):
        d = deriv(val) if callable(deriv) else deriv
        ax.plot(x, val, color=color, linewidth=2.5, label=name)
        ax.plot(x, d, color=color, linewidth=1.5, linestyle="--", alpha=0.6,
                label=f"{name}' (derivalt)")
        ax.axhline(y=0, color="gray", linewidth=0.5)
        ax.axvline(x=0, color="gray", linewidth=0.5)
        ax.set_title(f"{name}\n{formula}", fontweight="bold")
        ax.legend(loc="upper left", fontsize=9); ax.grid(True, alpha=0.3)
    plt.suptitle("Aktivalasi fuggvenyek es derivaltjaik", fontsize=14,
                 fontweight="bold")
    plt.tight_layout(); plt.show()

    # Softmax demonstracio
    print("\n--- Softmax demonstracio ---")
    logits = np.array([2.0, 1.0, 0.1, -1.0, 3.5])
    sm = np.exp(logits) / np.sum(np.exp(logits))
    print(f"  Logits:  {logits}")
    print(f"  Softmax: [{', '.join(f'{v:.4f}' for v in sm)}]")
    print(f"  Osszeg:  {sm.sum():.4f}  (mindig 1.0)")

    fig, ax = plt.subplots(figsize=(8, 4))
    classes = [f"Osztaly {i}" for i in range(len(logits))]
    bars = ax.bar(classes, sm, color="steelblue", edgecolor="k")
    for bar, val in zip(bars, sm, strict=False):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{val:.3f}", ha="center")
    ax.set_ylabel("Valoszinuseg")
    ax.set_title("Softmax kimenet", fontweight="bold")
    plt.tight_layout(); plt.show()

    # Aktivalasi fuggveny hatasa az MLP pontossagra
    print("\n--- Aktivalasi fuggveny hatasa az MLP-re ---")
    X_tr, X_te, y_tr, y_te = make_scaled_data(n_samples=1500, n_features=20,
                                                n_classes=4)
    for act in ["relu", "tanh", "logistic"]:
        mlp = MLPClassifier(hidden_layer_sizes=(100, 50), activation=act,
                            max_iter=500, random_state=42)
        mlp.fit(X_tr, y_tr)
        acc = accuracy_score(y_te, mlp.predict(X_te))
        print(f"  {act:10s} -> pontossag: {acc:.4f}  (epochok: {mlp.n_iter_})")


# =============================================================================
# 5. Overfitting demonstracio es regularizacio
# =============================================================================

def demo_overfitting():
    """Tul nagy vs regularizalt modell kis adathalmazon."""
    sep("5. Overfitting demonstracio es regularizacio")

    X, y = make_classification(n_samples=300, n_features=20, n_informative=8,
                               n_redundant=5, random_state=42)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3,
                                               random_state=42)
    sc = StandardScaler()
    X_tr_s, X_te_s = sc.fit_transform(X_tr), sc.transform(X_te)
    print(f"\n  Kis adat: {X.shape[0]} minta, {X.shape[1]} feature")

    configs = {
        "Tul nagy (overfit)": dict(hidden_layer_sizes=(512, 256, 128, 64),
                                   alpha=0.0001, early_stopping=False),
        "Tul kicsi (underfit)": dict(hidden_layer_sizes=(5,), alpha=0.0001,
                                     early_stopping=False),
        "Regularizalt (alpha=0.1)": dict(hidden_layer_sizes=(100, 50),
                                         alpha=0.1, early_stopping=False),
        "Early stopping": dict(hidden_layer_sizes=(100, 50), alpha=0.0001,
                               early_stopping=True, validation_fraction=0.15,
                               n_iter_no_change=10),
    }

    print(f"\n  {'Konfig':<28s} | Train  | Test   | Gap    | Ep.")
    print("  " + "-" * 65)
    results = {}
    for name, params in configs.items():
        mlp = MLPClassifier(activation="relu", solver="adam", max_iter=1000,
                            random_state=42, **params)
        mlp.fit(X_tr_s, y_tr)
        tr_a = accuracy_score(y_tr, mlp.predict(X_tr_s))
        te_a = accuracy_score(y_te, mlp.predict(X_te_s))
        gap = tr_a - te_a
        tag = " OVERFIT!" if gap > 0.1 else ""
        results[name] = dict(train=tr_a, test=te_a, loss=mlp.loss_curve_)
        print(f"  {name:<28s} | {tr_a:.4f} | {te_a:.4f} | "
              f"{gap:+.4f} | {mlp.n_iter_}{tag}")

    # Vizualizacio
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    names = list(results.keys())
    x_pos = np.arange(len(names))
    w = 0.35
    axes[0].bar(x_pos - w/2, [results[n]["train"] for n in names], w,
                label="Train", color="steelblue", edgecolor="k")
    axes[0].bar(x_pos + w/2, [results[n]["test"] for n in names], w,
                label="Test", color="coral", edgecolor="k")
    axes[0].set_xticks(x_pos)
    axes[0].set_xticklabels(names, rotation=20, ha="right", fontsize=8)
    axes[0].set_ylabel("Pontossag"); axes[0].set_ylim(0.5, 1.05)
    axes[0].legend()
    axes[0].set_title("Train vs Test (nagy kulonbseg = overfitting)",
                      fontweight="bold")

    clrs = iter(["red", "blue", "green", "orange"])
    for n in names:
        axes[1].plot(results[n]["loss"], label=n, linewidth=1.5,
                     color=next(clrs))
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("Loss")
    axes[1].set_title("Tanulasi gorbek", fontweight="bold")
    axes[1].legend(fontsize=8); axes[1].grid(True, alpha=0.3)
    plt.suptitle("Overfitting demonstracio", fontsize=14, fontweight="bold")
    plt.tight_layout(); plt.show()

    print("\n  Tanacsok:")
    print("  - train >> test -> OVERFITTING: regularizalj vagy csokkentsd")
    print("  - train is alacsony -> UNDERFITTING: noveld a kapacitast")
    print("  - Early stopping: legegyszerubb vedelem")


# =============================================================================
# Fo futtato
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  DEEP LEARNING ALAPOK - KOD PELDAK")
    print("  13. fejezet | sklearn implementacio")
    print("=" * 70)

    demo_perceptron()
    demo_mlp_architectures()
    demo_multilabel()
    demo_activation_functions()
    demo_overfitting()

    print("\n" + "=" * 70)
    print("  Kesz! Minden demo sikeresen lefutott.")
    print("=" * 70)
