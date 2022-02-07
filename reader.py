from PIL import Image

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
    8. Use mindtct to extract minutiae
    9. Find way to pump identifying info from step 1, classification from step 6, and minutiae info stored in the .xyt file generated from mindtct to database

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