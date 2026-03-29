# Felügyelt Tanulási Algoritmusok

## Gyors Áttekintés

> A felügyelt tanulási (supervised learning) algoritmusok olyan gépi tanulási módszerek, amelyek címkézett adatokból tanulnak: ismert bemeneti-kimeneti párok alapján építenek modellt, majd ezt használják új, ismeretlen adatok predikciójára. Ez a fejezet a nem neurális hálózat alapú algoritmusokat tekinti át -- a K-Nearest Neighbors-tol a lineáris modelleken és döntési fákon át az ensemble módszerekig (Random Forest, Gradient Boosting, XGBoost, LightGBM, CatBoost). Ezek az algoritmusok bizonyos feladatokban pontosabb és jobban interpretálható eredményt adnak, mint a neurális hálózatok.

## Kulcsfogalmak

| Fogalom | Definíció |
|---------|-----------|
| **Feature set (X)** | Az adatok bemeneti jellemzoi, amelyeket a modell bemenetként használ |
| **Címkék / Target (y)** | A célváltozó, amelyet a modell megpróbál prediktálni |
| **Train-test felosztás** | Az adatok szétválasztása tanító és teszt halmazra az általánosítás méréséhez |
| **Hyperparaméter** | A modell tanítása elott beállított paraméter (pl. learning rate, max_depth) |
| **Költségfüggvény (loss/cost function)** | A modell hibáját méro függvény, amelyet minimalizálni szeretnénk |
| **Regularizáció** | Technika a túltanulás ellen, amely bünteti a modell túlzott komplexitását |
| **Túltanulás (overfitting)** | A modell túl jól megtanulja a tanító adatokat, de rosszul általánosít |
| **Alultanulás (underfitting)** | A modell nem tanul meg eleget, mindkét halmazon gyenge |
| **Accuracy (pontosság)** | A helyesen prediktált minták aránya az összes mintához képest |
| **MAE (Mean Absolute Error)** | A predikciók és valódi értékek abszolút eltéréseinek átlaga |
| **MSE (Mean Squared Error)** | A predikciók és valódi értékek négyzetes eltéréseinek átlaga |

---

## Adat-elokeészítés és kiértékelés alapok

Mielott bármely algoritmust alkalmaznánk, szükséges az adatok elokészítése. A felügyelt tanulás alapveto lépései:

1. **Feature set (X) és célváltozó (y) létrehozása** -- fontos, hogy a target NE kerüljön bele a feature set-be
2. **Train-test felosztás** -- jellemzoen 67-80% tanító, 20-33% teszt halmaz
3. **Modell betanítása** a `fit()` metódussal
4. **Predikció** a `predict()` metódussal
5. **Kiértékelés** megfelelő metrikával (accuracy, MAE, stb.)

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Adat betöltés
df = pd.read_csv("saved_dataframe.csv")

# Feature set és target létrehozása
y = df["V24"]
X = df.drop(columns="V24")

# Train-test felosztás
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.33, random_state=42
)

# Segédfüggvény a pontosság kiírásához
def get_accuracy(model, X_train, X_test, y_train, y_test):
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    train_accuracy = accuracy_score(y_train, y_train_pred)
    test_accuracy = accuracy_score(y_test, y_test_pred)
    print("Train Accuracy:", train_accuracy)
    print("Test Accuracy:", test_accuracy)
```

> **Fontos szabály:** A `random_state` paraméter biztosítja, hogy a felosztás reprodukálható legyen, így a különbözo modellek eredményei összehasonlíthatók maradnak.

---

## K-Nearest Neighbors (KNN)

### Muködési elv

A KNN egy **nem lineáris**, példa-alapú (instance-based) algoritmus. Nem épít explicit modellt, hanem minden új pont predikciójánál megkeresi a **K darab legközelebbi szomszédot** a tanító halmazban, és azok többségi szavazata (osztályozás) vagy átlaga (regresszió) adja a predikciót.

A legközelebbi szomszédok meghatározása **euklideszi távolsággal** történik:

```
d(P, Q) = sqrt( (P1-Q1)^2 + (P2-Q2)^2 + ... + (Pn-Qn)^2 )
```

Ez a számítás minden tanító pontra elvégzendo, majd a K legkisebb távolságú pont kerül kiválasztásra.

### Hyperparaméterek

| Paraméter | Leírás | Alapértelmezés |
|-----------|--------|----------------|
| `n_neighbors` (K) | Hány szomszédot vegyen figyelembe | 5 |
| `metric` | Távolságmérték (euclidean, manhattan, minkowski) | minkowski |
| `weights` | Egyenletes (`uniform`) vagy távolság-alapú (`distance`) súlyozás | uniform |

### Elonyök és hátrányok

**Elonyök:**
- Egyszerű, könnyen értheto algoritmus
- Kevés hyperparaméter, gyors prototipizálás
- Nem lineáris döntési határokat is képes megtanulni

**Hátrányok:**
- **Nagyon lassú** nagy adathalmazoknál (sok sor vagy sok oszlop esetén), mert minden predikcióhoz az összes tanító ponttól ki kell számítani a távolságot
- Érzékeny a feature-ök skálázására
- Az "átokkent" ismert dimenziónövekedési probléma (curse of dimensionality)

### Kód példa

```python
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score

# KNN modell létrehozása (4 szomszéd)
knn = KNeighborsClassifier(n_neighbors=4)
knn.fit(X_train, y_train)

# Predikció és kiértékelés
y_train_pred = knn.predict(X_train)
y_test_pred = knn.predict(X_test)

print("Train Accuracy:", accuracy_score(y_train, y_train_pred))  # ~91%
print("Test Accuracy:", accuracy_score(y_test, y_test_pred))      # ~87%
```

---

## Lineáris Modellek

### Elméleti alapok

A lineáris modellek a bemeneti változók **lineáris kombinációját** használják a predikcióhoz. A modell egyenlete:

```
y_hat = theta_0 + theta_1 * x_1 + theta_2 * x_2 + ... + theta_n * x_n
```

Ahol:
- `y_hat` -- a prediktált érték
- `theta_0` -- eltolás (intercept/bias)
- `theta_1, theta_2, ...` -- a modell által tanult súlyok (paraméterek)
- `x_1, x_2, ...` -- a feature-ök értékei

**Vektorizált forma:** `y_hat = theta^T * x` (a súlyvektor és a feature vektor skaláris szorzata)

```python
# Skaláris szorzat példa
import numpy as np
u = np.array([2, 3, 4])
v = np.array([5, 1, 2])
dot_product = np.dot(u, v)  # 5*2 + 1*3 + 2*4 = 21
```

**Linearitás lényege:** A feature-ök csak összeadódnak (súlyozottan), nem szorzódnak egymással. Minden feature elott csak egy konstans szorzó állhat.

**Költségfüggvény -- Mean Squared Error (MSE):**

```
MSE = (1/n) * sum( (y_i - y_hat_i)^2 )
```

A négyzetre emelés azért fontos, mert a nagyobb eltéréseket erosebben bünteti. A cél ennek a függvénynek a minimalizálása.

### Gradient Descent

A modell paramétereinek (theta vektor) meghatározására két fo módszer létezik:

#### 1. Normál egyenlet (zárt forma)

```
theta = (X^T * X)^(-1) * X^T * y
```

**Hátránya:** Ha a feature-ök száma nő (pl. megduplázódik), a számítási ido akár 5-8-szorosára is nohet. Nagyon sok feature esetén használhatatlanul lassú.

#### 2. Gradient Descent (gradiens csökkentés)

Iteratív optimalizációs módszer, amely lépésrol lépésre halad a költségfüggvény minimuma felé.

**Muködése:**
1. Random kezdo paraméterbeállítás (theta-k)
2. A költségfüggvény gradiensének kiszámítása (merre "lejt a hegy")
3. Lépés a gradiens irányába (a meredekség felé lefelé)
4. Ismétlés, amíg el nem érjük a minimumot

**Learning rate (tanulási ráta):**
- **Túl kicsi:** nagyon lassan konvergál, nem éri el az optimumot ésszeru idon belül
- **Túl nagy:** a költség nőhet, nem konvergál, "átugrik" a minimumon
- **Megfelelő:** szépen, fokozatosan csökken a költség a minimum felé

**Konvexitás fontossága:**
- **Konvex függvények** (pl. MSE, MAE): egyetlen globális minimum, nincs lokális minimum csapda
- **Nem konvex függvények:** lokális minimumokba ragadhat a modell

**Skálázás fontossága:** Ha a feature-ök nincsenek skálázva, a gradient descent cikk-cakkos, instabil pályán halad. Skálázott adatoknál egyenletesen konvergál.

**Típusok:**
| Típus | Leírás |
|-------|--------|
| **Batch GD** | A teljes adathalmazon számol gradienst, majd frissíti a paramétereket |
| **Stochastic GD (SGD)** | Egyetlen mintán frissít -- gyorsabb, de zajosabb |
| **Mini-batch GD** | Kis csoportokon (batch) frissít -- kompromisszum a ketto között |

### Lineáris regresszió

A lineáris regresszió folytonos célváltozó predikciójára szolgál.

#### Kód példa

```python
from sklearn.datasets import load_diabetes
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

# Diabetes adathalmaz betöltése
diabetes = load_diabetes()
data = pd.DataFrame(data=diabetes.data, columns=diabetes.feature_names)
data['target'] = diabetes.target

# Feature set és target
X = data.drop(columns=["target"])

# Target skálázás (fontos regularizált modellekhez)
y_orig = data["target"].values.reshape(-1, 1)
scaler = MinMaxScaler()
y = scaler.fit_transform(y_orig)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.33, random_state=42
)

# Lineáris regresszió
linear_reg_model = LinearRegression()
linear_reg_model.fit(X_train, y_train)

# Kiértékelés
y_pred = linear_reg_model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
print("MAE:", mae)
print("Coefficients:", linear_reg_model.coef_)
print("Intercept:", linear_reg_model.intercept_)
```

### Ridge, Lasso, ElasticNet regularizáció

A regularizáció a költségfüggvényhez hozzáad egy **bünteto tagot**, amely a nagy súlyokat bünteti, ezzel csökkentve a túltanulás esélyét.

| Algoritmus | Regularizáció | Költségfüggvény | Feature selection |
|------------|---------------|-----------------|-------------------|
| **Ridge** | L2 | `MSE + alpha * sum(theta_i^2)` | Nem (súlyok kicsik, de nem nullák) |
| **Lasso** | L1 | `MSE + alpha * sum(abs(theta_i))` | Igen (súlyokat nullára állíthatja) |
| **ElasticNet** | L1 + L2 | `MSE + alpha * (r * sum(abs(theta_i)) + (1-r)/2 * sum(theta_i^2))` | Igen |

Az **alpha** paraméter szabályozza a regularizáció erosségét:
- **alpha = 0:** nincs regularizáció (sima lineáris regresszió)
- **alpha túl nagy:** a modell nem tanul megfeleloen
- **Megfelelő alpha:** csökkenti a túltanulást anélkül, hogy rontaná a modellt

Az **l1_ratio** (ElasticNet-nél): meghatározza az L1 és L2 regularizáció arányát (0 = tiszta Ridge, 1 = tiszta Lasso).

#### Kód példák

```python
# Ridge regresszió (L2)
from sklearn.linear_model import Ridge

ridge_model = Ridge(alpha=0.1)
ridge_model.fit(X_train, y_train)
y_pred_ridge = ridge_model.predict(X_test)
mae_ridge = mean_absolute_error(y_test, y_pred_ridge)
print("Ridge MAE:", mae_ridge)
print("Coefficients:", ridge_model.coef_)

# Lasso regresszió (L1)
from sklearn.linear_model import Lasso

lasso_model = Lasso(alpha=0.001)
lasso_model.fit(X_train, y_train)
y_pred_lasso = lasso_model.predict(X_test)
mae_lasso = mean_absolute_error(y_test, y_pred_lasso)
print("Lasso MAE:", mae_lasso)
print("Coefficients:", lasso_model.coef_)  # Egyes súlyok nullák lehetnek!

# ElasticNet (L1 + L2 kombináció)
from sklearn.linear_model import ElasticNet

elasticnet_model = ElasticNet(alpha=0.001, l1_ratio=0.5)
elasticnet_model.fit(X_train, y_train)
y_pred_en = elasticnet_model.predict(X_test)
mae_en = mean_absolute_error(y_test, y_pred_en)
print("ElasticNet MAE:", mae_en)
print("Coefficients:", elasticnet_model.coef_)
```

> **Gyakorlati tanács:** A Lasso regularizáció fontos elonye a **feature selection**: nullára állíthatja a kevésbé fontos feature-ök súlyait. A Ridge általában pontosabb, de nem végez feature selection-t. Az ElasticNet mindkét elonyt kombinálja.

---

## Logisztikus Regresszió

A logisztikus regresszió -- neve ellenére -- **osztályozási** algoritmus. A lineáris regresszió kimenetét egy **sigmoid függvényen** vezeti át, így 0 és 1 közötti valószínuségi értéket kap.

### Bináris osztályozás

**Sigmoid függvény:**

```
sigma(z) = 1 / (1 + e^(-z))
```

Ahol `z = theta_0 + theta_1*x_1 + theta_2*x_2 + ...` (a lineáris kombináció).

**A sigmoid tulajdonságai:**
- Kimenete mindig **0 és 1 között** van
- Kis bemenet -> 0-hoz közeli kimenet
- Nagy bemenet -> 1-hez közeli kimenet
- **Könnyen interpretálható:** az output közvetlenül valószínuségként értelmezheto (pl. 0.8 = 80% valószínuséggel az adott osztályba tartozik)
- **Gyorsan számítható**
- A gradiense stabil (nem lesz túl nagy vagy túl kicsi), ami elősegíti a gradient descent hatékony működését

```python
# Sigmoid függvény implementáció
import numpy as np
import matplotlib.pyplot as plt

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

x_values = np.linspace(-7, 7, 200)
y_values = sigmoid(x_values)

plt.plot(x_values, y_values, label='sigmoid(x)', linewidth=2)
plt.axhline(0.5, color='red', linestyle='--', label='Küszöbérték (0.5)')
plt.title('Sigmoid Függvény')
plt.legend()
plt.grid(True)
plt.show()
```

### Többosztályos osztályozás (OvR, Softmax)

Többosztályos esetben a **softmax függvényt** használjuk. A softmax az összes osztályra kiszámítja a valószínuséget úgy, hogy az összegük 1 legyen.

**Softmax képlet:**

```
P(osztály_i) = e^(y_i) / sum_j(e^(y_j))
```

Ahol `y_i` a modell nyers kimenete az i-edik osztályra (bármilyen valós szám lehet).

**Példa (4 osztály: macska, kutya, medve, delfin):**
- A modell nyers kimenetei exponenciálódnak
- Elosztjuk az összes exponenciált érték összegével
- Eredmény: valószínuségi eloszlás (pl. macska: 22%, kutya: 18%, medve: 40%, delfin: 20%)

**Cross Entropy Loss:**

```
Loss = -sum_i( P_i * log(Q_i) )
```

Ahol P a valódi eloszlás (one-hot), Q a prediktált eloszlás. Ha a modell rosszul prediktál (pl. a helyes osztályhoz 0-hoz közeli valószínuséget rendel), a loss nagy. Tökéletes predikció esetén a loss nulla.

### Kód példa

```python
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# Bináris osztályozás
logreg_model = LogisticRegression(random_state=42)
logreg_model.fit(X_train, y_train)

y_train_pred = logreg_model.predict(X_train)
y_test_pred = logreg_model.predict(X_test)

print("Train Accuracy:", accuracy_score(y_train, y_train_pred))
print("Test Accuracy:", accuracy_score(y_test, y_test_pred))

# Többosztályos osztályozás (automatikus OvR vagy Softmax)
logreg_multi = LogisticRegression(
    multi_class='multinomial',  # Softmax
    solver='lbfgs',
    max_iter=1000,
    random_state=42
)
logreg_multi.fit(X_train_multi, y_train_multi)
```

---

## Support Vector Machines (SVM)

### Lineáris SVM

Az SVM egy régi, de megbízható osztályozási algoritmus, amely a **legjobb szeparáló hipersíkot** (döntési határt) keresi az osztályok között.

**Alapfogalmak:**
- **Support vectorok:** azok az adatpontok, amelyek a legközelebb vannak a döntési határhoz. Ezek határozzák meg a szeparáló hipersíkot.
- **Margin:** a support vectorok és a döntési határ közötti távolság. Az SVM célja ennek **maximalizálása**.

### Kernel trükk (RBF, polinomiális)

Nem minden adat **lineárisan szeparálható** (nem lehet egyenes vonallal elválasztani az osztályokat). Ilyenkor **kernel függvényeket** használunk:

| Kernel | Leírás | Mikor használd |
|--------|--------|----------------|
| `linear` | Lineáris döntési határ | Lineárisan szeparálható adatok, sok feature |
| `rbf` | Radial Basis Function | Általános célú, nem lineáris problémák |
| `poly` | Polinomiális transzformáció | Nem lineáris, de strukturált adatok |
| `sigmoid` | Sigmoid függvény alapú | Ritkábban használt |

A **kernel trükk** lényege: az adatokat magasabb dimenziós térbe képezi át, ahol már lineárisan szeparálhatóvá válnak, anélkül hogy a transzformációt ténylegesen végre kellene hajtani.

### Hyperparaméterek (C, gamma, kernel)

| Paraméter | Hatás | Túltanulás szempontjából |
|-----------|-------|--------------------------|
| **C** (nagy) | Szigorúbb döntési határ, pontosabb tanítás | Növeli a túltanulás kockázatát |
| **C** (kicsi) | Szoftabb döntési határ, toleránsabb | Csökkenti a túltanulást, de alultanulhat |
| **gamma** (nagy) | Szukebb hatókör, komplexebb döntési határ | Növeli a túltanulást |
| **gamma** (kicsi) | Tágabb hatókör, simább döntési határ | Csökkenti a túltanulást |
| **kernel** | A transzformáció típusa | Függ az adattól |

### Kód példa

```python
from sklearn.svm import SVC

# SVM modell RBF kernellel
svm = SVC(kernel='rbf', C=2)
svm.fit(X_train, y_train)
get_accuracy(svm, X_train, X_test, y_train, y_test)

# Különböző kernel és C kombinációk tesztelése
svm_linear = SVC(kernel='linear', C=1)
svm_linear.fit(X_train, y_train)
get_accuracy(svm_linear, X_train, X_test, y_train, y_test)

svm_poly = SVC(kernel='poly', C=1, degree=3)
svm_poly.fit(X_train, y_train)
get_accuracy(svm_poly, X_train, X_test, y_train, y_test)
```

> **Fontos:** Nagy C érték 100%-os train pontosságot eredményezhet, de a teszt pontosság alacsony marad (túltanulás). A C csökkentésével a train és test pontosság közeledik egymáshoz.

---

## Döntési Fa (Decision Tree)

### Muködési elv (Gini, Entropy)

A döntési fa az adatokat **szabályok sorozatával** osztályozza. Minden csomópontban (nód) egy feltétel alapján kettéosztja az adatokat, és a levelekben adja a végso predikciót.

**GINI index:**

```
GINI = 1 - sum(p_i^2)
```

Ahol `p_i` az i-edik osztály aránya az adott csomópontban.
- **GINI = 0:** tökéletesen homogén (minden minta egy osztályba tartozik)
- **GINI kozel 0.5:** erosen kevert (bináris esetben)
- A döntési fa célja a GINI **minimalizálása**

**Entrópia:**

Az adatok rendezetlenségét méri. Matematikailag a logaritmus miatt lassabb a GINI-nél, ezért a GINI általában javasolt.

### Hyperparaméterek

| Paraméter | Leírás | Túltanulás csökkentése |
|-----------|--------|------------------------|
| `criterion` | `gini`, `entropy` vagy `log_loss` | - |
| `splitter` | `best` (legjobb) vagy `random` | random csökkenti |
| `max_depth` | A fa maximális mélysége | **Csökkentsd** |
| `min_samples_split` | Min. minta egy csomópont felosztásához | **Növeld** |
| `min_samples_leaf` | Min. minta egy levélben | **Növeld** |
| `max_features` | Max. felhasznált feature-ök száma | **Csökkentsd** |
| `max_leaf_nodes` | Max. levelek száma | **Csökkentsd** |
| `min_impurity_decrease` | Min. impurity csökkenés az osztáshoz | **Növeld** |
| `class_weight` | Osztálysúlyozás (kiegyensúlyozatlan adatoknál) | `balanced` |
| `ccp_alpha` | Komplexitás-korrekciós paraméter (pruning) | **Növeld** |

> **Foökölszabály:** A `max_`-szal kezdodo paramétereket **csökkentve**, a `min_`-nel kezdodoket **növelve** csökkentheto a túltanulás.

### Pruning (metszés)

A **ccp_alpha** paraméterrel szabályozható a fa metszése: minél nagyobb az értéke, annál több ágat vág le, egyszerusítve a fát. Ez a post-pruning (utólagos metszés) módszer.

### Elonyök és hátrányok

**Elonyök:**
- **Interpretálható és elmagyarázható** -- pontosan látható, milyen szabályok alapján dönt
- Gyors tanítás és predikció
- Nem igényel skálázást
- Vizualizálható

**Hátrányok:**
- Hajlamos a **túltanulásra** (mély fák esetén)
- Instabil (kis adatváltozás nagy faváltozást okozhat)
- Egymagában ritkán a legjobb modell

### Kód példa

```python
from sklearn.tree import DecisionTreeClassifier, export_graphviz

# Döntési fa létrehozása és tanítása
dt_clf = DecisionTreeClassifier(max_depth=3)
dt_clf.fit(X_train, y_train)
get_accuracy(dt_clf, X_train, X_test, y_train, y_test)
# Train: ~90%, Test: ~89% -- kis különbség, jó jel

# Vizualizáció
export_graphviz(
    dt_clf,
    out_file='tree.dot',
    feature_names=X_train.columns.tolist(),
    class_names=["0", "1"],
    rounded=True,
    filled=True
)
# Terminálban: dot -Tpng tree.dot -o tree.png

# Megjelenítés Jupyter Notebook-ban
from IPython.display import Image
Image(filename='tree.png')
```

---

## Ensemble Módszerek

Az ensemble (együttes) tanulás több modell kombinálásával ér el jobb predikciót, mint bármelyik egyedi modell önmagában. Az alapötlet a **"tömeg bölcsessége"**: sok gyenge prediktor együtt erosebb, mint egyetlen eros modell.

### Voting Classifier

Több különbözo algoritmust tanítunk be, és a szavazataik alapján döntünk:

- **Hard voting:** többségi szavazat dönt, minden modell egyenlo súlyú
- **Soft voting:** a modellek súlya a teljesítményük alapján változik, a jobb modellek nagyobb súlyt kapnak

### Bagging és Pasting

- **Bagging (Bootstrap Aggregating):** véletlenszeru mintavételezés **visszatevéssel** -- ugyanaz a pont többször is szerepelhet
- **Pasting:** véletlenszeru mintavételezés **visszatevés nélkül** -- minden pont egyszer szerepel

Mindkét esetben több modellt (pl. döntési fát) tanítunk be különbözo almintákon, majd szavaztatjuk oket.

---

### Bagging - Random Forest

#### Muködési elv

A Random Forest a bagging módszer kiterjesztése:
1. **Több döntési fát** tanít be (pl. 50, 500 vagy akár 5000)
2. Minden fa **véletlenszeru adatmintán** tanul (bootstrap)
3. Minden fa **véletlenszeru feature-alhalmazon** is tanul (ez a "random" a nevében)
4. A végso predikció a fák **szavazata** (osztályozás) vagy **átlaga** (regresszió)

Minden egyes döntési fa egy **gyenge prediktor** -- önmagában nem túl pontos, de együtt erosek.

#### Hyperparaméterek

| Paraméter | Leírás | Alapértelmezés |
|-----------|--------|----------------|
| `n_estimators` | Döntési fák száma | 100 |
| `max_depth` | Fák maximális mélysége | None (korlátlan) |
| `max_features` | Max. feature-ök száma fánként | 'sqrt' |
| `min_samples_split` | Min. minta a csomópont osztásához | 2 |
| `min_samples_leaf` | Min. minta egy levélben | 1 |
| `bootstrap` | Bootstrap mintavételezés | True |

A Random Forest **örökli** a döntési fa összes hyperparaméterét, és vannak sajátjai is (pl. `n_estimators`).

**Feature importance:** A Random Forest képes megmutatni, mely feature-ök járulnak hozzá legjobban a predikcióhoz a `feature_importances_` attribútumon keresztül. Ez hasznos a feature selection-höz és a modell megértéséhez.

#### Kód példa

```python
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt
import numpy as np

# Random Forest tanítása
rf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=0)
rf.fit(X_train, y_train)
get_accuracy(rf, X_train, X_test, y_train, y_test)

# Feature importance kinyerése és vizualizáció
feature_importances = rf.feature_importances_
feature_names = X_train.columns

sorted_indices = np.argsort(feature_importances)[::-1]
sorted_importances = feature_importances[sorted_indices]
sorted_names = np.array(feature_names)[sorted_indices]

# Top 10 feature
top_n = 10
plt.figure(figsize=(12, 8))
plt.title("Top 10 Feature Importances - Random Forest")
plt.bar(sorted_names[:top_n], sorted_importances[:top_n])
plt.xlabel("Features")
plt.ylabel("Importance")
plt.xticks(rotation=45)
plt.show()
```

> **Fontos:** A feature importance eredményeit mindig **doménytudással** kell összevetni. Egy feature lehet statisztikailag fontos, de üzleti szempontból nem korrekt felhasználni (pl. ha az adat szivárgást -- data leakage -- okoz).

---

### Boosting alapelv

A Boosting módszer lényege, hogy a gyenge prediktorok **egymás után, szekvenciálisan** tanulnak -- minden újabb modell az elozo modell hibáira fókuszál.

**Fo különbség a Random Forest-tol:**

| Szempont | Random Forest (Bagging) | Boosting |
|----------|------------------------|----------|
| Tanulás | **Párhuzamos** -- a fák egymástól függetlenek | **Szekvenciális** -- minden fa az elozo hibáira épít |
| Párhuzamosíthatóság | Igen | Nem |
| Fo cél | Variancia csökkentése | Bias csökkentése |

### Gradient Boosting

A Gradient Boosting a **maradó hiba** (residual) csökkentésére fókuszál:
1. Betanít egy gyenge prediktort
2. Kiszámítja a maradó hibát (prediktált vs. valódi értékek)
3. A következo fa ezt a hibát próbálja prediktálni
4. Minden iterációban hozzáadunk egy fát
5. A végso predikció az összes fa együttes eredménye

A **learning rate** szabályozza, hogy az új fák mennyire járulnak hozzá a végso modellhez:
- **Magas learning rate:** gyorsabb tanulás, de nagyobb túltanulás kockázat
- **Alacsony learning rate:** lassabb, stabilabb tanulás, de több fa kell

```python
from sklearn.ensemble import GradientBoostingClassifier

gbc = GradientBoostingClassifier(
    max_depth=2,
    n_estimators=300,
    learning_rate=0.2
)
gbc.fit(X_train, y_train)
get_accuracy(gbc, X_train, X_test, y_train, y_test)
```

> **Sweet spot:** Van egy optimális paraméterbeállítás, ahol a modell a legjobb teszt pontosságot éri el. Ezt elore nem lehet tudni -- próbálkozással és hyperparaméter-optimalizálással található meg.

### AdaBoost

Az AdaBoost (Adaptive Boosting) másként muködik, mint a Gradient Boosting:
- A **hibásan prediktált mintákra** helyez nagyobb súlyt a következo iterációban
- A döntési határ folyamatosan változik, hogy jobban elkülönítse az osztályokat
- Minden iterációban a rosszul osztályozott pontok "fontosabbá" válnak

```python
from sklearn.ensemble import AdaBoostClassifier

ab = AdaBoostClassifier(n_estimators=100, random_state=0)
ab.fit(X_train, y_train)
get_accuracy(ab, X_train, X_test, y_train, y_test)
```

### XGBoost

Az **eXtreme Gradient Boosting** a gradient boosting továbbfejlesztett, optimalizált változata.

**Fo elonyök:**
- **Beépített regularizáció** (L1 és L2)
- **Ritka mátrixok** hatékony kezelése (sok nullát tartalmazó adatok)
- **Beépített cross-validation**
- Gyors számítás
- Igen pontos eredmények

```python
# pip install xgboost
from xgboost import XGBClassifier

xgb = XGBClassifier(max_depth=4, n_estimators=10)
xgb.fit(X_train, y_train)
get_accuracy(xgb, X_train, X_test, y_train, y_test)
```

### LightGBM

A **Light Gradient Boosting Machine** a Microsoft által fejlesztett, kifejezetten gyors és memóriahatékony boosting algoritmus.

**Fo elonyök:**
- **Nagyon gyors** -- gyakran a leggyorsabb boosting algoritmus
- **Kevés memóriát** használ
- Képes **kategóriaváltozókat kezelni** label encoding vagy one-hot encoding nélkül
- Párhuzamosan számítható
- Kicsi és nagy adathalmazoknál is jól teljesít
- Gyakran a **legpontosabb** algoritmus a gyakorlatban

```python
# pip install lightgbm
from lightgbm import LGBMClassifier

lgbm = LGBMClassifier(max_depth=4, n_estimators=50)
lgbm.fit(X_train, y_train)
get_accuracy(lgbm, X_train, X_test, y_train, y_test)
```

### CatBoost

A **Categorical Boosting** a Yandex által fejlesztett boosting algoritmus, amely kifejezetten jól kezeli a kategóriaváltozókat.

**Fo elonyök:**
- **Kategóriaváltozók** natív kezelése (nem kell encoding)
- **Ritka mátrixok** kezelése
- Szinte **nulla adateloofeldolgozás** szükséges
- Gyors és pontos

```python
# pip install catboost
from catboost import CatBoostClassifier

catboost = CatBoostClassifier(max_depth=7, n_estimators=5, verbose=0)
catboost.fit(X_train, y_train)
get_accuracy(catboost, X_train, X_test, y_train, y_test)
```

---

## Algoritmus-Választó Összefoglaló Táblázat

| Algoritmus | Típus | Fo elony | Fo hátrány | Mikor használd | Fontos HP-k |
|------------|-------|----------|------------|----------------|-------------|
| **KNN** | Osztályozás / Regresszió | Egyszerű, kevés paraméter | Lassú nagy adatoknál | Gyors prototípus, kis adathalmaz | `n_neighbors`, `metric` |
| **Lineáris Regresszió** | Regresszió | Interpretálható, gyors | Csak lineáris kapcsolatokat talál | Lineáris összefüggések, baseline | - |
| **Ridge** | Regresszió | Pontos, L2 regularizáció | Nem végez feature selection-t | Regresszió túltanulás ellen | `alpha` |
| **Lasso** | Regresszió | Feature selection (L1) | Kevésbé pontos, mint Ridge | Feature selection szükséges | `alpha` |
| **ElasticNet** | Regresszió | Ridge + Lasso kombinációja | Két HP hangolandó | Sok feature, regularizáció kell | `alpha`, `l1_ratio` |
| **Logisztikus Reg.** | Osztályozás | Interpretálható, gyors | Csak lineáris döntési határ | Bináris/többosztályos, baseline | `C`, `penalty`, `solver` |
| **SVM** | Osztályozás / Regresszió | Pontos, kernel trükk | Lassú nagy adatoknál, nehezen interpretálható | Nagy dimenziójú adat, bináris osztályozás | `C`, `kernel`, `gamma` |
| **Döntési Fa** | Osztályozás / Regresszió | Interpretálható, gyors, vizualizálható | Hajlamos túltanulásra | Interpretálhatóság fontos | `max_depth`, `min_samples_split`, `ccp_alpha` |
| **Random Forest** | Osztályozás / Regresszió | Pontos, feature importance, robusztus | Nehezebben interpretálható | Általános célú, pontos modell kell | `n_estimators`, `max_depth`, `max_features` |
| **Gradient Boosting** | Osztályozás / Regresszió | Nagyon pontos | Szekvenciális (lassabb), overfit veszély | Pontosság fontos | `n_estimators`, `learning_rate`, `max_depth` |
| **AdaBoost** | Osztályozás / Regresszió | Hibákra fókuszál | Zajos adatoknál gyenge | Hibákra érzékeny feladatok | `n_estimators`, `learning_rate` |
| **XGBoost** | Osztályozás / Regresszió | Gyors, pontos, beépített regularizáció | Külön telepítés, több HP | Versenyek, produkciós modellek | `n_estimators`, `max_depth`, `learning_rate`, `reg_alpha`, `reg_lambda` |
| **LightGBM** | Osztályozás / Regresszió | Leggyorsabb, kevés memória, kategória kezelés | Kis adatoknál overfit | Nagy adathalmaz, kategóriaváltozók | `n_estimators`, `max_depth`, `learning_rate`, `num_leaves` |
| **CatBoost** | Osztályozás / Regresszió | Kategória kezelés, minimális elofeldolgozás | Külön telepítés | Sok kategóriaváltozó, minimális adatkezelés | `n_estimators`, `max_depth`, `learning_rate` |

---

## Gyakorlati Útmutató

### Algoritmus-kiválasztási szempontok

A kurzus anyaga alapján a következo szempontok szerint érdemes algoritmust választani:

| Szempont | Ajánlott algoritmus(ok) |
|----------|------------------------|
| **Interpretálhatóság kell** | Lineáris modellek, Döntési fa |
| **Maximális pontosság kell** | Ensemble modellek (RF, GB, XGBoost, LightGBM), SVM |
| **Gyorsaság fontos** | Lineáris modellek + SGD, Döntési fa, KNN, SVM (lineáris kernel), LightGBM, XGBoost |
| **Minimális adat-elokeészítés** | LightGBM, CatBoost |
| **Nagy adathalmaz kezelése** | Random Forest, Gradient Boosting, Lineáris modellek + SGD, SVM (lineáris kernel) |
| **Feature selection szükséges** | Lasso, ElasticNet, Random Forest (feature importance) |

> **Gyakorlati tanács a kurzusból:** Gyakran érdemes **több algoritmust** is kipróbálni, azok hyperparamétereit optimalizálni, és akár ensemble modellbe (pl. voting) kombinálni oket. Nem csak egyetlen algoritmust kell kiválasztani!

### Modell-összehasonlítás sablon kód

```python
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    AdaBoostClassifier
)

# Ha telepítve vannak:
# from xgboost import XGBClassifier
# from lightgbm import LGBMClassifier
# from catboost import CatBoostClassifier

# Adatok előkészítése
# X_train, X_test, y_train, y_test = train_test_split(...)

# Modellek definiálása
models = {
    "KNN (k=5)": KNeighborsClassifier(n_neighbors=5),
    "Logistic Reg.": LogisticRegression(random_state=42, max_iter=1000),
    "SVM (RBF)": SVC(kernel='rbf', C=1),
    "Decision Tree": DecisionTreeClassifier(max_depth=5, random_state=42),
    "Random Forest": RandomForestClassifier(
        n_estimators=100, max_depth=8, random_state=42
    ),
    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=100, max_depth=3, learning_rate=0.1
    ),
    "AdaBoost": AdaBoostClassifier(n_estimators=100, random_state=42),
    # "XGBoost": XGBClassifier(max_depth=4, n_estimators=100),
    # "LightGBM": LGBMClassifier(max_depth=4, n_estimators=100),
    # "CatBoost": CatBoostClassifier(max_depth=5, n_estimators=100, verbose=0),
}

# Összehasonlítás
results = []
for name, model in models.items():
    model.fit(X_train, y_train)
    train_acc = accuracy_score(y_train, model.predict(X_train))
    test_acc = accuracy_score(y_test, model.predict(X_test))
    diff = train_acc - test_acc  # túltanulás indikátor
    results.append({
        "Modell": name,
        "Train Acc": round(train_acc, 4),
        "Test Acc": round(test_acc, 4),
        "Különbség": round(diff, 4),
        "Megjegyzés": "OK" if diff < 0.1 else "Túltanulás!"
    })

results_df = pd.DataFrame(results).sort_values("Test Acc", ascending=False)
print(results_df.to_string(index=False))
```

---

## Gyakori Hibák és Tippek

### 1. Target érték bekerül a feature set-be (data leakage)
- **Hiba:** Az X-ben benne hagyják a célváltozót, ami irreálisan magas pontosságot ad
- **Megoldás:** Mindig `X = df.drop(columns="target")` módszerrel hozzuk létre az X-et

### 2. Skálázás hiánya
- **Hiba:** A gradient descent cikk-cakkosan konvergál, a KNN és SVM rosszul muködik
- **Megoldás:** MinMaxScaler vagy StandardScaler használata, különösen lineáris modellek, KNN és SVM esetén

### 3. Túl magas learning rate
- **Hiba:** A Gradient Boosting gyorsan 100%-ra ugrik a train halmazon, de a test nem javul (vagy romlik)
- **Megoldás:** Kisebb learning rate, több estimator

### 4. Kiegyensúlyozatlan osztályok figyelmen kívül hagyása
- **Hiba:** Ha az egyik osztályból sokkal kevesebb van, az accuracy félrevezeto
- **Megoldás:** `class_weight='balanced'` paraméter, vagy más metrikák (precision, recall, F1) használata

### 5. Hiányzó értékek kezelésének elmulasztása
- **Hiba:** A modellnek hiányzó értékeket adunk (NaN, None, üres string, kérdojel)
- **Megoldás:** Imputálás (átlag, medián), vagy külön kategória létrehozása, de mindig ellenorizni kell az adatokat

### 6. Train és test pontosság nem vizsgálata együtt
- **Hiba:** Csak a test accuracy-t nézik
- **Megoldás:** Mindig mindkettot vizsgáljuk:
  - Train >> Test: **túltanulás** -- egyszerusítsd a modellt
  - Train ~ Test, de mindketto alacsony: **alultanulás** -- komplexebb modell kell
  - Train ~ Test, mindketto magas: ideális

### 7. A modell pontosságának értékelése kontextus nélkül
A kurzus három megközelítést ajánl:
1. **Szakértoi összehasonlítás:** mennyire pontosak emberek / szakértok az adott feladaton?
2. **Kutatási eredmények:** mit értek el mások hasonló adatokon?
3. **Belso vizsgálat:** train vs. test pontosság összehasonlítása

---

## Kapcsolódó Témák

- [06_modell_validacio_es_metrikak.md](06_modell_validacio_es_metrikak.md) -- Cross-validation, hyperparaméter-optimalizálás, kiértékelési metrikák (precision, recall, F1, ROC-AUC)
- [04_adatelokeszites_es_feature_engineering.md](04_adatelokeszites_es_feature_engineering.md) -- Adattisztítás, skálázás, encoding, feature selection
- [12_ajanlorendszerek.md](12_ajanlorendszerek.md) -- Felügyelt tanulás ajánlórendszerekben, cosine similarity, collaborative filtering
- [13_deep_learning_alapok.md](13_deep_learning_alapok.md) -- Deep Learning mint a felügyelt tanulás következő szintje, MLP, neurális hálózatok

## További Források

- **Scikit-learn dokumentáció:** https://scikit-learn.org/stable/supervised_learning.html
- **XGBoost dokumentáció:** https://xgboost.readthedocs.io/
- **LightGBM dokumentáció:** https://lightgbm.readthedocs.io/
- **CatBoost dokumentáció:** https://catboost.ai/docs/
- **Kurzus notebook:** `Tanayag/04_het/Cubix_ML_Engineer_ML_algorithms.ipynb`
