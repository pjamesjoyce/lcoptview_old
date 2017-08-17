from flask_sqlalchemy import SQLAlchemy
from app import app
import hashlib

db = SQLAlchemy(app)


class ModelFile(db.Model):

    __tablename__ = 'models'

    id = db.Column('modelfile_id', db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    filepath = db.Column(db.String(255))
    link_id = db.Column(db.String(255))

    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    owner = db.relationship('User', backref='owner', lazy='select')

    description = db.Column(db.Text)
    name = db.Column(db.String(255))

    def __init__(self, filename, filepath, owner_id, description=None, name=None):
        self.filename = filename
        self.filepath = filepath
        to_hash = "{}{}".format(id, filename)
        self.link_id = hashlib.md5(to_hash.encode('utf-8')).hexdigest()

        # TODO: sort out the owner bit

        self.owner_id = owner_id

        if description is None:
            self.description = "This is where the description will go when I've set it up so that the user can put a description in when they upload a model"
        else:
            self.description = description

        if name is None:
            self.name = filename
        else:
            self.name = name

    def __repr__(self):
        return '<Model {}>'.format(self.filename)


class User(db.Model):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    username = db.Column(db.String)
    password = db.Column(db.String)
    authenticated = db.Column(db.Boolean, default=False)

    def is_active(self):
        return True

    def get_id(self):
        return self.id

    def is_authenticated(self):
        return self.authenticated

    def is_anonymous(self):
        return False
