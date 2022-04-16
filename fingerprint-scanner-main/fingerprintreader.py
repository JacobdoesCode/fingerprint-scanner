import subprocess
import random
import string
from time import sleep
import sqlite3 
import tempfile
import os
import shutil
import sys
from cryptography.fernet import Fernet
import hashlib
from picamera import PiCamera


"""
General work flow

Intro
    1. Ask user to input 1 for enrollment, 2 for verification, 3 for identification
Enrollement
    1. Ask user for username this information will be called identifying info from now on
    2. Ask user to press finger againist prism
    3. Capture image
    4. Use Convert to convert the image to grayscale
    6. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise close
    7. Make temporary directory to host mindtct result files
    8. Run mindtct, read .xyt file into database, kill tmp directory

Verification
    1. Ask user for identifying info
    2. Ask user to press finger againist prism
    3. Capture image 
    4. Use Convert to convert the image to grayscale
    5. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise close
    6. Use mindtct to extract minutiae
    7. Pull minutiae info from database row with matching identifying info
    8. Use BOZORTH3 to compare minutiae
    9. If the match score reaches a certain score then pass, otherwise fail   
   
Identification
    1. Ask user to press finger againist prism
    2. Capture image 
    3. Use Convert to convert the image to grayscale
    4. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise close
    5. Use mindtct to extract mintuiae, this will be referred to as the probe file from now on 
    6. Pull all fingerprint minutiae data from database this will be referred to as the gallery files from now on
    7. Run probe file againist all gallery files using bozorth one to many
    8. If a match score reaches a certain score then pass
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

# Read in encryption key
def read_key():
    try:
        key = open("key","rb").read()
    except IOError:
        print("Key not found, exiting")
        sys.exit()
    return key

# Encrypt key using AES-based encryption algorithm
def encrypt(value):
    key = read_key()
    value = value.encode()
    f = Fernet(key)
    return f.encrypt(value)

# Decrypt key using AES-based encryption algorithm
def decrypt(value):
    key = read_key()
    f = Fernet(key)
    value=f.decrypt(value)
    return value.decode()

# Gets username, fingerprint minutiae data and sends it to database
def enrollment():
    username = input("Please make a username: ")
    # Gets hash and encryption values for username
    hashed_user=hashlib.sha3_224(username.encode('utf-8'))
    username = encrypt(username)
    image = take_image()
    mindtct_results = run_mindtct(image)
    # Gets hash and encryption values for minutiae
    hashed_minutiae=hashlib.sha3_224(mindtct_results.encode('utf-8'))
    mindtct_results = encrypt(mindtct_results)
    # Inserts all data associated with user into database
    con = sqlite3.connect('./fingerprints.db')
    cur = con.cursor()
    SQL='''INSERT INTO fingerprints(publicId,minutiaeDetection,publicIdHash,minutiaeDetectionHash) VALUES(?,?,?,?)'''
    cur.execute(SQL,(username,mindtct_results,hashed_user.digest(),hashed_minutiae.digest()))
    con.commit()
    con.close()

# Allows user to claim an identity and uses fingerprint recognization to see if they are who they say 
def verification():
    username = input("Please enter your username: ")
    # Takes reference image and gets minutiae data
    image = take_image()
    mindtct_results = run_mindtct(image)
    # Hashes username for reference point for sql
    hashed_user=hashlib.sha3_224(username.encode('utf-8'))
    # Runs SQL query to find minutiae features of claimed identity
    con = sqlite3.connect('./fingerprints.db')
    cur = con.cursor()
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
    print(match_score)
    if match_score >=20:
        print("Identity verified")
    else:
        print("Verification failed, exiting")
        sys.exit()

# Compares a fingerprint againist all fingerprints in database until it finds a match
def identification():
    image = take_image()
    print('Searching for fingerprint match!')
    mindtct_results = run_mindtct(image)
    # Runs SQL query to grab all minutiae features in database
    con = sqlite3.connect('./fingerprints.db')
    cur = con.cursor()
    SQL='''SELECT minutiaeDetection FROM fingerprints'''
    cur.execute(SQL)
    rows = cur.fetchall()
    con.commit()
    con.close()
    if not rows:
        print("Connected database does not appear to have any rows.")
        sys.exit()
    print("Beginning identification!")
    # Runs through all rows in database, attempting to match them with input fingerprint
    match_score = run_bozorth3_one_to_many(mindtct_results, rows)
    print(match_score)
    # Loops through list of match scores given by the one to many funcion and checks if one is above 20
    for i in range(0,len(match_score)):
        if(int(match_score[i])>=20 and match_score[i]==max(match_score)):
            row=rows[i]
            row = decrypt(row[0])
            # Runs function that outputs that matched user
            successfulIdentification(row)
    # Prints and exits if no user is found
    print("No match found, exiting")
    sys.exit()


def take_image():
    # Sets up camera, changes resolution and then captures image
    image = "fingerprint.jpg" # This is just a variable for the name of the file since I use capture for it and then return it
    camera = PiCamera()
    camera.resolution = (1024,768)
    sleep(3)
    camera.capture(image)
    camera.close()
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
        subprocess.check_call(['/home/pi/Documents/bin/mindtct', source_file_path, result_file_path])
        # Read minutiae data into file
        file = open(result_file_path+'.xyt')
        result_file = file.read()
        file.close()
    return result_file

# Generates grayscale image
def convert_to_grayscale(image,temp_directory):
    print("Converting to Grayscale!")
    save_directory= os.path.join(temp_directory,'grayscale_image.jpg')
    # Converts fingerprint to grayscale and sets it in specified temporary directory
    subprocess.check_call(['convert', "./"+image,"-colorspace" ,"Gray" ,save_directory])
    # Deletes non-grayscaled print
    subprocess.check_call(['rm', "./"+image]) 
    # Runs fingerprint quality check
    nfiq_score = run_nfiq(save_directory)
    # If quality check succeeds then carry on with minutiae extraction
    if nfiq_score<=3:
        return save_directory
    # If quality check fails then restart enrollment 
    else:
        print("Sorry we did not get a good enough picture, exiting")
        sys.exit() 

# Runs terminal command that checks fingerprint quality
def run_nfiq(grayscale_image_path):
    print("Checking fingerprint quality!")
    # Runs nfiq with given grayscaled print and returns result
    nfiq_process=subprocess.Popen(["/home/pi/Documents/bin/nfiq" , grayscale_image_path],stdout=subprocess.PIPE)
    nfiq_result= nfiq_process.communicate()
    return int(nfiq_result[0])

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
            bozorth3_process=subprocess.Popen(['/home/pi/Documents/bin/bozorth3', temp_probe_file.name, temp_gallery_file.name],stdout=subprocess.PIPE)
            bozorth3_result= bozorth3_process.communicate()
    # Returns match score
    return int(bozorth3_result[0])


# Runs terminal command that gets match score for one to many
# -G flag not working 
def run_bozorth3_one_to_many(probe_info, gallery_info_rows):
    # Jacob sold his soul to make this work
    # Creates two temporary files with the .xyt file extension
    one_to_many_root = tempfile.mkdtemp()
    probe_path = os.path.join(one_to_many_root,'probe_file.xyt')
    file = open(probe_path,"w")
    file.write(probe_info)
    file.close()

    # Loops through minutiae data, writes them to files ands them to list of files
    files=[]
    # For loop that gets the row data and well as its index
    for count,row in enumerate(gallery_info_rows):
        row = decrypt(row[0])
        # Sets the file name to be the index number.xyt, this naming scheme ensures the file names will be unique
        file_name = str(count)+".xyt"
        file_location = os.path.join(one_to_many_root,file_name)
        # Adds the new files location to the files list
        files.append(file_location)
        # writes the row data to the new file
        file = open(file_location,"w")
        file.write(row)
        file.close()
    # Uses bozorth to run one probe file againist all the different gallery files
    command = ['/home/pi/Documents/bin/bozorth3', '-p', probe_path] + files
    result = subprocess.check_output(command).strip()
    # Puts the resulting match scores into a list split by new line characters and deletes temp directory
    result_split = result.decode('utf8').split('\n')
    shutil.rmtree(one_to_many_root)
    return result_split

# Called from identification upon successful fingerprint match
def successfulIdentification(minutiae):
    hashed_min=hashlib.sha3_224(minutiae.encode('utf-8'))
    # Gets user associated with the identified minutiae 
    con = sqlite3.connect('./fingerprints.db')
    cur = con.cursor()
    SQL='''SELECT publicId FROM fingerprints WHERE minutiaeDetectionHash=?'''
    cur.execute(SQL,(hashed_min.digest(),))
    row = cur.fetchone()
    con.close()
    if not row:
        print("System error has occured, exiting")
        sys.exit()
    # Prints out associated user
    result=decrypt(row[0])
    print("Match found with user", result)
    sys.exit()

if __name__ == "__main__":
    main()
