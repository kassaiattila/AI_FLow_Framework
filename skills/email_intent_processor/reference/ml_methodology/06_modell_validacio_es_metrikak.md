# Modell Validacio es Metrikak

## Gyors Attekintes

> A gepi tanulasi modellek fejlesztesenek kritikus fazisa a kiertekeles es optimalizalas. Ez a fejezet a validacios strategiakat (train/validation/test split, K-Fold, idosor cross-validacio), az osztalyozasi metrikakat (confusion matrix, accuracy, precision, recall, F1-score, ROC-AUC, PR-AUC), a regresszios metrikakat (MAE, MAPE, MSE, RMSE, R2) es a bias-variance tradeoff-ot targyalja. A cel: megerteni, hogy melyik metrikat mikor es hogyan alkalmazzuk, es hogyan javitsuk a modell teljesitmenyet.

---

## Kulcsfogalmak

| Fogalom | Definicio |
|---------|-----------|
| **Train halmaz** | Az adathalmaz, amelyen a modellt tanitjuk |
| **Validation halmaz** | Az adathalmaz, amelyen a hiperparametereket optimalizaljuk |
| **Test halmaz** | Az adathalmaz, amelyen a vegleges teljesitmenyt merjuk -- NEM hasznaljuk optimalizalasra |
| **Cross-validation** | Az adathalmaz tobbszori felosztasa a megbizhatobb eredmenyert |
| **Confusion matrix** | A tenyleges es prediktalt ertekek osszeveto tablazata |
| **Bias** | A modell eloitelete -- tul egyszeru modellnel nagy (underfitting) |
| **Variance** | A modell erzekenysege a trening adatokra -- tul komplex modellnel nagy (overfitting) |
| **Hiperparameter** | A modell beallitasa, amit nem a tanitas soran tanul meg, hanem elore kell megadni |
| **Threshold (kuszobertek)** | Az a hatarertek, ami alapjan a modell pozitiv vagy negativ osztalyba sorol |

---

## Adatfelosztas

### Train/Validation/Test Split

A gepi tanulasi fejlesztesi folyamat soran harom kulon adathalmazra van szukseg:

1. **Train halmaz**: A modell tanitasara szolgal
2. **Validation halmaz**: A hiperparameterek optimalizalasara -- ez biztositja, hogy nem a teszt halmazra optimalizalunk
3. **Test halmaz**: A vegleges teljesitmeny meresere -- csak a legvegen hasznaljuk

**Fontos szabaly**: Soha ne optimalizaljuk a modellt a teszt halmazon! Ha a teszt halmazon allitgatjuk a parametereket, az eredmenyek tulzottan optimistak lehetnek, es a valos kornyezetben rosszabb teljesitmenyt tapasztalunk.

**Aranyok meghatarozasa**:
- Keves adat eseten: nagyobb aranyban kell validation es teszt adatokat tartani
- Nagy adatmennyiseg eseten: akar 1% vagy kevesebb is elegendo lehet a validation es teszt halmazokra
- Tipikus felosztas: 60-70% train, 15-20% validation, 15-20% test

### Stratified Split

Stratified split eseten az eredeti adathalmaz osztalyeloszlasat megorizve tortenik a felosztas. Ez kulonosen fontos kiegyensulyozatlan adathalmazok eseten, hogy minden reszhalmazban hasonlo aranyban legyenek kepviselve az osztalyok.

```python
from sklearn.model_selection import train_test_split

# Stratified split -- a stratify parameter biztositja az osztalyeloszlas megorzeset
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.33, random_state=42, stratify=y
)
```

### Kod pelda (train_test_split)

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# Adatok betoltese
df = pd.read_csv("preprocessed_data.csv")
y = df["target"]
X = df.drop(columns="target")

# Elso felosztas: train+validation vs test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.33/2, random_state=42
)

# Masodik felosztas: train vs validation
X_train, X_cv, y_train, y_cv = train_test_split(
    X_train, y_train, test_size=0.33/2, random_state=20
)

print(f"Train meret:      {X_train.shape[0]}")
print(f"Validation meret: {X_cv.shape[0]}")
print(f"Test meret:       {X_test.shape[0]}")
```

---

## Cross-Validation

### K-Fold

A K-Fold cross-validation soran az adatokat K reszre osztjuk, es minden resz egyszer validacios halmazkent szolgal, mig a tobbi a tanito halmaz. Elonye, hogy minden adatpont egyszer kerul a validacios halmazba, igy megbizhatobb eredmenyt kapunk.

**Fontos szabalyok**:
- Ugyanazokkal a hiperparameterekkel kell futtatni minden fold-ban
- Minden iteracioban **nullarol** inicializaljuk a modellt -- nem tanithato tovabb elozo iteracio modellje
- Az eredmenyek atlagat vesszuk vegso validacios eredmenykent
- Tobbe kerul: K-szer annyi szamitas szukseges

```python
from sklearn.model_selection import KFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import numpy as np

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.33, random_state=42
)

# Indexek resetelese fontos!
X_train = X_train.reset_index(drop=True)
y_train = y_train.reset_index(drop=True)

kf = KFold(n_splits=5)
accuracies = []

for i, (train_index, cv_index) in enumerate(kf.split(X_train)):
    # FONTOS: Minden iteracioban uj modell!
    clf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=0)
    clf.fit(X_train.iloc[train_index], y_train.iloc[train_index])

    y_cv_pred = clf.predict(X_train.iloc[cv_index])
    cv_accuracy = accuracy_score(y_train[cv_index], y_cv_pred)

    print(f"Fold {i} CV Accuracy: {cv_accuracy:.4f}")
    accuracies.append(cv_accuracy)

print(f"\nAtlag CV Accuracy: {np.mean(accuracies):.4f}")
```

### Stratified K-Fold

A Stratified K-Fold biztositja, hogy minden fold-ban megmarad az eredeti osztalyeloszlas. Kulonosen fontos kiegyensulyozatlan adathalmazoknal.

```python
from sklearn.model_selection import StratifiedKFold

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

for train_index, cv_index in skf.split(X_train, y_train):
    clf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=0)
    clf.fit(X_train.iloc[train_index], y_train.iloc[train_index])
    # ... kiertekeles ...
```

### Leave-One-Out (LOO)

A Leave-One-Out cross-validation a K-Fold szelsoseges esete, ahol K = az adatpontok szama. Minden iteracioban egyetlen adatpont a validacios halmaz. Nagyon pontos, de szamitasigenyes -- csak kis adathalmazoknal praktikus.

```python
from sklearn.model_selection import LeaveOneOut

loo = LeaveOneOut()
for train_index, cv_index in loo.split(X):
    # Minden iteracioban 1 elem a teszthalmaz
    pass
```

### Idosor Cross-Validacio (TimeSeriesSplit)

Idosoros adatoknal **nem szabad** veletlen felosztast alkalmazni, mert a modell "a jovobe lathatna". Az idosor cross-validacionalaz adatok sorrendje kulcsfontossagu:

1. **Elso a trening, aztan a validacio, vegul a teszt** -- mindig idorendben
2. A modell sosem lathat jovobeli adatokat a tanitas soran
3. Nem mindig a legtobb adat adja a legjobb eredmenyt -- az adatok elavulhatnak

**Ket fo megkozelites**:

**a) Expanding window (sklearn TimeSeriesSplit)**:
```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
for train_index, test_index in tscv.split(X):
    X_train_fold = X.iloc[train_index]
    X_test_fold = X.iloc[test_index]
    # A trening halmaz folyamatosan no
```

**b) Blocking Time Series Split (fix ablak)**:
- Fix hosszusagu trening ablak (pl. 4 het) es teszt ablak (pl. 1 het)
- Elonye: figyelembe veszi az adatok elavulasat
- Erdemes kiprobalni, mennyi adattal erheto el a legjobb pontossag

### Kod peldak -- cross_val_score

```python
from sklearn.model_selection import cross_val_score

# Egyszeru cross-validation egyetlen sorban
scores = cross_val_score(clf, X_train, y_train, cv=5, scoring='accuracy')
print(f"CV Accuracy: {scores.mean():.4f} (+/- {scores.std():.4f})")
```

---

## Osztalyozasi Metrikak

### Confusion Matrix

A confusion matrix az alapja az osszes osztalyozasi metrikanak. Megmutatja, hogy a modell mennyire "zavarodott ossze" -- azaz hol hibazik.

**Binaris osztályozas (pl. spam / nem spam)**:

|  | Prediktalt Pozitiv | Prediktalt Negativ |
|---|---|---|
| **Tenyleges Pozitiv** | True Positive (TP) | False Negative (FN) |
| **Tenyleges Negativ** | False Positive (FP) | True Negative (TN) |

- **True Positive (TP)**: Helyesen prediktalt pozitiv (pl. spam, es tenyleg spam)
- **True Negative (TN)**: Helyesen prediktalt negativ (pl. nem spam, es tenyleg nem az)
- **False Positive (FP)**: Tevesen pozitivnak prediktalt negativ (pl. nem spam, de a modell spamnek mondta) -- **I. fajta hiba**
- **False Negative (FN)**: Tevesen negativnak prediktalt pozitiv (pl. spam, de a modell nem ismerte fel) -- **II. fajta hiba**

**Tobbosztályu osztalyozas**: Ugyanez a logika kiterjesztheto tobb osztalyra, ahol a matrix merete NxN (N = osztalyok szama).

```python
from sklearn.metrics import confusion_matrix

y_test_pred = clf.predict(X_test)

# Confusion matrix
conf_matrix = confusion_matrix(y_test, y_test_pred)
print("Confusion Matrix:\n", conf_matrix)

# Egyes ertekek kinyerese (binaris eseten)
tn, fp, fn, tp = confusion_matrix(y_test, y_test_pred).ravel()
print(f"TP={tp}, TN={tn}, FP={fp}, FN={fn}")
```

**Vizualizacio**:
```python
from sklearn.metrics import ConfusionMatrixDisplay
import matplotlib.pyplot as plt

disp = ConfusionMatrixDisplay(confusion_matrix=conf_matrix)
disp.plot(cmap='Blues')
plt.title("Confusion Matrix")
plt.show()
```

### Accuracy

**Keplet**: `Accuracy = (TP + TN) / (TP + FP + TN + FN)`

Az osszes helyes predikcios aranya. Egyszeru es jol ertelmezheto, de **kiegyensulyozatlan adathalmaznal felrevezeto** lehet (pl. 99% negativ eseten mindig negativot mondva 99% accuracy erheto el).

```python
from sklearn.metrics import accuracy_score

accuracy = accuracy_score(y_test, y_test_pred)
print(f"Accuracy: {accuracy:.4f}")
```

### Precision

**Keplet**: `Precision = TP / (TP + FP)`

Ha a modell azt mondja, hogy pozitiv, mennyire bizhatunk benne? Magas precision = kevesebb false positive.

**Pelda**: Ha a spam detektor precision-je 0.94, akkor a spam-nek jelolt emailek 94%-a tenyleg spam.

```python
from sklearn.metrics import precision_score

precision = precision_score(y_test, y_test_pred)
print(f"Precision: {precision:.4f}")
```

### Recall (Sensitivity)

**Keplet**: `Recall = TP / (TP + FN)`

Az osszes tenyleges pozitiv eset kozul hanyat talalt meg a modell? Magas recall = kevesebb kihagyott pozitiv eset.

**Pelda**: Ha 100 spam van es a recall 0.59, akkor a modell 59 spamet fog megtalalni.

**Fontos**: A precision es a recall **ellentetes celu**. Ha mindent pozitivnak jelolunk, a recall 1.0 lesz, de a precision nagyon alacsony. A celtol fugg, melyik fontosabb.

```python
from sklearn.metrics import recall_score

recall = recall_score(y_test, y_test_pred)
print(f"Recall: {recall:.4f}")
```

### F1-Score, F-beta

**F1-Score keplet**: `F1 = 2 * (Precision * Recall) / (Precision + Recall)`

A precision es recall harmonikus atlaga. **Kiegyensulyozatlan adathalmazoknal ajanlott**, mert mindkettot egyenlo sullyal veszi figyelembe. Erteke 0 es 1 kozott van (1 = tokeletes).

**F-beta Score**: Az F1-score altalanositott valtozata, ahol a beta parameter allitja a sulyozast:
- **beta = 1**: F1-score (egyenlo suly)
- **beta > 1**: Recall-nak nagyobb suly (pl. beta=2: a recall fontosabb)
- **beta < 1**: Precision-nak nagyobb suly (pl. beta=0.5: a precision fontosabb)

```python
from sklearn.metrics import f1_score, fbeta_score

# F1-score
f1 = f1_score(y_test, y_test_pred)
print(f"F1 Score: {f1:.4f}")

# F-beta score (precision fontosabb)
fbeta_05 = fbeta_score(y_test, y_test_pred, beta=0.5)
print(f"F-beta (beta=0.5): {fbeta_05:.4f}")

# F-beta score (recall fontosabb)
fbeta_2 = fbeta_score(y_test, y_test_pred, beta=2)
print(f"F-beta (beta=2): {fbeta_2:.4f}")

# F-beta score (recall meg fontosabb)
fbeta_3 = fbeta_score(y_test, y_test_pred, beta=3)
print(f"F-beta (beta=3): {fbeta_3:.4f}")
```

### Specificity

**Keplet**: `Specificity = TN / (TN + FP)`

A negativ esetek kozul hanyat azonositott helyesen a modell. A recall "parkepessege" a negativ osztalyra.

```python
# Specificity szamitasa manuálisan
tn, fp, fn, tp = confusion_matrix(y_test, y_test_pred).ravel()
specificity = tn / (tn + fp)
print(f"Specificity: {specificity:.4f}")
```

### ROC gorbe es AUC

A **ROC-gorbe** (Receiver Operating Characteristic) a True Positive Rate (TPR = Recall) es a False Positive Rate (FPR = 1 - Specificity) kapcsolatat abrazoljar kulonbozo kuszobertek-beallitasok mellett.

**Hogyan szamoljuk?**
1. Kulonbozo kusobertekeket allitunk be (0.1, 0.2, ..., 0.9)
2. Minden kusoberteknel kiszamoljuk a confusion matrix-et
3. Kiszamoljuk a TPR-t es FPR-t
4. Pontokent felrajzoljuk

**AUC (Area Under Curve)**: A gorbe alatti terulet:
- **AUC = 1.0**: Tokeletes modell
- **AUC = 0.5**: Veletlen talalgatas (a szaggatott atloval)
- **AUC < 0.5**: Rosszabb, mint a veletlen

**Hasznalat**: Nem csak binaris, hanem tobbosztályu osztalyozasnal is alkalmazhato (one-vs-rest).

```python
from sklearn.metrics import roc_curve, roc_auc_score
import matplotlib.pyplot as plt

# Valoszinuseg-predikciok (nem binaris predikciok!)
y_test_probs = clf.predict_proba(X_test)[:, 1]

# ROC gorbe szamitasa
fpr, tpr, thresholds = roc_curve(y_test, y_test_probs)
roc_auc = roc_auc_score(y_test, y_test_probs)

# Vizualizacio
plt.figure(figsize=(8, 6))
plt.plot(fpr, tpr, color='blue', lw=2,
         label=f'ROC gorbe (AUC = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], color='darkgrey', lw=2, linestyle='--',
         label='Veletlen talalgatas')
plt.xlabel('False Positive Rate (FPR)')
plt.ylabel('True Positive Rate (TPR)')
plt.title('ROC Gorbe')
plt.legend(loc="lower right")
plt.grid(True, alpha=0.3)
plt.show()

print(f"ROC AUC: {roc_auc:.4f}")
```

### Precision-Recall gorbe es PR-AUC

A **Precision-Recall gorbe** a precision-t es recall-t abrazoljar kulonbozo kusobertekek mellett. A **PR-AUC** a gorbe alatti terulet.

**Mikor hasznaljuk a ROC helyett?**
- Nagyon kiegyensulyozatlan adathalmazoknal (pl. 99% negativ)
- Amikor foleg a pozitiv esetek erdekelnek
- A ROC-AUC ilyen esetben felrevezetoen magas lehet

```python
from sklearn.metrics import precision_recall_curve, auc
import matplotlib.pyplot as plt

# Precision-Recall gorbe szamitasa
precision_vals, recall_vals, _ = precision_recall_curve(y_test, y_test_probs)
pr_auc = auc(recall_vals, precision_vals)

# Vizualizacio
plt.figure(figsize=(8, 6))
plt.plot(recall_vals, precision_vals, color='green', lw=2,
         label=f'PR gorbe (AUC = {pr_auc:.2f})')
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Gorbe')
plt.legend(loc="lower left")
plt.grid(True, alpha=0.3)
plt.show()

print(f"PR AUC: {pr_auc:.4f}")
```

**Teljes vizualizacio (ROC + PR egyutt)**:
```python
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, auc

y_test_probs = clf.predict_proba(X_test)[:, 1]

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# ROC gorbe
fpr, tpr, _ = roc_curve(y_test, y_test_probs)
roc_auc = roc_auc_score(y_test, y_test_probs)
axes[0].plot(fpr, tpr, 'b-', lw=2, label=f'ROC (AUC={roc_auc:.2f})')
axes[0].plot([0, 1], [0, 1], 'k--', lw=1)
axes[0].set_xlabel('False Positive Rate')
axes[0].set_ylabel('True Positive Rate')
axes[0].set_title('ROC Gorbe')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# PR gorbe
prec, rec, _ = precision_recall_curve(y_test, y_test_probs)
pr_auc = auc(rec, prec)
axes[1].plot(rec, prec, 'g-', lw=2, label=f'PR (AUC={pr_auc:.2f})')
axes[1].set_xlabel('Recall')
axes[1].set_ylabel('Precision')
axes[1].set_title('Precision-Recall Gorbe')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
```

---

## Melyik Metrikat Valasszam? (Osztalyozas)

### Balanced dataset eseten

- **Accuracy**: Egyszeru, jol interpretalhato, dontezhozoknak is bemutatható. A kuszobertek elore meghatarozott (altalaban 0.5).
- **ROC-AUC**: Ha a precision es a recall egyarant fontos, es kulonbozo kusobertekek mellett szeretnenk latni a teljesitmenyt.

### Imbalanced dataset eseten

- **F1-Score**: Ha a precision es recall egyenlo sullyal fontos, es kiegyensulyozatlan az adathalmaz. Elonye a PR-AUC-val szemben: konnyen kommunikalhato uzleti partnerknek.
- **F-beta Score**: Ha az egyik (precision vagy recall) fontosabb a masiknal.
- **PR-AUC**: Ha nagyon kiegyensulyozatlan az adathalmaz es kulonbozo kusobertekek mellett szeretnenk latni az eredmenyt. A ROC-AUC ilyenkor felrevezetoen optimista lehet.

### Dontesi segedlet

```
Kiegyensulyozott adat?
  |-- IGEN --> Accuracy vagy ROC-AUC
  |-- NEM  --> Melyik fontosabb?
                |-- Pozitiv predikciok megbizhatosaga --> Precision
                |-- Pozitiv esetek megtalálasa        --> Recall
                |-- Mindketto egyenlo                 --> F1-Score
                |-- Kulonbozo kusobertekek vizsgalata  --> PR-AUC
                |-- Sulyozas szukseges                --> F-beta Score
```

**Pelda szituaciok:**
- **Spam detektor**: Precision fontos (ne jeloljunk jo emailt spamnek)
- **Betegsegsures**: Recall fontos (ne hagyjunk ki beteget)
- **Altalanos osztalyozas**: F1-Score vagy ROC-AUC
- **Ritka esemenyek detektalasa** (pl. csalasdetekcio): PR-AUC

---

## Regresszios Metrikak

### MAE (Mean Absolute Error)

**Keplet**: `MAE = (1/n) * SUM(|y_i - y_pred_i|)`

Az elorejelezes es a valos ertek kozotti atlagos abszolut elteres. **Jol ertelmezheto**: megmutatja, atlagosan mennyivel ter el a predikció a valos ertektol.

**Elonyok**: Jol hasznalhato uzleti prezentaciokhoz, intuitiv
**Hatranyok**: Nem bunteti sulyosabban a nagy hibakat

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

regr = RandomForestRegressor(n_estimators=20, max_depth=5, random_state=0)
regr.fit(X_train, y_train)

y_pred_train = regr.predict(X_train)
y_pred_test = regr.predict(X_test)

mae_train = mean_absolute_error(y_train, y_pred_train)
mae_test = mean_absolute_error(y_test, y_pred_test)
print(f"MAE (train): {mae_train:.2f}")
print(f"MAE (test):  {mae_test:.2f}")
```

### MSE (Mean Squared Error)

**Keplet**: `MSE = (1/n) * SUM((y_i - y_pred_i)^2)`

A hibak negyzetenek atlaga. **Jobban bunteti a nagy hibakat**, ezert optimalizaciohoz alkalmas (pl. cost function-kent).

**Elonyok**: Jolhasznalhato optimalizaciohoz, differenciálhato
**Hatranyok**: Nem az eredeti mertekegysegben van, nehezen ertelmezheto ugyfeleknek

```python
from sklearn.metrics import mean_squared_error

mse = mean_squared_error(y_test, y_pred_test)
print(f"MSE: {mse:.2f}")
```

### RMSE (Root Mean Squared Error)

**Keplet**: `RMSE = sqrt(MSE)`

Az MSE negyzetgyoke, igy visszakapjuk az eredeti mertekegyseget. Ugyanugy bunteti a nagy hibakat, de konnyebben ertelmezheto.

```python
import numpy as np
from sklearn.metrics import mean_squared_error

rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
print(f"RMSE: {rmse:.2f}")
```

### R-squared (R2)

**Keplet**: `R2 = 1 - (RSS / TSS)`, ahol RSS = residual sum of squares, TSS = total sum of squares

Megmutatja, a modell mennyire magyarazza az adatok varianciaját:
- **R2 = 1**: Tokeletes modell
- **R2 = 0**: A modell nem jobb, mint az atlag
- **R2 < 0**: Nagyon rossz predikció

**Figyelmeztetés**: Az R2 hasznalata gepi tanulasban **vitatott**. Nem mindig tukrozi jol a modell minoseget, felrevezeto lehet. **Soha ne hasznaljuk egyedul** -- mindig mas metrikakkal egyutt alkalmazzuk.

```python
from sklearn.metrics import r2_score

r2 = r2_score(y_test, y_pred_test)
print(f"R2 Score: {r2:.4f}")
```

### Adjusted R2

Az Adjusted R2 figyelembe veszi a feature-ok szamat is, es bunteti a felesleges valtozok hozzaadasat:

**Keplet**: `Adj_R2 = 1 - ((1 - R2) * (n - 1)) / (n - p - 1)`, ahol n = mintak szama, p = feature-ok szama

```python
def adjusted_r2(r2, n, p):
    """
    r2: R-squared ertek
    n: mintak szama
    p: feature-ok szama
    """
    return 1 - ((1 - r2) * (n - 1)) / (n - p - 1)

adj_r2 = adjusted_r2(r2, len(y_test), X_test.shape[1])
print(f"Adjusted R2: {adj_r2:.4f}")
```

### MAPE (Mean Absolute Percentage Error)

**Keplet**: `MAPE = (1/n) * SUM(|y_i - y_pred_i| / |y_i|) * 100`

A hibat szazalekosan fejezi ki -- jol hasznalhato kulonbozo nagysagrendu ertekek osszehasonlitasahoz.

**Elonyok**: Szazalekos ertek, jol ertelmezheto uzleti partnerek szamara
**Hatranyok**: Ha a celoertek nulla, nullaval osztas lep fel!

```python
import numpy as np

# Manualis MAPE szamitas
mape_test = np.mean(np.abs((y_test - y_pred_test) / y_test)) * 100
print(f"MAPE (test): {mape_test:.2f}%")

# sklearn MAPE (0.24+ verziotol)
from sklearn.metrics import mean_absolute_percentage_error
mape_sklearn = mean_absolute_percentage_error(y_test, y_pred_test) * 100
print(f"MAPE sklearn (test): {mape_sklearn:.2f}%")
```

---

## Bias-Variance Tradeoff

### Underfitting vs Overfitting

A gepi tanulas egyik legfontosabb temaja, bar sok kurzus nem beszel rola elegen.

| Jellemzo | Underfitting (High Bias) | Overfitting (High Variance) |
|----------|--------------------------|------------------------------|
| Modell | Tul egyszeru | Tul komplex |
| Trening hiba | Magas | Nagyon alacsony (akar 0) |
| Validacios hiba | Magas | Magas |
| Kulonbseg | Kicsi (mindketto rossz) | Nagy (train jo, val rossz) |
| Pelda | Egyenes illesztese gorbult adatokra | Minden adatpontra tokeletes illesztes |

**Harom allapot**:
1. **Underfitting**: A modell nem tanul eleget -- nagy bias, alacsony variance
2. **Optimalis**: Jo egyensuly bias es variance kozott
3. **Overfitting**: A modell tultanulja a trening adatokat -- alacsony bias, nagy variance

### Felismeres (learning curves)

A bias-variance problemat a **trening es validacios hiba gorbekbol** ismerhetjuk fel:

- **Modell komplexitas novelesekor**:
  - Trening hiba: csokken (komplexebb modell jobban illeszkszik)
  - Validacios hiba: eloszor csokken, majd no (az optimalis pont utan tultanulas)
  - Cel: megallni ott, ahol a validacios hiba minimalis

- **Adatmennyiseg novelesekor**:
  - Trening pontossag: altalaban csokken (tobb adat nehezebb megtanulni)
  - Validacios pontossag: no (tobb adat segit az altalanositasban)

**Elvart pontossag meghataroza**: Fontos egy realis celerteket kituzni:
- Szakertoi velemeny (pl. radiologus pontossaga agytumor felismeresenel)
- Kutatasi eredmenyek hasonlo feladatokbol
- Nem varhatjuk el, hogy a modell jobban teljesitsen egy emberi szakertonal

**High bias eseten**: A pontossag mindenhol az elvart alatt marad -- az adat nem megfelelo vagy a modell tul egyszeru.

**High variance eseten**: A trening pontossag nagyon magas (akar 100%), de a validacios alacsony -- nagy a kulonbseg a ketto kozott.

```python
from sklearn.model_selection import learning_curve
import matplotlib.pyplot as plt
import numpy as np

train_sizes, train_scores, val_scores = learning_curve(
    clf, X_train, y_train, cv=5,
    train_sizes=np.linspace(0.1, 1.0, 10),
    scoring='accuracy'
)

plt.figure(figsize=(10, 6))
plt.plot(train_sizes, np.mean(train_scores, axis=1), 'o-', label='Trening pontossag')
plt.plot(train_sizes, np.mean(val_scores, axis=1), 'o-', label='Validacios pontossag')
plt.xlabel('Trening mintak szama')
plt.ylabel('Pontossag')
plt.title('Learning Curve')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

### Megoldasok

| Problema | Megoldas |
|----------|----------|
| **Underfitting** | Komplexebb modell, tobb feature, kevesebb regularizacio |
| **Overfitting** | Egyszerubb modell, tobb adat, regularizacio, dropout, early stopping |
| **Mindketto** | Jobb minosegu adat, feature engineering, mas megkozelites |

---

## Optimalizalasi Lehetosegek Attekintes

A predikcios pontossag javitasanak lehetosegei -- Andrew Ng szerint: *"Annak van a legjobb eredmenye, akinek a legtobb es legjobb adata van, nem annak, akinek a legjobb modellje."*

### 1. Adat
- **Tobb adat gyujtese**: Tobb sor, tobb oszlop -- kommunikacio az uzleti es data engineering csapattal
- **Cimkezes**: Felügyelt tanulas szinte mindig jobb; celzott cimkezes kivalasztott adatpontokra
- **Adatminoseg novelese**: Domain knowledge, programozasi modszerek, ML-alapu imputalas
- **Semi-supervised learning**: Keves cimkezett + sok cimkezetlen adat hasznositasa
- **Publikus/vasarolt adathalmazok**: Atalakitva hasznalhatok

### 2. Feature Engineering
- Domain ismeretek alkalmazasa
- Uj feature-ok letrehozasa
- Adattranszformaciok (skalazas, encoding, outlier kezeles)
- Dimenzio redukcio (PCA, stb.)
- Klaszterek mint uj feature-ok

### 3. Modell
- Kulonbozo architektúrak kiprobálasa (fa alapu, neuralis halo, SVM, stb.)
- Bias-variance elemzes alapjan donteni: egyszerubb vagy komplexebb modell
- **Hiba elemzes**: A modell hibainak vizsgalata -- gyakran trivialis megoldasokhoz vezet
- Ensemble modszerek
- **Hiperparameter tuning**: Fontos, de NEM az egyetlen lehetoseg -- gyakran hamar eléri a hatarat
- Cross-validation hasznalata
- **Transfer learning**: Elore betanitott modell finomhangolasa sajat adatokra
- Kutatasi cikkek olvasasa az adott temaban

### 4. Kommunikacio
- Beszeljunk az uzleti oldallal, data engineering-gel
- Keressuk a kapcsolatokat mas szervezetekkel (pl. korhazak agytumor-predikcionál)

---

## Osszehasonlito Tablazat

### Osztalyozasi metrikak

| Metrika | Tipus | Mikor hasznald | Erzekeny erre | Ertek tartomany |
|---------|-------|-----------------|----------------|------------------|
| **Accuracy** | Osztályozas | Balanced dataset, egyszeru ertelmezes | Imbalanced data | 0-1 |
| **Precision** | Osztályozas | FP minimalizalasa fontos (pl. spam) | Threshold valasztas | 0-1 |
| **Recall** | Osztályozas | FN minimalizalasa fontos (pl. betegség) | Threshold valasztas | 0-1 |
| **F1-Score** | Osztályozas | Imbalanced data, precision es recall egyenlo | Mindkettore | 0-1 |
| **F-beta** | Osztályozas | Sulyozott precision/recall | Beta parameter | 0-1 |
| **Specificity** | Osztályozas | Negativ esetek azonositasa | FP arany | 0-1 |
| **ROC-AUC** | Osztályozas | Enyhén imbalanced, threshold-fuggetlen | Nagyon imbalanced data-nal felrevezeto | 0-1 |
| **PR-AUC** | Osztályozas | Nagyon imbalanced, pozitiv esetek fontosak | Osztaly eloszlas | 0-1 |

### Regresszios metrikak

| Metrika | Tipus | Mikor hasznald | Erzekeny erre | Ertek tartomany |
|---------|-------|-----------------|----------------|------------------|
| **MAE** | Regresszio | Uzleti prezentacio, intuitiv hiba | Nem bunteti nagy hibakat | 0 - inf |
| **MAPE** | Regresszio | Szazalekos hiba, kulonbozo skalak | Nulla ertekek (osztas!) | 0% - inf |
| **MSE** | Regresszio | Optimalizacio, cost function | Nagy hibakat sulyosan bunteti | 0 - inf |
| **RMSE** | Regresszio | Optimalizacio, eredeti mertekegyseg | Nagy hibakat sulyosan bunteti | 0 - inf |
| **R2** | Regresszio | Variancia magyarazat (ovatos!) | Felrevezeto lehet, soha nem egyedul | -inf - 1 |
| **Adj. R2** | Regresszio | Tobb feature eseten R2 helyett | Feature szam | -inf - 1 |

---

## Gyakorlati Utmutato

### Teljes klasszifikacios pipeline pelda

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, KFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    confusion_matrix, ConfusionMatrixDisplay,
    accuracy_score, precision_score, recall_score,
    f1_score, fbeta_score,
    roc_curve, roc_auc_score,
    precision_recall_curve, auc,
    classification_report
)

# --- 1. Adat betoltes es felosztas ---
# df = pd.read_csv("adat.csv")
# X = df.drop(columns="target")
# y = df["target"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.33, random_state=42
)

# --- 2. Modell tanitas K-Fold-dal ---
X_train = X_train.reset_index(drop=True)
y_train = y_train.reset_index(drop=True)

kf = KFold(n_splits=5)
accuracies = []

for i, (train_idx, cv_idx) in enumerate(kf.split(X_train)):
    clf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=0)
    clf.fit(X_train.iloc[train_idx], y_train.iloc[train_idx])
    y_cv_pred = clf.predict(X_train.iloc[cv_idx])
    cv_acc = accuracy_score(y_train[cv_idx], y_cv_pred)
    accuracies.append(cv_acc)
    print(f"  Fold {i}: CV Accuracy = {cv_acc:.4f}")

print(f"Atlag CV Accuracy: {np.mean(accuracies):.4f}")

# --- 3. Vegleges modell tanitas es teszteles ---
clf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=0)
clf.fit(X_train, y_train)
y_pred = clf.predict(X_test)
y_probs = clf.predict_proba(X_test)[:, 1]

# --- 4. Osszes metrika szamitasa ---
print("\n=== Osztalyozasi Metrikak ===")
print(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
print(f"Precision: {precision_score(y_test, y_pred):.4f}")
print(f"Recall:    {recall_score(y_test, y_pred):.4f}")
print(f"F1-Score:  {f1_score(y_test, y_pred):.4f}")
print(f"ROC-AUC:   {roc_auc_score(y_test, y_probs):.4f}")

prec_vals, rec_vals, _ = precision_recall_curve(y_test, y_probs)
print(f"PR-AUC:    {auc(rec_vals, prec_vals):.4f}")

print("\nReszletes jelentes:")
print(classification_report(y_test, y_pred))

# --- 5. Confusion matrix ---
cm = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()
print(f"TP={tp}, TN={tn}, FP={fp}, FN={fn}")
specificity = tn / (tn + fp)
print(f"Specificity: {specificity:.4f}")

# --- 6. Vizualizacio ---
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# Confusion Matrix
ConfusionMatrixDisplay(confusion_matrix=cm).plot(ax=axes[0], cmap='Blues')
axes[0].set_title('Confusion Matrix')

# ROC gorbe
fpr, tpr, _ = roc_curve(y_test, y_probs)
axes[1].plot(fpr, tpr, 'b-', lw=2,
             label=f'ROC (AUC={roc_auc_score(y_test, y_probs):.2f})')
axes[1].plot([0, 1], [0, 1], 'k--')
axes[1].set_xlabel('FPR')
axes[1].set_ylabel('TPR')
axes[1].set_title('ROC Gorbe')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

# PR gorbe
axes[2].plot(rec_vals, prec_vals, 'g-', lw=2,
             label=f'PR (AUC={auc(rec_vals, prec_vals):.2f})')
axes[2].set_xlabel('Recall')
axes[2].set_ylabel('Precision')
axes[2].set_title('Precision-Recall Gorbe')
axes[2].legend()
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
```

### Teljes regresszios pipeline pelda

```python
import numpy as np
from sklearn.datasets import load_diabetes
from sklearn.model_selection import train_test_split, KFold
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error,
    r2_score, mean_absolute_percentage_error
)

# --- 1. Adat ---
diabetes = load_diabetes()
X = pd.DataFrame(diabetes.data, columns=diabetes.feature_names)
y = diabetes.target

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.33, random_state=42
)

# --- 2. Modell ---
regr = RandomForestRegressor(n_estimators=20, max_depth=5, random_state=0)
regr.fit(X_train, y_train)

y_pred_train = regr.predict(X_train)
y_pred_test = regr.predict(X_test)

# --- 3. Osszes regresszios metrika ---
print("=== Regresszios Metrikak ===")
print(f"MAE  (train): {mean_absolute_error(y_train, y_pred_train):.2f}")
print(f"MAE  (test):  {mean_absolute_error(y_test, y_pred_test):.2f}")

mse_test = mean_squared_error(y_test, y_pred_test)
print(f"MSE  (test):  {mse_test:.2f}")
print(f"RMSE (test):  {np.sqrt(mse_test):.2f}")

print(f"R2   (test):  {r2_score(y_test, y_pred_test):.4f}")

mape = mean_absolute_percentage_error(y_test, y_pred_test) * 100
print(f"MAPE (test):  {mape:.2f}%")
```

> Bovebb, onalloan futtatható kod peldakat lasd: [_kod_peldak/validacio_metrikak.py](_kod_peldak/validacio_metrikak.py)

---

## Gyakori Hibak es Tippek

### Hibak

1. **Teszt halmazon optimalizalas**: Soha ne hangold a modellt a teszt halmazon -- erre valo a validation halmaz. A teszt halmaz csak a vegleges kiertekelesre szolgal.

2. **Accuracy hasznalata imbalanced dataset-en**: 99% negativ osztalyu adatnal a "mindig negativot mondunk" strategia 99% accuracy-t ad, de hasznalhatatlan modell.

3. **Nem inicializalt modell K-Fold-ban**: Minden fold-ban uj modellt kell letrehozni! Ha az elozo iteracio modelljét tanítjuk tovább, adatszivárgas tortenik.

4. **Idősor véletlen felosztása**: Idősoroknál SOHA ne használjunk veletlen felosztast -- a modell a jovobe latna.

5. **R2 egyedul torteno hasznalata**: Az R2 felrevezeto lehet, mindig mas metrikaval egyutt alkalmazzuk.

6. **Rossz metrika valasztas**: Osztályozashoz ne hasznaljunk regresszios metrikat es forditva -- az eredmeny ertelmezhetetlen.

7. **MAPE nulla ertekeknel**: Ha a celoertek tartalmaz nullat, a MAPE szamitasnal nullaval osztas tortenik.

### Tippek

1. **Kommunikacio**: Andrew Ng hangsúlyozza -- gyakran az adat javitasa hozza a legnagyobb javulast. Kerdezzuk meg a domain szakertoket, az uzleti oldalt, a data engineering csapatot.

2. **Mindig train ES validation ES test halmazon is nezzuk a metrikakat** -- igy latjuk a bias-variance helyzetet.

3. **Cross-validation hasznalata**: Megbizhatobb eredmenyt ad, mint egyetlen felosztas.

4. **Hiperparameter tuning nem az egyetlen lehetoseg**: Sokan megragadnak itt, de az adat javitas, feature engineering, mas algoritmus kiprobálása gyakran tobbet hoz.

5. **Hibaelemzes**: Vizsgaljuk meg, hol hibazik a modell -- gyakran egyszeru mintazatokat talàlunk, amelyeket javithatunk.

6. **Elvart pontossag meghatározása**: Hatarozzuk meg elore, milyen teljesitmenyt varunk el (szakertoi szint, kutatasi eredmenyek alapjan).

7. **classification_report hasznalata**: Egy sorban megadja az osszes fontos metrikat:
```python
from sklearn.metrics import classification_report
print(classification_report(y_test, y_pred))
```

---

## Kapcsolodo Temak

- [07_hyperparameter_optimalizalas.md](07_hyperparameter_optimalizalas.md) -- GridSearchCV, Optuna, genetikus algoritmusok
- [05_felugyelt_tanulasi_algoritmusok.md](05_felugyelt_tanulasi_algoritmusok.md) -- Random Forest, SVM, linearis/logisztikus regresszio
- [10_mlops_es_deployment.md](10_mlops_es_deployment.md) -- Teszteles production kornyezetben, train-inference konzisztencia, CI/CD

---

## Tovabbi Forrasok

- **Kurzus notebook**: `Tanayag/05_het/5_week_Cubix_ML_Engineer_Evaluation_Optimization.ipynb`
- **sklearn dokumentacio**: [Model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html)
- **sklearn metriak**: [sklearn.metrics](https://scikit-learn.org/stable/modules/classes.html#module-sklearn.metrics)
- **Cross-validation guide**: [sklearn Cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- **Andrew Ng ML tanfolyam**: A data-centric AI megkozelites es optimalizalasi strategiak
- Hivatkozott cikkek a kurzus notebook-bol:
  - [V7 Labs - Train/Validation/Test](https://www.v7labs.com/blog/train-validation-test-set)
  - [Medium - Time Series Cross-Validation](https://medium.com/@soumyachess1496/cross-validation-in-time-series-566ae4981ce4)
  - [Analytics Vidhya - Confusion Matrix Multi-class](https://www.analyticsvidhya.com/blog/2021/06/confusion-matrix-for-multi-class-classification/)
  - [Is R-squared Useless?](https://library.virginia.edu/data/articles/is-r-squared-useless)
