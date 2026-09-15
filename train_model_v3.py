"""
Trains the predictive water-quality model used by the aquaculture backend.

The model does NOT judge whether the water is safe right now — that is settled
by the fixed rule in telemetry/rules.py. This model answers a different
question: given the present reading and how much each parameter has moved
since the previous reading, will the rule be triggered at any point within the
next 60 minutes?

Run from the repository root with the virtual environment active:

    python train_model_v3.py

Writes aquaculture_model_v3.pkl.
"""

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, matthews_corrcoef,
                             precision_score, recall_score, roc_auc_score)
from sklearn.tree import DecisionTreeClassifier, export_text

DATASET = "aquaculture_dataset_v3.csv"
OUTPUT = "aquaculture_model_v3.pkl"

FEATURES = ["temperature", "ph_level", "turbidity",
            "temp_delta", "ph_delta", "turb_delta"]
TARGET = "will_fail_60min"

# Settings chosen by five-fold cross-validation on the training split.
TREE = dict(max_depth=4, criterion="gini", min_samples_leaf=50,
            ccp_alpha=0.004, random_state=42)

df = pd.read_csv(DATASET, parse_dates=["timestamp"])
print(f"loaded {len(df):,} readings from {DATASET}")

# Only readings that were sound at the moment of measurement, that have valid
# deltas, and that have a full hour of record after them can be modelled.
usable = df[df.in_model_set].sort_values(["timestamp", "node_name"]).reset_index(drop=True)
print(f"{len(usable):,} usable for modelling "
      f"({len(df) - len(usable):,} withheld: already unsafe, following a gap, "
      f"or in the final hour)")

# Chronological split. A random split would leak, because the label of a
# reading is determined by the readings that follow it.
cut = int(len(usable) * 0.8)
train, test = usable.iloc[:cut], usable.iloc[cut:]
print(f"train {len(train):,} ending {train.timestamp.max():%d %b} "
      f"({train[TARGET].sum()} positive, {100 * train[TARGET].mean():.2f}%)")
print(f"test  {len(test):,} from {test.timestamp.min():%d %b} "
      f"({test[TARGET].sum()} positive, {100 * test[TARGET].mean():.2f}%)")

# Balance the training set only. The test set keeps the pond's real proportion.
X_bal, y_bal = SMOTE(random_state=42).fit_resample(train[FEATURES], train[TARGET])
print(f"after SMOTE: {len(X_bal):,} training rows, classes equal")

model = DecisionTreeClassifier(**TREE).fit(X_bal, y_bal)

pred = model.predict(test[FEATURES])
prob = model.predict_proba(test[FEATURES])[:, 1]
tn, fp, fn, tp = confusion_matrix(test[TARGET], pred).ravel()

print("\nperformance on the withheld readings")
print(f"  warned and a failure followed   TP {tp}")
print(f"  warned and none followed        FP {fp}")
print(f"  stayed quiet, none followed     TN {tn}")
print(f"  stayed quiet, a failure came    FN {fn}")
print(f"  accuracy           {100 * accuracy_score(test[TARGET], pred):6.2f}%")
print(f"  precision          {100 * precision_score(test[TARGET], pred):6.2f}%")
print(f"  recall             {100 * recall_score(test[TARGET], pred):6.2f}%")
print(f"  F1                 {100 * f1_score(test[TARGET], pred):6.2f}")
print(f"  balanced accuracy  {100 * balanced_accuracy_score(test[TARGET], pred):6.2f}%")
print(f"  MCC                {matthews_corrcoef(test[TARGET], pred):6.3f}")
print(f"  AUC                {roc_auc_score(test[TARGET], prob):6.3f}")

print("\nfitted tree")
print(export_text(model, feature_names=FEATURES, decimals=2))

joblib.dump(model, OUTPUT)
print(f"saved {OUTPUT}")
