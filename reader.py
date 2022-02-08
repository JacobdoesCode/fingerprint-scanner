import random
from PIL import Image
import string
from picamera import PiCamera
from time import sleep


"""
General work flow

Intro
    1. Ask user to input 1 for enrollment, 2 for verification, 3 for identification
Enrollement
    1. Either ask user for name or generate them a random ID or both. This information will be called identifying info from now on
    2. Ask user to press finger againist prism
    3. Capture image
    4. Use jpegtran (if it is ever gotten working) or Pillow to convert the image to grayscale
    5. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise repeat step 4
    6. Use pcasys to classify fingerprint image
    7. Use 'cwsq .75 *filename*' to convert to a WSQ compressed file
    8. Make temporary directory to host mindtct result files
    9. Run mindtct, read .xyt file into database, kill tmp directory

Verification
    May want to change to use pcasys as a potential "quick negative", would improve best case running speed but worsen worst case
    1. Ask user for identifying info
    2. Ask user to press finger againist prism
    3. Capture image 
    4. Use jpegtran (if it is ever gotten working) or Pillow to convert the image to grayscale
    5. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise repeat step 3
    6. Use 'cwsq .75 *filename*' to convert to a WSQ compressed file
    7. Use mindtct to extract minutiae
    8. Pull minutiae info from database row with matching identifying info
    9. Use BOZORTH3 to compare minutiae
   10. If the match score reaches a certain score (There's a suggested score in the user's guide) then pass, otherwise fail   
   
Identification
    1. Ask user to press finger againist prism
    2. Capture image 
    3. Use jpegtran (if it is ever gotten working) or Pillow to convert the image to grayscale
    4. Use nfiq to determine the quality of the fingerprint image, if it is above a certain score then proceed, otherwise repeat step 2
    5. Use pcasys to classify fingerprint image
    6. Use 'cwsq .75 *filename*' to convert to a WSQ compressed file
    7. Use mindtct to extract mintuiae 
    8. Pull fingerprint minutiae data from database rows with matching classification 
    9. Compare this minutiae data with the captured fingerprint image's minutiae data
    10. If one is eventually found then pass, otherwise fail
"""

def enrollment():
    name = input("Please enter your name: ")
    print("Please press finger againist prism")


def verification():
    print("test2")


def identification():
    print("test3")

camera = PiCamera()
choice = int(input("Hello welcome to our fingerprint scanner, please select from the following: \n 1. Enrollment \n 2. Verification \n 3. Identification \n"))
if(choice == 1):
    enrollment()
if(choice == 2):
    verification()
if(choice == 3):
    identification()

