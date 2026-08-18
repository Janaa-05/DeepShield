import os
import uuid
import csv
import io
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, send_file
from werkzeug.utils import secure_filename
from PIL import Image
from utils.detector import analyze_image, download_image_from_url, get_recent_scans, clear_scans, generate_pdf_for_scan
from utils.evaluation import get_model_evaluation_metrics

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'static', 'reports')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB Limit for Batch Uploads

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}

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

@app.route('/')
def home():
    recent = get_recent_scans(limit=5)
    metrics = get_model_evaluation_metrics()
    return render_template('index.html', recent_scans=recent, eval_metrics=metrics)

@app.route('/history-page')
def history_page():
    scans = get_recent_scans(limit=100)
    return render_template('history.html', scans=scans)

@app.route('/batch-upload', methods=['GET', 'POST'])
def batch_upload_route():
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
                        res = analyze_image(saved_path, REPORTS_FOLDER)
                        batch_results.append(res)
                    except Exception as e:
                        print("Batch Item Error:", e)
                else:
                    if os.path.exists(saved_path):
                        os.remove(saved_path)
    return render_template('batch.html', batch_results=batch_results)

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """
    REST API Endpoint (/api/analyze)
    Accepts an image via POST and returns JSON containing:
    - prediction
    - confidence
    - authenticity_score
    - source_attribution
    - inference_time_ms
    - forensic_summary
    """
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

    analysis = analyze_image(saved_path, REPORTS_FOLDER)

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

@app.route('/report/<int:analysis_id>')
def download_pdf_report(analysis_id):
    try:
        pdf_path = generate_pdf_for_scan(analysis_id, UPLOAD_FOLDER, REPORTS_FOLDER)
        if not pdf_path or not os.path.exists(pdf_path):
            return "Analysis report unavailable", 404
            
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"deepshield_report_{analysis_id}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return f"PDF Generation Error: {str(e)}", 500

@app.route('/export-csv')
def export_csv():
    scans = get_recent_scans(limit=1000)
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
def clear_history_route():
    clear_scans()
    return redirect(url_for('history_page'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
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

            analysis = analyze_image(saved_path, REPORTS_FOLDER)

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

@app.route('/history')
def history_json():
    scans = get_recent_scans(limit=50)
    return jsonify(scans)

@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template('upload.html', error='File size exceeds maximum allowable payload limit.'), 413

if __name__ == '__main__':
    app.run(debug=True, port=5000)
