from functools import wraps

import connexion
import jwt
from consul import Consul, Check
from flask import request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

JWT_SECRET = 'MY JWT SECRET'
JWT_LIFETIME_SECONDS = 600000

# Adding MS to consul

consul_port = 8500
service_name = "order"
service_port = 5005


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


def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])


def create_order(order_body):
    username = order_body['username']
    shopping_cart = order_body['shopping_cart']
    number_products = order_body['number_products']
    total_price = order_body['total_price']
    new_order = Order(username=username, shopping_cart=shopping_cart, number_products=number_products,
                      total_price=total_price)

    db.session.add(new_order)
    db.session.commit()
    return order_schema.dump(new_order)


# @has_role(["shopping_cart", "payment"])
def get_order_details(order_id):
    existing_order = db.session.query(Order).filter_by(id=order_id).first()
    if existing_order:
        return order_schema.dump(existing_order)
    else:
        return {'error': 'Order not found'}, 404


# @has_role(["shopping_cart", "payment"])
def get_user_orders(username):
    orders = db.session.query(Order).filter_by(username=username)
    return order_schema.dump(orders, many=True)


# @has_role(["shopping_cart", "payment"])
def get_orders_shopping_cart(shopping_cart):
    orders = db.session.query(Order).filter_by(shopping_cart=shopping_cart)
    return order_schema.dump(orders, many=True)


def get_all_orders():
    orders = db.session.query(Order).all()
    return order_schema.dump(orders, many=True)


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")

from models import Order, OrderSchema

order_schema = OrderSchema()
# register_to_consul()

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5005, debug=True)
