import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Conversation(db.Model):
    """Model to store user conversations with the brain"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), index=True, nullable=False)
    user_input = db.Column(db.Text, nullable=False)
    brain_response = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(64), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    selected_agent = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    messages = db.relationship('Message', back_populates='conversation', cascade='all, delete-orphan')
    tracking_data = db.relationship('PackageTracking', back_populates='conversation', cascade='all, delete-orphan')
    password_reset_data = db.relationship('PasswordReset', back_populates='conversation', cascade='all, delete-orphan')
    store_locator_data = db.relationship('StoreLocator', back_populates='conversation', cascade='all, delete-orphan')
    product_info_data = db.relationship('ProductInfo', back_populates='conversation', cascade='all, delete-orphan')

class Message(db.Model):
    """Model to store individual messages in a conversation"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(32), nullable=False)  # 'user', 'assistant', 'system'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    conversation = db.relationship('Conversation', back_populates='messages')

class PackageTracking(db.Model):
    """Model to store package tracking information"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    tracking_number = db.Column(db.String(128), nullable=False)
    shipping_carrier = db.Column(db.String(64), nullable=True)
    order_number = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(64), nullable=True)
    estimated_delivery = db.Column(db.String(64), nullable=True)
    current_location = db.Column(db.String(128), nullable=True)
    last_updated = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    conversation = db.relationship('Conversation', back_populates='tracking_data')

class PasswordReset(db.Model):
    """Model to store password reset information"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    email = db.Column(db.String(128), nullable=True)
    username = db.Column(db.String(128), nullable=True)
    account_type = db.Column(db.String(64), nullable=True)
    issue = db.Column(db.String(128), nullable=True)
    reset_link_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    conversation = db.relationship('Conversation', back_populates='password_reset_data')

class AgentConfig(db.Model):
    """Model to store agent configuration settings"""
    id = db.Column(db.Integer, primary_key=True)
    agent_name = db.Column(db.String(64), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    confidence_threshold = db.Column(db.Float, default=0.3)
    description = db.Column(db.Text, nullable=True)
    prompt_template = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class StoreLocator(db.Model):
    """Model to store store locator information"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    location = db.Column(db.String(128), nullable=True)
    radius = db.Column(db.Integer, default=10)
    service = db.Column(db.String(128), nullable=True)
    store_id = db.Column(db.String(64), nullable=True)
    store_name = db.Column(db.String(128), nullable=True)
    store_address = db.Column(db.String(256), nullable=True)
    store_phone = db.Column(db.String(64), nullable=True)
    store_hours = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    conversation = db.relationship('Conversation', back_populates='store_locator_data')

class ProductInfo(db.Model):
    """Model to store product information"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    product_name = db.Column(db.String(256), nullable=True)
    product_id = db.Column(db.String(128), nullable=True)
    category = db.Column(db.String(128), nullable=True)
    price = db.Column(db.String(64), nullable=True)
    availability = db.Column(db.String(64), nullable=True)
    description = db.Column(db.Text, nullable=True)
    specifications = db.Column(db.Text, nullable=True)
    search_query = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    conversation = db.relationship('Conversation', back_populates='product_info_data')

class AnalyticsData(db.Model):
    """Model to store analytics data about agent usage"""
    id = db.Column(db.Integer, primary_key=True)
    agent_name = db.Column(db.String(64), nullable=False)
    request_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    avg_confidence = db.Column(db.Float, default=0)
    avg_response_time = db.Column(db.Float, default=0)
    date = db.Column(db.Date, nullable=False)
    
    __table_args__ = (db.UniqueConstraint('agent_name', 'date', name='unique_agent_day'),)