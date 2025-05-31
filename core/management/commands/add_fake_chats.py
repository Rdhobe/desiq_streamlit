from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import ChatRoom, ChatMessage
from django.utils import timezone
import random
from datetime import timedelta
from faker import Faker
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Add fake chat messages between users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rooms',
            type=int,
            default=5,
            help='Number of chat rooms to create'
        )
        parser.add_argument(
            '--messages',
            type=int,
            default=200,
            help='Number of messages to create'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if chat rooms already exist'
        )

    def handle(self, *args, **options):
        rooms_to_create = options['rooms']
        messages_to_create = options['messages']
        force = options['force']
        
        # Initialize Faker with Indian locale
        fake = Faker('en_IN')
        
        # Get all users
        users = list(User.objects.all())
        if len(users) < 5:
            self.stdout.write(self.style.WARNING(f"Not enough users to create meaningful chat rooms. Found {len(users)} users, need at least 5."))
            return
        
        # Check if we already have chat rooms
        existing_rooms = ChatRoom.objects.count()
        if existing_rooms > 0 and not force:
            self.stdout.write(self.style.WARNING(f"Chat rooms already exist ({existing_rooms} found). Use --force to create more."))
        
        # Create community chat room if it doesn't exist
        community_room, created = ChatRoom.objects.get_or_create(
            name="Community Chat",
            room_type="public",
            defaults={
                'created_by': random.choice(users),
                'description': "Public community chat room for all users"
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS("Created Community Chat room"))
        else:
            self.stdout.write("Community Chat room already exists")
        
        # Add all users as participants in the community room
        for user in users:
            community_room.participants.add(user)
        
        # Create additional chat rooms
        created_rooms = []
        if force or existing_rooms == 0:
            self.stdout.write(f"Creating {rooms_to_create} chat rooms...")
            
            for i in range(rooms_to_create):
                # Decide room type
                room_type = random.choice(['personal', 'group', 'public'])
                
                # Generate room name
                if room_type == 'personal':
                    user1 = random.choice(users)
                    user2 = random.choice([u for u in users if u != user1])
                    name = f"Chat between {user1.first_name} and {user2.first_name}"
                    description = f"Private chat between {user1.username} and {user2.username}"
                    participants = [user1, user2]
                elif room_type == 'group':
                    name = fake.catch_phrase()
                    description = fake.paragraph(nb_sentences=2)
                    # Add 3-8 random participants
                    participants = random.sample(users, random.randint(3, min(8, len(users))))
                else:  # public
                    name = f"Public: {fake.bs()}"
                    description = fake.paragraph(nb_sentences=2)
                    # Add 5-15 random participants or all if less than 15
                    participants = random.sample(users, random.randint(5, min(15, len(users))))
                
                # Create the room
                room = ChatRoom.objects.create(
                    name=name,
                    description=description,
                    created_by=random.choice(participants),
                    room_type=room_type
                )
                
                # Add participants
                for user in participants:
                    room.participants.add(user)
                
                created_rooms.append(room)
                
                if (i + 1) % 5 == 0 or i + 1 == rooms_to_create:
                    self.stdout.write(f"Created {i + 1}/{rooms_to_create} rooms")
        
        # Combine all rooms for message creation
        all_rooms = list(ChatRoom.objects.all())
        
        # Create chat messages
        self.stdout.write(f"Creating {messages_to_create} chat messages...")
        
        # Common Indian chat phrases and greetings
        greetings = [
            "Namaste!", "Kaise ho?", "Kya chal raha hai?", "Sab badhiya?", 
            "Hello ji!", "Good morning!", "Kem cho?", "Kya haal hai?",
            "Sat sri akal", "Aur batao", "Kya kar rahe ho?", "Kiddan?",
            "Vanakkam", "Namaskar", "Radhe Radhe", "Jai Shree Krishna"
        ]
        
        # Common conversation starters
        conversation_starters = [
            "Aaj ka mausam kaisa hai?", "Lunch mein kya khaya?", "Weekend ka kya plan hai?",
            "New movie dekhi?", "Cricket match dekha kal?", "Office mein sab theek?",
            "Kya chal raha hai aajkal?", "Koi nayi book padh rahe ho?", "Ghar pe sab kaise hain?",
            "Koi travel plan hai?", "Naya phone liya?", "Koi accha restaurant recommend karoge?",
            "Work from home kar rahe ho?", "Traffic kaisa tha aaj?", "Diwali ke liye kya plan hai?",
            "Koi accha web series suggest karo", "Gym jaate ho?", "Chai ya coffee?",
            "Monsoon mein kya karna pasand hai?", "Favorite street food kya hai?"
        ]
        
        # Common responses
        responses = [
            "Haan bilkul!", "Nahi yaar", "Pata nahi", "Ho sakta hai", "Zaroor", 
            "Ekdum sahi", "Mujhe lagta hai", "Shayad", "Haan sahi hai", "Accha idea hai",
            "Main soch raha tha", "Kal baat karte hain", "Thik hai", "Pakka", "Dekhte hain",
            "Mujhe batana", "Koi baat nahi", "Koshish karta hoon", "Definitely", "Samajh gaya"
        ]
        
        # Common chat expressions
        expressions = [
            "Haha!", "LOL!", "Exactly!", "Sahi baat hai", "Ekdum correct", 
            "Mast!", "Badhiya!", "Wow!", "OMG!", "Seriously?", 
            "Interesting...", "Hmm...", "Accha", "Theek hai", "Samajh gaya",
            "Bilkul", "Ekdum", "Haan ji", "Arrey wah!", "Kya baat hai!"
        ]
        
        created_count = 0
        
        # Generate messages in chronological order
        start_date = timezone.now() - timedelta(days=30)  # Messages from last 30 days
        
        for i in range(messages_to_create):
            try:
                # Select a random room
                room = random.choice(all_rooms)
                
                # Select a random participant from the room
                participants = list(room.participants.all())
                if not participants:
                    continue
                    
                sender = random.choice(participants)
                
                # Generate message timestamp (chronological order)
                message_date = start_date + timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                # Generate message content
                message_type = random.randint(1, 10)
                
                if message_type == 1:
                    # Greeting
                    content = random.choice(greetings)
                elif message_type == 2:
                    # Question/conversation starter
                    content = random.choice(conversation_starters)
                elif message_type == 3:
                    # Response
                    content = random.choice(responses)
                elif message_type == 4:
                    # Expression
                    content = random.choice(expressions)
                else:
                    # Random sentence
                    content = fake.sentence()
                
                # Create the message
                message = ChatMessage.objects.create(
                    room=room,
                    sender=sender,
                    content=content,
                    timestamp=message_date,
                    is_read=True  # Mark as read since these are historical messages
                )
                
                created_count += 1
                
                if (i + 1) % 100 == 0 or i + 1 == messages_to_create:
                    self.stdout.write(f"Created {i + 1}/{messages_to_create} messages")
                    
            except Exception as e:
                logger.error(f"Error creating chat message: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error creating message {i+1}: {str(e)}"))
        
        # Create conversation threads (replies to messages)
        self.stdout.write("Creating conversation threads...")
        
        # Get all messages
        all_messages = list(ChatMessage.objects.all().order_by('timestamp'))
        
        # For some messages, create a thread of replies
        thread_count = min(len(all_messages) // 10, 20)  # Create up to 20 threads
        
        for _ in range(thread_count):
            try:
                # Pick a random message to start a thread
                starter_message = random.choice(all_messages)
                room = starter_message.room
                
                # Get participants who can reply
                participants = list(room.participants.all())
                if len(participants) < 2:
                    continue
                
                # Create 2-5 replies in this thread
                reply_count = random.randint(2, 5)
                
                for j in range(reply_count):
                    # Select a sender different from the last message
                    sender = random.choice([u for u in participants if u != starter_message.sender])
                    
                    # Generate reply timestamp (after the starter message)
                    reply_date = starter_message.timestamp + timedelta(
                        minutes=random.randint(1, 30)
                    )
                    
                    # Generate reply content
                    if j == 0:
                        # First reply often responds directly
                        content = random.choice(responses) + " " + fake.sentence()
                    else:
                        # Subsequent replies
                        content = fake.sentence()
                    
                    # Create the reply message
                    reply = ChatMessage.objects.create(
                        room=room,
                        sender=sender,
                        content=content,
                        timestamp=reply_date,
                        is_read=True
                    )
                    
                    created_count += 1
                    starter_message = reply  # For the next reply in the thread
                
            except Exception as e:
                logger.error(f"Error creating reply thread: {str(e)}")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created {created_count} chat messages in {len(all_rooms)} rooms"))
        self.stdout.write(self.style.SUCCESS(f"Community Chat room has {ChatMessage.objects.filter(room=community_room).count()} messages")) 