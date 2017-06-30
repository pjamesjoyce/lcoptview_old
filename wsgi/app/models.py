from flask_sqlalchemy import SQLAlchemy
from app import app

db = SQLAlchemy(app)


class ModelFile(db.Model):
    __tablename__ = 'modelfiles'
    id = db.Column('modelfile_id', db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    filepath = db.Column(db.String(255))

    def __init__(self, filename, filepath):
        self.filename = filename
        self.filepath = filepath
