import base64
import datetime
import os
from io import BytesIO
import paramiko
import requests
from dotenv import load_dotenv
from pathlib import Path
env_path = Path(__file__).parent / "emag_cred.env"
load_dotenv(dotenv_path=env_path)


username = os.getenv("EMAG_USERNAME")
password = os.getenv("EMAG_PASSWORD")

SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_PORT = (os.getenv("SFTP_PORT"))
SFTP_USERNAME = os.getenv("SFTP_USERNAME")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
SFTP_UPLOAD_DIR = os.getenv("SFTP_UPLOAD_DIR")





# Base64 encode credentials
encoded_credentials = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")

# API Endpoints
ORDERS_URL = "https://marketplace-api.emag.ro/api-3/order/read"  # Fetch orders
AWB_URL = "https://marketplace-api.emag.ro/api-3/awb/save"        # Generate AWB
AWB_DOWNLOAD_URL = "https://marketplace-api.emag.ro/api-3/awb/read_pdf"  # Download AWB

# Headers for requests
headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
}



def fetch_orders_with_status_2():
    """Fetch orders with status 2 (ready for AWB generation)."""
    data = {
        "status": 2
    }
    headers_form = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        response = requests.post(ORDERS_URL, headers=headers_form, data=data)
        if response.status_code == 200:
            orders = response.json().get("results", [])
            print(f"[INFO] Fetched {len(orders)} orders with status 2")
            return orders
        else:
            print(f"[ERROR] Failed to fetch orders: {response.status_code}, {response.text}")
            return []
    except requests.RequestException as e:
        print(f"[EXCEPTION] Failed to fetch orders: {str(e)}")
        return []

def calculate_cod_amount(order):
    """Calculate the total cash-on-delivery (COD) amount for an order."""
    cod_amount = 0
    vat_rate = 0.19  # 19% VAT rate for Romania

    if order.get("payment_mode_id") == 1:  # 1 indicates cash on delivery
        for product in order.get("products", []):
            sale_price = float(product.get("sale_price", 0))
            quantity = int(product.get("quantity", 1))
            product_total = sale_price * quantity * (1 + vat_rate)

            for voucher in product.get("product_voucher_split", []):
                product_total += voucher.get("value", 0)

            cod_amount += product_total

        if cod_amount < 250:
            shipping_tax = float(order.get("shipping_tax", 0))
            cod_amount += shipping_tax

    return round(cod_amount, 2)

def generate_and_download_awb(order):
    """Generate and download the AWB for a COD order."""
    order_id = order["id"]
    receiver_data = order.get("customer", {})
    cod_amount = calculate_cod_amount(order)

    awb_data = {
        "order_id": order_id,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "is_oversize": 0,
        "insured_value": cod_amount,
        "weight": 1.2,
        "parcel_number": 1,
        "envelope_number": 0,
        "cod": cod_amount,
        "pickup_and_return": 0,
        "saturday_delivery": 0,
        "sameday_delivery": 0,
        "dropoff_locker": 1 if "EasyBox" in receiver_data.get("shipping_street", "") else 0,
        "observation": order_id,
        "receiver": {
            "name": receiver_data.get("name", ""),
            "contact": receiver_data.get("name", ""),
            "phone1": receiver_data.get("phone_1", ""),
            "locality_id": int(receiver_data.get("shipping_locality_id", 0)),
            "street": receiver_data.get("shipping_street", ""),
            "zipcode": receiver_data.get("shipping_postal_code", ""),
            "country": "Romania"
        },
        "sender": {
            "name": "SENDER",
            "contact": "SENDER_CONTACT",
            "phone1": "PHONE_NUMBER",
            "locality_id": 2,# From emag locality list
            "street": "SENDER_STREET",
            "zipcode": "ZIPCODE",
            "country": "COUNTRY"
        },
    }

    try:
        response = requests.post(AWB_URL, json=awb_data, headers=headers)
        response_data = response.json()

        if response.status_code == 200 and not response_data.get("isError", True):
            emag_id = response_data["results"]["awb"][0]["emag_id"]
            download_awb(emag_id, order_id)
        else:
            print(f"[ERROR] Failed to generate AWB for order {order_id}: {response_data.get('messages', 'Unknown error')}")
    except requests.RequestException as e:
        print(f"[EXCEPTION] Request failed for order {order_id}: {str(e)}")

def download_awb(emag_id, order_id):
    """Download AWB as PDF and upload it to an SFTP server."""
    download_url = f"{AWB_DOWNLOAD_URL}?emag_id={emag_id}"

    try:
        response = requests.get(download_url, headers=headers)
        if response.status_code == 200 and response.headers.get("Content-Type") == "application/pdf":
            pdf_content = response.content
            pdf_filename = f"{order_id}.pdf"
            with open(pdf_filename, 'wb') as pdf_file:
                pdf_file.write(pdf_content)
            print(f"[INFO] AWB downloaded and saved as {pdf_filename}")
            upload_to_sftp(pdf_filename, pdf_content)
        else:
            print(f"[ERROR] Failed to download AWB for emag_id {emag_id}")
    except requests.RequestException as e:
        print(f"[EXCEPTION] Failed to download AWB: {str(e)}")

def upload_to_sftp(filename, file_content):
    """Upload the PDF file to the SFTP server."""
    try:
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USERNAME, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_path = f"{SFTP_UPLOAD_DIR}/{filename}"
        with BytesIO(file_content) as file_obj:
            sftp.putfo(file_obj, remote_path)

        print(f"[INFO] AWB uploaded to SFTP as {remote_path}")
        sftp.close()
        transport.close()
    except Exception as e:
        print(f"[ERROR] SFTP upload failed: {str(e)}")

def process_orders():
    """Fetch, generate, and download AWBs for all orders with status 2."""
    orders = fetch_orders_with_status_2()
    for order in orders:
        generate_and_download_awb(order)

# Start the process
