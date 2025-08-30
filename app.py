import streamlit as st
import pandas as pd
import json
import re
from pathlib import Path

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

# --- Normalize old users and ensure all have proper names ---
for k, v in list(users.items()):
    # If old format (password as string), convert to dict
    if isinstance(v, str):
        users[k] = {"name": k, "password": v}  # fallback: name = phone/email

    # If dict exists but missing 'name' key or empty
    elif isinstance(v, dict):
        if "name" not in v or not v["name"]:
            users[k]["name"] = k  # fallback: name = phone/email

# Save back updated users
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
def ensure_user_records():
    user = st.session_state.current_user
    if user and user not in patient_records:
        patient_records[user] = []
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
                ensure_user_records()
                st.success("✅ Login successful!")
                st.stop()  # <-- This forces Streamlit to rerun immediately
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
                # Save user login credentials
                users[new_email_phone] = {"name": new_name, "password": new_password}
                save_json(user_file, users)

                # Save basic patient info
                patient_records[new_name] = [{
                    "age": new_age,
                    "sex": new_sex,
                    "weight": new_weight,
                    "height_cm": new_height
                }]
                save_json(data_file, patient_records)

                st.session_state.logged_in = True
                st.session_state.current_user = new_name
                st.success("✅ Registered and logged in!")
                st.stop()  # <-- This forces Streamlit to rerun immediately
def bmi_risk(bmi, age, sex):
     advice = ""
     if age < 18:
        # For children/adolescents, BMI-for-age charts should be used.
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
            # Optional: sex-based note
     if sex.lower() == "female" and bmi >= 25:
        advice += " (Women have slightly higher cardiovascular risk at lower BMI.)"

     return risk, advice

# --- Risk Checker (simplified) ---
def check_risks(glucose, bmi, systolic_bp, diastolic_bp, hemoglobin=None, age=25, sex="Male"):
    risk = []
    doctors = set()
    advice_list = []

    if glucose >= 120:
        risk.append("High Glucose")
        doctors.add("Endocrinologist")
    
    bmi_category, bmi_advice = bmi_risk(bmi, age, sex)
    risk.append(bmi_category)
    advice_list.append(bmi_advice)

    if systolic_bp >= 140 or diastolic_bp >= 90:
        risk.append("High BP")
        doctors.add("Cardiologist")
    overall_health = "Excellent Health" if not risk else "Moderate Risk"
    return risk, doctors, advice_list, overall_health

# --- Main App ---
if not st.session_state.logged_in:
    login_ui()
    registration_ui()
else:
    ensure_user_records()
    st.title("🩺 Doctor Buddy")
    st.write(f"👋 Welcome, {st.session_state.current_user}!")
    
      # --- Load stored user info ---
    user_records = patient_records.get(st.session_state.current_user, [])
    if user_records:
        latest_info = user_records[0]  # registration info
        age = latest_info.get("age", 25)
        sex = latest_info.get("sex", "Male")
        weight = latest_info.get("weight", 70.0)
        height_cm = latest_info.get("height_cm", 170.0)
    else:
        # Fallback if not found
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

    # --- Calculate BMI automatically ---
    bmi = round(weight / ((height_cm / 100) ** 2), 2)
    st.write(f"**BMI:** {bmi}")

    if st.button("Check Risk"):
        risk, doctors, advice, overall_health = check_risks(glucose, bmi, systolic_bp, diastolic_bp, hemoglobin, age, sex)

        st.subheader("Results Summary")
        st.write(f"**Overall Health:** {overall_health}")
        if risk: st.write("Risks:", risk)
        if doctors: st.write("See specialists:", ", ".join(doctors))
        if advice: st.write("Advice:", advice)
 
        # Save new health record
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
        st.experimental_rerun() 