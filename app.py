from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import shutil
import tempfile
import uuid
import base64
from PIL import Image
import io
import os

from simple import FortuneTellerProcessor

app = Flask(__name__)

# Configure upload settings
TEMP_DIR = Path(tempfile.gettempdir()) / "fortune_teller"
TEMP_DIR.mkdir(exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

@app.route('/api/process', methods=['POST'])
def process_image():
    """Process uploaded fortune teller image and return extracted segments"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Create unique working directory
        session_id = str(uuid.uuid4())
        work_dir = TEMP_DIR / session_id
        work_dir.mkdir(parents=True)
        
        # Save uploaded file
        input_path = work_dir / "input.png"
        file.save(str(input_path))
        
        # Process image
        processor = FortuneTellerProcessor(str(input_path))
        output_dir = work_dir / "segments"
        output_dir.mkdir()
        
        # Extract segments
        processor.extract_all(str(output_dir))
        
        # Convert extracted images to base64
        results = {}
        for segment_path in output_dir.glob("*.png"):
            segment_id = segment_path.stem
            with open(segment_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
                results[segment_id] = f"data:image/png;base64,{img_data}"
        
        return jsonify({
            "session_id": session_id,
            "segments": results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reconstruct', methods=['POST'])
def reconstruct_image():
    """Reconstruct fortune teller from uploaded segments"""
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files provided'}), 400

        # Create unique working directory
        session_id = str(uuid.uuid4())
        work_dir = TEMP_DIR / session_id
        work_dir.mkdir(parents=True)
        
        # Save uploaded files
        input_dir = work_dir / "input"
        input_dir.mkdir()
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = input_dir / filename
                file.save(str(file_path))
        
        # Process reconstruction
        processor = FortuneTellerProcessor(template_size=800)
        output_path = work_dir / "reconstructed.png"
        
        reconstructed = processor.reconstruct(str(input_dir), str(output_path))
        
        # Convert result to base64
        with open(output_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode()
            
        return jsonify({
            "session_id": session_id,
            "image": f"data:image/png;base64,{img_data}"
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup/<session_id>', methods=['DELETE'])
def cleanup_session(session_id):
    """Clean up temporary files for a session"""
    try:
        session_dir = TEMP_DIR / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reconstruct_from_composites', methods=['POST'])
def reconstruct_from_composites():
    """Reconstruct fortune teller from composite images"""
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files provided'}), 400

        # Create unique working directory
        session_id = str(uuid.uuid4())
        work_dir = TEMP_DIR / session_id
        work_dir.mkdir(parents=True)
        
        # Create composites directory
        composites_dir = work_dir / "composites"
        composites_dir.mkdir()
        
        # Save uploaded composite files
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = composites_dir / filename
                file.save(str(file_path))
        
        # Process reconstruction
        processor = FortuneTellerProcessor(template_size=800)
        output_path = work_dir / "reconstructed.png"
        
        # Use reconstruct_from_composites instead of reconstruct
        reconstructed = processor.reconstruct_from_composites(
            str(composites_dir),
            str(output_path)
        )
        
        # Convert result to base64
        with open(output_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode()
            
        return jsonify({
            "session_id": session_id,
            "image": f"data:image/png;base64,{img_data}"
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to allow frontend requests"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)