from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pandas as pd
import os
import uuid
from power_flow_viz import PowerFlowViz

app = Flask(__name__)

# Directories for uploads and results
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
RESULT_FOLDER = os.path.join(os.getcwd(), 'result')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# In-memory session store (sessions ne persistent pas au redémarrage de l’application)
# Pour conserver les sessions après un restart, utilisez une base externe (Redis, fichier, bdd, etc.)
sessions = {}

@app.route('/sessions', methods=['POST'])
def create_session():
    """
    Create a new PowerFlowViz session.
    Expects multipart/form-data with:
    - file: Excel file
    - Sb: float (VA)
    - Vb: float (V)
    - f: float (Hz)
    - name: string (session name)
    - sheet_name: string (optional, Excel sheet name to load)
    Returns JSON { session_id: str }
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    filename = secure_filename(file.filename)
    session_file = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, session_file)
    file.save(filepath)

    try:
        Sb = float(request.form.get('Sb'))
        Vb = float(request.form.get('Vb'))
        f_val = float(request.form.get('f'))
        name = request.form.get('name', '').strip()
        sheet_name = request.form.get('sheet_name') or 0
    except (TypeError, ValueError) as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400

    try:
        xls = pd.read_excel(filepath, sheet_name=sheet_name)
    except Exception as e:
        return jsonify({'error': f'Failed to read Excel (sheet {sheet_name}): {str(e)}'}), 400

    try:
        pfv = PowerFlowViz(xls, Sb, Vb, f_val, name)
        pfv.set_net()
    except Exception as e:
        return jsonify({'error': f'Initialization error: {str(e)}'}), 500

    session_id = str(uuid.uuid4())
    sessions[session_id] = pfv
    base_url = request.host_url.rstrip('/')
    links = {
        "session_id": session_id,
        "static_plot_url": f"{base_url}/sessions/{session_id}/static_plot&save=false",
        "day_slice_url": f"{base_url}/sessions/{session_id}/day_slice?hour_start=17&hour_end=18&anonymous=false&save=false",
        "export_net_url": f"{base_url}/sessions/{session_id}/export_net"
    }
    return jsonify(links), 201

@app.route('/sessions/<session_id>/day_slice', methods=['GET','POST'])
def day_slice(session_id):
    """
    Generate a day slice visualization.
    Supports GET (query string) and POST (JSON body).
    Parameters:
    - hour_start: int
    - hour_end: int
    - anonymous: bool

    Saves two HTML files:
    1) standard file named <base>_from_<h1>h_to_<h2>h.html
    2) direct link file named direct_<session_id>_day_slice.html
    Returns the direct link file.
    """
    pfv = sessions.get(session_id)
    if not pfv:
        return jsonify({'error': 'Invalid session_id'}), 404

    if request.method == 'GET':
        params = request.args
    else:
        params = request.get_json() or {}
    try:
        hour_start = int(params.get('hour_start', 0))
        hour_end   = int(params.get('hour_end', 24))
        anonymous  = params.get('anonymous', 'false').lower() == 'true'
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {e}'}), 400

    # Standard save via PowerFlowViz
    try:
        map_obj = pfv.generate_time_slider_map(
            hour_start=hour_start,
            hour_end=hour_end,
            save=True,
            anonymous=anonymous
        )
        direct_name = f"direct_{session_id}_day_slice.html"
        direct_path = os.path.join(RESULT_FOLDER, direct_name)
        map_obj.save_map(direct_path)
    except Exception as e:
        return jsonify({'error': f'Visualization save error: {e}'}), 500

    # Serve direct link file
    return send_file(direct_path, mimetype='text/html')

@app.route('/sessions/<session_id>/static_plot', methods=['GET','POST'])
def static_plot(session_id):
    """
    Generate static max load / min voltage plot.
    Supports GET and POST with
    """
    pfv = sessions.get(session_id)
    if not pfv:
        return jsonify({'error': 'Invalid session_id'}), 404

    if request.method == 'GET':
        params = request.args
    else:
        params = request.get_json() or {}

    try:
        map_obj = pfv.generate_static_summary_map(save=True)
        direct_name = f"direct_{session_id}_static_plot.html"
        direct_path = os.path.join(RESULT_FOLDER, direct_name)
        map_obj.save_map(direct_path)
    except Exception as e:
        return jsonify({'error': f'Visualization error: {e}'}), 500
    
    return send_file(direct_path, mimetype='text/html')

@app.route('/sessions/<session_id>/export_net', methods=['GET'])
def export_net(session_id):
    """
    Export the underlying pandapower network as JSON.
    """
    pfv = sessions.get(session_id)
    if not pfv:
        return jsonify({'error': 'Invalid session_id'}), 404
    try:
        net = pfv.export_net()
        net_json = net.to_json()
        return app.response_class(net_json, mimetype='application/json')
    except Exception as e:
        return jsonify({'error': f'Export error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
