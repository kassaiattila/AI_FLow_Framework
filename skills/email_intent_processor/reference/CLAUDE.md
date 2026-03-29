# Email Intent Processor - Reference Materials

## CFPB ML Pipeline (referencia implementacio)
- cfpb_documentation.md: CFPB ML pipeline docs (CRISP-DM, sklearn TF-IDF+LinearSVC)
- cfpb_pipeline.py: Reference sklearn pipeline code (REFERENCE ONLY, beolvadt sklearn_classifier.py-ba)

## Cubix ML Engineering kurzus anyag (ml_methodology/)
Teljes feldolgozott tananyag a Cubix Machine Learning Engineering kurzusbol:
- 00_attekintes_es_navigacio.md - Kurzus attekintes
- 01_ml_alapfogalmak_es_tipusok.md - ML alapok, felugyelt/felugyeletlen tanulas
- 02_fejlesztoi_kornyezet_es_pandas.md - Python, pandas, numpy
- 03_adatmegertes_es_eda.md - Explorative Data Analysis
- 04_adatelokeszites_es_feature_engineering.md - Feature engineering, TF-IDF
- 05_felugyelt_tanulasi_algoritmusok.md - LinearSVC, LogReg, LightGBM, XGBoost
- 06_modell_validacio_es_metrikak.md - Macro F1, cross-validation, confusion matrix
- 07_hyperparameter_optimalizalas.md - Optuna, Grid/Random search
- 08_dimenziocsokkentes.md - TruncatedSVD, PCA
- 09_klaszterezes.md - K-Means, DBSCAN
- 10_mlops_es_deployment.md - Model serving, monitoring
- _kod_peldak/ - Python kodpeldak a tananyaghoz

## Hasznalati utmutato
- A referencia anyagok a training pipeline fejlesztesehez szolgalnak alapul
- A TF-IDF + CalibratedClassifierCV(LinearSVC) pipeline a CFPB pilot alapjan bevalt megoldas
- Magyar szovegekhez: strip_accents=None (NE hasznald 'unicode'-ot!)
- Minimum Macro F1 target: 0.60 (class-balanced metrika)
