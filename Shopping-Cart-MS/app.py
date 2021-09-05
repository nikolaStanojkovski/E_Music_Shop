from functools import wraps

import connexion
import jwt
import requests
from consul import Consul, Check
from flask import request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

JWT_SECRET = 'MY JWT SECRET'
SHOPPING_CART_APIKEY = 'SHOPPING CART MS SECRET'

# Adding MS to consul

consul_port = 8500
service_name = "shopping_cart"
service_port = 5003


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

    return service_info['Address'], service_info['Port']


def get_service_url(service_name):
    address, port = get_service(service_name)

    url = "{}:{}".format(address, port)

    if not url.startswith("http"):
        url = "http://{}".format(url)

    return url


def has_role(arg):
    def has_role_inner(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            try:
                headers = request.headers
                if headers.environ['HTTP_AUTHORIZATION']:
                    token = headers.environ['HTTP_AUTHORIZATION']
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


def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])


# CRUD Operations

def get_all_shopping_carts():
    shopping_carts = db.session.query(ShoppingCart).all()
    return shopping_cart_schema.dump(shopping_carts, many=True)


def create_shopping_cart(shopping_cart_body):
    body = {
        'username': shopping_cart_body['username'],
        'password': shopping_cart_body['password']
    }
    jwt_token = requests.post(url='http://localhost:5001/api/auth',
                              json=body)

    if jwt_token:
        new_sc = ShoppingCart(order_id=None, username=shopping_cart_body['username'],
                              number_products=0, total_price=0)
        db.session.add(new_sc)
        db.session.commit()

        return shopping_cart_schema.dump(new_sc)
    else:
        return {'error': 'Incorrect username or password'}, 404


def get_shopping_cart(shopping_cart_id):
    existing_sc = db.session.query(ShoppingCart).filter_by(id=shopping_cart_id).first()
    if existing_sc:
        return shopping_cart_schema.dump(existing_sc)
    else:
        return {'error': 'Shopping cart with id: {} was not found!'.format(shopping_cart_id)}, 404


# Other operations

def create_new_song(song_body):
    body = {
        'username': song_body['username'],
        'password': song_body['password']
    }
    jwt_token = requests.post(url='http://localhost:5001/api/auth',
                              json=body)

    if jwt_token:
        auth_value = "Bearer {}".format(jwt_token.json())
        AUTH_HEADER = {"AUTHORIZATION": auth_value}
        body = {
            'artist': song_body['artist'],
            'name': song_body['name'],
            'length': song_body['length'],
            'copies': song_body['copies'],
            'price': song_body['price']
        }

        response = requests.post(url='http://localhost:5002/api/song/add',
                                 headers=AUTH_HEADER,
                                 json=body)

        if response.status_code == 200:
            return {'success': 'Successfully added song!'}, 200
        else:
            return {'error': 'Unauthorized access! You must an admin to create a new song'}, 404
    else:
        return {'error': 'Incorrect username or password'}, 404


def create_new_album(album_body):
    body = {
        'username': album_body['username'],
        'password': album_body['password']
    }
    jwt_token = requests.post(url='http://localhost:5001/api/auth',
                              json=body)

    if jwt_token:
        auth_value = "Bearer {}".format(jwt_token.json())
        AUTH_HEADER = {"AUTHORIZATION": auth_value}
        body = {
            'artist': album_body['artist'],
            'name': album_body['name'],
            'length': album_body['length'],
            'no_songs': album_body['no_songs'],
            'copies': album_body['copies'],
            'price': album_body['price']
        }

        response = requests.post(url='http://localhost:5002/api/album/add',
                                 headers=AUTH_HEADER,
                                 json=body)

        if response.status_code == 200:
            return {'success': 'Successfully added album!'}, 200
        else:
            return {'error': 'Unauthorized access! You must an admin to create a new album'}, 404
    else:
        return {'error': 'Unauthorized access! Incorrect username or password'}, 404


def add_song_to_shopping_cart(shopping_cart_song):
    body = {
        'username': shopping_cart_song['username'],
        'password': shopping_cart_song['password']
    }
    jwt_token = requests.post(url='http://localhost:5001/api/auth',
                              json=body)

    if jwt_token:
        auth_value = "Bearer {}".format(jwt_token.json())
        AUTH_HEADER = {"AUTHORIZATION": auth_value}
        body = {
            'no_copies': shopping_cart_song['no_copies']
        }

        response = requests.post(url='http://localhost:5002/api/song/{}/buy'.format(shopping_cart_song['name']),
                                 headers=AUTH_HEADER,
                                 json=body)

        if response.status_code == 200:
            existing_shopping_cart = db.session.query(ShoppingCart).filter_by(
                id=shopping_cart_song['shopping_cart_id']).first()
            existing_shopping_cart.number_products = existing_shopping_cart.number_products + shopping_cart_song[
                'no_copies']
            price = response.json()['price']
            existing_shopping_cart.total_price = existing_shopping_cart.total_price + (
                    shopping_cart_song['no_copies'] * price)

            db.session.commit()
            return {'success': 'Successfully added song to shopping cart!'}, 200
        else:
            return {'error': 'Unauthorized access when trying to buy a song!'}, 404
    else:
        return {'error': 'Unauthorized access! Incorrect username or password'}, 404


def add_album_to_shopping_cart(shopping_cart_album):
    body = {
        'username': shopping_cart_album['username'],
        'password': shopping_cart_album['password']
    }
    jwt_token = requests.post(url='http://localhost:5001/api/auth',
                              json=body)

    if jwt_token:
        auth_value = "Bearer {}".format(jwt_token.json())
        AUTH_HEADER = {"AUTHORIZATION": auth_value}
        body = {
            'no_copies': shopping_cart_album['no_copies']
        }

        response = requests.post(url='http://localhost:5002/api/album/{}/buy'.format(shopping_cart_album['name']),
                                 headers=AUTH_HEADER,
                                 json=body)

        if response.status_code == 200:
            existing_shopping_cart = db.session.query(ShoppingCart).filter_by(
                id=shopping_cart_album['shopping_cart_id']).first()
            existing_shopping_cart.number_products = existing_shopping_cart.number_products + shopping_cart_album[
                'no_copies']
            price = response.json()['price']
            existing_shopping_cart.total_price = existing_shopping_cart.total_price + (
                    shopping_cart_album['no_copies'] * price)

            db.session.commit()
            return {'success': 'Successfully added album to shopping cart!'}, 200
        else:
            return {'error': 'Unauthorized access when trying to buy an album!'}, 404
    else:
        return {'error': 'Unauthorized access! Incorrect username or password'}, 404


def make_order(create_order_body):
    body = {
        'username': create_order_body['username'],
        'password': create_order_body['password']
    }
    jwt_token = requests.post(url='http://localhost:5001/api/auth',
                              json=body)

    if jwt_token:
        auth_value = "Bearer {}".format(jwt_token.json())
        AUTH_HEADER = {"AUTHORIZATION": auth_value}

        existing_shopping_cart = db.session.query(ShoppingCart).filter_by(
            id=create_order_body['shopping_cart_id']).first()

        payment_body = {
            'shopping_cart': existing_shopping_cart.id,
            'username': create_order_body['username'],
            'quantity': existing_shopping_cart.number_products,
            'money': existing_shopping_cart.total_price,
        }

        payment_response = requests.post(url='http://localhost:5004/api/make_payment/',
                                         headers=AUTH_HEADER,
                                         json=payment_body)

        if payment_response.status_code == 200:

            order_body = {
                'shopping_cart': existing_shopping_cart.id,
                'username': create_order_body['username'],
                'number_products': existing_shopping_cart.number_products,
                'total_price': existing_shopping_cart.total_price,
            }

            order_response = requests.post(url='http://localhost:5005/api/order/add',
                                           headers=AUTH_HEADER,
                                           json=order_body)

            if order_response.status_code == 200:
                # Delete the shopping cart with which the payment and order was made
                db.session.query(ShoppingCart).filter_by(id=existing_shopping_cart.id).delete()
                db.session.commit()

                return {'success': 'Successfully made a payment and made a new order!'}, 200
            else:
                return {'error': 'There was an error creating an order'}, 404
        else:
            return {'error': 'There was an error making a payment'}, 404
    else:
        return {'error': 'Unauthorized access! Incorrect username or password'}, 404


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")

from models import ShoppingCart, ShoppingCartSchema

shopping_cart_schema = ShoppingCartSchema()
# register_to_consul()
if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5003, debug=True)
