import os.path
import datetime
import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk, ImageDraw
import cv2
import face_recognition
from twilio.rest import Client


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
                    known_face_names.append(os.path.splitext(filename)[0])

                    # Extract mobile number from the filename (assuming it's stored in the filename)
                    # Change this logic based on your naming convention
                    mobile_number = filename.split('_')[0]
                    known_mobile_numbers.append(mobile_number)
                except IndexError:
                    print(f"Warning: No face found in {filename}")

        return known_face_encodings, known_face_names, known_mobile_numbers

    def log_attendance(self, name, mobile_number):
        if name != "Unknown":
            with open(self.log_path, 'a') as f:
                f.write('{}, {}, {}\n'.format(name, mobile_number, datetime.datetime.now()))
            self.send_sms_notification(name, mobile_number)

    def send_sms_notification(self, name, mobile_number):
        # Format the mobile number to E.164 format
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
        self.register_window = RegisterUserWindow(self.main_window)

    def capture_image_and_save(self, name, mobile_number):
        ret, frame = self.cap.read()
        # Adjust filename logic
        img_path = os.path.join(self.db_dir, f'{mobile_number}_{name}.jpg')
        cv2.imwrite(img_path, frame)
        with open(self.log_path, 'a') as f:
            f.write('{}, {}, {}\n'.format(name, mobile_number, datetime.datetime.now()))

    def start(self):
        self.main_window.mainloop()

class RegisterUserWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.geometry("500x300+500+200")
        self.title("Register New User")

        self.name_label = tk.Label(self, text="Enter Name:")
        self.name_label.pack(pady=20)

        self.name_entry = tk.Entry(self)
        self.name_entry.pack(pady=20)

        self.mobile_label = tk.Label(self, text="Enter Mobile Number:")
        self.mobile_label.pack(pady=20)

        self.mobile_entry = tk.Entry(self)
        self.mobile_entry.pack(pady=20)

        self.register_button = tk.Button(self, text="Register", command=self.register_user)
        self.register_button.pack(pady=20)

    def register_user(self):
        name = self.name_entry.get()
        mobile_number = self.mobile_entry.get()
        if name and mobile_number:
            app.capture_image_and_save(name, mobile_number)
            app.registered_users_count += 1
            msg = "Your seat is booked!" if app.registered_users_count <= App.MAX_BOOKED_SEATS else "Your seat is waiting. We have reached the maximum booked seats."
            simpledialog.messagebox.showinfo("Registration Message", msg)
            app.log_attendance(name, mobile_number)
            self.destroy()

if __name__ == "__main__":
    app = App()
    app.start()