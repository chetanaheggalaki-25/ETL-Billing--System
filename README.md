# 🧾 ETL Billing System

## 📌 Overview

This project is an ETL (Extract, Transform, Load) system that processes billing documents (PDF/images) and converts unstructured invoice data into structured Excel output.

 It automates bill data extraction and reduces manual effort.

---

## 🚀 Features

* Upload and process billing documents
* Extract invoice details (Invoice No, Date, Vendor)
* Rule-based data extraction system
* Editable rule table for adding custom attributes
* Extracts line items (Description, Quantity, Price, Amount)
* Export extracted data to Excel (.xlsx)
* Duplicate file detection
* Validation for incorrect or non-bill inputs
* Progress tracking for multiple uploads

---

## 🛠️ Technologies Used

* Python
* Pandas
* OpenCV
* OCR (Text Extraction)
* Regular Expressions
* HTML, CSS, JavaScript
* Flask (Backend)
* OpenPyXL (Excel handling)

---

## ⚙️ Workflow

1. Upload bill (PDF/Image)
2. Preprocess document
3. Extract text using OCR
4. Generate extraction rules
5. Extract line items and key fields
6. Transform data into structured format
7. Export to Excel

---

## ▶️ How to Run

1. Clone the repository:
   git clone https://github.com/chetanaheggalaki-25/ETL-Billing--System.git

2. Navigate to the project folder:
   cd ETL-Billing--System

3. Run the application:
   startApp.bat

👉 The application will launch automatically.

---

## 📂 Input

* PDF bills
* Invoice images

---

## 📤 Output

* Structured Excel file containing:

  * Invoice Number
  * Date
  * Vendor Name
  * Line Items (Description, Quantity, Price, Amount)
  * Total Amount
  * Tax details

---

## 📊 Line Item Extraction

The system detects tabular data in invoices and extracts:

* Description
* Quantity
* Unit Price
* Total Amount

---

## ⚠️ Notes

* Accuracy depends on input quality
* Works best with clear and structured invoices
* Ensure Python is installed before running

---

## 💡 Future Improvements

* Improve accuracy for complex invoice formats
* AI-based rule learning
* UI enhancements
* Optional cloud deployment
