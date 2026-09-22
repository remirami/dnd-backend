from rest_framework import serializers
from characters.models import Character
from gauntlet.models import GauntletRun, GauntletSnapshotHero


class GauntletSnapshotHeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = GauntletSnapshotHero
        fields = [
            'id',
            'character_id',
            'name',
            'character_class',
            'level',
            'current_hp',
            'max_hp',
            'temp_hp',
            'hit_dice_remaining',
            'hit_dice_total',
            'hit_die_type',
            'spell_slots',
            'is_alive',
            'death_saves',
            'created_at',
        ]


class GauntletRunSerializer(serializers.ModelSerializer):
    snapshot_heroes = GauntletSnapshotHeroSerializer(many=True, read_only=True)
    current_combat_session_id = serializers.IntegerField(source='current_combat_session.id', read_only=True)

    class Meta:
        model = GauntletRun
        fields = [
            'id',
            'name',
            'status',
            'theme',
            'party_level',
            'party_size',
            'current_wave',
            'max_waves',
            'is_endless',
            'current_combat_session_id',
            'score',
            'enemies_killed',
            'damage_dealt',
            'turns_elapsed',
            'active_boons',
            'snapshot_heroes',
            'created_at',
            'completed_at',
        ]
        read_only_fields = [
            'status',
            'party_level',
            'party_size',
            'current_wave',
            'score',
            'enemies_killed',
            'damage_dealt',
            'turns_elapsed',
            'created_at',
            'completed_at',
        ]


class GauntletRunCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False, default="The Gauntlet")
    theme = serializers.ChoiceField(choices=GauntletRun.THEME_CHOICES, default='colosseum')
    character_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=6,
        help_text="IDs of 1 to 6 characters to enter into the Gauntlet"
    )
    auto_delete_oldest = serializers.BooleanField(required=False, default=False)

    def validate_character_ids(self, value):
        user = self.context['request'].user
        chars = Character.objects.filter(id__in=value)
        if user and user.is_authenticated:
            chars = chars.filter(user=user)

        if chars.count() != len(value):
            raise serializers.ValidationError("One or more characters not found or not owned by user.")
        return value


class RespiteRequestSerializer(serializers.Serializer):
    choice_type = serializers.ChoiceField(
        choices=['breather', 'arcane_surge', 'supply_drop', 'tactical_boon'],
        help_text="Respite bonus choice"
    )
    details = serializers.DictField(required=False, default=dict)
