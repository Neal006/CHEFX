import os
import re
import json
import argparse
import PyPDF2
import spacy
from dotenv import load_dotenv
from aimeasurement import DynamicKitchenConverter

# Load environment variables
load_dotenv()

# Get API key from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY. Please check your .env file.")

# Initialize the measurement converter
converter = DynamicKitchenConverter(GEMINI_API_KEY)

# Load spaCy NLP model for ingredient and measurement extraction
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model...")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Common vague measurement patterns
VAGUE_MEASUREMENTS = [
    r"a handful", r"a pinch", r"a dash", r"a sprinkle", r"a touch", 
    r"a bit", r"a lot", r"some", r"a few", r"a little", r"a splash",
    r"a dollop", r"a drizzle", r"a squeeze", r"a smidge", r"to taste",
    r"a scoop", r"several", r"generous", r"heaping", r"rounded",
    r"scant", r"a glass", r"a cup", r"a bowl", r"a plate"
]

# Compile regex pattern for vague measurements
VAGUE_PATTERN = re.compile(
    r'(' + '|'.join(VAGUE_MEASUREMENTS) + r')\s+(?:of\s+)?([a-zA-Z\s]+)'
)

def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file."""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def parse_recipe_ingredients(text):
    """
    Parse recipe text to extract ingredients and measurements.
    Returns a list of tuples: (measurement, ingredient)
    """
    ingredients = []
    
    # Extract using regex for vague measurements
    vague_matches = VAGUE_PATTERN.findall(text)
    for measurement, ingredient in vague_matches:
        ingredients.append((measurement.strip(), ingredient.strip()))
    
    # Use spaCy for additional extraction
    doc = nlp(text)
    
    # Look for quantities and ingredients in parsed text
    for sent in doc.sents:
        # Skip very short sentences
        if len(sent.text.split()) < 3:
            continue
            
        # Check if sentence might be an ingredient line
        if any(token.like_num for token in sent) or any(token.is_digit for token in sent):
            # Extract potential quantities and ingredients
            quantity = None
            ingredient = []
            for token in sent:
                if token.like_num or token.is_digit or token.text in ["a", "an", "some", "few"]:
                    if not quantity:
                        quantity = token.text
                elif token.pos_ in ["NOUN", "PROPN"] and not any(word in token.text.lower() for word in ["bowl", "pan", "oven", "minutes", "seconds", "hour"]):
                    ingredient.append(token.text)
            
            if quantity and ingredient:
                # Join the ingredients
                full_ingredient = " ".join(ingredient)
                
                # Check if this isn't already in our vague matches
                if not any(ing == full_ingredient for _, ing in vague_matches):
                    ingredients.append((quantity, full_ingredient))
    
    return ingredients

def convert_recipe_measurements(pdf_path, output_path=None):
    """
    Process a recipe PDF, detect vague measurements, and convert them.
    Saves results to a JSON file if output_path is provided.
    """
    # Extract text from PDF
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print(f"Could not extract text from {pdf_path}")
        return None
    
    # Parse ingredients with measurements
    ingredient_measurements = parse_recipe_ingredients(text)
    if not ingredient_measurements:
        print(f"No ingredient measurements found in {pdf_path}")
        return None
    
    # Convert vague measurements to precise measurements
    conversions = []
    for measurement, ingredient in ingredient_measurements:
        try:
            print(f"Converting: {measurement} of {ingredient}")
            result = converter.convert_measurement(measurement, ingredient)
            conversions.append(result)
        except Exception as e:
            print(f"Error converting {measurement} of {ingredient}: {e}")
    
    # Create the results dictionary
    recipe_name = os.path.basename(pdf_path).replace('.pdf', '')
    results = {
        "recipe_name": recipe_name,
        "source_file": pdf_path,
        "conversions": conversions
    }
    
    # Save results to JSON file if output path is provided
    if output_path:
        if not output_path.endswith('.json'):
            output_path += '.json'
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"Conversion results saved to {output_path}")
    
    return results

def display_conversion_results(results):
    """Pretty print the conversion results."""
    if not results or not results.get("conversions"):
        print("No conversions to display.")
        return
    
    print("\n===== MEASUREMENT CONVERSION RESULTS =====")
    print(f"Recipe: {results['recipe_name']}")
    print(f"Source: {results['source_file']}")
    print("\nConversions:")
    
    for i, conversion in enumerate(results["conversions"], 1):
        print(f"\n{i}. {conversion['original']}")
        print(f"   Interpretation: {conversion['interpretation']}")
        print(f"   Weight: {conversion['grams']}g / {conversion['ounces']}oz")
        print(f"   Volume: {conversion['milliliters']}ml / {conversion['cups']} cups / "
              f"{conversion['tablespoons']} tbsp / {conversion['teaspoons']} tsp")
        print(f"   Ingredient: {conversion['ingredient_info']['category']} "
              f"({conversion['ingredient_info']['state']}, "
              f"density: {conversion['ingredient_info']['density']} g/ml)")

def replace_measurements_in_text(text, results):
    """Replace vague measurements in text with precise measurements."""
    if not results or not results.get("conversions"):
        return text
    
    # Sort conversions by length of original string (longer first)
    # This helps prevent partial replacements
    sorted_conversions = sorted(
        results["conversions"], 
        key=lambda x: len(x["original"]), 
        reverse=True
    )
    
    for conversion in sorted_conversions:
        original = conversion["original"]
        
        # Create replacement text with both weight and volume
        replacement = f"{original} ({conversion['grams']}g / {conversion['tablespoons']} tbsp)"
        
        # Replace the original measurement with the precise one
        text = text.replace(original, replacement)
    
    return text

def main():
    parser = argparse.ArgumentParser(
        description="Convert vague measurements in recipe PDFs to precise measurements."
    )
    parser.add_argument("pdf_path", help="Path to the recipe PDF file")
    parser.add_argument(
        "-o", "--output", 
        help="Output JSON file path for conversion results (optional)"
    )
    parser.add_argument(
        "--convert-text", action="store_true",
        help="Generate a new text file with converted measurements"
    )
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: File {args.pdf_path} does not exist.")
        return
    
    print(f"Processing {args.pdf_path}...")
    results = convert_recipe_measurements(args.pdf_path, args.output)
    
    if results:
        display_conversion_results(results)
        
        # If requested, create a new text file with converted measurements
        if args.convert_text:
            text = extract_text_from_pdf(args.pdf_path)
            converted_text = replace_measurements_in_text(text, results)
            
            text_output = args.pdf_path.replace('.pdf', '_converted.txt')
            with open(text_output, 'w', encoding='utf-8') as f:
                f.write(converted_text)
            print(f"\nConverted text saved to {text_output}")

if __name__ == "__main__":
    main() 