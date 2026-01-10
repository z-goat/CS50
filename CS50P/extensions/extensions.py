import sys


filename = input("File name: ").strip().lower()

if "." not in filename:
    print("application/octet-stream")
    sys.exit()
file_extension = filename.split(".")[-1]

if file_extension == "gif" or file_extension == "png":
    media_type = "image"
elif file_extension == "jpg" or file_extension == "jpeg":
    print("image/jpeg")
    sys.exit()
elif file_extension == "pdf" or file_extension == "zip":
    media_type = "application"
elif file_extension == "txt":
    print("text/plain")
    sys.exit()
else:
    print("application/octet-stream")
    sys.exit()

print(f"{media_type}/{file_extension}")
