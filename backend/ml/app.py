from typing import List, Dict
from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import numpy as np
from PIL import Image
import pickle
from tensorflow.keras.models import load_model
from sklearn.preprocessing import StandardScaler

# Load environment variables
load_dotenv()
mongodb_uri = os.getenv("MONGODB_URI")
secret_key = os.getenv("SECRET_KEY")

print(f"MongoDB URI: {mongodb_uri}")  # just to check

# Flask app setup
app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MODEL_PKL_PATH = 'fake_medicine_detection_model.pkl'
MODEL_H5_PATH = 'fake_medicine_detection_model.h5'

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load models
try:
    with open(MODEL_PKL_PATH, 'rb') as f:
        model_components = pickle.load(f)
    scaler = model_components['scaler']
    classifier = model_components['classifier']
    
    keras_model = load_model(MODEL_H5_PATH)
    
    print("Models loaded successfully")
except Exception as e:
    print(f"Error loading models: {e}")
    raise e

# Helper functions
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_path: str, target_size=(224, 224)) -> np.ndarray:
    """Preprocess the image for model prediction"""
    try:
        img = Image.open(image_path).resize(target_size)
        img_array = np.array(img) / 255.0
        if len(img_array.shape) == 2:  # grayscale
            img_array = np.stack((img_array,)*3, axis=-1)
        img_array = np.expand_dims(img_array, axis=0)
        return img_array
    except Exception as e:
        print(f"Error preprocessing image: {e}")
        raise e

def extract_features(image_array: np.ndarray) -> np.ndarray:
    """Extract features from the image using the Keras model"""
    try:
        features = keras_model.predict(image_array)
        return features.flatten()
    except Exception as e:
        print(f"Error extracting features: {e}")
        raise e

# API route
@app.route('/api/analyze-medicine', methods=['POST'])
def analyze_medicine():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            temp_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(temp_path)
            
            processed_image = preprocess_image(temp_path)
            features = extract_features(processed_image)
            features_scaled = scaler.transform([features])
            
            prediction = classifier.predict(features_scaled)
            confidence = classifier.predict_proba(features_scaled).max()
            
            os.remove(temp_path)
            
            return jsonify({
                'isAuthentic': bool(prediction[0]),
                'confidence': float(confidence),
                'message': 'Analysis complete'
            })
        except Exception as e:
            print(f"Error during analysis: {e}")
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
