from app import db
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class ShoppingCart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, nullable=True)
    number_products = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    username = db.Column(db.String, nullable=False)


class ShoppingCartSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ShoppingCart
        load_instance = True