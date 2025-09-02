from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Literal, List

from pydantic import BaseModel, EmailStr, Field

class Patient(BaseModel):
	patient_id: int
	first_name: str
	last_name: str
	dob: date
	email: Optional[EmailStr] = None
	phone: Optional[str] = None
	insurance_carrier: Optional[str] = None
	member_id: Optional[str] = None
	group_id: Optional[str] = None
	is_returning: bool = False

	@property
	def full_name(self) -> str:
		return f"{self.first_name} {self.last_name}".strip()


class InsuranceInfo(BaseModel):
	carrier: str
	member_id: str
	group_id: str


class AppointmentRequest(BaseModel):
	first_name: str
	last_name: str
	dob: date
	doctor: str
	location: str
	email: Optional[EmailStr] = None
	phone: Optional[str] = None
	insurance: Optional[InsuranceInfo] = None


class Slot(BaseModel):
	doctor: str
	location: str
	date: date
	start_time: str
	end_time: str
	is_booked: bool = False


class Appointment(BaseModel):
	appointment_id: str
	patient_id: Optional[int] = None
	patient_name: str
	patient_type: Literal["new", "returning"]
	doctor: str
	location: str
	date: date
	start_time: str
	end_time: str
	duration_minutes: int
	insurance: Optional[InsuranceInfo] = None
	created_at: datetime = Field(default_factory=datetime.utcnow)
	status: Literal["confirmed", "cancelled"] = "confirmed"
	cancellation_reason: Optional[str] = None


class ReminderStatus(BaseModel):
	appointment_id: str
	reminder_number: Literal[1, 2, 3]
	sent_at: datetime
	confirmed: Optional[bool] = None
	forms_completed: Optional[bool] = None
	cancellation_reason: Optional[str] = None


