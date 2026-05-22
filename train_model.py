import pandas as pd
from sklearn.tree import DecisionTreeClassifier
import joblib

print("Loading dataset...")
# 1. Load the data
df = pd.read_csv('aquaculture_dataset.csv')

# 2. Separate the Inputs (Features) and the Output (Target)
X = df[['temperature', 'ph_level', 'turbidity']]
y = df['is_safe']

print("Training the Decision Tree model...")
# 3. Initialize and train the AI
model = DecisionTreeClassifier(random_state=42)
model.fit(X, y)

# 4. Save the "brain" to a file so Django can use it later
joblib.dump(model, 'aquaculture_model.pkl')

print("Success! Model trained and saved as 'aquaculture_model.pkl'")