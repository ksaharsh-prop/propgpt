from groq import Groq
import os

# Initialize Groq API client
GROQ_API_KEY = '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'  # Load your API key securely from environment variable
client = Groq(api_key=GROQ_API_KEY)

# Function to query Groq API and get property recommendations
def query_groq_api_city(query):
    try:
        # Prepare messages for the Groq API interaction
        messages = [
    {
  "role": "system",
  "content": """
  You are a Property assistant named PropGPT. Respond to greeting messages with your name and appropriate greetings.

  You are an NER agent. Your task is to extract only the city name from the request query. If the query does not contain a city name, explicitly mention 'City not found in the query'.
    Just give the name of city.
    Give the correct response.
  """
}
]






        messages.append({"role": "user", "content": query})

        # Query the Groq API with the appropriate model
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Adjust this to the correct model as per Groq API documentation
            messages=messages,
            temperature=1,
            max_tokens=1024,
        )

        # Debug: Print out the type and content of the full response
        # print("Full Completion Response:", completion)

        # Check if the response is a dictionary and contains 'choices'
        # if isinstance(completion, dict):
        response=completion.choices[0].message.content
        # else:
        #     return "Unexpected response structure."
        return response
    except Exception as e:
        return f"Error with Groq API: {str(e)}"
    





