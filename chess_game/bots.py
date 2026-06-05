"""Central bot roster, avatar paths, and profile helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


BOT_ASSET_DIR = Path(__file__).resolve().parent / 'resources' / 'bot_avatars'


@dataclass(frozen=True)
class BotProfile:
    """Structured opponent/coach profile used by menus, games, and review."""

    id: str
    display_name: str
    rating: int | str
    avatar_path: str
    personality_type: str
    description: str
    dialogue_pool: dict[str, tuple[str, ...]]
    group: str
    color: str
    engine_strength: int | None = None
    is_coach: bool = False


def _avatar(filename: str) -> str:
    return str(BOT_ASSET_DIR / filename)


def _pool(
    intro: str,
    *,
    opening: str,
    capture: str,
    check: str,
    mistake: str,
    win: str,
    loss: str,
    draw: str = 'Fair result. I will take the half point.',
) -> dict[str, tuple[str, ...]]:
    return {
        'move': (intro,),
        'opening': (opening,),
        'capture': (capture,),
        'check': (check,),
        'mistake': (mistake,),
        'win': (win,),
        'loss': (loss,),
        'draw': (draw,),
    }


ALL_BOT_PROFILES: tuple[BotProfile, ...] = (
    BotProfile(
        id='timmy',
        display_name='Timmy',
        rating=100,
        avatar_path=_avatar('timmy.svg'),
        personality_type='friendly_child',
        description='Friendly child who loves moving random pieces and cheering for both sides.',
        dialogue_pool=_pool(
            'I picked a piece and gave it an adventure.',
            opening='This opening has a name? Cool.',
            capture='I got one! That counts as a plan.',
            check='Check! I saw that one.',
            mistake='Oops. That piece wanted a vacation.',
            win='That was fun. Can we play again?',
            loss='You played really good moves. Nice job.',
        ),
        group='Beginner',
        color='#5ca8ff',
    ),
    BotProfile(
        id='mia',
        display_name='Mia',
        rating=250,
        avatar_path=_avatar('mia.svg'),
        personality_type='beginner_student',
        description='Beginner student, excited to learn and happy to try new ideas.',
        dialogue_pool=_pool(
            'I am trying to remember: center, pieces, king safety.',
            opening='I practiced this first move yesterday.',
            capture='That capture felt important.',
            check='Check! I am writing that down.',
            mistake='I learned something from that one.',
            win='I did it! My notebook is getting a star.',
            loss='Good game. I know what I want to practice next.',
        ),
        group='Beginner',
        color='#6fbf73',
    ),
    BotProfile(
        id='martin',
        display_name='Martin',
        rating=400,
        avatar_path=_avatar('martin.svg'),
        personality_type='family_dad',
        description='Casual family dad who plays a relaxed game when he gets a minute.',
        dialogue_pool=_pool(
            'Just squeezing in one more move before dinner.',
            opening='Classic enough for a kitchen-table game.',
            capture='That piece was hanging around too long.',
            check='Check. Dad reflexes.',
            mistake='I may have played that between coffee sips.',
            win='Not bad for a casual game.',
            loss='Alright, you got me. Rematch after snacks.',
        ),
        group='Beginner',
        color='#a8754f',
    ),
    BotProfile(
        id='gary',
        display_name='Gary',
        rating=600,
        avatar_path=_avatar('gary.svg'),
        personality_type='office_worker',
        description='Office worker who sneaks in games during lunch breaks.',
        dialogue_pool=_pool(
            'I have exactly eleven minutes before my next meeting.',
            opening='This opening looks efficient. I like efficient.',
            capture='Captured and filed.',
            check='Check. Please respond by end of day.',
            mistake='That move was not in the quarterly plan.',
            win='Lunch break well spent.',
            loss='Back to spreadsheets. Good game.',
        ),
        group='Beginner',
        color='#5f8fbf',
    ),
    BotProfile(
        id='olivia',
        display_name='Olivia',
        rating=800,
        avatar_path=_avatar('olivia.svg'),
        personality_type='attacking_beginner',
        description='Tactical beginner who likes attacking and forcing moves.',
        dialogue_pool=_pool(
            'If there is a target, I am aiming at it.',
            opening='Fast development means faster attacks.',
            capture='That opens a lane. I like lanes.',
            check='Check. Pressure is the point.',
            mistake='I attacked first and asked questions later.',
            win='The attack landed.',
            loss='I went for it. You defended better.',
        ),
        group='Intermediate',
        color='#3e8c7d',
    ),
    BotProfile(
        id='ethan',
        display_name='Ethan',
        rating=1000,
        avatar_path=_avatar('ethan.svg'),
        personality_type='club_player',
        description='Club player with headphones, practical habits, and a steady rhythm.',
        dialogue_pool=_pool(
            'I have played this kind of position at the club.',
            opening='This line usually gives both sides chances.',
            capture='Clean capture. Keep the tempo.',
            check='Check. Time to calculate.',
            mistake='That was a little loose.',
            win='Solid game. The rhythm felt right.',
            loss='Good technique. I lost the thread there.',
        ),
        group='Intermediate',
        color='#6d7ed6',
    ),
    BotProfile(
        id='sarah',
        display_name='Sarah',
        rating=1200,
        avatar_path=_avatar('sarah.svg'),
        personality_type='positional_player',
        description='Positional player who values structure, patience, and small advantages.',
        dialogue_pool=_pool(
            'I am looking for the square that improves everything quietly.',
            opening='This structure tells us where the pieces belong.',
            capture='That exchange changes the pawn structure.',
            check='Check, but the position still matters after it.',
            mistake='That weakened more squares than it gained.',
            win='The small advantages added up.',
            loss='You disrupted my structure nicely.',
        ),
        group='Intermediate',
        color='#8a9aa6',
    ),
    BotProfile(
        id='victor',
        display_name='Victor',
        rating=1400,
        avatar_path=_avatar('victor.svg'),
        personality_type='aggressive_player',
        description='Aggressive player who prefers initiative and direct threats.',
        dialogue_pool=_pool(
            'Quiet positions are just attacks waiting to happen.',
            opening='Give me activity and I will take it from there.',
            capture='Material plus momentum. Good combination.',
            check='Check. Now the clock starts ticking.',
            mistake='That gave me a hook.',
            win='The initiative did its job.',
            loss='You absorbed the attack. Respect.',
        ),
        group='Advanced',
        color='#c65050',
    ),
    BotProfile(
        id='anna',
        display_name='Anna',
        rating=1600,
        avatar_path=_avatar('anna.svg'),
        personality_type='opening_enthusiast',
        description='Opening enthusiast who knows plans, move orders, and typical traps.',
        dialogue_pool=_pool(
            'The move order matters more than people think.',
            opening='Ah, a familiar branch. Now the details begin.',
            capture='That capture changes the theory a bit.',
            check='Check, and also a useful move-order note.',
            mistake='That is exactly why this line is tricky.',
            win='Preparation helps when the board gets sharp.',
            loss='You took me out of book and made it count.',
        ),
        group='Advanced',
        color='#c79b52',
    ),
    BotProfile(
        id='leo',
        display_name='Leo',
        rating=1800,
        avatar_path=_avatar('leo.svg'),
        personality_type='tactical_expert',
        description='Tactical expert who trusts calculation and concrete forcing lines.',
        dialogue_pool=_pool(
            'Checks, captures, threats. Then we decide.',
            opening='A normal start, but tactics decide normal games too.',
            capture='That capture creates forcing moves.',
            check='Check. Candidate moves just got easier.',
            mistake='The tactic was hiding in plain sight.',
            win='Calculation paid the bill.',
            loss='You found the resource I missed.',
        ),
        group='Advanced',
        color='#7a78d7',
    ),
    BotProfile(
        id='sofia',
        display_name='Sofia',
        rating=2000,
        avatar_path=_avatar('sofia.svg'),
        personality_type='calm_strategist',
        description='Calm strategist who improves pieces before forcing the issue.',
        dialogue_pool=_pool(
            'No rush. The position will tell us what it needs.',
            opening='This setup gives long-term plans to both sides.',
            capture='A useful transformation.',
            check='Check, but the follow-up is what matters.',
            mistake='That left a long-term weakness.',
            win='Quiet pressure became decisive.',
            loss='You changed the nature of the position well.',
        ),
        group='Master',
        color='#4f9f8f',
    ),
    BotProfile(
        id='coach_levy',
        display_name='Coach Levy',
        rating='Coach',
        avatar_path=_avatar('coach_levy.svg'),
        personality_type='supportive_coach',
        description='Instructional and supportive coach who explains ideas clearly.',
        dialogue_pool=_pool(
            'I will explain the ideas as we play.',
            opening='This is a good moment to connect opening moves to plans.',
            capture='Before capturing, ask what changes after the trade.',
            check='Checks are forcing, so calculate the reply too.',
            mistake='No stress. Let us find the habit behind that mistake.',
            win='Nice finish. Now we can review how you built it.',
            loss='We will turn the loss into one clear lesson.',
        ),
        group='Coach',
        color='#c73d3d',
        engine_strength=1300,
        is_coach=True,
    ),
    BotProfile(
        id='professor_stone',
        display_name='Professor Stone',
        rating='Coach',
        avatar_path=_avatar('professor_stone.svg'),
        personality_type='positional_coach',
        description='Deep positional coach focused on structure, plans, and endgames.',
        dialogue_pool=_pool(
            'We will study the position patiently.',
            opening='The opening has already shaped the pawn skeleton.',
            capture='Every exchange leaves a footprint in the structure.',
            check='A check is useful when the resulting position is also useful.',
            mistake='This is a structural lesson, not just a one-move issue.',
            win='A good conversion begins with understanding the position.',
            loss='The result gives us a useful positional theme to study.',
        ),
        group='Coach',
        color='#7d8790',
        engine_strength=1800,
        is_coach=True,
    ),
    BotProfile(
        id='captain_gambit',
        display_name='Captain Gambit',
        rating=2200,
        avatar_path=_avatar('captain_gambit.svg'),
        personality_type='gambit_specialist',
        description='Adventurous gambit specialist who spends material for initiative.',
        dialogue_pool=_pool(
            'Material is only ballast if the attack is sailing.',
            opening='A sharp course. Excellent.',
            capture='Take it if you dare. The files are opening.',
            check='Check from open waters.',
            mistake='That gave my attack a tailwind.',
            win='The gambit reached shore.',
            loss='You weathered the storm.',
        ),
        group='Master',
        color='#9a6040',
    ),
    BotProfile(
        id='the_engineer',
        display_name='The Engineer',
        rating=2400,
        avatar_path=_avatar('the_engineer.svg'),
        personality_type='calculation_machine',
        description='Modern engineer with clean calculation and minimal emotion.',
        dialogue_pool=_pool(
            'Candidate line selected. Variance acceptable.',
            opening='Opening schema loaded.',
            capture='Material transaction approved.',
            check='Forcing sequence detected.',
            mistake='Error margin increased.',
            win='Process complete.',
            loss='Model updated.',
        ),
        group='Master',
        color='#4c8799',
    ),
    BotProfile(
        id='grandmaster_vera',
        display_name='Grandmaster Vera',
        rating=2500,
        avatar_path=_avatar('grandmaster_vera.svg'),
        personality_type='elite_technician',
        description='Elite technician who converts small edges with serious precision.',
        dialogue_pool=_pool(
            'Accuracy first. Style can wait.',
            opening='This line is playable, but only with precision.',
            capture='A clean technical decision.',
            check='The check is only part of the conversion.',
            mistake='At this level, that concession matters.',
            win='The conversion was controlled.',
            loss='You gave me no practical chances.',
        ),
        group='Master',
        color='#6e6b76',
    ),
    BotProfile(
        id='the_monk',
        display_name='The Monk',
        rating=2600,
        avatar_path=_avatar('the_monk.svg'),
        personality_type='defensive_expert',
        description='Calm defensive expert who waits for overextension.',
        dialogue_pool=_pool(
            'Stillness is also a move.',
            opening='A peaceful shell can hide sharp teeth.',
            capture='Only what is necessary.',
            check='The king breathes. The defense holds.',
            mistake='Impatience creates entry squares.',
            win='The position answered in time.',
            loss='Your pressure was disciplined.',
        ),
        group='Master',
        color='#9b7b52',
    ),
    BotProfile(
        id='the_machine',
        display_name='The Machine',
        rating=2800,
        avatar_path=_avatar('the_machine.svg'),
        personality_type='robot_hybrid',
        description='Nearly emotionless opponent that plays with mechanical precision.',
        dialogue_pool=_pool(
            'Position evaluated.',
            opening='Database path acceptable.',
            capture='Material delta updated.',
            check='King safety constraint applied.',
            mistake='Suboptimal move recorded.',
            win='Result: win.',
            loss='Unexpected result.',
            draw='Result: draw.',
        ),
        group='Master',
        color='#7a858a',
    ),
    BotProfile(
        id='oracle',
        display_name='Oracle',
        rating=3000,
        avatar_path=_avatar('oracle.svg'),
        personality_type='mysterious_oracle',
        description='Mysterious opponent with cryptic comments and glowing confidence.',
        dialogue_pool=_pool(
            'The board has already whispered three futures.',
            opening='An old path, newly walked.',
            capture='A sacrifice to certainty.',
            check='The crown hears the warning.',
            mistake='A door opened where none should be.',
            win='The prophecy was quiet, but exact.',
            loss='Even visions can be overturned.',
        ),
        group='Master',
        color='#8666d1',
    ),
    BotProfile(
        id='stockfish_prime',
        display_name='Stockfish Prime',
        rating='Engine',
        avatar_path=_avatar('stockfish_prime.svg'),
        personality_type='engine_mascot',
        description='Stylized engine mascot for serious analysis and maximum-strength play.',
        dialogue_pool=_pool(
            'Depth increasing.',
            opening='Book complete. Calculation begins.',
            capture='Capture evaluated.',
            check='Forcing line found.',
            mistake='Evaluation swing detected.',
            win='Engine result confirmed.',
            loss='Human result accepted.',
            draw='Tablebase mood: balanced.',
        ),
        group='Master',
        color='#3c9fc7',
        engine_strength=3000,
    ),
)


def engine_strength(profile: BotProfile | dict[str, Any]) -> int:
    """Return the numeric strength the local engine should use for a profile."""

    if isinstance(profile, dict):
        return int(profile.get('engine_strength') or profile.get('elo') or 1000)
    return int(profile.engine_strength or profile.rating)


def rating_label(profile: BotProfile | dict[str, Any]) -> str:
    """Human-readable rating label."""

    rating = profile.get('rating') if isinstance(profile, dict) else profile.rating
    return f'{rating} Elo' if isinstance(rating, int) else str(rating)


def profile_to_dict(profile: BotProfile) -> dict[str, Any]:
    """Compatibility layer for existing UI code that still expects dictionaries."""

    first_line = profile.dialogue_pool.get('move', ('Ready when you are.',))[0]
    return {
        'id': profile.id,
        'display_name': profile.display_name,
        'name': profile.display_name,
        'rating': profile.rating,
        'rating_label': rating_label(profile),
        'elo': engine_strength(profile),
        'engine_strength': engine_strength(profile),
        'avatar_path': profile.avatar_path,
        'personality_type': profile.personality_type,
        'description': profile.description,
        'dialogue': first_line,
        'dialogue_pool': profile.dialogue_pool,
        'group': profile.group,
        'color': profile.color,
        'is_coach': profile.is_coach,
    }


BOT_PROFILES = tuple(profile_to_dict(profile) for profile in ALL_BOT_PROFILES if not profile.is_coach)
COACH_PROFILES = tuple(profile_to_dict(profile) for profile in ALL_BOT_PROFILES if profile.is_coach)
BOT_PROFILE_BY_ID = {profile.id: profile for profile in ALL_BOT_PROFILES}
