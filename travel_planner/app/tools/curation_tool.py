import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

RECOMMENDATIONS = {
    "paris": {
        "dining": [
            {"name": "Le Bistrot Paul Bert", "cuisine": "Classic French Bistro", "interests": ["food", "fine dining", "culture"], "tier": "Moderate"},
            {"name": "L'As du Fallafel", "cuisine": "Middle Eastern / Falafel", "interests": ["food", "budget", "street food"], "tier": "Economy"},
            {"name": "L'Ambroisie", "cuisine": "3-Star Michelin Haute Cuisine", "interests": ["fine dining", "luxury"], "tier": "Luxury"},
            {"name": "Angelina Paris", "cuisine": "Pastry & Hot Chocolate Shop", "interests": ["family", "food", "kids"], "tier": "Moderate"},
            {"name": "Le Comptoir du Relais", "cuisine": "Gourmet Bistro", "interests": ["food", "romance"], "tier": "Moderate"}
        ],
        "attractions": [
            {"name": "Eiffel Tower", "type": "Landmark", "interests": ["sightseeing", "romance", "first-time"], "description": "Iconic iron tower with sweeping views of the city."},
            {"name": "Louvre Museum", "type": "Museum / Art", "interests": ["art", "history", "culture"], "description": "World's largest art museum housing the Mona Lisa."},
            {"name": "Musée d'Orsay", "type": "Museum / Art", "interests": ["art", "culture"], "description": "Fabulous impressionist art collection in a grand former railway station."},
            {"name": "Disneyland Paris", "type": "Theme Park", "interests": ["family", "kids", "adventure"], "description": "Magic kingdom for families and children."},
            {"name": "Palace of Versailles", "type": "History / Architecture", "interests": ["history", "architecture", "luxury"], "description": "Royal chateau with stunning gold hall and gardens."}
        ]
    },
    "tokyo": {
        "dining": [
            {"name": "Sukiyabashi Jiro", "cuisine": "World-Class Sushi", "interests": ["food", "fine dining", "luxury"], "tier": "Luxury"},
            {"name": "Ichiran Ramen", "cuisine": "Tonkotsu Ramen", "interests": ["food", "budget", "quick"], "tier": "Economy"},
            {"name": "Robot Restaurant / Izakaya", "cuisine": "Themed Izakaya Dining", "interests": ["adventure", "nightlife", "entertainment"], "tier": "Moderate"},
            {"name": "Rokurinsha", "cuisine": "Tsukemen (Dipping Ramen)", "interests": ["food", "culture"], "tier": "Economy"},
            {"name": "New York Grill at Park Hyatt", "cuisine": "Steak & Jazz Club", "interests": ["fine dining", "romance", "views"], "tier": "Luxury"}
        ],
        "attractions": [
            {"name": "Shibuya Crossing", "type": "Urban Walk", "interests": ["sightseeing", "first-time", "culture"], "description": "The world's busiest pedestrian intersection."},
            {"name": "Senso-ji Temple", "type": "Buddhist Temple", "interests": ["history", "culture", "sightseeing"], "description": "Tokyo's oldest and most significant temple in Asakusa."},
            {"name": "teamLab Planets", "type": "Digital Art Museum", "interests": ["art", "kids", "family", "adventure"], "description": "Immersive digital art galleries walked through barefoot."},
            {"name": "Meiji Shrine", "type": "Shinto Shrine", "interests": ["history", "nature", "culture"], "description": "Serene shrine surrounded by forest in the middle of Shibuya."},
            {"name": "Ghibli Museum", "type": "Animation Museum", "interests": ["family", "art", "kids"], "description": "Charming museum showcasing Studio Ghibli's work."}
        ]
    }
}

def curate_recommendations(destination: str, interests: List[str], budget_range: str) -> Dict[str, Any]:
    dest_key = destination.lower().strip()
    matched_city = None
    for k in RECOMMENDATIONS:
        if k in dest_key:
            matched_city = k
            break
            
    interests_lower = [i.lower() for i in interests]
    budget_lower = budget_range.lower()
    
    if matched_city:
        city_data = RECOMMENDATIONS[matched_city]
        dining_list = []
        for d in city_data["dining"]:
            match_score = sum(1 for i in d["interests"] if i in interests_lower)
            if d["tier"].lower() == budget_lower:
                match_score += 2
            dining_list.append((d, match_score))
        dining_list.sort(key=lambda x: x[1], reverse=True)
        curated_dining = [item[0] for item in dining_list[:3]]
        
        attraction_list = []
        for a in city_data["attractions"]:
            match_score = sum(1 for i in a["interests"] if i in interests_lower)
            attraction_list.append((a, match_score))
        attraction_list.sort(key=lambda x: x[1], reverse=True)
        curated_attractions = [item[0] for item in attraction_list[:3]]
        
        return {
            "dining": curated_dining,
            "attractions": curated_attractions
        }
    else:
        return {
            "dining": [
                {"name": "The Local Diner", "cuisine": "Traditional Local Eats", "interests": ["food", "culture"], "tier": "Economy"},
                {"name": "The Grand Palace Restaurant", "cuisine": "Gourmet Fine Dining", "interests": ["fine dining", "luxury"], "tier": "Luxury"},
                {"name": "Central Park Cafe", "cuisine": "Cafe & Bistro", "interests": ["family", "nature"], "tier": "Moderate"}
            ],
            "attractions": [
                {"name": f"{destination.title()} Central Square", "type": "Plaza", "interests": ["sightseeing", "first-time"], "description": "The central hub of the town featuring street artists and architecture."},
                {"name": f"{destination.title()} Museum of Art", "type": "Museum", "interests": ["art", "history", "culture"], "description": "A collection of contemporary and historical local artwork."},
                {"name": f"{destination.title()} National Garden", "type": "Park", "interests": ["nature", "family", "kids"], "description": "Beautiful walking trails and botanical gardens."}
            ]
        }
