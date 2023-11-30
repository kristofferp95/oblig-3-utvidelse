from cassandra.cluster import Cluster
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import datetime

# Establishing a connection to Cassandra
cluster = Cluster(['127.0.0.1'])  # Add your Cassandra nodes here
session = cluster.connect('task4')

class UserModel:
    @staticmethod
    def create_user(username, password):
        hashed_password = generate_password_hash(password)
        query = "INSERT INTO users (username, hashed_password) VALUES (%s, %s)"
        session.execute(query, (username, hashed_password))

    @staticmethod
    def verify_user(username, password):
        query = "SELECT hashed_password FROM users WHERE username = %s"
        user = session.execute(query, (username,)).one()
        if user:
            return check_password_hash(user.hashed_password, password)
        return False

class TokenModel:
    @staticmethod
    def create_token(jwt, expiry_date):
        query = "INSERT INTO jwt (jwt, expiry_date) VALUES (%s, %s)"
        session.execute(query, (jwt, expiry_date))
        
    @staticmethod
    def verify_token(auth_header):
        # Split the header into parts and remove 'Bearer' if present
        parts = auth_header.split()
        if parts[0].lower() == 'bearer' and len(parts) == 2:
            jwt = parts[1]
        else:
            jwt = auth_header.strip()  # In case the token is sent without 'Bearer'

        query = "SELECT expiry_date FROM jwt WHERE jwt = %s"
        try:
            result = session.execute(query, (jwt,)).one()
            if result:
                if result.expiry_date > datetime.datetime.utcnow():
                    return True
                else:
                    print("Token expired")
            else:
                print("Token not found in database")
        except Exception as e:
            print(f"Error verifying token: {e}")
        return False

class PersonModel:
    @staticmethod
    def generate_checksum(data):
        data_string = ''.join(str(data[key]) for key in sorted(data))
        return hashlib.sha256(data_string.encode()).hexdigest()

    @staticmethod
    def create_person(id, name, address, phone_number, personnummer, account_balance):
        # Generate the checksum value based on your logic
        checksum = PersonModel.generate_checksum({
            'id': id,
            'name': name,
            'address': address,
            'phone_number': phone_number,
            'personnummer': personnummer,
            'account_balance': account_balance
        })
        
        # Construct the query with all necessary fields
        query = """
        INSERT INTO persons (id, name, address, phone_number, personnummer, account_balance, checksum)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        session.execute(query, (id, name, address, phone_number, personnummer, account_balance, checksum))

    @staticmethod
    def get_all_persons():
        query = "SELECT * FROM persons"
        return list(session.execute(query))

    @staticmethod
    def get_person_by_id(id):
        query = "SELECT * FROM persons WHERE id = %s"
        person = session.execute(query, (id,)).one()
        if person:
            person_data = {'id': person.id, 'name': person.name, 'address': person.address,
                           'phone_number': person.phone_number, 'personnummer': person.personnummer,
                           'account_balance': person.account_balance}
            checksum = PersonModel.generate_checksum(person_data)
            if checksum != person.checksum:
                raise ValueError("Data integrity check failed")
        return person

    @staticmethod
    def update_person(id, name, address, phone_number, personnummer, account_balance):
        person_data = {'id': id, 'name': name, 'address': address,
                       'phone_number': phone_number, 'personnummer': personnummer,
                       'account_balance': account_balance}
        checksum = PersonModel.generate_checksum(person_data)
        query = """
        UPDATE persons SET name = %s, address = %s, phone_number = %s, 
        personnummer = %s, account_balance = %s, checksum = %s WHERE id = %s
        """
        session.execute(query, (name, address, phone_number, personnummer, account_balance, checksum, id))

    @staticmethod
    def delete_person(id):
        query = "DELETE FROM persons WHERE id = %s"
        session.execute(query, (id,))
