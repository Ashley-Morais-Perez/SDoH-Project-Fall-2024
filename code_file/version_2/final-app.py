from flask import Flask, render_template, request, url_for
from mongoConnect import mongodbconnection  # Import MongoDB connection function
from dotenv import load_dotenv  # For loading environment variables
import json  
import requests 
import urllib.parse  
import os  

# Load the .env file to read environment variables
load_dotenv()

# Connect to the MongoDB database
client = mongodbconnection()
collection = client["sdoh_resources"]  # Access the "sdoh_resources" collection

# Get the unique values of "delivery_method" from the database to use in the form
unique_delivery_method = collection.distinct("delivery_method")
print('Unique Delivery Method: ', unique_delivery_method)

# Define the base URL for the Google Maps Geocoding API
search = 'https://maps.googleapis.com/maps/api/geocode/json?address='
api_key = os.getenv("GOOGLE_MAPS_API")  # Retrieve the Google Maps API key from environment variables

# Define a mapping between categories and their associated tags
category_mapping = {
    "Food & Nutrition Services": ["Food Pantries", "WIC Service"],
    "Housing & Utility Assistance": ["Emergency Housing", "Emergency Energy and Utility Assistance"],
    "Health & Medical Services": ["Health Clinics", "Mental Health Services", "Medical Insurance"],
    "Community & Family Services": ["Community Assistance", "Family and Childrens Services (Chambers/Civics)", "Family and Childrens Services (Government/Elected)"],
    "Legal & Social Assistance": ["Domestic Violence", "Social Work Services"],
    "Emergency & Crisis Services": ["Important Numbers / Hotlines", "Emergency Housing", "Emergency Energy and Utility Assistance"],
    "Employment & Veteran Services": ["Employment"],
    "Transportation Services": ["Transportation"],
}

# Initialize the Flask app
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    # Handle the POST request when the form is submitted
    if request.method == 'POST':
        # Get form data from the request
        zip_code = request.form['zipcode']
        distance = request.form['distance']
        category_response = request.form.get('category')
        deliverymethod_response = request.form['deliverymethod']

        # Map the selected category to corresponding filter tags
        category_response = category_mapping.get(category_response, [])

        # Ensure deliverymethod_response is always a list (or the 'all' option is selected)
        if deliverymethod_response == 'all':
            deliverymethod_response = unique_delivery_method
        else:
            deliverymethod_response = [deliverymethod_response]  # Convert to list

        # Ensure category_response is always a list
        if isinstance(category_response, str):
            category_response = [category_response]

        # Convert the distance to an integer and calculate in meters
        distance_miles = int(distance)
        distance_meters = distance_miles * 1609.34  # Convert miles to meters

        # URL encode the zip code to prepare it for the API request
        location = urllib.parse.quote(zip_code)
        url = search + location + '&key=' + api_key  # Create the Google Maps API request URL

        # Send the request to the Google Maps API and parse the response
        response = requests.get(url).json()

        # Try to extract the geometry bounds (northeast and southwest) from the API response
        try:
            partialPolygon = response['results'][0]['geometry']['bounds']

            # Calculate the midpoint by averaging the latitudes and longitudes of the northeast and southwest corners
            northeast = partialPolygon['northeast']
            southwest = partialPolygon['southwest']

            center_lat = (northeast['lat'] + southwest['lat']) / 2
            center_lng = (northeast['lng'] + southwest['lng']) / 2

            # The center of the bounding box (midpoint)
            center_coordinates = [center_lng, center_lat]

        except (KeyError, IndexError):
            # If there is an error (e.g., invalid ZIP code), render the page with an error message
            return render_template(
                'index.html',
                error="Invalid ZIP code or Google Maps API error.",
                category=category_mapping.keys(),
                unique_delivery_method=unique_delivery_method
            )

        # Define a function to create a query for geographic search (within a distance)
        def create_geo_query(category_response, deliverymethod_response):
            return {
                "geometry": {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": center_coordinates
                        },
                        "$maxDistance": distance_meters  # Limit to the specified distance in meters
                    }
                },
                "filter_tags": {"$in": category_response},  # Filter by selected categories
                "delivery_method": {"$in": deliverymethod_response}  # Filter by selected delivery methods
            }

        # Define a function to create a query for results that don't have geometry (null geometry)
        def create_null_geo_query(category_response, deliverymethod_response):
            return {
                "geometry": None,
                "filter_tags": {"$in": category_response},
                "delivery_method": {"$in": deliverymethod_response}
            }

        # Perform the MongoDB queries for results that match the geo query and the null geo query
        geo_query = create_geo_query(category_response, deliverymethod_response)
        null_geo_query = create_null_geo_query(category_response, deliverymethod_response)

        geo_results = list(collection.find(geo_query))  # Get results within geographic bounds
        null_geo_results = list(collection.find(null_geo_query))  # Get results without geometry

        # Combine both result sets
        results_list = geo_results + null_geo_results

        # Convert the results to JSON format
        results_json = json.dumps(results_list, default=str)

        # Render the results on the template
        return render_template(
            'index.html',
            category=category_mapping.keys(),
            unique_delivery_method=unique_delivery_method,
            results=results_list,
            category_response=request.form['category'],  # Show original category selection in UI
            results_json=results_json,
            zipcode=zip_code,
            distance=distance_miles
        )

    # If the request method is GET, render the initial form
    else:
        return render_template(
            'index.html',
            category=category_mapping.keys(),
            unique_delivery_method=unique_delivery_method
        )

# Run the Flask app in debug mode
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
