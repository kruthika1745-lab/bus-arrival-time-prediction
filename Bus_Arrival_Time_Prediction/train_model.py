import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import joblib

# Load dataset
data = pd.read_csv("dataset.csv")

# Features and target
X = data[['Distance', 'Traffic', 'Weather', 'Speed']]
y = data['ArrivalTime']

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Save model
joblib.dump(model, "model/model.pkl")

print("Model trained successfully!") 
print("Model saved as model/model.pkl")