import os
import json
import random
import time
import threading
from django.conf import settings
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError
from django.utils import timezone
from .models import Scenario, ScenarioOption, DynamicScenario, DynamicScenarioQuestion, DynamicScenarioAnswer
import logging
from django.core.cache import cache
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ExecutorTimeoutError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.db import connection
import functools
import hashlib
import concurrent.futures
from django.db.models import F
from django.contrib.auth.models import User
from core.models import Profile
from django.db import transaction

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client with timeout settings
client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    timeout=30.0,  # Reduced from 45 to 30 seconds to be well below worker timeout
    max_retries=2,  # Reduced from 3 to 2 for faster fallback
)

# Global timeout settings
API_CALL_TIMEOUT = getattr(settings, 'AI_REQUEST_TIMEOUT', 30)  # Default 30 seconds
MAX_TOKENS_MAP = getattr(settings, 'AI_MODEL_MAX_TOKENS', {
    'scenario': 600,     # Reduced from 800
    'question': 200,     # Reduced from 300
    'evaluation': 200,   # Reduced from 300
    'report': 800,       # Reduced from 1000
})

CATEGORIES = [
    'career', 'finance', 'relationships', 'time_management', 
    'education', 'health', 'ethics', 'other'
]

# Centralized OpenAI call function with safety mechanisms
def safe_openai_call(model, messages, max_tokens, response_format=None, temperature=0.7):
    """
    Execute an OpenAI API call with improved timeout safety and caching
    
    Args:
        model (str): The OpenAI model to use
        messages (list): List of message objects
        max_tokens (int): Maximum tokens for the response
        response_format (dict, optional): Format specification for the response
        temperature (float): Sampling temperature
        
    Returns:
        str or None: Response content or None if failed
    """
    # Create a more deterministic cache key from the messages content
    last_msg_content = messages[-1]['content'][:150]  # Take more context for better matching
    cache_key = f"openai_call_{model}_{hashlib.md5(last_msg_content.encode()).hexdigest()}"
    
    # Check cache first
    cached_response = cache.get(cache_key)
    if cached_response:
        logger.info(f"Using cached response for OpenAI call")
        return cached_response
    
    # Define the actual API call function with timeout handling
    def execute_call():
        try:
            kwargs = {
                'model': model,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'timeout': API_CALL_TIMEOUT - 2,  # Subtract 2 seconds for safety margin
            }
            
            if response_format:
                kwargs['response_format'] = response_format
                
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content.strip()
            
            # Cache successful responses for longer (6 hours)
            cache.set(cache_key, content, 21600)
            
            return content
        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI call: {str(e)}")
            return None
    
    # Execute with timeout protection using a thread pool
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(execute_call)
        try:
            # Reduce timeout by 1 second to ensure we return before any middleware timeouts
            result = future.result(timeout=API_CALL_TIMEOUT - 1)
            return result
        except (TimeoutError, concurrent.futures.TimeoutError):
            logger.error(f"OpenAI call timed out after {API_CALL_TIMEOUT - 1} seconds")
            # Cancel the future if possible
            try:
                future.cancel()
            except:
                pass
            return None
        except Exception as e:
            logger.error(f"Error in thread execution: {str(e)}")
            return None

def generate_scenario_with_openai(category=None, previous_option=None):
    """
    Generate a decision scenario using OpenAI
    
    Args:
        category (str, optional): The category of the scenario. If None, a random category will be selected.
        previous_option (ScenarioOption, optional): If provided, the new scenario will be related to this option.
    
    Returns:
        dict: A dictionary containing the scenario data
    """
    if not category:
        category = random.choice(CATEGORIES)
    
    # Check cache first with a more reliable cache key
    cache_key = f"scenario_cache_{category}_{hash(str(previous_option))}"
    cached_scenario = cache.get(cache_key)
    if cached_scenario:
        logger.info(f"Using cached scenario for category {category}")
        return cached_scenario
    
    # Base prompt
    prompt = f"""
    Create a decision-making scenario in the category of {category}. 
    The scenario should present a realistic situation where someone needs to make a decision.
    """
    
    # If there's a previous option, make this scenario related to that decision
    if previous_option:
        prompt += f"""
        This scenario should be a logical follow-up to a previous decision where the person chose:
        "{previous_option.text}"
        The feedback for that choice was: "{previous_option.feedback}"
        Make this scenario continue the same story or situation, dealing with the consequences
        or next steps after that previous decision.
        """
    
    prompt += """
    Format the response as a JSON object with the following structure:
    {
        "title": "Brief title of the scenario",
        "description": "Detailed description of the situation (1-2 paragraphs)",
        "difficulty": 1-3 (1=easy, 2=medium, 3=hard),
        "category": "category name",
        "xp_reward": 10-50 (based on difficulty),
        "options": [
            {
                "text": "Option 1 description",
                "rationality_points": 1-10,
                "decisiveness_points": 1-10,
                "empathy_points": 1-10,
                "clarity_points": 1-10,
                "feedback": "Detailed feedback explaining the consequences"
            },
            {
                "text": "Option 2 description",
                "rationality_points": 1-10,
                "decisiveness_points": 1-10,
                "empathy_points": 1-10,
                "clarity_points": 1-10,
                "feedback": "Detailed feedback explaining the consequences"
            },
            {
                "text": "Option 3 description",
                "rationality_points": 1-10,
                "decisiveness_points": 1-10,
                "empathy_points": 1-10,
                "clarity_points": 1-10,
                "feedback": "Detailed feedback explaining the consequences"
            }
        ]
    }
    
    Assign points based on different decision-making styles. Total points for each option should be about 20-25.
    """
    
    # Call OpenAI safely with timeout handling
    logger.info(f"Generating scenario with OpenAI for category {category}")
    
    # Use smaller model and reduced tokens
    model = "gpt-4o-mini"
    messages = [
        {"role": "system", "content": "You are a helpful assistant that creates decision-making scenarios in valid JSON format only."},
        {"role": "user", "content": prompt}
    ]
    
    content = safe_openai_call(model, messages, MAX_TOKENS_MAP['scenario'], {"type": "json_object"})
    
    # If successful, parse the response
    if content:
        try:
            scenario_data = json.loads(content)
            
            # Validate the required fields
            required_fields = ['title', 'description', 'difficulty', 'category', 'xp_reward', 'options']
            if all(field in scenario_data for field in required_fields):
                # Cache the successful result
                cache.set(cache_key, scenario_data, 3600)  # Cache for 1 hour
                return scenario_data
        except:
            logger.error("Error parsing JSON response from OpenAI")
    
    # If we got here, something failed - use fallback
    return create_fallback_scenario(category)

def create_fallback_scenario(category):
    """
    Create a fallback scenario if OpenAI API fails
    
    Args:
        category (str): The category of the scenario
    
    Returns:
        dict: A dictionary containing the scenario data
    """
    title = f"Decision in {category.capitalize()}"
    
    # Basic descriptions based on category
    descriptions = {
        'career': "You've received two job offers: one from a well-established company with good benefits but limited growth, and another from a startup with higher risk but potentially more rewarding.",
        'finance': "You have some extra savings and need to decide how to allocate them: paying down debt, investing in the stock market, or keeping as emergency fund.",
        'relationships': "A friend has shared a secret with you, but keeping it might harm another friend. You need to decide whether to keep the secret or tell the truth.",
        'time_management': "You have multiple deadlines approaching and limited time. You need to decide how to prioritize your tasks.",
        'education': "You need to choose between pursuing a higher degree that will take 2 years or taking a shorter professional certification course.",
        'health': "You need to decide between two treatment options for a minor health issue: one is faster but has side effects, the other is slower but gentler.",
        'ethics': "You witnessed a colleague bending company rules. You need to decide whether to report it, confront them directly, or stay silent.",
        'other': "You need to make a decision about a situation that will affect your future. There are several options, each with pros and cons."
    }
    
    description = descriptions.get(category, descriptions['other'])
    
    # Create the fallback scenario data
    scenario_data = {
        'title': title,
        'description': description,
        'difficulty': 1,
        'category': category,
        'xp_reward': 10,
        'options': [
            {
                'text': "Option A: Take the safer, more conventional approach.",
                'rationality_points': 7,
                'decisiveness_points': 5,
                'empathy_points': 3,
                'clarity_points': 5,
                'feedback': "You chose the safer option. This demonstrates good rational thinking and a clear understanding of the risks. It's a solid choice that avoids major pitfalls."
            },
            {
                'text': "Option B: Take the riskier approach with potentially higher rewards.",
                'rationality_points': 4,
                'decisiveness_points': 8,
                'empathy_points': 2,
                'clarity_points': 6,
                'feedback': "You chose the riskier option. This shows decisiveness and willingness to pursue greater opportunities, though with less emphasis on cautious analysis."
            },
            {
                'text': "Option C: Find a middle ground that balances different considerations.",
                'rationality_points': 6,
                'decisiveness_points': 3,
                'empathy_points': 8,
                'clarity_points': 5,
                'feedback': "You chose a balanced approach. This demonstrates empathy and consideration of multiple factors, though it might take longer to implement."
            }
        ]
    }
    
    return scenario_data

def create_scenario_from_data(scenario_data, previous_option=None):
    """
    Create a Scenario and ScenarioOptions from the generated data
    
    Args:
        scenario_data (dict): The scenario data from OpenAI
        previous_option (ScenarioOption, optional): If provided, this scenario is a follow-up to the option
    
    Returns:
        Scenario: The created scenario object
    """
    # Create the scenario
    scenario = Scenario.objects.create(
        title=scenario_data['title'],
        description=scenario_data['description'],
        category=scenario_data['category'],
        difficulty=scenario_data['difficulty'],
        xp_reward=scenario_data['xp_reward'],
        unlocked_at_level=scenario_data.get('unlocked_at_level', 1)  # Default to level 1 if not specified
    )
    
    # Create the options
    for option_data in scenario_data['options']:
        ScenarioOption.objects.create(
            scenario=scenario,
            text=option_data['text'],
            rationality_points=option_data['rationality_points'],
            decisiveness_points=option_data['decisiveness_points'],
            empathy_points=option_data['empathy_points'],
            clarity_points=option_data['clarity_points'],
            feedback=option_data['feedback']
        )
    
    # If this scenario is a follow-up, link the previous option to this new scenario
    if previous_option:
        previous_option.next_scenario = scenario
        previous_option.save()
    
    return scenario

def generate_daily_challenges_for_user(user, num_challenges=3):
    """
    Generate daily challenges for a user
    
    Args:
        user (User): The user to generate challenges for
        num_challenges (int): Number of challenges to generate
    
    Returns:
        list: List of created DailyChallenge objects
    """
    from .models import DailyChallenge, DailyUsageTracker
    
    # Get today's usage tracker
    today = timezone.now().date()
    tracker = DailyUsageTracker.get_for_user(user, today)
    
    # Daily challenges should not count against the scenario generation limit
    # Calculate how many challenges to generate
    num_to_generate = num_challenges
    
    # Generate scenarios across different categories
    categories = random.sample(CATEGORIES, min(num_to_generate, len(CATEGORIES)))
    challenges = []
    
    for category in categories:
        # Generate scenario data
        scenario_data = generate_scenario_with_openai(category)
        
        # Create the scenario in the database
        scenario = create_scenario_from_data(scenario_data)
        
        # Create the daily challenge
        challenge = DailyChallenge.objects.create(
            user=user,
            scenario=scenario
        )
        
        challenges.append(challenge)
    
    # We no longer update the tracker.scenarios_generated counter for daily challenges
    
    return challenges 

def handle_form_errors(form, request):
    """
    Helper function to handle form validation errors and display them as messages
    
    Args:
        form: The form with errors
        request: The HTTP request object
    """
    from django.contrib import messages
    
    for field, errors in form.errors.items():
        for error in errors:
            if field == '__all__':
                messages.error(request, f"Error: {error}")
            else:
                messages.error(request, f"Error in {field}: {error}") 

def generate_dynamic_scenario(user, category=None):
    """
    Generate a dynamic scenario with multiple questions using OpenAI
    
    Args:
        user (User): The user to create the scenario for
        category (str, optional): The category of the scenario. If None, a random category will be selected.
    
    Returns:
        DynamicScenario: The created scenario object
    """
    if not category:
        category = random.choice(CATEGORIES)
    
    # Use a more detailed prompt for scenario generation
    prompt = f"""
    Create a complex, realistic decision-making scenario in the category of {category}.
    
    The scenario should:
    1. Present a realistic situation with multiple decision points
    2. Be challenging but approachable for professional development
    3. Allow for diverse approaches and perspectives
    4. Be detailed enough to support 5-7 follow-up questions
    5. Be engaging and thought-provoking
    
    Format the response as a JSON object with the following structure:
    {{
        "title": "Clear, concise title for the scenario",
        "description": "Detailed description of the situation (2-3 paragraphs)",
        "difficulty": 1-3 (1=easy, 2=medium, 3=hard),
        "category": "{category}",
        "total_questions": 5-7
    }}
    
    The description should set up the context clearly without suggesting the initial question.
    """
    
    try:
        # Call OpenAI with better timeout handling
        response = safe_openai_call(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert scenario designer who creates realistic, engaging decision-making scenarios."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=MAX_TOKENS_MAP['scenario'],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        # If we got a response, parse it
        if response:
            try:
                scenario_data = json.loads(response)
                
                # Validate the required fields
                required_fields = ['title', 'description', 'difficulty', 'category', 'total_questions']
                if all(field in scenario_data for field in required_fields):
                    # Limit total questions to a reasonable number (5-7)
                    total_questions = min(max(scenario_data.get('total_questions', 5), 5), 7)
                    
                    # Create the dynamic scenario with a single database operation
                    scenario = DynamicScenario.objects.create(
                        user=user,
                        title=scenario_data['title'],
                        description=scenario_data['description'],
                        category=scenario_data['category'],
                        difficulty=scenario_data['difficulty'],
                        total_questions=total_questions,
                        current_question=0,  # Start with question 0, will be incremented when first question is generated
                        rationality_score=0,
                        decisiveness_score=0,
                        empathy_score=0,
                        clarity_score=0
                    )
                    
                    # Generate the first question immediately to save a request
                    generate_next_question(scenario)
                    
                    return scenario
            except json.JSONDecodeError:
                logger.error("Error parsing JSON response from OpenAI")
            except Exception as e:
                logger.error(f"Error creating dynamic scenario: {str(e)}")
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
    
    # If we reach here, use the fallback
    return create_fallback_dynamic_scenario(user, category)

def create_fallback_dynamic_scenario(user, category):
    """
    Create a fallback dynamic scenario if OpenAI API fails
    
    Args:
        user (User): The user to create the scenario for
        category (str): The category of the scenario
    
    Returns:
        DynamicScenario: The created scenario object
    """
    # Improved fallback scenarios with more detailed templates
    title_templates = {
        'career': "Career Crossroads Decision",
        'finance': "Financial Strategy Dilemma",
        'relationships': "Interpersonal Challenge",
        'time_management': "Priority Management Crisis",
        'education': "Learning Path Decision",
        'health': "Wellness Approach Choice",
        'ethics': "Ethical Dilemma Resolution",
        'other': "Complex Decision Challenge"
    }
    
    descriptions = {
        'career': "You're at a critical point in your career journey. You have two opportunities before you: joining an established company with stability and clear advancement paths, or taking a role at a promising startup with higher risk but potentially greater rewards and growth. The established company offers better benefits and work-life balance, while the startup would require longer hours but gives you significant equity and more decision-making authority. Your decision will impact not just your income, but your skill development, professional network, and long-term career trajectory.",
        
        'finance': "You've recently received an unexpected sum of money that could significantly impact your financial situation. Now you need to decide how to allocate these funds most effectively. You could pay down existing debts to reduce interest payments, invest in the market for potential long-term growth, save for a major upcoming expense, or diversify across multiple options. Each choice offers different risk levels, timeframes, and potential returns. Your current financial obligations, future goals, and risk tolerance all need to be considered in this decision.",
        
        'relationships': "You've discovered information that creates tension between your loyalty to two close friends. One friend has shared something in confidence that directly affects the other friend, who remains unaware. Keeping the secret maintains one friendship but may indirectly harm the other person who deserves to know. Revealing the information breaks your promise of confidentiality but could prevent future harm. The situation is complicated by your own values about honesty, loyalty, and the potential consequences of either choice on these long-term relationships and the broader social group.",
        
        'time_management': "You're facing multiple urgent deadlines competing for your limited time and attention. A major work project, family obligations, personal commitments, and an unexpected emergency have all converged at once. You cannot reasonably complete everything to the highest standard within the available time. You need to make difficult decisions about what to prioritize, what to delegate, what to postpone, and what to potentially let go. Each choice has professional, personal, and relationship implications that extend beyond the immediate timeframe.",
        
        'education': "You need to make an important educational decision that will impact your future learning path and career options. You're torn between pursuing an advanced degree that will take significant time and financial investment but potentially open more doors long-term, versus taking a specialized professional certification that can be completed more quickly and applied immediately in your current field. The degree option requires a two-year commitment with uncertain job prospects, while the certification builds directly on your existing experience but may have more limited growth potential.",
        
        'health': "You're facing a health decision that requires balancing different aspects of wellbeing. You've been diagnosed with a condition that has multiple treatment options, each with different approaches, timelines, and side effects. One treatment option is faster but more aggressive with potential side effects, while another is gentler but takes longer to show results. You need to weigh medical advice, quality of life considerations, impact on your daily activities and relationships, and your own health values and priorities to determine the best approach for your specific situation.",
        
        'ethics': "You're confronting an ethical dilemma at work that requires careful consideration of competing values. You've observed behavior from a colleague that violates company policy but isn't clearly illegal. Reporting the violation could protect the company and other stakeholders but might severely impact your colleague's career. Staying silent avoids conflict but could make you complicit if the situation worsens. The organizational culture, your professional responsibilities, personal values, and the potential consequences for all involved must factor into your decision-making process.",
        
        'other': "You're facing a complex situation that requires balancing multiple factors and stakeholder interests. There are several viable options before you, each with different advantages, risks, and implications. Your decision will have both immediate consequences and potential long-term effects that aren't entirely predictable. You need to consider not just the practical outcomes, but also alignment with your values, impact on relationships, and the precedent your choice might set for future situations."
    }
    
    # Get the title and description for this category
    title = title_templates.get(category, title_templates['other'])
    description = descriptions.get(category, descriptions['other'])
    
    # Create the scenario with a single DB operation
    scenario = DynamicScenario.objects.create(
        user=user,
        title=title,
        description=description,
        category=category,
        difficulty=2,  # Medium difficulty
        total_questions=7,  # Standard number of questions
        current_question=0,  # Start with question 0
        rationality_score=0,
        decisiveness_score=0,
        empathy_score=0,
        clarity_score=0
    )
    
    # Generate the first question immediately
    question = DynamicScenarioQuestion.objects.create(
        scenario=scenario,
        question_text="What information would you want to gather before making your initial decision in this situation?",
        order=1
    )
    
    # Update the scenario's current question counter
    DynamicScenario.objects.filter(id=scenario.id).update(current_question=1)
    scenario.current_question = 1
    
    return scenario

def generate_next_question(scenario, previous_answer=None):
    """
    Generate the next question for a dynamic scenario based on previous answers
    
    Args:
        scenario (DynamicScenario): The scenario to generate a question for
        previous_answer (DynamicScenarioAnswer, optional): The previous answer to base the next question on
    
    Returns:
        DynamicScenarioQuestion: The created question object
    """
    # Determine the next question number
    next_question_order = scenario.current_question + 1
    
    # If we've reached the total questions, return None
    if next_question_order > scenario.total_questions:
        return None
        
    # Skip caching to ensure fresh questions on each request
    
    # Get all previous questions and answers - use select_related to minimize db queries
    previous_questions = DynamicScenarioQuestion.objects.filter(scenario=scenario).order_by('order')
    question_answer_history = []
    
    for q in previous_questions:
        question_text = q.question_text
        # Use prefetch_related to optimize the query
        answers = list(q.answers.all()[:1])  # Limit to just the first answer
        answer_text = answers[0].answer_text if answers else None
        
        if answer_text:
            question_answer_history.append({
                "question": question_text,
                "answer": answer_text
            })
    
    logger.info(f"Generating question #{next_question_order} for scenario {scenario.id}")
    
    # Enhanced prompt for question generation with more context and dynamic elements
    prompt = f"""
    Generate the next question (question #{next_question_order}) for this dynamic decision-making scenario.
    
    Scenario title: {scenario.title}
    Scenario description: {scenario.description}
    Category: {scenario.category}
    
    This is question {next_question_order} of {scenario.total_questions}.
    
    Previous questions and answers:
    {json.dumps(question_answer_history, indent=2)}
    
    Generate a question that:
    1. Builds on the previous answers and creates a coherent narrative
    2. Is open-ended but focused on decision-making
    3. Is challenging but appropriate for the scenario context
    4. Is different from previous questions and explores new aspects
    5. Would help assess the user's decision-making abilities
    
    Format the response as a JSON object with the following structure:
    {{
        "question": "The next engaging question to ask"
    }}
    """
    
    # Call OpenAI safely with timeout handling
    messages = [
        {"role": "system", "content": "You are a helpful assistant that creates thought-provoking decision-making questions in valid JSON format only."},
        {"role": "user", "content": prompt}
    ]
    
    content = safe_openai_call("gpt-4o-mini", messages, MAX_TOKENS_MAP['question'], {"type": "json_object"})
    
    # If successful, parse the response
    if content:
        try:
            question_data = json.loads(content)
            
            # Validate and create the question
            if 'question' in question_data:
                # Create the question
                question = DynamicScenarioQuestion.objects.create(
                    scenario=scenario,
                    question_text=question_data['question'],
                    order=next_question_order
                )
                
                # Update the scenario - use update to minimize db writes
                DynamicScenario.objects.filter(id=scenario.id).update(
                    current_question=next_question_order
                )
                
                # Update the local object
                scenario.current_question = next_question_order
                
                return question
        except Exception as e:
            logger.error(f"Error parsing JSON response from OpenAI for question generation: {str(e)}")
    
    # Fallback for API failures
    fallback_question = create_fallback_question(scenario, next_question_order)
    
    # Update the scenario - use update to minimize db writes
    DynamicScenario.objects.filter(id=scenario.id).update(
        current_question=next_question_order
    )
    
    # Update the local object
    scenario.current_question = next_question_order
    
    return fallback_question

def create_fallback_question(scenario, question_order):
    """
    Create a fallback question if OpenAI API fails
    
    Args:
        scenario (DynamicScenario): The scenario to create a question for
        question_order (int): The order of the question
    
    Returns:
        DynamicScenarioQuestion: The created question object
    """
    # Category-specific questions for more relevant fallbacks
    category_questions = {
        'career': [
            "What specific information would you need to evaluate both job opportunities properly?",
            "Which aspects of your career goals are most important to you in this decision?",
            "How would you weigh stability against potential growth in this situation?",
            "What potential risks do you see in each option, and how would you mitigate them?",
            "Who would you consult for advice in this career decision, and why?",
            "How would you approach negotiating your role and compensation in your preferred option?",
            "What would your decision-making timeline look like for this career choice?"
        ],
        'finance': [
            "What information about your current financial situation is most relevant to this decision?",
            "How would you prioritize immediate financial needs versus long-term growth?",
            "What specific criteria would you use to evaluate different investment options?",
            "How would you assess the risk levels you're comfortable with in this financial decision?",
            "What external factors might influence the outcomes of your financial choice?",
            "How would you create a balanced approach that addresses multiple financial goals?",
            "What would trigger you to reassess or modify your financial decision in the future?"
        ],
        'relationships': [
            "How do you weigh your responsibilities to each person in this situation?",
            "What principles or values are most important to you in navigating this interpersonal dilemma?",
            "How might your decision affect the trust within these relationships?",
            "What are possible ways to address this situation without choosing one person over the other?",
            "What would a conversation with each party involved look like?",
            "How might your personal biases be influencing your perspective on this situation?",
            "What boundaries would you need to establish going forward after this situation?"
        ],
        'time_management': [
            "What criteria would you use to prioritize these competing demands?",
            "How would you communicate your capacity limitations to stakeholders?",
            "What tasks could be delegated or postponed, and what would that process look like?",
            "How would you restructure your approach to maximize efficiency?",
            "What strategies would you use to maintain quality while managing multiple priorities?",
            "How would you prevent similar time conflicts from occurring in the future?",
            "What personal boundaries would you establish to maintain well-being during this busy period?"
        ],
        'education': [
            "What specific career outcomes are you hoping to achieve through this educational decision?",
            "How would you evaluate the return on investment for each educational path?",
            "What learning style works best for you, and how does that factor into your decision?",
            "What networking or mentorship opportunities does each option provide?",
            "How would you balance educational pursuits with other life responsibilities?",
            "What would your contingency plan be if your chosen path doesn't meet expectations?",
            "How would you measure success in your educational journey?"
        ],
        'health': [
            "What aspects of your health and well-being are most important to consider in this decision?",
            "How would you gather and evaluate different medical opinions?",
            "What role should your personal preferences play versus expert recommendations?",
            "How would you incorporate this health decision into your daily routine?",
            "What support systems would you need to implement your health plan effectively?",
            "How would you track progress and measure success with your chosen approach?",
            "What would trigger you to reconsider or adjust your health plan?"
        ],
        'ethics': [
            "What ethical principles or values are in conflict in this situation?",
            "How would you weigh your professional responsibilities against personal relationships?",
            "What are the potential consequences of each possible action for all stakeholders?",
            "How might your organizational culture influence your approach to this ethical dilemma?",
            "What information would you need to gather before making a final decision?",
            "How would you communicate your decision to those affected?",
            "What precedent might your decision set for future similar situations?"
        ]
    }
    
    # Get questions for this category or use generic questions
    category = scenario.category
    questions = category_questions.get(category, [])
    
    # Generic questions as fallback
    generic_questions = [
        "What initial information would you want to gather before making any decisions in this situation?",
        "What are the key factors you would consider in this decision?",
        "Who are the stakeholders affected by this decision and how would you consider their interests?",
        "What potential risks do you see in this situation?",
        "What potential opportunities do you see in this situation?",
        "How would you prioritize competing interests in this scenario?",
        "What would be your first action step in addressing this situation?",
        "How would you measure success in this scenario?",
        "What would you do if your initial approach doesn't work?",
        "How would you communicate your decision to others involved?",
        "What resources would you need to implement your decision?",
        "How would you handle resistance to your decision?",
        "What would be your backup plan?",
        "How would you evaluate the effectiveness of your decision after implementation?",
        "What lessons would you take from this scenario for future decisions?"
    ]
    
    # Combine category-specific questions with generic ones
    all_questions = questions + generic_questions
    
    # Use the appropriate question based on order, or cycle through if we've run out
    if question_order <= len(all_questions):
        question_text = all_questions[question_order - 1]
    else:
        # Cycle through questions if we've run out
        index = (question_order - 1) % len(all_questions)
        question_text = all_questions[index]
    
    # Create the question
    question = DynamicScenarioQuestion.objects.create(
        scenario=scenario,
        question_text=question_text,
        order=question_order
    )
    
    # Skip save operation and use update for efficiency
    # The caller already updates the scenario current_question
    
    return question

def evaluate_answer(question, answer_text):
    """
    Evaluate a user's answer to a dynamic scenario question
    
    Args:
        question (DynamicScenarioQuestion): The question being answered
        answer_text (str): The user's answer text
    
    Returns:
        dict: Evaluation data with scores and feedback
    """
    # Get scenario details for context
    scenario = question.scenario
    
    # Use a more comprehensive prompt for better evaluation
    prompt = f"""
    You are evaluating a user's answer to a question in a decision-making scenario.
    
    Scenario Context: {scenario.title} - {scenario.description}
    Category: {scenario.category}
    
    Question: {question.question_text}
    User Answer: {answer_text}
    
    Please evaluate the answer on the following four criteria on a scale from 1-10:
    1. Rationality: Logical reasoning and critical thinking
    2. Decisiveness: Clear decision-making and confidence
    3. Empathy: Consideration of others' perspectives and feelings
    4. Clarity: Clear communication and structured thinking
    
    Format your response as a valid JSON object with the following structure:
    {{
        "rationality_score": 7,
        "decisiveness_score": 8,
        "empathy_score": 6,
        "clarity_score": 7,
        "feedback": "Concise feedback on the answer highlighting strengths and areas for improvement (2-3 sentences)"
    }}
    """
    
    # Call OpenAI safely with timeout handling
    messages = [
        {"role": "system", "content": "You are an expert decision-making coach who provides objective evaluations. Always respond with valid JSON only."},
        {"role": "user", "content": prompt}
    ]
    
    content = safe_openai_call("gpt-4o-mini", messages, MAX_TOKENS_MAP['evaluation'], {"type": "json_object"})
    
    # If successful, parse the response
    if content:
        try:
            # Clean up the response to ensure it's valid JSON
            # Remove any leading/trailing whitespace and ensure we only parse the JSON object
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            evaluation_data = json.loads(content)
            
            # Validate and normalize scores
            for score_key in ['rationality_score', 'decisiveness_score', 'empathy_score', 'clarity_score']:
                if score_key not in evaluation_data:
                    evaluation_data[score_key] = 5  # Default score
                else:
                    # Ensure score is an integer between 1 and 10
                    try:
                        score = int(evaluation_data[score_key])
                        evaluation_data[score_key] = max(1, min(score, 10))
                    except (ValueError, TypeError):
                        evaluation_data[score_key] = 5  # Default score if not valid
            
            # Ensure feedback is present
            if 'feedback' not in evaluation_data or not evaluation_data['feedback']:
                evaluation_data['feedback'] = "This is a balanced response showing some consideration of key factors."
            
            return evaluation_data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing evaluation response: {str(e)}")
            # If we get a JSON parsing error, extract scores using regex as a fallback
            try:
                import re
                rationality = re.search(r'rationality_score["\s]*:[\s"]*(\d+)', content)
                decisiveness = re.search(r'decisiveness_score["\s]*:[\s"]*(\d+)', content)
                empathy = re.search(r'empathy_score["\s]*:[\s"]*(\d+)', content)
                clarity = re.search(r'clarity_score["\s]*:[\s"]*(\d+)', content)
                feedback = re.search(r'feedback["\s]*:[\s"]*["\'](.*?)["\']', content)
                
                return {
                    "rationality_score": int(rationality.group(1)) if rationality else 5,
                    "decisiveness_score": int(decisiveness.group(1)) if decisiveness else 5,
                    "empathy_score": int(empathy.group(1)) if empathy else 5,
                    "clarity_score": int(clarity.group(1)) if clarity else 5,
                    "feedback": feedback.group(1) if feedback else "This is a balanced response showing good consideration of key factors."
                }
            except Exception as ex:
                logger.error(f"Error in fallback evaluation parsing: {str(ex)}")
                return create_fallback_evaluation()
        except Exception as e:
            logger.error(f"Error in evaluation: {str(e)}")
    
    # Fallback for API failures
    return create_fallback_evaluation()

def create_fallback_evaluation():
    """
    Create a fallback evaluation if OpenAI API fails
    
    Returns:
        dict: Default evaluation data
    """
    return {
        'rationality_score': 5,
        'decisiveness_score': 5,
        'empathy_score': 5,
        'clarity_score': 5,
        'feedback': "Your answer demonstrates a balanced approach to the situation. Consider exploring more details in future responses."
    }

def generate_final_report(scenario):
    """
    Generate a final report for a completed dynamic scenario with better timeout handling
    and reduced database operations
    
    Args:
        scenario (DynamicScenario): The completed scenario
    
    Returns:
        dict: Report data including scores, analysis, and recommendations
    """
    # Use cache to avoid regenerating reports frequently
    cache_key = f"report_cache_{scenario.id}"
    cached_report = cache.get(cache_key)
    if cached_report:
        # If we have a cached report, just set the scenario as completed
        if not scenario.completed:
            DynamicScenario.objects.filter(id=scenario.id).update(completed=True)
            scenario.completed = True
        logger.info(f"Using cached report for scenario {scenario.id}")
        return cached_report
    
    # Get all answers for this scenario with their evaluations
    questions = DynamicScenarioQuestion.objects.filter(scenario=scenario).order_by('order')
    
    # Collect answers data
    answers_data = []
    total_rationality = 0
    total_decisiveness = 0
    total_empathy = 0
    total_clarity = 0
    
    # Track if we have at least one answer
    has_answers = False
    
    for question in questions:
        # Get the first answer for this question (assuming there's only one per question)
        answers = DynamicScenarioAnswer.objects.filter(question=question)
        if answers.exists():
            has_answers = True
            answer = answers.first()
            answers_data.append({
                'question': question.question_text,
                'answer': answer.answer_text,
                'evaluation': {
                    'rationality': answer.rationality_score,
                    'decisiveness': answer.decisiveness_score,
                    'empathy': answer.empathy_score,
                    'clarity': answer.clarity_score,
                    'feedback': answer.feedback
                }
            })
            
            # Accumulate scores
            total_rationality += answer.rationality_score
            total_decisiveness += answer.decisiveness_score
            total_empathy += answer.empathy_score
            total_clarity += answer.clarity_score
    
    # If no answers, create a default report
    if not has_answers:
        return create_fallback_report(scenario)
    
    # Calculate average scores (avoid division by zero)
    num_answers = len(answers_data)
    avg_rationality = total_rationality / num_answers if num_answers > 0 else 0
    avg_decisiveness = total_decisiveness / num_answers if num_answers > 0 else 0
    avg_empathy = total_empathy / num_answers if num_answers > 0 else 0
    avg_clarity = total_clarity / num_answers if num_answers > 0 else 0
    
    # Calculate final score (sum of all averages)
    final_score = avg_rationality + avg_decisiveness + avg_empathy + avg_clarity
    
    # Generate the report with OpenAI (ensuring consistent scores)
    prompt = f"""
    Generate a comprehensive decision-making report based on this scenario and the user's answers.
    
    Scenario: {scenario.title} - {scenario.description}
    
    Answers & Evaluations:
    {json.dumps(answers_data, indent=2)}
    
    Please generate a JSON response with the following format:
    {{
        "strengths": ["Strength 1", "Strength 2", "Strength 3"],
        "weaknesses": ["Area for improvement 1", "Area for improvement 2", "Area for improvement 3"],
        "improvement_plan": ["Specific action item 1", "Specific action item 2", "Specific action item 3"],
        "resources": ["Resource/tip 1", "Resource/tip 2", "Resource/tip 3"]
    }}
    
    Note: These results should be consistent with the numerical scores:
    - Rationality: {avg_rationality:.1f}/10
    - Decisiveness: {avg_decisiveness:.1f}/10
    - Empathy: {avg_empathy:.1f}/10
    - Clarity: {avg_clarity:.1f}/10
    - Overall Score: {final_score:.1f}/40
    """
    
    # Call OpenAI safely with timeout handling
    messages = [
        {"role": "system", "content": "You are an expert decision-making coach who provides detailed, personalized assessments and actionable advice."},
        {"role": "user", "content": prompt}
    ]
    
    content = safe_openai_call("gpt-4o-mini", messages, MAX_TOKENS_MAP['report'], {"type": "json_object"})
    
    # Process the response
    if content:
        try:
            # Clean up the response to ensure it's valid JSON
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            report_data = json.loads(content)
            
            # Ensure all required fields are present
            if not all(k in report_data for k in ['strengths', 'weaknesses', 'improvement_plan', 'resources']):
                logger.error("Missing fields in report data")
                report_data = create_fallback_report_data()
            
            # Update the scenario with the report data
            with transaction.atomic():
                # Update the scenario scores and status
                DynamicScenario.objects.filter(id=scenario.id).update(
                    final_score=final_score,
                    rationality_score=avg_rationality,
                    decisiveness_score=avg_decisiveness,
                    empathy_score=avg_empathy,
                    clarity_score=avg_clarity,
                    strengths=json.dumps(report_data['strengths']),
                    weaknesses=json.dumps(report_data['weaknesses']),
                    improvement_plan=json.dumps(report_data['improvement_plan']),
                    resources=json.dumps(report_data['resources']),
                    completed=True
                )
                
                # Update the local object
                scenario.final_score = final_score
                scenario.rationality_score = avg_rationality
                scenario.decisiveness_score = avg_decisiveness
                scenario.empathy_score = avg_empathy
                scenario.clarity_score = avg_clarity
                scenario.strengths = json.dumps(report_data['strengths'])
                scenario.weaknesses = json.dumps(report_data['weaknesses'])
                scenario.improvement_plan = json.dumps(report_data['improvement_plan'])
                scenario.resources = json.dumps(report_data['resources'])
                scenario.completed = True
                
                # Update the user's profile with XP and skill points
                if hasattr(scenario.user, 'profile'):
                    Profile.objects.filter(user=scenario.user).update(
                        xp_points=F('xp_points') + 50,  # 50 XP for completing a dynamic scenario
                        rationality_score=F('rationality_score') + avg_rationality,
                        decisiveness_score=F('decisiveness_score') + avg_decisiveness,
                        empathy_score=F('empathy_score') + avg_empathy,
                        clarity_score=F('clarity_score') + avg_clarity
                    )
            
            # Store the full report data in cache to avoid regenerating
            full_report = {
                'final_score': final_score,
                'rationality_score': avg_rationality,
                'decisiveness_score': avg_decisiveness,
                'empathy_score': avg_empathy,
                'clarity_score': avg_clarity,
                'strengths': report_data['strengths'],
                'weaknesses': report_data['weaknesses'],
                'improvement_plan': report_data['improvement_plan'],
                'resources': report_data['resources']
            }
            
            # Cache the report for future use
            cache.set(cache_key, full_report, 86400)  # 24 hours
            
            return full_report
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing report data: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
    
    # Fallback to default report
    return create_fallback_report(scenario)

def create_fallback_report(scenario):
    """Create a fallback report if the OpenAI generation fails"""
    # Calculate scores from existing answers if available
    questions = DynamicScenarioQuestion.objects.filter(scenario=scenario).order_by('order')
    
    total_rationality = 0
    total_decisiveness = 0
    total_empathy = 0
    total_clarity = 0
    num_answers = 0
    
    for question in questions:
        answers = DynamicScenarioAnswer.objects.filter(question=question)
        if answers.exists():
            answer = answers.first()
            total_rationality += answer.rationality_score
            total_decisiveness += answer.decisiveness_score
            total_empathy += answer.empathy_score
            total_clarity += answer.clarity_score
            num_answers += 1
    
    # Calculate average scores
    avg_rationality = total_rationality / num_answers if num_answers > 0 else 5
    avg_decisiveness = total_decisiveness / num_answers if num_answers > 0 else 5
    avg_empathy = total_empathy / num_answers if num_answers > 0 else 5
    avg_clarity = total_clarity / num_answers if num_answers > 0 else 5
    
    # Calculate final score
    final_score = avg_rationality + avg_decisiveness + avg_empathy + avg_clarity
    
    # Generate fallback report data
    report_data = create_fallback_report_data()
    
    # Update the scenario with the fallback data
    with transaction.atomic():
        DynamicScenario.objects.filter(id=scenario.id).update(
            final_score=final_score,
            rationality_score=avg_rationality,
            decisiveness_score=avg_decisiveness,
            empathy_score=avg_empathy,
            clarity_score=avg_clarity,
            strengths=json.dumps(report_data['strengths']),
            weaknesses=json.dumps(report_data['weaknesses']),
            improvement_plan=json.dumps(report_data['improvement_plan']),
            resources=json.dumps(report_data['resources']),
            completed=True
        )
        
        # Update the local object
        scenario.final_score = final_score
        scenario.rationality_score = avg_rationality
        scenario.decisiveness_score = avg_decisiveness
        scenario.empathy_score = avg_empathy
        scenario.clarity_score = avg_clarity
        scenario.strengths = json.dumps(report_data['strengths'])
        scenario.weaknesses = json.dumps(report_data['weaknesses'])
        scenario.improvement_plan = json.dumps(report_data['improvement_plan'])
        scenario.resources = json.dumps(report_data['resources'])
        scenario.completed = True
        
        # Update the user's profile with XP and skill points
        if hasattr(scenario.user, 'profile'):
            Profile.objects.filter(user=scenario.user).update(
                xp_points=F('xp_points') + 50,  # 50 XP for completing a dynamic scenario
                rationality_score=F('rationality_score') + avg_rationality,
                decisiveness_score=F('decisiveness_score') + avg_decisiveness,
                empathy_score=F('empathy_score') + avg_empathy,
                clarity_score=F('clarity_score') + avg_clarity
            )
    
    full_report = {
        'final_score': final_score,
        'rationality_score': avg_rationality,
        'decisiveness_score': avg_decisiveness,
        'empathy_score': avg_empathy,
        'clarity_score': avg_clarity,
        'strengths': report_data['strengths'],
        'weaknesses': report_data['weaknesses'],
        'improvement_plan': report_data['improvement_plan'],
        'resources': report_data['resources']
    }
    
    return full_report

def create_fallback_report_data():
    """Create default report data"""
    return {
        'strengths': [
            "Balanced decision-making approach",
            "Consideration of multiple perspectives",
            "Practical problem-solving skills"
        ],
        'weaknesses': [
            "Could develop more structured analysis",
            "May benefit from considering long-term implications",
            "Could strengthen emotional intelligence in decisions"
        ],
        'improvement_plan': [
            "Practice breaking down complex decisions into smaller steps",
            "Consider creating pros/cons lists for important choices",
            "Reflect on past decisions to identify patterns"
        ],
        'resources': [
            "Try decision-making frameworks like WRAP (Widen options, Reality-test assumptions, Attain distance, Prepare to be wrong)",
            "Consider journaling about important decisions",
            "Practice mindfulness to improve clarity during decision-making"
        ]
    }

def send_notification_email(notification):
    """
    Send an email based on a notification object.
    """
    try:
        user = notification.user
        notification_type = notification.notification_type
        subject = notification.title
        
        # Get email template based on notification type
        template_name = f"core/emails/{notification_type}_email.html"
        
        # Context for the email template
        context = {
            'user': user,
            'notification': notification,
            'site_name': 'DesiQ',
            'support_email': settings.DEFAULT_FROM_EMAIL,
        }
        
        # Render HTML content
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        # Send the email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Sent {notification_type} email to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending {notification_type} email: {str(e)}")
        return False

def send_welcome_email(user):
    """
    Send welcome email to newly registered users
    """
    from .models import Notification
    
    title = f"Welcome to DesiQ, {user.username}!"
    message = (
        f"Thank you for joining DesiQ! We're excited to have you with us.\n\n"
        f"Start exploring scenarios, take personality tests, and connect with mentors "
        f"to improve your decision-making skills.\n\n"
        f"If you have any questions, feel free to reach out to our support team."
    )
    
    # Create notification record
    notification = Notification.create_notification(
        user=user,
        title=title,
        message=message,
        notification_type='welcome',
        send_email=True
    )
    
    return notification

def send_profile_update_notification(user):
    """
    Send notification when user updates their profile
    """
    from .models import Notification
    
    title = "Profile Updated Successfully"
    message = (
        f"Your profile has been updated successfully.\n\n"
        f"If you didn't make these changes, please contact our support team immediately."
    )
    
    # Create notification record
    notification = Notification.create_notification(
        user=user,
        title=title,
        message=message,
        notification_type='profile',
        send_email=True
    )
    
    return notification

def handle_user_registered(user, is_new=False, **kwargs):
    """
    Handle user registration from any source (including social auth)
    This function is meant to be connected to social auth signals
    """
    if is_new:
        # Send welcome email for new users
        try:
            send_welcome_email(user)
            logger.info(f"Welcome email sent to {user.email} after social auth registration")
        except Exception as e:
            logger.error(f"Failed to send welcome email after social auth: {str(e)}")
    
    return None 

def log_request_performance(view_func):
    """
    Decorator to log request performance metrics
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Start timing
        start_time = time.time()
        
        # Record query count before request
        initial_queries = len(connection.queries)
        
        # Process view
        response = view_func(request, *args, **kwargs)
        
        # Calculate total time
        duration = time.time() - start_time
        
        # Calculate queries executed during this request
        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries
        
        # Log request info for requests taking more than 200ms
        if duration > 0.2:
            # Note: In production, this would produce a lot of logs,
            # so we only log slower requests
            logger.info(
                f"Slow request: {request.path} - "
                f"Time: {duration:.4f}s, "
                f"Queries: {query_count}, "
                f"Method: {request.method}, "
                f"User: {request.user.username if request.user.is_authenticated else 'anonymous'}"
            )
            
            # Log slow queries (over 100ms)
            slow_queries = []
            for query in connection.queries[initial_queries:final_queries]:
                query_time = float(query.get('time', 0))
                if query_time > 0.1:  # 100ms
                    slow_queries.append({
                        'sql': query.get('sql', '')[:100] + '...',  # Truncate for log clarity
                        'time': query_time
                    })
            
            if slow_queries:
                logger.warning(
                    f"Slow queries in {request.path}:\n" +
                    "\n".join([f" - {q['time']:.4f}s: {q['sql']}" for q in slow_queries])
                )
        
        return response
    
    return wrapper 

def cached_queryset(prefix, timeout=300):
    """
    Decorator for caching expensive QuerySet operations
    
    Args:
        prefix (str): Prefix for the cache key
        timeout (int): Cache timeout in seconds (default: 5 minutes)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key based on function name, args and kwargs
            key_parts = [prefix, func.__name__]
            
            # Add stringified args and kwargs to the key
            for arg in args:
                # Handle special case for request objects
                if hasattr(arg, 'path') and hasattr(arg, 'method'):
                    # For request objects, use user ID if authenticated
                    if hasattr(arg, 'user') and hasattr(arg.user, 'id'):
                        key_parts.append(f"user_{arg.user.id}")
                    else:
                        key_parts.append("anon")
                else:
                    key_parts.append(str(arg))
            
            # Add sorted kwargs to ensure consistent key generation
            sorted_kwargs = sorted(kwargs.items())
            for k, v in sorted_kwargs:
                key_parts.append(f"{k}_{v}")
            
            cache_key = "_".join(key_parts)
            
            # Try to get cached result
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # If not cached, execute the function
            result = func(*args, **kwargs)
            
            # Cache the result (only if it's a valid result)
            if result is not None:
                cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator 