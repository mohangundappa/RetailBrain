from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
app.secret_key = "staples-brain-secret-key"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health', methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Staples Brain is running",
        "version": "1.0.0",
        "agents": ["Package Tracking Agent", "Reset Password Agent"]
    })

@app.route('/api/agents', methods=["GET"])
def list_agents():
    return jsonify({
        "success": True,
        "agents": ["Package Tracking Agent", "Reset Password Agent"]
    })

@app.route('/api/process', methods=["POST"])
def process_request():
    data = request.json
    
    if not data or "input" not in data:
        return jsonify({
            "success": False,
            "error": "Missing required field: input"
        }), 400
    
    user_input = data["input"]
    
    # Simple mock responses for demo
    if "track" in user_input.lower() or "package" in user_input.lower():
        return jsonify({
            "agent": "Package Tracking Agent",
            "response": "Your package with tracking number TRACK123456 is currently in transit and expected to be delivered in 3 days. It's currently in Chicago, IL and should arrive at your location soon.",
            "tracking_info": {
                "tracking_number": "TRACK123456",
                "shipping_carrier": "UPS",
                "order_number": None,
                "time_frame": "3 days"
            },
            "package_status": {
                "tracking_number": "TRACK123456",
                "status": "in_transit",
                "estimated_delivery": "2023-10-15",
                "current_location": "Chicago, IL",
                "last_updated": "2023-10-12 08:30:45",
                "message": "Package is currently in transit",
                "is_simulated": True
            },
            "success": True,
            "selected_agent": "Package Tracking Agent",
            "confidence": 0.9
        })
    elif "password" in user_input.lower() or "reset" in user_input.lower():
        return jsonify({
            "agent": "Reset Password Agent",
            "response": "I've sent password reset instructions to your email address. Please check your inbox and follow the instructions to create a new password. The email should arrive within the next few minutes.",
            "account_info": {
                "email": "user@example.com",
                "username": None,
                "account_type": "Staples.com",
                "issue": "forgot password"
            },
            "reset_status": {
                "status": "instructions_provided",
                "message": "Password reset instructions for your account with email: user@example.com",
                "instructions": [
                    "Go to Staples.com and click on 'Sign In' at the top of the page.",
                    "Click on 'Forgot Password' below the login form.",
                    "Enter your email address associated with your account.",
                    "Check your email inbox for a password reset link.",
                    "Click the link and follow the instructions to create a new password.",
                    "Use your new password to log in."
                ],
                "reset_link_sent": False,
                "is_simulated": True
            },
            "success": True,
            "selected_agent": "Reset Password Agent",
            "confidence": 0.85
        })
    else:
        return jsonify({
            "success": False,
            "error": "No suitable agent found",
            "response": "I'm sorry, I don't have the capability to help with that request at the moment. I can assist with package tracking and password reset inquiries.",
            "confidence": 0.2
        })

@app.route('/api/track-package', methods=["POST"])
def track_package():
    return jsonify({
        "agent": "Package Tracking Agent",
        "response": "Your package with tracking number TRACK123456 is currently in transit and expected to be delivered in 3 days. It's currently in Chicago, IL and should arrive at your location soon.",
        "tracking_info": {
            "tracking_number": "TRACK123456",
            "shipping_carrier": "UPS",
            "order_number": None,
            "time_frame": "3 days"
        },
        "package_status": {
            "tracking_number": "TRACK123456",
            "status": "in_transit",
            "estimated_delivery": "2023-10-15",
            "current_location": "Chicago, IL",
            "last_updated": "2023-10-12 08:30:45",
            "message": "Package is currently in transit",
            "is_simulated": True
        },
        "success": True
    })

@app.route('/api/reset-password', methods=["POST"])
def reset_password():
    return jsonify({
        "agent": "Reset Password Agent",
        "response": "I've sent password reset instructions to your email address. Please check your inbox and follow the instructions to create a new password. The email should arrive within the next few minutes.",
        "account_info": {
            "email": "user@example.com",
            "username": None,
            "account_type": "Staples.com",
            "issue": "forgot password"
        },
        "reset_status": {
            "status": "instructions_provided",
            "message": "Password reset instructions for your account with email: user@example.com",
            "instructions": [
                "Go to Staples.com and click on 'Sign In' at the top of the page.",
                "Click on 'Forgot Password' below the login form.",
                "Enter your email address associated with your account.",
                "Check your email inbox for a password reset link.",
                "Click the link and follow the instructions to create a new password.",
                "Use your new password to log in."
            ],
            "reset_link_sent": False,
            "is_simulated": True
        },
        "success": True
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
