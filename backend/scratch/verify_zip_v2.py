import zipfile
import os

zip_path = r'C:\Users\Kaushal\Downloads\Accenture Tech Acquisition Analysis_7b520617-b2ec-4044-bacf-4827b56ba9f3_Package.zip'
if os.path.exists(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        print(f"ZIP Contents: {zipf.namelist()}")
else:
    print(f"ZIP not found: {zip_path}")
