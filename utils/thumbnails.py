from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os

def generate_thumbnail(client, concept, video_title, platform="YouTube"):
    """Generate a thumbnail image based on the concept and video title."""

    try:
        # Choose thumbnail size based on platform
        if platform.lower() == "youtube":
            aspect_ratio = "16:9"
            size = "1792x1024"
        elif platform.lower() == "instagram":
            aspect_ratio = "1:1"
            size = "1024x1024"
        elif platform.lower() == "linkedin":
            aspect_ratio = "1.91:1"
            size = "1792x1024"
        else:
            aspect_ratio = "16:9"
            size = "1792x1024"

        # Extract concept elements
        text_overlay = concept.get('text_overlay', '')
        focal_point = concept.get('focal_point', '')
        tone = concept.get('tone', '')
        concept_desc = concept.get('concept', '')
        colors = concept.get('colors', ['#FFFFFF', '#000000'])

        main_color = colors[0] if colors else '#FFFFFF'

        # Create prompt for DALL·E 3
        prompt = f"""
        Create a professional {platform} thumbnail with the following:
        - Clear {aspect_ratio} format suitable for {platform}
        - Main focus: {focal_point}
        - Emotional tone: {tone}
        - Bold, clear text overlay reading: "{text_overlay}"
        - Text should be highly legible, possibly in color {main_color} with a contrasting outline
        - Concept: {concept_desc}
        - Related to: {video_title}
        - Eye-catching, high-contrast and high-quality design
        - Text should be integrated with visual elements in a visually appealing way
        """

        # Generate image from DALL·E 3
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt.strip(),
            size=size,
            quality="standard",
            n=1
        )

        image_url = response.data[0].url
        return image_url

    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None


def create_gradient_background(concept, width=1280, height=720):
    """Create a gradeint background using the colors from the concept."""
    colors = concept.get('colors', ['#3366CC','#FFFFFF','#FF5555'])
    
    if len(colors)>2:
        colors.append('#FFFFFF')
    
    try:
        color1 = hex_to_rgb(colors[0])
        color2 = hex_to_rgb(colors[1] if len(colors)> 1 else '#FFFFFF')
    except:
        #Fallback to default colours if parsing fails
        color1 = (51, 102, 244)  # 3366CC
        color2 = (255, 255, 255)  #FFFFFF
        
    #Create a new image
    img = Image.new('RGB',(width, height),color=color1)
    draw = ImageDraw.Draw(img)
    
    for y in range(height):
        ratio = y/height
        r = int(color1[0]*(1-ratio)+color2[0]*ratio)
        g = int(color1[1]*(1-ratio)+color2[1]*ratio)
        b = int(color1[2]*(1-ratio)+color2[2]*ratio)
        
        draw.line([(0,y),(width,y)],fill=(r,g,b))
    
    tone = concept.get('tone','').lower()
    if 'professional' in tone or 'educational' in tone:
        add_professional_pattern(img,draw)
    elif 'energetic' in tone or 'exciting' in tone:
        add_energetic_pattern(img,draw)
    elif 'emotional' in tone or 'dramatic' in tone:
        add_dramatic_pattern(img,draw)
        
    return img

def add_text_with_outline(img,draw,concept):
    """Add outlined overlay text to the image."""
    text = concept.get('text_overlay', '')
    color = concept.get('colors', ['#FFFFFF'])[0]
    font_size = 64  # You can make this dynamic based on image size
    
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    text_width, text_height = draw.textsize(text, font=font)
    x = (img.width - text_width) // 2
    y = (img.height - text_height) // 2

    # Draw outline
    outline_color = (0, 0, 0)  # black outline
    for dx in [-2, -1, 0, 1, 2]:
        for dy in [-2, -1, 0, 1, 2]:
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

    # Draw main text
    draw.text((x, y), text, font=font, fill=color)
    

def add_watermark(img,draw):
    """Add a watermark to the image."""
    watermark_text= "Video SEO Optimizer"
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    draw.text(
        (img.width-220,img.height-30),
        watermark_text,
        fill=(255,255,255,15),
        font=font
    )

def add_professional_pattern(img,draw):
    """Add a subtle professional pattern to the background"""
    width, height = img.size
    for i in range(0,width,40):
        draw.line([(i,0),(i,height)],fill=(255,255,255,10))
    for i in range(0,height,40):
        draw.line([(i,0),(width,i)],fill=(255,255,255,10))

def add_energetic_pattern(img,draw):
    """Add an energetic pattern to the image"""
    width , height = img.size
     
    for i in range(-height, width+height, 60):
        draw.line([(i,0),(i+height,height)],fill=(255,255,255,15))
        draw.line([(i,height),(i+height,0)],fill=(255,255,255,15))

def add_dramatic_pattern(img,draw):
    """Add a dramatic pattern to the image."""
    width, height = img.size
    center_x, center_y = width//2,height//2
    
    for radius in range(50, max(width,height),100):
        draw.arc(
            [(center_x - radius, center_y - radius),
             (center_x + radius, center_y + radius)],
            0, 360, fill=(255,255,255,20)
        )
        
        
def hex_to_rgb(hex_color):
    """Convert a hex color to RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2],16) for i in (0,2,4))


def create_thumbnail_preview(concept,video_title,base_image_url=None):
    """Create a thumbnail preview for the video based on the concept."""
    if base_image_url:
        try:
            response = requests.get(base_image_url)
            img = Image.open(BytesIO(response.content))
            img = img.resize((1280,720))
        except Exception:
            img = create_gradient_background(concept)
    else:
        img = create_gradient_background(concept)
        
    draw = ImageDraw.Draw(img)
    if concept.get('text_overlay'):
        add_text_with_outline(img,draw,concept)
        
    add_watermark(img,draw)
    
    return img