import os
from app import app
from flask import render_template, request, redirect, url_for, send_file, session
from werkzeug.utils import secure_filename
from .lcoptview import *
from .excel_functions import create_excel_method, create_excel_summary
from .parameters import parameter_sorting
from .models import *
from collections import OrderedDict
import json


ALLOWED_EXTENSIONS = set(['lcoptview'])

#TEST_FILE = app.config['CURRENT_FILE']


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


@app.route('/')
@app.route('/index')
def index():
    #return "Hello, Flask World!"
    args = {}
    if 'current_model' not in session:
        session['current_model'] = app.config['CURRENT_FILE']

    return render_template('index.html', args=args)


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
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename) 
            
            # add to database
            db_item = ModelFile(filename, filepath)
            db.session.add(db_item)
            db.session.commit()

            file.save(filepath)
            session['current_model'] = filepath

            return redirect('/sandbox')

    return render_template('upload.html')


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


@app.route('/parameters')
def sorted_parameter_setup():

    modelview = load_viewfile(session['current_model'])
    
    sorted_parameters = parameter_sorting(modelview)
        
    args = {'title': 'Parameter set'}
    args['sorted_parameters'] = sorted_parameters
    args['ps_names'] = [x for x in modelview.parameter_sets.keys()]
    
    return render_template('parameter_set_table_sorted.html', args=args)


@app.route('/models')
def view_models():
    args = ModelFile.query.all()
    return render_template('models.html', args=args)


@app.route('/set_model/<filename>')
def set_model(filename):
    session['current_model'] = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return redirect('/sandbox')
