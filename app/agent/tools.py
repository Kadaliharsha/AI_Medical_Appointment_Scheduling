import pandas as pd
from langchain.tools import tool
from datetime import datetime, timedelta, timezone
from app.config import PATIENT_CSV_PATH, SCHEDULE_XLSX_PATH, FORMS_DIR, USE_REAL_EMAIL, EXPORTS_DIR
import os


def _normalize_date_string(date_str: str) -> str:
    """
    Accept flexible human date inputs (e.g., "September 10, 2025", "2025/09/10")
    and return canonical YYYY-MM-DD string. Falls back to original if parsing fails.
    """
    try:
        # pandas is robust to many formats
        parsed = pd.to_datetime(str(date_str), errors='raise')
        return parsed.strftime('%Y-%m-%d')
    except Exception:
        # Last resort: try common formats
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
            try:
                parsed = datetime.strptime(str(date_str), fmt)
                return parsed.strftime('%Y-%m-%d')
            except Exception:
                continue
        return str(date_str)

@tool
def lookup_patient(first_name: str, last_name: str, dob: str) -> dict:
    """
    Looks up a patient in the patient database (patients.csv) using their
    first name, last name, and date of birth (YYYY-MM-DD).
    Returns the patient's details if found, otherwise indicates the patient is new.
    """
    try:
        df = pd.read_csv(PATIENT_CSV_PATH)
        # Normalize and strip all relevant fields in both input and CSV
        def norm(s):
            return str(s).strip().lower()
        input_first = norm(first_name)
        input_last = norm(last_name)
        input_dob = str(dob).strip()
        df['first_name_norm'] = df['first_name'].astype(str).str.strip().str.lower()
        df['last_name_norm'] = df['last_name'].astype(str).str.strip().str.lower()
        df['dob_norm'] = df['dob'].astype(str).str.strip()
        patient = df[
            (df['first_name_norm'] == input_first) &
            (df['last_name_norm'] == input_last) &
            (df['dob_norm'] == input_dob)
        ]
        if not patient.empty:
            return patient.drop(columns=['first_name_norm','last_name_norm','dob_norm']).to_dict('records')[0]
        else:
            return {"message": "Patient not found. This is a new patient."}
    except Exception as e:
        return {"error": f"An error occurred while looking up the patient: {str(e)}"}

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
        
        # Handle merged 60-minute slot IDs: calendly_pair_i_j
        if slot_id.startswith("calendly_pair_"):
            try:
                _, _, i_str, j_str = slot_id.split('_')
                idx1 = int(i_str)
                idx2 = int(j_str)
            except Exception:
                return "Error: Invalid merged slot ID format."

            if idx1 in df.index and idx2 in df.index:
                slot1 = df.loc[idx1]
                slot2 = df.loc[idx2]
                if (not bool(slot1['is_booked'])) and (not bool(slot2['is_booked'])):
                    df.loc[idx1, 'is_booked'] = True
                    df.loc[idx2, 'is_booked'] = True
                    df.to_excel(SCHEDULE_XLSX_PATH, index=False)

                    email_display = patient_email if patient_email else "your email"
                    booking_id = f"calendly_booking_{idx1}_{idx2}"
                    
                    # Export admin record (60-minute merged)
                    try:
                        export_appointment.invoke({
                            "booking_id": booking_id,
                            "patient_name": patient_name,
                            "patient_email": patient_email or "",
                            "patient_phone": "",
                            "doctor": str(slot1['doctor']),
                            "date": str(slot1['date']),
                            "start_time": str(slot1['start_time']),
                            "end_time": str(slot2['end_time']),
                            "duration_minutes": 60,
                            "location": str(slot1['location'])
                        })
                    except Exception as _:
                        pass

                    # Automatically send intake forms if email is provided
                    forms_message = ""
                    if patient_email and '@' in patient_email:
                        try:
                            forms_result = send_intake_forms.invoke({
                                "booking_id": booking_id,
                                "patient_name": patient_name,
                                "patient_email": patient_email,
                                "appointment_date": str(slot1['date']),
                                "doctor_name": str(slot1['doctor'])
                            })
                            if "Success" in forms_result:
                                forms_message = " Intake forms have been sent to your email."
                            else:
                                forms_message = f" Note: {forms_result}"
                        except Exception as e:
                            forms_message = f" Note: Could not send intake forms: {str(e)}"

                    return (
                        f"Success: Calendly booking confirmed! Booking ID: {booking_id}. "
                        f"Appointment with {slot1['doctor']} on {slot1['date']} from {slot1['start_time']} to {slot2['end_time']}. "
                        f"Calendar invite has been sent to {email_display}.{forms_message}"
                    )
                else:
                    return "Error: One of the paired slots is already booked."
            else:
                return "Error: Paired slot indices not found."

        # Extract single-slot index format: calendly_<index>
        try:
            slot_index = int(slot_id.split('_')[-1]) if '_' in slot_id else None
        except ValueError:
            return "Error: Invalid slot ID format."

        if slot_index is not None and 0 <= slot_index < len(df):
            slot = df.iloc[slot_index]
            if bool(slot['is_booked']):
                return "Error: This slot is already booked."

            df.loc[slot_index, 'is_booked'] = True
            df.to_excel(SCHEDULE_XLSX_PATH, index=False)

            email_display = patient_email if patient_email else "your email"
            booking_id = f"calendly_booking_{slot_index}"
            
            # Export admin record (30-minute single)
            try:
                export_appointment.invoke({
                    "booking_id": booking_id,
                    "patient_name": patient_name,
                    "patient_email": patient_email or "",
                    "patient_phone": "",
                    "doctor": str(slot['doctor']),
                    "date": str(slot['date']),
                    "start_time": str(slot['start_time']),
                    "end_time": str(slot['end_time']),
                    "duration_minutes": 30,
                    "location": str(slot['location'])
                })
            except Exception as _:
                pass

            # Automatically send intake forms if email is provided
            forms_message = ""
            if patient_email and '@' in patient_email:
                try:
                    forms_result = send_intake_forms.invoke({
                        "booking_id": booking_id,
                        "patient_name": patient_name,
                        "patient_email": patient_email,
                        "appointment_date": str(slot['date']),
                        "doctor_name": str(slot['doctor'])
                    })
                    if "Success" in forms_result:
                        forms_message = " Intake forms have been sent to your email."
                    else:
                        forms_message = f" Note: {forms_result}"
                except Exception as e:
                    forms_message = f" Note: Could not send intake forms: {str(e)}"

            return (
                f"Success: Calendly booking confirmed! Booking ID: {booking_id}. "
                f"Appointment with {slot['doctor']} on {slot['date']} at {slot['start_time']}. "
                f"Calendar invite has been sent to {email_display}.{forms_message}"
            )
        else:
            return "Error: Invalid slot ID or slot not available in Calendly."
    except Exception as e:
        return f"Calendly booking error: {str(e)}"

@tool
def get_calendly_availability_with_duration(calendly_link: str, date: str, required_duration_minutes: int, doctor_name: str = "") -> list:
    """
    Duration-aware Calendly availability. For 60-minute appointments, this merges
    two consecutive 30-minute free slots into one 60-minute option.
    Returns a list of slots in Calendly-like format. Slot IDs for merged pairs use
    the form: "calendly_pair_{i}_{j}" where i and j are row indices in the schedule.
    """
    try:
        df = pd.read_excel(SCHEDULE_XLSX_PATH)
        df['date'] = df['date'].astype(str).str.split(' ').str[0]
        date_str = _normalize_date_string(date)
        # Use datetime objects for robust comparison
        try:
            requested_date = datetime.strptime(date_str, '%Y-%m-%d')
            today_date = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            print(f"[DEBUG] Date comparison: date_str={date_str}, requested_date={requested_date}, today_date={today_date}")
            if requested_date < today_date:
                user_date = requested_date.strftime('%B %d, %Y')
                print(f"[DEBUG] Date rejected: requested_date < today_date")
                return [{"error": f"{user_date} is in the past. Please choose today or a future date."}]
        except Exception as e:
            print(f"[DEBUG] Date parsing error: {e}, date_str={date_str}")
            # If parsing fails, fallback to string comparison
            today_str = datetime.today().strftime('%Y-%m-%d')
            print(f"[DEBUG] String comparison: date_str={date_str}, today_str={today_str}")
            if isinstance(date_str, str) and date_str < today_str:
                user_date = date_str
                print(f"[DEBUG] Date rejected (string): date_str < today_str")
                return [{"error": f"{user_date} is in the past. Please choose today or a future date."}]
        # Determine doctor explicitly if provided; otherwise fall back to link heuristic
        if not doctor_name:
            doctor_name = "Dr. Sharma" if "sharma" in calendly_link.lower() else "Dr. Verma"

        day_slots = df[(df['doctor'].str.lower() == doctor_name.lower()) & (df['date'] == date) & (df['is_booked'] == False)].copy()
        if day_slots.empty:
            return [{"message": "No available slots found for the specified date."}]

        # Normalize times to datetime for sequencing
        day_slots['start_time_str'] = day_slots['start_time'].astype(str)
        day_slots['end_time_str'] = day_slots['end_time'].astype(str)
        day_slots['start_dt'] = pd.to_datetime(day_slots['date'] + ' ' + day_slots['start_time_str'])
        day_slots['end_dt'] = pd.to_datetime(day_slots['date'] + ' ' + day_slots['end_time_str'])
        day_slots = day_slots.sort_values('start_dt')

        results = []
        if required_duration_minutes <= 30:
            for idx, slot in day_slots.iterrows():
                results.append({
                    "slot_id": f"calendly_{idx}",
                    "start_time": str(slot['start_time']),
                    "end_time": str(slot['end_time']),
                    "duration_minutes": 30,
                    "available": True,
                    "calendly_link": calendly_link,
                    "doctor": slot['doctor'],
                    "location": slot['location']
                })
            return results

        # For 60 minutes: find consecutive pairs where end of first == start of second
        indices = list(day_slots.index)
        for i in range(len(indices) - 1):
            idx1 = indices[i]
            idx2 = indices[i + 1]
            s1 = day_slots.loc[idx1]
            s2 = day_slots.loc[idx2]
            # Robust adjacency check: exact match on strings OR <= 1 minute gap
            string_adjacent = str(s1['end_time_str']) == str(s2['start_time_str'])
            time_gap = (s2['start_dt'] - s1['end_dt']).total_seconds()
            near_adjacent = 0 <= time_gap <= 60  # allow up to 1 minute tolerance
            if string_adjacent or near_adjacent:
                results.append({
                    "slot_id": f"calendly_pair_{idx1}_{idx2}",
                    "start_time": str(s1['start_time']),
                    "end_time": str(s2['end_time']),
                    "duration_minutes": 60,
                    "available": True,
                    "calendly_link": calendly_link,
                    "doctor": s1['doctor'],
                    "location": s1['location']
                })
        if not results:
            return [{"message": "No 60-minute continuous slots available. Please try another date."}]
        return results
    except Exception as e:
        return [{"error": f"Calendly duration search error: {str(e)}"}]

@tool
def save_new_patient(first_name: str, last_name: str, dob: str, email: str = "", phone: str = "", preferred_doctor: str = "", location: str = "") -> str:
    """
    Persist a newly identified patient into patients.csv with duplicate protection.
    A duplicate is same first+last (case-insensitive) and exact DOB (YYYY-MM-DD).
    Adds fields if the CSV doesn't already contain them.
    """
    try:
        # Normalize inputs
        first = (first_name or "").strip()
        last = (last_name or "").strip()
        dob_norm = _normalize_date_string(dob or "").strip()
        email = (email or "").strip()
        phone = (phone or "").strip()
        preferred_doctor = (preferred_doctor or "").strip()
        location = (location or "").strip()
        # Define missing fields as empty strings
        insurance_carrier = ""
        member_id = ""
        group_id = ""

        # Load existing or create new DataFrame
        if os.path.exists(PATIENT_CSV_PATH):
            df = pd.read_csv(PATIENT_CSV_PATH)
        else:
            df = pd.DataFrame(columns=[
                'first_name','last_name','dob','email','phone','preferred_doctor','location','created_at'
            ])

        # Prepare for case-insensitive match; handle missing columns gracefully
        if 'first_name' in df.columns and 'last_name' in df.columns and 'dob' in df.columns:
            mask = (
                df['first_name'].astype(str).str.lower() == first.lower()
            ) & (
                df['last_name'].astype(str).str.lower() == last.lower()
            ) & (
                df['dob'].astype(str) == dob_norm
            )
            if df[mask].shape[0] > 0:
                # Update missing details for existing patient
                update_fields = {
                    'email': email,
                    'phone': phone,
                    'preferred_doctor': preferred_doctor,
                    'location': location,
                    'insurance_carrier': insurance_carrier,
                    'member_id': member_id,
                    'group_id': group_id
                }
                for field, value in update_fields.items():
                    if value:
                        df.loc[mask, field] = value
                df.to_csv(PATIENT_CSV_PATH, index=False)
                return f"Success: Updated details for existing patient {first} {last} ({dob_norm}) in the EMR."

        # Build new row
        new_row = {
            'first_name': first,
            'last_name': last,
            'dob': dob_norm,
            'email': email,
            'phone': phone,
            'preferred_doctor': preferred_doctor,
            'location': location,
            'insurance_carrier': insurance_carrier,
            'member_id': member_id,
            'group_id': group_id,
            'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        }

        # Ensure all columns exist; extend df columns if needed
        for key in new_row.keys():
            if key not in df.columns:
                df[key] = ""

        # Append row and save
        df = df.reindex(columns=list(df.columns))
        row_df = pd.DataFrame([{col: new_row.get(col, "") for col in df.columns}])
        df = pd.concat([df, row_df], ignore_index=True)
        df.to_csv(PATIENT_CSV_PATH, index=False)

        return f"Success: Added new patient {first} {last} ({dob_norm}) to the EMR."
    except Exception as e:
        return f"Error saving new patient: {str(e)}"

@tool
def export_appointment(booking_id: str, patient_name: str, patient_email: str, patient_phone: str, doctor: str, date: str, start_time: str, end_time: str, duration_minutes: int, location: str) -> str:
    """
    Append a confirmed appointment to app/exports/appointments.xlsx.
    Creates the file with headers if missing.
    """
    try:
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        export_path = os.path.join(EXPORTS_DIR, 'appointments.xlsx')

        required_cols = [
            'booking_id', 'patient_name', 'patient_email', 'patient_phone',
            'doctor', 'location', 'date', 'start_time', 'end_time',
            'duration_minutes', 'created_at'
        ]

        record = {
            'booking_id': str(booking_id),
            'patient_name': str(patient_name),
            'patient_email': str(patient_email or ''),
            'patient_phone': str(patient_phone or ''),
            'doctor': str(doctor),
            'location': str(location or ''),
            'date': _normalize_date_string(date),
            'start_time': str(start_time),
            'end_time': str(end_time),
            'duration_minutes': int(duration_minutes),
            'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        }

        if os.path.exists(export_path):
            existing = pd.read_excel(export_path)
            # Normalize existing to required schema only
            for col in required_cols:
                if col not in existing.columns:
                    existing[col] = ''
            existing = existing[required_cols]
        else:
            existing = pd.DataFrame(columns=required_cols)

        new_row = pd.DataFrame([[record[c] for c in required_cols]], columns=required_cols)
        out_df = pd.concat([existing, new_row], ignore_index=True)

        with pd.ExcelWriter(export_path, engine='openpyxl', mode='w') as writer:
            out_df.to_excel(writer, index=False)
        return f"Success: Exported booking {booking_id} to appointments.xlsx"
    except Exception as e:
        return f"Error exporting appointment: {str(e)}"

@tool
def build_admin_report(start_date: str, end_date: str) -> str:
    """
    Build an admin summary report (appointments_report.xlsx) for a date range.
    Summary tab by date and doctor; Raw tab with filtered rows.
    """
    try:
        export_path = os.path.join(EXPORTS_DIR, 'appointments.xlsx')
        if not os.path.exists(export_path):
            return "Error: No appointments.xlsx found to build a report."

        df = pd.read_excel(export_path)
        if df.empty:
            return "Error: appointments.xlsx has no rows."

        s = _normalize_date_string(start_date)
        e = _normalize_date_string(end_date)

        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        mask = (df['date'] >= s) & (df['date'] <= e)
        filt = df[mask].copy()
        if filt.empty:
            return f"Info: No appointments between {s} and {e}."

        # Convert duration to numeric
        filt['duration_minutes'] = pd.to_numeric(filt['duration_minutes'], errors='coerce').fillna(0).astype(int)

        # Summary by date/doctor
        summary = (
            filt.groupby(['date', 'doctor'])
            .agg(total_appointments=('booking_id', 'count'),
                 total_minutes_booked=('duration_minutes', 'sum'),
                 avg_duration_minutes=('duration_minutes', 'mean'))
            .reset_index()
        )
        summary['avg_duration_minutes'] = summary['avg_duration_minutes'].round(1)

        report_path = os.path.join(EXPORTS_DIR, 'appointments_report.xlsx')
        with pd.ExcelWriter(report_path, engine='openpyxl', mode='w') as writer:
            summary.to_excel(writer, index=False, sheet_name='Summary')
            filt.to_excel(writer, index=False, sheet_name='Raw')

        return f"Success: Admin report saved to {report_path}"
    except Exception as e:
        return f"Error building report: {str(e)}"

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
def validate_email_config() -> str:
    """
    Validates the email configuration and provides setup instructions.
    This tool checks if SMTP settings are properly configured for sending emails.
    Returns a status report with configuration details and setup instructions.
    """
    try:
        from app.config import USE_REAL_EMAIL, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
        
        config_status = {
            "USE_REAL_EMAIL": USE_REAL_EMAIL,
            "SMTP_SERVER": SMTP_SERVER,
            "SMTP_PORT": SMTP_PORT,
            "SMTP_USERNAME": "SET" if SMTP_USERNAME else "MISSING",
            "SMTP_PASSWORD": "SET" if SMTP_PASSWORD else "MISSING"
        }
        
        issues = []
        if not USE_REAL_EMAIL:
            issues.append("Real email is disabled (USE_REAL_EMAIL=0)")
        if not SMTP_USERNAME:
            issues.append("SMTP username not set")
        if not SMTP_PASSWORD:
            issues.append("SMTP password not set")
        
        status_report = f"Email Configuration Status:\n"
        for key, value in config_status.items():
            status_report += f"- {key}: {value}\n"
        
        if issues:
            status_report += f"\nIssues found:\n"
            for issue in issues:
                status_report += f"- {issue}\n"
            
            status_report += f"\nTo fix these issues, add the following to your .env file:\n"
            status_report += f"USE_REAL_EMAIL=1\n"
            status_report += f"SMTP_SERVER={SMTP_SERVER}\n"
            status_report += f"SMTP_PORT={SMTP_PORT}\n"
            status_report += f"SMTP_USERNAME=your_email@gmail.com\n"
            status_report += f"SMTP_PASSWORD=your_app_password\n"
            status_report += f"\nNote: For Gmail, you need to use an App Password, not your regular password."
        else:
            status_report += f"\n✅ Email configuration looks good!"
        
        return status_report
    except Exception as e:
        return f"Error validating email configuration: {str(e)}"

@tool
def send_intake_forms(booking_id: str, patient_name: str, patient_email: str, appointment_date: str, doctor_name: str) -> str:
    """
    Sends patient intake forms via email after appointment confirmation.
    This tool emails the necessary intake forms to the patient.
    Returns confirmation of form delivery.
    """
    print(f"[DEBUG] send_intake_forms called for booking_id={booking_id}, patient_email={patient_email}")
    try:
        # Require a valid recipient email
        if not patient_email or '@' not in patient_email:
            return "Error: A valid patient_email is required to send intake forms. Please provide and confirm the patient's email address."

        # Check if forms directory exists
        if not os.path.exists(FORMS_DIR):
            return f"Error: Forms directory not found at {FORMS_DIR}"
        
        # Get list of available form files
        form_files = []
        for file in os.listdir(FORMS_DIR):
            if file.endswith(('.pdf', '.doc', '.docx')):
                form_files.append(file)
        
        if not form_files:
            return f"Error: No form files found in {FORMS_DIR}"
        
        # Read the main intake form PDF
        main_form_path = os.path.join(FORMS_DIR, "New Patient Intake Form.pdf")
        form_attachments = []
        
        if os.path.exists(main_form_path):
            try:
                with open(main_form_path, 'rb') as f:
                    form_content = f.read()
                    form_size = len(form_content)
                    form_attachments.append({
                        "filename": "New Patient Intake Form.pdf",
                        "size": form_size,
                        "content": form_content
                    })
                print(f"[FORM READ] Successfully read 'New Patient Intake Form.pdf' ({form_size} bytes)")
            except Exception as e:
                print(f"[FORM READ ERROR] Could not read main form: {str(e)}")
        
        # Read other available forms
        for form_file in form_files:
            if form_file != "New Patient Intake Form.pdf":
                form_path = os.path.join(FORMS_DIR, form_file)
                try:
                    with open(form_path, 'rb') as f:
                        form_content = f.read()
                        form_size = len(form_content)
                        form_attachments.append({
                            "filename": form_file,
                            "size": form_size,
                            "content": form_content
                        })
                    print(f"[FORM READ] Successfully read '{form_file}' ({form_size} bytes)")
                except Exception as e:
                    print(f"[FORM READ ERROR] Could not read {form_file}: {str(e)}")
        
        # Prepare email content
        form_subject = f"Intake Forms for Your Appointment with {doctor_name} - {appointment_date}"
        form_body = f"""
Dear {patient_name},

Thank you for booking your appointment with {doctor_name} on {appointment_date}.

Please find attached the necessary intake forms that need to be completed before your visit:

"""
        
        # Add form list to email body
        for i, attachment in enumerate(form_attachments, 1):
            form_body += f"{i}. {attachment['filename']}\n"
        
        form_body += f"""
Total forms attached: {len(form_attachments)}

Please complete these forms and bring them to your appointment, or submit them online if the link is provided.

If you have any questions, please contact our office.

Best regards,
MediCare Clinic Team
        """
        
        # Simulate email sending with actual form data
        print(f"[EMAIL] To: {patient_email}")
        print(f"[EMAIL] Subject: {form_subject}")
        print(f"[EMAIL] Body: {form_body}")
        print(f"[EMAIL] Attachments: {len(form_attachments)} files")
        
        for attachment in form_attachments:
            print(f"[EMAIL] - {attachment['filename']} ({attachment['size']} bytes)")
        
        # Real email service integration (when USE_REAL_EMAIL=True)
        if USE_REAL_EMAIL:
            print(f"[REAL EMAIL BLOCK] USE_REAL_EMAIL is True. Attempting to send real email...")
            
            # Validate SMTP configuration
            from app.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
            if not SMTP_USERNAME or not SMTP_PASSWORD:
                print(f"[REAL EMAIL ERROR] SMTP credentials not configured. SMTP_USERNAME: {'SET' if SMTP_USERNAME else 'MISSING'}, SMTP_PASSWORD: {'SET' if SMTP_PASSWORD else 'MISSING'}")
                return f"Error: Email configuration incomplete. SMTP credentials not properly set. Please check your .env file."
            
            try:
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                from email.mime.application import MIMEApplication
                import smtplib
                import time
                
                # Create email message
                msg = MIMEMultipart()
                msg['From'] = SMTP_USERNAME
                msg['To'] = patient_email
                msg['Subject'] = form_subject
                
                # Add email body
                msg.attach(MIMEText(form_body, 'plain'))
                
                # Attach form files
                for attachment in form_attachments:
                    pdf_attachment = MIMEApplication(attachment['content'], _subtype='pdf')
                    pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                            filename=attachment['filename'])
                    msg.attach(pdf_attachment)
                
                # Retry logic for email sending
                max_retries = 3
                retry_delay = 2  # seconds
                
                for attempt in range(max_retries):
                    try:
                        print(f"[REAL EMAIL] Attempt {attempt + 1}/{max_retries} - Connecting to {SMTP_SERVER}:{SMTP_PORT}")
                        
                        # Create SMTP connection with timeout
                        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
                        server.set_debuglevel(0)  # Set to 1 for debug output
                        
                        # Enable TLS
                        server.starttls()
                        
                        # Login with credentials
                        server.login(SMTP_USERNAME, SMTP_PASSWORD)
                        
                        # Send the email
                        server.send_message(msg)
                        server.quit()
                        
                        print(f"[REAL EMAIL] Successfully sent email with {len(form_attachments)} attachments to {patient_email}")
                        break  # Success, exit retry loop
                        
                    except smtplib.SMTPAuthenticationError as e:
                        print(f"[REAL EMAIL ERROR] Authentication failed: {str(e)}")
                        return f"Error: Email authentication failed. Please check your SMTP username and password in the .env file."
                    except smtplib.SMTPRecipientsRefused as e:
                        print(f"[REAL EMAIL ERROR] Recipient refused: {str(e)}")
                        return f"Error: Email address {patient_email} was refused by the server. Please verify the email address."
                    except smtplib.SMTPServerDisconnected as e:
                        print(f"[REAL EMAIL ERROR] Server disconnected: {str(e)}")
                        if attempt < max_retries - 1:
                            print(f"[REAL EMAIL] Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            return f"Error: Email server connection failed after {max_retries} attempts. Please check your internet connection and SMTP settings."
                    except smtplib.SMTPException as e:
                        print(f"[REAL EMAIL ERROR] SMTP error: {str(e)}")
                        if attempt < max_retries - 1:
                            print(f"[REAL EMAIL] Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            return f"Error: Email sending failed after {max_retries} attempts. SMTP error: {str(e)}"
                    except Exception as e:
                        print(f"[REAL EMAIL ERROR] Unexpected error: {str(e)}")
                        if attempt < max_retries - 1:
                            print(f"[REAL EMAIL] Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            return f"Error: Email sending failed after {max_retries} attempts. Error: {str(e)}"
                else:
                    # This runs if the for loop completes without breaking
                    return f"Error: Email sending failed after {max_retries} attempts. Please try again later or contact support."
                
            except Exception as e:
                print(f"[REAL EMAIL ERROR] Critical error: {str(e)}")
                return f"Error: Critical email error: {str(e)}"
        else:
            print("[EMAIL SIMULATION] Real email disabled - using simulation mode")
        
        return f"Success: Intake forms sent to {patient_email} for booking {booking_id}. " \
               f"Attached {len(form_attachments)} form(s): {', '.join([att['filename'] for att in form_attachments])}"
    except Exception as e:
        return f"Error sending intake forms: {str(e)}"

all_tools = [
    lookup_patient,
    get_calendly_availability_with_duration,  # duration-aware availability (authoritative)
    book_calendly_slot,
    save_new_patient,
    export_appointment,
    build_admin_report,
    schedule_enhanced_reminders,
    validate_email_config,
    send_intake_forms,
]
