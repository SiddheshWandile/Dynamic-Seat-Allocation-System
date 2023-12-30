Face Recognition and User Registration System
This project is a simple face recognition and user registration system implemented in Python using the Tkinter GUI toolkit and OpenCV for webcam interaction. It allows users to register their face, log in, and provides seat booking functionality with a waiting list.

Features
User Registration: Users can register their face along with their name and mobile number.
Face Recognition: The system uses template matching for face recognition during login.
Seat Booking: Users can book seats, and if the maximum limit is reached, additional users are added to a waiting list.
Logging: The system logs successful logins with the user's name and timestamp.
Prerequisites
Python 3.x
OpenCV (pip install opencv-python)
Pillow (pip install Pillow)
Usage
Clone the repository:

bash
Copy code
git clone https://github.com/your-username/your-repo.git
Navigate to the project directory:

bash
Copy code
cd your-repo
Install the required dependencies:

bash
Copy code
pip install -r requirements.txt
Run the application:

bash
Copy code
python main.py
Instructions
Click the "Login" button to recognize registered users.
Click the "Register New User" button to add new users.
Follow the on-screen instructions for registration and login.
Successful logins will be recorded in the log.txt file.
Additional Notes
Face Recognition: The system uses a simple template matching approach for face recognition. Adjust the threshold in the code for optimal results.
Waiting List: If the maximum user limit is reached, additional users are added to the waiting list.
