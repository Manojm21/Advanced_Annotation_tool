from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import numpy as np
import cv2
# from PIL import Image


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
    if 'file' not in request.files:
        return render_template('index.html', error='No file part')

    file = request.files['file']
    if file.filename == '':
        return render_template('index.html', error='No selected file')

    if file:
        filename = file.filename
        image_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'images')  # Directory to save images
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        
        image_path = os.path.join(image_dir, filename)
        file.save(image_path)

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

        # Check if the file already exists
        if os.path.exists(save_path):
            # Read existing annotations to prevent duplicates
            with open(save_path, 'r') as f:
                existing_annotations = set(f.readlines())

            mode = 'a'  # Append mode
        else:
            mode = 'w'  # Write mode

        with open(save_path, mode) as f:
            if mode == 'a':
                # Check if annotation already exists, if yes, skip adding
                for annotation in annotations:
                    if annotation['width'] != 0 and annotation['height'] != 0:  # Check if width and height are not zero
                        bbox = f"{annotation['class']} {annotation['x']} {annotation['y']} {annotation['width']} {annotation['height']}\n"
                        if bbox not in existing_annotations:
                            f.write(bbox)
                            existing_annotations.add(bbox)
            else:
                for annotation in annotations:
                    if annotation['width'] != 0 and annotation['height'] != 0:  # Check if width and height are not zero
                        f.write(f"{annotation['class']} {annotation['x']} {annotation['y']} {annotation['width']} {annotation['height']}\n")

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
    
    image_path="static/uploads/images"+"/"+filename
    input_image = cv2.imread(image_path)  # Replace 'input_image.jpg' with the path to your input image
    print("before ROI")

    canvas_width = data.get('can_width')
    canvas_height = data.get('can_height')
    original_image_width = input_image.shape[1]
    original_image_height = input_image.shape[0]

# Calculate scaling factors
    scale_x = original_image_width / canvas_width
    scale_y = original_image_height / canvas_height

# Calculate offset
    offset_x = (canvas_width - original_image_width / scale_x) / 2
    offset_y = (canvas_height - original_image_height / scale_y) / 2

    transformation_matrix = np.array([
    [scale_x, 0, offset_x],
    [0, scale_y, offset_y],
    [0, 0, 1]
    ])

# Map coordinates
    def map_coordinates(x, y):
        mapped_coordinates = np.dot(transformation_matrix, [x, y, 1])
        original_x, original_y = mapped_coordinates[:2]  # Extract mapped coordinates
        return original_x, original_y
    
    def inverse_map_coordinates(original_x, original_y):
        canvas_x = original_x / scale_x + offset_x
        canvas_y = original_y / scale_y + offset_y
        return canvas_x, canvas_y


    x1, y1 = map_coordinates(x,y)
    x2, y2 = map_coordinates(x+width,y+height)
    roi = input_image[int(y1):int(y2), int(x1):int(x2)]
    cv2.imshow("mmssmll",roi)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    # roi.show()

    print("after ROI")
    # Perform template matching
    result = cv2.matchTemplate(input_image, roi, cv2.TM_CCOEFF_NORMED)

    def check_overlap(bbox, existing_bboxes):
        x1, y1, w1, h1 = map(int, bbox[1:])
        for existing_bbox in existing_bboxes:

            x2, y2, w2, h2 = map(int, existing_bbox[1:])
            if not (x1 >= x2 + w2 or
                    x1 + w1 <= x2 or
                    y1 >= y2 + h2 or
                    y1 + h1 <= y2):
                return True  # Overlapping bounding boxes found
        return False

    # Define a threshold for template matching result
    threshold = 0.9
    loc = np.where(result >= threshold)

    detected_bboxes = [[selected_class,int(x),int(y),width,height]]

    for i, pt in enumerate(zip(*loc[::-1])):  #need to edit here
        if i == 0:
            continue  # Skip the first bounding box
        can_x, can_y = inverse_map_coordinates(pt[0], pt[1])
        proposed_bbox = [selected_class, can_x, can_y, width, height]  # Adjust coordinates to the original image
        if not check_overlap(proposed_bbox, detected_bboxes):
            detected_bboxes.append(proposed_bbox)
    print(detected_bboxes[0])
    print(len(detected_bboxes))


   
    
    
    detected_bboxes_json = []
    for bbox in detected_bboxes:
        class_name, x, y, width, height = bbox
        bbox_json = {
            'class': str(class_name),  # Convert class_name to string
            'x': int(x),               # Convert x to integer
            'y': int(y),               # Convert y to integer
            'width': float(width),    # Convert width to float
            'height': float(height)   
        }
        detected_bboxes_json.append(bbox_json)

    return jsonify(detected_bboxes_json)
   

if __name__ == '__main__':
    app.run(debug=True)
