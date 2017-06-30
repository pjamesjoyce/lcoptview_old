from flask import Flask  
app = Flask(__name__)
app.config.from_pyfile('app.cfg')


def uc_first(string):
    return string[0].upper() + string[1:]


app.jinja_env.filters['uc_first'] = uc_first  

from app import views
