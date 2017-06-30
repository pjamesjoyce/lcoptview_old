from app import app
import os

if not os.environ.get('OPENSHIFT_HOMEDIR'):
    
    print(app.config['SQLALCHEMY_DATABASE_URI'])
    print('running locally')
    from app.models import *
    db.create_all()


if __name__ == "__main__":
    app.run(debug = True)
