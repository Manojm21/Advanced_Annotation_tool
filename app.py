from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import numpy as np
import cv2
# from PIL import Image


app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

file_class_map = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return render_template('index.html', error='No file part')
    file = request.files['file']
    if file.filename == '':
        return render_template('index.html', error='No selected file')

    if file:
        filename = file.filename
                
        images_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'images')
        # Ensure that the 'images' directory exists, create it if it doesn't
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        # Assuming filename is the name of the uploaded file
        file_path = os.path.join(images_folder, filename)


        file.save(file_path)

        return redirect(url_for('annotate_image', filename=filename))

    return render_template('index.html', error='Upload failed')

@app.route('/annotate/<filename>')
def annotate_image(filename):
    return render_template('annotate.html', filename=filename)


@app.route('/save_annotation', methods=['POST'])
def save_annotation():
    data = request.get_json()

    if data:
        filename = data['filename']
        annotations = data['annotations']
        
        labels_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'labels')  # Directory to save labels
        if not os.path.exists(labels_dir):
            os.makedirs(labels_dir)
        
        save_path = os.path.join(labels_dir, filename.split('.')[0] + '.txt')

        existing_bboxes = []  # List to store existing bounding boxes
        semi_existing_bboxes = [] 
        # Check if the file already exists and store existing bounding boxes
        if os.path.exists(save_path):
            with open(save_path, 'r') as f:
                for line in f:
                    bbox = list(map(float, line.strip().split()[1:]))
                    existing_bboxes.append(bbox)

        new_annotations = []

        # Check for duplicates within new annotations
        new_bbox_strs = set()
        for annotation in annotations:
            bbox_str = ' '.join(map(str, [annotation['x'], annotation['y'], annotation['width'], annotation['height']]))
            if bbox_str not in new_bbox_strs:
                new_bbox_strs.add(bbox_str)
                new_annotations.append(annotation)

        
        
        if not existing_bboxes:
            with open(save_path, 'w') as f:
                for annotation in new_annotations:
                    new_bbox = [annotation['x'], annotation['y'], annotation['width'], annotation['height']]
                    class_name = annotation['class']
                    overlap = False
                
                    for semi_existing_bbox in semi_existing_bboxes:
                        iou = calculate_iou(new_bbox, semi_existing_bbox)
                        if iou > 0.4:  # IOU threshold
                            overlap = True
                            break  # No need to check further if overlap is detected
                    if not overlap:
                        x, y, width, height = annotation['x'], annotation['y'], annotation['width'], annotation['height']
                        semi_bbox = [x, y, width, height]
                        semi_existing_bboxes.append(semi_bbox)
                        f.write(f"{class_name} {x} {y} {width} {height}\n")

        else:
            # Perform IOU check and add only non-duplicate new annotations
            with open(save_path, 'a') as f:
                for annotation in new_annotations:
                    x, y, width, height = annotation['x'], annotation['y'], annotation['width'], annotation['height']
                    new_bbox = [x, y, width, height]

                    # Check if the new bounding box overlaps with any existing bounding box
                    overlap = False
                    for existing_bbox in existing_bboxes:
                        iou = calculate_iou(new_bbox, existing_bbox)
                        if iou > 0.4:  # IOU threshold
                            overlap = True
                            break

                    if not overlap:
                        class_name = annotation['class']
                        new_bbox = [x, y, width, height]
                        existing_bboxes.append(new_bbox)
                        f.write(f"{class_name} {x} {y} {width} {height}\n")

        return jsonify({'success': True})

    return jsonify({'success': False})


@app.route('/annotate_rectangle', methods=['GET', 'POST'])
def annotate_rectangle():
    data = request.json
    selected_class = data.get('class')
    x, y, width, height = data.get('x'), data.get('y'), data.get('width'), data.get('height')
    filename = data.get('filename')

    image_path = "static/uploads" + "/" + filename
    input_image = cv2.imread(image_path)

    canvas_width = data.get('can_width')
    canvas_height = data.get('can_height')
    original_image_width = input_image.shape[1]
    original_image_height = input_image.shape[0]

    scale_x = original_image_width / canvas_width
    scale_y = original_image_height / canvas_height
    offset_x = (canvas_width - original_image_width / scale_x) / 2
    offset_y = (canvas_height - original_image_height / scale_y) / 2

    transformation_matrix = np.array([
        [scale_x, 0, offset_x],
        [0, scale_y, offset_y],
        [0, 0, 1]
    ])

    def map_coordinates(x, y):
        mapped_coordinates = np.dot(transformation_matrix, [x, y, 1])
        original_x, original_y = mapped_coordinates[:2]
        return original_x, original_y

    def inverse_map_coordinates(original_x, original_y):
        canvas_x = original_x / scale_x + offset_x
        canvas_y = original_y / scale_y + offset_y
        return canvas_x, canvas_y

    x1, y1 = map_coordinates(x, y)
    x2, y2 = map_coordinates(x + width, y + height)

    roi = input_image[int(y1):int(y2), int(x1):int(x2)]
    cv2.imshow("mmssmll", roi)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    # roi.show()

    result = cv2.matchTemplate(input_image, roi, cv2.TM_CCOEFF_NORMED)

    def check_overlap(bbox, existing_bboxes):
        x1, y1, w1, h1 = map(int, bbox[1:])
        for existing_bbox in existing_bboxes:
            x2, y2, w2, h2 = map(int, existing_bbox[1:])
            x2 = int(x2)
            y2 = int(y2)
            w2 = int(w2)
            h2 = int(h2)
            if not (x1 >= x2 + w2 or
                    x1 + w1 <= x2 or
                    y1 >= y2 + h2 or
                    y1 + h1 <= y2):
                return True
        return False

    threshold = 0.9
    loc = np.where(result >= threshold)

    detected_bboxes = [[selected_class, int(x), int(y), width, height]]
    for pt in zip(*loc[::-1]):
        can_x, can_y = inverse_map_coordinates(pt[0], pt[1])
        proposed_bbox = [selected_class, can_x, can_y, width, height]
        if not check_overlap(proposed_bbox, detected_bboxes):
            detected_bboxes.append(proposed_bbox)

    detected_bboxes_json = []
    for bbox in detected_bboxes:
        class_name, x, y, width, height = bbox
        bbox_json = {
            'class': str(class_name),
            'x': int(x),
            'y': int(y),
            'width': float(width),
            'height': float(height)
        }
        detected_bboxes_json.append(bbox_json)

    return jsonify(detected_bboxes_json)


def calculate_iou(bbox1, bbox2):
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2

    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    bbox1_area = w1 * h1
    bbox2_area = w2 * h2
    union_area = bbox1_area + bbox2_area - intersection_area
    iou = intersection_area / union_area

    return iou


if __name__ == '__main__':
    app.run(debug=True)
