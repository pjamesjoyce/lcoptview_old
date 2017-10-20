import os
from app import app
from flask import render_template, request, redirect, url_for, send_file, session, abort, flash
from werkzeug.utils import secure_filename
from .lcoptview import *
from .excel_functions import create_excel_method, create_excel_summary
from .parameters import parameter_sorting
from .models import *
from collections import OrderedDict
import json
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_bcrypt import Bcrypt
from .forms import LoginForm, RegistrationForm
from urllib.parse import urlparse, urljoin

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'

bcrypt = Bcrypt()

ALLOWED_EXTENSIONS = set(['lcoptview'])

#TEST_FILE = app.config['CURRENT_FILE']


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def load_viewfile(filename):
    return LcoptModelView(filename)


def get_sandbox_variables(filename):

    m = load_viewfile(filename)
    db = m.database['items']
    matrix = m.matrix
    
    def output_code(process_id):
        
        exchanges = m.database['items'][process_id]['exchanges']
        
        production_filter = lambda x: x['type'] == 'production'
           
        code = list(filter(production_filter, exchanges))[0]['input'][1]
        
        return code

    sandbox_positions = m.sandbox_positions

    products = OrderedDict((k, v) for k, v in db.items() if v['type'] == 'product')
    product_codes = [k[1] for k in products.keys()]

    processes = OrderedDict((k, v) for k, v in db.items() if v['type'] == 'process')
    process_codes = [k[1] for k in processes.keys()]
    process_name_map = {k[1]: v['name'] for k, v in processes.items()}

    # note this maps from output code to process
    process_output_map = {output_code(x): x[1] for x in processes.keys()}
    reverse_process_output_map = {value: key for key, value in process_output_map.items()}

    intermediates = {k: v for k, v in products.items() if v['lcopt_type'] == 'intermediate'}
    intermediate_codes = [k[1] for k in intermediates.keys()]
    intermediate_map = {k[1]: v['name'] for k, v in intermediates.items()}

    #process_output_name_map = {process_code: output_name for x in processes.keys()}
    process_output_name_map = {x[1]: intermediate_map[reverse_process_output_map[x[1]]] for x in processes.keys()}

    inputs = OrderedDict((k, v) for k, v in products.items() if v['lcopt_type'] == 'input')
    input_codes = [k[1] for k in inputs.keys()]
    input_map = {k[1]: v['name'] for k, v in inputs.items()}
    reverse_input_map = {value: key for key, value in input_map.items()}

    biosphere = OrderedDict((k, v) for k, v in products.items() if v['lcopt_type'] == 'biosphere')
    biosphere_codes = [k[1] for k in biosphere.keys()]
    biosphere_map = {k[1]: v['name'] for k, v in biosphere.items()}
    reverse_biosphere_map = {value: key for key, value in biosphere_map.items()}

    label_map = dict(input_map, **process_output_name_map)
    label_map = dict(label_map, **biosphere_map)
    #label_map = input_map.update(process_output_name_map)
    #label_map = label_map.update(biosphere_map)
    print (label_map)

    #print('label_map = {}\n'.format(label_map))
    
    outputlabels = [{'process_id': x, 'output_name': process_output_name_map[x]} for x in process_codes]
    
    link_indices = [process_output_map[x] if x in intermediate_codes else x for x in product_codes]
           
    if matrix is not None:
        # TODO: edit this to list of lists 
        row_totals = [sum(a) for a in matrix]
        input_row_totals = {k: row_totals[m.names.index(v)] for k, v in input_map.items()}
        biosphere_row_totals = {k: row_totals[m.names.index(v)] for k, v in biosphere_map.items()}
    
    # compute the nodes
    i = 1
    nodes = []
    for t in process_codes:
        nodes.append({'name': process_name_map[t], 'type': 'transformation', 'id': t, 'initX': i * 100, 'initY': i * 100})
        i += 1
    
    i = 1
    for p in input_codes:
        if input_row_totals[p] != 0:
            nodes.append({'name': input_map[p], 'type': 'input', 'id': p + "__0", 'initX': i * 50 + 150, 'initY': i * 50})
            i += 1

    i = 1
    for p in biosphere_codes:
        if biosphere_row_totals[p] != 0:
            nodes.append({'name': biosphere_map[p], 'type': 'biosphere', 'id': p + "__0", 'initX': i * 50 + 150, 'initY': i * 50})
            i += 1
   
    # compute links
    links = []
    
    input_duplicates = []
    biosphere_duplicates = []
    
    #check there is a matrix (new models won't have one until parameter_scan() is run)
    if matrix is not None:

        columns = list(map(list, zip(*matrix))) # transpose the matrix

        for c, column in enumerate(columns):
            for r, i in enumerate(column):
                if i > 0:
                    p_from = link_indices[r]
                    p_to = link_indices[c]
                    if p_from in input_codes:
                        suffix = "__" + str(input_duplicates.count(p_from))
                        input_duplicates.append(p_from)
                        p_type = 'input'
                    elif p_from in biosphere_codes:
                        suffix = "__" + str(biosphere_duplicates.count(p_from))
                        biosphere_duplicates.append(p_from)
                        p_type = 'biosphere'
                    else:
                        suffix = ""
                        p_type = 'intermediate'
                    
                    links.append({'sourceID': p_from + suffix, 'targetID': p_to, 'type': p_type, 'amount': 1, 'label': label_map[p_from]})
           
    #add extra nodes
    while len(input_duplicates) > 0:
        p = input_duplicates.pop()
        count = input_duplicates.count(p)
        if count > 0:
            suffix = "__" + str(count)
            nodes.append({'name': input_map[p], 'type': 'input', 'id': p + suffix, 'initX': i * 50 + 150, 'initY': i * 50})
            i += 1
            
    while len(biosphere_duplicates) > 0:
        p = biosphere_duplicates.pop()
        count = biosphere_duplicates.count(p)
        if count > 0:
            suffix = "__" + str(count)
            nodes.append({'name': biosphere_map[p], 'type': 'biosphere', 'id': p + suffix, 'initX': i * 50 + 150, 'initY': i * 50})
            i += 1
            
    #try and reset the locations
    
    for n in nodes:
        node_id = n['id']
        if node_id in sandbox_positions:
            n['initX'] = sandbox_positions[node_id]['x']
            n['initY'] = sandbox_positions[node_id]['y']
            
    #print(nodes)
    #print(inputs)
    #print(process_name_map)
    return m.name, nodes, links, outputlabels


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@login_manager.user_loader
def user_loader(user_id):
    return User.query.get(user_id)


@app.route('/')
@app.route('/index')
def index():
    if request.args.get('code'):
        my_code = request.args.get('code')

        find_model = ModelFile.query.filter_by(link_id=my_code).first()

        if find_model is not None:
            return redirect('/view/{}'.format(my_code))

    return render_template('index.html')


@app.route('/models')
@login_required
def models():

    if 'current_model' not in session:
        session['current_model'] = app.config['CURRENT_FILE']

    args = ModelFile.query.filter(ModelFile.owner.has(username=current_user.username))

    return render_template('models.html', args=args)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']

        if file.filename == '':
            
            return redirect(request.url)

        #print(file.filename)
        save_filename = '{}_{}'.format(current_user.username, file.filename)
        #print(save_filename)

        if file and allowed_file(file.filename):
            filename = secure_filename(save_filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], save_filename) 
            file.save(filepath)

            tmp = load_viewfile(filepath)
            friendly_name = tmp.name
            # add to database
            db_item = ModelFile(filename, filepath, current_user.id, None, friendly_name)
            db.session.add(db_item)
            db.session.commit()

            return redirect('/models')

    return render_template('upload.html')

"""
@app.route('/sandbox')
def sandbox():
    args = {}
    name, nodes, links, outputlabels = get_sandbox_variables(session['current_model'])
    args = {'model': {'name': name}, 'nodes': nodes, 'links': links, 'outputlabels': outputlabels}

    return render_template('sandbox.html', args=args)


@app.route('/results')
def results():
    args = {}
    modelview = load_viewfile(session['current_model'])

    if modelview.result_set is not None:

        item = modelview.result_set['settings']['item']

        args = {'model': {'name': modelview.name}}

        args['item'] = item
        args['result_sets'] = modelview.result_set
        return render_template('analysis.html', args=args)
    else:
        return render_template('analysis_fail.html')


@app.route('/results.json')
def results_json():
    modelview = load_viewfile(session['current_model'])
    return json.dumps(modelview.result_set)
"""

@app.route('/results/<model_code>.json')
def include_results(model_code):
    my_model = ModelFile.query.filter_by(link_id=model_code).first()
    modelview = load_viewfile(my_model.filepath)
    return json.dumps(modelview.result_set)


@app.route('/excel_export')
def excel_export():

    modelview = load_viewfile(session['current_model'])

    export_type = request.args.get('type')
    ps = int(request.args.get('ps'))
    m = int(request.args.get('m'))

    print (export_type, ps, m)

    if export_type == 'summary':

        output = create_excel_summary(modelview)

        filename = "{}_summary_results.xlsx".format(modelview.name)

    elif export_type == 'method':

        output = create_excel_method(modelview, m)

        filename = "{}_{}_results.xlsx".format(modelview.name, modelview.result_set['settings']['method_names'][m])

    #finally return the file
    return send_file(output, attachment_filename=filename, as_attachment=True)

"""
@app.route('/parameters')
def sorted_parameter_setup():

    modelview = load_viewfile(session['current_model'])
    
    sorted_parameters = parameter_sorting(modelview)
        
    args = {'title': 'Parameter set'}
    args['sorted_parameters'] = sorted_parameters
    args['ps_names'] = [x for x in modelview.parameter_sets.keys()]
    
    return render_template('parameter_set_table_sorted.html', args=args)


@app.route('/set_model/<filename>')
def set_model(filename):
    session['current_model'] = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return redirect('/sandbox')
"""

@app.route('/admin')
@login_required
def admin():
    
    args = ModelFile.query.all()

    return render_template('admin.html', args=args)


@app.route('/delete_model/<id>')
@login_required
def delete_model(id):
    
    item = ModelFile.query.get(id)
    filepath = item.filepath
    print(filepath)
    db.session.delete(item)
    db.session.commit()
    os.remove(filepath)

    return redirect('/admin')


@app.route("/login", methods=["GET", "POST"])
def login():
    """For GET requests, display the login form. For POSTS, login the current user
    by processing the form."""
    #print (db)
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter((User.email == form.login_data.data) | (User.username == form.login_data.data)).first()
        print(user)
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                user.authenticated = True
                db.session.add(user)
                db.session.commit()
                login_user(user, remember=True)
                next = request.args.get('next')
                print('next up is {}'.format(request.args))
                # is_safe_url should check if the url is safe for redirects.
                # See http://flask.pocoo.org/snippets/62/ for an example.
                if not is_safe_url(next):
                    return abort(400)
                flash('Successfully logged in - welcome {}'.format(user.username))
                return redirect(next or url_for('index'))
                
            else:
                print('Wrong password')
                flash('Username or password incorrect')
        else:
            flash('Username or password incorrect')
            
    else:
        print("Can't validate form")
    print('End of login')

    return render_template("login.html", form=form)

@app.route("/logout", methods=["GET"])
@login_required
def logout():
    """Logout the current user."""
    user = current_user
    user.authenticated = False
    db.session.add(user)
    db.session.commit()
    logout_user()
    return render_template("logout.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        pw_hash = bcrypt.generate_password_hash(form.password.data).decode("utf-8") 
        print(type(pw_hash))

        if len(User.query.filter((User.email == form.email.data) | (User.username == form.username.data)).all()) != 0:
            flash('already exists')
            return redirect(url_for('register'))
        elif form.password.data != form.password_repeat.data:
            flash('passwords dont match')
            return redirect(url_for('register'))
        else:
            user = User(email=form.email.data, password=pw_hash, username=form.username.data)
            user.authenticated = True
            db.session.add(user)
            db.session.commit()
            flash ('Registration successful - welcome {}'.format(user.username))
            login_user(user, remember=True)
            return redirect(url_for('models'))

    return render_template("register.html", form=form)


@app.route('/restricted')
@login_required
def restricted():
    return render_template("restricted.html")


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


@app.route('/view/<model_code>')
def view_model(model_code):
    my_model = ModelFile.query.filter_by(link_id=model_code).first()

    name, nodes, links, outputlabels = get_sandbox_variables(my_model.filepath)
    modelview = load_viewfile(my_model.filepath)

    args = {'model': {'name': name}, 'nodes': nodes, 'links': links, 'outputlabels': outputlabels}

    if modelview.result_set is not None:

        item = modelview.result_set['settings']['item']

        args['item'] = item
        args['result_sets'] = modelview.result_set
       
    sorted_parameters = parameter_sorting(modelview)

    args['sorted_parameters'] = sorted_parameters
    args['ps_names'] = [x for x in modelview.parameter_sets.keys()]

    return render_template('model_page.html', args=args)

#@app.errorhandler(401)
#def unauthorised(e):
#    return render_template('401.html'), 401
