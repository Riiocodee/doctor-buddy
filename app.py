import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
import tabula
from pathlib import Path

def load_markdown(file_path):
    # Read file with UTF-8 encoding
    return Path(file_path).read_text(encoding="utf-8")


# Load and display README markdown (text only)
with open("README.md", "r", encoding="utf-8") as file:
 markdown_text = file.read()
st.markdown(load_markdown("README.md"))

import streamlit as st
from pathlib import Path

def load_markdown(file_path):
    return Path(file_path).read_text()

st.markdown(load_markdown("README.md"))
st.image("images/diagram1.png", caption="System Architecture Diagram")
st.image("images/screenshot.png", caption="App Screenshot")


# --- Initializing Default Values ---
hemoglobin = wbc = platelets = None
tsh = t3 = t4 = None
alt = ast = bilirubin = alp = ggt = albumin = total_protein = None
creatinine = urea = uric_acid = sodium = potassium = egfr = None
glucose = None

# --- Function to extract values from text using regex ---
def extract_value(label, text):
    pattern = rf"{label}\s*[:\-]?\s*([\d]+\.?[\d]*)"
    match = re.search(pattern, text, re.IGNORECASE)
    return float(match.group(1)) if match else None

# --- Function to perform risk checks ---
def check_risks(glucose, bmi, systolic_bp, diastolic_bp,
                hemoglobin=None, wbc=None, platelets=None,
                tsh=None, t3=None, t4=None,
                alt=None, ast=None, bilirubin=None, alp=None, ggt=None, albumin=None, total_protein=None,
                creatinine=None, urea=None, uric_acid=None, sodium=None, potassium=None, egfr=None):

    risk = []
    doctors = set()
    advice_list = []
    overall_health = None

    if "patient_records" not in st.session_state:
     st.session_state["patient_records"] = []

    if "can_add_entry" not in st.session_state:
      st.session_state["can_add_entry"] = False


    # Existing glucose/BMI/BP checks 
    
    if glucose is not None:
        if glucose >= 126:
            risk.append("High Glucose (Diabetes suspected)")
            doctors.add("Endocrinologist")
            advice_list.append("Consider HbA1c test and diabetes management.")
        elif glucose >= 100:
            risk.append("Impaired Glucose Tolerance (Prediabetes)")
            doctors.add("Endocrinologist")
            advice_list.append("Lifestyle modification recommended.")

    if bmi is not None:
        if bmi >= 30:
            risk.append("High BMI (Obesity)")
            doctors.add("Nutritionist")
            advice_list.append("Diet and exercise plan recommended.")
        elif bmi >= 25:
            risk.append("Overweight BMI")
            advice_list.append("Maintain healthy diet and physical activity.")

    if systolic_bp is not None and diastolic_bp is not None:
        if systolic_bp >= 140 or diastolic_bp >= 90:
            risk.append("High Blood Pressure (Hypertension)")
            doctors.add("Cardiologist")
            advice_list.append("Monitor BP regularly and consult doctor.")
        elif systolic_bp >= 120 or diastolic_bp >= 80:
            risk.append("Elevated Blood Pressure")
            advice_list.append("Lifestyle changes advised.")

    # --- Thyroid Profile ---
    if tsh is not None:
        if tsh > 4.5:
            risk.append("Hypothyroidism (High TSH)")
            doctors.add("Endocrinologist")
            advice_list.append("Schedule a consult for thyroid management.")
        elif tsh < 0.4:
            risk.append("Hyperthyroidism (Low TSH)")
            doctors.add("Endocrinologist")
            advice_list.append("Review for possible overactive thyroid.")

    if t3 is not None:
        if t3 < 80:
            risk.append("Low T3")
            doctors.add("Endocrinologist")
            advice_list.append("Possible hypothyroidism.")
        elif t3 > 200:
            risk.append("High T3")
            doctors.add("Endocrinologist")
            advice_list.append("Possible hyperthyroidism.")

    if t4 is not None:
        if t4 < 5:
            risk.append("Low T4")
            doctors.add("Endocrinologist")
            advice_list.append("Possible hypothyroidism.")
        elif t4 > 12:
            risk.append("High T4")
            doctors.add("Endocrinologist")
            advice_list.append("Possible hyperthyroidism.")

    # --- Liver Profile ---
    if alt is not None and alt > 56:
        risk.append("High ALT (Liver inflammation)")
        doctors.add("Hepatologist")
    if ast is not None and ast > 40:
        risk.append("High AST (Possible liver injury)")
        doctors.add("Hepatologist")
    if bilirubin is not None and bilirubin > 1.2:
        risk.append("High Bilirubin (Liver/biliary issue)")
        doctors.add("Hepatologist")
    if alp is not None and alp > 120:
        risk.append("High ALP")
        doctors.add("Hepatologist")
    if ggt is not None and ggt > 60:
        risk.append("High GGT")
        doctors.add("Hepatologist")

    # --- Kidney Profile ---
    if creatinine is not None and creatinine > 1.3:
        risk.append("High Creatinine (Kidney function issue)")
        doctors.add("Nephrologist")
    if urea is not None and urea > 45:
        risk.append("High Urea (Possible kidney dysfunction)")
        doctors.add("Nephrologist")
    if egfr is not None and egfr < 60:
        risk.append("Low eGFR (Chronic Kidney Disease risk)")
        doctors.add("Nephrologist")

    # --- CBC (Hemoglobin) —
    if hemoglobin is not None:
        if hemoglobin < 12:
            risk.append("Low Hemoglobin (Anemia)")
            doctors.add("Hematologist")
        elif hemoglobin > 17.5:
            risk.append("High Hemoglobin")
            doctors.add("Hematologist")

    # --- Overall Health Assessment ---
    overall_health = ("Excellent Health" if not risk
                      else "Moderate Risk" if len(risk) <= 2
                      else "Needs Medical Attention")

    return risk, doctors, advice_list, overall_health

# --- Streamlit UI ---
st.title("🩺 Health Risk Checker")

uploaded_file = st.file_uploader("Upload Lab Report (CSV, PDF, JPEG/PNG)", 
                                 type=["csv", "pdf", "jpg", "jpeg", "png"])

# --- Extract Data from Uploaded File ---
if uploaded_file:
    # CSV
    if uploaded_file.type == "text/csv":
        df = pd.read_csv(uploaded_file)
        if df is not None:
            st.subheader("Extracted Lab Report Table")
            st.dataframe(df)
    # PDF
    elif uploaded_file.type == "application/pdf":
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        dfs = tabula.read_pdf("temp.pdf", pages="all", multiple_tables=True)
        df = pd.concat(dfs, ignore_index=True)
        if df is not None:
            st.subheader("Extracted Lab Report Table")
            st.dataframe(df)
    # Image
    else:
        img = Image.open(uploaded_file)
        text = pytesseract.image_to_string(img)
        if uploaded_file.type.startswith("image/"):
            st.subheader("OCR Extracted Text")
            st.text_area("Parsed Text:", text, height=300)
        df = None

    # If data is from CSV / PDF, populate fields programmatically
    def get_val(cols, df):
        for c in cols:
            if df is not None and c in df.columns:
                return float(df[c].iloc[0])
        return None

    # If DataFrame is available
    if df is not None:
        glucose = get_val(['glucose'], df) or glucose
        hemoglobin = get_val(['hemoglobin'], df) or hemoglobin
        tsh = get_val(['tsh'], df) or tsh
        t3 = get_val(['t3'], df) or t3
        t4 = get_val(['t4'], df) or t4
        alt = get_val(['alt'], df) or alt
        ast = get_val(['ast'], df) or ast
        bilirubin = get_val(['bilirubin'], df) or bilirubin
        alp = get_val(['alp'], df) or alp
        ggt = get_val(['ggt'], df) or ggt
        creatinine = get_val(['creatinine'], df) or creatinine
        urea = get_val(['urea'], df) or urea
        uric_acid = get_val(['uric_acid'], df) or uric_acid
        sodium = get_val(['sodium'], df) or sodium
        potassium = get_val(['potassium'], df) or potassium
        egfr = get_val(['egfr'], df) or egfr

    # If OCR text exists
    if uploaded_file.type.startswith("image/"):
        glucose = extract_value("glucose", text) or glucose
        hemoglobin = extract_value("hemoglobin", text) or hemoglobin
        tsh = extract_value("tsh", text) or tsh
        t3 = extract_value("t3", text) or t3
        t4 = extract_value("t4", text) or t4
        alt = extract_value("alt", text) or alt
        ast = extract_value("ast", text) or ast
        bilirubin = extract_value("bilirubin", text) or bilirubin
        alp = extract_value("alp", text) or alp
        ggt = extract_value("ggt", text) or ggt
        creatinine = extract_value("creatinine", text) or creatinine
        urea = extract_value("urea", text) or urea
        uric_acid = extract_value("uric acid", text) or uric_acid
        sodium = extract_value("sodium", text) or sodium
        potassium = extract_value("potassium", text) or potassium
        egfr = extract_value("egfr", text) or egfr


# --- Manual Entry Fields ---
st.subheader("Manual Entry")
glucose = st.number_input("Glucose (mg/dL)", value=glucose or 80.0)
systolic_bp = st.number_input("Systolic BP (mmHg)", value=120)
diastolic_bp = st.number_input("Diastolic BP (mmHg)", value=80)
weight = st.number_input("Weight (kg)", value=70.0)
height_cm = st.number_input("Height (cm)", value=170.0)
bmi = round(weight / ((height_cm/100)**2), 2)

# Additional optional fields
st.subheader("Optional Advanced Parameters")
hemoglobin = st.number_input("Hemoglobin (g/dL)", value=hemoglobin or 14.0)
tsh = st.number_input("TSH (mIU/L)", value=tsh or 2.5)
t3 = st.number_input("T3 (ng/dL)", value=t3 or 100.0)
t4 = st.number_input("T4 (µg/dL)", value=t4 or 8.0)
alt = st.number_input("ALT (U/L)", value=alt or 30.0)
creatinine = st.number_input("Creatinine (mg/dL)", value=creatinine or 1.0)
ast = st.number_input("AST (U/L)", value=ast or 30.0)
bilirubin = st.number_input("Bilirubin (mg/dL)", value=bilirubin or 1.0)
alp = st.number_input("ALP (U/L)", value=alp or 100.0)
ggt = st.number_input("GGT (U/L)", value=ggt or 40.0)
urea = st.number_input("Urea (mg/dL)", value=urea or 25.0)
uric_acid = st.number_input("Uric Acid (mg/dL)", value=uric_acid or 5.5)
sodium = st.number_input("Sodium (mmol/L)", value=sodium or 140.0)
potassium = st.number_input("Potassium (mmol/L)", value=potassium or 4.0)
egfr = st.number_input("eGFR (mL/min/1.73m²)", value=egfr or 90.0)


# --- Button to Check Risks ---
if st.button("Check Risk", key="check_risk"):
    risk, doctors, advice_list, overall_health = check_risks(
        glucose, bmi, systolic_bp, diastolic_bp,
        hemoglobin=hemoglobin, wbc=wbc, platelets=platelets,
        tsh=tsh, t3=t3, t4=t4,
        alt=alt, ast=ast, bilirubin=bilirubin, alp=alp, ggt=ggt,
        albumin=albumin, total_protein=total_protein,
        creatinine=creatinine, urea=urea, uric_acid=uric_acid,
        sodium=sodium, potassium=potassium, egfr=egfr
    )

    # Store results in session_state
    st.session_state["last_risk"] = risk
    st.session_state["last_doctors"] = doctors
    st.session_state["last_advice"] = advice_list
    st.session_state["last_overall_health"] = overall_health
    st.session_state["can_add_entry"] = True
    # Display results
    st.subheader("Results Summary")
    st.markdown(f"- **Glucose:** {glucose}")
    st.markdown(f"- **BMI:** {bmi}")
    st.markdown(f"- **Systolic BP:** {systolic_bp} mmHg")
    st.markdown(f"- **Diastolic BP:** {diastolic_bp} mmHg")
    st.markdown(f"- **Overall Health:** **{overall_health}**")

    if risk:
        st.subheader("Detected Risks")
        for r in risk:
            st.write("- " + r)
    if advice_list:
        st.subheader("Advice")
        for advice in advice_list:
            st.write("- " + advice)
    if doctors:
        st.subheader("Suggested Specialists")
        st.write(", ".join(doctors))


if "overall_health" in locals():
     if st.button("Add Entry to Database" ,key="add_entry_btn"):
        new_record = {
            "glucose": glucose,
            "bmi": bmi,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "tsh": tsh,
            "t3": t3,
            "t4": t4,
            "creatinine": creatinine,
            "urea": urea,
            "hemoglobin": hemoglobin,
            "overall_health": overall_health,
            "risk": risk,
            "advice": advice_list
        }
        if "patient_records" not in st.session_state:
            st.session_state["patient_records"] = []
        st.session_state["patient_records"].append(new_record)
        st.success("✅ Patient entry added to session database.")
else:
    st.info("⚠️ Please run 'Check Risk' first to enable storing the entry.")

    # --- Store patient record in session ---
# Initialize session state containers for patient records and last check results
# Initialize session state (put this near the top of your script)
if "patient_records" not in st.session_state:
    st.session_state["patient_records"] = []

if "last_risk" not in st.session_state:
    st.session_state["last_risk"] = []

if "last_doctors" not in st.session_state:
    st.session_state["last_doctors"] = set()

if "last_advice" not in st.session_state:
    st.session_state["last_advice"] = []

if "last_overall_health" not in st.session_state:
    st.session_state["last_overall_health"] = None

if "can_add_entry" not in st.session_state:
    st.session_state["can_add_entry"] = True


# --- Add Entry Button: only show if a valid risk check was done ---
if st.session_state["can_add_entry"]:
    
        new_record = {
            "glucose": glucose,
            "bmi": bmi,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "tsh": tsh,
            "t3": t3,
            "t4": t4,
            "creatinine": creatinine,
            "urea": urea,
            "hemoglobin": hemoglobin,
            "overall_health": st.session_state["last_overall_health"],
            "risk": st.session_state["last_risk"],
            "advice": st.session_state["last_advice"]
        }
        st.session_state["patient_records"].append(new_record)
        st.success("✅ Patient entry added to session database.")
        st.session_state["can_add_entry"] = False  # Disable until next check
else:
    st.info("⚠️ Please run 'Check Risk' first to enable storing the entry.")

# --- Display All Entries ---
if st.session_state["patient_records"]:
    st.subheader("📋 All Patient Records")
    all_patients_df = pd.DataFrame(st.session_state["patient_records"])
    st.dataframe(all_patients_df)

    # --- Summary Stats ---
    st.subheader("📊 Overall Health Summary")
    health_counts = all_patients_df["overall_health"].value_counts()
    st.bar_chart(health_counts)

    # --- Average Lab Values ---
    st.subheader("📈 Average Lab Values Across Patients")
    numeric_cols = ["glucose", "bmi", "systolic_bp", "diastolic_bp",
                    "tsh", "t3", "t4", "creatinine", "urea", "hemoglobin"]
    for col in numeric_cols:
        if col in all_patients_df.columns:
            st.markdown(f"- **{col.upper()}**: {round(all_patients_df[col].mean(), 2)}")

    # --- Risk Pattern Summary ---
    all_risks = all_patients_df["risk"].explode().dropna()
    if not all_risks.empty:
        st.subheader("⚠️ Most Common Risk Factors")
        st.bar_chart(all_risks.value_counts())

    # --- Optional: Download as CSV ---
    csv_data = all_patients_df.to_csv(index=False)
    st.download_button("📥 Download All Patient Data", csv_data, "patient_data.csv")

