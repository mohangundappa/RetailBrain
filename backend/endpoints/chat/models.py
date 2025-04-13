"""
Models for Chat and Observability API endpoints.
"""
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field


class CustomerProfile(BaseModel):
    """Customer profile information"""
    customer_id: str = Field(..., description="Unique customer identifier")
    email: str = Field(..., description="Customer email address")
    phone: Optional[str] = Field(None, description="Customer phone number")
    type: str = Field("individual", description="Customer type: individual or business")
    tier: str = Field("regular", description="Customer tier: regular, premier, or plus")
    preferred_store_id: Optional[str] = Field(None, description="Preferred store location ID")


class IdentityContext(BaseModel):
    """Identity context information"""
    visitor_id: Optional[str] = Field(None, description="Anonymous visitor ID")
    customer_id: Optional[str] = Field(None, description="Authenticated customer ID")
    session_id: Optional[str] = Field(None, description="Current session ID")
    authentication_level: str = Field("none", description="Authentication level: none, basic, mfa")


class ChatContext(BaseModel):
    """Complete chat context model"""
    identity: Optional[IdentityContext] = Field(None, description="Identity context")
    customer_profile: Optional[CustomerProfile] = Field(None, description="Customer profile data")


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., description="User message text")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    context: Optional[ChatContext] = Field(None, description="Chat context information")


class ChatResponse(BaseModel):
    """Chat response model"""
    success: bool = Field(..., description="Operation success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if applicable")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")


class ObservabilityResponse(BaseModel):
    """Observability response model"""
    success: bool = Field(..., description="Operation success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Observability data")
    error: Optional[str] = Field(None, description="Error message if applicable")


class ConversationSummary(BaseModel):
    """Conversation summary model"""
    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    timestamp: str = Field(..., description="Creation timestamp")
    message_count: int = Field(..., description="Number of message exchanges")


class ConversationsResponse(BaseModel):
    """Conversations list response model"""
    success: bool = Field(..., description="Operation success status")
    data: List[ConversationSummary] = Field(..., description="List of conversations")
    error: Optional[str] = Field(None, description="Error message if applicable")