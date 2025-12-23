from django.test import TestCase
from .models import Enemy, EnemyStats
from .serializers import EnemySerializer


class EnemySerializerTests(TestCase):
    def test_enemy_serializer_includes_nested_stats_and_displays(self):
        """EnemySerializer should include nested stats and readable choice displays."""
        enemy = Enemy.objects.create(
            name="Skeleton",
            hp=13,
            ac=13,
            challenge_rating="1/4",
            size="M",
            creature_type="undead",
            alignment="NE",
        )
        EnemyStats.objects.create(enemy=enemy, hit_points=13, armor_class=13)

        data = EnemySerializer(enemy).data

        # Basic fields
        self.assertEqual(data["name"], "Skeleton")
        self.assertEqual(data["challenge_rating"], "1/4")

        # Nested stats present
        self.assertIn("stats", data)
        self.assertIsNotNone(data["stats"])
        self.assertEqual(data["stats"]["hit_points"], 13)

        # Human-readable choice fields
        self.assertEqual(data["size_display"], "Medium")
        self.assertEqual(data["creature_type_display"], "Undead")
        self.assertEqual(data["alignment_display"], "Neutral Evil")
