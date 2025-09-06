import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- Core Configuration ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Data File Paths ---
DATA_DIR = os.path.join(BASE_DIR, 'app', 'data')
PATIENT_CSV_PATH = os.path.join(DATA_DIR, 'patients.csv')
SCHEDULE_XLSX_PATH = os.path.join(DATA_DIR, 'schedules.xlsx')
FORMS_DIR = os.path.join(DATA_DIR, 'forms')

# --- Export File Paths ---
EXPORTS_DIR = os.path.join(BASE_DIR, 'app', 'exports')
os.makedirs(EXPORTS_DIR, exist_ok=True)

# --- API Keys ---
# Load the OpenAI API key for the ChatGPT model
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Agent Configuration ---
# We will use an OpenAI model now
AGENT_MODEL_NAME = "gpt-4o-mini"

# --- Email Configuration ---
USE_REAL_EMAIL = os.getenv("USE_REAL_EMAIL", "0") == "1"

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
