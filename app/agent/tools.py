import pandas as pd
from langchain.tools import tool
from datetime import datetime, timedelta
from app.config import PATIENT_CSV_PATH, SCHEDULE_XLSX_PATH
import json

@tool
def lookup_patient(first_name: str, last_name: str, dob: str) -> dict:
    """
    Looks up a patient in the patient database (patients.csv) using their
    first name, last name, and date of birth (YYYY-MM-DD).
    Returns the patient's details if found, otherwise indicates the patient is new.
    """
    try:
        df = pd.read_csv(PATIENT_CSV_PATH)
        # Search for a matching patient, ignoring case for names
        patient = df[
            (df['first_name'].str.lower() == first_name.lower()) &
            (df['last_name'].str.lower() == last_name.lower()) &
            (df['dob'] == dob)
        ]
        
        if not patient.empty:
            return patient.to_dict('records')[0]
        else:
            return {"message": "Patient not found. This is a new patient."}
    except Exception as e:
        return {"error": f"An error occurred while looking up the patient: {str(e)}"}

@tool
def find_available_slots(doctor_name: str, date: str) -> list:
    """
    Finds all available (is_booked=False) appointment slots for a given doctor
    on a specific date (YYYY-MM-DD) from the schedules.xlsx file.
    Returns a list of available time slots.
    """
    try:
        df = pd.read_excel(SCHEDULE_XLSX_PATH)
        # Ensure date column is treated as a string for reliable matching
        df['date'] = df['date'].astype(str).str.split(' ').str[0]
        
        # Filter for the doctor on the specified date with available slots
        available_slots = df[
            (df['doctor'].str.lower() == doctor_name.lower()) &
            (df['date'] == date) &
            (df['is_booked'] == False)
        ]
        
        if not available_slots.empty:
            # Convert time objects to strings for clean output
            slots_list = available_slots[['start_time', 'end_time']].to_dict('records')
            for slot in slots_list:
                slot['start_time'] = str(slot['start_time'])
                slot['end_time'] = str(slot['end_time'])
            return slots_list
        else:
            return [{"message": "No available slots found for the specified doctor and date."}]
    except Exception as e:
        return [{"error": f"An error occurred while finding slots: {str(e)}"}]

@tool
def book_appointment(doctor_name: str, date: str, start_time: str) -> str:
    """
    Books an appointment by marking the slot as booked (is_booked=True) in the
    schedules.xlsx file for the specified doctor, date, and start time (HH:MM:SS).
    Returns a confirmation message.
    """
    try:
        df = pd.read_excel(SCHEDULE_XLSX_PATH)
        df['date'] = df['date'].astype(str).str.split(' ').str[0]
        df['start_time'] = df['start_time'].astype(str)
        
        # Find the specific slot to book
        slot_index = df[
            (df['doctor'].str.lower() == doctor_name.lower()) &
            (df['date'] == date) &
            (df['start_time'] == start_time) &
            (df['is_booked'] == False)
        ].index
        
        if not slot_index.empty:
            # Mark the slot as booked and save the file
            df.loc[slot_index, 'is_booked'] = True
            df.to_excel(SCHEDULE_XLSX_PATH, index=False)
            return f"Success: Appointment with {doctor_name} on {date} at {start_time} has been booked."
        else:
            return "Error: The selected slot is not available or does not exist. Please check the details and try again."
    except Exception as e:
        return f"An error occurred while booking the appointment: {str(e)}"

@tool
def get_calendly_availability(calendly_link: str, date: str) -> list:
    """
    Simulates Calendly integration to get available appointment slots.
    This tool connects to the Calendly calendar and returns available time slots
    for the specified date. The calendly_link should be the doctor's Calendly URL.
    Returns a list of available time slots in Calendly format.
    """
    try:
        # Simulate Calendly API call by reading from our Excel schedule
        df = pd.read_excel(SCHEDULE_XLSX_PATH)
        df['date'] = df['date'].astype(str).str.split(' ').str[0]
        
        # Extract doctor name from Calendly link (simulation)
        # In real implementation, this would parse the Calendly link
        doctor_name = "Dr. Sharma" if "sharma" in calendly_link.lower() else "Dr. Verma"
        
        # Filter for the doctor on the specified date with available slots
        available_slots = df[
            (df['doctor'].str.lower() == doctor_name.lower()) &
            (df['date'] == date) &
            (df['is_booked'] == False)
        ]
        
        if not available_slots.empty:
            # Format response to look like Calendly API
            calendly_slots = []
            for idx, slot in available_slots.iterrows():
                calendly_slot = {
                    "slot_id": f"calendly_{idx}",
                    "start_time": str(slot['start_time']),
                    "end_time": str(slot['end_time']),
                    "duration_minutes": 30,  # Default slot duration
                    "available": True,
                    "calendly_link": calendly_link,
                    "doctor": slot['doctor'],
                    "location": slot['location']
                }
                calendly_slots.append(calendly_slot)
            
            return calendly_slots
        else:
            return [{"message": "No available slots found in Calendly for the specified date."}]
    except Exception as e:
        return [{"error": f"Calendly API error: {str(e)}"}]

@tool
def book_calendly_slot(calendly_link: str, slot_id: str, patient_name: str, patient_email: str = "") -> str:
    """
    Books an appointment slot through Calendly integration.
    This tool creates a booking in the Calendly calendar and marks the slot as booked.
    Returns a confirmation message with booking details.
    """
    try:
        # Simulate Calendly booking by updating our Excel schedule
        df = pd.read_excel(SCHEDULE_XLSX_PATH)
        df['date'] = df['date'].astype(str).str.split(' ').str[0]
        df['start_time'] = df['start_time'].astype(str)
        
        # Extract slot details from slot_id (simulation)
        # In real implementation, this would use Calendly's booking API
        try:
            slot_index = int(slot_id.split('_')[-1]) if '_' in slot_id else None
        except ValueError:
            return "Error: Invalid slot ID format."
        
        if slot_index is not None and 0 <= slot_index < len(df):
            slot = df.iloc[slot_index]
            
            # Mark the slot as booked
            df.loc[slot_index, 'is_booked'] = True
            df.to_excel(SCHEDULE_XLSX_PATH, index=False)
            
            # Simulate Calendly confirmation
            confirmation = {
                "booking_id": f"calendly_booking_{slot_index}",
                "patient_name": patient_name,
                "doctor": slot['doctor'],
                "date": slot['date'],
                "start_time": str(slot['start_time']),
                "end_time": str(slot['end_time']),
                "location": slot['location'],
                "calendly_link": calendly_link,
                "confirmation_sent": True,
                "calendar_invite_sent": True
            }
            
            email_display = patient_email if patient_email else "your email"
            return f"Success: Calendly booking confirmed! Booking ID: {confirmation['booking_id']}. " \
                   f"Appointment with {slot['doctor']} on {slot['date']} at {slot['start_time']}. " \
                   f"Calendar invite has been sent to {email_display}."
        else:
            return "Error: Invalid slot ID or slot not available in Calendly."
    except Exception as e:
        return f"Calendly booking error: {str(e)}"

@tool
def schedule_enhanced_reminders(booking_id: str, patient_name: str, appointment_date: str, appointment_time: str, doctor_name: str, patient_email: str = "", patient_phone: str = "") -> str:
    """
    Schedules 3 automated reminders with specific actions for each reminder.
    Reminder 1: Regular appointment reminder
    Reminder 2: Ask if forms have been completed
    Reminder 3: Ask for confirmation or cancellation reason
    Returns confirmation of scheduled reminders.
    """
    try:
        # For demo purposes, we'll simulate the scheduling
        # In production, this would use a proper scheduler like APScheduler
        
        # Handle time format - add seconds if not present
        if len(appointment_time.split(':')) == 2:
            appointment_time = appointment_time + ":00"
        appointment_datetime = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M:%S")
        
        # Calculate reminder times (for demo: 1 day, 2 hours, 30 minutes before appointment)
        reminder1_time = appointment_datetime - timedelta(days=1)
        reminder2_time = appointment_datetime - timedelta(hours=2)
        reminder3_time = appointment_datetime - timedelta(minutes=30)
        
        # Store reminder schedule (in production, this would be in a database)
        reminder_schedule = {
            "booking_id": booking_id,
            "patient_name": patient_name,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "doctor_name": doctor_name,
            "patient_email": patient_email,
            "patient_phone": patient_phone,
            "reminders": [
                {
                    "reminder_number": 1,
                    "scheduled_time": reminder1_time.isoformat(),
                    "type": "regular_reminder",
                    "message": f"Reminder: You have an appointment with {doctor_name} on {appointment_date} at {appointment_time}. Please arrive 15 minutes early.",
                    "status": "scheduled"
                },
                {
                    "reminder_number": 2,
                    "scheduled_time": reminder2_time.isoformat(),
                    "type": "forms_check",
                    "message": f"Reminder: Your appointment with {doctor_name} is in 2 hours. Have you completed the intake forms? Please reply YES if completed, NO if not.",
                    "status": "scheduled"
                },
                {
                    "reminder_number": 3,
                    "scheduled_time": reminder3_time.isoformat(),
                    "type": "confirmation_check",
                    "message": f"Final reminder: Your appointment with {doctor_name} is in 30 minutes. Please confirm you're still coming or reply with your cancellation reason.",
                    "status": "scheduled"
                }
            ]
        }
        
        # In production, save to database or scheduler
        print(f"[REMINDER SYSTEM] Scheduled 3 reminders for booking {booking_id}")
        print(f"[REMINDER 1] {reminder1_time.strftime('%Y-%m-%d %H:%M')} - Regular reminder")
        print(f"[REMINDER 2] {reminder2_time.strftime('%Y-%m-%d %H:%M')} - Forms completion check")
        print(f"[REMINDER 3] {reminder3_time.strftime('%Y-%m-%d %H:%M')} - Final confirmation/cancellation")
        
        return f"Success: Enhanced reminder system activated for booking {booking_id}. " \
               f"3 automated reminders scheduled: " \
               f"1) Regular reminder 1 day before, " \
               f"2) Forms completion check 2 hours before, " \
               f"3) Final confirmation 30 minutes before appointment."
    except Exception as e:
        return f"Error scheduling reminders: {str(e)}"

@tool
def send_intake_forms(booking_id: str, patient_name: str, patient_email: str, appointment_date: str, doctor_name: str) -> str:
    """
    Sends patient intake forms via email after appointment confirmation.
    This tool emails the necessary intake forms to the patient.
    Returns confirmation of form delivery.
    """
    try:
        # Simulate form sending
        form_subject = f"Intake Forms for Your Appointment with {doctor_name} - {appointment_date}"
        form_body = f"""
Dear {patient_name},

Thank you for booking your appointment with {doctor_name} on {appointment_date}.

Please find attached the necessary intake forms that need to be completed before your visit:

1. Patient Information Form
2. Medical History Form
3. Insurance Information Form
4. Consent Forms

Please complete these forms and bring them to your appointment, or submit them online if the link is provided.

If you have any questions, please contact our office.

Best regards,
MediCare Clinic Team
        """
        
        # In production, this would use real email service
        print(f"[EMAIL] To: {patient_email}")
        print(f"[EMAIL] Subject: {form_subject}")
        print(f"[EMAIL] Body: {form_body}")
        print(f"[EMAIL] Attachments: Patient Intake Form.pdf, Medical History Form.pdf")
        
        return f"Success: Intake forms sent to {patient_email} for booking {booking_id}. " \
               f"Forms include: Patient Information, Medical History, Insurance Information, and Consent Forms."
    except Exception as e:
        return f"Error sending intake forms: {str(e)}"

# A list containing all the tools we've created.
# This will be used by our agent graph to know what actions it can perform.
all_tools = [lookup_patient, get_calendly_availability, book_calendly_slot, schedule_enhanced_reminders, send_intake_forms, find_available_slots, book_appointment]

