from flask import Flask, request, render_template, send_file, redirect, url_for
import pandas as pd
from lxml import etree
import os

app = Flask(__name__)

# Define the tags to extract
tags = [
    "oper_type", "msg_type", "sttl_type", "oper_date", "acq_inst_bin", 
    "response_code", "is_reversal", "merchant_name", "merchant_country", 
    "terminal_type", "transaction_type", "account_number", "balance_type", 
    "amount_purpose", "card_number", "card_country", "auth_code"
]

# Function to parse XML and convert to DataFrame
def parse_xml_to_df(xml_file, ns):
    tree = etree.parse(xml_file)
    root = tree.getroot()

    data = []
    for operation in root.findall(".//ns:operation", ns):
        row = {tag: None for tag in tags}

        for tag in ["oper_type", "msg_type", "sttl_type", "oper_date", "acq_inst_bin", "response_code", "is_reversal", "merchant_name", "merchant_country", "terminal_type"]:
            element = operation.find(f"ns:{tag}", ns)
            row[tag] = element.text if element is not None else None

        transaction = operation.find("ns:transaction", ns)
        if transaction is not None:
            for tag in ["transaction_type", "amount_purpose"]:
                element = transaction.find(f"ns:{tag}", ns)
                row[tag] = element.text if element is not None else None

            for entry_type in ["debit_entry", "credit_entry"]:
                entry = transaction.find(f".//ns:{entry_type}/ns:account", ns)
                if entry is not None:
                    for tag in ["account_number", "balance_type"]:
                        element = entry.find(f"ns:{tag}", ns)
                        if element is not None:
                            row[tag] = element.text

        issuer = operation.find("ns:issuer", ns)
        if issuer is not None:
            for tag in ["card_number", "card_country", "auth_code"]:
                element = issuer.find(f"ns:{tag}", ns)
                row[tag] = element.text if element is not None else None

        oper_amount = operation.find("ns:oper_amount", ns)
        if oper_amount is not None:
            currency_element = oper_amount.find("ns:currency", ns)
            row["currency"] = currency_element.text if currency_element is not None else None
        else:
            row["currency"] = None

        data.append(row)

    return pd.DataFrame(data, columns=tags)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_us', methods=['POST'])
def upload_us():
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    if file.filename == '':
        return "No selected file"
    if file:
        filepath = os.path.join('uploads', file.filename)
        file.save(filepath)
        return redirect(url_for('generate_excel_us', filename=file.filename))

@app.route('/upload_them', methods=['POST'])
def upload_them():
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    if file.filename == '':
        return "No selected file"
    if file:
        filepath = os.path.join('uploads', file.filename)
        file.save(filepath)
        return redirect(url_for('generate_excel_them', filename=file.filename))

@app.route('/generate_excel_us', methods=['GET'])
def generate_excel_us():
    filename = request.args.get('filename')
    if not filename:
        return "Filename not provided"
    
    xml_file = os.path.join('uploads', filename)
    ns = {"ns": "http://bpc.ru/sv/SVXP/clearing"}
    df = parse_xml_to_df(xml_file, ns)
    output_file = os.path.join('output', f'output_us_{filename}.xlsx')
    df.to_excel(output_file, index=False)
    return send_file(output_file, as_attachment=True)

@app.route('/generate_excel_them', methods=['GET'])
def generate_excel_them():
    filename = request.args.get('filename')
    if not filename:
        return "Filename not provided"
    
    xml_file = os.path.join('uploads', filename)
    ns = {"ns": "http://bpc.ru/sv/SVXP/clearing"}
    df = parse_xml_to_df(xml_file, ns)
    output_file = os.path.join('output', f'output_them_{filename}.xlsx')
    df.to_excel(output_file, index=False)
    return send_file(output_file, as_attachment=True)

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    if not os.path.exists('output'):
        os.makedirs('output')
    app.run(debug=True)
