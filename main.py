# Import necessary modules and packages
from flask import Flask, jsonify, request, abort, url_for, render_template, redirect
from models import UserModel, TokenModel, PersonModel  # Import your model classes
from utils import generate_token  # Import a utility function
from functools import wraps  # Import a decorator for token verification
from decimal import Decimal  # Import Decimal for precise floating-point arithmetic
import os  # Import the 'os' module for working with environment variables

# Create a Flask web application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # Set a secret key for session security

# Helper function to make person data HATEOAS compliant
def make_public_person(person):
    new_person = {}
    for field in ['id', 'name', 'address', 'phone_number', 'personnummer', 'account_balance']:
        if hasattr(person, field):
            new_person[field] = getattr(person, field)
    new_person['uri'] = url_for('get_person', person_id=person.id, _external=True)
    new_person['links'] = [
        {"rel": "self", "href": new_person['uri']},
        {"rel": "update", "href": new_person['uri'], "method": "PUT"},
        {"rel": "delete", "href": new_person['uri'], "method": "DELETE"}
    ]
    return new_person

# Token verification decorator
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            abort(401, description="Token is missing!")  # Unauthorized if token is missing
        if not TokenModel.verify_token(token):
            abort(401, description="Invalid or expired token.")  # Unauthorized if token is invalid
        return f(*args, **kwargs)
    return decorated_function

# Route for the home page
@app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def home():
    return render_template('home.html')  # Render the home page using a template

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')  # Render the registration form
    elif request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'message': 'Missing username or password'}), 400  # Bad Request if missing data

        UserModel.create_user(username, password)
        return redirect(url_for('login'))  # Redirect to the login page after successful registration

# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')  # Render the login form
    elif request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'message': 'Missing username or password'}), 400  # Bad Request if missing data

        if UserModel.verify_user(username, password):
            token = generate_token()  # Generate a token for the authenticated user
            return jsonify({'token': token}), 200  # Return the token in JSON format

        return jsonify({'message': 'Invalid credentials'}), 401  # Unauthorized if login is unsuccessful

# CRUD operations for persons
@app.route('/persons', methods=['GET'])
@token_required  # Decorate the route to require a valid token
def get_persons():
    persons = PersonModel.get_all_persons()  # Retrieve all persons from the database
    return jsonify([make_public_person(person) for person in persons])  # Return persons in JSON format

@app.route('/persons/<int:person_id>', methods=['GET'])
@token_required  # Decorate the route to require a valid token
def get_person(person_id):
    person = PersonModel.get_person_by_id(person_id)  # Retrieve a person by their ID
    if person is None:
        abort(404)  # Not Found if the person does not exist
    return jsonify(make_public_person(person))  # Return the person in JSON format

@app.route('/persons', methods=['POST'])
@token_required  # Decorate the route to require a valid token
def create_person():
    data = request.get_json()
    required_fields = ['id', 'name', 'address', 'phone_number', 'personnummer', 'account_balance']

    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Missing data'}), 400  # Bad Request if missing required data

    # Convert 'id' to int and 'account_balance' to Decimal
    data['id'] = int(data['id'])
    data['account_balance'] = Decimal(data['account_balance'])

    PersonModel.create_person(**data)  # Create a new person with the provided data
    return jsonify({'message': 'Person created successfully'}), 201  # Created

@app.route('/persons/<int:person_id>', methods=['PUT'])
@token_required  # Decorate the route to require a valid token
def update_person(person_id):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400  # Bad Request if no data is provided

    # Check if the person exists
    if not PersonModel.get_person_by_id(person_id):
        return jsonify({'message': 'Person not found'}), 404  # Not Found if the person does not exist

    # Exclude 'id' from the data dictionary if it's present
    data.pop('id', None)
    # Convert 'account_balance' to Decimal
    data['account_balance'] = Decimal(data['account_balance'])

    # Call the update method with the converted data
    PersonModel.update_person(person_id, **data)
    return jsonify({'message': 'Person updated successfully'}), 200  # OK

@app.route('/persons/<int:person_id>', methods=['DELETE'])
@token_required  # Decorate the route to require a valid token
def delete_person(person_id):
    if not PersonModel.get_person_by_id(person_id):
        return jsonify({'message': 'Person not found'}), 404  # Not Found if the person does not exist

    PersonModel.delete_person(person_id)  # Delete the person from the database
    return jsonify({'message': 'Person deleted successfully'}), 200  # OK

# Run the Flask app if this script is the main module
if __name__ == '__main__':
    app.run(debug=True)

