"""
SMS notification module for Staples Brain.
Uses Twilio to send SMS notifications for package tracking.
"""
import os
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def send_sms_notification(to_phone_number: str, message: str) -> dict:
    """
    Send an SMS notification using Twilio.
    
    Args:
        to_phone_number: The phone number to send the SMS to
        message: The message content to send
        
    Returns:
        A dictionary with the status and message SID if successful
    """
    # Validate environment variables
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        logger.error("Missing Twilio credentials. SMS notification not sent.")
        return {
            "success": False,
            "error": "Missing Twilio credentials",
            "message": "Unable to send SMS. Please configure Twilio credentials."
        }
    
    try:
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send message
        message_obj = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone_number
        )
        
        logger.info(f"SMS notification sent to {to_phone_number}, SID: {message_obj.sid}")
        
        return {
            "success": True,
            "message_sid": message_obj.sid,
            "status": message_obj.status
        }
        
    except Exception as e:
        logger.error(f"Error sending SMS notification: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to send SMS notification"
        }

def send_tracking_update(to_phone_number: str, tracking_data: dict) -> dict:
    """
    Send a tracking update notification.
    
    Args:
        to_phone_number: The phone number to send the update to
        tracking_data: Dictionary containing tracking information
        
    Returns:
        Result of the SMS sending operation
    """
    # Format tracking message
    tracking_number = tracking_data.get("tracking_number", "Unknown")
    status = tracking_data.get("status", "unknown")
    carrier = tracking_data.get("shipping_carrier", "")
    location = tracking_data.get("current_location", "")
    delivery = tracking_data.get("estimated_delivery", "")
    
    # Format a nice message
    message = f"Staples Package Update: Your package ({tracking_number}) "
    
    if status == "delivered":
        message += f"has been delivered"
        if location:
            message += f" to {location}"
    elif status == "in_transit":
        message += f"is in transit"
        if location:
            message += f" and currently in {location}"
        if delivery:
            message += f". Estimated delivery: {delivery}"
    elif status == "out_for_delivery":
        message += f"is out for delivery today"
        if location:
            message += f" from {location}"
    else:
        message += f"status is {status}"
        if location:
            message += f" at {location}"
        if delivery:
            message += f". Estimated delivery: {delivery}"
    
    if carrier:
        message += f". Carrier: {carrier}"
        
    message += ". Reply STOP to stop notifications."
    
    # Send the message
    return send_sms_notification(to_phone_number, message)

def send_delivery_confirmation(to_phone_number: str, tracking_data: dict) -> dict:
    """
    Send a delivery confirmation notification.
    
    Args:
        to_phone_number: The phone number to send the confirmation to
        tracking_data: Dictionary containing tracking information
        
    Returns:
        Result of the SMS sending operation
    """
    # Format delivery message
    tracking_number = tracking_data.get("tracking_number", "Unknown")
    order_number = tracking_data.get("order_number", "")
    
    message = f"Staples Delivery Confirmation: Your package ({tracking_number})"
    
    if order_number:
        message += f" for order #{order_number}"
        
    message += " has been delivered. Thank you for shopping with Staples!"
    
    # Send the message
    return send_sms_notification(to_phone_number, message)