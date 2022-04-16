import subprocess
import random
from PIL import Image
import sqlite3 
import tempfile
import os
import shutil
import sys
from cryptography.fernet import Fernet
import hashlib

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
    8. Make temporary directory to host mindtct result files
    9. Run mindtct, read .xyt file into database, kill tmp directory

Verification
    May want to change to use pcasys as a potential "quick negative", would improve best case running speed but worsen worst case
    1. Ask user for identifying info
    2. Ask user to press finger againist prism
    3. Capture image 
    4. Use Pillow to convert the image to grayscale
    5. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise repeat step 3
    6. Use mindtct to extract minutiae
    7. Pull minutiae info from database row with matching identifying info
    8. Use BOZORTH3 to compare minutiae
    9. If the match score reaches a certain score (according to documentation above 40 is considered a true match) then pass, otherwise fail   
   
Identification
    1. Ask user to press finger againist prism
    2. Capture image 
    3. Use Pillow to convert the image to grayscale
    4. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise repeat step 2
   -- 5. Use pcasys to classify fingerprint image
    6. Use mindtct to extract mintuiae, this will be referred to as the probe file from now on 
    7. Pull all fingerprint minutiae data from database thes will be referred to as the gallery files from now on
    8. Run probe file againist all gallery files using bozorth one to many
    9. If the match score reaches a certain score then pass
"""

# Start, get user choice
def main():
    choice = int(input("Hello welcome to our fingerprint scanner, please select from the following: \n 1. Enrollment \n 2. Verification \n 3. Identification \n"))
    if(choice == 1):
        enrollment()
    elif(choice == 2):
        verification()
    elif(choice == 3):
        identification()

def read_key():
    try:
        key = open("key","rb").read()
    except IOError:
        print("Key not found, exiting")
        sys.exit()
    return key

def encrypt(value):
    key = read_key()
    value = value.encode()
    f = Fernet(key)
    return f.encrypt(value)

def decrypt(value):
    key = read_key()
    f = Fernet(key)
    value=f.decrypt(value)
    return value.decode()

# Gets username, fingerprint minutiae data and sends it to database
# Improvement: Add check to see if username has been used before 
def enrollment():
    username = input("Please make a username: ")
    hashed_user=hashlib.sha3_224(username.encode('utf-8'))
    username = encrypt(username)
    image = take_image()
    mindtct_results = run_mindtct(image)
    hashed_minutiae=hashlib.sha3_224(mindtct_results.encode('utf-8'))
    mindtct_results = encrypt(mindtct_results)
    con = sqlite3.connect('./fingerprints')
    cur = con.cursor()
    SQL='''INSERT INTO fingerprints(publicId,minutiaeDetection,publicIdHash,minutiaeDetectionHash) VALUES(?,?,?,?)'''
    cur.execute(SQL,(username,mindtct_results,hashed_user.digest(),hashed_minutiae.digest()))
    con.commit()
    con.close()

# Allows user to claim an identity and uses fingerprint recognization to see if they are who they say 
# Improvement: Add check to see if username exists, if not print out verification failed
def verification():
    username = input("Please enter your username: ")
    image = take_image()
    mindtct_results = run_mindtct(image)
    con = sqlite3.connect('./fingerprints')
    cur = con.cursor()
    # Runs SQL query to find minutiae features of claimed identity
    hashed_user=hashlib.sha3_224(username.encode('utf-8'))
    username = encrypt(username)
    SQL='''SELECT minutiaeDetection FROM fingerprints WHERE publicIdHash=?'''
    cur.execute(SQL,(hashed_user.digest(),))
    row = cur.fetchone()
    con.commit()
    con.close()
    if not row:
        # Error message intentionally vague. Feels like a bad idea to confirm or deny that a specific exists in a database
        print("Verification process failed, please try again")
        sys.exit()
    print("Verifying identity!")
    # Attempts to match input fingerprint to fingerprint of claimed identity
    results=decrypt(row[0])
    match_score = run_bozorth3_one_to_one(mindtct_results,results)
    if match_score >40:
        print("Identity verified")
    else:
        print("Verification failed, exiting")
        sys.exit()

# Compares a fingerprint againist all fingerprints in database until it finds a match
# Improvement: Use Bozorth3 one-to-many function instead
def identification():
    image = take_image()
    print("Input Image", image)
    print('Searching for fingerprint match!')
    mindtct_results = run_mindtct(image)
    con = sqlite3.connect('./fingerprints')
    cur = con.cursor()
    # Runs SQL query to grab all minutiae features in database
    SQL='''SELECT minutiaeDetection FROM fingerprints'''
    cur.execute(SQL)
    rows = cur.fetchall()
    con.close()
    if not rows:
        print("You do not appear to be enrolled in the connected database, please enroll and try again.")
        sys.exit()
    print("Beginning identification!")
    # Runs through all rows in database, attempting to match them with input fingerprint
    match_score = run_bozorth3_one_to_many(mindtct_results, rows)
    print(match_score)
    for i in range(0,len(match_score)):
        if(int(match_score[i])>40 and match_score[i]==max(match_score)):
            row=rows[i]
            row = decrypt(row[0])
            successfulIdentification(row)
    print("No match found, exiting")
    sys.exit()

def take_image():
    print("Please press finger againist prism")
    # Grabs random image from fingerprint directory I have on my desktop, will be replaced once camera is setup
    image = random.choice(os.listdir("/home/jacob-mcclain/Desktop/fingerprints"))
    print(image)
    return image

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

# Generates grayscale image
def convert_to_grayscale(image,temp_directory):
    print("Converting to Grayscale!")
    grayscale_image=Image.open("/home/jacob-mcclain/Desktop/fingerprints/"+image).convert('1')
    save_directory= os.path.join(temp_directory,'grayscale_image.jpg')
    grayscale_image.save(save_directory)
    # Runs fingerprint quality check
    nfiq_score = run_nfiq(save_directory)
    # If quality check succeeds then carry on with minutiae extraction
    if nfiq_score>=3:
        return save_directory
    # If quality check fails then restart enrollment 
    else:
        bad_fingerprint(temp_directory)
        sys.exit()    

# Runs terminal command that checks fingerprint quality
def run_nfiq(grayscale_image_path):
    print("Checking fingerprint quality!")
    nfiq_process=subprocess.Popen(['nfiq', grayscale_image_path],stdout=subprocess.PIPE)
    nfiq_result= nfiq_process.communicate()
    return int(nfiq_result[0])

# Deletes temporary directory and restarts enrollment process 
def bad_fingerprint(temp_directory):
    print("Sorry we did not get a good enough picture, please try again!")
    shutil.rmtree(temp_directory)
    take_image()

# Runs terminal command that gets match score
def run_bozorth3_one_to_one(probe_info, gallery_info):
    # Creates two temporary files with the .xyt file extension
    with tempfile.NamedTemporaryFile(suffix=".xyt") as temp_probe_file:
        with tempfile.NamedTemporaryFile(suffix=".xyt") as temp_gallery_file:
            # Opens up both temporary files and writes the values of input arguments
            probe_file_open = open(temp_probe_file.name,"w")
            probe_file_open.write(probe_info)
            probe_file_open.close()

            gallery_file_open = open(temp_gallery_file.name,"w")
            gallery_file_open.write(gallery_info)
            gallery_file_open.close()

            # Uses Bozorth3 to get the match score of the input arguments
            bozorth3_process=subprocess.Popen(['bozorth3', temp_probe_file.name, temp_gallery_file.name],stdout=subprocess.PIPE)
            bozorth3_result= bozorth3_process.communicate()
    # Returns match score
    return int(bozorth3_result[0])


# Runs terminal command that gets match score
# use -p  flag for bozorth
# -G flag not working 
def run_bozorth3_one_to_many(probe_info, gallery_info_rows):
    # Creates two temporary files with the .xyt file extension

    one_to_many_root = tempfile.mkdtemp()
    probe_path = os.path.join(one_to_many_root,'probe_file.xyt')
    file = open(probe_path,"w")
    file.write(probe_info)
    file.close()

    files=[]
    for count,row in enumerate(gallery_info_rows):
        row = decrypt(row[0])
        file_name = str(count)+".xyt"
        file_location = os.path.join(one_to_many_root,file_name)
        files.append(file_location)
        file = open(file_location,"w")
        file.write(row)
        file.close()
    command = ['bozorth3', '-p', probe_path] + files
    result = subprocess.check_output(command).strip()
    result_split = result.decode('utf8').split('\n')
    shutil.rmtree(one_to_many_root)
    return result_split

# Called from identification upon successful fingerprint match
# need to change to use hashes
def successfulIdentification(minutiae):
    hashed_min=hashlib.sha3_224(minutiae.encode('utf-8'))
    con = sqlite3.connect('./fingerprints')
    cur = con.cursor()
    SQL='''SELECT publicId FROM fingerprints WHERE minutiaeDetectionHash=?'''
    cur.execute(SQL,(hashed_min.digest(),))
    row = cur.fetchone()
    con.close()
    if not row:
        print("System error has occured, exiting")
        sys.exit()
    print(row)
    result=decrypt(row[0])
    print("Match found with user", result)
    sys.exit()

if __name__ == "__main__":
    main()