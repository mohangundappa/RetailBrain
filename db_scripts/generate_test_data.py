#!/usr/bin/env python3
"""
Test data generator for Staples Brain database
This script generates sample data for testing the Staples Brain application.
"""

import os
import random
from datetime import datetime, timedelta
import argparse

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except ImportError:
    print("Error: SQLAlchemy not installed. Run: pip install sqlalchemy")
    exit(1)

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models import (
        Conversation, Message, PackageTracking, 
        StoreLocator, PasswordReset, ProductInfo
    )
except ImportError:
    print("Error: Could not import models. Make sure you run this from the project root.")
    exit(1)


def random_date(days=30):
    """Generate a random date within the last N days"""
    return datetime.now() - timedelta(days=random.randint(0, days))


def create_test_data(session, count=20):
    """Generate test data for the Staples Brain database"""
    print(f"Generating {count} test conversations with related data...")
    
    # Define sample intents and agents
    intents = [
        {"name": "track_package", "agent": "Package Tracking Agent"},
        {"name": "reset_password", "agent": "Reset Password Agent"},
        {"name": "find_store", "agent": "Store Locator Agent"},
        {"name": "product_info", "agent": "Product Info Agent"}
    ]
    
    # Sample user inputs for each intent
    user_inputs = {
        "track_package": [
            "Where is my order?",
            "Track my package",
            "What's the status of my delivery?",
            "When will my order arrive?",
            "Is my package on the way?"
        ],
        "reset_password": [
            "I forgot my password",
            "Need to reset my login",
            "Can't remember my account password",
            "How do I change my password?",
            "I need a new password for my account"
        ],
        "find_store": [
            "Where is the nearest Staples?",
            "Find a store near me",
            "Staples locations in my area",
            "Is there a Staples in downtown?",
            "Closest store with copy services"
        ],
        "product_info": [
            "I need information about printers",
            "Tell me about your laptops",
            "Do you have paper in stock?",
            "What kind of office chairs do you sell?",
            "Price check on toner cartridges"
        ]
    }
    
    # Sample brain responses for each intent
    brain_responses = {
        "track_package": [
            "I'll help you track your package. Could you provide your order number?",
            "I can check on your delivery. What's your tracking number?",
            "Let me find your package status. Do you have an order or tracking number?",
            "I'd be happy to help track your order. Could you share the order ID?",
            "I'll assist with locating your package. What's the order reference?"
        ],
        "reset_password": [
            "I can help you reset your password. What's the email address on your account?",
            "Let's get your password reset. Could you provide the username or email?",
            "I'll guide you through resetting your password. First, what's your email address?",
            "To reset your password, I'll need to know which account. What's your email?",
            "I'll help you create a new password. What email do you use to log in?"
        ],
        "find_store": [
            "I can help find the nearest Staples store. What's your ZIP code?",
            "Let me locate Staples stores in your area. What's your current location?",
            "I'll find Staples locations for you. Could you share your city or ZIP?",
            "To show you nearby stores, I need your location. What ZIP code are you in?",
            "I can point you to the closest Staples. What's your address or ZIP code?"
        ],
        "product_info": [
            "I'd be happy to provide information about that product. What specific details do you need?",
            "Let me check our product catalog. Could you be more specific about what you're looking for?",
            "I can tell you about our products. Which features are most important to you?",
            "I'll help you find product information. Are you looking for something specific?",
            "I can provide details on that product. Are you interested in pricing, features, or availability?"
        ]
    }

    # Create conversations
    for i in range(count):
        # Choose a random intent
        intent = random.choice(intents)
        intent_name = intent["name"]
        
        # Create a new conversation
        user_input = random.choice(user_inputs[intent_name])
        brain_response = random.choice(brain_responses[intent_name])
        
        conversation = Conversation(
            session_id=f"test-session-{i+100}",
            user_input=user_input,
            brain_response=brain_response,
            intent=intent_name,
            confidence=random.uniform(0.7, 0.98),
            selected_agent=intent["agent"],
            created_at=random_date()
        )
        session.add(conversation)
        session.flush()  # Flush to get the ID
        
        # Add messages for this conversation
        message_count = random.randint(2, 5)
        for j in range(message_count):
            msg_date = conversation.created_at - timedelta(minutes=random.randint(0, j*2))
            role = "user" if j % 2 == 0 else "assistant"
            content = user_input if role == "user" else brain_response
            
            message = Message(
                conversation_id=conversation.id,
                role=role,
                content=content,
                created_at=msg_date
            )
            session.add(message)
        
        # Add agent-specific data based on intent
        if intent_name == "track_package":
            carriers = ["UPS", "FedEx", "USPS", "DHL"]
            statuses = ["Delivered", "In Transit", "Out for Delivery", "Delayed", "Processing"]
            
            tracking = PackageTracking(
                conversation_id=conversation.id,
                tracking_number=f"1Z{random.randint(10000000, 99999999)}",
                shipping_carrier=random.choice(carriers),
                order_number=f"ST{random.randint(10000, 99999)}",
                status=random.choice(statuses),
                estimated_delivery=(datetime.now() + timedelta(days=random.randint(0, 5))).strftime("%Y-%m-%d"),
                current_location=f"Distribution Center, {random.choice(['Atlanta', 'Chicago', 'Dallas', 'Denver', 'Miami'])}, {random.choice(['GA', 'IL', 'TX', 'CO', 'FL'])}",
                created_at=conversation.created_at
            )
            session.add(tracking)
            
        elif intent_name == "reset_password":
            domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com"]
            account_types = ["customer", "employee", "business", "rewards_member"]
            issues = ["forgotten password", "account locked", "security concern", "new device"]
            
            reset = PasswordReset(
                conversation_id=conversation.id,
                email=f"user{random.randint(100, 999)}@{random.choice(domains)}",
                username=f"user{random.randint(1000, 9999)}",
                account_type=random.choice(account_types),
                issue=random.choice(issues),
                reset_link_sent=random.choice([True, False]),
                created_at=conversation.created_at
            )
            session.add(reset)
            
        elif intent_name == "find_store":
            zip_codes = ["30308", "60611", "10001", "90210", "75201", "02108", "98101"]
            services = ["Copy & Print", "Tech Services", "Shipping", "None"]
            store_names = ["Staples Downtown", "Staples Midtown", "Staples Business Center", "Staples Express"]
            
            store = StoreLocator(
                conversation_id=conversation.id,
                location=random.choice(zip_codes),
                radius=random.choice([5, 10, 15, 20]),
                service=random.choice(services),
                store_id=f"STR-{random.randint(100, 999)}",
                store_name=random.choice(store_names),
                store_address=f"{random.randint(100, 9999)} Main St, City, State {random.choice(zip_codes)}",
                store_phone=f"({random.randint(200, 999)}) 555-{random.randint(1000, 9999)}",
                created_at=conversation.created_at
            )
            session.add(store)
            
        elif intent_name == "product_info":
            categories = ["Electronics", "Office Supplies", "Furniture", "Print Services", "Technology"]
            availabilities = ["In Stock", "Limited Stock", "Out of Stock", "Back Ordered", "Available Online Only"]
            products = [
                "Laptop Pro X5", "Wireless Ergonomic Mouse", "Executive Office Chair", 
                "Multi-Function Printer", "Portable SSD Drive", "Standing Desk", 
                "Paper Shredder", "Laser Printer Toner", "Wireless Headphones"
            ]
            
            product = ProductInfo(
                conversation_id=conversation.id,
                product_name=random.choice(products),
                product_id=f"SKU-{random.randint(10000, 99999)}",
                category=random.choice(categories),
                price=f"${random.randint(20, 1000)}.{random.randint(0, 99):02d}",
                availability=random.choice(availabilities),
                search_query=user_input,
                created_at=conversation.created_at
            )
            session.add(product)
    
    # Commit all changes
    session.commit()
    print(f"Successfully generated {count} conversations with related agent data")


def main():
    parser = argparse.ArgumentParser(description="Generate test data for Staples Brain")
    parser.add_argument("-c", "--count", type=int, default=20, help="Number of conversations to generate (default: 20)")
    parser.add_argument("-d", "--database-url", type=str, help="Database URL (default: from environment)")
    args = parser.parse_args()
    
    # Get database URL from environment or args
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        print("Error: No DATABASE_URL found. Please set it as an environment variable or use the --database-url flag.")
        exit(1)
    
    print(f"Connecting to database: {database_url}")
    try:
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        create_test_data(session, args.count)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()