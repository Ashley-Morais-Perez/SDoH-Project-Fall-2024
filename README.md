# SDoH-Project-Fall-2024


This repository contains the deliverables for our HHA 502/504 Fall Project.




## Systems Architecture 

![image](https://github.com/user-attachments/assets/6cb916dc-a22e-466e-90e8-9992a780d6b6)

The Systems Architecture explains how the dashboard provides resources based on a user’s input. Here's how it works:

1) User Input: The user enters a zip code and a radius (e.g., distance from resource on Long Island) into the dashboard.
2) Processing:
   - The Flask API Server sends the zip code to the Google Maps API to get location data.
   - It queries MongoDB for resources within the specified area.
3) Results: The server combines the location data and resources, then sends the results back to the dashboard.
4) Display: The user sees a list of resources and an interactive map on the dashboard.
