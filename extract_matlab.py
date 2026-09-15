import joblib
import numpy as np
from sklearn.tree import _tree

def export_tree_to_matlab(model, feature_names):
    # Your model is a single DecisionTreeClassifier, so we access tree_ directly
    tree_ = model.tree_
        
    feature_name = [
        feature_names[i] if i != _tree.TREE_UNDEFINED else "undefined!"
        for i in tree_.feature
    ]

    # Matching the exact 6 features for the MATLAB function arguments
    print("function prediction = evaluate_water(temperature, ph_level, turbidity, temp_delta, ph_delta, turb_delta)")
    
    def recurse(node, depth):
        indent = "    " * (depth + 1)
        if tree_.feature[node] != _tree.TREE_UNDEFINED:
            name = feature_name[node]
            threshold = tree_.threshold[node]
            print(f"{indent}if {name} <= {threshold:.4f}")
            recurse(tree_.children_left[node], depth + 1)
            print(f"{indent}else")
            recurse(tree_.children_right[node], depth + 1)
            print(f"{indent}end")
        else:
            # Leaf node gives the prediction (0 or 1)
            value = tree_.value[node]
            class_idx = np.argmax(value)
            print(f"{indent}prediction = {class_idx};")

    recurse(0, 0)
    print("end")

# 1. Load the .pkl using joblib as it was saved
print("Loading model...")
model = joblib.load('aquaculture_model_v2.pkl')

# 2 & 3. Read structure and print as MATLAB if/else
features = ['temperature', 'ph_level', 'turbidity', 'temp_delta', 'ph_delta', 'turb_delta']
print("\n--- COPY THE MATLAB CODE BELOW ---\n")
export_tree_to_matlab(model, features)