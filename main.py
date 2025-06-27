from fasthtml.common import *
import google.generativeai as genai
import os
import logging
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('word_zoom_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv(override=True)  # Force override existing env vars
logger.info("Environment variables loaded from .env file")

# Configure the Gemini API key
try:
    api_key = os.environ['GOOGLE_API_KEY']
    logger.info("Retrieved GOOGLE_API_KEY from environment variables")
    
    # Debug: Log the actual model name being read
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')
    logger.info(f"GEMINI_MODEL from env: '{GEMINI_MODEL}'")
    logger.info(f"Raw GEMINI_MODEL value: {repr(os.environ.get('GEMINI_MODEL'))}")
    
    if not api_key or api_key == "your_api_key_here":
        logger.error("GOOGLE_API_KEY is not set or is still the placeholder value")
        print("ERROR: The GOOGLE_API_KEY is not set or is still the placeholder value. Please set it in the .env file.")
        exit(1)
    genai.configure(api_key=api_key)
    logger.info("Gemini AI API configured successfully")
    
    logger.info(f"Using Gemini model: {GEMINI_MODEL}")
except KeyError:
    logger.error("GOOGLE_API_KEY environment variable is not set")
    print("ERROR: The GOOGLE_API_KEY environment variable is not set. Please create a .env file and set it.")
    exit(1)

app, rt = fast_app()
logger.info("FastHTML app initialized successfully")

# Create the model once at startup
try:
    model = genai.GenerativeModel(GEMINI_MODEL)
    logger.info(f"Gemini model '{GEMINI_MODEL}' created successfully at startup")
except Exception as e:
    logger.error(f"Failed to create Gemini model at startup: {str(e)}")
    raise

# Stack to keep track of search terms and their contexts
search_history = []
MAX_HISTORY_SIZE = 10  # Keep last 10 searches for context

def add_to_search_history(word, context, definition):
    """Add a search term and its definition to the history stack"""
    search_entry = {
        'word': word,
        'context': context[:200],  # Keep first 200 chars of context
        'definition': definition
    }
    search_history.append(search_entry)
    
    # Keep only the last MAX_HISTORY_SIZE entries
    if len(search_history) > MAX_HISTORY_SIZE:
        search_history.pop(0)
    
    logger.info(f"Added '{word}' to search history. History size: {len(search_history)}")

def get_context_with_history(current_context):
    """Build enhanced context including previous searches"""
    if not search_history:
        return current_context
    
    history_context = "\n\nPrevious word definitions from this session:\n"
    for entry in search_history[-5:]:  # Include last 5 searches
        history_context += f"- {entry['word']}: {entry['definition']}\n"
    
    return current_context + history_context

@rt('/')
def get():
    logger.info("Home route accessed - serving main page")
    try:
        page_content = Titled('Word Zoom',
            Div(
                Div(
                    id='text-input', 
                    contenteditable='true',
                    data_placeholder='Paste your text here...',
                    style='width: 75%; height: calc(100vh - 40px); margin: 20px auto; padding: 20px; box-sizing: border-box; border: 1px solid #ddd; outline: none; font-family: Arial, sans-serif; font-size: 16px; line-height: 1.5; overflow-y: auto; background: white; border-radius: 8px;'
                ),
                style='margin: 0; padding: 0; width: 100vw; height: 100vh; overflow: hidden; display: flex; justify-content: center; align-items: flex-start; background: #f5f5f5;',
                id='content-wrapper'
            ),
            Script(src='/static/script.js'),
            Style("""
                body, html { 
                    margin: 0; 
                    padding: 0; 
                    width: 100%; 
                    height: 100%; 
                    overflow: hidden; 
                    font-family: Arial, sans-serif;
                }
                #text-input {
                    transition: opacity 0.5s ease-in-out;
                }
                #text-input.loading {
                    opacity: 0.3;
                }
                #text-input::-webkit-scrollbar {
                    width: 12px;
                }
                #text-input::-webkit-scrollbar-track {
                    background: #f1f1f1;
                }
                #text-input::-webkit-scrollbar-thumb {
                    background: #888;
                    border-radius: 6px;
                }
                #text-input::-webkit-scrollbar-thumb:hover {
                    background: #555;
                }
                #text-input:empty:before {
                    content: attr(data-placeholder);
                    color: #999;
                    pointer-events: none;
                }
                .word-definition {
                    background: #e3f2fd;
                    border-left: 3px solid #2196f3;
                    padding: 8px 12px;
                    margin: 8px 0;
                    border-radius: 4px;
                    font-style: italic;
                    color: #1976d2;
                    position: relative;
                    opacity: 0;
                    animation: fadeIn 0.5s ease-in-out forwards;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .word-definition .close-btn {
                    position: absolute;
                    top: 4px;
                    right: 8px;
                    background: none;
                    border: none;
                    font-size: 16px;
                    cursor: pointer;
                    color: #666;
                }
                .word-definition .close-btn:hover {
                    color: #333;
                }
                .defined-word {
                    background: #fff3e0;
                    border-bottom: 2px solid #ff9800;
                    cursor: pointer;
                    padding: 2px 4px;
                    border-radius: 3px;
                }
                .loading-indicator {
                    background: #ffecb3;
                    border-left: 3px solid #ffc107;
                    padding: 8px 12px;
                    margin: 8px 0;
                    border-radius: 4px;
                    color: #f57c00;
                    font-style: italic;
                    animation: pulse 1s infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.7; }
                }
            """)
        )
        logger.info("Main page content generated successfully")
        return page_content
    except Exception as e:
        logger.error(f"Error generating main page: {str(e)}")
        return P("An error occurred while loading the page.")

@rt('/define')
def get(word: str, context: str):
    start_time = time.time()
    logger.info(f"Definition route accessed - word: '{word}', context length: {len(context)} characters")
    logger.debug(f"Full context provided: {context[:200]}..." if len(context) > 200 else f"Full context: {context}")
    
    try:
        # Enhance context with search history
        enhanced_context = get_context_with_history(context)
        logger.info(f"Enhanced context length: {len(enhanced_context)} characters (includes {len(search_history)} previous searches)")
        
        prompt = f"""Provide a concise definition for the word '{word}' using the the following context: {enhanced_context}"""
        logger.info(f"Sending prompt to Gemini API for word definition")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        
        api_start_time = time.time()
        response = model.generate_content(prompt)
        api_end_time = time.time()
        api_duration = api_end_time - api_start_time
        
        if response and response.text:
            total_duration = time.time() - start_time
            logger.info(f"Successfully received definition from Gemini API - API call took {api_duration:.2f}s, total request took {total_duration:.2f}s")
            logger.info(f"Response length: {len(response.text)} characters")
            logger.debug(f"API response: {response.text[:100]}..." if len(response.text) > 100 else f"API response: {response.text}")
            
            # Add this search to history
            add_to_search_history(word, context, response.text)
            
            return P(response.text)
        else:
            logger.warning(f"Gemini API returned empty or None response after {api_duration:.2f}s")
            return P("Sorry, I couldn't generate a definition for that word.")
            
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"Error in definition route after {total_duration:.2f}s: {str(e)}")
        logger.error(f"Error occurred while processing word: '{word}' with context length: {len(context)}")
        return P("An error occurred while generating the definition. Please try again.")

if __name__ == "__main__":
    logger.info("Starting FastHTML server...")
    serve()
else:
    logger.debug("Module imported/reloaded")