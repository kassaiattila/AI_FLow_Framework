"""
REFERENCE ONLY - Not used in production workflow.
Merged into email_intent_processor sklearn_classifier.py (2026-03-29).

CFPB Panasz Intent Routing Pipeline
====================================
Train-inference pipeline: panasz szöveg → intent → routing csoport.
Sklearn Pipeline: TfidfVectorizer → Classifier (LinearSVC / LightGBM)
"""

import json
import re
import sys
import warnings
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

warnings.filterwarnings("ignore")

# --- Projekt útvonalak ---
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_DIR / "complaints_sample_50k.csv"
MODEL_DIR = PROJECT_DIR / "models"
MODEL_PATH = MODEL_DIR / "intent_routing_model.joblib"
METADATA_PATH = MODEL_DIR / "model_metadata.json"

# --- Intent Mapping: 154 Issue → ~10+1 routing csoport ---
INTENT_MAP = {
    # 1. Hitjelentés pontossága
    'Incorrect information on your report': 'credit_report_accuracy',
    'Incorrect information on credit report': 'credit_report_accuracy',
    'Information is not mine': 'credit_report_accuracy',

    # 2. Személyazonosság-lopás / Jogosulatlan használat
    'Improper use of your report': 'identity_theft_unauthorized',
    'Fraud or scam': 'identity_theft_unauthorized',
    'Identity theft / Fraud / Embezzlement': 'identity_theft_unauthorized',
    'Unauthorized use of the card': 'identity_theft_unauthorized',
    'Improper use of my credit report': 'identity_theft_unauthorized',

    # 3. Vizsgálat / Escalation
    "Problem with a company's investigation into an existing problem": 'investigation_escalation',
    "Problem with a credit reporting company's investigation into an existing problem": 'investigation_escalation',
    "Problem with a company's investigation into an existing issue": 'investigation_escalation',
    "Credit reporting company's investigation": 'investigation_escalation',

    # 4. Tartozás-behajtási gyakorlat
    'Attempts to collect debt not owed': 'debt_collection_practice',
    'Written notification about debt': 'debt_collection_practice',
    'Communication tactics': 'debt_collection_practice',
    'False statements or representation': 'debt_collection_practice',
    'Took or threatened to take negative or legal action': 'debt_collection_practice',
    "Cont'd attempts collect debt not owed": 'debt_collection_practice',
    'Disclosure verification of debt': 'debt_collection_practice',
    'Threat of lawsuit on time barred debt': 'debt_collection_practice',
    'Taking/Coverage of a legal action': 'debt_collection_practice',
    'Threatened to contact someone or share information improperly': 'debt_collection_practice',
    'Taking/threatening an illegal action': 'debt_collection_practice',
    'Improper contact or sharing of info': 'debt_collection_practice',
    'Electronic communications': 'debt_collection_practice',

    # 5. Számlakezelés
    'Managing an account': 'account_management',
    'Closing an account': 'account_management',
    'Opening an account': 'account_management',
    'Closing your account': 'account_management',
    'Account opening, closing, or management': 'account_management',
    'Deposits and withdrawals': 'account_management',
    'Managing, opening, or closing your mobile wallet account': 'account_management',
    'Trouble accessing funds in your mobile or digital wallet': 'account_management',

    # 6. Fizetési problémák
    'Trouble during payment process': 'payment_issues',
    'Problem when making payments': 'payment_issues',
    'Problem caused by your funds being low': 'payment_issues',
    'Late fee': 'payment_issues',
    'Billing disputes': 'payment_issues',
    'APR or interest rate': 'payment_issues',
    'Problem with a lender or other company charging your account': 'payment_issues',
    'Charged fees or interest you didn\'t expect': 'payment_issues',
    'Money was not available when promised': 'payment_issues',
    'Unexpected or other fees': 'payment_issues',
    'Struggling to pay your bill': 'payment_issues',
    'Problems caused by my funds being low': 'payment_issues',
    'Problems when you are unable to pay': 'payment_issues',
    'Making/receiving payments, sending money': 'payment_issues',

    # 7. Jelzálog / Hitel szerviz
    'Dealing with your lender or servicer': 'mortgage_loan_servicing',
    'Struggling to pay mortgage': 'mortgage_loan_servicing',
    'Applying for a mortgage or refinancing an existing mortgage': 'mortgage_loan_servicing',
    'Loan servicing, payments, escrow account': 'mortgage_loan_servicing',
    'Closing on a mortgage': 'mortgage_loan_servicing',
    'Loan modification,collection,foreclosure': 'mortgage_loan_servicing',
    'Settlement process and target costs': 'mortgage_loan_servicing',
    'Application, originator, mortgage broker': 'mortgage_loan_servicing',
    'Dealing with my lender or servicer': 'mortgage_loan_servicing',
    'Settlement process and costs': 'mortgage_loan_servicing',

    # 8. Kártya- és vásárlási viták
    'Problem with a purchase shown on your statement': 'card_purchase_disputes',
    'Getting a credit card': 'card_purchase_disputes',
    'Fees or interest': 'card_purchase_disputes',
    'Other transaction problem': 'card_purchase_disputes',
    'Other features, terms, or problems': 'card_purchase_disputes',
    'Trouble using your card': 'card_purchase_disputes',
    'Advertising and marketing, including promotional offers': 'card_purchase_disputes',
    'Rewards': 'card_purchase_disputes',
    'Credit card protection / Coverage': 'card_purchase_disputes',
    'Unauthorized transactions or other transaction problem': 'card_purchase_disputes',
    'Trouble using the card': 'card_purchase_disputes',
    'Problem with a purchase or transfer': 'card_purchase_disputes',
    'Problem getting a card or closing an account': 'card_purchase_disputes',
    'Confusing or missing disclosures': 'card_purchase_disputes',
    'Confusing or misleading advertising or marketing': 'card_purchase_disputes',
    'Problem with additional add-on products or services': 'card_purchase_disputes',
    'Using a debit or ATM card': 'card_purchase_disputes',

    # 9. Hitel / Lízing kezelés
    'Managing the loan or lease': 'loan_lease_management',
    'Struggling to repay your loan': 'loan_lease_management',
    'Problems at the end of the loan or lease': 'loan_lease_management',
    'Getting a loan or lease': 'loan_lease_management',
    'Getting a loan': 'loan_lease_management',
    'Vehicle was repossessed or sold the vehicle': 'loan_lease_management',
    'Struggling to pay your loan': 'loan_lease_management',
    'Repossession': 'loan_lease_management',
    'Getting the loan': 'loan_lease_management',
    'Problem with the payoff process at the end of the loan': 'loan_lease_management',
    'Can\'t repay my loan': 'loan_lease_management',
    'Taking out the loan or lease': 'loan_lease_management',
    'Getting a line of credit': 'loan_lease_management',
    'Received a loan you didn\'t apply for': 'loan_lease_management',

    # 10. Kredit monitoring és hozzáférés
    'Unable to get your credit report or credit score': 'credit_monitoring_access',
    'Credit monitoring or identity theft protection services': 'credit_monitoring_access',
    'Problem with fraud alerts or security freezes': 'credit_monitoring_access',
    'Problem with customer service': 'credit_monitoring_access',
    'Unable to get credit report/credit score': 'credit_monitoring_access',
    'Identity theft protection or other monitoring services': 'credit_monitoring_access',
}

ROUTING_DISPLAY_NAMES = {
    'credit_report_accuracy': 'Hitjelentés pontossága',
    'identity_theft_unauthorized': 'Személyazonosság-lopás / Jogosulatlan használat',
    'investigation_escalation': 'Vizsgálat / Escalation',
    'debt_collection_practice': 'Tartozás-behajtási gyakorlat',
    'account_management': 'Számlakezelés',
    'payment_issues': 'Fizetési problémák',
    'mortgage_loan_servicing': 'Jelzálog / Hitel szerviz',
    'card_purchase_disputes': 'Kártya- és vásárlási viták',
    'loan_lease_management': 'Hitel / Lízing kezelés',
    'credit_monitoring_access': 'Kredit monitoring és hozzáférés',
    'other': 'Egyéb',
}

ROUTING_DESCRIPTIONS = {
    'credit_report_accuracy': 'Helytelen információ a hiteljelentésben, adatpontossági viták',
    'identity_theft_unauthorized': 'Személyazonosság-lopás, csalás, jogosulatlan hozzáférés',
    'investigation_escalation': 'Vizsgálati eljárás problémái, escalation kérelmek',
    'debt_collection_practice': 'Tartozás-behajtási gyakorlatok, kommunikáció, fenyegetések',
    'account_management': 'Számlanyitás, -zárás, -kezelés problémái',
    'payment_issues': 'Fizetési folyamat problémái, díjak, kamatok',
    'mortgage_loan_servicing': 'Jelzálog- és hitelszerviz, törlesztés, refinanszírozás',
    'card_purchase_disputes': 'Bankkártya-viták, vásárlási problémák, díjak',
    'loan_lease_management': 'Hitel/lízing kezelés, törlesztés, visszavétel',
    'credit_monitoring_access': 'Kredit monitoring, hiteljelentés hozzáférés, fraud alert',
    'other': 'Egyéb, nem kategorizált panaszok',
}


def clean_text(text: str) -> str:
    """Szövegtisztítás: lowercase, XXXX→REDACTED, speciális karakterek eltávolítása."""
    if pd.isna(text) or not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'x{2,}', 'redacted', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def map_intent(issue: str) -> str:
    """Issue → routing csoport mapping. Ismeretlen → 'other'."""
    if pd.isna(issue):
        return 'other'
    return INTENT_MAP.get(issue, 'other')


def load_and_prepare_data(data_path: str = None) -> tuple:
    """Adat betöltés, szűrés, intent mapping, szövegtisztítás, train-test split."""
    if data_path is None:
        data_path = str(DATA_PATH)

    df = pd.read_csv(data_path)

    # Szűrés: csak ahol van szöveges panasz
    df = df.dropna(subset=['Consumer complaint narrative'])
    df = df[df['Consumer complaint narrative'].str.strip().astype(bool)]

    # Intent mapping
    df['routing_group'] = df['Issue'].apply(map_intent)

    # Szövegtisztítás
    df['clean_text'] = df['Consumer complaint narrative'].apply(clean_text)

    # Üres szövegek szűrése
    df = df[df['clean_text'].str.len() > 0]

    X = df['clean_text']
    y = df['routing_group']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    return X_train, X_test, y_train, y_test, df


def build_pipeline(calibrate: bool = True) -> Pipeline:
    """Sklearn Pipeline: TfidfVectorizer → CalibratedClassifierCV(LinearSVC)."""
    if calibrate:
        classifier = CalibratedClassifierCV(
            LinearSVC(max_iter=2000, class_weight='balanced', random_state=42),
            cv=3
        )
    else:
        classifier = LinearSVC(max_iter=2000, class_weight='balanced', random_state=42)

    return Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=30000,
            min_df=5,
            max_df=0.95,
            ngram_range=(1, 2),
            sublinear_tf=True,
            strip_accents='unicode'
        )),
        ('clf', classifier)
    ])


def train(data_path: str = None, save: bool = True) -> dict:
    """Teljes tanítási folyamat: adat betöltés → pipeline fit → eval → save."""
    print("Adat betöltése és előfeldolgozás...")
    X_train, X_test, y_train, y_test, df = load_and_prepare_data(data_path)

    print(f"Train: {len(X_train)}, Test: {len(X_test)}")
    print(f"Routing csoportok: {sorted(y_train.unique())}")

    print("\nPipeline építés és tanítás...")
    pipe = build_pipeline(calibrate=True)
    pipe.fit(X_train, y_train)

    # Evaluation
    y_pred = pipe.predict(X_test)
    macro_f1 = f1_score(y_test, y_pred, average='macro')
    weighted_f1 = f1_score(y_test, y_pred, average='weighted')
    accuracy = (y_pred == y_test).mean()

    print("\n--- Eredmények ---")
    print(f"Accuracy:    {accuracy:.4f}")
    print(f"Macro F1:    {macro_f1:.4f}")
    print(f"Weighted F1: {weighted_f1:.4f}")
    print("\nRészletes jelentés:")
    print(classification_report(y_test, y_pred))

    # Mentés
    if save:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipe, MODEL_PATH)
        print(f"\nModell mentve: {MODEL_PATH}")

        metadata = {
            'accuracy': float(accuracy),
            'macro_f1': float(macro_f1),
            'weighted_f1': float(weighted_f1),
            'routing_groups': sorted(y_train.unique().tolist()),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'model_type': 'CalibratedClassifierCV(LinearSVC)',
        }
        with open(METADATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"Metaadatok mentve: {METADATA_PATH}")

    return {
        'pipeline': pipe,
        'accuracy': accuracy,
        'macro_f1': macro_f1,
        'weighted_f1': weighted_f1,
        'report': classification_report(y_test, y_pred, output_dict=True),
    }


def load_model() -> Pipeline:
    """Mentett modell betöltése."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Nincs mentett modell: {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


def predict(texts, model: Pipeline = None) -> list:
    """Routing csoport predikció szöveg(ek)re."""
    if model is None:
        model = load_model()

    if isinstance(texts, str):
        texts = [texts]

    cleaned = [clean_text(t) for t in texts]
    predictions = model.predict(cleaned)

    results = []
    for _text, pred in zip(texts, predictions, strict=False):
        results.append({
            'routing_group': pred,
            'routing_group_hu': ROUTING_DISPLAY_NAMES.get(pred, pred),
        })

    return results if len(results) > 1 else results[0]


def predict_proba(texts, model: Pipeline = None) -> list:
    """Routing + confidence + összes csoport valószínűsége."""
    if model is None:
        model = load_model()

    if isinstance(texts, str):
        texts = [texts]

    cleaned = [clean_text(t) for t in texts]

    # predict_proba csak CalibratedClassifierCV-vel működik
    probas = model.predict_proba(cleaned)
    classes = model.classes_

    results = []
    for i, _text in enumerate(texts):
        proba_dict = {cls: float(p) for cls, p in zip(classes, probas[i], strict=False)}
        sorted_classes = sorted(proba_dict.items(), key=lambda x: x[1], reverse=True)

        top_pred = sorted_classes[0]
        top_alternatives = [
            {
                'routing_group': cls,
                'routing_group_hu': ROUTING_DISPLAY_NAMES.get(cls, cls),
                'probability': round(prob, 4),
            }
            for cls, prob in sorted_classes[:3]
        ]

        results.append({
            'routing_group': top_pred[0],
            'routing_group_hu': ROUTING_DISPLAY_NAMES.get(top_pred[0], top_pred[0]),
            'confidence': round(top_pred[1], 4),
            'top_alternatives': top_alternatives,
            'all_probabilities': {k: round(v, 4) for k, v in proba_dict.items()},
        })

    return results if len(results) > 1 else results[0]


# --- CLI ---
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Használat:")
        print("  python pipeline.py train [data_path]")
        print('  python pipeline.py predict "panasz szöveg"')
        print('  python pipeline.py predict_proba "panasz szöveg"')
        sys.exit(1)

    command = sys.argv[1]

    if command == 'train':
        data_path = sys.argv[2] if len(sys.argv) > 2 else None
        train(data_path)

    elif command == 'predict':
        if len(sys.argv) < 3:
            print("Hiányzik a szöveg. Használat: python pipeline.py predict \"szöveg\"")
            sys.exit(1)
        text = sys.argv[2]
        result = predict(text)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == 'predict_proba':
        if len(sys.argv) < 3:
            print("Hiányzik a szöveg. Használat: python pipeline.py predict_proba \"szöveg\"")
            sys.exit(1)
        text = sys.argv[2]
        result = predict_proba(text)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print(f"Ismeretlen parancs: {command}")
        print("Elérhető parancsok: train, predict, predict_proba")
        sys.exit(1)
