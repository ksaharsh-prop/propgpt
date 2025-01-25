from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware  # CORS middleware
from pydantic import BaseModel
import mysql.connector
from typing import List, Optional
import uvicorn
from groqmodel import query_groq_api_city
import requests


# FastAPI instance
app = FastAPI()

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Allow CORS for frontend interaction (you can adjust origins for more security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Can be specific origins like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database connection settings (adjust these to your MySQL setup)
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "1234"
DB_NAME = "property_db"

# Create a Pydantic model to represent property data
class Property(BaseModel):
    owner_name: str
    location: str
    price: float

# Database query function to get properties from MySQL
def get_properties_from_db(price_range=None, location=None):
    query = '''SELECT owner_name, location, price FROM property_listing WHERE 1=1'''
    params = []

    # Add filters to query based on user input
    if price_range:
        query += ''' AND price <= %s '''
        params.append(float(price_range))
    if location:
        query += ''' AND (location LIKE %s) '''
        params.append(location)

    # Connect to the MySQL database
    connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, tuple(params))
    result = cursor.fetchall()

    cursor.close()
    connection.close()

    # Return the properties as a list of Pydantic models
    return [Property(owner_name=prop['owner_name'], location=prop['location'], price=prop['price']) for prop in result]
###############################
#############################
#below is the response from groq
###############

def fetch_city_id(searchtxt):
    url = f"https://www.magicbricks.com/mbutility/homepageAutoSuggest?searchtxt={searchtxt}"
    print("url",url)

    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.magicbricks.com/",
    "Accept-Language": "en-US,en;q=0.9",
}
    response = requests.get(url,headers=headers)
    print("api_response",response)
    if response.status_code == 200:
        data = response.json()
        for location in data.get('locationMap', {}).get('LOCATION', []):
            if location.get('result') == searchtxt:
                return location.get('city')
    return None


def fetch_property_data(cityId):
    url = f"https://www.magicbricks.com/mbsrp/suggestedProjectData?locid=undefined&cityId={cityId}&budgetMin=&budgetMax=&mainSrp=Y"
    print("url",url)

    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.magicbricks.com/",
    "Accept-Language": "en-US,en;q=0.9",
}
    response = requests.get(url,headers=headers)
    print("api_response",response)
    if response.status_code == 200:
        data = response.json()
        return data 
    return None

# Function to extract price and location using Ollama model
def extract_property_details(query: str):
    
    response = query_groq_api_city(query)
    print("response",response)
    cityId=fetch_city_id(response)
    if cityId:
        
        
        final_response=fetch_property_data(cityId)
        print("final_response",final_response)
    else:
         final_response=response   
    return final_response

# Endpoint for the chatbot interaction
@app.get("/")
async def chatbot_ui(request: Request):
    return templates.TemplateResponse("chatbot_ui.html", {"request": request})

# Endpoint to process the user's query
@app.post("/chatbot/")
async def chatbot(query: Optional[str] = None):
    if query:
        # Debug: Print the received query to ensure it's arriving correctly
        print("Received query:", query)

        # Extract price and location using Ollama
        response= extract_property_details(query)
        final_response=response["projectsCards"][:2]
        final_dict={}
        final_list=[]
        for prop in final_response:
            
            final_dict["lmtDName"]=prop["lmtDName"]
            final_dict["minPriceDesc"]=prop["minPriceDesc"]
            final_dict["maxPriceDesc"]=prop["maxPriceDesc"]
            final_dict["imageUrl"]=prop["imageUrl"]
            print(final_dict)
            final_list.append(final_dict)
        
        print(final_list)    
        # response["projectsCards"].pop("amenitiesDisp")
        if "projectsCards" in response:
            
            return {
            "message": "",
            "properties": final_list
        }
        # If price and location are found, query the database
        # if price and location:
        #     properties = get_properties_from_db(price_range=price, location=location)
        #     return {
        #         "message": f"Here are the properties based on your query: {query}",
        #         "properties": properties
        #     }
        # elif price or location:
        #     properties = get_properties_from_db(price_range=price, location=location)
        #     return {
        #         "message": f"Here are the properties based on the extracted details: {query}",
        #         "properties": properties
        #     }
        else:
        
            return {
                "message": f"{response}",
                "properties": []
            }
    else:
        return {"message": "Please provide a query with price or location to get property suggestions."}

# Main entry point to run the application
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
