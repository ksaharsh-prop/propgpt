from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
from typing import List, Optional
import uvicorn
from groqmodel import query_groq_api_city
import requests
import logging
import random
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI instance
app = FastAPI()

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection settings
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "1234"
DB_NAME = "property_db"

# User Agent pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
]

# Property model
class Property(BaseModel):
    owner_name: str
    location: str
    price: float

# Enhanced fetch_city_id function
def fetch_city_id(searchtxt):
    try:
        url = f"https://www.magicbricks.com/mbutility/homepageAutoSuggest?searchtxt={searchtxt}"
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.magicbricks.com/",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        logger.info(f"Fetching city ID for: {searchtxt}")
        logger.info(f"Full URL: {url}")
        
        response = requests.get(
            url, 
            headers=headers, 
            timeout=15,  # Increased timeout
        )
        
        logger.info(f"Response Status: {response.status_code}")
        
        # Log response content for debugging
        logger.debug(f"Response Content: {response.text}")
        
        response.raise_for_status()
        data = response.json()
        
        for location in data.get('locationMap', {}).get('LOCATION', []):
            if location.get('result') == searchtxt:
                return location.get('city')
        
        logger.warning(f"No city found for: {searchtxt}")
        return None
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching city ID: {e}")
        logger.error(traceback.format_exc())
        return None
    except ValueError as e:
        logger.error(f"JSON parsing error: {e}")
        logger.error(traceback.format_exc())
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        return None

# Enhanced fetch_property_data function
def fetch_property_data(cityId):
    try:
        url = f"https://www.magicbricks.com/mbsrp/suggestedProjectData?locid=undefined&cityId={cityId}&budgetMin=&budgetMax=&mainSrp=Y"
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.magicbricks.com/",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        logger.info(f"Fetching property data for city ID: {cityId}")
        logger.info(f"Full URL: {url}")
        
        response = requests.get(
            url, 
            headers=headers, 
            timeout=15  # Increased timeout
        )
        
        logger.info(f"Response Status: {response.status_code}")
        
        # Log response content for debugging
        logger.debug(f"Response Content: {response.text}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching property data: {e}")
        logger.error(traceback.format_exc())
        return None
    except ValueError as e:
        logger.error(f"JSON parsing error: {e}")
        logger.error(traceback.format_exc())
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        return None

# Extract property details
def extract_property_details(query: str):
    try:
        response = query_groq_api_city(query)
        logger.info(f"Groq API response: {response}")
        
        cityId = fetch_city_id(response)
        logger.info(f"Fetched City ID: {cityId}")
        
        if cityId:
            final_response = fetch_property_data(cityId)
        else:
            final_response = response
        
        return final_response
    except Exception as e:
        logger.error(f"Error in extract_property_details: {e}")
        logger.error(traceback.format_exc())
        return None

# Chatbot UI endpoint
@app.get("/")
async def chatbot_ui(request: Request):
    return templates.TemplateResponse("chatbot_ui.html", {"request": request})

# Chatbot endpoint
@app.post("/chatbot/")
async def chatbot(query: Optional[str] = None):
    if not query:
        return {"message": "Please provide a query with price or location to get property suggestions."}
    
    try:
        logger.info(f"Received query: {query}")
        
        response = extract_property_details(query)
        
        if response and "projectsCards" in response:
            final_response = response["projectsCards"][:2]
            final_list = []
            
            for prop in final_response:
                final_dict = {
                    "lmtDName": prop.get("lmtDName", ""),
                    "minPriceDesc": prop.get("minPriceDesc", ""),
                    "maxPriceDesc": prop.get("maxPriceDesc", ""),
                    "imageUrl": prop.get("imageUrl", "")
                }
                final_list.append(final_dict)
            
            return {
                "message": "",
                "properties": final_list
            }
        else:
            return {
                "message": str(response),
                "properties": []
            }
    
    except Exception as e:
        logger.error(f"Unexpected error in chatbot endpoint: {e}")
        logger.error(traceback.format_exc())
        return {
            "message": f"An error occurred: {str(e)}",
            "properties": []
        }

# Main entry point
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)