import os
import re

from . import databases
from .address import *
from .core_rando import BOSS_SLOTS

from f4c import encode_text

WACKY_CHALLENGES = {
    'musical'           : 'Final Fantasy IV:\nThe Musical',
    'bodyguard'         : 'The Bodyguard',
    'fistfight'         : 'Fist Fight',
    'omnidextrous'      : 'Omnidextrous',
    'biggermagnet'      : 'A Much\nBigger Magnet',
    'sixleggedrace'     : 'Six-Legged Race',
    'floorislava'       : 'The Floor Is\nMade Of Lava',
    'neatfreak'         : 'Neat Freak',
    'timeismoney'       : 'Time is Money',
    'nightmode'         : 'Night Mode',
    'mysteryjuice'      : 'Mystery Juice',
    'misspelled'        : 'Misspelled',
    'enemyunknown'      : 'Enemy Unknown',
    'kleptomania'       : 'Kleptomania',
    'darts'             : 'World Championship\nof Darts',
    'unstackable'       : 'Unstackable',
    'menarepigs'        : 'Men Are Pigs',
    'skywarriors'       : 'The Sky Warriors',
    'zombies'           : 'Zombies!!!',
    'afflicted'         : 'Afflicted',
    'batman'            : 'Holy Onomatopoeias,\nBatman!',
    'battlescars'       : 'Battle Scars',
    'imaginarynumbers'  : 'Imaginary Numbers',
    'tellahmaneuver'    : 'The Tellah\nManeuver',
    '3point'            : 'The 3-Point System',
    'friendlyfire'      : 'Friendly Fire',
    'payablegolbez'     : 'Payable Golbez',
    'gottagofast'       : 'Gotta Go Fast',
    'worthfighting'     : 'Something Worth\nFighting For',
    'saveusbigchocobo'  : 'Save Us,\nBig Chocobo!',
    'isthisrandomized'  : 'Is This Even\nRandomized?',
    'forwardisback'     : 'Forward is\nthe New Back',
    'dropitlikeitshot'  : 'Drop It Like It\'s Hot',
    'whatsmygear'       : 'What\'s My\nGear Again?',
    'scrambledstats'    : 'Scrambled Stats',
    'advertising'       : 'Truth in\nAdvertising',
}

WACKY_ROM_ADDRESS = BusAddress(0x268000)
WACKY_RAM_ADDRESS = BusAddress(0x7e1660)

def setup(env):
    wacky_challenge = None
    if env.options.test_settings.get('wacky', None):
        wacky_challenge = env.options.test_settings['wacky']
    elif env.options.flags.has('-wacky:random'):
        wacky_challenge = env.rnd.choice(list(WACKY_CHALLENGES))
    else:
        wacky_challenge = env.options.flags.get_suffix('-wacky:')

    if wacky_challenge:
        env.meta['wacky_challenge'] = wacky_challenge
        setup_func = globals().get(f'setup_{wacky_challenge}')
        if setup_func:
            setup_func(env)

def apply(env):
    wacky_challenge = env.meta.get('wacky_challenge', None)
    if wacky_challenge:
        env.add_file('scripts/wacky/wacky_common.f4c')

        # apply script of the same name, if it exists
        script_filename = f'scripts/wacky/{wacky_challenge}.f4c'
        if os.path.isfile(os.path.join(os.path.dirname(__file__), script_filename)):
            env.add_file(script_filename)

        apply_func = globals().get(f'apply_{wacky_challenge}', None)
        if apply_func:
            apply_func(env)

        env.add_substitution('intro disable', '')

        text = WACKY_CHALLENGES[wacky_challenge]
        centered_text = '\n'.join([line.center(26).upper().rstrip() for line in text.split('\n')])
        env.add_substitution('wacky challenge title', centered_text)
        env.add_substitution('wacky_rom_data_addr', f'{WACKY_ROM_ADDRESS.get_bus():06X}')
        env.add_toggle('wacky_challenge_enabled')

        env.add_script(f'''
            msfpatch {{ 
                .def Wacky__ROMData ${WACKY_ROM_ADDRESS.get_bus():06x} 
                .def Wacky__RAM     ${WACKY_RAM_ADDRESS.get_bus():06x}
                }}
        ''')

        env.spoilers.add_table('WACKY CHALLENGE', [[text.replace('\n', ' ')]], public=env.options.flags.has_any('-spoil:all', '-spoil:misc'))


def apply_musical(env):
    env.add_substitution('wacky_fightcommandreplacement', '#$08')

def apply_bodyguard(env):
    # need substitution to mark all characters as cover-capable
    env.add_toggle('wacky_all_characters_cover')
    env.add_toggle('wacky_cover_check')

def apply_fistfight(env):
    env.add_toggle('wacky_all_characters_ambidextrous')
    # change claws to be universally equippable, all other weapons not
    for item_id in range(0x01, 0x60):
        if item_id < 0x07:
            # is claw
            eqp_byte = 0x00
        elif item_id not in [0x3E, 0x46]: # ignore Spoon and custom weapon
            eqp_byte = 0x1F
        else:
            eqp_byte = None

        if eqp_byte is not None:
            env.add_binary(UnheaderedAddress(0x79106 + (0x08 * item_id)), [eqp_byte], as_script=True)

def apply_omnidextrous(env):
    env.add_toggle('wacky_all_characters_ambidextrous')
    env.add_toggle('wacky_omnidextrous')

def apply_whatsmygear(env):
    # this function can't be called from where it lives in assets.item_info.generate.py, so repeat it here
    def ff4strlen(text):
        shrunken_text = re.sub(r'\[.*?\]', '*', text)
        return len(shrunken_text)

    STAT_NAMES = ['STR', 'AGI', 'VIT', 'WIS', 'WIL']
    BYTE_DICT = {
        0 : (3, 0),
        1 : (5, 0),
        2 : (10, 0),
        3 : (15, 0),
        4 : (5, 5),   # use positive second entry for the four negatives because we're writing strings
        5 : (10, 10), #
        6 : (15, 15), #
        7 : (5, 10)   #
        }

    gear_description_bytes = {} # dictionary with keys = item_ids, values = replacement description lines 2-4 in bytes

    # starting at 0 means we're including "no weapon" and "no armour"; could ignore 0x00 and 0x60 otherwise
    for i in range(0,176): 
        # patch each weapon/armour with a new stats byte, chosen uniformly at random
        # skip 0x00 (empty weapon) and 0x60 (empty armour) for now; descriptions require hooks specifically for equipping different slots
        if i in [0,96]:
            continue
        newstatbyte = env.rnd.randrange(0,256)
        env.add_binary(UnheaderedAddress(0x079100 + 0x07 + i * 0x08), [newstatbyte], as_script=True)

        # write replacement text descriptions for the Select info box
        # every weapon/armour gets a "stat-change-only" style box, with the info on the third row
        stats = newstatbyte & 0xF8 # just the stats bits
        pair = newstatbyte & 0x07 # just the pair bits

        if stats == 0x00:
            if pair & 0x04: 
                # all stats decrease
                bonus = BYTE_DICT[pair][1]
                stats_text = '[$c7]'.join(STAT_NAMES) + f'[$c2]{bonus}.'
                filler = ' ' * (27-ff4strlen(stats_text))
            else: 
                # no stat changes, so write 'no stat changes.'
                stats_text = 'no stat changes.'
                filler = ' ' * (27-ff4strlen(stats_text))
        elif (stats == 0xF8) or not (pair & 0x04): 
            # all or some stats increase, no stats decrease
            bonus = BYTE_DICT[pair][0]
            plus_list = [STAT_NAMES[7-b] for b in range(7,2,-1) if (stats >> b) & 0x01]
            stats_text = '[$c7]'.join(plus_list) + f'[$cb]{bonus}.'
            filler = ' ' * (27-ff4strlen(stats_text))
        else:
            plus_bonus = BYTE_DICT[pair][0]
            plus_list = [STAT_NAMES[7-b] for b in range(7,2,-1) if (stats >> b) & 0x01]
            minus_bonus = BYTE_DICT[pair][1]
            minus_list = [STAT_NAMES[7-b] for b in range(7,2,-1) if not ((stats >> b) & 0x01)]
            stats_text = '[$c7]'.join(plus_list) + f'[$cb]{plus_bonus}' + '[$c9] ' + '[$c7]'.join(minus_list) + f'[$c2]{minus_bonus}.'
            filler = ' ' * (27-ff4strlen(stats_text))
        
        # when we allow multiple wackies, usual_row should read '[$00][$fa]As advertised[$c9] except      [$fb][$00][$00]'
        # when What's My Gear Again? interacts with Truth in Advertising (i.e. What's My Gear Again? takes priority).
        usual_row = '[$00][$fa]As normal[$c9] except          [$fb][$00][$00]'
        stats_row = f'[$00][$fa]{stats_text}{filler}[$fb][$00][$00]'
        blank_row = '[$00][$fa]                           [$fb][$00][$00]'
        
        if ff4strlen(stats_row) != 32: # really shouldn't need this check
            raise Exception(f"Unexpected line length {ff4strlen(stats_row)} : {stats_row}")
        gear_description_bytes[i] = encode_text(usual_row + stats_row + blank_row)

    # pass the gear_descriptions to env in order to have generator.py make the replacements while it does the other descriptions
    env.meta['wacky_gear_descriptions'] = gear_description_bytes

def apply_scrambledstats(env):
    statslist = [0, 1, 2, 3, 4] # Str, Agi, Vit, Wis, Wil
    env.rnd.shuffle(statslist)
    statsdict = {stat : statslist[i] for stat, i in zip(['STR', 'AGI', 'VIT', 'WIS', 'WIL'], [0, 1, 2, 3, 4])}

    env.add_substitution('3966 STR substitute', f'{102+statsdict["STR"]:02X}')
    env.add_substitution('3967 AGI substitute', f'{102+statsdict["AGI"]:02X}')
    env.add_substitution('2015 AGI substitute', f'{20+statsdict["AGI"]:02X}')
    env.add_substitution('wacky scrambled stats agi address', f'    .def  CharAgilityAddress  $20{20+statsdict["AGI"]:02X}')
    env.add_substitution('3968 VIT substitute', f'{102+statsdict["VIT"]:02X}')
    env.add_substitution('2716 VIT substitute', f'{20+statsdict["VIT"]:02X}')
    env.add_substitution('2016 VIT substitute', f'{20+statsdict["VIT"]:02X}')
    env.add_substitution('3969 WIS substitute', f'{102+statsdict["WIS"]:02X}')
    env.add_substitution('2017 WIS substitute', f'{20+statsdict["WIS"]:02X}')
    env.add_substitution('ldx WIS offset', f'ldx #$00{statsdict["WIS"]:02X}')
    env.add_substitution('3970 WIL substitute', f'{102+statsdict["WIL"]:02X}')
    env.add_substitution('2018 WIL substitute', f'{20+statsdict["WIL"]:02X}')
    env.add_substitution('ldx WIL offset', f'ldx #$00{statsdict["WIL"]:02X}')

    env.add_toggle('wacky_scrambledstats')
    env.add_file('scripts/wacky/scrambledstats.f4c')

def apply_sixleggedrace(env):
    env.add_toggle('wacky_challenge_show_detail')

def apply_neatfreak(env):
    env.add_toggle('wacky_neatfreak')

def apply_timeismoney(env):
    env.add_file('scripts/sell_zero.f4c')

def setup_mysteryjuice(env):
    juices = '''
        Sweet Sour Bitter Salty Spicy Fruity Minty Milky Creamy Meaty Tart Savory Buttery Purple Green Brown Clear Glowing Hot Cold Lukewarm Slushy Cloudy Smooth Gooey Lumpy Juicy Crunchy Chunky Muddy Runny Chewy Steamy Frothy Inky Murky Tasty Fancy Foamy Zesty Smoky Dry Wet Bubbly Fizzy Pungent Chalky Stringy Thick Gritty Gross Neon Bold Simple Shiny
        '''.split()
    env.rnd.shuffle(juices)
    
    JUICE_ITEMS = list(range(0xB0, 0xE2)) + [0xE4, 0xE5, 0xEB, 0xED]
    juice_mapping = {}
    juice_prices = env.meta.setdefault('altered_item_prices', {})
    for item_id in JUICE_ITEMS:
        juice_mapping[item_id] = '[potion]' + juices.pop()
        juice_prices[item_id] = 1000

    env.meta.setdefault('altered_item_names', {}).update(juice_mapping)
    env.meta['wacky_juices'] = juice_mapping

def apply_mysteryjuice(env):
    ITEM_DESCRIPTION = (
        [0x00, 0xFA] + ([0xFF] * 27) + [0xFB, 0x00, 0x00] +
        [0x00, 0xFA] + ([0xFF] * 12) + ([0xC5] * 3) + ([0xFF] * 12) + [0xFB, 0x00, 0x00] +
        [0x00, 0xFA] + ([0xFF] * 27) + [0xFB, 0x00, 0x00] +
        [0x00, 0xFA] + ([0xFF] * 27) + [0xFB, 0x00, 0x00]
        )
    for item_id in env.meta['wacky_juices']:
        env.add_script(f'''
            text(item name ${item_id:02X}) {{{env.meta['wacky_juices'][item_id]}}}
        ''')
        env.meta.setdefault('item_description_overrides', {})[item_id] = ITEM_DESCRIPTION

def apply_misspelled(env):
    spells_dbview = databases.get_spells_dbview()
    remappable_spells = spells_dbview.find_all(lambda sp: (sp.code >= 0x01 and sp.code <= 0x47 and sp.code not in [0x40,0x41]))
    shuffled_spells = list(remappable_spells)
    env.rnd.shuffle(shuffled_spells)

    # get summon effects and pair them with their summon spell
    raw_summon_effects = spells_dbview.find_all(lambda sp: (sp.code >=0x4D and sp.code <= 0x5D))
    summon_effects_list = list(raw_summon_effects)
    summon_effects_linked = {}
    for effect in summon_effects_list:
        # three Asuna effects
        if (effect.code in [0x5A, 0x5B, 0x5C]):
            try:
                summon_effects_linked[0x3E].append(effect)
            except:
                summon_effects_linked[0x3E] = [effect]
        # bahamut
        elif (effect.code == 0x5D):
            summon_effects_linked[0x3F] = effect
        else:
            summon_effects_linked[effect.code - 0x1C] = effect


    pairings = zip(remappable_spells, shuffled_spells)
    remap_data = [0x00] * 0x100
    for pair in pairings:
        remap_data[pair[0].code] = pair[1].code
        env.add_script(f'''
            text(spell name {pair[1].const}) {{{pair[0].name}}}
        ''')
        # rename effects of summon spells as well
        if (pair[1].code >= 0x31 and pair[1].code <= 0x3D):
            env.add_script(f'''
                text(spell name ${pair[1].code + 0x1C:02X}) {{{pair[0].name}}}
            ''')
        elif (pair[1].code == 0x3E):
            # three Asura effects
            env.add_script(f'''
                text(spell name $5A) {{{pair[0].name}}}
                text(spell name $5B) {{{pair[0].name}}}
                text(spell name $5C) {{{pair[0].name}}}
            ''')
        elif (pair[1].code == 0x3F):
            # bahamut
            env.add_script(f'''
                text(spell name $5D) {{{pair[0].name}}}
            ''')
        
        # trade MP costs
        env.add_binary(
            BusAddress(0xF97A5 + (0x06 * pair[1].code)),
            [(pair[0].data[5] & 0x7F) | (pair[1].data[5] & 0x80)],
            as_script=True
        )

        # trade summon effect MP costs as well
        if (pair[1].code >= 0x31 and pair[1].code <= 0x3D):
            env.add_binary(
                BusAddress(0xF97A5 + (0x06 * (pair[1].code + 0x1C))),
                [(pair[0].data[5] & 0x7F) | (summon_effects_linked[pair[1].code].data[5] & 0x80)],
                as_script=True
            )
        elif (pair[1].code == 0x3E):
            # three Asuna effects
            env.add_binary(
                BusAddress(0xF97A5 + (0x06 * 0x5A)),
                [(pair[0].data[5] & 0x7F) | (summon_effects_linked[0x3E][0].data[5] & 0x80)],
                as_script=True
            )
            env.add_binary(
                BusAddress(0xF97A5 + (0x06 * 0x5B)),
                [(pair[0].data[5] & 0x7F) | (summon_effects_linked[0x3E][1].data[5] & 0x80)],
                as_script=True
            )
            env.add_binary(
            BusAddress(0xF97A5 + (0x06 * 0x5C)),
            [(pair[0].data[5] & 0x7F) | (summon_effects_linked[0x3E][2].data[5] & 0x80)],
            as_script=True
            )
        elif (pair[1].code == 0x3F):
            # bahamut
            env.add_binary(
            BusAddress(0xF97A5 + (0x06 * 0x5D)),
            [(pair[0].data[5] & 0x7F) | (summon_effects_linked[0x3F].data[5] & 0x80)],
            as_script=True
            )   

    

    env.add_binary(WACKY_ROM_ADDRESS, remap_data, as_script=True)
    env.add_toggle('wacky_misspelled')

def apply_kleptomania(env):
    VANILLA_MONSTER_LEVELS = [3,5,5,4,5,20,19,4,6,5,5,6,6,6,6,6,7,23,7,7,8,8,9,36,16,25,12,9,21,9,11,14,97,19,10,10,11,12,23,48,15,8,8,16,12,15,16,13,16,31,17,20,20,79,17,17,15,18,18,34,20,20,35,15,27,20,20,21,21,41,22,22,41,25,44,49,27,26,35,32,28,79,28,29,39,14,14,28,25,29,29,32,32,33,34,43,26,27,34,32,30,31,53,31,50,33,39,96,40,35,67,42,23,36,37,45,43,23,39,32,40,48,26,58,40,40,44,48,98,30,50,98,36,37,96,16,60,60,61,34,97,40,45,54,99,61,97,32,99,99,30,71,99,61,62,98,97,54,98,99,99,10,10,2,15,15,15,9,9,9,16,15,15,16,16,16,26,36,31,47,31,7,32,32,25,15,15,50,53,79,47,37,63,79,79,19,5,48,48,63,96,96,47,5,31,17,1,1,1,1,15,15,47,79,63,63,63,1,31,31,31,31,1,3]
    items_dbview = databases.get_items_dbview()
    available_weapons = items_dbview.find_all(lambda it: it.category == 'weapon' and it.tier >= 2 and it.tier <= 8)
    available_armor = items_dbview.find_all(lambda it: it.category == 'armor' and it.tier >= 1 and it.tier <= 8)
    available_weapons.sort(key=lambda it: it.tier)
    available_armor.sort(key=lambda it: it.tier)

    is_armor_queue = [bool((i % 5) < 2) for i in range(len(VANILLA_MONSTER_LEVELS))]
    env.rnd.shuffle(is_armor_queue)

    equipment_bytes = []
    VARIATION = 0.05
    for monster_id,monster_level in enumerate(VANILLA_MONSTER_LEVELS):
        if is_armor_queue[monster_id]:
            available_items = available_armor
            scale = 30.0
        else:
            available_items = available_weapons
            scale = 50.0
        normalized_level = max(VARIATION, min(1.0 - VARIATION, monster_level / scale))

        variated_level = normalized_level + (env.rnd.random() - 0.50) * (VARIATION * 2.0)
        index = max(0, min(len(available_items) - 1, int(len(available_items) * variated_level)))
        item = available_items[index]
        equipment_bytes.append(item.code)

    env.add_binary(WACKY_ROM_ADDRESS, equipment_bytes, as_script=True)        

def apply_darts(env):
    env.add_substitution('wacky_fightcommandreplacement', '#$16')

def apply_unstackable(env):
    env.add_toggle('wacky_unstackable')
    env.add_toggle('wacky_initialize_axtor_hook')

def apply_menarepigs(env):
    env.add_toggle('wacky_initialize_axtor_hook')
    env.add_file('scripts/wacky/status_enforcement.f4c')
    env.add_toggle('wacky_status_enforcement_uses_job')

def apply_skywarriors(env):
    env.add_toggle('wacky_initialize_axtor_hook')
    env.add_file('scripts/wacky/status_enforcement.f4c')

def apply_zombies(env):
    env.add_file('scripts/wacky/status_enforcement.f4c')
    env.add_toggle('wacky_initialize_axtor_hook')
    env.add_toggle('wacky_status_enforcement_uses_slot')
    env.add_toggle('wacky_status_enforcement_uses_battleinit_context')
    env.add_toggle('wacky_status_enforcement_uses_battle_context')
    env.add_toggle('wacky_post_battle_hook')

def apply_afflicted(env):
    env.add_file('scripts/wacky/status_enforcement.f4c')
    env.add_toggle('wacky_initialize_axtor_hook')
    env.add_toggle('wacky_status_enforcement_uses_axtor')
    env.add_toggle('wacky_status_enforcement_uses_battleinit_context')
    env.add_toggle('wacky_spell_filter_hook')
    env.add_toggle('wacky_post_battle_hook')

    STATUSES = {
        'poison'  : [0x01, 0x00, 0x00, 0x00],
        'blind'   : [0x02, 0x00, 0x00, 0x00],
        'mute'    : [0x04, 0x00, 0x00, 0x00],
        'piggy'   : [0x08, 0x00, 0x00, 0x00],
        'mini'    : [0x10, 0x00, 0x00, 0x00],
        'toad'    : [0x20, 0x00, 0x00, 0x00],
        #'stone'   : [0x40, 0x00, 0x00, 0x00],
        'calcify' : [0x00, 0x01, 0x00, 0x00],
        'calcify2': [0x00, 0x02, 0x00, 0x00],
        'berserk' : [0x00, 0x04, 0x00, 0x00],
        'charm'   : [0x00, 0x08, 0x00, 0x00],
        #'sleep'   : [0x00, 0x10, 0x00, 0x00],
        #'stun'    : [0x00, 0x20, 0x00, 0x00],
        'float'   : [0x00, 0x40, 0x00, 0x00],
        'curse'   : [0x00, 0x80, 0x00, 0x00],
        'blink1'  : [0x00, 0x00, 0x00, 0x04],
        'blink2'  : [0x00, 0x00, 0x00, 0x08],
        'armor'   : [0x00, 0x00, 0x00, 0x10],
        'wall'    : [0x00, 0x00, 0x00, 0x20],
    }

    status_bytes = []
    for status in STATUSES:
        status_bytes.extend(STATUSES[status])    
    env.add_binary(WACKY_ROM_ADDRESS, status_bytes, as_script=True)

    rng_table = [env.rnd.randint(0, len(STATUSES) - 1) for i in range(0x200)]
    env.add_binary(WACKY_ROM_ADDRESS.offset(0x100), rng_table, as_script=True)


'''
def apply_afflicted_legacyversion(env):
    env.add_toggle('wacky_initialize_axtor_hook')
    env.add_file('scripts/wacky/status_enforcement.f4c')
    env.add_toggle('wacky_status_enforcement_uses_axtor')

    STATUSES = {
        'poison'  : [0x01, 0x00, 0x00, 0x00],
        'blind'   : [0x02, 0x00, 0x00, 0x00],
        'mute'    : [0x04, 0x00, 0x00, 0x00],
        'piggy'   : [0x08, 0x00, 0x00, 0x00],
        'mini'    : [0x10, 0x00, 0x00, 0x00],
        'toad'    : [0x20, 0x00, 0x00, 0x00],
        'calcify' : [0x00, 0x01, 0x00, 0x00],
        'calcify2': [0x00, 0x02, 0x00, 0x00],
        'berserk' : [0x00, 0x04, 0x00, 0x00],
        #'sleep'   : [0x00, 0x10, 0x00, 0x00],
        'float'   : [0x00, 0x40, 0x00, 0x00],
        'curse'   : [0x00, 0x80, 0x00, 0x00],
        'blink'   : [0x00, 0x00, 0x00, 0x08],
        'wall'    : [0x00, 0x00, 0x00, 0x20],
    }

    status_names = list(STATUSES)
    status_bytes = []
    for axtor_id in range(0x20):
        status = env.rnd.choice(status_names)
        status_bytes.extend(STATUSES[status])
    
    env.add_binary(WACKY_ROM_ADDRESS, status_bytes, as_script=True)
'''

def apply_battlescars(env):
    env.add_toggle('wacky_initialize_axtor_hook')
    env.add_toggle('wacky_post_battle_hook')

def apply_tellahmaneuver(env):
    env.add_toggle('wacky_omit_mp')

    # precalculate MP costs times 10
    spells_dbview = databases.get_spells_dbview()
    data = [0x00] * 0x400
    for spell_id in range(0x48):
        mp_cost = 10 * spells_dbview.find_one(lambda sp: sp.code == spell_id).mp
        data[spell_id] = mp_cost & 0xFF
        data[spell_id + 0x100] = (mp_cost >> 8) & 0xFF

    # also precalculate number * 10 in general
    for v in range(0x100):
        data[v + 0x200] = ((v * 10) & 0xFF)
        data[v + 0x300] = ((v * 10) >> 8) & 0xFF
    
    env.add_binary(WACKY_ROM_ADDRESS, data, as_script=True)

def apply_3point(env):
    env.add_toggle('wacky_initialize_axtor_hook')

    # change all MP costs to 1
    spells_dbview = databases.get_spells_dbview()
    for spell_id in range(0x48):
        spell = spells_dbview.find_one(lambda sp: sp.code == spell_id)
        if spell.mp > 0:
            env.add_binary(
                BusAddress(0xF97A5 + (0x06 * spell_id)),
                [(spell.data[5] & 0x80) | 0x01],
                as_script=True
            )
    for spell_id in range(0x4D, 0x5E):
        spell = spells_dbview.find_one(lambda sp: sp.code == spell_id)
        env.add_binary(
            BusAddress(0xF97A5 + (0x06 * spell_id)),
            [(spell.data[5] & 0x80) | 0x01],
            as_script=True
        )

def apply_friendlyfire(env):
    env.add_toggle('wacky_spell_filter_hook')
    env.add_file('scripts/wacky/spell_filter_hook.f4c')

def setup_payablegolbez(env):
    bribe_slots = BOSS_SLOTS.copy()
    env.meta['payablegolbez_slots'] = bribe_slots

def apply_payablegolbez(env):
    BOSS_SLOT_HPS = {
        'antlion_slot' : 1000,
        'asura_slot' : 23000,
        'bahamut_slot' : 37000,
        'baigan_slot' : 4200,
        'calbrena_slot' : 8524,
        'cpu_slot' : 24000,
        'darkelf_slot' : 5000,
        'darkimp_slot' : 597,
        'dlunar_slot' : 42000,
        'dmist_slot' : 465,
        'elements_slot' : 65000,
        'evilwall_slot' : 19000,
        'fabulgauntlet_slot' : 1880,
        'golbez_slot' : 3002,
        'guard_slot' : 400,
        'kainazzo_slot' : 4000,
        'karate_slot' : 4000,
        'kingqueen_slot' : 6000,
        'leviatan_slot' : 35000,
        'lugae_slot' : 18943,
        'magus_slot' : 9000,
        'milon_slot' : 2780,
        'milonz_slot' : 3000,
        'mirrorcecil_slot' : 1000,
        'mombomb_slot' : 1250,
        'octomamm_slot' : 2350,
        'odin_slot' : 20500,
        'officer_slot' : 302,
        'ogopogo_slot' : 37000,
        'paledim_slot' : 27300,
        'plague_slot' : 28000,
        'rubicant_slot' : 25200,
        'valvalis_slot' : 6000,
        'wyvern_slot' : 25000,
    }
    bribe_values = []
    bribe_slots = env.meta.get('payablegolbez_slots')
    for slot in bribe_slots:
        bribe = BOSS_SLOT_HPS[slot] * 5
        bribe_values.extend([
            ((bribe >> (i * 8)) & 0xFF) for i in range(4)
        ])

    env.add_binary(WACKY_ROM_ADDRESS, bribe_values, as_script=True)
    env.add_toggle('allow_boss_bypass')
    env.add_toggle('wacky_boss_skip_hook')

def apply_gottagofast(env):
    env.add_toggle('wacky_sprint')

def apply_worthfighting(env):
    env.add_toggle('wacky_post_treasure_hook')
    env.add_toggle('wacky_post_battle_hook')

def apply_advertising(env):
    MONSTER_DATA_CHANGES = {
        0x01 : {'weak' : '#Ice'}, # Basilisk
        0x05 : {'resist element' : None, 'attack element' : '#Absorb', 'weak' : '#Air #Immune'}, # Cave Bat
        0x08 : {'resist status' : '#Mini'}, # TinyMage
        0x0A : {'weak' : None}, # SandMoth
        0x0D : {'trait' : None}, # CaveToad
        0x0F : {'attack element' : '#Absorb'}, # Zombie
        0x12 : {'trait' : None}, # Mad Toad
        0x18 : {'weak' : '#Holy'}, # Dark Imp
        0x1C : {'weak' : '#Holy'}, # Slime
        0x20 : {'weak' : '#Lit #Air'}, # Tricker
        0x25 : {'trait' : None}, # Gargoyle
        0x27 : {'trait' : None}, # Hooligan
        0x2A : {'trait' : '#Reptile'}, # Aligator
        0x2C : {'resist element' : None}, # Fighter
        0x30 : {'attack element' : '#Absorb'}, # Ghoul
        0x32 : {'attack element' : '#Absorb'}, # Revenant
        0x33 : {'resist element' : None, 'attack element' : '#Absorb', 'weak' : '#Fire #Holy #Air #Immune'}, # VampGirl
        0x34 : {'weak' : None}, # CaveNaga
        0x37 : {'trait' : '#Reptile'}, # Crocdile
        0x38 : {'weak' : '#Ice'}, # Hydra
        0x3D : {'trait' : '#Reptile', 'weak' : '#Ice'}, # Python
        0x3E : {'trait' : '#Spirit', 'weak' : None, 'resist element' : None}, # Grudger
        0x3F : {'trait' : '#Mage'}, # Mage
        0x41 : {'weak' : None}, # Ogre
        0x42 : {'weak' : None}, # Panther
        0x43 : {'trait' : None, 'weak' : None, 'resist element' : None}, # SwordMan
        0x45 : {'trait' : '#Zombie', 'attack element' : '#Absorb', 'weak' : '#Fire #Holy #Air'}, # VampLady
        0x47 : {'weak' : None}, # Puppet
        0x48 : {'weak' : None}, # GlomWing
        0x4A : {'trait' : '#Spirit'}, # Screamer
        0x4E : {'weak' : None, 'trait' : None}, # BladeMan
        0x50 : {'attack status' : '#Stone'}, # Medusa
        0x54 : {'weak' : '#Holy #Immune', 'trait' : '#Spirit'}, # Ghost
        0x55 : {'weak' : '#Ice', 'resist element' : '#Fire #Absorb'}, # Bomb
        0x56 : {'weak' : '#Fire', 'resist element' : '#Ice #Absorb'}, # GrayBomb
        0x58 : {'resist element' : None}, # Carapace
        0x5A : {'attack element' : '#Fire'}, # FlameDog
        0x5B : {'attack status' : '#Stone'}, # Gorgon
        0x5D : {'trait' : '#Reptile', 'resist status' : '#Sleep #Stun', 'weak' : None}, # Lilith
        0x5F : {'trait' : None}, # TinyToad
        0x63 : {'trait' : '#Giant'}, # Mad Ogre
        0x65 : {'resist element' : None, 'attack element' : '#Absorb', 'weak' : '#Air'}, # GiantBat
        0x66 : {'weak' : None}, # Arachne
        0x68 : {'weak' : '#Lit'}, # Beamer
        0x69 : {'weak' : None}, # Balloon
        0x6A : {'weak' : '#Holy'}, # Grenade
        0x6C : {'weak' : '#Lit'}, # Last Arm
        0x6E : {'weak' : '#Lit', 'trait' : '#Dragon #Robot', 'resist element' : '#Fire'}, # D.Machin
        0x6F : {'weak' : None}, # Talantla
        0x70 : {'weak' : None}, # Gremlin
        0x72 : {'resist element' : '#Fire #Absorb', 'weak' : '#Ice #Immune'}, # Red Worm
        0x76 : {'weak' : None}, # RockMoth
        0x77 : {'resist element' : None, 'weak' : '#Air'}, # Were Bat
        0x78 : {'attack element' : '#Ice', 'weak' : '#Fire #Immune'}, # IceBeast
        0x7D : {'trait' : None, 'weak' : '#Fire #Holy'}, # DarkTree
        0x81 : {'weak' : '#Ice #Immune'}, # Tofu
        0x82 : {'weak' : '#Dark #Immune'}, # Pudding
        0x84 : {'weak' : '#Fire'}, # Ironman
        0x87 : {'weak' : '#Lit'}, # Alert
        0x88 : {'weak' : '#Lit'}, # Machine
        0x89 : {'weak' : '#Lit'}, # MacGiant
        0x8A : {'attack status' : '#Blind #Mute #Piggy #Mini #Toad #Charm'}, # Molbol
        0x8C : {'resist element' : '#Ice #Absorb'}, # Ging-Ryu
        0x90 : {'weak' : '#Lit'}, # EvilMask
        0x91 : {'trait' : None}, # Horseman
        0x92 : {'weak' : '#Ice', 'resist element' : '#Fire'}, # RedGiant
        0x95 : {'weak' : '#Fire #Holy'}, # D. Lunar
        0x96 : {'weak' : '#Lit'}, # Searcher
        0x9A : {'weak' : '#Lit', 'resist element' : '#Ice #Absorb'}, # Ogopogo
        0x9B : {'weak' : '#Fire', 'resist element' : '#Ice #Absorb'}, # Blue D
        0x9C : {'resist element' : '#Lit #Absorb'}, # King-Ryu
        0x9D : {'weak' : None}, # Clapper
        0x9E : {'weak' : '#Dark', 'resist element' : '#Holy #Absorb'}, # Pale Dim
        0xA1 : {'weak' : '#Dark', 'trait' : '#Dragon'}, # D.Mist
        0xA2 : {'resist element' : None, 'weak' : '#Lit'}, # Octomamm
        0xA4 : {'resist element' : '#Fire #Absorb', 'weak' : '#Ice'}, # MomBomb
        0xA6 : {'resist element' : None}, # Milon Z
        0xA7 : {'trait' : '#Reptile'}, # Baigan
        0xA8 : {'trait' : '#Reptile'}, # RightArm
        0xA9 : {'trait' : '#Reptile'}, # LeftArm
        0xAA : {'trait' : '#Reptile'}, # Kainazzo
        0xAC : {'trait' : '#Mage'}, # Dark Elf
        0xB1 : {'weak' : '#Air'}, # Valvalis
        0xB4 : {'weak' : '#Holy', 'resist element' : '#Dark #Immune', 'trait' : '#Mage'}, # Golbez
        0xB8 : {'trait' : '#Robot #Zombie'}, # Dr. Lugae second phase
        0xBB : {'trait' : '#Mage', 'resist element' : '#Fire #Ice #Absorb'}, # Rubicant
        0xBC : {'weak' : None}, # Odin
        0xBD : {'trait' : '#Reptile'}, # Leviatan
        0xBE : {'trait' : '#Dragon'}, # Bahamut
        0xBF : {'trait' : '#Spirit'}, # EvilWall
        0xC1 : {'trait' : '#Zombie', 'weak' : '#Fire #Immune', 'resist element' : '#Ice #Lit #Dark #Holy #Air #Absorb'}, # Elements (Milon Z/Rubicant)
        0xC2 : {'trait' : '#Reptile', 'weak' : '#Lit #Immune', 'resist element' : '#Fire #Ice #Dark #Holy #Air #Absorb'}, # Elements (Kainazzo/Valvalis)
        0xC3 : {'resist element' : None}, # Dark Dragon
        0xC4 : {'trait' : '#Reptile', 'weak' : '#Lit'}, # Waterhag boss version
        0xC5 : {'trait' : '#Robot', 'weak' : '#Lit #Air'}, # CPU
        0xC6 : {'trait' : '#Robot', 'weak' : '#Lit #Air'}, # Defender
        0xCD : {'weak' : '#Holy', 'resist element' : '#Dark'}, # D.Knight
        0xD4 : {'trait' : '#Robot #Zombie'}, # Balnab-Z
        0xD5 : {'trait' : '#Robot', 'weak' : '#Lit #Air'}, # Attacker
        0xD6 : {'weak' : '#Ice', 'resist element' : '#Fire #Absorb'}, # Bomb boss version
        0xD7 : {'weak' : '#Fire', 'resist element' : '#Ice #Absorb'}, # GrayBomb boss version
        0xDC : {'trait' : None}, # Gargoyle gauntlet version
        0xDD : {'weak' : '#Holy'}, # Dark Imp boss version
    }

    advertising_script = [] # no need for newlines

    for id in MONSTER_DATA_CHANGES:
        advertising_script.append(f'monster(${id:02X}) {{')
        changes = MONSTER_DATA_CHANGES[id]
        for param in changes:
            if param == 'weak':
                advertising_script.append('    weak element ' + (changes[param] if changes[param] else ''))
            if param in ['resist element', 'resist status']:
                advertising_script.append('    ' + param + ' ' + (changes[param] if changes[param] else ''))
            if param == 'trait':
                advertising_script.append('    race ' + (changes[param] if changes[param] else ''))
            if param in ['attack element', 'attack status']:
                advertising_script.append('    ' + param + ' ' + (changes[param] if changes[param] else ''))
        advertising_script.append('}\n')

    gear_description_bytes = {} # dictionary with keys = item_ids, values = replacement description lines 2-4 in bytes

    # Ice weaponry changes, to hit reptiles (Claw, Brand, Spear, Arrows)
    for equip_id in [0x02, 0x1D, 0x26, 0x57]:
        env.add_binary(BusAddress(0x0F9100 + 0x05 + (equip_id * 0x08)), [0x04], as_script=True)
    gear_description_bytes[0x02] = encode_text(
        '[$00][$fa]Deals ice damage.          [$fb][$00][$00]' +
        '[$00][$fa]Strong against reptiles.   [$fb][$00][$00]' +
        '[$00][$fa]                           [$fb][$00][$00]' 
        )
    gear_description_bytes[0x1D] = encode_text(
        '[$00][$fa]Deals ice damage.          [$fb][$00][$00]' +
        '[$00][$fa]Strong against reptiles.   [$fb][$00][$00]' +
        '[$00][$fa]                           [$fb][$00][$00]' 
        )
    gear_description_bytes[0x26] = encode_text(
        '[$00][$fa]Casts [blackmagic]Ice[$c2]2. Deals ice    [$fb][$00][$00]' +
        '[$00][$fa]damage. Strong v. reptiles [$fb][$00][$00]' +
        '[$00][$fa]and flying enemies.        [$fb][$00][$00]' 
        )
    gear_description_bytes[0x57] = encode_text(
        '[$00][$fa]Deals ice damage.          [$fb][$00][$00]' +
        '[$00][$fa]Strong against reptiles.   [$fb][$00][$00]' +
        '[$00][$fa]                           [$fb][$00][$00]' 
        )
    # Bolt weaponry changes, to hit robots (Thunder Rod, Blitz Whip)
    for equip_id in [0x0A, 0x35]:
        env.add_binary(BusAddress(0x0F9100 + 0x05 + (equip_id * 0x08)), [0x02], as_script=True)
    gear_description_bytes[0x0A] = encode_text(
        '[$00][$fa]WIS[$cb]3. Casts [blackmagic]Lit[$c2]1.       [$fb][$00][$00]' +
        '[$00][$fa]Deals lightning damage.    [$fb][$00][$00]' +
        '[$00][$fa]Strong v. robots.          [$fb][$00][$00]' 
        )
    # Blitz Whip's description handled later.
    # Earth hammer isn't Fire elemental
    env.add_binary(BusAddress(0x0F9100 + 0x04 + (0x4A * 0x08)), [0x00], as_script=True)
    gear_description_bytes[0x4A] = encode_text(
        '[$00][$fa]STR[$cb]5. Two[$c2]handed. Casts   [$fb][$00][$00]' +
        '[$00][$fa][blackmagic]Quake. Strong             [$fb][$00][$00]' +
        '[$00][$fa]against robots.            [$fb][$00][$00]' 
        )    
    # Make Zeus gauntlets (and anything with the same element/status index) resist Lit as well
    env.add_binary(BusAddress(0x0FA590 + (0x14 * 0x03)), [0x04], as_script=True)
    gear_description_bytes[0xA3] = encode_text(
        '[$00][$fa]STR[$cb]10[$c9] VIT[$cb]10. Prevents   [$fb][$00][$00]' +
        '[$00][$fa]Mini. Resists lightning    [$fb][$00][$00]' +
        '[$00][$fa]damage and robots.         [$fb][$00][$00]' 
        )   
    # Dwarf Axe should hit Air weakness
    env.add_binary(BusAddress(0x0F9100 + 0x04 + (0x39 * 0x08)), [0x06], as_script=True)
    gear_description_bytes[0x39] = encode_text(
        '[$00][$fa]STR[$c7]VIT[$cb]5[$c9] AGI[$c7]WIS[$c7]WIL[$c2]5.  [$fb][$00][$00]' +
        '[$00][$fa]Strong against flying      [$fb][$00][$00]' +
        '[$00][$fa]enemies.                   [$fb][$00][$00]' 
        )   
    # Drain Spear needs a new element/status entry, for Air/Absorb
    # Note that the forge weapon takes entry 0x3B, so start after that
    env.add_binary(BusAddress(0x0FA590 + (0x3C * 0x03)), [0x60, 0x00, 0x00], as_script=True)
    env.add_binary(BusAddress(0x0F9100 + 0x04 + (0x29 * 0x08)), [0x3C], as_script=True )
    gear_description_bytes[0x29] = encode_text(
        '[$00][$fa]STR[$c7]AGI[$c7]VIT[$c7]WIS[$c7]WIL[$c2]10.    [$fb][$00][$00]' +
        '[$00][$fa]Absorbs HP. Strong against [$fb][$00][$00]' +
        '[$00][$fa]giant[$c7]slime[$c7]flying foes.   [$fb][$00][$00]' 
        )
    # Darkness arrows also need a new element/status entry, for Dark/Blind
    env.add_binary(BusAddress(0x0FA590 + (0x3D * 0x03)), [0x08, 0x02, 0x00], as_script=True)
    env.add_binary(BusAddress(0x0F9100 + 0x04 + (0x59 * 0x08)), [0x3D], as_script=True)
    gear_description_bytes[0x59] = encode_text(
        '[$00][$fa]Deals dark damage.         [$fb][$00][$00]' +
        '[$00][$fa]Inflicts Blind.            [$fb][$00][$00]' +
        '[$00][$fa]                           [$fb][$00][$00]' 
        )
    # the Spoon, being a dinner utensil, should be effective against dessert monsters (Slimes)
    env.add_binary(BusAddress(0x0F9100 + 0x05 + (0x3E * 0x08)), [0x20], as_script=True)
    gear_description_bytes[0x3E] = encode_text(
        '[$00][$fa]Dart for massive damage.   [$fb][$00][$00]' +
        '[$00][$fa]Strong against slimes.     [$fb][$00][$00]' +
        '[$00][$fa]                           [$fb][$00][$00]' 
        )
    # the Gigant Axe is handled in custom_weapon_rando.py

    # ElvenBow gets to actually cast Shell
    env.add_binary(BusAddress(0x0F9100 + 0x03 + (0x51 * 0x08)), [0x06], as_script=True)
    gear_description_bytes[0x51] = encode_text(
        '[$00][$fa]WIS[$cb]5. Casts [whitemagic]Shell.       [$fb][$00][$00]' +
        '[$00][$fa]Strong v. mages and flying [$fb][$00][$00]' +
        '[$00][$fa]foes.                      [$fb][$00][$00]' 
        )
    # Lunar gets to actually cast Dspel
    env.add_binary(BusAddress(0x0F9100 + 0x03 + (0x13 * 0x08)), [0x0C], as_script=True)
    gear_description_bytes[0x13] = encode_text(
        '[$00][$fa]                           [$fb][$00][$00]' +
        '[$00][$fa]WIL[$cb]10. Casts [whitemagic]Dspel.      [$fb][$00][$00]' +
        '[$00][$fa]                           [$fb][$00][$00]' 
        )    
    # Defense gets to cast Armor
    env.add_binary(BusAddress(0x0F9100 + 0x03 + (0x1E * 0x08)), [0x05], as_script=True)
    gear_description_bytes[0x1E] = encode_text(
        '[$00][$fa]                           [$fb][$00][$00]' +
        '[$00][$fa]VIT[$cb]15. Casts [whitemagic]Armor.      [$fb][$00][$00]' +
        '[$00][$fa]                           [$fb][$00][$00]' 
        )
    # Murasame gets to cast Slow instead of Armor; thematic with Masamune
    env.add_binary(BusAddress(0x0F9100 + 0x03 + (0x2F * 0x08)), [0x07], as_script=True)
    env.add_binary(BusAddress(0x0FD4E0 + 0x2F), [0x07], as_script=True)
    gear_description_bytes[0x2F] = encode_text(
        '[$00][$fa]STR[$c7]VIT[$c7]WIS[$cb]5[$c9] AGI[$c7]WIL[$c2]5.  [$fb][$00][$00]' +
        '[$00][$fa]Casts [whitemagic]Slow.               [$fb][$00][$00]' +
        '[$00][$fa]                           [$fb][$00][$00]' 
        )
    # Power staff gets to *cast* Bersk, not just proc it. Need to add its hits data though.
    env.add_binary(BusAddress(0x0F9070 + 0x12), [0x01], as_script=True)
    env.add_binary(BusAddress(0x0F9100 + 0x02 + (0x12 * 0x08)), [0xE3, 0x09], as_script=True)
    gear_description_bytes[0x12] = encode_text(
        '[$00][$fa]STR[$cb]10. Casts [whitemagic]Bersk.      [$fb][$00][$00]' +
        '[$00][$fa]Inflicts Berserk.          [$fb][$00][$00]' +
        '[$00][$fa]                           [$fb][$00][$00]' 
        )
    # Blitz whip casts Blitz (the Ninja spell, not the enemy spell, as partially busted as that would be). Also needs hits.
    env.add_binary(BusAddress(0x0F9070 + 0x35), [0x04], as_script=True)
    env.add_binary(BusAddress(0x0FD4E0 + 0x35), [0x44], as_script=True)
    env.add_binary(BusAddress(0x0F9100 + 0x02 + (0x35 * 0x08)), [0xBC, 0x44], as_script=True)
    gear_description_bytes[0x35] = encode_text(
        '[$00][$fa]Casts Blitz. Lightning     [$fb][$00][$00]' +
        '[$00][$fa]damage. Strong v. robots.  [$fb][$00][$00]' +
        '[$00][$fa]Inflicts Paralyze.         [$fb][$00][$00]' 
        )
    # Flame whip casts Flame. Also needs... a bit more damage for hits, for balance.
    env.add_binary(BusAddress(0x0F9070 + 0x36), [0x08], as_script=True)
    env.add_binary(BusAddress(0x0FD4E0 + 0x36), [0x42], as_script=True)
    env.add_binary(BusAddress(0x0F9100 + 0x02 + (0x36 * 0x08)), [0xC1, 0x42], as_script=True)
    gear_description_bytes[0x36] = encode_text(
        '[$00][$fa]STR[$c7]AGI[$c7]VIT[$cb]5[$c9] WIS[$c7]WIL[$c2]5.  [$fb][$00][$00]' +
        '[$00][$fa]Casts Flame. Fire damage.  [$fb][$00][$00]' +
        '[$00][$fa]Inflicts Paralyze.         [$fb][$00][$00]' 
        )

    # since we changed equipment, need to manually modify descriptions for every piece of gear
    # (but not if What's My Gear Again? is on; deal with that when we merge multi-wacky)
    env.meta['wacky_gear_descriptions'] = gear_description_bytes

    env.add_file('scripts/wacky/advertising.f4c')
    env.add_script('\n'.join(advertising_script))
    

def setup_saveusbigchocobo(env):
    env.meta['wacky_starter_kit'] = [( 'Carrot', [5] )]

def apply_dropitlikeitshot(env):
    env.add_file('scripts/wacky/dropitlikeitshot.f4c')