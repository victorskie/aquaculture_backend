import joblib
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

# 1. Load the retrained AI model
print("Loading aquaculture_model_v2.pkl...")
model = joblib.load('aquaculture_model_v2.pkl')

# 2. Define the input shape and data type
# The model expects exactly 6 floating-point features: 
# [temperature, ph_level, turbidity, temp_delta, ph_delta, turb_delta]
# 'None' allows it to process any number of sensor readings at once.
initial_type = [('float_input', FloatTensorType([None, 6]))]

# 3. Convert the scikit-learn model to ONNX format
print("Converting to ONNX format...")
onnx_model = convert_sklearn(model, initial_types=initial_type)

# 4. Save the new ONNX file
with open("aquaculture_model_v2.onnx", "wb") as f:
    f.write(onnx_model.SerializeToString())

print("Success! aquaculture_model_v2.onnx has been generated.")