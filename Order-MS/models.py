from app import db
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    shopping_cart = db.Column(db.Integer, nullable=False)
    number_products = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)


class OrderSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        load_instance = True
