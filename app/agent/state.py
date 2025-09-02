from typing import List, TypedDict, Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

class PatientDetails(BaseModel):
    """A Pydantic model to store structured patient information."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[str] = None
    is_new_patient: Optional[bool] = None

class AgentState(TypedDict):
    """
    Represents the state of our AI agent. This is the "memory" of the conversation.
    """
    messages: List[BaseMessage]
    patient_details: Optional[PatientDetails]