from flask import Flask, request, jsonify
from ml_model import load_model, predict_traffic

app = Flask(__name__)

# Load the trained model
model = load_model()

@app.route("/predict", methods=["POST"])
def predict():
    """
    API endpoint to predict traffic classification.

    Request JSON format:
        {
            "latency": float,
            "throughput": float,
            "packet_loss": float,
            "jitter": float,
            "traffic_volume": float
        }

    Response JSON format:
        {
            "prediction": "NORMAL" | "CRITICAL" | "SECURE"
        }
    """
    data = request.get_json()
    features = [
        data.get("latency"),
        data.get("throughput"),
        data.get("packet_loss"),
        data.get("jitter"),
        data.get("traffic_volume")
    ]

    prediction = predict_traffic(model, features)
    return jsonify({"prediction": prediction})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)