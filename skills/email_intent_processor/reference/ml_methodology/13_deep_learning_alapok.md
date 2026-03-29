# Deep Learning Alapok

## Gyors Attekintes

> A **Deep Learning** (melytanulas) a gepi tanulas egy alterulete, amely mesterseges neuralalis halozatokat hasznal komplex mintazatok automatikus felismeresehez. A hagyomanyos ML modszerekkel szemben a DL legnagyobb elonye, hogy nem igenyel manualis **feature engineering**-et: a halozat kozvetlenul a nyers adatbol tanulja meg a relevans jellemzoket. Ez kulonosen kepek, szovegek, hang es idosoros adatok feldolgozasanal jelent aattoreset, ahol az emberi feature-tervezes korlatozott vagy lehetetlen lenne.

---

## Kulcsfogalmak

| Fogalom | Jelentes |
|---------|----------|
| **Deep Learning** | A gepi tanulas alterulete, amely tobbretegu neuralalis halozatokkal dolgozik. A "deep" (mely) a sok retegre utal, amelyek hierarchikusan egyre absztraktabb jellemzoket tanulnak. |
| **Neuron** | A neuralalis halozat alapepitoelemke. Bemeneteket kap, sulyozott osszegzest vegez, majd egy aktivalasi fuggvenyen keresztul kimenetet ad. |
| **Perceptron** | A legegyszerubb neuralalis halozat: egyetlen neuronbol all. Linearis osztalyozasra kepes, nemlinearis problemakra nem. |
| **Weight (suly)** | A neuron bemeneteinek sulyai, amelyek meghatarozzak, mennyire fontos az adott bemenet. A tanulas soran a halozat ezeket a sulyokat optimalizalja. |
| **Bias (eltohas)** | Egy extra parameter a neuronban, amely lehetove teszi a dontesi hatar eltolasat. Matematikailag: y = f(w*x + **b**). |
| **Activation Function (aktivalasi fuggveny)** | Nemlinearitast bevezeto fuggveny a neuron kimeneteben. Nelkule a halozat csak linearis transzformaciokra lenne kepes, barmennyire is mely. |
| **Sigmoid** | Aktivalasi fuggveny: f(x) = 1/(1+e^(-x)). Kimenete 0 es 1 kozott, binaris osztalyozasra hasznaljak. |
| **ReLU (Rectified Linear Unit)** | Aktivalasi fuggveny: f(x) = max(0, x). A leggyakrabban hasznalt fuggveny rejtett retegekben, gyors es hatekonyan szamithato. |
| **Softmax** | Aktivalasi fuggveny: a kimeneti ertekeket valoszinusegi eloszlassa alakitja. Tobbosztalyos osztalyozas kimeneti retegeben hasznaljak. |
| **Tanh** | Aktivalasi fuggveny: f(x) = (e^x - e^(-x))/(e^x + e^(-x)). Kimenete -1 es 1 kozott, a Sigmoid kozeppontra szimmetrikus valtozata. |
| **Fully Connected Layer (dense reteg)** | Olyan reteg, ahol minden neuron az elozo reteg osszes neuronajahoz kapcsolodik. Az ANN-ek alapveto epitoelemke. |
| **Hidden Layer (rejtett reteg)** | Az input es output reteg kozotti retegek. A deep learning "melyseget" a rejtett retegek szama adja. |
| **Input Layer (bemeneti reteg)** | A halozat elso retege, amely a nyers adatot fogadja. Neuronjainak szama megegyezik a feature-ok szamaval. |
| **Output Layer (kimeneti reteg)** | A halozat utolso retege, amely a predikalt eredmenyt adja. Neuronszama a feladattol fugg (1 binaris, N tobbosztalyos). |
| **Forward Propagation** | Az adat athalad a halozaton a bemenettol a kimenig. Minden reteg vegrehajt egy sulyozott osszegzest es egy aktivacios fuggvenyt. |
| **Backpropagation** | A tanulasi algoritmus: a kimeneti hiba gradienset visszaterjeszti a halozaton, es ennek alapjan frissiti a sulyokat (lancszabaly alkalmazasaval). |
| **Epoch** | Az osszes tanitoadat egyszeri vegigfuttatasa a halozaton (forward + backward pass). Tobbszaaz epoch szukseges a konvergalashoz. |
| **Batch Size** | Hany mintaval szamol a halozat egy sulyfrissitest megelozoen. Kisebb batch = zajos gradiens, de gyorsabb frissites. |
| **Learning Rate (tanulasi rata)** | A sulyfrissites merteke. Tul nagy: a modell nem konvergal. Tul kicsi: lassan tanul. Az egyik legfontosabb hyperparameter. |
| **Overfitting** | A modell tulaprozodan megtanulja a tanito adatot (zajt is), ezert uj adaton rosszul teljesit. Neuralalis halozatoknal kulonosen veszelyes a nagy parameterszam miatt. |
| **Dropout** | Regularizacios technika: a tanitas soran veletlenszeruen kinulaz neuronokat (pl. 20-50%-ot). Ez megakadalyozza, hogy a halozat tulsagosan tamaszkodjon egyes neuronokra. |
| **Multi-Label Classification** | Osztalyozasi feladat, ahol egy minta egyszerre tobb cimkehez is tartozhat (pl. egy film egyszerre thriller es drama). |
| **CNN (Convolutional Neural Network)** | Konvolucios halozat, elssorban kepek es grid-szeru adatok feldolgozasara. Lokalis mintazatokat (elek, formak) ismer fel. |
| **RNN (Recurrent Neural Network)** | Rekurrens halozat, szekvencialis adatokhoz (szoveg, idosoros). A korabbi lepesek informaciojat megorzi. |
| **Autoencoder** | Olyan halozat, amely az inputot reprodukalja az outputon, mikozben egy szuk "szukonyer" retegen halad at. Dimenziocsokkentesenre es anomalia detekciolra hasznaljak. |
| **GAN (Generative Adversarial Network)** | Ket halozat (generahor es diszkriminator) versenyez egymassal. A generator uj adatot (pl. kepet) general, a diszkriminator eldonti, valodi-e. |
| **Transformer** | Modern architektura, az **attention** mechanizmusra epit. Az NLP forradalmositoja (BERT, GPT). Kepekkel is hasznalhato (Vision Transformer). |

---

## Deep Learning vs Hagyomanyos ML

![ML vs Deep Learning dontesi diagram](_kepek_cleaned/02_tasks_of_ml/slide_03.png)

*1. abra: Mikor erdemes Deep Learning-et hasznalni? -- Ha van elegendo hardver kapacitas (GPU) ES nagy mennyisegu adat, a DL gyakran felulmulya a hagyomanyos ML modszereket.*

### A fo kulonbseg: Feature Engineering

A hagyomanyos gepi tanulas es a deep learning kozotti legfontosabb kulonbseg a **feature-ok** kezeleseben rejlik:

**Hagyomanyos ML pipeline:**
```
Nyers adat → Domain expert → Manualis feature tervezes → Feature matrix → ML modell → Eredmeny
```

**Deep Learning pipeline:**
```
Nyers adat → Neuralalis halozat (automatikus feature tanulas) → Eredmeny
```

### Reszletes osszehasonlitas

| Szempont | Hagyomanyos ML | Deep Learning |
|----------|---------------|---------------|
| Feature engineering | **Manualis**, domain tudasra epul | **Automatikus**, a halo tanulja |
| Adatigeny | Keves adat is eleg lehet | **Nagy mennyisegu** adat szukseges |
| Szamitasi igeny | Altalaban kisebb | **GPU/TPU** gyakran szukseges |
| Interpretalhataosag | Gyakran jol ertelmezheto | **"Fekete doboz"**, nehezen ertelmezheto |
| Feature-ok minosege | Domain experttol fugg | Az adat minosgetol fugg |
| Strukturalt adat | **Gyakran jobb** (tablaak) | Nem feltetlenul jobb tablan |
| Nem strukturalt adat | Korlatozott | **Kiemelkedo** (kep, szoveg, hang) |
| Modellek peldak | Logistic Regression, SVM, RF, XGBoost | CNN, RNN, Transformer |

### Mikor erdemes Deep Learning-et hasznalni?

**DL-t valaszd, ha**: nem strukturalt adatokkal (kep, szoveg, hang) dolgozol, nagyon sok adatod van (>10.000 minta), es komplex mintazatokat kell felismerni, amelyeket nehez kezzel leirni.

**Hagyomanyos ML-t valaszd, ha**: strukturalt / tablazatos adatokkal dolgozol, keves adatod van, ertelmezheto modellre van szukseged, vagy gyors iteraciora torekszel korlatozott eroforrasokkal.

---

## Feature Extraction Automatizalasa

![ML vs DL pipeline: feature extraction kulonbseg](_kepek_cleaned/02_tasks_of_ml/slide_04.png)

*2. abra: A hagyomanyos ML es a Deep Learning pipeline kozotti alapveto kulonbseg -- a DL automatikusan tanulja meg a feature-oket a nyers adatbol, nincs szukseg manualis feature engineering-re.*

A klasszikus ML-ben a **domain expert** tervezi meg a feature-oket kezzel (pl. kepeknel: elek szama, textura jellemzok), majd betaplaja az ML modellbe. Ez idoigenyes es a szakerto tudasatol fugg.

A DL halozatok **retegenkent** egyre absztraktabb jellemzoket tanulnak automatikusan:

**Pelda - Kepfelismeres CNN-nel:**
- **1. reteg**: alacsonyszintu jellemzok -- elek, vonalak, szinek
- **2-3. reteg**: kozepszintu jellemzok -- formak, texturak, sarkok
- **4-5. reteg**: magasszintu jellemzok -- szemek, orr, fulak
- **Kimeneti reteg**: teljes objektum felismeres -- "macska", "kutya"

Ez a hierarchikus feature tanulas az, ami a deep learninget olyan hatekonynya teszi kepek, hang es szoveg feldolgozasaban.

---

## Deep Learning Architekturak Attekintese

![AI/ML/DL reszletes taxonomia](_kepek_cleaned/02_tasks_of_ml/slide_06.png)

*3. abra: AI -> ML -> DL taxonomia reszletes algoritmus-bontassal -- a hagyomanyos ML modszerek (SVM, logisztikus regresszio, dontesi fak) es a DL architekturak (CNN, RNN, GAN) rendszertana.*

### CNN (Convolutional Neural Network)

A **CNN** a kepfeldolgozas alap architekturaja. **Konvolucios retegeket** hasznal, amelyek lokalis mintazatokat (elek, formak, texturak) ismernek fel. A **pooling retegek** csokkentik a teren dimenziot, vegul **fully connected retegek** vegzik az osztalyozast. Fo erossege a **transzlacio-invariancia**: felismeri a mintazatot, fuggeletlenul a poziciotol.

### RNN (Recurrent Neural Network)

Az **RNN** szekvencialis adatok feldolgozasara keszult. A korabbi lepesek informaciojat egy belso allapotban (hidden state) orzi meg. Fejlettebb valtozatai: **LSTM** (Long Short-Term Memory) es **GRU** (Gated Recurrent Unit), amelyek megoldjak a "vanishing gradient" problemat. Alkalmazasok: gepi forditas, idosoros elorejeles, beszedfelismeres.

### Autoencoder

Az **Autoencoder** megtanulja az input tomoritett reprezentaciojat (**encoder** → **bottleneck** → **decoder**). A halozat azt tanulja, mi a lenyeges az adatban. Alkalmazasok: dimenziocsollkentes, anomalia detektalas, zaj eltavolitas (denoising).

### GAN (Generative Adversarial Network)

A **GAN** ket halozat versengesebol all: a **generator** veletlenszeru zajbol uj adatot general, a **diszkriminator** eldonti, valodi-e. A ket halozat egyidejuleg tanul. Alkalmazasok: kepgeneralas, adataugmentacio, stilustranszfer.

### Transformer

A **Transformer** a **self-attention** mechanizmusra epit: a szekvencia minden eleme "figyel" az osszes tobbire. Parhuzamositahato (szemben az RNN-nel), es pozicio-kodolast hasznal. Neves modellek: **BERT**, **GPT**, **T5**, **LLaMA**. Alkalmazasok: szovegertelmenes, szoveggeneralas, gepi forditas, kod-generalas.

---

## A Perceptron Modell

### Egyetlen neuron felepitese

A **Perceptron** a neuralalis halozatok legegyszerubb epitoeleme -- egyetlen neuronbol all. Frank Rosenblatt javasolta 1957-ben.

```
   x1 ──w1──┐
             │
   x2 ──w2──┤
             ├──→ Σ(wi*xi) + b ──→ f(z) ──→ kimenet (y)
   x3 ──w3──┤
             │
   xn ──wn──┘
             ↑
           bias (b)
```

### Matematikai formula

A perceptron kimenete:

```
z = Σ(wi * xi) + b = w1*x1 + w2*x2 + ... + wn*xn + b

y = f(z)
```

ahol:
- **xi**: bemeneti ertekek (feature-ok)
- **wi**: sulyok (weights) -- meghatarozzak az egyes bemenetek fontossagat
- **b**: bias (eltolas) -- lehetove teszi a dontesi hatar mozgatasat
- **f()**: aktivalasi fuggveny -- nemlinearitast vezet be
- **y**: a neuron kimenete

### Linearis vs. nemlinearis szeparacio

A perceptron onmagaban **linearis** szeparaciora kepes:
- Binaris osztalyozas: egy egyenessel (2D-ben) vagy siikkal (magasabb dimenzioban) valasztja el az osztalyokat
- **XOR problema**: a perceptron NEM kepes megoldani (nemlinearis hatar kellene)
- Megoldas: **tobb reteg** (Multi-Layer Perceptron) -- nemlinearis aktivalasi fuggvenyekkel

### Tanulasi folyamat

1. **Inicializalas**: veletlenszeru sulyok es bias
2. **Forward pass**: kiszamitja a kimenetet az aktualis sulyokkal
3. **Hiba szamitas**: osszehasonlitja a predikcioot a valos cimkevel
4. **Sulyfrissites**: a hiba iranyaba modositja a sulyokat
5. **Ismetles**: amig a hiba nem csokken egy elfogadhato szintre

---

## Mestlerseges Neuralalis Halozat (ANN) Architektura

### Retegek felepitese

Az **ANN (Artificial Neural Network)** tobb reteg neuronbol all:

```
  Bemeneti reteg      Rejtett reteg(ek)       Kimeneti reteg
  (Input Layer)       (Hidden Layers)         (Output Layer)

  ┌───┐               ┌───┐  ┌───┐           ┌───┐
  │ x1│──────────────→ │ h1│──│ h4│──────────→│ y1│
  ├───┤               ├───┤  ├───┤           ├───┤
  │ x2│──────────────→ │ h2│──│ h5│──────────→│ y2│
  ├───┤               ├───┤  ├───┤           └───┘
  │ x3│──────────────→ │ h3│──│ h6│
  └───┘               └───┘  └───┘
                       1. reteg  2. reteg
```

- **Input layer**: a feature-ok szama hatarozza meg (pl. 784 neuron egy 28x28-as kephez)
- **Hidden layers**: a "tanulas" itt tortenik. Tobb reteg = melyebb halozat = komplexebb mintazatok
- **Output layer**: a feladattol fugg
  - Binaris osztalyozas: 1 neuron + Sigmoid
  - Tobbosztalyos osztalyozas: N neuron + Softmax
  - Regresszio: 1 neuron, aktivalas nelkul

### Fully Connected (Dense) Layers

Egy **fully connected** retegben minden neuron osszekapcsolodik az elozo reteg osszes neuronajaval. Ez azt jelenti, hogy ha az elozo retegben `m` neuron van es az aktualis retegben `n`, akkor `m * n` suly es `n` bias parameter van.

**Pelda**: 100 bemeneti neuron es 64 neuronos rejtett reteg eseten: 100 * 64 + 64 = **6.464 parameter** -- mar egyetlen retegnel is!

### Forward Propagation

A **forward propagation** soran az adat vegighalad a halozaton:

```
1. Input reteg:    X (nyers adat)
                    ↓
2. Rejtett reteg 1: z1 = W1 * X + b1  →  a1 = f(z1)
                    ↓
3. Rejtett reteg 2: z2 = W2 * a1 + b2 →  a2 = f(z2)
                    ↓
4. Output reteg:    z3 = W3 * a2 + b3 →  y_pred = g(z3)
```

ahol:
- **Wi**: az i. reteg sulymatrixa
- **bi**: az i. reteg bias vektora
- **f()**: rejtett retegek aktivalasi fuggvenye (pl. ReLU)
- **g()**: kimeneti reteg aktivalasi fuggvenye (pl. Softmax)

### Backpropagation

A **backpropagation** a tanulas motorja. Lenyege:

1. **Hibaszamitas**: a kimeneten kiszamitja a veszteseget (loss), pl. cross-entropy
2. **Gradiens szamitas**: a lancszabaly (chain rule) segitsegevel kiszamitja, hogy minden egyes suly mennyiben jarult hozza a hibahoz
3. **Sulyfrisssites**: a gradiens ellentetes iranyaba modositja a sulyokat

```
Loss(y, y_pred)
      ↓
∂Loss/∂W3 → W3 frissites
      ↓
∂Loss/∂W2 → W2 frissites
      ↓
∂Loss/∂W1 → W1 frissites
```

A **learning rate** hatarozza meg, mekkora lepeseket tesz a frissites soran:
```
W_uj = W_regi - learning_rate * ∂Loss/∂W
```

### Hyperparameter-ek

A neuralalis halozatok legfontosabb hyperparameterei:

| Hyperparameter | Jelentes | Tipikus ertekek |
|---------------|----------|-----------------|
| **Rejtett retegek szama** | A halozat melysege | 1-5 (kezdononek 1-2) |
| **Neuronok szama retegenkent** | A reteg szelessege | 32, 64, 128, 256, 512 |
| **Learning rate** | Sulyfrisssites merteke | 0.001, 0.01, 0.1 |
| **Epochs** | Hany tanulasi kor | 50-500 |
| **Batch size** | Mintak szama egy frissiteshez | 16, 32, 64, 128 |
| **Activation function** | Rejtett retegek fuggvenye | ReLU (leggyakoribb) |
| **Optimizer** | Optimalizalasi algoritmus | Adam, SGD |
| **Dropout rate** | Regularizacio merteke | 0.2-0.5 |

---

## Aktivalasi Fuggvenyek

### Miert kellenek aktivalasi fuggvenyek?

Aktivalasi fuggvenyek nelkul a neuralalis halozat -- barmennyire is mely -- csak **linearis transzformaciokat** tud vegrehajtani. Azaz:

```
f(g(h(x))) = A * x + b    (linearis)
```

Az aktivalasi fuggvenyek **nemlinearitast** vezetnek be, amivel a halozat kepes osszetett, nemlinearis donksihatarokat megtanulni.

### Osszehasonlitas

| Fuggveny | Keplet | Tartomany | Alkalmazas | Elonyok | Hatranyok |
|----------|--------|-----------|------------|---------|-----------|
| **Sigmoid** | f(x) = 1/(1+e^(-x)) | (0, 1) | Binaris osztalyozas output | Valoszinusegkent ertelmezheto | Vanishing gradient, lassu |
| **ReLU** | f(x) = max(0, x) | [0, +inf) | Rejtett retegek | Gyors, egyszeru, hatekoky | "Dying ReLU" (negativ resz 0) |
| **Tanh** | f(x) = (e^x-e^(-x))/(e^x+e^(-x)) | (-1, 1) | Rejtett retegek | Kozeppontra szimmetrikus | Vanishing gradient |
| **Softmax** | f(xi) = e^xi / Σe^xj | (0, 1), osszeg = 1 | Tobbosztalyos output | Valoszinusegi eloszlas | Csak output retegben |
| **Leaky ReLU** | f(x) = max(0.01x, x) | (-inf, +inf) | Rejtett retegek | Megoldja a "dying ReLU"-t | Extra hyperparameter |

### Reszletes kiegeszites

- **Sigmoid**: Tortenelmi jelentoseggel bir, de a **vanishing gradient** problema miatt (szellso ertekeknel a gradiens kozel 0) modern halozatokban a rejtett retegekben mar ritkan hasznaljak. Output retegben binaris osztalyozasnal viszont meg klasszikus.
- **ReLU**: A leggyakoribb, mert egyszeru es gyors. Hatranya a "dying ReLU": ha egy neuron kimenete mindig negativ, a gradiense 0 lesz es tobbe nem tanul. Megoldas: **Leaky ReLU**.
- **Tanh**: A Sigmoid kozeppontra szimmetrikus valtozata. RNN-ekben (LSTM, GRU) meg gyakran hasznaljak. Szinten erintett a vanishing gradient altal.
- **Softmax**: Az osszes kimenet osszege pontosan 1.0. Pelda: 3 osztaly eseten [0.7, 0.2, 0.1] -- 70% valoszinuseggel az 1. osztaly.

---

## Multi-Label Classification

### Multi-Class vs Multi-Label

Fontos megkulonboztetni ezt a ket fogalmat:

| Szempont | Multi-Class | Multi-Label |
|----------|------------|-------------|
| **Cimkek szama** | Pontosan 1 cimke | 1 vagy tobb cimke |
| **Pelda** | Allat: macska VAGY kutya VAGY madar | Film: akcio ES thriller ES drama |
| **Output** | Softmax (1 erteket valaszt) | Sigmoid minden kimeneten (kulon valoszinuseg) |
| **Kimeneti reteg** | 1 neuron osztalyonkent, osszetartoznak | 1 neuron cimkenken, fuggetlenek |
| **Loss fuggveny** | Categorical cross-entropy | Binary cross-entropy (cimkenkent) |

### Peldak multi-label feladatokra

- **Film mufajok**: egy film egyszerre lehet "akcio", "thriller" es "sci-fi"
- **Orvosi diagnozis**: egy paciens egyszerre tobbfele betegsegben is szenvedhet
- **Kep cimkezes**: egy fotoon egyszerre lehet "auto", "fa" es "epulet"

### MLPClassifier multi-label hasznalata

Az sklearn `MLPClassifier` tamogatja a multi-label osztalyozast. A celvaltozo `multi_label_indicator` formatumban (binaris matrix) kell megadni:

```python
from sklearn.neural_network import MLPClassifier
from sklearn.datasets import make_multilabel_classification
from sklearn.model_selection import train_test_split

# Multi-label adat generalasa
X, y = make_multilabel_classification(
    n_samples=1000,
    n_features=20,
    n_classes=5,    # 5 lehetseges cimke
    n_labels=2,     # atlagosan 2 cimke mintanken
    random_state=42
)

# y alakja: (1000, 5) -- binaris matrix
# Pl. [1, 0, 1, 0, 1] = az 1., 3. es 5. cimke igaz

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

mlp = MLPClassifier(
    hidden_layer_sizes=(100, 50),
    max_iter=500,
    random_state=42
)
mlp.fit(X_train, y_train)

# Predikcio: minden cimkere kulon 0/1 ertek
y_pred = mlp.predict(X_test)
print(f"Pelda predikcio: {y_pred[0]}")
```

---

## Osszehasonlito Tablazat -- Deep Learning Architekturak

| Architektura | Fo alkalmazas | Bemeneti adat | Kulcs mechanizmus | Peldak |
|-------------|--------------|---------------|-------------------|--------|
| **ANN / MLP** | Tablazatos adat, altalanos | Strukturalt | Fully connected retegek | Hitelbiraalt, ugyfel-elorejelzes |
| **CNN** | Kepfeldolgozas | Kepek, grid adat | Konvolucio + pooling | ImageNet, arcfelismeres |
| **RNN / LSTM** | Szekvenciak | Szoveg, idosoros | Rekurrens kapcsolatok | Gepi forditas, idosoros elorejeles |
| **Autoencoder** | Dimenzio csokkentes | Barmilyen | Encoder-decoder, bottleneck | Anomalia detektalas, zaj eltav. |
| **GAN** | Generativ feladatok | Kepek, adat | Generator vs diszkriminator | Kepgeneralas, data augmentation |
| **Transformer** | NLP, Vision | Szoveg, kepek | Self-attention | BERT, GPT, Vision Transformer |

### Melyik architekturaat valaszd?

```
Milyen adatod van?
│
├── Tablazatos / strukturalt → ANN / MLP (vagy hagyomanyos ML!)
│
├── Kep → CNN
│
├── Szoveg / szekvencia
│   ├── Rovid szoveg, osztalyozas → Transformer (BERT)
│   ├── Szoveggeneralas → Transformer (GPT)
│   └── Idosoros elorejeles → RNN / LSTM
│
├── Anomalia detektalas → Autoencoder
│
└── Uj adat generalasa → GAN vagy Autoencoder
```

---

## Gyakorlati Utmutato

### Mikor valaszd a DL-t es mikor a hagyomanyos ML-t?

```
       Van eleg adatod? (>10.000 minta)
       │
       ├── NEM → Hagyomanyos ML (RF, XGBoost, SVM)
       │
       └── IGEN
            │
            ├── Strukturalt / tablazatos adat?
            │   ├── IGEN → Probald eloszoer az XGBoost/RF-et!
            │   │          Ha nem eleg, MLP-vel kiegeszitheted
            │   └── NEM → Deep Learning
            │
            └── Kep / Szoveg / Hang / Video?
                └── IGEN → Deep Learning (CNN / Transformer / RNN)
```

### Perceptron es MLP pelda sklearn-nel

Az sklearn **MLPClassifier** es **Perceptron** osztalyok lehetove teszik, hogy GPU nelkul, egyszeru Python kornyezetben is kiprobald a neuralalis halozatokat:

```python
from sklearn.linear_model import Perceptron
from sklearn.neural_network import MLPClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Adat generalasa
X, y = make_classification(n_samples=1000, n_features=20, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Perceptron -- egyetlen neuron
perc = Perceptron(max_iter=100, random_state=42)
perc.fit(X_train, y_train)
print(f"Perceptron pontossag: {accuracy_score(y_test, perc.predict(X_test)):.4f}")

# MLP -- tobbretegu halozat
mlp = MLPClassifier(
    hidden_layer_sizes=(100, 50),    # 2 rejtett reteg: 100 es 50 neuron
    activation='relu',               # ReLU aktivalasi fuggveny
    max_iter=500,
    random_state=42
)
mlp.fit(X_train, y_train)
print(f"MLP pontossag: {accuracy_score(y_test, mlp.predict(X_test)):.4f}")
```

### Aktivalasi fuggvenyek vizualizacioja

```python
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(-5, 5, 200)

# Sigmoid
sigmoid = 1 / (1 + np.exp(-x))

# ReLU
relu = np.maximum(0, x)

# Tanh
tanh = np.tanh(x)

fig, axes = plt.subplots(1, 3, figsize=(15, 4))

axes[0].plot(x, sigmoid, 'b-', linewidth=2)
axes[0].set_title('Sigmoid')
axes[0].axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
axes[0].grid(True, alpha=0.3)

axes[1].plot(x, relu, 'r-', linewidth=2)
axes[1].set_title('ReLU')
axes[1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
axes[1].grid(True, alpha=0.3)

axes[2].plot(x, tanh, 'g-', linewidth=2)
axes[2].set_title('Tanh')
axes[2].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
```

### Kod peldak

A reszletes, futtathato kod peldak elerhetek:
- Feldolgozott peldak: [_kod_peldak/deep_learning_alapok.py](_kod_peldak/deep_learning_alapok.py)

### Altalanos DL/MLP workflow

```python
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# 1. Adat betoltese es skalazasa -- FONTOS a neuralalis halozatoknal!
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 2. Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42)

# 3. MLP modell definialasa
mlp = MLPClassifier(
    hidden_layer_sizes=(128, 64, 32),  # 3 rejtett reteg
    activation='relu',
    solver='adam',
    max_iter=500,
    early_stopping=True,               # Overfitting ellen
    validation_fraction=0.1,
    random_state=42
)

# 4. Tanitas
mlp.fit(X_train, y_train)

# 5. Kiertekeles
y_pred = mlp.predict(X_test)
print(classification_report(y_test, y_pred))
```

---

## Gyakori Hibak es Tippek

### Hibak

#### 1. Skalazas elfelejtese

A neuralalis halozatok **nagyon erzekeynyek** a bemeneti adatok skalajara. Ha az egyik feature 0-1 kozott, a masik 0-100.000 kozott van, a nagy erteku feature dominalni fog.

```python
# HIBAS: skalazas nelkul
mlp.fit(X_train, y_train)  # Rossz eredmenyt adhat!

# HELYES: StandardScaler-rel
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)  # transform, NEM fit_transform!
mlp.fit(X_train_scaled, y_train)
```

#### 2. Tul bonyolult halozat kis adathalmazra

Ha csak 500 mintad van es 5 rejtett reteget, retegenkent 512 neuronnal hasznalsz, a modell meg fogja tanulni a zajt is (**overfitting**).

```python
# HIBAS: tul bonyolult kis adatra
mlp = MLPClassifier(hidden_layer_sizes=(512, 256, 128, 64, 32))

# HELYES: egyszerubb architektura
mlp = MLPClassifier(hidden_layer_sizes=(50, 25), early_stopping=True)
```

#### 3. Learning rate rosszul valasztasa

- **Tul nagy** (pl. 1.0): a modell "ugral", nem konvergal
- **Tul kicsi** (pl. 0.000001): a modell nagyon lassan tanul, sok epoch kell

```python
# Ajanlott: Adam optimizer-rel az alapertelmezett jo kiindulas
mlp = MLPClassifier(solver='adam', learning_rate_init=0.001)
```

#### 4. Multi-class es multi-label osszetevesztese

```python
# Multi-class: y = [0, 1, 2, 0, 1] -- egy cimke mintankent
# Multi-label: y = [[1,0,1], [0,1,0], [1,1,0]] -- tobb cimke, binaris matrix
```

#### 5. Konvergencia figyelmen kivul hagyasa

Ha a `ConvergenceWarning` megjelenik, a modell nem konvergalt -- noveld a `max_iter` erteket!

```python
# Ha figyelmeztetes jon: "ConvergenceWarning: Stochastic Optimizer..."
mlp = MLPClassifier(max_iter=1000)  # Az alapertelmezett 200 nem mindig eleg
```

### Tippek

#### 1. Kezdd egyszeruen

Eloszor probald meg egy rejtett reteggel es keves neuronnal. Ha nem eleg jo, fokozatosan bovitsd:

```python
# 1. lepes: egyszeru modell
mlp1 = MLPClassifier(hidden_layer_sizes=(50,))

# 2. lepes: ha nem eleg jo, bovits
mlp2 = MLPClassifier(hidden_layer_sizes=(100, 50))

# 3. lepes: ha meg nem eleg, tedd melyebbe
mlp3 = MLPClassifier(hidden_layer_sizes=(200, 100, 50))
```

#### 2. Hasznalj early stopping-ot

Az **early stopping** figyeli a validacios veszteseget, es megallitja a tanitrast, ha mar nem javul -- ez a legegyszerubb overfitting-vedelem:

```python
mlp = MLPClassifier(
    early_stopping=True,
    validation_fraction=0.1,    # a tanito adat 10%-a validaciora
    n_iter_no_change=10         # 10 epoch javulas nelkul → megall
)
```

#### 3. Tanulasi gorbe vizualizalasa

Az `mlp.loss_curve_` attributum megmutatja, hogyan csokken a veszteseg az epochok soran:

```python
plt.plot(mlp.loss_curve_)
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('Tanulasi gorbe')
plt.show()
```

Ha a gorbe "zajos" es nem csokken: probald csokkenteni a learning rate-et.
Ha a gorbe hamar platora er: talan tul egyszeru a modell.

#### 4. Hasznald a GridSearchCV-t a hyperparameter hangoalshoz

```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'hidden_layer_sizes': [(50,), (100,), (100, 50), (100, 50, 25)],
    'activation': ['relu', 'tanh'],
    'learning_rate_init': [0.001, 0.01],
}

grid = GridSearchCV(MLPClassifier(max_iter=500), param_grid, cv=3, n_jobs=-1)
grid.fit(X_train_scaled, y_train)
print(f"Legjobb parameterek: {grid.best_params_}")
```

#### 5. Dropout es regularizacio

Az sklearn MLPClassifier az `alpha` parametern keresztul L2 regularizaciot tamogat:

```python
mlp = MLPClassifier(
    hidden_layer_sizes=(100, 50),
    alpha=0.01,   # L2 regularizacio erossege (alapertelmezett: 0.0001)
)
```

> **Megjegyzes**: Igazi dropout, batch normalization es egyeb fejlett technikak hasznalatahoz PyTorch vagy TensorFlow szukseges.

---

## Kapcsolodo Temak

- [05_felugyelt_tanulasi_algoritmusok.md](05_felugyelt_tanulasi_algoritmusok.md) -- A felügyelt tanulasi algoritmusok, amelyekre a neuralalis halozatok epitennek (osztalyozas, regresszio)
- [07_hyperparameter_optimalizalas.md](07_hyperparameter_optimalizalas.md) -- A DL modellek hyperparameter hangolasa (GridSearch, RandomSearch, Optuna)
- [01_ml_alapfogalmak_es_tipusok.md](01_ml_alapfogalmak_es_tipusok.md) -- ML vs DL: alapfogalmak es a tanulasi tipusok keretrendszere
- [08_dimenziocsokkentes.md](08_dimenziocsokkentes.md) -- Az autoencoder mint dimenziocsokkento modszer, valamint a PCA es egyeb hagyomanyos modszerek
- [06_modell_validacio_es_metrikak.md](06_modell_validacio_es_metrikak.md) -- Modellertekelesi metrikak, amelyek a DL modellekre is ervenyesek

---

## Tovabbi Forrasok

### Kurzus anyagai
- **Videok**: 08_09 es 08_10 (Cubix EDU ML Engineering, 8. het)
- **Transcript-ek**: `Tanayag/08_het/08_09_*_transcript_hu.md`, `08_10_*_transcript_hu.md`

### Kulso hivatkozasok es dokumentaciok
- sklearn MLPClassifier: [sklearn.neural_network.MLPClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPClassifier.html)
- sklearn Perceptron: [sklearn.linear_model.Perceptron](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Perceptron.html)
- PyTorch tutorial (ha DL framework-re valtasz): [pytorch.org/tutorials](https://pytorch.org/tutorials/)
- TensorFlow / Keras kezdolpepes: [tensorflow.org/tutorials](https://www.tensorflow.org/tutorials)
- fastai (magas szintu DL library): [docs.fast.ai](https://docs.fast.ai/)
- 3Blue1Brown -- Neural Networks vizualisan: [YouTube playlist](https://www.youtube.com/playlist?list=PLZHQObOWTQDNU6R1_67000Dx_ZCJB-3pi)
- Stanford CS231n -- CNN for Visual Recognition: [cs231n.stanford.edu](https://cs231n.stanford.edu/)
- Stanford CS224n -- NLP with Deep Learning: [cs224n.stanford.edu](https://web.stanford.edu/class/cs224n/)

---

## Osszefoglalas -- A kurzus legfontosabb tanulsagai

1. **A Deep Learning** nem varazslat -- a hagyomanyos ML modszerek sokszor elegek es jobbak, kulonosen tablazatos adaton
2. **A Perceptron** az alapepitelemke: egy neuron = sulyozott osszeg + bias + aktivalasi fuggveny
3. **Az ANN** retegekbe szervezett neuronokbol all: input → hidden → output
4. **A ReLU** a leggyakoribb aktivalasi fuggveny rejtett retegekben, a **Sigmoid** binaris output-hoz
5. **Multi-label vs multi-class**: fontos megkulonboztetni -- a multi-label eseten tobb cimke is igaz lehet egyszerre
6. A DL igazi ereje a **nem strukturalt adatoknal** (kep, szoveg, hang) mutatkozik meg
7. Az sklearn MLPClassifier **jo kiindulopont**, de komoly DL feladatokhoz PyTorch vagy TensorFlow szukseges
8. **Mindig skalazz** (StandardScaler) a neuralalis halozatok elott!
9. **Kezdd egyszeruen**, es fokozatosan novelod a komplexitast
10. Hasznalj **early stopping**-ot az overfitting elkerulesehez
