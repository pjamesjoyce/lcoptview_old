import os
from app import app
from flask import render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from .lcoptview import *

RUNNING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.environ.get('OPENSHIFT_DATA_DIR', os.path.join(RUNNING_DIRECTORY, 'data'))
ALLOWED_EXTENSIONS = set(['lcopt'])


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
@app.route('/index')
def index():
    #return "Hello, Flask World!"
    args = {}
    args['test'] = UPLOAD_FOLDER

    return render_template('test.html', args=args)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file', filename=filename))

    return render_template('upload.html')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return "you uploaded " + filename
    #return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
