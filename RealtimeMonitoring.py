import os.path
import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import cv2
import face_recognition  # Add this line
from twilio.rest import Client
import qrcode
import numpy as np
from pyzbar.pyzbar import decode


class App:
    MAX_BOOKED_SEATS = 3
    TWILIO_SID = 'ACec004b11f65670e2e51f189ed9f5f023'
    TWILIO_AUTH_TOKEN = 'cda9503865977d5f96eace0f414647c6'
    TWILIO_PHONE_NUMBER = '+12069664675'

    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.geometry("1200x600+350+100")
        self.main_window.title("Face Recognition Attendance System")

        background_image = Image.open("background_image.png")
        background_photo = ImageTk.PhotoImage(background_image)
        self.background_label = tk.Label(self.main_window, image=background_photo)
        self.background_label.image = background_photo
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.webcam_label = self.get_img_label(self.main_window)
        self.webcam_label.place(x=68, y=38, width=530, height=424)

        self.status_label = self.get_status_label(self.main_window)
        self.status_label.place(x=800, y=530)

        self.db_dir = './db'
        if not os.path.exists(self.db_dir):
            os.mkdir(self.db_dir)

        self.qr_codes_dir = './qr_codes'
        if not os.path.exists(self.qr_codes_dir):
            os.mkdir(self.qr_codes_dir)

        self.log_path = './log.txt'

        self.face_recognition_active = False
        self.face_recognition_interval = 5
        self.frame_count = 0
        self.recognized_set = set()

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 530)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 424)

        self.update_webcam_feed()

        self.registered_users_count = 0

        self.register_new_user_button_main_window = self.get_button(self.main_window, 'Register New User', 'gray',
                                                                    self.register_new_user, fg='black', width=30, height=3)
        self.register_new_user_button_main_window.place(x=700, y=450)

        self.take_attendance_button_main_window = self.get_button(self.main_window, 'Take Attendance', 'green',
                                                                   self.toggle_continuous_recognition, fg='black', width=30, height=3)
        self.take_attendance_button_main_window.place(x=950, y=450)

        self.scan_qr_code_button_main_window = self.get_button(self.main_window, 'Scan QR Code', 'blue',
                                                        self.scan_qr_code, fg='black', width=30, height=3)
        self.scan_qr_code_button_main_window.place(x=850, y=380)

    def update_webcam_feed(self):
        ret, frame = self.cap.read()
        if ret:
            most_recent_capture_arr = frame
            img_ = cv2.cvtColor(most_recent_capture_arr, cv2.COLOR_BGR2RGB)
            most_recent_capture_pil = Image.fromarray(img_)
            imgtk = ImageTk.PhotoImage(image=most_recent_capture_pil)

            self.webcam_label.imgtk = imgtk
            self.webcam_label.configure(image=imgtk)

            if self.face_recognition_active:
                if self.frame_count % self.face_recognition_interval == 0:
                    recognized_name = self.recognize_and_mark_attendance(most_recent_capture_arr)
                    self.overlay_text_on_image(most_recent_capture_pil, recognized_name)

            self.frame_count += 1

        self.main_window.after(20, self.update_webcam_feed)

    def recognize_and_mark_attendance(self, frame):
        known_face_encodings, known_face_names, known_mobile_numbers = self.load_known_faces()

        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        recognized_name = "Unknown"

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)

            for i, match in enumerate(matches):
                if match:
                    recognized_name = known_face_names[i]
                    mobile_number = known_mobile_numbers[i]

                    if recognized_name not in self.recognized_set:
                        self.status_label.config(text=f"Marked attendance: {recognized_name}")
                        self.log_attendance(recognized_name, mobile_number)
                        self.recognized_set.add(recognized_name)

        return recognized_name

    def load_known_faces(self):
        known_face_encodings = []
        known_face_names = []
        known_mobile_numbers = []

        for filename in os.listdir(self.db_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(self.db_dir, filename)
                try:
                    face_encoding = face_recognition.face_encodings(face_recognition.load_image_file(img_path))[0]
                    known_face_encodings.append(face_encoding)

                    mobile_number = os.path.splitext(filename)[0]
                    known_mobile_numbers.append(mobile_number)

                    with open(os.path.join(self.db_dir, f'{mobile_number}.txt')) as user_info_file:
                        for line in user_info_file:
                            if line.startswith('Name:'):
                                known_face_names.append(line.split(': ')[1].strip())
                                break
                except IndexError:
                    print(f"Warning: No face found in {filename}")

        return known_face_encodings, known_face_names, known_mobile_numbers

    def log_attendance(self, name, mobile_number):
        if name != "Unknown":
            with open(self.log_path, 'a') as f:
                f.write('{}, {}, {}\n'.format(name, mobile_number, datetime.datetime.now()))
            self.send_sms_notification(name, mobile_number)

    def send_sms_notification(self, name, mobile_number):
        formatted_mobile_number = f"+91{mobile_number}"

        client = Client(App.TWILIO_SID, App.TWILIO_AUTH_TOKEN)

        try:
            message = client.messages.create(
                to=formatted_mobile_number,
                from_=App.TWILIO_PHONE_NUMBER,
                body=f"Attendance marked for {name} at {datetime.datetime.now()}"
            )
            print(f"SMS sent to {formatted_mobile_number}")
        except Exception as e:
            print(f"Error sending SMS: {e}")

    def overlay_text_on_image(self, pil_image, text):
        draw = ImageDraw.Draw(pil_image)
        draw.text((10, 10), f"Recognized: {text}", fill="white")

    def toggle_continuous_recognition(self):
        self.face_recognition_active = not self.face_recognition_active
        if not self.face_recognition_active:
            self.recognized_set.clear()

    def get_img_label(self, window):
        return tk.Label(window)

    def get_status_label(self, window):
        return tk.Label(window, text="", font=("Helvetica", 16))

    def get_button(self, window, text, bg, command, fg=None, width=None, height=None):
        return tk.Button(window, text=text, bg=bg, command=command, fg=fg, width=width, height=height)

    def register_new_user(self):
        name = simpledialog.askstring("Register New User", "Enter the user's name:")
        if name:
            mobile_number = simpledialog.askstring("Register New User", "Enter the user's mobile number:")
            if mobile_number:
                self.capture_image_and_save(name, mobile_number)
                qr_code = self.generate_qr_code(name, mobile_number)
                self.show_qr_code_window(qr_code)
                self.registered_users_count += 1
                msg = "Your seat is booked!" if self.registered_users_count <= App.MAX_BOOKED_SEATS else "Your seat is waiting. We have reached the maximum booked seats."
                simpledialog.messagebox.showinfo("Registration Message", msg)
                self.log_attendance(name, mobile_number)

    def scan_qr_code(self):
        ret, frame = self.cap.read()
        qr_code_data, bbox, qr_code_frame = self.detect_qr_code(frame)

        if qr_code_data:
            recognized_name = self.recognize_user_from_qr_code(qr_code_data)
            if recognized_name:
                self.status_label.config(text=f"Scanned QR Code: {recognized_name}")
            else:
                self.status_label.config(text="User not recognized")
        else:
            self.status_label.config(text="QR Code not detected")

        imgtk = ImageTk.PhotoImage(image=Image.fromarray(qr_code_frame))
        self.webcam_label.imgtk = imgtk
        self.webcam_label.configure(image=imgtk)

        self.main_window.after(20, self.scan_qr_code)  # Continue scanning


    def recognize_user_from_qr_code(self, qr_code_data):
        known_face_names, known_mobile_numbers = self.load_known_users()

        for i, mobile_number in enumerate(known_mobile_numbers):
            if f"Mobile Number: {mobile_number}" == qr_code_data:
                recognized_name = known_face_names[i]
                mobile_number = known_mobile_numbers[i]

                if recognized_name not in self.recognized_set:
                    self.status_label.config(text=f"Marked attendance: {recognized_name}")
                    self.log_attendance(recognized_name, mobile_number)
                    self.recognized_set.add(recognized_name)

                return recognized_name

        return None

    def load_known_users(self):
        known_face_names = []
        known_mobile_numbers = []

        for filename in os.listdir(self.db_dir):
            if filename.lower().endswith('.txt'):
                user_info_path = os.path.join(self.db_dir, filename)
                with open(user_info_path, 'r') as user_info_file:
                    for line in user_info_file:
                        if line.startswith('Name:'):
                            known_face_names.append(line.split(': ')[1].strip())
                        elif line.startswith('Mobile Number:'):
                            known_mobile_numbers.append(line.split(': ')[1].strip())

        return known_face_names, known_mobile_numbers

    def detect_qr_code(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Use pyzbar to detect QR codes
        decoded_objects = decode(frame)

        for obj in decoded_objects:
            qr_code_data = obj.data.decode('utf-8')
            bbox = obj.polygon

            # Draw the bounding box around the QR code
            if len(bbox) == 4:
                cv2.polylines(frame, [np.array(bbox)], True, (0, 255, 0), 2)

            return qr_code_data, bbox, frame

        return None, None, frame

    def generate_qr_code(self, name, mobile_number):
        qr_data = f"Mobile Number: {mobile_number}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        qr_code_image_path = os.path.join(self.qr_codes_dir, f'{name}_{mobile_number}_qr.png')
        img.save(qr_code_image_path)

        qr_code_image = ImageTk.PhotoImage(Image.open(qr_code_image_path))

        return qr_code_image

    def show_qr_code_window(self, qr_code):
        qr_code_window = tk.Toplevel(self.main_window)
        qr_code_window.title("QR Code")
        qr_label = tk.Label(qr_code_window, image=qr_code)
        qr_label.image = qr_code
        qr_label.pack()

    def capture_image_and_save(self, name, mobile_number):
        ret, frame = self.cap.read()
        img_path = os.path.join(self.db_dir, f'{name}.jpg')
        cv2.imwrite(img_path, frame)
        user_info_path = os.path.join(self.db_dir, f'{name}.txt')
        with open(user_info_path, 'w') as user_info_file:
            user_info_file.write('Name: {}\n'.format(name))
            user_info_file.write('Mobile Number: {}\n'.format(mobile_number))
            user_info_file.write('Timestamp: {}\n'.format(datetime.datetime.now()))
        with open(self.log_path, 'a') as f:
            f.write('{}, {}, {}\n'.format(name, mobile_number, datetime.datetime.now()))

    def start(self):
        self.main_window.mainloop()

if __name__ == "__main__":
    app = App()
    app.start()
