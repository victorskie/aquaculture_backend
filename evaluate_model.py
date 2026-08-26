import pandas as pd
import joblib
from sklearn.metrics import accuracy_score, confusion_matrix

def evaluate_aquaculture_model():
    print("Loading model and dataset...")
    
    # 1. Load your trained model and the dataset
    model = joblib.load('aquaculture_model_v2.pkl')
    dataset = pd.read_csv('aquaculture_dataset_v2.csv')

    # 2. Define the inputs (X) and the actual correct answers (y_true)
    feature_columns = ['temperature', 'ph_level', 'turbidity', 'temp_delta', 'ph_delta', 'turb_delta']
    X = dataset[feature_columns]
    y_true = dataset['is_safe']

    # 3. Ask the AI to predict the safety of every row
    print("Generating predictions...")
    y_pred = model.predict(X)

    # 4. Calculate the metrics
    accuracy = accuracy_score(y_true, y_pred)
    conf_matrix = confusion_matrix(y_true, y_pred)

    # 5. Print the results clearly
    print("\n==================================")
    print("      MODEL EVALUATION RESULTS      ")
    print("==================================\n")
    print(f"Overall Accuracy: {accuracy * 100:.2f}%\n")
    
    print("Confusion Matrix:")
    print("[[True Negatives (TN)  False Positives (FP)]")
    print(" [False Negatives (FN) True Positives (TP) ]]\n")
    print(conf_matrix)
    print("\n==================================")

if __name__ == "__main__":
    evaluate_aquaculture_model()