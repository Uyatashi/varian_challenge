import os
from flask import Flask, flash, request, Response, redirect, url_for, jsonify, send_file
from werkzeug.utils import secure_filename
import time
import zipfile
import subprocess
import json
import pydicom
import os
import matplotlib.pyplot as plt

# from PIL import Image, ImageDraw


# The base url from ngrok
# base_url = raw_input("Ngrok base url(http://<id>.ngrok.io): ")

# base_url = 'http://a6cb8bf4.ngrok.io'
base_url = 'localhost:5000'

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


def extract_patient_images(patient_id):
    patient_path = 'data/' + patient_id + '/'
    patient_files = os.listdir(patient_path)
    if (len(patient_files) == 0):
        return 0
    try:
        process = subprocess.Popen('mkdir ' + patient_path + 'jpg', stdout=subprocess.PIPE, shell=True)
        output, error = process.communicate()
    except:
        pass
    for image in patient_files:
        try:
            # if (image.split('.')[0] != 'CT' and image.split('.')[0] != 'MR'):
            if (image.split('.')[0] != 'MR'):
                continue
            image_dcm = pydicom.dcmread(patient_path + image)
            img_file = open(patient_path + 'jpg/' + image.replace('.dcm', '') + '.jpg', 'wb')
            plt.imsave(img_file, image_dcm.pixel_array)
        except:
            continue
    return 1


def get_images(patient_id):
    # Found patient's record
    images_path = 'data/' + patient_id + '/jpg/'
    if os.path.exists(images_path):
        img_vector = []
        for image in os.listdir(images_path):
            img_url = base_url + images_path + image
            print('Image: ', img_url)
            img_vector.append(img_url)
    else:
        return []

    return img_vector


def jsonify_images(img_vector):
    json_str = '{'
    for img in img_vector:
        json_str = json_str + '{"frame"="' + img + '",'
        json_str = json_str + '"score"="0.98"},'
    json_str = json_str[:-1] + '}'
    return json_str


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
        timestamp = str(time.time()).replace('.', '')
        filename_extended = filename.split('.')
        uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                          filename_extended[0] + '_' + timestamp + '.' + filename_extended[1])
        file.save(uploaded_file_path)

        # Extract zipped patient files
        if filename_extended[1] == 'zip':
            if (zip_extract(uploaded_file_path) == 0):
                return "Failed to extract .zip file"

            # Delete the uploaded .zip file
            process = subprocess.Popen('rm ' + uploaded_file_path, stdout=subprocess.PIPE, shell=True)
            output, error = process.communicate()

        # Extract images and return image url list

        if (extract_patient_images(filename_extended[0]) == 0):
            return 'Failed to extract patient images'
        img_vector = get_images(filename_extended[0])
        json_res = jsonify_images(img_vector)
        return Response(json_res, mimetype='application/json')
        # return Response(json.dumps(img_vector),  mimetype='application/json')
        # return img_vector
        # return 'Success'
        return

    return 'Fail'


# Return image vector for a given patient
# @app.route('/get_images/<string:patient_id>', methods=['GET'])
# def get_images(patient_id):
#     #Found patient's record
#     images_path = 'data/' + patient_id + '/jpg/'
#     if os.path.exists(images_path):
#         img_vector = []
#
#         [ { "name" : filename, "size" : st.st_size ,
#         "url" : url_for('show', filename=filename)} ]
#
#         for image in os.listdir(images_path):
#             img_url = base_url + images_path + image
#             print('Image: ', img_url)
#             img_vector.append(img_url)
#     else:
#         return 'No images for this patient yet'
#
#     #I don't think we need a json response here
#     return Response(json.dumps(img_vector),  mimetype='application/json')

# Return the queried image
@app.route('/data/<string:patient_id>/jpg/<string:image>', methods=['GET'])
def show_image(patient_id, image):
    image_path = 'data/' + patient_id + '/jpg/' + image
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/jpg')


# serve static files
@app.route('/<path:path>')
def static_file(path):
    return app.send_static_file(path)


if __name__ == '__main__':
    app.static_folder = "varian/"
    app.run(host='0.0.0.0', debug=True, port=5000)
