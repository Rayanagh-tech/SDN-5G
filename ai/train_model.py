import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from ml_model import train_model, save_model

def generate_synthetic_data():
    """
    Generate synthetic data for training the model.

    Returns:
        tuple: Feature matrix and labels.
    """
    np.random.seed(42)
    num_samples = 1000

    # Features: latency, throughput, packet_loss, jitter, traffic_volume
    data = np.random.rand(num_samples, 5) * [100, 1000, 10, 50, 10000]

    # Labels: NORMAL, CRITICAL, SECURE
    labels = np.random.choice(["NORMAL", "CRITICAL", "SECURE"], size=num_samples)

    return data, labels

def main():
    # Generate synthetic data
    data, labels = generate_synthetic_data()

    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(data, labels, test_size=0.2, random_state=42)

    # Train the model
    model = train_model(X_train, y_train)

    # Evaluate the model
    y_pred = model.predict(X_test)
    print("Classification Report:")
    print(classification_report(y_test, y_pred))

    # Save the model
    save_model(model)

if __name__ == "__main__":
    main()