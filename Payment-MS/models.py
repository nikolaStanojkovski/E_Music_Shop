from app import db
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_money = db.Column(db.String, nullable=False)


class PaymentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Payment
        load_instance = True