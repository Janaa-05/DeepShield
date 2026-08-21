import os
import uuid
import csv
import io
import re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, send_file, send_from_directory, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image

from utils.detector import analyze_image, download_image_from_url, generate_pdf_for_scan
from utils.evaluation import get_model_evaluation_metrics
from utils.db import (
    init_db,
    get_user_by_email,
    get_user_by_id,
    create_user,
    update_user_last_login,
    update_user_name,
    update_user_password,
    get_recent_scans,
    get_scan_by_id,
    get_user_stats,
    clear_scans
)

app = Flask(__name__)

# Security & Session Configurations
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'static', 'reports')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB Limit for Batch Uploads
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'deepshield_secure_production_key_2026_forensics')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}

@app.route('/favicon.ico')
def favicon():
    """Serve root favicon directly for standard browser queries."""
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Initialize SQLite Database and Migrate Schema Safely
init_db()

# ==================== AUTHENTICATION HELPER & DECORATORS ====================

def login_required(f):
    """Reusable decorator to protect routes against unauthenticated access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user():
    """Injects current logged-in user into all Jinja templates automatically."""
    if 'user_id' in session:
        return {
            'current_user': {
                'id': session.get('user_id'),
                'name': session.get('user_name'),
                'email': session.get('user_email')
            }
        }
    return {'current_user': None}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image_bytes(file_path):
    """Phase 2 Security: Validates MIME header and prevents corrupt/executable payload files."""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False

# ==================== PUBLIC ROUTES & AUTHENTICATION ====================

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Input Validation
        if not name or not email or not password or not confirm_password:
            return render_template('register.html', error="All fields are required.", name=name, email=email)

        # Email syntax validation
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            return render_template('register.html', error="Invalid email address format.", name=name, email=email)

        if len(password) < 8:
            return render_template('register.html', error="Password must be at least 8 characters long.", name=name, email=email)

        if password != confirm_password:
            return render_template('register.html', error="Password confirmation does not match.", name=name, email=email)

        # Check unique email
        existing_user = get_user_by_email(email)
        if existing_user:
            return render_template('register.html', error="Email address is already registered.", name=name, email=email)

        # Hash password securely
        password_hash = generate_password_hash(password)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            create_user(name, email, password_hash, created_at)
            return redirect(url_for('login'))
        except Exception as e:
            return render_template('register.html', error="Failed to create account. Please try again.", name=name, email=email)

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            return render_template('login.html', error="Invalid email or password.", email=email)

        user = get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            # Create secure Flask session
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']

            # Update last login timestamp
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_user_last_login(user['id'], now_str)

            next_url = request.args.get('next')
            return redirect(next_url if next_url else url_for('dashboard'))

        # Generic security response - do not reveal if email exists
        return render_template('login.html', error="Invalid email or password.", email=email)

    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== PROTECTED USER DASHBOARD & PROFILE ====================

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    stats = get_user_stats(user_id)
    recent_scans = get_recent_scans(limit=10, user_id=user_id)
    return render_template('dashboard.html', stats=stats, recent_scans=recent_scans)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    stats = get_user_stats(user_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            new_name = request.form.get('name', '').strip()
            if not new_name:
                return render_template('profile.html', user=user, stats=stats, error="Name cannot be empty.")
            update_user_name(user_id, new_name)
            session['user_name'] = new_name
            user = get_user_by_id(user_id)
            return render_template('profile.html', user=user, stats=stats, success="Profile updated successfully!")

        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_new_password = request.form.get('confirm_new_password', '')

            if not check_password_hash(user['password_hash'], current_password):
                return render_template('profile.html', user=user, stats=stats, error="Current password is incorrect.")

            if len(new_password) < 8:
                return render_template('profile.html', user=user, stats=stats, error="New password must be at least 8 characters.")

            if new_password != confirm_new_password:
                return render_template('profile.html', user=user, stats=stats, error="New passwords do not match.")

            new_hash = generate_password_hash(new_password)
            update_user_password(user_id, new_hash)
            user = get_user_by_id(user_id)
            return render_template('profile.html', user=user, stats=stats, success="Password changed successfully!")

    return render_template('profile.html', user=user, stats=stats)

# ==================== PROTECTED FORENSIC ANALYSIS & HISTORY ====================

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    user_id = session['user_id']
    if request.method == 'POST':
        saved_path = None
        filename = None

        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            if not allowed_file(file.filename):
                return render_template('upload.html', error='Security violation: Invalid image extension.')

            filename = secure_filename(file.filename)
            saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(saved_path)

        elif 'image_url' in request.form and request.form['image_url'].strip() != '':
            url = request.form['image_url'].strip()
            try:
                ext = 'jpg'
                if '.' in url.split('/')[-1]:
                    possible_ext = url.split('/')[-1].split('.')[-1].lower()
                    if possible_ext in ALLOWED_EXTENSIONS:
                        ext = possible_ext

                filename = secure_filename(f"url_scan_{uuid.uuid4().hex[:8]}.{ext}")
                saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                download_image_from_url(url, saved_path)
            except Exception as e:
                return render_template('upload.html', error=f"Failed to fetch remote image URL: {str(e)}")

        if saved_path and os.path.exists(saved_path):
            if not validate_image_bytes(saved_path):
                os.remove(saved_path)
                return render_template('upload.html', error='Security alert: Invalid or corrupted binary image payload.')

            analysis = analyze_image(saved_path, REPORTS_FOLDER, user_id=user_id)

            return render_template(
                'upload.html',
                scan_id=analysis['scan_id'],
                result=analysis['result'],
                confidence=analysis['confidence'],
                authenticity_score=analysis['authenticity_score'],
                authenticity_label=analysis['authenticity_label'],
                authenticity_explanation=analysis['authenticity_explanation'],
                source_attribution=analysis['source_attribution'],
                inference_time_ms=analysis['inference_time_ms'],
                is_ai=analysis['is_ai'],
                filename=filename,
                image_url=f"/static/uploads/{filename}",
                gradcam_url=analysis['gradcam_url'],
                gradcam_explanation=analysis['gradcam_explanation'],
                ela_url=analysis['ela_url'],
                fft_url=analysis['fft_url'],
                ela_std_dev=analysis['ela_std_dev'],
                fft_freq=analysis['fft_freq'],
                noise_var=analysis['noise_var'],
                jpeg_ratio=analysis['jpeg_ratio'],
                edge_density=analysis['edge_density'],
                color_entropy=analysis['color_entropy'],
                sharpness=analysis['sharpness'],
                metadata_flags=analysis['metadata_flags']
            )

        return render_template('upload.html', error='No valid image file or URL supplied.')

    return render_template('upload.html')

@app.route('/batch-upload', methods=['GET', 'POST'])
@login_required
def batch_upload_route():
    user_id = session['user_id']
    batch_results = []
    if request.method == 'POST':
        files = request.files.getlist('images')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                saved_path = os.path.join(app.config['UPLOAD_FOLDER'], f"batch_{uuid.uuid4().hex[:6]}_{filename}")
                file.save(saved_path)

                if validate_image_bytes(saved_path):
                    try:
                        res = analyze_image(saved_path, REPORTS_FOLDER, user_id=user_id)
                        batch_results.append(res)
                    except Exception as e:
                        print("Batch Item Error:", e)
                else:
                    if os.path.exists(saved_path):
                        os.remove(saved_path)
    return render_template('batch.html', batch_results=batch_results)

@app.route('/history-page')
@login_required
def history_page():
    user_id = session['user_id']
    scans = get_recent_scans(limit=100, user_id=user_id)
    return render_template('history.html', scans=scans)

@app.route('/history')
@login_required
def history_json():
    user_id = session['user_id']
    scans = get_recent_scans(limit=50, user_id=user_id)
    return jsonify(scans)

# ==================== IDOR REPORT & FILE SECURITY ====================

@app.route('/report/<int:analysis_id>')
@login_required
def download_pdf_report(analysis_id):
    """
    IDOR Security Enforced:
    Verifies that analysis_id belongs strictly to session['user_id'].
    """
    user_id = session['user_id']
    scan = get_scan_by_id(analysis_id, user_id=user_id)
    if not scan:
        return render_template('error.html', code=403, title="Access Denied", message="You do not have permission to view or download this report."), 403

    try:
        pdf_path = generate_pdf_for_scan(analysis_id, UPLOAD_FOLDER, REPORTS_FOLDER, user_id=user_id)
        if not pdf_path or not os.path.exists(pdf_path):
            return render_template('error.html', code=404, title="Report Unavailable", message="The requested report file is unavailable."), 404
            
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"deepshield_report_{analysis_id}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return render_template('error.html', code=500, title="PDF Generation Error", message="An error occurred while building the PDF audit report."), 500

@app.route('/export-csv')
@login_required
def export_csv():
    user_id = session['user_id']
    scans = get_recent_scans(limit=1000, user_id=user_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Filename', 'Result', 'Confidence', 'Authenticity_Score', 'Source_Attribution', 'Inference_Time_MS', 'Is_AI', 'ELA_Std_Dev', 'FFT_High_Freq', 'Timestamp'])
    
    for s in scans:
        writer.writerow([
            s.get('id'), s.get('filename'), s.get('result'), s.get('confidence'), 
            s.get('authenticity_score'), s.get('source_attribution'), s.get('inference_time_ms'),
            s.get('is_ai'), s.get('ela_std_dev'), s.get('fft_high_freq'), s.get('timestamp')
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=deepshield_audit_logs.csv"}
    )

@app.route('/clear-history', methods=['POST'])
@login_required
def clear_history_route():
    user_id = session['user_id']
    clear_scans(user_id=user_id)
    return redirect(url_for('history_page'))

# ==================== REST API ENDPOINT ====================

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """
    REST API Endpoint (/api/analyze)
    Accepts an image via POST and returns JSON.
    Maintains backward compatibility for external API clients.
    Associates scan with user_id if session authentication exists.
    """
    user_id = session.get('user_id')

    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image file provided'}), 400

    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Invalid extension'}), 400

    filename = secure_filename(file.filename)
    saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(saved_path)

    if not validate_image_bytes(saved_path):
        os.remove(saved_path)
        return jsonify({'status': 'error', 'message': 'Corrupt binary payload'}), 400

    analysis = analyze_image(saved_path, REPORTS_FOLDER, user_id=user_id)

    forensic_summary = {
        "ela_std_dev": analysis['ela_std_dev'],
        "fft_high_freq": analysis['fft_freq'],
        "noise_var": analysis['noise_var'],
        "tenengrad_sharpness": analysis['sharpness'],
        "jpeg_block_ratio": analysis['jpeg_ratio'],
        "canny_edge_density_pct": analysis['edge_density'],
        "rgb_channel_entropy": analysis['color_entropy'],
        "metadata_flags": analysis['metadata_flags']
    }

    return jsonify({
        "status": "success",
        "scan_id": analysis['scan_id'],
        "filename": filename,
        "prediction": analysis['result'],
        "confidence": analysis['confidence'],
        "authenticity_score": analysis['authenticity_score'],
        "source_attribution": analysis['source_attribution'],
        "inference_time_ms": analysis['inference_time_ms'],
        "is_ai": analysis['is_ai'],
        "gradcam_url": analysis['gradcam_url'],
        "forensic_summary": forensic_summary
    })

# ==================== DEEPSHIELD ERROR HANDLERS ====================

@app.errorhandler(401)
def unauthorized_error(error):
    return render_template('error.html', code=401, title="Unauthorized", message="Authentication required. Please sign in to access this page."), 401

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('error.html', code=403, title="Access Denied", message="You do not have permission to view or access this resource."), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', code=404, title="Page Not Found", message="The requested URL or resource could not be found."), 404

@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template('error.html', code=413, title="Payload Too Large", message="File size exceeds maximum allowable payload limit (32MB)."), 413

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html', code=500, title="Internal Error", message="An unexpected server error occurred. Please try again later."), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
