import os
from flask import Flask, flash, request, Response, redirect, url_for, jsonify, send_file
# from werkzeug.utils import secure_filename
import time
import zipfile
import subprocess
import json
import pydicom
import os
import matplotlib.pyplot as plt
from io import BytesIO

# from PIL import Image, ImageDraw


# The base url from ngrok
# base_url = raw_input("Ngrok base url(http://<id>.ngrok.io): ")

# base_url = 'http://a6cb8bf4.ngrok.io'
# base_url = 'localhost:5000/'

UPLOAD_FOLDER = 'data/'
JPG_FOLDER = "varian/pictures/"
JPG_SERVE_FOLDER = "/pictures/"
ALLOWED_EXTENSIONS = {'dcm', 'jpg', 'zip'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def get_filename_and_ext(filename: str):
    dot_idx = filename.rfind(".")
    return (filename, "") if dot_idx is -1 else (filename[:dot_idx], filename[dot_idx + 1:])


def allowed_file_ext(ext: str) -> bool:
    return ext.lower() in ALLOWED_EXTENSIONS


def zip_extract(file):
    try:
        with zipfile.ZipFile(BytesIO(file)) as zip_ref:
            zip_ref.extractall(UPLOAD_FOLDER)
        return True
    except Exception as e:
        print(e)
        return False


def remove_directory(dir_path):
    if not os.path.exists(dir_path):
        return

    for f in os.listdir(dir_path):
        os.remove(dir_path + f)
    os.rmdir(dir_path)


def convert_file(idx, filename, in_path, out_path):
    with open(out_path + str(idx) + '.jpg', 'wb') as f:
        plt.imsave(f, pydicom.dcmread(in_path + filename).pixel_array)


def extract_patient_images(patient_id):
    patient_data_folder = UPLOAD_FOLDER + patient_id + "/"
    try:
        patient_files = os.listdir(patient_data_folder)
        if not patient_files:
            return False

        patient_jpg_folder = JPG_FOLDER + patient_id + "/"
        remove_directory(patient_jpg_folder)
        os.mkdir(patient_jpg_folder)

        mr_files = list(filter(lambda x: x.split(".")[0] == "MR", patient_files))
        for idx, f in enumerate(mr_files):
            convert_file(idx, f, patient_data_folder, patient_jpg_folder)

    except Exception as e:
        print(e)
        return False

    finally:
        remove_directory(patient_data_folder)

    return True


def get_images_by_patient(patient_id: str):
    if patient_id[-1] != "/":
        patient_id += "/"

    folder = JPG_FOLDER + patient_id
    if not os.path.exists(folder):
        return []
    return list(map(lambda x: JPG_SERVE_FOLDER + patient_id + x, os.listdir(folder)))


def jsonify_images(img_vector):
    return json.dumps(list(map(lambda x: {'frame': x, 'score': '0.98'}, img_vector)))


@app.route("/upload", methods=['POST'])
def upload_data():
    # check if the post request has the file part
    if 'file' not in request.files:
        # return redirect(request.url)
        pass

    file = request.files.get('file', False)
    if not file or not file.filename:
        return "No selected file", 400

    name, ext = get_filename_and_ext(file.filename)
    if not allowed_file_ext(ext):
        return 'File extension "{}" not allowed'.format(ext), 400

    if not zip_extract(file.read()):
        return "Failed to extract .zip file", 400

    # Extract images and return image url list
    if not extract_patient_images(name):
        return 'Failed to extract patient images', 500

    return redirect("/userData.html?id=" + name)


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


@app.route('/userData/<string:patient_id>')
def get_user_data(patient_id):
    return Response(jsonify_images(get_images_by_patient(patient_id)), mimetype='application/json')


# serve static files
@app.route('/<path:path>')
def serve_static(path):
    return app.send_static_file(path)


# serve index.html
@app.route("/")
def root():
    return app.send_static_file("index.html")


if __name__ == '__main__':
    app.static_folder = "varian/"

    if not os.path.exists(JPG_FOLDER):
        os.mkdir(JPG_FOLDER)

    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)

    app.run(host='0.0.0.0', debug=True, port=5000)
