from io import BytesIO
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from googleapiclient.http import MediaIoBaseUpload

from google_drive import GoogleDriveService

app = Flask(__name__)
service = GoogleDriveService().build()

# Configuratie
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Serve the landing page
@app.route('/home')
def landing_page():
    return send_from_directory('static', 'landing.html')


# Serve the upload form
@app.route('/upload')
def upload_page():
    return send_from_directory('static', 'upload.html')


# Serve the gallery page (a separate frontend that fetches gallery content)
@app.route('/gallery')
def get_gallery():
    results = service.files().list(
        pageSize=50, fields="nextPageToken, files(id, name, webViewLink)").execute()
    items = results.get('files', [])
    return send_from_directory('static', 'gallery.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400

    files = request.files.getlist('files')
    uploaded_files = []

    for uploaded_file in files:
        if uploaded_file and allowed_file(uploaded_file.filename):
            try:
                # Debugging: Log file details
                print(f"Uploading file: {uploaded_file.filename}")

                buffer_memory = BytesIO()
                uploaded_file.save(buffer_memory)
                buffer_memory.seek(0)  # Go back to the start of the buffer

                # Create the media upload object
                media_body = MediaIoBaseUpload(buffer_memory, mimetype=uploaded_file.mimetype, resumable=True)

                # Generate a unique filename with timestamp
                created_at = datetime.now().strftime("%Y%m%d%H%M%S")
                file_metadata = {
                    "name": f"{uploaded_file.filename} ({created_at})"
                }

                # Debugging: Check if Google Drive service is available
                if not service:
                    print("Google Drive service is not initialized.")
                    return jsonify({'success': False, 'message': 'Google Drive service failed to initialize'}), 500

                # Upload to Google Drive
                print("Uploading to Google Drive...")
                returned_fields = "id, name, mimeType, webViewLink"
                file = service.files().create(
                    body=file_metadata,
                    media_body=media_body,
                    fields=returned_fields
                ).execute()

                print(f"File uploaded successfully: {file['name']}")

                uploaded_files.append({
                    'name': uploaded_file.filename,
                    'id': file['id'],
                    'link': file['webViewLink']
                })

            except Exception as e:
                print(f"Error during upload: {e}")
                return jsonify({'success': False, 'message': 'Error uploading to Google Drive'}), 500

    return jsonify({'success': True, 'files': uploaded_files})


if __name__ == '__main__':
    app.run(port=5000, debug=True)