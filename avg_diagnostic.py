from camera_detect import run_detect, load_graph
import cv2
import numpy as np
import tensorflow as tf

cap = cv2.VideoCapture('/dev/camera')
print("Loading pre-trained model...")
detection_graph = load_graph()
sess = tf.Session(graph=detection_graph)
run_detect(cap, sess, 1)
print("Detection model loaded!")

for i in range(100):
    print("Step" + str(i))
    result = run_detect(cap, sess, 5)   # 5 samples 
    x.append(result[0])

cap.release()
sess.close()

y = np.array(x)
mean = np.mean(y)
var = np.var(y)
print("Mean: " + str(mean))
print("Variance: " + str(var))
