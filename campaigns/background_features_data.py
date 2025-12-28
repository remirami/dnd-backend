"""
D&D 5e Background Features

This module contains background feature data for automatic application during character creation.
Features are organized by background name.
"""

# Background features by background name
BACKGROUND_FEATURES = {
    'acolyte': [
        {
            'name': 'Shelter of the Faithful',
            'description': 'As an acolyte, you command the respect of those who share your faith, and you can perform the religious ceremonies of your deity. You and your adventuring companions can expect to receive free healing and care at a temple, shrine, or other established presence of your faith, though you must provide any material components needed for spells. Those who share your religion will support you (but only you) at a modest lifestyle. You also have ties to the temple where you used to serve. When you are in a settlement, you can gain access to the temple and its resources, though you might be called upon to assist the temple in return.'
        }
    ],
    
    'criminal': [
        {
            'name': 'Criminal Contact',
            'description': 'You have a reliable and trustworthy contact who acts as your liaison to a network of other criminals. You know how to get messages to and from your contact, even over great distances; specifically, you know the local messengers, corrupt caravan masters, and seedy sailors who can deliver messages for you.'
        }
    ],
    
    'folk-hero': [
        {
            'name': 'Rustic Hospitality',
            'description': 'Since you come from the ranks of the common folk, you fit in among them with ease. You can find a place to hide, rest, or recuperate among other commoners, unless you have shown yourself to be a danger to them. They will shield you from the law or anyone else searching for you, though they will not risk their lives for you.'
        }
    ],
    
    'noble': [
        {
            'name': 'Position of Privilege',
            'description': 'Thanks to your noble birth, people are inclined to think the best of you. You are welcome in high society, and people assume you have the right to be wherever you are. The common folk make every effort to accommodate you and avoid your displeasure, and other people of high birth treat you as a member of the same social sphere. You can secure an audience with a local noble if you need to.'
        }
    ],
    
    'sage': [
        {
            'name': 'Researcher',
            'description': 'When you attempt to learn or recall a piece of lore, if you do not know that information, you often know where and from whom you can obtain it. Usually, this information comes from a library, scriptorium, university, or a sage or other learned person or creature. Your DM might rule that the knowledge you seek is secreted away in an almost inaccessible place, or that it simply cannot be found. Unearthing the deepest secrets of the multiverse can require an adventure or even a whole campaign.'
        }
    ],
    
    'soldier': [
        {
            'name': 'Military Rank',
            'description': 'You have a military rank from your career as a soldier. Soldiers loyal to your former military organization still recognize your authority and influence, and they defer to you if they are of a lower rank. You can invoke your rank to exert influence over other soldiers and requisition simple equipment or horses for temporary use. You can also usually gain access to friendly military encampments and fortresses where your rank is recognized.'
        }
    ],
    
    'hermit': [
        {
            'name': 'Discovery',
            'description': 'The quiet seclusion of your extended hermitage gave you access to a unique and powerful discovery. The exact nature of this revelation depends on the nature of your seclusion. It might be a great truth about the cosmos, the deities, the powerful beings of the outer planes, or the forces of nature. It could be a site that no one else has ever seen. You might have uncovered a fact that has long been forgotten, or unearthed some relic of the past that could rewrite history. It might be information that would be damaging to the people who or consigned you to exile, and hence the reason for your return to society. Work with your DM to determine the details of your discovery and its impact on the campaign.'
        }
    ],
    
    'outlander': [
        {
            'name': 'Wanderer',
            'description': 'You have an excellent memory for maps and geography, and you can always recall the general layout of terrain, settlements, and other features around you. In addition, you can find food and fresh water for yourself and up to five other people each day, provided that the land offers berries, small game, water, and so forth.'
        }
    ],
    
    'entertainer': [
        {
            'name': 'By Popular Demand',
            'description': 'You can always find a place to perform, usually in an inn or tavern but possibly with a circus, at a theater, or even in a noble\'s court. At such a place, you receive free lodging and food of a modest or comfortable standard (depending on the quality of the establishment), as long as you perform each night. In addition, your performance makes you something of a local figure. When strangers recognize you in a town where you have performed, they typically take a liking to you.'
        }
    ],
    
    'guild-artisan': [
        {
            'name': 'Guild Membership',
            'description': 'As an established and respected member of a guild, you can rely on certain benefits that membership provides. Your fellow guild members will provide you with lodging and food if necessary, and pay for your funeral if needed. In some cities and towns, a guildhall offers a central place to meet other members of your profession, which can be a good place to meet potential patrons, allies, or hirelings. Guilds often wield tremendous political power. If you are accused of a crime, your guild will support you if a good case can be made for your innocence or the crime is justifiable. You must pay dues of 5 gp per month to the guild. If you break guild rules, you might be fined or even expelled from the guild.'
        }
    ],
    
    'charlatan': [
        {
            'name': 'False Identity',
            'description': 'You have created a second identity that includes documentation, established acquaintances, and disguises that allow you to assume that persona. In addition, you can forge documents including official papers and personal letters, as long as you have seen an example of the kind of document or the handwriting you are trying to copy.'
        }
    ],
    
    'sailor': [
        {
            'name': 'Ship\'s Passage',
            'description': 'When you need to, you can secure free passage on a sailing ship for yourself and your adventuring companions. You might sail on the ship you served on, or another ship you have good relations with (perhaps one captained by a former crewmate). Because you\'re calling in a favor, you can\'t be certain of a schedule or route that will be to your liking, and your shipmates might call on such favors as well. In return for your free passage, you and your companions are expected to assist the crew during the voyage.'
        }
    ]
}


def get_background_features(background_name):
    """
    Get background features for a specific background.
    
    Args:
        background_name: Name of the background (e.g., 'acolyte', 'criminal')
    
    Returns:
        List of feature dictionaries with 'name' and 'description' keys
    """
    background_name_lower = background_name.lower()
    if background_name_lower not in BACKGROUND_FEATURES:
        return []
    
    return BACKGROUND_FEATURES[background_name_lower]


def apply_background_features_to_character(character):
    """
    Apply background features to a character.
    Creates CharacterFeature instances for all background features.
    
    Args:
        character: Character instance
    
    Returns:
        List of created CharacterFeature instances
    """
    from characters.models import CharacterFeature
    
    if not character.background:
        return []
    
    background_name = character.background.name
    background_features = get_background_features(background_name)
    
    created_features = []
    for feature_data in background_features:
        feature = CharacterFeature.objects.create(
            character=character,
            name=feature_data['name'],
            feature_type='background',
            description=feature_data['description'],
            source=f"{character.background.get_name_display()} Background"
        )
        created_features.append(feature)
    
    return created_features

