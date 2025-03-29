from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
from PIL import Image
from google.genai import types
from io import BytesIO
import base64
import os
from fastapi import FastAPI, HTTPException
import json
import re

# Load environment variables
load_dotenv()

# Get API key                                                                                                                                                                                                                                                     
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextRequest(BaseModel):
    prompt:str

@app.post("/generate-text")
async def generate_text(request: TextRequest):
    contents = request.prompt
    response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=contents 
    )
    return response.text



class ImageRequest(BaseModel):
    prompt: str  # Changed from 'contents' to match common practice

@app.post("/generate-image")
async def generate_image(request: ImageRequest):
    contents = request.prompt

    try:
        # Generate content
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp-image-generation",
            contents=contents,
            config=types.GenerateContentConfig(
              response_modalities=['Text', 'Image']
            )
        )
                # Check for images in response
        
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                image = Image.open(BytesIO((part.inline_data.data)))

                # save the image
                image.save('gemini-native-image.png')

                #read the image
                with open('gemini-native-image.png', 'rb') as image_file:
                    image_data = image_file.read()
                    image_str = base64.b64encode(image_data).decode("utf-8")     
                    return {"image": image_str}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# edit image 
class EditImageRequest(BaseModel):
    image: str
    prompt: str

@app.post("/edit-image")
async def edit_image(request: EditImageRequest):
    text_input = request.prompt
    image_data = base64.b64decode(request.image)
    image = Image.open(BytesIO(image_data))
    try:
        response = client.models.generate_content(
        model="gemini-2.0-flash-exp-image-generation",
        contents=[text_input, image],
        config=types.GenerateContentConfig(
        response_modalities=['Text', 'Image']
        )
    )       
        for part in response.candidates[0].content.parts:
                if part.text is not None:
                    print(part.text)
                elif part.inline_data is not None:
                    image = Image.open(BytesIO((part.inline_data.data)))
                    image.save('gemini-edited-image.png')
                    #read the image
                    with open('gemini-native-image.png', 'rb') as image_file:
                        image_data = image_file.read()
                        image_str = base64.b64encode(image_data).decode("utf-8")     
                        return {"image": image_str}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-trends")
async def get_trends():
    print("Getting trends")
    trends = json.load(open('trending.json'))
    return trends


@app.post("/get-hashtags")
async def generate_text(request: TextRequest):
    contents = f"""
    You are a hashtag generator.
    you are given a description of a product and you need to generate 10 hashtags for the product.
    the hashtags should be relevant to the product and should be in the style of the product.
    the product description is: {request.prompt}
    Note the output should be a json array of strings. with key as "hashtags" and value as an array of strings.
    """
    response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=contents 
    )
    print(response.text)
    match = re.search(r"\{.*\}", response.text, re.DOTALL)
    
    if match:
        json_str = match.group(0)  # Extract the JSON part
        try:
            json_response = json.loads(json_str)
            return json_response  # Return the extracted JSON
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response"}
    else:
        return {"error": "No JSON found in response"}
    #out {'hashtags': ['#CatsofInstagram', '#Instacat', '#Meow', '#Kitty', '#Feline', '#CatLover', '#CuteCats', '#Caturday', '#Purrfect', '#CatsOfTwitter']}

# run the app: uvicorn app:app --reload
