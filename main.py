import pymongo
import datetime
import cv2
import threading
from deepface import DeepFace
import queue
import certifi

MONGODB_URI = "mongodb+srv://sysadmin:kraFY1B9omw619ik@attendance-system.cumins2.mongodb.net/?retryWrites=true&w=majority&appName=attendance-system"
client = pymongo.MongoClient(MONGODB_URI, tls=True, tlsAllowInvalidCertificates=True, tlsCAFile=certifi.where())
db = client["attendance_db"] 
attendance_collection = db["attendance"]
students_collection = db["students"]

try:
    result = client.admin.command('ismaster')
    print("Connected to MongoDB!")
except Exception as e:
    print(f"An error occurred: {e}")

frame_queue = queue.Queue(maxsize=1)

reference_imgs = [
    cv2.imread("reference.png"),
    cv2.imread("reference2.png"),
    cv2.imread("reference3.png")
]

face_match = False

def check_face():
    global face_match
    while True:
        frame = frame_queue.get()
        try:
            face_match = any(DeepFace.verify(frame, ref_img.copy())['verified'] for ref_img in reference_imgs)
        except ValueError:
            face_match = False

threading.Thread(target=check_face, daemon=True).start()

def mark_attendance(student_name):
    now = datetime.datetime.now()
    today = now.date()

    if 7 <= now.hour < 9:
        lecture_number = 1
    elif 9 <= now.hour < 11:
        lecture_number = 2
    else:
        lecture_number = 0 

    student_exists = students_collection.find_one({"student_name": student_name})

    if student_exists is None:
        print(f"Student '{student_name}' not found. Please add them to the student list.")
    else:
        existing_record = attendance_collection.find_one({
            "student_name": student_name,
            "lecture_number": lecture_number, 
            "date": today.isoformat()
        })

        if existing_record is None:
            attendance_document = {
                "student_name": student_name,
                "lecture_number": lecture_number, 
                "date": today.isoformat(),
                "time": now.time().isoformat()
            }
            attendance_collection.insert_one(attendance_document)
            print(f"Attendance marked for {student_name}, lecture {lecture_number}")
        else:
            print("Student already marked present for this lecture today")

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if ret:
        try:
            frame_queue.put_nowait(frame.copy())
        except queue.Full:
            pass

        if face_match:
            cv2.putText(frame, "Recognized", (20, 450), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
            mark_attendance("student1") 
            face_match = False  
        else:
            cv2.putText(frame, "Unknown", (20, 450), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)

        cv2.imshow('video', frame)

    key = cv2.waitKey(1)
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
