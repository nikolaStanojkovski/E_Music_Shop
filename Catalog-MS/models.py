from app import db
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artist = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    length = db.Column(db.Integer, nullable=False)
    publish_date = db.Column(db.DateTime, nullable=False)
    copies = db.Column(db.Integer, nullable=False)
    available = db.Column(db.Boolean, nullable=False)
    price = db.Column(db.Float, nullable=False)


class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artist = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    length = db.Column(db.Integer, nullable=False)
    number_songs = db.Column(db.Integer, nullable=False)
    publish_date = db.Column(db.DateTime, nullable=False)
    copies = db.Column(db.Integer, nullable=False)
    available = db.Column(db.Boolean, nullable=False)
    price = db.Column(db.Float, nullable=False)


class SongSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Song
        load_instance = True


class AlbumSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Album
        load_instance = True
