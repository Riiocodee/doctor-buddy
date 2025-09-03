import os
import bcrypt
import datetime
os.environ["JAVA_HOME"] = r"C:\Program Files\Java\jdk-23"
os.environ["PATH"] = os.environ["JAVA_HOME"] + r"\bin;" + os.environ["PATH"]
from pdf2image import convert_from_bytes
import tabula
import streamlit as st
import pandas as pd
import json
from PIL import Image
import pytesseract
import re
import tempfile
from pathlib import Path

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\All programs\poppler-25.07.0\Library\bin")

# Alternatively in Streamlit:
user_poppler_path = st.text_input("Poppler Path", value=POPPLER_PATH)
POPPLER_PATH = user_poppler_path.strip() or POPPLER_PATH


def hash_password(plain_text_password):
    return bcrypt.hashpw(plain_text_password.encode(), bcrypt.gensalt()).decode()

def check_password(plain_text_password, hashed_password):
    try:
        return bcrypt.checkpw(plain_text_password.encode(), hashed_password.encode())
    except Exception:
        return False


def extract_text_from_pdf(pdf_path):
    text = ""
    tmp_path = None
    try:
        dfs = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True, lattice=True)
        if dfs and any(not df.empty for df in dfs):
            for df in dfs:
                text += df.to_csv(index=False) + "\n"
        else:
            raise ValueError("No tables detected")
    except Exception:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(open(pdf_path, "rb").read())
                tmp_path = tmp_file.name

            pages = convert_from_bytes(open(pdf_path, 'rb').read(), poppler_path=POPPLER_PATH)
            for page in pages:
                text += pytesseract.image_to_string(page, config="--psm 6 -l eng") + "\n"
        except Exception as ocr_e:
            print(f"❌ OCR failed: {ocr_e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
    return text




# --- Paths ---
BASE_DIR = Path.cwd()
user_file = BASE_DIR / "users.json"
data_file = BASE_DIR / "patient_data.json"

# --- Load/save JSON ---
def load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return default
                return json.loads(content)
        except json.JSONDecodeError:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

users = load_json(user_file, {})
patient_records = load_json(data_file, {})

save_json(user_file, users)
save_json(data_file, patient_records)

# --- Session state ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "current_user_email" not in st.session_state:
    st.session_state.current_user_email = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- Ensure user records ---
def ensure_user_records(user_email):
    if user_email and user_email not in patient_records:
        patient_records[user_email] = []
        save_json(data_file, patient_records)

# --- Login ---
def login_ui():
    st.title("🔐 Health Checker Login")
    email_phone = st.text_input("📧 Email or 📱 Phone")
    password = st.text_input("🔑 Password", type="password")
    if st.button("Login"):
        if not email_phone.strip():
            st.error("Please enter your email or phone.")
        elif not password:
            st.error("Please enter your password.")
        else:
            if email_phone in users:
                user_data = users[email_phone]
                if check_password(password, user_data["password"]):

                    st.session_state.logged_in = True
                    st.session_state.current_user = user_data["name"]
                    st.session_state.current_user_email = email_phone
                    ensure_user_records(st.session_state.current_user_email)
                    st.success(f"✅ Login successful! Welcome {st.session_state.current_user}")
                    st.session_state["page"] = "main"
                else:
                    st.error("❌ Invalid password")
            else:
                st.error("❌ User not found")



# --- Registration ---
def registration_ui():
    st.write("---")
    st.write("New user? Register below:")
    with st.form("register_form"):
        new_email_phone = st.text_input("📧 New Email/Phone")
        new_name = st.text_input("📝 Full Name")
        new_password = st.text_input("🔑 New Password", type="password")
        new_age = st.number_input("Age (years)", min_value=1, max_value=120, value=25)
        new_sex = st.selectbox("Sex", ["Male", "Female"])
        new_weight = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, value=70.0)
        new_height = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=170.0)
        submitted = st.form_submit_button("Register")

        if submitted:
            if not new_email_phone.strip():
                st.warning("⚠️ Please enter an email or phone.")
            elif not new_name.strip():
                st.warning("⚠️ Please enter your full name.")
            elif not new_password:
                st.warning("⚠️ Please enter a password.")
            elif new_email_phone in users:
                st.warning("⚠️ User already exists. Try logging in.")
            else:
                # Save new user credentials
                users[new_email_phone] = {
                     "name": new_name,
                     "password": hash_password(new_password)
                   }
                save_json(user_file, users)

                # Save initial patient record with demographic info
                patient_records[new_email_phone] = [{
                    "age": new_age,
                    "sex": new_sex,
                    "weight": new_weight,
                    "height_cm": new_height
                }]
                save_json(data_file, patient_records)

                # Set session state to logged in
                st.session_state.logged_in = True
                st.session_state.current_user = new_name
                st.session_state.current_user_email = new_email_phone

                st.success(f"✅ Registered and logged in! Welcome {new_name}")
                st.session_state["page"] = "main"

# Add a new page for profile editing
def profile_ui():
    st.title("👤 Edit Profile")
    user_email = st.session_state.current_user_email
    patient_data = patient_records.get(user_email, [{}])[0]
    user_data = users.get(user_email, {})
    
    with st.form("profile_form"):
        new_name = st.text_input("Full Name", value=user_data.get("name", ""))
        new_age = st.number_input("Age", min_value=1, max_value=120, value=patient_data.get("age", 25))
        new_sex = st.selectbox("Sex", ["Male", "Female"], index=0 if patient_data.get("sex", "Male") == "Male" else 1)
        new_weight = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, value=patient_data.get("weight", 70.0))
        new_height = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=patient_data.get("height_cm", 170.0))

        st.write("**Change Password:**")
        old_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")

        submitted = st.form_submit_button("Save Changes")

        if submitted:
            # Verify old password if changing password
            if new_password or confirm_password:
                if not old_password:
                    st.error("Please enter your current password to change password.")
                    return
                if not check_password(old_password, user_data.get("password", "")):
                    st.error("Current password is incorrect.")
                    return
                if new_password != confirm_password:
                    st.error("New password and confirm password do not match.")
                    return
                # Update password hash
                users[user_email]["password"] = hash_password(new_password)

            # Update name and patient records
            old_name = user_data.get("name", "")
            if new_name and new_name != old_name:
                # Update users dict key if name changes
                users[user_email]["name"] = new_name
                # Update name only
                if new_name and new_name != old_name:
                    users[user_email]["name"] = new_name
                    st.session_state.current_user = new_name

            # Update demographic info
            patient_records[user_email][0] = {
                "age": new_age,
                "sex": new_sex,
                "weight": new_weight,
                "height_cm": new_height
            }

            save_json(user_file, users)
            save_json(data_file, patient_records)
            st.success("Profile updated successfully!")

def extract_text(file):
    """
    Handles uploaded files: PDF, images, or CSV.
    PDF: Try Tabula first, then OCR fallback.
    """
    text = ""
    try:
        if file.type in ["image/jpeg", "image/png"]:
            img = Image.open(file)
            text = pytesseract.image_to_string(img, config="--psm 6")
        elif file.type == "application/pdf":
            # Save uploaded PDF to temp
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file.getbuffer())
                tmp_path = tmp_file.name

            # Extract text using new function
                text = extract_text_from_pdf(tmp_path)
            os.remove(tmp_path)
        elif file.type == "text/csv":
            df = pd.read_csv(file)
            text += df.to_csv(index=False)
    except Exception as e:
        st.warning(f"Failed to parse {file.name}: {e}")
    return text

def parse_lab_values(text):
    lab_data = {}
    patterns = {
    "Glucose": r"(?:Glucose|GLU)\s*[:=]?\s*([\d.]+)",
    "Hemoglobin": r"(?:Hemoglobin|Hb|H B)\s*[:=]?\s*([\d.]+)",
    "Systolic_BP": r"(?:Systolic|Sys\.?)\s*[:=]?\s*([\d]+)",
    "Diastolic_BP": r"(?:Diastolic|Dia\.?)\s*[:=]?\s*([\d]+)",
    "TSH": r"(?:TSH|Thyroid)\s*[:=]?\s*([\d.]+)",
    "ALT": r"(?:ALT|SGPT)\s*[:=]?\s*([\d.]+)",
    "AST": r"(?:AST|SGOT)\s*[:=]?\s*([\d.]+)",
    "Creatinine": r"(?:Creatinine|CREA)\s*[:=]?\s*([\d.]+)",
    "Urea": r"(?:Urea|BUN)\s*[:=]?\s*([\d.]+)",
       # Blood counts
    "WBC": r"WBC(?: count)?\s*[:=]?\s*([\d.]+)",
    "RBC": r"RBC(?: count)?\s*[:=]?\s*([\d.]+)",
    "Platelets": r"(?:PLT|Platelets?)\s*[:=]?\s*([\d.]+)",
    "MCV": r"MCV\s*[:=]?\s*([\d.]+)",
    "MCH": r"MCH\s*[:=]?\s*([\d.]+)",
    "MCHC": r"MCHC\s*[:=]?\s*([\d.]+)",

    # Electrolytes
    "Sodium": r"(?:Sodium|Na[\+\s]*)\s*[:=]?\s*([\d.]+)",
    "Potassium": r"(?:Potassium|K[\+\s]*)\s*[:=]?\s*([\d.]+)",
    "Chloride": r"(?:Chloride|Cl[\-\s]*)\s*[:=]?\s*([\d.]+)",

    # Lipid Profile
    "Total Cholesterol": r"(?:Total\s*)?Cholesterol\s*[:=]?\s*([\d.]+)",
    "LDL": r"LDL\s*[:=]?\s*([\d.]+)",
    "HDL": r"HDL\s*[:=]?\s*([\d.]+)",
    "Triglycerides": r"Triglycerides\s*[:=]?\s*([\d.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                lab_data[key] = float(match.group(1))
            except ValueError:
                continue
    return lab_data

# --- Risk checker ---
def bmi_risk(bmi, age, sex):
    advice = ""
    if age < 18:
        risk = "Check BMI percentile for age & sex"
        advice = "Consult pediatrician for proper growth assessment."
    else:
        if bmi < 18.5:
            risk = "Underweight"
            advice = "Increase calorie intake & balanced diet."
        elif 18.5 <= bmi < 25:
            risk = "Normal weight"
            advice = "Maintain healthy lifestyle."
        elif 25 <= bmi < 30:
            risk = "Overweight"
            advice = "Increase physical activity and monitor diet."
        else:
            risk = "Obese"
            advice = "Consult doctor/nutritionist for weight management."
    if sex.lower() == "female" and bmi >= 25:
        advice += " (Women have slightly higher cardiovascular risk at lower BMI.)"
    return risk, advice

def check_risks(glucose, hb, bmi, systolic_bp, diastolic_bp, labs, age=25, sex="Male"):
    risk = []
    doctors = set()
    advice_list = []

    if glucose >= 120: risk.append("High Glucose"); doctors.add("Endocrinologist")
    bmi_cat, bmi_adv = bmi_risk(bmi, age, sex)
    risk.append(bmi_cat); advice_list.append(bmi_adv)
    if systolic_bp >= 140 or diastolic_bp >= 90: risk.append("High BP"); doctors.add("Cardiologist")
    
    # Thyroid / TSH
    if labs.get("TSH", 0) > 5.0:
        risk.append("High TSH")
        doctors.add("Endocrinologist")

    # Liver enzymes
    if labs.get("ALT", 0) > 45 or labs.get("AST", 0) > 40:
        risk.append("Liver Enzyme High")
        doctors.add("Hepatologist")


    # Kidney
    if labs.get("Creatinine",0) > 1.3 or labs.get("Urea",0) > 50:
        risk.append("Kidney function abnormal")
        doctors.add("Nephrologist")


    # Hemoglobin check based on sex
    hb = labs.get("Hemoglobin", hb)  # Use extracted value if available, else use passed hb

    if hb is not None:
        if sex.lower() == "male" and hb < 13.5:
            risk.append("Low Hemoglobin")
            advice_list.append("Iron-rich diet & check for anemia. ")
            doctors.add("Hematologist")
        elif sex.lower() == "female" and hb < 12.0:
            risk.append("Low Hemoglobin")
            advice_list.append("Iron-rich diet & check for anemia .")
            doctors.add("Hematologist")
 
    if len(risk) == 0:
        overall_health = "Excellent Health"
    elif 1 <= len(risk) <= 2:
        overall_health = "Please monitor your health"
    else:
        overall_health = "Needs medical attention"

    return risk, doctors, advice_list, overall_health

# --- Main App ---
def main_app_ui():
    ensure_user_records(st.session_state.current_user)
    st.title("🩺 Doctor Buddy")
    st.write(f"👋 Welcome, {st.session_state.current_user}!")

    user_records = patient_records.get(st.session_state.current_user, [])
    if user_records:
       latest_info = user_records[0]
       age = int(latest_info.get("age", 25))
       sex = latest_info.get("sex", "Male")
       weight = float(latest_info.get("weight", 70.0))
       height_cm = float(latest_info.get("height_cm", 170.0))
    else:
       age, sex, weight, height_cm = 25, "Male", 70.0, 170.0


    st.write(f"**Age:** {age} | **Sex:** {sex} | **Weight:** {weight} kg | **Height:** {height_cm} cm")

    glucose = st.number_input("Glucose (mg/dL)", value=90.0)
    systolic_bp = st.number_input("Systolic BP (mmHg)", value=120)
    diastolic_bp = st.number_input("Diastolic BP (mmHg)", value=80)
    hemoglobin = st.number_input("Hemoglobin (g/dL)", value=14.0)
    weight = st.number_input("Weight (kg)", value=weight)
    height_cm = st.number_input("Height (cm)", value=height_cm)

    # --- File Upload ---
    st.subheader("📄 Upload Lab Reports / CSV / PDF / Images")
    uploaded_files = st.file_uploader(
        "Choose files", type=['pdf', 'png', 'jpg', 'jpeg', 'csv'], accept_multiple_files=True
    )

    extracted_data_per_file = {}

    if uploaded_files:
        for file in uploaded_files:
            raw_text = extract_text(file)
            lab_values = parse_lab_values(raw_text)
            extracted_data_per_file[file.name] = lab_values

             # ✅ Debug: Show raw extracted text
            with st.expander(f"🧾 Show Raw Text for {file.name}"):
                st.text(raw_text)

    if extracted_data_per_file:
        st.subheader("📄 Extracted Lab Values by File")
        for fname, labs in extracted_data_per_file.items():
            st.markdown(f"**File:** {fname}")
            if labs:
                df = pd.DataFrame(list(labs.items()), columns=["Lab Test", "Value"])
                st.dataframe(df)
            else:
                st.write("_No lab values detected._")
            st.write("---")

    # Merge all lab values as before to extracted_data dict
    extracted_data = {}
    for labs in extracted_data_per_file.values():
        for k, v in labs.items():
            if v is not None:
                if k not in extracted_data or v > extracted_data[k]:
                    extracted_data[k] = v



        glucose = extracted_data.get("Glucose", glucose)
        hemoglobin = extracted_data.get("Hemoglobin", hemoglobin)
        systolic_bp = extracted_data.get("Systolic_BP", systolic_bp)
        diastolic_bp = extracted_data.get("Diastolic_BP", diastolic_bp)
            
        extracted_data["Glucose"] = glucose
        extracted_data["Hemoglobin"] = hemoglobin
        extracted_data["Systolic_BP"] = systolic_bp
        extracted_data["Diastolic_BP"] = diastolic_bp
   
    bmi = round(weight / ((height_cm / 100) ** 2), 2)
    st.write(f"**BMI:** {bmi}")

    if st.button("Check Risk"):
        glucose = float(glucose)
        hemoglobin = float(hemoglobin)
        systolic_bp = float(systolic_bp)
        diastolic_bp = float(diastolic_bp)
        bmi = float(bmi)

        risk, doctors, advice, overall_health = check_risks(
            glucose=glucose,
            hb=hemoglobin,
            bmi=bmi,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            labs=extracted_data,
            age=age,
            sex=sex
        )


        st.subheader("Results Summary")
        st.write(f"**Overall Health:** {overall_health}")
        if risk: st.write("Risks:", risk)
        if doctors: st.write("See specialists:", ", ".join(doctors))
        if advice: st.write("Advice:", advice)

        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "age": age,
            "sex": sex,
            "weight": weight,
            "height_cm": height_cm,
            "glucose": glucose,
            "bmi": bmi,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "hemoglobin": hemoglobin,
            "labs": extracted_data,
            "overall_health": overall_health,
            "risk": risk
        }
        patient_records[st.session_state.current_user].append(record)
        save_json(data_file, patient_records)

    past_records = patient_records.get(st.session_state.current_user, [])
    if past_records:
     st.subheader("📋 Your Past Records")
     df = pd.DataFrame(past_records)
     st.dataframe(df)

     csv_data = df.to_csv(index=False).encode("utf-8")
     st.download_button(
        label="📥 Download Records as CSV",
        data=csv_data,
        file_name="my_health_records.csv",
        mime="text/csv",
    )
    else:
     st.info("No past records found.")


    st.subheader("💡 Healthy Lifestyle Tips")
    st.markdown("""
    - 🥗 Eat a balanced diet with fruits & vegetables  
    - 🚶 Exercise at least 30 minutes daily  
    - 💧 Drink enough water  
    - 💤 Sleep 7-8 hours every night  
    - 🚭 Avoid smoking & limit alcohol  
    - 🧘 Manage stress with meditation/yoga
    """)

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.current_user_email = None
        st.experimental_rerun()


 # --- Sidebar Navigation ---
if st.session_state.logged_in:
    st.sidebar.title("🔧 Navigation")
    choice = st.sidebar.radio("Go to", ["🏠 Home", "👤 Profile", "🚪 Logout"])

    if choice == "🏠 Home":
        st.session_state.page = "main"
    elif choice == "👤 Profile":
        st.session_state.page = "profile"
    elif choice == "🚪 Logout":
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.current_user_email = None
        st.session_state.page = "login"
        st.experimental_rerun()

    
# --- Page Routing ---
if not st.session_state.logged_in or st.session_state.page == "login":
    login_ui()
    registration_ui()
elif st.session_state.page == "main":
    main_app_ui()
elif st.session_state.page == "profile":
    profile_ui()

