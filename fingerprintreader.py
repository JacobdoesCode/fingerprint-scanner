import subprocess
import random
from PIL import Image
import string
from time import sleep
import sqlite3 
import tempfile
import os
import shutil
import sys
"""
General work flow

Intro
    1. Ask user to input 1 for enrollment, 2 for verification, 3 for identification
Enrollement
    1. Either ask user for name or generate them a random ID or both. This information will be called identifying info from now on
    2. Ask user to press finger againist prism
    3. Capture image
    4. Use Pillow to convert the image to grayscale
    6. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise repeat step 4
   -- 7. Use pcasys to classify fingerprint image
   -- 8. Use 'cwsq .75 *filename*' to convert to a WSQ compressed file
    9. Make temporary directory to host mindtct result files
    10. Run mindtct, read .xyt file into database, kill tmp directory

--Verification
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
   
--Identification
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
# Deletes temporary directory and restarts enrollment process 
def bad_fingerprint(temp_directory):
    print("Sorry we did not get a good enough picture, please try again!")
    shutil.rmtree(temp_directory)
    enrollment()

# Runs terminal command that checks fingerprint quality
def run_nfiq(grayscale_image_path):
    print("Checking fingerprint quality!")
    nfiq_process=subprocess.Popen(['nfiq', grayscale_image_path],stdout=subprocess.PIPE)
    nfiq_result= nfiq_process.communicate()
    return int(nfiq_result[0])

# Generates grayscale image
def convert_to_grayscale(image,temp_directory):
    print("Converting to Grayscale!")
    grayscale_image=Image.open("/home/jacob-mcclain/Desktop/fingerprints/"+image).convert('1')
    save_directory= os.path.join(temp_directory,'grayscale_image.jpg')
    grayscale_image.save(save_directory)
    nfiq_score = run_nfiq(save_directory)
    print(nfiq_score)
    if nfiq_score>=3:
        return save_directory
    else:
        bad_fingerprint(temp_directory)
        sys.exit()

# Generates fingerprint minutiae data
def run_mindtct(image):
    # Opens temporary directory
    with tempfile.TemporaryDirectory() as temp_directory:
        # Converts fingerprint image to grayscale and returns the new files location
        source_file_path=convert_to_grayscale(image,temp_directory)
        print("Extracting fingerprint features!")
        # Sets up a file path for the minutiae output
        result_file_path = os.path.join(temp_directory,'output')
        # Get minutiae data
        subprocess.check_call(['mindtct', source_file_path, result_file_path]) 
        # Read minutiae data into file
        file = open(result_file_path+'.xyt')
        result_file = file.read()
        file.close()
    return result_file
    
# Gets username, fingerprint minutiae data and sends it to database
def enrollment():
    username = input("Please make a username: ")
    # Add check to see if username has been used before 
    print("Please press finger againist prism")
    # Grabs random image from fingerprint directory I have on my desktop, will be replaced once camera is setup
    image = random.choice(os.listdir("/home/jacob-mcclain/Desktop/fingerprints"))
    mindtct_results = run_mindtct(image)
    con = sqlite3.connect('/home/jacob-mcclain/Desktop/fingerprint-database/fingerprints')
    cur = con.cursor()
    SQL='''INSERT INTO fingerprints(publicId,minutiaeDetection) VALUES(?,?)'''
    cur.execute(SQL,(username,mindtct_results))
    con.commit()
    con.close()

def verification():
    print("test2")


def identification():
    print("test3")

# Start, get user choice
choice = int(input("Hello welcome to our fingerprint scanner, please select from the following: \n 1. Enrollment \n 2. Verification \n 3. Identification \n"))
if(choice == 1):
    enrollment()
elif(choice == 2):
    verification()
elif(choice == 3):
    identification()

