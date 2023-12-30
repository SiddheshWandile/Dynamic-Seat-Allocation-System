import os.path
import datetime
import tkinter as tk
import cv2
from PIL import Image, ImageTk
import util

class App:
    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.geometry("1200x520+350+100")

        self.login_button_main_window = util.get_button(self.main_window, 'login', 'green', self.login)
        self.login_button_main_window.place(x=750, y=300)

        self.register_new_user_button_main_window = util.get_button(self.main_window, 'register new user', 'gray',
                                                                    self.register_new_user, fg='black')
        self.register_new_user_button_main_window.place(x=750, y=400)

        self.webcam_label = util.get_img_label(self.main_window)
        self.webcam_label.place(x=10, y=0, width=700, height=500)

        self.add_webcam(self.webcam_label)

        self.db_dir = './db'
        if not os.path.exists(self.db_dir):
            os.mkdir(self.db_dir)

        self.waiting_list_dir = './waiting_list'
        if not os.path.exists(self.waiting_list_dir):
            os.mkdir(self.waiting_list_dir)

        self.log_path = './log.txt'

        self.max_users = 6  # Maximum number of users allowed
        self.registered_users = 0
        self.booked_users = 0
        self.waiting_list_users = 0

    def add_webcam(self, label):
        if 'cap' not in self.__dict__:
            self.cap = cv2.VideoCapture(0)

        self._label = label
        self.process_webcam()

    def process_webcam(self):
        ret, frame = self.cap.read()

        self.most_recent_capture_arr = frame
        img_ = cv2.cvtColor(self.most_recent_capture_arr, cv2.COLOR_BGR2RGB)
        self.most_recent_capture_pil = Image.fromarray(img_)
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        self._label.imgtk = imgtk
        self._label.configure(image=imgtk)

        self._label.after(20, self.process_webcam)

    def login(self):
        unknown_img_path = './tmp.jpg'

        cv2.imwrite(unknown_img_path, self.most_recent_capture_arr)

        # Check in the main user directory
        name_main = self.recognize_face(self.db_dir, unknown_img_path)

        if name_main:
            util.msg_box('Welcome back!', 'Welcome, {}.'.format(name_main))
            with open(self.log_path, 'a') as f:
                f.write('{},{}\n'.format(name_main, datetime.datetime.now()))
        else:
            # Check in the waiting list directory only if the main directory check fails
            name_waiting = self.recognize_face(self.waiting_list_dir, unknown_img_path)

            if name_waiting:
                util.msg_box('Welcome back!', 'Welcome, {} (from waiting list).'.format(name_waiting))
                # You can perform additional actions for users from the waiting list here
            else:
                util.msg_box('Ups...', 'Unknown user. Please register a new user or try again.')

        os.remove(unknown_img_path)

    def recognize_face(self, directory, unknown_img_path):
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(directory, filename)
                target_img = cv2.imread(img_path)

                # Resize both images to a consistent size for comparison
                target_img = cv2.resize(target_img, (self.most_recent_capture_arr.shape[1], self.most_recent_capture_arr.shape[0]))

                # Compare the images using OpenCV's template matching
                result = cv2.matchTemplate(self.most_recent_capture_arr, target_img, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)

                # Adjust the threshold based on your use case
                threshold = 0.7
                if max_val >= threshold:
                    return os.path.splitext(filename)[0]

        return None

    def register_new_user(self):
        if self.registered_users >= self.max_users:
            util.msg_box('Limit Exceeded', 'Maximum users limit reached (6). Cannot register more users.')
            return

        self.register_new_user_window = tk.Toplevel(self.main_window)
        self.register_new_user_window.geometry("1200x520+370+120")

        self.accept_button_register_new_user_window = util.get_button(self.register_new_user_window, 'Accept', 'green', self.accept_register_new_user)
        self.accept_button_register_new_user_window.place(x=750, y=300)

        self.try_again_button_register_new_user_window = util.get_button(self.register_new_user_window, 'Try again', 'grey', self.try_again_register_new_user)
        self.try_again_button_register_new_user_window.place(x=750, y=400)

        self.capture_label = util.get_img_label(self.register_new_user_window)
        self.capture_label.place(x=10, y=0, width=700, height=500)

        self.add_img_to_label(self.capture_label)

        self.entry_name_register_new_user = util.get_entry_text(self.register_new_user_window)
        self.entry_name_register_new_user.place(x=750, y=100)

        self.entry_mobile_register_new_user = util.get_entry_text(self.register_new_user_window)
        self.entry_mobile_register_new_user.place(x=750, y=200)

        self.text_label_name_register_new_user = util.get_text_label(self.register_new_user_window, 'Please enter Name:')
        self.text_label_name_register_new_user.place(x=750, y=70)

        self.text_label_mobile_register_new_user = util.get_text_label(self.register_new_user_window, 'Please enter Mobile Number:')
        self.text_label_mobile_register_new_user.place(x=750, y=170)

    def try_again_register_new_user(self):
        self.register_new_user_window.destroy()

    def add_img_to_label(self, label):
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        label.imgtk = imgtk
        label.configure(image=imgtk)

        self.register_new_user_capture = self.most_recent_capture_arr.copy()

    def accept_register_new_user(self):
        name = self.entry_name_register_new_user.get(1.0, "end-1c")
        mobile = self.entry_mobile_register_new_user.get(1.0, "end-1c")

        if not name.strip() or not mobile.strip():
            util.msg_box('Incomplete Information', 'Please provide both Name and Mobile Number.')
            return

        if os.path.exists(os.path.join(self.db_dir, '{}.jpg'.format(name))):
            util.msg_box('Duplicate User', 'User with the same name already exists. Please choose a different name.')
            return

        existing_users = [filename.split('.')[0] for filename in os.listdir(self.db_dir) if filename.endswith('.txt')]
        for existing_user in existing_users:
            existing_user_info_file = os.path.join(self.db_dir, '{}.txt'.format(existing_user))
            if os.path.exists(existing_user_info_file):
                with open(existing_user_info_file, 'r') as f:
                    existing_mobile = f.readline().strip()
                    if existing_mobile == mobile:
                        util.msg_box('Duplicate Mobile Number', 'User with the same mobile number already exists. Please use a different mobile number.')
                        return

        if not mobile.isdigit() or len(mobile) != 10:
            util.msg_box('Invalid Mobile Number', 'Please enter a valid 10-digit mobile number.')
            return

        if self.booked_users < 3:
            cv2.imwrite(os.path.join(self.db_dir, '{}.jpg'.format(name)), self.register_new_user_capture)
            user_info_file = os.path.join(self.db_dir, '{}.txt'.format(name))
            with open(user_info_file, 'w') as f:
                f.write('{}\n{}'.format(name, mobile))
            util.msg_box('Congratulations!', 'Your Seat is Booked!')
            self.booked_users += 1
        elif self.waiting_list_users < 3:
            cv2.imwrite(os.path.join(self.waiting_list_dir, '{}.jpg'.format(name)), self.register_new_user_capture)
            user_info_file = os.path.join(self.waiting_list_dir, '{}.txt'.format(name))
            with open(user_info_file, 'w') as f:
                f.write('{}\n{}'.format(name, mobile))
            util.msg_box('Seats are Booked', 'Your seat is added to the waiting list.')
            self.waiting_list_users += 1
        else:
            util.msg_box('Limit Exceeded', 'Maximum users limit reached (6). Cannot register more users.')

        self.registered_users += 1
        self.register_new_user_window.destroy()

    def start(self):
        self.main_window.mainloop()

if __name__ == "__main__":
    app = App()
    app.start()
