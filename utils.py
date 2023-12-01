import uuid
from datetime import datetime, timedelta
from models import TokenModel

def generate_token():
    jwt = str(uuid.uuid4())  # Generate a unique token
    expiry_date = datetime.utcnow() + timedelta(days=2)  # Set token expiry to 10 days from now
    TokenModel.create_token(jwt, expiry_date)
    return jwt