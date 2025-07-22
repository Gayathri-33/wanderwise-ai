from flask import Flask, render_template, request, jsonify, send_file
import json
import random
from datetime import datetime, timedelta
import io
import uuid
import os

# Try to import reportlab for PDF generation, handle gracefully if not available
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not installed. PDF export will be disabled.")
    print("To enable PDF export, install reportlab: pip install reportlab==4.0.4")

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Mock AI Travel Data (In real app, this would be connected to OpenAI/Gemini API)
DESTINATIONS_DATA = {
    'paris': {
        'name': 'Paris, France',
        'attractions': ['Eiffel Tower', 'Louvre Museum', 'Notre-Dame Cathedral', 'Champs-Élysées', 'Arc de Triomphe', 'Sacré-Cœur', 'Versailles Palace', 'Seine River Cruise'],
        'restaurants': ['Le Comptoir du Relais', 'L\'As du Fallafel', 'Breizh Café', 'Du Pain et des Idées', 'Le Mary Celeste', 'Bistrot Paul Bert'],
        'hotels': ['Hotel des Grands Boulevards', 'Le Bristol Paris', 'Hotel Malte Opera', 'Generator Paris'],
        'activities': ['Walking tour of Montmartre', 'Seine river cruise', 'Wine tasting', 'Cooking class', 'Art workshop'],
        'daily_budget': {'budget': 80, 'mid-range': 150, 'luxury': 300}
    },
    'tokyo': {
        'name': 'Tokyo, Japan',
        'attractions': ['Senso-ji Temple', 'Tokyo Skytree', 'Shibuya Crossing', 'Meiji Shrine', 'Tsukiji Fish Market', 'Imperial Palace', 'Harajuku'],
        'restaurants': ['Sukiyabashi Jiro', 'Ramen Yashichi', 'Kozasa', 'Nabezo', 'Ginza Kyoboshi'],
        'hotels': ['Park Hyatt Tokyo', 'Capsule Hotel', 'Ryokan Tokyo', 'Business Hotel'],
        'activities': ['Sushi making class', 'Temple visit', 'Karaoke', 'Cherry blossom viewing', 'Traditional tea ceremony'],
        'daily_budget': {'budget': 60, 'mid-range': 120, 'luxury': 250}
    },
    'new york': {
        'name': 'New York City, USA',
        'attractions': ['Statue of Liberty', 'Central Park', 'Times Square', 'Brooklyn Bridge', 'Empire State Building', '9/11 Memorial', 'High Line'],
        'restaurants': ['Joe\'s Pizza', 'Katz\'s Delicatessen', 'The Halal Guys', 'Shake Shack', 'Peter Luger'],
        'hotels': ['The Plaza', 'Pod Hotels', 'YMCA', 'The High Line Hotel'],
        'activities': ['Broadway show', 'Museum visits', 'Food tours', 'Walking tours', 'Rooftop bars'],
        'daily_budget': {'budget': 100, 'mid-range': 200, 'luxury': 400}
    },
    'london': {
        'name': 'London, UK',
        'attractions': ['Big Ben', 'Tower of London', 'British Museum', 'London Eye', 'Buckingham Palace', 'Westminster Abbey', 'Tower Bridge'],
        'restaurants': ['Dishoom', 'Borough Market', 'The Ivy', 'Fish and Chips shops', 'Sketch'],
        'hotels': ['The Savoy', 'Premier Inn', 'YHA London', 'The Shard Hotel'],
        'activities': ['Thames cruise', 'Pub crawl', 'West End show', 'Royal tours', 'Market visits'],
        'daily_budget': {'budget': 70, 'mid-range': 140, 'luxury': 280}
    }
}

TRAVEL_INTERESTS = {
    'adventure': ['hiking', 'bungee jumping', 'rock climbing', 'zip lining', 'white water rafting'],
    'culture': ['museums', 'art galleries', 'historical sites', 'local festivals', 'architecture tours'],
    'food': ['food tours', 'cooking classes', 'local markets', 'wine tasting', 'street food'],
    'history': ['historical sites', 'guided tours', 'museums', 'archaeological sites', 'heritage walks'],
    'nightlife': ['bars', 'clubs', 'live music', 'rooftop lounges', 'night markets'],
    'nature': ['parks', 'gardens', 'beaches', 'hiking trails', 'wildlife viewing'],
    'shopping': ['local markets', 'shopping districts', 'boutiques', 'souvenir shops', 'malls']
}

# Store generated itineraries (in production, use database)
generated_itineraries = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-itinerary', methods=['POST'])
def generate_itinerary():
    try:
        data = request.get_json()
        
        # Extract form data
        destination = data.get('destination', '').lower()
        days = int(data.get('days', 3))
        budget_type = data.get('budget', 'mid-range')
        interests = data.get('interests', [])
        travel_style = data.get('travelStyle', 'solo')
        start_date = data.get('startDate', '')
        
        # Generate AI-powered itinerary
        itinerary = generate_ai_itinerary(destination, days, budget_type, interests, travel_style, start_date)
        
        # Store itinerary with unique ID
        itinerary_id = str(uuid.uuid4())
        generated_itineraries[itinerary_id] = itinerary
        itinerary['id'] = itinerary_id
        
        return jsonify({
            'success': True,
            'itinerary': itinerary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

def generate_ai_itinerary(destination, days, budget_type, interests, travel_style, start_date):
    """Generate AI-powered travel itinerary"""
    
    # Get destination data (fallback to generic if not found)
    dest_key = destination.replace(' ', '').replace(',', '').lower()
    if dest_key not in DESTINATIONS_DATA:
        # Find partial match
        dest_key = next((k for k in DESTINATIONS_DATA.keys() if k in dest_key or dest_key in k), 'paris')
    
    dest_data = DESTINATIONS_DATA[dest_key]
    daily_budget = dest_data['daily_budget'][budget_type]
    
    # Generate day-by-day itinerary
    itinerary_days = []
    
    # Parse start date
    try:
        current_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else datetime.now()
    except:
        current_date = datetime.now()
    
    for day in range(days):
        day_date = current_date + timedelta(days=day)
        
        # Select attractions based on interests and day
        day_attractions = select_personalized_attractions(dest_data, interests, day, days)
        day_restaurants = random.sample(dest_data['restaurants'], min(2, len(dest_data['restaurants'])))
        day_activities = select_personalized_activities(dest_data, interests, day)
        
        # Calculate budget breakdown
        budget_breakdown = calculate_daily_budget(daily_budget, travel_style)
        
        day_plan = {
            'day': day + 1,
            'date': day_date.strftime('%A, %B %d, %Y'),
            'attractions': day_attractions,
            'restaurants': {
                'breakfast': day_restaurants[0] if len(day_restaurants) > 0 else 'Local café',
                'lunch': day_restaurants[1] if len(day_restaurants) > 1 else 'Street food',
                'dinner': random.choice(dest_data['restaurants'])
            },
            'activities': day_activities,
            'budget': budget_breakdown,
            'tips': generate_daily_tips(day, interests, travel_style)
        }
        
        itinerary_days.append(day_plan)
    
    # Calculate total budget
    total_budget = calculate_total_budget(daily_budget, days, travel_style)
    
    # Generate hotel suggestions
    hotel_suggestions = select_hotels(dest_data, budget_type, travel_style)
    
    itinerary = {
        'destination': dest_data['name'],
        'duration': f"{days} days",
        'budget_type': budget_type.title(),
        'travel_style': travel_style.title(),
        'interests': interests,
        'total_budget': total_budget,
        'daily_budget': daily_budget,
        'hotels': hotel_suggestions,
        'days': itinerary_days,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'travel_tips': generate_travel_tips(dest_data['name'], interests, travel_style)
    }
    
    return itinerary

def select_personalized_attractions(dest_data, interests, day, total_days):
    """Select attractions based on user interests"""
    attractions = dest_data['attractions'].copy()
    
    # Prioritize based on interests
    if 'culture' in interests or 'history' in interests:
        cultural_attractions = [a for a in attractions if any(word in a.lower() for word in ['museum', 'cathedral', 'palace', 'temple', 'shrine'])]
        attractions = cultural_attractions + [a for a in attractions if a not in cultural_attractions]
    
    if 'adventure' in interests:
        adventure_attractions = [a for a in attractions if any(word in a.lower() for word in ['tower', 'bridge', 'cruise', 'skytree'])]
        attractions = adventure_attractions + [a for a in attractions if a not in adventure_attractions]
    
    # Select 2-3 attractions per day
    attractions_per_day = min(3, len(attractions) // total_days + 1)
    start_idx = day * attractions_per_day
    end_idx = start_idx + attractions_per_day
    
    return attractions[start_idx:end_idx] if end_idx <= len(attractions) else attractions[start_idx:]

def select_personalized_activities(dest_data, interests, day):
    """Select activities based on interests"""
    all_activities = dest_data['activities'].copy()
    
    # Add interest-specific activities
    for interest in interests:
        if interest in TRAVEL_INTERESTS:
            all_activities.extend(TRAVEL_INTERESTS[interest][:2])
    
    # Remove duplicates and select random activities
    unique_activities = list(set(all_activities))
    return random.sample(unique_activities, min(2, len(unique_activities)))

def calculate_daily_budget(base_budget, travel_style):
    """Calculate detailed daily budget breakdown"""
    
    # Adjust base budget based on travel style
    multiplier = {
        'backpacker': 0.7,
        'solo': 1.0,
        'couple': 1.3,
        'family': 1.8,
        'luxury': 2.0
    }.get(travel_style, 1.0)
    
    adjusted_budget = int(base_budget * multiplier)
    
    return {
        'accommodation': int(adjusted_budget * 0.35),
        'food': int(adjusted_budget * 0.30),
        'attractions': int(adjusted_budget * 0.20),
        'transport': int(adjusted_budget * 0.10),
        'miscellaneous': int(adjusted_budget * 0.05),
        'total': adjusted_budget
    }

def calculate_total_budget(daily_budget, days, travel_style):
    """Calculate total trip budget"""
    daily_breakdown = calculate_daily_budget(daily_budget, travel_style)
    total = daily_breakdown['total'] * days
    
    return {
        'accommodation': daily_breakdown['accommodation'] * days,
        'food': daily_breakdown['food'] * days,
        'attractions': daily_breakdown['attractions'] * days,
        'transport': daily_breakdown['transport'] * days + 200,  # Added flight/transport
        'miscellaneous': daily_breakdown['miscellaneous'] * days,
        'total': total + 200
    }

def select_hotels(dest_data, budget_type, travel_style):
    """Select appropriate hotels based on budget and style"""
    hotels = dest_data['hotels'].copy()
    
    # Filter based on budget and travel style
    if budget_type == 'budget' or travel_style == 'backpacker':
        return [h for h in hotels if any(word in h.lower() for word in ['hostel', 'ymca', 'capsule', 'budget', 'generator'])][:2]
    elif budget_type == 'luxury':
        return [h for h in hotels if any(word in h.lower() for word in ['plaza', 'hyatt', 'bristol', 'savoy', 'luxury'])][:2]
    else:
        return hotels[:3]

def generate_daily_tips(day, interests, travel_style):
    """Generate personalized daily tips"""
    tips = []
    
    if day == 0:
        tips.append("Start early to beat the crowds at major attractions")
        if 'food' in interests:
            tips.append("Try local breakfast specialties to start your culinary journey")
    
    if 'culture' in interests:
        tips.append("Book museum tickets online to skip the lines")
    
    if 'adventure' in interests:
        tips.append("Wear comfortable walking shoes for today's activities")
    
    if travel_style == 'family':
        tips.append("Plan rest breaks between activities for children")
    
    return tips[:2]  # Limit to 2 tips per day

def generate_travel_tips(destination, interests, travel_style):
    """Generate general travel tips for the destination"""
    tips = [
        "Download offline maps before exploring",
        "Learn basic local phrases for better interactions",
        "Keep copies of important documents",
        "Research local customs and etiquette"
    ]
    
    if 'food' in interests:
        tips.append("Ask locals for restaurant recommendations")
    
    if travel_style == 'solo':
        tips.append("Stay in touch with family/friends regularly")
    
    return tips

@app.route('/export-pdf/<itinerary_id>')
def export_pdf(itinerary_id):
    """Export itinerary to PDF"""
    try:
        if not REPORTLAB_AVAILABLE:
            return jsonify({
                'error': 'PDF export is not available. Please install reportlab: pip install reportlab==4.0.4'
            }), 500
            
        if itinerary_id not in generated_itineraries:
            return "Itinerary not found", 404
        
        itinerary = generated_itineraries[itinerary_id]
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Build PDF content
        story = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.blue)
        
        # Title
        story.append(Paragraph(f"WanderWise AI - {itinerary['destination']} Itinerary", title_style))
        story.append(Spacer(1, 12))
        
        # Trip details
        story.append(Paragraph(f"<b>Duration:</b> {itinerary['duration']}", styles['Normal']))
        story.append(Paragraph(f"<b>Budget:</b> {itinerary['budget_type']}", styles['Normal']))
        story.append(Paragraph(f"<b>Travel Style:</b> {itinerary['travel_style']}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Daily itinerary
        for day_plan in itinerary['days']:
            story.append(Paragraph(f"<b>Day {day_plan['day']} - {day_plan['date']}</b>", styles['Heading2']))
            story.append(Paragraph(f"<b>Attractions:</b> {', '.join(day_plan['attractions'])}", styles['Normal']))
            story.append(Paragraph(f"<b>Activities:</b> {', '.join(day_plan['activities'])}", styles['Normal']))
            story.append(Paragraph(f"<b>Daily Budget:</b> ${day_plan['budget']['total']}", styles['Normal']))
            story.append(Spacer(1, 12))
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(buffer, as_attachment=True, download_name=f"WanderWise_Itinerary_{itinerary['destination'].replace(' ', '_')}.pdf", mimetype='application/pdf')
        
    except Exception as e:
        return jsonify({
            'error': f'Error generating PDF: {str(e)}',
            'suggestion': 'Try using the print function instead, or install reportlab for PDF export'
        }), 500

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Handle contact form submission
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # In production, you would save this to database or send email
        print(f"Contact form submission: {name}, {email}, {message}")
        
        return render_template('contact.html', success=True)
    
    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)