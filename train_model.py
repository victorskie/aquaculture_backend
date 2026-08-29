import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from imblearn.over_sampling import SMOTE
import joblib

print("Loading dataset 'aquaculture_dataset_v2.csv'...")
df = pd.read_csv('aquaculture_dataset_v2.csv')

# Separate features (X) and labels (y)
X = df[['temperature', 'ph_level', 'turbidity', 'temp_delta', 'ph_delta', 'turb_delta']]
y = df['is_safe']

print("Splitting data into 80% Training and 20% Testing...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

# ==========================================
# PHASE 1: BEFORE SMOTE (Imbalanced Training)
# ==========================================
print("\n--- PHASE 1: BEFORE SMOTE ---")
# Using max_depth=4 to simulate a model that generalizes rather than memorizing noise
model_imbalanced = DecisionTreeClassifier(max_depth=4, random_state=42)
model_imbalanced.fit(X_train, y_train)
y_pred_imbalanced = model_imbalanced.predict(X_test)

print(f"Overall Accuracy: {accuracy_score(y_test, y_pred_imbalanced):.4f}")
print("Confusion Matrix:\n[[True Negatives (TN)  False Positives (FP)]\n [False Negatives (FN) True Positives (TP)]]")
print(confusion_matrix(y_test, y_pred_imbalanced))

# ==========================================
# PHASE 2: AFTER SMOTE (Balanced Training)
# ==========================================
print("\n--- PHASE 2: AFTER SMOTE ---")
print("Applying SMOTE to balance the training data...")
smote = SMOTE(random_state=42)
X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)

# Combine the balanced features back together
df_smote = X_train_smote.copy()

# Round the synthetic SMOTE data to match physical ESP32 sensor precision
df_smote = df_smote.round({
    'temperature': 2,
    'ph_level': 2,
    'turbidity': 1,
    'temp_delta': 2,
    'ph_delta': 2,
    'turb_delta': 1
})

# Add the labels back in
df_smote['is_safe'] = y_train_smote

# Export the new balanced data to a CSV file
df_smote.to_csv('aquaculture_dataset_smote.csv', index=False)
print("Balanced SMOTE dataset saved as 'aquaculture_dataset_smote.csv'")

print("\nTraining the final model on the balanced dataset...")
model_balanced = DecisionTreeClassifier(max_depth=4, random_state=42)
model_balanced.fit(X_train_smote, y_train_smote)
y_pred_balanced = model_balanced.predict(X_test)

print(f"Overall Accuracy: {accuracy_score(y_test, y_pred_balanced):.4f}")
print("Confusion Matrix:\n[[True Negatives (TN)  False Positives (FP)]\n [False Negatives (FN) True Positives (TP)]]")
print(confusion_matrix(y_test, y_pred_balanced))

# Export the final SMOTE-enhanced model for the backend
joblib.dump(model_balanced, 'aquaculture_model_v2.pkl')
print("\nSuccess! Final SMOTE model saved as 'aquaculture_model_v2.pkl'")