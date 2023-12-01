# Import necessary libraries and modules
from cassandra.cluster import Cluster
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
from cassandra.auth import PlainTextAuthProvider
import datetime
import os
from ssl import SSLContext, PROTOCOL_TLSv1_2, CERT_REQUIRED
from cassandra import ConsistencyLevel
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Configure SSL/TLS for secure connection
ssl_context = SSLContext(PROTOCOL_TLSv1_2)
ssl_context.load_verify_locations('certs/sf-class2-root.crt')  # Path to the Amazon Root CA certificate
ssl_context.verify_mode = CERT_REQUIRED

# Get credentials from environment variables
auth_provider = PlainTextAuthProvider(
    username=os.getenv('AMAZON_KEYSPACE_USERNAME'),
    password=os.getenv('AMAZON_KEYSPACE_PASSWORD')
)

# Cluster configuration for Cassandra
cluster = Cluster(
    contact_points=['cassandra.eu-north-1.amazonaws.com'],  # Replace with your specific endpoint
    ssl_context=ssl_context,
    auth_provider=auth_provider,
    port=9142
)

# Connect to the Cassandra session
session = cluster.connect("task4")

# Set default consistency level for Cassandra queries
session.default_consistency_level = ConsistencyLevel.LOCAL_QUORUM

# Define a class for managing user-related operations
class UserModel:
    @staticmethod
    def create_user(username, password):
        # Generate a hashed password using Werkzeug's security functions
        hashed_password = generate_password_hash(password)
        # Create a query to insert the user data into the Cassandra 'users' table
        query = "INSERT INTO users (username, hashed_password) VALUES (%s, %s)"
        session.execute(query, (username, hashed_password))

    @staticmethod
    def verify_user(username, password):
        # Query to retrieve the hashed password for a given username
        query = "SELECT hashed_password FROM users WHERE username = %s"
        user = session.execute(query, (username,)).one()
        if user:
            # Check if the provided password matches the stored hashed password
            return check_password_hash(user.hashed_password, password)
        return False

# Define a class for managing JWT token operations
class TokenModel:
    @staticmethod
    def create_token(jwt, expiry_date):
        # Create a query to insert a JWT token and its expiry date into the 'jwt' table
        query = "INSERT INTO jwt (jwt, expiry_date) VALUES (%s, %s)"
        session.execute(query, (jwt, expiry_date))
        
    @staticmethod
    def verify_token(auth_header):
        # Split the authorization header to extract the JWT token
        parts = auth_header.split()
        if parts[0].lower() == 'bearer' and len(parts) == 2:
            jwt = parts[1]
        else:
            jwt = auth_header.strip()  # In case the token is sent without 'Bearer'

        # Query to check if the token exists and is not expired
        query = "SELECT expiry_date FROM jwt WHERE jwt = %s"
        try:
            result = session.execute(query, (jwt,)).one()
            if result:
                if result.expiry_date > datetime.datetime.utcnow():
                    return True
                else:
                    print("Token expired")
            else:
                print("Token not found in the database")
        except Exception as e:
            print(f"Error verifying token: {e}")
        return False

# Define a class for managing person-related operations
class PersonModel:
    @staticmethod
    def generate_checksum(data):
        # Generate a checksum value based on sorted data keys
        data_string = ''.join(str(data[key]) for key in sorted(data))
        return hashlib.sha256(data_string.encode()).hexdigest()

    @staticmethod
    def create_person(id, name, address, phone_number, personnummer, account_balance):
        # Generate a checksum for the person's data
        checksum = PersonModel.generate_checksum({
            'id': id,
            'name': name,
            'address': address,
            'phone_number': phone_number,
            'personnummer': personnummer,
            'account_balance': account_balance
        })
        
        # Construct a query to insert person data into the 'persons' table
        query = """
        INSERT INTO persons (id, name, address, phone_number, personnummer, account_balance, checksum)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        session.execute(query, (id, name, address, phone_number, personnummer, account_balance, checksum))

    @staticmethod
    def get_all_persons():
        # Query to retrieve all persons from the 'persons' table
        query = "SELECT * FROM persons"
        return list(session.execute(query))

    @staticmethod
    def get_person_by_id(id):
        # Query to retrieve a person by their ID
        query = "SELECT * FROM persons WHERE id = %s"
        person = session.execute(query, (id,)).one()
        if person:
            # Verify data integrity by comparing the checksum
            person_data = {'id': person.id, 'name': person.name, 'address': person.address,
                           'phone_number': person.phone_number, 'personnummer': person.personnummer,
                           'account_balance': person.account_balance}
            checksum = PersonModel.generate_checksum(person_data)
            if checksum != person.checksum:
                raise ValueError("Data integrity check failed")
        return person

    @staticmethod
    def update_person(id, name, address, phone_number, personnummer, account_balance):
        # Generate a checksum for the updated person data
        person_data = {'id': id, 'name': name, 'address': address,
                       'phone_number': phone_number, 'personnummer': personnummer,
                       'account_balance': account_balance}
        checksum = PersonModel.generate_checksum(person_data)
        # Query to update person data in the 'persons' table
        query = """
        UPDATE persons SET name = %s, address = %s, phone_number = %s, 
        personnummer = %s, account_balance = %s, checksum = %s WHERE id = %s
        """
        session.execute(query, (name, address, phone_number, personnummer, account_balance, checksum, id))

    @staticmethod
    def delete_person(id):
        # Query to delete a person by their ID
        query = "DELETE FROM persons WHERE id = %s"
        session.execute(query, (id,))
