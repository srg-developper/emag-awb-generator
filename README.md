# eMAG AWB Generator

This Python project automates the extraction of orders with status 2 from the eMAG Marketplace API. For each order, it generates an AWB (shipping label) and uploads it to a specified SFTP server.

## 🔧 Technologies Used

- Python
- requests
- dotenv
- paramiko
- datetime

## 📁 Folder Structure

- `main.py` – the main script for processing and uploading AWBs
- `.env.example` – sample environment variables file
- `README.md` – project documentation

## ⚙️ Setup Instructions

1. Clone this repository:

```bash
git clone https://github.com/YOUR_USERNAME/emag-awb-generator.git
cd emag-awb-generator
```

2. Create a `.env` file based on `.env.example` and fill in your credentials:

```env
EMAG_USERNAME=your_email@example.com
EMAG_PASSWORD=your_password
SFTP_HOST=ftp.example.com
SFTP_PORT=8573
SFTP_USERNAME=username
SFTP_PASSWORD=password
SFTP_UPLOAD_DIR=AWB_EMAG
```

3. Install dependencies:

```bash
pip install requests python-dotenv paramiko
```

4. Run the script:

```bash
python main.py
```

## 🔒 Security

- Do **not** commit your `.env` file to version control.
- Make sure `.gitignore` contains `.env`

## 📜 License

Personal project, not for commercial use.
