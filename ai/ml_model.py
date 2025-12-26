import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

def train_model(data, labels):
    """
    Train a RandomForestClassifier model.

    Parameters:
        data (numpy.ndarray): Feature matrix.
        labels (numpy.ndarray): Target labels.

    Returns:
        model: Trained RandomForestClassifier model.
    """
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(data, labels)
    return model

def save_model(model, filename="traffic_model.pkl"):
    """Save the trained model to a file."""
    with open(filename, "wb") as f:
        pickle.dump(model, f)

def load_model(filename="traffic_model.pkl"):
    """Load a trained model from a file."""
    with open(filename, "rb") as f:
        return pickle.load(f)

def predict_traffic(model, features):
    """
    Predict traffic classification based on input features.

    Parameters:
        model: Trained model.
        features (list): List of input features [latency, throughput, packet_loss, jitter, traffic_volume].

    Returns:
        str: Predicted class (NORMAL, CRITICAL, SECURE).
    """
    prediction = model.predict([features])
    return prediction[0]