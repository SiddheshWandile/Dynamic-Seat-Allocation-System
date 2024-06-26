import os.path
import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import cv2
import face_recognition
import qrcode
import numpy as np
from pyzbar.pyzbar import decode
import json

class RegisterUserWindow:
    MAX_WAITING_LIST_USERS = 2
    def __init__(self, app_instance, is_waiting_list=False):
        self.app_instance = app_instance
        self.parent = app_instance.main_window
        self.register_user_window = tk.Toplevel(self.parent)
        self.register_user_window.title("Register New User")
        self.register_user_window.geometry("300x300")
        self.name_label = tk.Label(self.register_user_window, text="Enter the user's name:")
        self.name_label.pack(pady=10)
        self.name_entry = tk.Entry(self.register_user_window)
        self.name_entry.pack(pady=10)
        self.mobile_label = tk.Label(self.register_user_window, text="Enter the user's mobile number:")
        self.mobile_label.pack(pady=10)
        self.mobile_entry = tk.Entry(self.register_user_window)
        self.mobile_entry.pack(pady=10)
        self.register_button = tk.Button(self.register_user_window, text="Register", command=self.register_user)
        self.register_button.pack(pady=20)
        self.is_waiting_list = is_waiting_list

    def register_user(self):
        name = self.name_entry.get().strip()
        mobile_number = self.mobile_entry.get().strip()

        if name and mobile_number:
            if self.app_instance.wait_counter >= RegisterUserWindow.MAX_WAITING_LIST_USERS:
                messagebox.showerror("Train Full", "Train is full! No more bookings available.")
                self.register_user_window.destroy()
                return

            seat_number = self.app_instance.get_next_seat_number()
            
            self.app_instance.capture_image_and_save(name, mobile_number, seat_number, self.is_waiting_list)

            if not self.is_waiting_list:
                qr_code = self.app_instance.generate_qr_code(name, mobile_number)

            self.app_instance.registered_users_count += 1

            if not self.is_waiting_list:
                msg = f"Your seat is booked! Seat No: {seat_number}"
                self.app_instance.log_attendance(name, mobile_number, seat_number, self.is_waiting_list)
            else:
                wating_seat = self.app_instance.get_next_waitseat_number()
                msg = f"Your are Register in Wating List! Watting Number: {wating_seat}" 
                self.app_instance.log_attendance(name, mobile_number, -wating_seat, self.is_waiting_list)

            simpledialog.messagebox.showinfo("Registration Message", msg)
            
            self.register_user_window.destroy()
        else:
            messagebox.showerror("Error", "Please enter both name and mobile number.")

class App:
    MAX_BOOKED_SEATS = 2

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
        self.attendance_status_path = './attendance_status.json'

        self.face_recognition_active = False
        self.face_recognition_interval = 5
        self.frame_count = 0
        self.recognized_set = set()

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 530)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 424)

        self.update_webcam_feed()

        self.registered_users_count = 0

        self.register_user_window = None

        self.register_new_user_button_main_window = self.get_button(self.main_window, 'Register New User', 'gray',
                                                                    self.register_new_user, fg='black', width=30, height=3)
        self.register_new_user_button_main_window.place(x=700, y=450)

        self.take_attendance_button_main_window = self.get_button(self.main_window, 'Take Attendance', 'green',
                                                                   self.toggle_continuous_recognition, fg='black', width=30, height=3)
        self.take_attendance_button_main_window.place(x=950, y=450)

        self.scan_qr_code_button_main_window = self.get_button(self.main_window, 'Scan QR Code', 'blue',
                                                               self.scan_qr_code_method, fg='black', width=30, height=3)
        self.scan_qr_code_button_main_window.place(x=950, y=380)

        self.wait_button_main_window = self.get_button(self.main_window, 'Status Update', 'orange', self.send_whatsapp_poll,
                                                       fg='black', width=30, height=3)
        self.wait_button_main_window.place(x=700, y=380)

        self.seat_counter = 0
        self.wait_counter = 0

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
        known_face_encodings, known_face_names, known_mobile_numbers, is_waiting_list = self.load_known_faces()

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

                        # Use existing seat number from attendance status
                        attendance_status = self.load_attendance_status()
                        seat_number = attendance_status[recognized_name]["seat_number"]

                        self.log_attendance(recognized_name, mobile_number, seat_number,    is_waiting_list[i])
                        self.recognized_set.add(recognized_name)

                        # Update attendance status to mark as present
                        attendance_status[recognized_name]["marked_present"] = True
                        self.save_attendance_status(attendance_status)

                    return recognized_name

        return recognized_name

    def load_known_faces(self):
        known_face_encodings = []
        known_face_names = []
        known_mobile_numbers = []
        is_waiting_list = []

        for filename in os.listdir(self.db_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(self.db_dir, filename)
                try:
                    face_encoding = face_recognition.face_encodings(face_recognition.load_image_file(img_path))[0]
                    known_face_encodings.append(face_encoding)

                    name = os.path.splitext(filename)[0]
                    known_mobile_numbers.append(name)

                    user_info_path = os.path.join(self.db_dir, f'{name}.json')
                    with open(user_info_path, 'r') as user_info_file:
                        user_data = json.load(user_info_file)
                        known_face_names.append(user_data["name"])
                        is_waiting_list.append(user_data.get("is_waiting_list", False))
                except IndexError:
                    print(f"Warning: No face found in {filename}")

        return known_face_encodings, known_face_names, known_mobile_numbers, is_waiting_list

    def log_attendance(self, name, mobile_number, seat_number, is_waiting_list=False):
        if name != "Unknown":
            log_path = self.log_path if not is_waiting_list else './waiting_list_log.txt'
            with open(log_path, 'a') as f:
                f.write('{}, {}, {}, {}, {}\n'.format(name, mobile_number, seat_number, is_waiting_list, datetime.datetime.now()))

            # Update attendance status JSON file
            attendance_status = self.load_attendance_status()
            if name in attendance_status:
                if not is_waiting_list and not attendance_status[name]["marked_present"]:
                    # Set to True only if not in waiting list and not already marked as present
                    attendance_status[name]["marked_present"] = True
                    attendance_status[name]["seat_number"] = seat_number
                    attendance_status[name]["is_waiting_list"] = is_waiting_list
            else:
                attendance_status[name] = {"marked_present": False, "seat_number": seat_number, "is_waiting_list": is_waiting_list}
            self.save_attendance_status(attendance_status)

    def load_attendance_status(self):
        if os.path.exists(self.attendance_status_path):
            with open(self.attendance_status_path, 'r') as json_file:
                try:
                    attendance_status = json.load(json_file)
                except json.decoder.JSONDecodeError:
                    attendance_status = {}
        else:
            attendance_status = {}

        return attendance_status

    def save_attendance_status(self, attendance_status):
        with open(self.attendance_status_path, 'w') as json_file:
            json.dump(attendance_status, json_file)

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
        if self.registered_users_count < App.MAX_BOOKED_SEATS:
            self.register_user_window = RegisterUserWindow(self)
        else:
            response = messagebox.askyesno("Train Full", "Train is full! Do you want to book a ticket in waiting?")
            if response:
                self.register_user_window = RegisterUserWindow(self, is_waiting_list=True)
            else:
                response = messagebox.askquestion("Train Full", "No more bookings available. Do you want to go back and try again?")
                if response == 'yes':
                    self.register_new_user()  # Call the method to go back and try again
                
    def get_next_seat_number(self, is_waiting_list = False):
        if not is_waiting_list:
            self.seat_counter += 1
            return self.seat_counter
            
    def get_next_waitseat_number(self, is_waiting_list = True):  
        if is_waiting_list:
            self.wait_counter += 1
            return self.wait_counter

    def scan_qr_code_method(self):
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

        self.main_window.after(20, self.scan_qr_code_method)

    def send_whatsapp_poll(self):
        # Load attendance status from the JSON file
        attendance_status = self.load_attendance_status()
        seatNum = 0
        # Check for users who are not marked present and not in the waiting list
        users_to_remove = []
        for user_name, user_data in attendance_status.items():
            if not user_data["marked_present"] and not user_data["is_waiting_list"]:
                # Ask the user if they have boarded the train
                response = messagebox.askyesno("Boarding Confirmation", f"Have you boarded the train, {user_name}?")
                seatNum = user_data["seat_number"]
    
                if response:
                    # If user clicks 'Yes', update the attendance status and display a message
                    user_data["marked_present"] = True
                    self.save_attendance_status(attendance_status)
                    seat_number = user_data["seat_number"]
                    messagebox.showinfo("Seat Booked", f"Your seat ({seat_number}) is booked, {user_name}!")
                    return
                else:
                    # Add user data to the list for removal if the user clicks "No"
                    users_to_remove.append(user_name)
                    break
    
        wait_del_user = []
        waiting_list_users = [user_name for user_name, user_data in attendance_status.items() if user_data["is_waiting_list"] and user_data["marked_present"]]
        if waiting_list_users:
            # Remove users who clicked "No"
            if users_to_remove:
                for user_name in users_to_remove:
                    del attendance_status[user_name]
                self.save_attendance_status(attendance_status)
        
                # Assign the seat to the first waiting list user
                user_name = waiting_list_users[0]
                # print(user_name)
                user_data = attendance_status[user_name]
                user_data["is_waiting_list"] = False
                user_data["seat_number"] = seatNum
                self.save_attendance_status(attendance_status)

                # Display a message for waiting list user
                messagebox.showinfo("Seat Booked", f"Your seat is booked, {user_name}! Seat Number: {seatNum}")
            else:
                messagebox.showinfo("No Boarding", "No users have boarded the train or waiting list is empty.")
                for user_name, user_data in attendance_status.items():
                    if user_data["is_waiting_list"]:
                        # print("Waiting")
                        wait_del_user.append(user_name)
                        
    
                for user_name in wait_del_user:
                    # print("Removing user", user_name)
                    del attendance_status[user_name]
                self.save_attendance_status(attendance_status)
        
        else: 
            # If no waiting list user is present, display a message
            messagebox.showinfo("No Boarding", "No users have boarded the train or waiting list is empty.")
            for user_name, user_data in attendance_status.items():
                if user_data["is_waiting_list"]:
                    # print("Waiting")
                    wait_del_user.append(user_name)
                    

            for user_name in wait_del_user:
                # print("Removing user", user_name)
                del attendance_status[user_name]
            self.save_attendance_status(attendance_status)


    def recognize_user_from_qr_code(self, qr_code_data):
        known_face_names, known_mobile_numbers, is_waiting_list = self.load_known_users()

        for i, mobile_number in enumerate(known_mobile_numbers):
            if f"Mobile Number: {mobile_number}" == qr_code_data:
                recognized_name = known_face_names[i]
                mobile_number = known_mobile_numbers[i]

                if recognized_name not in self.recognized_set:
                    seat_number = self.get_next_seat_number(is_waiting_list[i])
                    self.status_label.config(text=f"Marked attendance: {recognized_name}, Seat No: {seat_number}")
                    self.log_attendance(recognized_name, mobile_number, seat_number, is_waiting_list[i])
                    self.recognized_set.add(recognized_name)

                    # Update attendance status to mark as present
                    attendance_status = self.load_attendance_status()
                    attendance_status[recognized_name]["marked_present"] = True
                    attendance_status[recognized_name]["seat_number"] = seat_number
                    attendance_status[recognized_name]["is_waiting_list"] = is_waiting_list[i]
                    self.save_attendance_status(attendance_status)

                return recognized_name

        return None

    def load_known_users(self):
        known_face_names = []
        known_mobile_numbers = []
        is_waiting_list = []

        for filename in os.listdir(self.db_dir):
            if filename.lower().endswith('.json'):
                user_info_path = os.path.join(self.db_dir, filename)
                with open(user_info_path, 'r') as user_info_file:
                    user_data = json.load(user_info_file)
                    known_face_names.append(user_data["name"])
                    known_mobile_numbers.append(user_data["mobile_number"])
                    is_waiting_list.append(user_data.get("is_waiting_list", False))

        return known_face_names, known_mobile_numbers, is_waiting_list

    def detect_qr_code(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        decoded_objects = decode(frame)

        for obj in decoded_objects:
            qr_code_data = obj.data.decode('utf-8')
            bbox = obj.polygon

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
        qr_code_image_path = os.path.join(self.qr_codes_dir, f'{name}_qr.png')
        img.save(qr_code_image_path)

        qr_code_image = ImageTk.PhotoImage(Image.open(qr_code_image_path))

        return qr_code_image

    def show_qr_code_window(self, qr_code):
        qr_code_window = tk.Toplevel(self.main_window)
        qr_code_window.title("QR Code")
        qr_label = tk.Label(qr_code_window, image=qr_code)
        qr_label.image = qr_code
        qr_label.pack()

    def capture_image_and_save(self, name, mobile_number, seat_number, is_waiting_list=False):
        ret, frame = self.cap.read()
        img_path = os.path.join(self.db_dir, f'{name}.jpg')
        cv2.imwrite(img_path, frame)

        user_info_path = os.path.join(self.db_dir, f'{name}.json')
        log_path = self.log_path

        # Check if QR code has already been generated for this user
        if not os.path.exists(user_info_path):
            # Generate QR code only for the first-time registration
            qr_code = self.generate_qr_code(name, mobile_number)

        with open(user_info_path, 'w') as user_info_file:
            user_data = {
                "name": name,
                "mobile_number": mobile_number,
                "seat_number": seat_number,
                "is_waiting_list": is_waiting_list,
                "timestamp": str(datetime.datetime.now())
            }
            json.dump(user_data, user_info_file)

        with open(log_path, 'a') as f:
            f.write('{}, {}, {}, {}, {}\n'.format(name, mobile_number, seat_number, is_waiting_list, datetime.datetime.now()))

    def start(self):
        self.main_window.mainloop()

if __name__ == "__main__":
    app = App()
    app.start()
