from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from bestiary.models import Enemy, EnemyStats
from .models import Encounter, EncounterEnemy


class EncounterEnemyModelTests(APITestCase):
    def setUp(self):
        self.enemy = Enemy.objects.create(name="Goblin", hp=7, ac=15)
        self.stats = EnemyStats.objects.create(enemy=self.enemy, hit_points=7, armor_class=15)
        self.encounter = Encounter.objects.create(name="Test Encounter")
        self.encounter_enemy = EncounterEnemy.objects.create(
            encounter=self.encounter,
            enemy=self.enemy,
            name="Goblin 1",
            current_hp=7,
        )

    def test_take_damage_reduces_hp_and_sets_dead(self):
        """Taking lethal damage should drop HP to 0 and mark enemy as not alive."""
        self.encounter_enemy.take_damage(10)
        self.encounter_enemy.refresh_from_db()
        self.assertEqual(self.encounter_enemy.current_hp, 0)
        self.assertFalse(self.encounter_enemy.is_alive)

    def test_heal_uses_enemy_stats_cap(self):
        """Healing should not exceed EnemyStats.hit_points and should revive if > 0 HP."""
        # Reduce HP first
        self.encounter_enemy.take_damage(5)
        self.encounter_enemy.refresh_from_db()
        self.assertEqual(self.encounter_enemy.current_hp, 2)

        # Heal more than missing HP; should cap at 7
        self.encounter_enemy.heal(10)
        self.encounter_enemy.refresh_from_db()
        self.assertEqual(self.encounter_enemy.current_hp, 7)
        self.assertTrue(self.encounter_enemy.is_alive)


class EncounterEnemyAPITests(APITestCase):
    def setUp(self):
        self.enemy = Enemy.objects.create(name="Orc", hp=15, ac=13)
        EnemyStats.objects.create(enemy=self.enemy, hit_points=15, armor_class=13)
        self.encounter = Encounter.objects.create(name="API Encounter")
        self.encounter_enemy = EncounterEnemy.objects.create(
            encounter=self.encounter,
            enemy=self.enemy,
            name="Orc 1",
            current_hp=15,
        )

    def test_damage_endpoint_applies_damage(self):
        """POST /encounter-enemies/<id>/damage/ should apply damage and return updated state."""
        url = f"/api/encounter-enemies/{self.encounter_enemy.id}/damage/"
        response = self.client.post(url, {"amount": 5}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.encounter_enemy.refresh_from_db()
        self.assertEqual(self.encounter_enemy.current_hp, 10)

    def test_heal_endpoint_applies_heal(self):
        """POST /encounter-enemies/<id>/heal/ should heal but not exceed max HP."""
        # First, damage the enemy
        self.encounter_enemy.take_damage(10)
        self.encounter_enemy.refresh_from_db()
        self.assertEqual(self.encounter_enemy.current_hp, 5)

        url = f"/api/encounter-enemies/{self.encounter_enemy.id}/heal/"
        response = self.client.post(url, {"amount": 20}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.encounter_enemy.refresh_from_db()
        self.assertEqual(self.encounter_enemy.current_hp, 15)
