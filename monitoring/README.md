# Online Proctoring System

A real-time online proctoring system built with Flask and WebSocket that allows administrators to monitor users through video streaming and detect suspicious behaviors.

## Features

- Real-time video streaming monitoring
- Admin and User dashboards
- Automatic detection of:
  - Multiple faces in frame
  - Suspicious head movements
- Real-time alerts and notifications
- Secure login system

## Prerequisites

- Python 3.7+
- pip (Python package manager)
- ngrok
- Webcam access

## Installation

1. Clone this repository:

```bash
git clone https://github.com/IvaR-KB/Online_Proctoring_System
cd monitoring
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required dependencies:

```bash
pip install flask flask-socketio opencv-python mediapipe numpy scipy pillow ngrok
```

## Configuration

1. Download and install ngrok from [https://ngrok.com/download](https://ngrok.com/download)
2. Sign up for a free ngrok account and get your authtoken
3. Configure ngrok with your authtoken:

```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

## Running the Application

1. Start the Flask application:

```bash
python app.py
```

2. In a new terminal, start ngrok to create a secure tunnel:

```bash
ngrok http 5000
```

3. Copy the HTTPS URL provided by ngrok (e.g., https://xxxx-xx-xx-xxx-xx.ngrok.io)

## Usage

### Admin Access

- URL: `<ngrok-url>/login`
- Username: `admin`
- Password: `admin123`

### User Access

- URL: `<ngrok-url>/login`
- Enter any username (no password required)

## Security Notes

- In a production environment, please change the following:
  - Update the `SECRET_KEY` in app.py
  - Implement proper user authentication
  - Store user credentials in a secure database
  - Use environment variables for sensitive data

## Browser Requirements

- Modern web browser with WebRTC support
- Webcam permissions enabled
- JavaScript enabled

## Troubleshooting

1. If the video stream isn't working:

   - Check browser permissions for camera access
   - Ensure WebSocket connection is established
   - Check browser console for errors
2. If ngrok connection fails:

   - Verify your authtoken is correctly configured
   - Ensure no other ngrok sessions are running
   - Check if port 5000 is available
