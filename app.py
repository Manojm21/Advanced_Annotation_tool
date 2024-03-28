from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import numpy as np
import cv2

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Map to store filename and class name
file_class_map = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    print("in the upload")
    if 'file' not in request.files:
        return render_template('index.html', error='No file part')
    print("in the upload1")
    file = request.files['file']
    if file.filename == '':
        return render_template('index.html', error='No selected file')

    # class_name = request.form['class_name']

    if file:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Store the mapping of filename to class name
        # file_class_map[filename] = class_name

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
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.split('.')[0] + '.txt')

        with open(save_path, 'w') as f:
            for annotation in annotations:
                class_name = annotation['class']
                x, y, width, height = annotation['x'], annotation['y'], annotation['width'], annotation['height']
                f.write(f"{class_name} {x} {y} {width} {height}\n")

        return jsonify({'success': True})

    return jsonify({'success': False})



@app.route('/annotate_rectangle', methods=['GET','POST'])
def annotate_rectangle():
    data = request.json  # Get JSON data from the request body
    selected_class = data.get('class')  # Get the class of the selected rectangle
    x, y, width, height = data.get('x'), data.get('y'), data.get('width'), data.get('height')  # Get the coordinates of the selected rectangle
    filename=data.get('filename')
    print("file name done")
    print(filename)
    # Load input image
    
    image_path="static/uploads"+"/"+filename
    input_image = cv2.imread(image_path)  # Replace 'input_image.jpg' with the path to your input image
    print("before ROI")

    canvas_width = 700
    canvas_height = 500
    original_image_width = input_image.shape[1]
    original_image_height = input_image.shape[0]

# Calculate scaling factors
    scale_x = original_image_width / canvas_width
    scale_y = original_image_height / canvas_height

# Calculate offset
    offset_x = (canvas_width - original_image_width / scale_x) / 2
    offset_y = (canvas_height - original_image_height / scale_y) / 2

# Map coordinates
    def map_coordinates(x, y):
        original_x = (x - offset_x) * scale_x
        original_y = (y - offset_y) * scale_y
        return original_x, original_y
    
    def inverse_map_coordinates(original_x, original_y):
        canvas_x = original_x / scale_x + offset_x
        canvas_y = original_y / scale_y + offset_y
        return canvas_x, canvas_y

# Example usage
    x1, y1 = map_coordinates(x,y)
    x2, y2 = map_coordinates(x+width,y+height)

    # Extract region of interest (ROI) from the input image
    # roi = input_image[int(y):int(y)+int(height), int(x):int(x)+int(width)]
    roi = input_image[int(y1):int(y2), int(x1):int(x2)]
    cv2.imshow("mmssmll",roi)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print("after ROI")
    # Perform template matching
    result = cv2.matchTemplate(input_image, roi, cv2.TM_CCOEFF_NORMED)

    # Define a threshold for template matching result
    threshold = 0.85
    loc = np.where(result >= threshold)



    def get_iou(box1, box2):
    # Extract coordinates
        _,x1a, y1a, x2a, y2a = box1
        _,x1b, y1b, x2b, y2b = box2
        # Calculate area of each box
        area_a = (x2a - x1a) * (y2a - y1a)
        area_b = (x2b - x1b) * (y2b - y1b)

        # Calculate intersection area
        intersection_x1 = max(x1a, x1b)
        intersection_y1 = max(y1a, y1b)
        intersection_x2 = min(x2a, x2b)
        intersection_y2 = min(y2a, y2b)
        intersection_area = (intersection_x2 - intersection_x1) * (intersection_y2 - intersection_y1)

        # Handle cases where boxes don't overlap
        if intersection_area <= 0:
           return 0
        # Calculate IoU
        iou = intersection_area / (area_a + area_b - intersection_area)
        return iou



    # Extract bounding box coordinates of detected instances
    detected_bboxes = []
    detected_bboxes.append((selected_class,x, y, width, height))
    for pt in zip(*loc[::-1]):
        can_x, can_y = inverse_map_coordinates(pt[0], pt[1])
        is_overlapping = False
        for existing_box in detected_bboxes:
            if existing_box == (selected_class, x, y, width, height):  # Skip the selected box
                continue
            iou = get_iou((selected_class, can_x, can_y, width, height), existing_box)
            if iou > 0.1:  # Adjust threshold for IoU (0 to 1)
                is_overlapping = True
                break

        if not is_overlapping:
            detected_bboxes.append((selected_class, can_x, can_y, width, height))

    print(detected_bboxes[0])
    print(len(detected_bboxes))
    
    
    # Check if any duplicate boxes are present
    unique_detected_bboxes = []
    for bbox in detected_bboxes:
        if bbox not in unique_detected_bboxes:
            unique_detected_bboxes.append(bbox)
    
    detected_bboxes_json = []
    for bbox in unique_detected_bboxes:
        class_name, x, y, width, height = bbox
        bbox_json = {
            'class': str(class_name),  # Convert class_name to string
            'x': int(x),               # Convert x to integer
            'y': int(y),               # Convert y to integer
            'width': float(width),    # Convert width to float
            'height': float(height)   
        }
        detected_bboxes_json.append(bbox_json)

    # save_annotation(detected_bboxes_json)

    return jsonify(detected_bboxes_json)
 
if __name__ == '__main__':
    app.run(debug=True)
