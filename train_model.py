import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix
import joblib

def train_and_evaluate_model():
    print("Loading dataset...")
    try:
        dataset = pd.read_csv('aquaculture_dataset_v2.csv')
    except FileNotFoundError:
        print("Error: 'aquaculture_dataset_v2.csv' not found.")
        return

    # 1. Define Inputs (X) and Output (y)
    feature_columns = ['temperature', 'ph_level', 'turbidity', 'temp_delta', 'ph_delta', 'turb_delta']
    X = dataset[feature_columns]
    y = dataset['is_safe']

    # 2. THE FIX: Split the data into 80% Training and 20% Testing
    # random_state=42 ensures the split is the same every time you run it
    print("Splitting data into 80% Training and 20% Testing...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Initialize and train the AI ONLY on the 80% training data
    print("Training the Decision Tree model on training data...")
    model = DecisionTreeClassifier(random_state=42)
    model.fit(X_train, y_train)

    # 4. Evaluate the model on the 20% unseen test data
    print("Generating predictions on unseen test data...")
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    conf_matrix = confusion_matrix(y_test, y_pred)

    print("\n==================================")
    print("   REALISTIC EVALUATION RESULTS   ")
    print("==================================\n")
    print(f"Overall Test Accuracy: {accuracy * 100:.2f}%\n")
    
    print("Confusion Matrix:")
    print("[[True Negatives (TN)  False Positives (FP)]")
    print(" [False Negatives (FN) True Positives (TP) ]]\n")
    print(conf_matrix)
    print("\n==================================")

    # 5. Save the trained "brain" to the correct V2 file
    output_filename = 'aquaculture_model_v2.pkl'
    joblib.dump(model, output_filename)
    
    print(f"\nSuccess! Model trained and saved as '{output_filename}'")

if __name__ == "__main__":
    train_and_evaluate_model()