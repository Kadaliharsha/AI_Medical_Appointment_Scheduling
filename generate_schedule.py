import pandas as pd
from datetime import datetime, timedelta

def generate_schedules():
    """
    Generates a synthetic doctor schedule for the next 14 days in 30-minute slots
    and saves it as an Excel file.
    """
    doctors = {
        "Dr. Sharma": {"location": "Main Clinic", "days": [0, 2, 4]},  # Mon, Wed, Fri
        "Dr. Verma": {"location": "City Hospital", "days": [1, 3]}     # Tue, Thu
    }
    
    start_date = datetime.now().date()
    num_days = 14
    
    all_slots = []

    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        day_of_week = current_date.weekday() # Monday is 0 and Sunday is 6

        for doc_name, details in doctors.items():
            if day_of_week in details["days"]:
                # Assume working hours are 9 AM to 5 PM
                start_hour = 9
                end_hour = 17
                
                for hour in range(start_hour, end_hour):
                    for minute in [0, 30]:
                        slot_start_time = f"{hour:02d}:{minute:02d}"
                        
                        # Calculate end time
                        if minute == 0:
                            slot_end_time = f"{hour:02d}:30"
                        else:
                            slot_end_time = f"{(hour + 1):02d}:00"
                            
                        all_slots.append({
                            "doctor": doc_name,
                            "location": details["location"],
                            "date": current_date.strftime('%Y-%m-%d'),
                            "start_time": slot_start_time,
                            "end_time": slot_end_time,
                            "is_booked": False # All slots start as available
                        })

    df = pd.DataFrame(all_slots)
    
    # Save to Excel file inside the app/data directory
    output_path = 'app/data/schedules.xlsx'
    df.to_excel(output_path, index=False)
    
    print(f"Successfully generated doctor schedules and saved to '{output_path}'")

if __name__ == "__main__":
    # To run this script, you need pandas and openpyxl:
    # pip install pandas openpyxl
    generate_schedules()
