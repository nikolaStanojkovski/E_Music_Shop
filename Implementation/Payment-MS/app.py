from datetime import datetime
from functools import wraps

import connexion
import jwt
from consul import Consul, Check
from flask import request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

JWT_SECRET = 'MY JWT SECRET'
JWT_LIFETIME_SECONDS = 600000
PAYMENT_APIKEY = 'PAYMENT MS SECRET'

# Adding MS to consul

consul_port = 8500
service_name = "payment"
service_port = 5004


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


def calculateTotalMoney(money_to_pay):
    initial_price = money_to_pay
    transaction_fee = 5.0
    # payment fee is 10% from the initial price
    payment_fee = initial_price * 0.1

    return initial_price + transaction_fee + payment_fee


@has_role(["shopping_cart"])
def make_payment(payment_body):
    date_payment = datetime.now()
    quantity = payment_body['quantity']
    total_money = calculateTotalMoney(payment_body['money'])

    payment = Payment(username=payment_body['username'], shopping_cart=payment_body['shopping_cart'],
                      date=date_payment, quantity=quantity, total_money=total_money)

    db.session.add(payment)
    db.session.commit()
    return payment_schema.dump(payment)


def get_all_payments():
    payments = db.session.query(Payment).all()
    return payment_schema.dump(payments, many=True)


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")

from models import Payment, PaymentSchema

payment_schema = PaymentSchema()

register_to_consul()

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5004, debug=True)
