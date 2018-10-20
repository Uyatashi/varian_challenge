import os
from flask import Flask, flash, request, Response, redirect, url_for, jsonify, send_file
from werkzeug.utils import secure_filename
import time
import zipfile
import subprocess
import json


#The base url from ngrok - doesn't change
base_url = 'http://9af98c19.ngrok.io/'


UPLOAD_FOLDER = 'data/'
ALLOWED_EXTENSIONS = set(['dcm', 'jpg', 'zip'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def zip_extract(path_to_zip):
    try:
        zip_ref = zipfile.ZipFile(path_to_zip, 'r')
        zip_ref.extractall(UPLOAD_FOLDER)
        zip_ref.close()
        return 1
    except:
        return 0

# @app.route("/")
# def hello():
#     return "Hello World!"

@app.route("/upload", methods=['POST'])
def upload_data():
    # check if the post request has the file part
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    # submit an empty part without filename
    if file.filename == '':
        return "No selected file"

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = str(time.time()).replace('.','')
        filename_extended = filename.split('.')
        uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_extended[0] + '_' + timestamp + '.' + filename_extended[1])
        file.save(uploaded_file_path)

        #Extract zipped patient files
        if filename_extended[1] == 'zip':
            if (zip_extract(uploaded_file_path) == 0):
                return "Failed to extract .zip file"

            #Delete the uploaded .zip file
            process = subprocess.Popen('rm ' + uploaded_file_path, stdout=subprocess.PIPE, shell=True)
            output, error = process.communicate()

            return 'File uploaded'

        #Upload a folder

    return "Nothing happened"


#Return image vector for a given patient
@app.route('/get_images/<string:patient_id>', methods=['GET'])
def get_images(patient_id):
    #Found patient's record
    images_path = 'data/' + patient_id + '/jpg/'
    if os.path.exists(images_path):
        img_vector = []

        [ { "name" : filename, "size" : st.st_size ,
        "url" : url_for('show', filename=filename)} ]

        for image in os.listdir(images_path):
            img_url = base_url + images_path + image
            print('Image: ', img_url)
            img_vector.append(img_url)
    else:
        return 'No images for this patient yet'

    #I don't think we need a json response here
    return Response(json.dumps(img_vector),  mimetype='application/json')

#Return the queried image
@app.route('/data/<string:patient_id>/jpg/<string:image>', methods=['GET'])
def show_image(patient_id, image):
    image_path = 'data/' + patient_id + '/jpg/' + image
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/jpg')


app.run(host='0.0.0.0', debug=True, port=5000)
