from flask import Flask, jsonify, request, abort, url_for, render_template, redirect, request
from models import UserModel, TokenModel, PersonModel
from utils import generate_token
from functools import wraps
from decimal import Decimal

import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

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
            abort(401, description="Token is missing!")
        if not TokenModel.verify_token(token):
            abort(401, description="Invalid or expired token.")
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    elif request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'message': 'Missing username or password'}), 400

        UserModel.create_user(username, password)
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'message': 'Missing username or password'}), 400

        if UserModel.verify_user(username, password):
            token = generate_token()  # Token generation no longer requires user_id
            return jsonify({'token': token}), 200  # Return the token in JSON

        return jsonify({'message': 'Invalid credentials'}), 401

# CRUD operations for persons
@app.route('/persons', methods=['GET'])
@token_required
def get_persons():
    persons = PersonModel.get_all_persons()
    return jsonify([make_public_person(person) for person in persons])

@app.route('/persons/<int:person_id>', methods=['GET'])
@token_required
def get_person(person_id):
    person = PersonModel.get_person_by_id(person_id)
    if person is None:
        abort(404)
    return jsonify(make_public_person(person))

@app.route('/persons', methods=['POST'])
@token_required
def create_person():
    data = request.get_json()
    required_fields = ['id', 'name', 'address', 'phone_number', 'personnummer', 'account_balance']

    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Missing data'}), 400

    # Convert id to int and account_balance to Decimal
    data['id'] = int(data['id'])
    data['account_balance'] = Decimal(data['account_balance'])

    PersonModel.create_person(**data)
    return jsonify({'message': 'Person created successfully'}), 201



@app.route('/persons/<int:person_id>', methods=['PUT'])
@token_required
def update_person(person_id):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    # Check if the person exists
    if not PersonModel.get_person_by_id(person_id):
        return jsonify({'message': 'Person not found'}), 404

    # Exclude 'id' from the data dictionary if it's present
    data.pop('id', None)
    # Convert account_balance to Decimal
    data['account_balance'] = Decimal(data['account_balance'])

    # Call the update method with the converted data
    PersonModel.update_person(person_id, **data)
    return jsonify({'message': 'Person updated successfully'}), 200



@app.route('/persons/<int:person_id>', methods=['DELETE'])
@token_required
def delete_person(person_id):
    if not PersonModel.get_person_by_id(person_id):
        return jsonify({'message': 'Person not found'}), 404

    PersonModel.delete_person(person_id)
    return jsonify({'message': 'Person deleted successfully'}), 200


if __name__ == '__main__':
    app.run(debug=True)
