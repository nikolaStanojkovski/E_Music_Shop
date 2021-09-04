from functools import wraps

import connexion
from flask import request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import jwt
import time
from flask_bcrypt import Bcrypt
from consul import Consul, Check

JWT_SECRET = 'MY JWT SECRET'
JWT_LIFETIME_SECONDS = 600000

SHOPPING_CART_APIKEY = 'SHOPPING CART MS SECRET'
RESERVATIONS_APIKEY = 'RESERVATIONS MS SECRET'
PAYMENT_APIKEY = 'PAYMENT MS SECRET'
INVENTORY_APIKEY = 'INVENTORY MS SECRET'

# Adding MS to consul

consul_port = 8500
service_name = "user"
service_port = 5001


def register_to_consul():
    consul = Consul(host='consul', port=consul_port)

    agent = consul.agent

    service = agent.service

    check = Check.http(f"http://{service_name}:{service_port}/api/ui", interval="10s", timeout="5s", deregister="1s")

    service.register(service_name, service_id=service_name, port=service_port, check=check)


def get_service(service_id):
    consul = Consul(host="consul", port=consul_port)

    agent = consul.agent

    service_list = agent.services()

    service_info = service_list[service_id]


def has_role(arg):
    def has_role_inner(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            try:
                headers = request.headers
                if headers.environ['HTTP_AUTHORIZATION']:
                    token = headers.environ['HTTP_AUTHORIZATION'].split(' ')[1]
                    decoded_token = decode_token(token)
                    if 'admin' in decoded_token['roles']:
                        return fn(*args, **kwargs)
                    for role in arg:
                        if role in decoded_token['roles']:
                            return fn(*args, **kwargs)
                    abort(401)
                return fn(*args, **kwargs)
            except Exception as e:
                abort(401)

        return decorated_view

    return has_role_inner


def auth(auth_body):
    timestamp = int(time.time())
    found_user = db.session.query(User).filter_by(username=auth_body['username']).first()
    if not bcrypt.check_password_hash(found_user.password, auth_body['password']):
        return {'error': 'Passwords does not match!'}, 401
    user_id = found_user.id
    roles = []
    if found_user.is_admin:
        roles.append("admin")
    else:
        roles.append("basic_user")
    payload = {
        "iss": 'User Microservice',
        "iat": int(timestamp),
        "exp": int(timestamp + JWT_LIFETIME_SECONDS),
        "sub": user_id,
        "roles": roles,
        "user-details": user_schema.dump(found_user)
    }
    encoded = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return encoded


def auth_microservice(auth_body_microservice):
    apikey = auth_body_microservice['apikey']
    roles = []
    if apikey == INVENTORY_APIKEY:
        roles.append("catalog")
        sub = 'catalog'
    elif apikey == PAYMENT_APIKEY:
        roles.append("payment")
        sub = 'payment'
    elif apikey == SHOPPING_CART_APIKEY:
        roles.append("shopping_cart")
        sub = 'shopping_cart'
    elif apikey == RESERVATIONS_APIKEY:
        roles.append("order")
        sub = 'order'

    timestamp = int(time.time())
    payload = {
        "iss": 'E Music Shop',
        "iat": int(timestamp),
        "exp": int(timestamp + JWT_LIFETIME_SECONDS),
        "sub": sub,
        "roles": roles
    }
    encoded = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return encoded


def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])


def register_user(user_register_body):
    found_user = db.session.query(User).filter_by(username=user_register_body['username']).first()
    if found_user:
        return {'error': 'User with username: {}, already exists!'.format(user_register_body['username'])}, 409
    else:
        if user_register_body['password'] == user_register_body['confirm_password']:
            username = user_register_body['username']
            email = user_register_body['email']
            name = user_register_body['name']
            surname = user_register_body['surname']
            is_admin = True if user_register_body['is_admin'] == 1 else False
            password = bcrypt.generate_password_hash(password=user_register_body['password'], rounds=10)
            new_user = User(username=username, password=password, email=email, name=name, surname=surname, is_admin=is_admin)
            db.session.add(new_user)
            db.session.commit()
            return user_schema.dump(new_user)
        else:
            return {'error': 'Passwords does not match!'}, 404


@has_role(["shopping_cart", "payments"])
def get_user_details(username):
    found_user = db.session.query(User).filter_by(username=username).first()
    if found_user:
        return user_schema.dump(found_user)
    else:
        return {'error': 'User not found'}, 404


@has_role(["admin"])
def delete_user(user_id):
    db.session.query(User).filter_by(id=user_id).delete()
    db.session.commit()
    return {'Response': 'User with id: {} has been deleted'.format(user_id)}, 200


def get_all_users():
    users = db.session.query(User).all()
    return user_schema.dump(users, many=True)


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")

from models import User, UserSchema

user_schema = UserSchema(exclude=['password'])
bcrypt = Bcrypt(app)
# register_to_consul()

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5001, debug=True)
