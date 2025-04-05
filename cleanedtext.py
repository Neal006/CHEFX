import re

def clean_dynamic_text(text):
    """
    Clean and format text while preserving proper spacing and removing markdown symbols.
    """
    # Remove [object Object] if present
    text = re.sub(r'\[object Object\]', '', text)
    
    # Remove HTML tags but preserve line breaks
    text = re.sub(r'<[^>]+>', '', text)
    
    # Normalize line endings
    text = text.replace('\r\n', '\n')
    
    # Handle section headers with proper formatting
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    
    # Clean up list markers and add proper HTML formatting
    text = re.sub(r'^\* \*\*(.+?):\*\* (.+)$', r'<strong>\1:</strong> \2', text, flags=re.MULTILINE)  # Handle bold items with colons
    text = re.sub(r'^\* (.+)$', r'• \1', text, flags=re.MULTILINE)  # Convert * to •
    text = re.sub(r'^- (.+)$', r'• \1', text, flags=re.MULTILINE)  # Convert - to •
    text = re.sub(r'^(\d+)\. (.+)$', r'\1. \2', text, flags=re.MULTILINE)  # Clean numbered lists
    
    # Remove markdown bold markers while preserving the text
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    
    # Remove square brackets from placeholders
    text = re.sub(r'\[(.*?)\]', r'\1', text)
    
    # Clean up extra whitespace while preserving intentional line breaks
    lines = text.split('\n')
    cleaned_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        
        if line:
            # Handle section headers (already converted to HTML)
            if line.startswith('<h'):
                if cleaned_lines:
                    cleaned_lines.append('')  # Add space before section
                cleaned_lines.append(line)
                cleaned_lines.append('')  # Add space after section
                in_list = False
            # Handle list items
            elif line.startswith('•') or re.match(r'^\d+\.', line):
                if not in_list and cleaned_lines:
                    cleaned_lines.append('')  # Add space before list starts
                cleaned_lines.append(line)
                in_list = True
            # Handle normal text
            else:
                if in_list:
                    cleaned_lines.append('')  # Add space after list ends
                cleaned_lines.append(line)
                in_list = False
        elif in_list:
            in_list = False
            cleaned_lines.append('')
    
    # Join lines back together
    text = '\n'.join(cleaned_lines)
    
    # Remove multiple consecutive blank lines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Ensure proper spacing after punctuation
    text = re.sub(r'([,.!?:;])\s*', r'\1 ', text)
    
    # Final cleanup
    text = text.strip()
    
    return text