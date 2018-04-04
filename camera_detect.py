import numpy as np
import os
import sys
import tensorflow as tf
import datetime
import cv2

from PIL import Image
from utils import label_map_util

# Load variables
MODEL_NAME = 'ssd_mobilenet_v1Graph'

# Path to frozen detection graph. This is the actual model that is used for the object detection.
PATH_TO_CKPT = MODEL_NAME + '/frozen_inference_graph.pb'

# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = os.path.join('data', 'object-detect.pbtxt')

# Image directory
IMG_DIR = 'data'

# Only 1 class label
NUM_CLASSES = 1

WIDTH = 640
HEIGHT = 480

# Visual sizes
CHARGER_WIDTH = 67. # Units in mm
CHARGER_HEIGHT = 95.5
FOCAL_DISTANCE = 533. # Units in pixels

# Only give trigger when confidence is over 90%
DETECTION_THRESHOLD = 0.9;

# End conditions for tracking loop (tolerances in mm)
X_TOLERANCE = 1.
Z_TOLERANCE = 1.
Y_TOLERANCE = 5.
DIST_THRESHOLD = 125.
ASPECT_RATIO = CHARGER_HEIGHT / CHARGER_WIDTH
AR_THRESHOLD = 0.25 # Triggers aspect ratio correction at 5% deviation

def load_graph():
    # Load frozen inference graph
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')

    label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
    categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
    category_index = label_map_util.create_category_index(categories)
    return detection_graph

def load_image_into_numpy_array(image):
  (im_width, im_height) = image.size
  return np.array(image.getdata()).reshape(
      (im_height, im_width, 3)).astype(np.uint8)

def check_aspect_ratio(ymin, xmin, ymax, xmax):
    ar_height = ymax - ymin
    ar_width = xmax - xmin
    ar = ar_height / ar_width
    if (ar < (1-AR_THRESHOLD) * ASPECT_RATIO) or (ar > (1+AR_THRESHOLD) * ASPECT_RATIO):
        return False
    else:
        return True

def get_loc_and_size(boxes, scores, width, height):
    if (boxes is not None) and (scores is not None):    # Sanity check to ensure we actually have results!
        for i in range(boxes.shape[0]):
            if scores[0][i] > DETECTION_THRESHOLD:
                ymin, xmin, ymax, xmax = tuple(boxes[0][i].tolist())   # Extract box definition
                ymin *= HEIGHT
                ymax *= HEIGHT
                xmin *= WIDTH
                xmax *= WIDTH
                ar_correct = check_aspect_ratio(ymin, xmin, ymax, xmax)

                low = np.array((xmin, ymin))             # Bottom left coodinate array
                high = np.array((xmax, ymax))            # Top right coordinate array
                center = (high + low) / 2                   # Calculate the center point
                apparentWidth = np.abs(xmax-xmin)     # Calculate the distance between high and low
                return center, apparentWidth, ar_correct
            else:
                return -1, -1, False
    else:
        return -1, -1, False
        print('No boxes or scores detected!')


def array2PIL(arr, size):
    mode = 'RGBA'
    arr = arr.reshape(arr.shape[0]*arr.shape[1], arr.shape[2])
    if len(arr[0]) == 3:
        arr = numpy.c_[arr, 255*numpy.ones((len(arr),1), numpy.uint8)]
    return Image.frombuffer(mode, size, arr.tostring(), 'raw', mode, 0, 1)

def calc_real_size(apparent_size):
    return FOCAL_DISTANCE * CHARGER_WIDTH / apparent_size

def calc_corrections(center, d, w, h):
    return (center[0] - w/2) * d / FOCAL_DISTANCE, (center[1] - h/2) * d / FOCAL_DISTANCE

def get_error_str(num):
    retStr = '  REASON: '
    if(num == -1):
        return retStr + 'Could not open camera stream\n'
    elif num == -2:
        return retStr + 'Camera could not capture frame\n'
    elif num == -3:
        return retStr + 'Target was not detected in frame\n'
    elif num == -4:
        return retStr + 'Target location out of frame\n'

def run_detect(cap, sess, avg_filter):
    dist = 0
    x_corr = 0
    z_corr = 0

    for i in range(avg_filter):
        if not cap.isOpened():
            return [-1]

        # Definite input and output Tensors for detection_graph
        image_tensor = sess.graph.get_tensor_by_name('image_tensor:0')
        # Each box represents a part of the image where a particular object was detected.
        detection_boxes = sess.graph.get_tensor_by_name('detection_boxes:0')
        # Each score represent how level of confidence for each of the objects.
        # Score is shown on the result image, together with the class label.
        detection_scores = sess.graph.get_tensor_by_name('detection_scores:0')
        # detection_classes = detection_graph.get_tensor_by_name('detection_classes:0')
        # num_detections = detection_graph.get_tensor_by_name('num_detections:0')

        # cv2.VideoCapture has 5 frame buffer; clear this to get the most recent frame!
        for j in range(5):
            cap.grab()

        # Grab a single frame from camera
        ret, frame = cap.retrieve()
        if not ret:
            return [-2]

        # Convert color encoding
        imageArr = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
        image_np_expanded = np.expand_dims(imageArr, axis=0)
        # Actual detection.
        (boxes, scores) = sess.run(
          [detection_boxes, detection_scores],
          feed_dict={image_tensor: image_np_expanded})
        center, size, ar_correct = get_loc_and_size(boxes, scores, WIDTH, HEIGHT)
        # Visualization of the results of a detection.
        if size > 0:
            if i == (avg_filter):
                cv2.line(imageArr, (0, int(center[1])), (WIDTH, int(center[1])), (0,255,0), 2)
                cv2.line(imageArr, (int(center[0]), 0), (int(center[0]), HEIGHT), (0,255,0), 2)
                cv2.imwrite('./img/current.jpg' , cv2.cvtColor(imageArr, cv2.COLOR_RGB2BGR))

            if(ar_correct):
                # Aspect ratio is correct, charger fully in sight
                temp_dist = calc_real_size(size)
                temp_x_corr, temp_z_corr = calc_corrections(center, temp_dist, WIDTH, HEIGHT)

                dist += temp_dist
                x_corr += (-temp_x_corr)
                z_corr += (-temp_z_corr)
            else:
                # Aspect ratio incorrect, charger partially obscured
                return [-4]

        else:
            return [-3]

    x_corr = x_corr/ avg_filter
    dist = dist / avg_filter
    z_corr = z_corr/ avg_filter
    y_corr = dist-DIST_THRESHOLD

    if np.abs(x_corr) <= X_TOLERANCE and np.abs(z_corr) <= Z_TOLERANCE and np.abs(y_corr) < Y_TOLERANCE:
        x_corr = 0.0
        z_corr = 0.0
        y_corr = 0.0

    return [dist, x_corr, z_corr, y_corr, ar_correct]
