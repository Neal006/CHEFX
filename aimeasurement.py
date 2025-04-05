import re, os, json, requests
import google.generativeai as genai
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class DynamicKitchenConverter:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # Base units for conversion
        self.base_units = {
            'milliliter': 1.0,
            'cup': 236.588,
            'tablespoon': 14.787,
            'teaspoon': 4.929
        }

        # Improved fallback densities for accuracy
        self.fallback_densities = {
            "water": 1.0, "milk": 1.03, "honey": 1.42, "oil": 0.92, "sugar": 0.85,
            "flour": 0.59, "butter": 0.92, "salt": 1.2, "rice": 0.85, "yogurt": 1.03
        }

        # Keywords for liquid vs solid classification
        self.liquid_keywords = {"juice", "oil", "syrup", "milk", "water", "soup", "broth", "beer", "wine", "honey"}
        self.solid_keywords = {"flour", "sugar", "grain", "bread", "cheese", "rice", "nuts", "beans", "meat"}

    def get_ingredient_density(self, ingredient: str) -> Dict[str, Any]:
        search_term = ingredient.lower().strip()
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={search_term}&json=1"

        try:
            response = requests.get(url, timeout=5)  # Set timeout
            response.raise_for_status()
            data = response.json()

            if "products" in data and data["products"]:
                product = data["products"][0]

                # Extract category
                categories = product.get("categories_tags", [])
                primary_category = next((c.replace("en:", "").title() for c in categories
                                         if "sweetener" in c or "syrup" in c), categories[0].replace("en:", "").title()) if categories else "General Ingredient"

                # Determine state (liquid/solid)
                ingredient_name = ingredient.lower()
                state = "liquid" if any(word in ingredient_name for word in self.liquid_keywords) else "solid"

                # Improved density calculation
                density = self.fallback_densities.get(ingredient_name, 1.0)
                if "nutriments" in product:
                    nutrients = product["nutriments"]
                    if "energy-kcal_100g" in nutrients:
                        density = max(0.1, min(2.0, nutrients["energy-kcal_100g"] / 400))
                    elif "carbohydrates_100g" in nutrients:
                        density = max(0.5, min(1.8, nutrients["carbohydrates_100g"] / 100))

                return {
                    "density": round(density, 2),
                    "state": state,
                    "category": primary_category
                }

        except (requests.RequestException, KeyError) as e:
            print(f"Error fetching data for {ingredient}: {e}")

        return {
            "density": self.fallback_densities.get(search_term, 1.0),
            "state": "unknown",
            "category": "General Ingredient"
        }

    def interpret_vague_measurement(self, measurement_str: str) -> Dict[str, float]:
        """Convert vague measurement to milliliters using Gemini AI."""
        prompt = f"""
        Convert this kitchen measurement: "{measurement_str}" into milliliters (ml).
        Return JSON format: {{"ml": 240.0, "description": "A standard drinking glass is typically 240ml"}}
        """

        try:
            response = self.model.generate_content(prompt)
            json_response = response.text.strip()
            json_response = re.sub(r"```json\n|\n```", "", json_response)

            result = json.loads(json_response)
            return result
        except json.JSONDecodeError:
            raise ValueError(f"Could not interpret measurement: Invalid JSON format in response: {json_response}")
        except Exception as e:
            raise ValueError(f"Could not interpret measurement: {e}")

    def validate_with_gemini(self, conversion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Pass final output to Gemini AI for validation and correction."""
        prompt = f"""
        Here is a kitchen measurement conversion result:
        {json.dumps(conversion_data, indent=4)}

        Check if all values (weight, volume, density, state, category) are accurate.
        If incorrect, return ONLY a corrected JSON in this format:
        ```json
        {{
            "original": "...",
            "interpretation": "...",
            "ingredient_info": {{
                "state": "...",
                "category": "...",
                "density": ...
            }},
            "milliliters": ...,
            "grams": ...,
            "ounces": ...,
            "cups": ...,
            "tablespoons": ...,
            "teaspoons": ...
        }}
        ```
        Do not include explanations or extra text.
        """

        try:
            response = self.model.generate_content(prompt)
            json_response = response.text.strip()

            # Extract JSON portion correctly
            json_match = re.search(r"```json\n(.*?)\n```", json_response, re.DOTALL)
            if json_match:
                json_response = json_match.group(1)

            corrected_data = json.loads(json_response)
            return corrected_data
        except (json.JSONDecodeError, AttributeError):
            print(f"Gemini validation failed: Could not extract JSON. Using original data.")
            return conversion_data  
        except Exception as e:
            print(f"Gemini validation failed: {e}")
            return conversion_data  


    def convert_measurement(self, measurement_str: str, ingredient: str) -> Dict[str, Any]:
        """Convert measurement and validate results using Open Food Facts and Gemini AI."""
        volume_info = self.interpret_vague_measurement(measurement_str)
        ml = volume_info['ml']

        ingredient_info = self.get_ingredient_density(ingredient)
        density = ingredient_info['density']
        grams = ml * density

        conversion_result = {
            'original': f"{measurement_str} of {ingredient}",
            'interpretation': volume_info['description'],
            'ingredient_info': {
                'state': ingredient_info['state'],
                'category': ingredient_info['category'],
                'density': density
            },
            'milliliters': round(ml, 1),
            'grams': round(grams, 1),
            'ounces': round(grams / 28.35, 2),
            'cups': round(ml / self.base_units['cup'], 2),
            'tablespoons': round(ml / self.base_units['tablespoon'], 1),
            'teaspoons': round(ml / self.base_units['teaspoon'], 1)
        }

        # Validate conversion with Gemini AI
        validated_data = self.validate_with_gemini(conversion_result)

        return validated_data  # Return the final, corrected result

# Testing Example
if __name__ == "__main__":
    api_key = os.getenv("GEMINI_API_KEY")
    converter = DynamicKitchenConverter(api_key)

    test_measurement = "4 tbsp"
    test_ingredient = "honey"

    result = converter.convert_measurement(test_measurement, test_ingredient)
    print("\n=== Final Conversion Result ===")
    print(json.dumps(result, indent=4))
