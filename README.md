<div align="center">

# 🩺 Doctor Buddy  
### Your Personal Health Risk Checker

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-Yes-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

🚀 A simple yet powerful **Streamlit app** to monitor health metrics, assess risks, and get personalized advice.  


</div>

---

## ✨ Features
- 🔐 **Login & Registration** (with local JSON storage)  
- 👤 Store & manage patient details (age, sex, weight, height)  
- 📊 **Health Metrics Input**:  
  - Glucose (mg/dL)  
  - Blood Pressure (Systolic/Diastolic)  
  - Hemoglobin (g/dL)  
  - Height & Weight → Automatic BMI calculation  
- 📄 **Lab Report Upload**:  
  - Supports CSV, PDF, and Image files (JPG/PNG)  
  - Automatic extraction of lab values (Glucose, Hemoglobin, TSH, ALT, AST, Creatinine, Urea)  
  - Overrides manual input if data is detected  
- 🧠 **Risk Analysis** with personalized recommendations  
  - Blood sugar, BMI, blood pressure  
  - Liver, kidney, thyroid lab alerts  
- 📝 Stores **past records** for each user and displays history  
- 💡 Healthy lifestyle tips for better living  
- 🌍 Runs on any device (once deployed online)  
---

## 🚀 Getting Started  

1. Clone the repository:
```bash
git clone https://github.com/Riiocodee/health-checker.git
cd health-checker
```
 2. Install dependencies:
Make sure Python 3.9+ is installed, then run:
```bash
pip install -r requirements.txt
```
 3. Run the app locally:
```bash
streamlit run app.py
```

---


### 🌍 Deployment
This project can be deployed on Streamlit Community Cloud for free:

1. Push your code to GitHub

2. Go to Streamlit Cloud

3. Link your repo and deploy
You’ll get a public link like:
```bash
https://Doctor_Buddy.streamlit.app
```

---

### 📂 Project Structure
```bash
📦 doctor-buddy
 ┣ 📜 app.py              # Main Streamlit app
 ┣ 📜 users.json          # User login credentials (auto-created)
 ┣ 📜 patient_data.json   # Patient health records (auto-created)
 ┣ 📜 requirements.txt    # Python dependencies
 ┗ 📜 README.md           # Project documentation
 ┗ 📜 manifest.json       # Add PWA manifest and image  
```

---

### 🛠️ Tech Stack

1. Python 3.9+
2. Streamlit (UI framework)
3. Pandas (data handling)
4. JSON (local storage)
5. Pillow & pytesseract (OCR for lab reports)
6. Tabula-py (PDF table extraction)

---

### 🙌 Contribution

Contributions are welcome!

1. Fork the repo

2. Create a new branch (feature/new-idea)

3. Commit changes

4. Open a Pull Request

---


### 📜 License

This project is open-source under the MIT License.

<div align="center">

💖 Made with care to help people live healthier lives

</div>

---



































































