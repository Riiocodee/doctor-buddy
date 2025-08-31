import streamlit as st
import pandas as pd
import json
from PIL import Image
import pytesseract
import re
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
        users[k] = {"name": k, "password": v}  # fallback: old users
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
    st.session_state.current_user_email = None  # stores email/phone for lookup

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
                st.experimental_rerun()
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
                # Save credentials
                users[new_email_phone] = {"name": new_name, "password": new_password}
                save_json(user_file, users)

                # Save patient info
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
                st.experimental_rerun()

    
# --- OCR & file parsing ---
def extract_text(file):
    text = ""
    try:
        if file.type in ["image/jpeg", "image/png"]:
            img = Image.open(file)
            text = pytesseract.image_to_string(img)
        elif file.type == "application/pdf":
            import tabula
            dfs = tabula.read_pdf(file, pages='all', multiple_tables=True)
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
        "Hemoglobin": r"(?:Hemoglobin|Hb)\s*[:=]?\s*([0-9.]+)",
        "Systolic_BP": r"Systolic\s*[:=]?\s*([0-9]+)",
        "Diastolic_BP": r"Diastolic\s*[:=]?\s*([0-9]+)",
        "TSH": r"(?:TSH|Thyroid)\s*[:=]?\s*([0-9.]+)",        # Thyroid
        "ALT": r"(?:ALT|SGPT)\s*[:=]?\s*([0-9.]+)",          # Liver
        "AST": r"(?:AST|SGOT)\s*[:=]?\s*([0-9.]+)",          # Liver
        "Creatinine": r"(?:Creatinine|CREA)\s*[:=]?\s*([0-9.]+)",  # Kidney
        "Urea": r"(?:Urea|BUN)\s*[:=]?\s*([0-9.]+)"                # Kidney
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            lab_data[key] = float(match.group(1))
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

def check_risks(glucose, bmi, systolic_bp, diastolic_bp, labs, age=25, sex="Male"):
    risk = []
    doctors = set()
    advice_list = []

    if glucose >= 120: risk.append("High Glucose"); doctors.add("Endocrinologist")
    bmi_cat, bmi_adv = bmi_risk(bmi, age, sex)
    risk.append(bmi_cat); advice_list.append(bmi_adv)
    if systolic_bp >= 140 or diastolic_bp >= 90: risk.append("High BP"); doctors.add("Cardiologist")
    
    # Additional lab alerts
    if labs.get("TSH", 0) > 5.0: risk.append("High TSH"); doctors.add("Endocrinologist")
    if labs.get("ALT", 0) > 45 or labs.get("AST",0) > 40: risk.append("Liver Enzyme High"); doctors.add("Hepatologist")
    if labs.get("Creatinine",0) > 1.3 or labs.get("Urea",0) > 50: risk.append("Kidney function abnormal"); doctors.add("Nephrologist")
    
    overall_health = "Excellent" if not risk else "Good Health"
    return risk, doctors, advice_list, overall_health


# --- Main App ---
if not st.session_state.logged_in:
    login_ui()
    registration_ui()
else:
    ensure_user_records(st.session_state.current_user)
    st.title("🩺 Doctor Buddy")
    st.write(f"👋 Welcome, {st.session_state.current_user}!")

    # --- Load user info ---
    user_records = patient_records.get(st.session_state.current_user, [])
    if user_records:
        latest_info = user_records[0]
        age = latest_info.get("age", 25)
        sex = latest_info.get("sex", "Male")
        weight = latest_info.get("weight", 70.0)
        height_cm = latest_info.get("height_cm", 170.0)
    else:
        age, sex, weight, height_cm = 25, "Male", 70.0, 170.0

    # --- Show stored info ---
    st.write(f"**Age:** {age} | **Sex:** {sex} | **Weight:** {weight} kg | **Height:** {height_cm} cm")

    # Manual entry
    glucose = st.number_input("Glucose (mg/dL)", value=90.0)
    systolic_bp = st.number_input("Systolic BP (mmHg)", value=120)
    diastolic_bp = st.number_input("Diastolic BP (mmHg)", value=80)
    hemoglobin = st.number_input("Hemoglobin (g/dL)", value=14.0)
    weight = st.number_input("Weight (kg)", value=weight)
    height_cm = st.number_input("Height (cm)", value=height_cm)
    

    # --- File upload ---
    st.subheader("📄 Upload Lab Reports / CSV / PDF / Images")
    uploaded_files = st.file_uploader("Choose files", type=['pdf', 'png', 'jpg', 'jpeg', 'csv'], accept_multiple_files=True)
    extracted_data = {}
    if uploaded_files:
        for file in uploaded_files:
            text = extract_text(file)
            data = parse_lab_values(text)
            extracted_data.update(data)

        st.success("✅ Data extracted from files!")
       
        # Override manual entries if extracted from uploaded files
        glucose = extracted_data.get("Glucose", glucose)
        hemoglobin = extracted_data.get("Hemoglobin", hemoglobin)
        systolic_bp = extracted_data.get("Systolic_BP", systolic_bp)
        diastolic_bp = extracted_data.get("Diastolic_BP", diastolic_bp)

       # Optional: extract additional labs for display or use in further analysis
        tsh = extracted_data.get("TSH", None)
        alt = extracted_data.get("ALT", None)
        ast = extracted_data.get("AST", None)
        creatinine = extracted_data.get("Creatinine", None)
        urea = extracted_data.get("Urea", None)

    # Display all extracted labs neatly
    st.subheader("📄 Extracted Lab Values")
    if extracted_data:
      lab_df = pd.DataFrame(list(extracted_data.items()), columns=["Lab Test", "Value"])
      st.dataframe(lab_df)
    else:
      st.info("No lab values extracted yet.")

    # --- Calculate BMI ---
    bmi = round(weight / ((height_cm / 100) ** 2), 2)
    st.write(f"**BMI:** {bmi}")

    
    # Risk Check
    if st.button("Check Risk"):
        risk, doctors, advice, overall_health = check_risks(glucose, bmi, systolic_bp, diastolic_bp, extracted_data, age, sex)

        st.subheader("Results Summary")
        st.write(f"**Overall Health:** {overall_health}")
        if risk: st.write("Risks:", risk)
        if doctors: st.write("See specialists:", ", ".join(doctors))
        if advice: st.write("Advice:", advice)
 # Save record
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

    # Past records
    past_records = patient_records[st.session_state.current_user][:]
    if past_records:
        st.subheader("📋 Your Past Records")
        df = pd.DataFrame(past_records)
        st.dataframe(df)
    else:
        st.info("No past records found.")

    # Health tips
    st.subheader("💡 Healthy Lifestyle Tips")
    st.markdown("""
    - 🥗 Eat a balanced diet with fruits & vegetables  
    - 🚶 Exercise at least 30 minutes daily  
    - 💧 Drink enough water  
    - 💤 Sleep 7-8 hours every night  
    - 🚭 Avoid smoking & limit alcohol  
    - 🧘 Manage stress with meditation/yoga
    """)

    # Logout
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.current_user_email = None
        st.experimental_rerun()
