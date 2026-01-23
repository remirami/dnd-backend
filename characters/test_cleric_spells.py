from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from characters.models import Character, CharacterClass, CharacterStats
from spells.models import Spell

class ClericSpellTest(APITestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='test', password='test')
        self.client.force_authenticate(user=self.user)
        
        self.cleric_class = CharacterClass.objects.create(name='cleric', hit_dice='d8')
        self.spell = Spell.objects.create(name='Bless', level=1, school='Enchantment', description='Buff')
        self.spell.classes.add(self.cleric_class)
        
        from characters.models import CharacterRace
        self.race = CharacterRace.objects.create(name='Human')
        
        self.character = Character.objects.create(
            user=self.user,
            name="ClericTest",
            character_class=self.cleric_class,
            race=self.race,
            level=1
        )
        CharacterStats.objects.create(character=self.character, wisdom=16, constitution=14)

    def test_cleric_can_add_spell(self):
        # Cleric attempts to "Learn" (Add) Bless
        url = reverse('character-learn-spell', kwargs={'pk': self.character.pk})
        data = {
            'spell_id': self.spell.id,
            'spell_name': self.spell.name,
            'spell_level': self.spell.level
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"Cleric failed to add spell: {response.data}")
        
    def test_cleric_prepare_flow(self):
        # 1. Add Spell
        url_learn = reverse('character-learn-spell', kwargs={'pk': self.character.pk})
        self.client.post(url_learn, {'spell_id': self.spell.id, 'spell_name': 'Bless', 'spell_level': 1})
        
        # 2. Prepare Spell
        url_prep = reverse('character-prepare-spell', kwargs={'pk': self.character.pk})
        data = {'spell_id': self.spell.id, 'prepare': True}
        response = self.client.post(url_prep, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"Failed to prepare spell: {response.data}")
