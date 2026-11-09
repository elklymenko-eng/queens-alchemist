"""Free Telegram onboarding choices. Archetypes are reflective metaphors, not a validated test."""
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

PATHS = ["Decode my love patterns", "Explore my inner archetypes", "Create my Love Vision", "Ask my own question"]
ARCHETYPE_PATHS = ["Feminine archetypes", "Masculine archetypes"]
STATUS = ["Single and looking for love", "Dating or exploring connections", "In a relationship", "Healing or starting over", "It's complicated"]
GENDER = ["Woman", "Man", "Nonbinary / another identity", "Prefer not to say"]
PATTERNS = [
    "I keep attracting people who can't fully meet me",
    "I give more than I receive",
    "The people I want don't seem to choose me",
    "I struggle to create or sustain attraction",
    "I want closeness, but something holds me back",
    "I keep experiencing conflict or disconnection",
    "I'm not sure what my pattern is yet",
]
REACTIONS = [
    "I overthink and seek reassurance",
    "I try harder, give more, or take charge",
    "I pull away, shut down, or protect myself",
    "I get frustrated, critical, or confrontational",
    "I stay hopeful and overlook warning signs",
    "It depends / I'm not sure",
]
QUIZZES = {
 "feminine": [
 ("When you feel most alive and naturally yourself, what comes most easily?", [
 "Expressing affection, pleasure, and sensuality", "Wonder, imagination, and openness to delight",
 "Caring for people and helping them feel supported", "Taking action and handling challenges",
 "Listening to intuition and noticing what others miss", "Seeking freedom and new experiences",
 "Bringing steadiness, discernment, and generosity", "Finding humor and lightness in life"]),
 ("What do you most long to experience in love?", [
 "Passion, pleasure, and intimate connection", "Being delighted in, cherished, and adored",
 "A warm bond of mutual care", "Respect, autonomy, and teamwork",
 "Soulful understanding and depth", "Adventure, authenticity, and freedom",
 "Security, mutual devotion, and generosity", "Laughter, friendship, and play"]),
 ("When you feel hurt or insecure, what do you sometimes do?", [
 "Try to become more desirable", "Look for reassurance or someone to rescue me",
 "Give more, help more, or fix things", "Take control or do everything myself",
 "Retreat into thought or spiritual explanations", "Escape, rebel, or run from the situation",
 "Become rigid, controlling, or emotionally distant", "Joke, distract, or act as if it doesn't matter"]),
 ("What do people tend to appreciate about you?", [
 "Warmth, passion, and appreciation of beauty", "Optimism and openness",
 "Compassion and care", "Courage and reliability",
 "Insight and intuition", "Originality and adventurous spirit",
 "Discernment and grounded presence", "Humor and the ability to lighten the mood"]),
 ("What would you most like to practice now?", [
 "Enjoying desire without needing validation", "Receiving love without losing my agency",
 "Caring without sacrificing myself", "Letting myself soften and accept support",
 "Staying connected while trusting my wisdom", "Honoring freedom without fleeing intimacy",
 "Leading my life without controlling everything", "Being playful while staying emotionally present"]),
 ],
 "masculine": [
 ("When you're at your best, what comes most naturally?", [
 "Leading with calm generosity", "Exploring challenges and discovering my potential",
 "Acting decisively and protecting what matters", "Seeing patterns and finding creative solutions",
 "Connecting through affection and passion", "Bringing humor and spontaneity"]),
 ("What motivates you most right now?", [
 "Building something meaningful for others", "Developing my abilities and achieving goals",
 "Overcoming challenges and honoring my values", "Understanding life and creating change",
 "Intimacy, beauty, and deep connection", "Freedom, adventure, and shared laughter"]),
 ("When you feel inadequate or rejected, what sometimes happens?", [
 "I control too much or avoid responsibility", "I overprove myself or feel defeated",
 "I become combative, rigid, or avoid confrontation", "I overanalyze or detach from emotion",
 "I seek validation or disconnect from feeling", "I use jokes or distraction to avoid vulnerability"]),
 ("What do others often appreciate about you?", [
 "Steadiness and generosity", "Ambition and willingness to learn",
 "Courage and follow-through", "Perspective and creativity",
 "Tenderness and emotional depth", "Humor and lightheartedness"]),
 ("What would you most like to strengthen?", [
 "Leading without controlling", "Building confidence without proving my worth",
 "Being strong without becoming rigid", "Using wisdom while staying connected to my heart",
 "Loving deeply without losing my center", "Being playful while honoring commitments"]),
 ],
}
ARCHETYPES = {
 "feminine":["Lover","Princess","Mother","Warrior","Priestess","Wild Woman","Queen","Jester"],
 "masculine":["King","Prince","Warrior","Magician","Lover","Jester"]
}
def markup(options, prefix, selected=(), multi=False, back=False):
    rows=[]
    for i, label in enumerate(options):
        mark=("✓ " if i in selected else "□ ") if multi else ""
        rows.append([InlineKeyboardButton(mark+label,callback_data=f"ob:{prefix}:{i}")])
    if multi:
        rows.append([InlineKeyboardButton("Continue",callback_data="ob:patternnext:0")])

    if back:
        rows.append([InlineKeyboardButton("Back to pathways",callback_data="ob:home:0")])
    return InlineKeyboardMarkup(rows)
SHORT_CHOICES = {"feminine":[["Affection and pleasure","Wonder and imagination","Caring for others","Taking action","Intuition and insight","Freedom and adventure","Calm discernment","Humor and play"],["Passion and intimacy","To be cherished","Mutual care","Respect and autonomy","Soulful depth","Freedom and adventure","Secure devotion","Laughter and play"],["Try to be desirable","Seek reassurance","Give or fix more","Take control","Retreat into thought","Escape or rebel","Become distant","Joke it away"],["Warmth and passion","Optimism","Compassion","Courage","Intuition","Adventurous spirit","Discernment","Humor"]],"masculine":[["Calm leadership","Explore my potential","Courage and action","Creative solutions","Affection and passion","Humor and spontaneity"],["Build something meaningful","Develop my abilities","Overcome challenges","Understand and create","Deep connection","Freedom and laughter"],["Control or withdraw","Overprove myself","Fight or avoid conflict","Overanalyze","Seek validation","Hide behind humor"],["Steadiness","Ambition","Courage","Creativity","Tenderness","Humor"]]}
def quiz_question(kind, step):
    prompt, original = QUIZZES[kind][step]
    return prompt, SHORT_CHOICES[kind][step] if step < 4 else original
def summarize(kind, answers):
    names=ARCHETYPES[kind]
    tally={name:0 for name in names}
    for i, choice in enumerate(answers):
        if isinstance(choice,int) and 0<=choice<len(names):
            tally[names[choice]]+=1
    return sorted(tally,key=lambda name:-tally[name])
