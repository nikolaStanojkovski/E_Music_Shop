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

# Adding MS to consul

consul_port = 8500
service_name = "catalog"
service_port = 5002


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


# Song methods


@has_role(["admin"])
def create_song(song_body):
    existing_song = db.session.query(Song).filter_by(name=song_body['name']).first()
    if existing_song:
        return {'error': 'Song with name {} already exists!'.format(song_body['name'])}, 404
    artist = song_body['artist']
    name = song_body['name']
    length = song_body['length']
    publish_date = datetime.now()
    copies = song_body['copies']
    available = False
    if copies != 0:
        available = True
    price = song_body['price']

    new_song = Song(artist=artist, name=name, length=length, publish_date=publish_date, copies=copies,
                    available=available, price=price)
    db.session.add(new_song)
    db.session.commit()

    return song_schema.dump(new_song)


@has_role(["shopping_cart"])
def get_song(request_body_song):
    existing_song = db.session.query(Song).filter_by(name=request_body_song['song_name']).first()
    if existing_song:
        return song_schema.dump(existing_song)
    else:
        return {'error': 'Song with name: {} was not found!'.format(request_body_song['song_name'])}, 404


@has_role(["admin"])
def update_song(song_name, song_update):
    existing_song = db.session.query(Song).get(song_name)
    if not existing_song:
        return {'error': 'Song with id: {} was not found!'.format(song_name)}, 404
    existing_song.copies = song_update['copies']
    existing_song.available = song_update['available']
    existing_song.price = song_update['price']

    db.session.commit()
    existing_song = db.session.query(Song).get(song_name)
    return song_schema.dump(existing_song)


def get_all_songs():
    songs = db.session.query(Song).all()
    return song_schema.dump(songs, many=True)


@has_role(["shopping_cart"])
def buy_song(song_name, song_copies):
    song = db.session.query(Song).filter_by(name=song_name).first()
    if song.available:
        if song.copies - song_copies['no_copies'] >= 0:
            song.copies -= song_copies['no_copies']
            if song.copies == 0:
                song.available = False
            db.session.commit()
            return album_schema.dump(song)
        else:
            return {'error': 'Not available copies!'}, 404
    else:
        return {'error': 'Song is currently not available'}, 404


# Album methods


@has_role(["admin"])
def create_album(album_body):
    existing_album = db.session.query(Album).filter_by(name=album_body['name']).first()
    if existing_album:
        return {'error': 'Album with name {} already exists!'.format(album_body['name'])}, 404
    artist = album_body['artist']
    name = album_body['name']
    length = album_body['length']
    number_songs = album_body['no_songs']
    publish_date = datetime.now()
    copies = album_body['copies']
    available = False
    if copies != 0:
        available = True
    price = album_body['price']

    new_album = Album(artist=artist, name=name, length=length, number_songs=number_songs, publish_date=publish_date,
                      copies=copies,
                      available=available, price=price)
    db.session.add(new_album)
    db.session.commit()

    return album_schema.dump(new_album)


@has_role(["shopping_cart"])
def get_album(request_body_album):
    existing_album = db.session.query(Album).filter_by(name=request_body_album['album_name']).first()
    if existing_album:
        return album_schema.dump(existing_album)
    else:
        return {'error': 'Album with name: {} was not found!'.format(request_body_album['album_name'])}, 404


@has_role(["admin"])
def update_album(album_id, album_update):
    existing_album = db.session.query(Album).get(album_id)
    if not existing_album:
        return {'error': 'Album with id: {} was not found!'.format(album_id)}, 404
    existing_album.copies = album_update['copies']
    existing_album.available = album_update['available']
    existing_album.price = album_update['price']

    db.session.commit()
    existing_album = db.session.query(Album).get(album_id)
    return album_schema.dump(existing_album)


def get_all_albums():
    albums = db.session.query(Album).all()
    return album_schema.dump(albums, many=True)


@has_role(["shopping_cart"])
def buy_album(album_name, album_copies):
    album = db.session.query(Album).filter_by(name=album_name).first()
    if album.available:
        if album.copies - album_copies['no_copies'] >= 0:
            album.copies -= album_copies['no_copies']
            if album.copies == 0:
                album.available = False
            db.session.commit()
            return album_schema.dump(album)
        else:
            return {'error': 'Not available copies!'}, 404
    else:
        return {'error': 'Album is currently not available'}, 404


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")

from models import Album, AlbumSchema, Song, SongSchema

album_schema = AlbumSchema()
song_schema = SongSchema()

register_to_consul()

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5002, debug=True)
