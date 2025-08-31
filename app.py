import os

os.environ["JAVA_HOME"] = r"C:\Program Files\Java\jdk-23"
os.environ["PATH"] = os.environ["JAVA_HOME"] + r"\bin;" + os.environ["PATH"]

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

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
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

# --- Normalize old users ---
for k, v in list(users.items()):
    if isinstance(v, str):
        users[k] = {"name": k, "password": v}
    elif isinstance(v, dict):
        if "name" not in v or not v["name"]:
            users[k]["name"] = k

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
def ensure_user_records(user_name):
    if user_name and user_name not in patient_records:
        patient_records[user_name] = []
        save_json(data_file, patient_records)

# --- Login ---
def login_ui():
    st.title("🔐 Health Checker Login")
    email_phone = st.text_input("📧 Email or 📱 Phone")
    password = st.text_input("🔑 Password", type="password")
    if st.button("Login"):
        if email_phone in users:
            user_data = users[email_phone]
            if user_data["password"] == password:
                st.session_state.logged_in = True
                st.session_state.current_user = user_data["name"]
                st.session_state.current_user_email = email_phone
                ensure_user_records(st.session_state.current_user)
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
            if new_email_phone in users:
                st.warning("⚠️ User already exists. Try logging in.")
            else:
                users[new_email_phone] = {"name": new_name, "password": new_password}
                save_json(user_file, users)
                patient_records[new_name] = [{
                    "age": new_age,
                    "sex": new_sex,
                    "weight": new_weight,
                    "height_cm": new_height
                }]
                save_json(data_file, patient_records)
                st.session_state.logged_in = True
                st.session_state.current_user = new_name
                st.session_state.current_user_email = new_email_phone
                st.success(f"✅ Registered and logged in! Welcome {new_name}")
                st.session_state["page"] = "main"

# --- Unified File Parser + Lab Extraction ---
def extract_text(file):
    text = ""
    try:
        if file.type in ["image/jpeg", "image/png"]:
            img = Image.open(file)
            text = pytesseract.image_to_string(img, config="--psm 6")
        elif file.type == "application/pdf":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file.getbuffer())
                tmp_path = tmp_file.name
            dfs = tabula.read_pdf(tmp_path, pages="all", multiple_tables=True)
            os.remove(tmp_path)
            if dfs:
                for df in dfs:
                    text += df.to_csv(index=False) + "\n"
        elif file.type == "text/csv":
            df = pd.read_csv(file)
            text += df.to_csv(index=False)
    except Exception as e:
        st.warning(f"Failed to parse {file.name}: {e}")
    return text

def parse_lab_values(text):
    lab_data = {}
    patterns = {
        "Glucose": r"(?:Glucose|GLU)\s*[:=]?\s*([0-9.]+)",
        "Hemoglobin": r"(?:Hemoglobin|Hb|H B)\s*[:=]?\s*([0-9.]+)",
        "Systolic_BP": r"(?:Systolic|Sys\.?)\s*[:=]?\s*([0-9]+)",
        "Diastolic_BP": r"(?:Diastolic|Dia\.?)\s*[:=]?\s*([0-9]+)",
        "TSH": r"(?:TSH|Thyroid)\s*[:=]?\s*([0-9.]+)",
        "ALT": r"(?:ALT|SGPT)\s*[:=]?\s*([0-9.]+)",
        "AST": r"(?:AST|SGOT)\s*[:=]?\s*([0-9.]+)",
        "Creatinine": r"(?:Creatinine|CREA)\s*[:=]?\s*([0-9.]+)",
        "Urea": r"(?:Urea|BUN)\s*[:=]?\s*([0-9.]+)"
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
    hb = labs.get("Hemoglobin", hb)
    if hb is not None:
        if sex.lower() == "male" and hb < 13.5:
            risk.append("Low Hemoglobin")
            advice_list.append("Iron-rich diet & check for anemia .")
            doctors.add("Hematologist")
        elif sex.lower() == "female" and hb < 12.0:
            risk.append("Low Hemoglobin")
            advice_list.append("Iron-rich diet & check for anemia .")
            doctors.add("Hematologist")

    overall_health = "Excellent" if not risk else "Good Health"
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

    extracted_data = {}
    if uploaded_files:
        for file in uploaded_files:
            raw_text = extract_text(file)
            lab_values = parse_lab_values(raw_text)
            extracted_data.update(lab_values)

        if extracted_data:
            st.subheader("📄 Extracted Lab Values")
            df = pd.DataFrame(list(extracted_data.items()), columns=["Lab Test", "Value"])
            st.dataframe(df)

            glucose = extracted_data.get("Glucose", glucose)
            hemoglobin = extracted_data.get("Hemoglobin", hemoglobin)
            systolic_bp = extracted_data.get("Systolic_BP", systolic_bp)
            diastolic_bp = extracted_data.get("Diastolic_BP", diastolic_bp)

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

# --- Page Routing ---
if st.session_state.page == "login" or not st.session_state.logged_in:
    login_ui()
    registration_ui()
elif st.session_state.page == "main":
    main_app_ui()








