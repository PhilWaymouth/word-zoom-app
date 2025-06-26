from fasthtml.common import *
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API key
# The GOOGLE_API_KEY should be set in a .env file in the same directory.
# You can get an API key from https://aistudio.google.com/app/apikey
try:
    api_key = os.environ['GOOGLE_API_KEY']
    if not api_key or api_key == "your_api_key_here":
        print("ERROR: The GOOGLE_API_KEY is not set or is still the placeholder value. Please set it in the .env file.")
        exit(1)
    genai.configure(api_key=api_key)
except KeyError:
    print("ERROR: The GOOGLE_API_KEY environment variable is not set. Please create a .env file and set it.")
    exit(1)

app, rt = fast_app()

def create_model():
    return genai.GenerativeModel('gemini-1.5-flash')

@rt('/')
def get():
    return Titled('Word Zoom',
        Div(
            Textarea(id='text-input', placeholder='Paste your text here...', style='width: 80%; height: 300px;'),
            id='content-wrapper'
        ),
        Script(src='/static/script.js')
    )

@rt('/define')
def get(word: str, context: str):
    model = create_model()
    prompt = f"""Provide a concise definition for the word '{word}' in the following context:

    {context}

    Definition:"""
    response = model.generate_content(prompt)
    return P(response.text)

serve()