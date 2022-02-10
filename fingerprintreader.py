from imp import source_from_cache
import subprocess
import random
from PIL import Image
import string
from time import sleep
import _sqlite3 
import tempfile
import os

"""
General work flow

Intro
    1. Ask user to input 1 for enrollment, 2 for verification, 3 for identification
Enrollement
    1. Either ask user for name or generate them a random ID or both. This information will be called identifying info from now on
    2. Ask user to press finger againist prism
    3. Capture image
    4. Use Pillow to convert the image to grayscale
   -- 5. Use djpegb to generate NIST IHead file
   -- 6. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise repeat step 4
   -- 7. Use pcasys to classify fingerprint image
   -- 8. Use 'cwsq .75 *filename*' to convert to a WSQ compressed file
    9. Make temporary directory to host mindtct result files
    10. Run mindtct, read .xyt file into database, kill tmp directory

Verification
    May want to change to use pcasys as a potential "quick negative", would improve best case running speed but worsen worst case
    1. Ask user for identifying info
    2. Ask user to press finger againist prism
    3. Capture image 
    4. Use Pillow to convert the image to grayscale
    5. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise repeat step 3
    6. Use 'cwsq .75 *filename*' to convert to a WSQ compressed file
    7. Use mindtct to extract minutiae
    8. Pull minutiae info from database row with matching identifying info
    9. Use BOZORTH3 to compare minutiae
   10. If the match score reaches a certain score (There's a suggested score in the user's guide) then pass, otherwise fail   
   
Identification
    1. Ask user to press finger againist prism
    2. Capture image 
    3. Use Pillow to convert the image to grayscale
    4. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise repeat step 2
    5. Use pcasys to classify fingerprint image
    6. Use 'cwsq .75 *filename*' to convert to a WSQ compressed file
    7. Use mindtct to extract mintuiae 
    8. Pull fingerprint minutiae data from database rows with matching classification 
    9. Compare this minutiae data with the captured fingerprint image's minutiae data
    10. If one is eventually found then pass, otherwise fail
"""
def convert_to_grayscale(image,temp_directory):
    grayscale_image=Image.open("C:\\Users\\jacob\\Desktop\\Fingerprints\\"+image).convert('L')
    save_directory= os.path.join(temp_directory,'grayscale_image.jpg')
    grayscale_image.save(save_directory)
    return save_directory

def run_mindtct(image):
    with tempfile.TemporaryDirectory() as temp_directory:
        source_file_path=convert_to_grayscale(image,temp_directory)
        result_file_path = os.path.join(temp_directory,'output')
        subprocess.check_call(['bash', '-i', '-c', 'mindtct', source_file_path, "output"]) # bash -i -c should be deleted after moving to linux
        file = open('output.xyt')
        result_file = file.read()
        file.close()
    return result_file
    

def enrollment():
    name = input("Please make a username: ")
    # Add check to see if username has been used before 
    print("Please press finger againist prism")
    image = random.choice(os.listdir("C:\\Users\\jacob\\Desktop\\Fingerprints"))
    mindtct_results = run_mindtct(image)
    print("hellooooo")

def verification():
    print("test2")


def identification():
    print("test3")

choice = int(input("Hello welcome to our fingerprint scanner, please select from the following: \n 1. Enrollment \n 2. Verification \n 3. Identification \n"))
if(choice == 1):
    enrollment()
elif(choice == 2):
    verification()
elif(choice == 3):
    identification()

