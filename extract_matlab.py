import joblib
from sklearn.tree import _tree

def export_to_matlab(model_path, output_file):
    # Load the model
    model = joblib.load(model_path)
    tree_ = model.tree_
    
    # The 6 features in strict order
    feature_names = ['temp', 'ph', 'turb', 'temp_delta', 'ph_delta', 'turb_delta']
    
    with open(output_file, "w") as f:
        # Write the MATLAB function header
        f.write("function is_safe = evaluate_water(temp, ph, turb, temp_delta, ph_delta, turb_delta)\n")
        f.write("    % Auto-generated ML Decision Tree Logic\n\n")
        
        def recurse(node, depth):
            indent = "    " * depth
            
            # If the node is not a leaf, it has a decision rule
            if tree_.feature[node] != _tree.TREE_UNDEFINED:
                name = feature_names[tree_.feature[node]]
                threshold = tree_.threshold[node]
                
                f.write(f"{indent}if {name} <= {threshold:.4f}\n")
                recurse(tree_.children_left[node], depth + 1)
                f.write(f"{indent}else\n")
                recurse(tree_.children_right[node], depth + 1)
                f.write(f"{indent}end\n")
            else:
                # If the node is a leaf, it outputs the prediction (0 or 1)
                value = tree_.value[node][0]
                # Determine which class has the majority vote
                prediction = 0 if value[0] > value[1] else 1
                f.write(f"{indent}is_safe = {prediction};\n")

        # Start the recursion from the root node (0) at depth 1
        recurse(0, 1)
        
        f.write("end\n")
    
    print(f"Success! MATLAB logic written to {output_file}")

# Run the generator
export_to_matlab('aquaculture_model_v2.pkl', 'evaluate_water.m')