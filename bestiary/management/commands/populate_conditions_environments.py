from django.core.management.base import BaseCommand
from bestiary.models import Condition, Environment


class Command(BaseCommand):
    help = 'Populate D&D 5e conditions and environments'

    def handle(self, *args, **options):
        # D&D 5e Conditions
        conditions = [
            ('blinded', 'A blinded creature can\'t see and automatically fails any ability check that requires sight.'),
            ('charmed', 'A charmed creature can\'t attack the charmer or target the charmer with harmful abilities or magical effects.'),
            ('deafened', 'A deafened creature can\'t hear and automatically fails any ability check that requires hearing.'),
            ('frightened', 'A frightened creature has disadvantage on ability checks and attack rolls while the source of its fear is within line of sight.'),
            ('grappled', 'A grappled creature\'s speed becomes 0, and it can\'t benefit from any bonus to its speed.'),
            ('incapacitated', 'An incapacitated creature can\'t take actions or reactions.'),
            ('invisible', 'An invisible creature is impossible to see without the aid of magic or a special sense.'),
            ('paralyzed', 'A paralyzed creature is incapacitated and can\'t move or speak.'),
            ('petrified', 'A petrified creature is transformed, along with any nonmagical object it is wearing or carrying, into a solid inanimate substance.'),
            ('poisoned', 'A poisoned creature has disadvantage on attack rolls and ability checks.'),
            ('prone', 'A prone creature\'s only movement option is to crawl, unless it stands up and thereby ends the condition.'),
            ('restrained', 'A restrained creature\'s speed becomes 0, and it can\'t benefit from any bonus to its speed.'),
            ('stunned', 'A stunned creature is incapacitated, can\'t move, and can speak only falteringly.'),
            ('unconscious', 'An unconscious creature is incapacitated, can\'t move or speak, and is unaware of its surroundings.'),
            ('exhaustion', 'Some special abilities and environmental hazards, such as starvation and the long-term effects of freezing or scorching temperatures, can lead to a special condition called exhaustion.'),
        ]
        
        for condition_name, description in conditions:
            Condition.objects.get_or_create(
                name=condition_name,
                defaults={'description': description}
            )
            self.stdout.write(f'Created condition: {condition_name}')
        
        # D&D 5e Environments
        environments = [
            'arctic', 'coastal', 'desert', 'forest', 'grassland', 
            'hill', 'mountain', 'swamp', 'underdark', 'underwater', 
            'urban', 'any'
        ]
        
        for env_name in environments:
            Environment.objects.get_or_create(name=env_name)
            self.stdout.write(f'Created environment: {env_name}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated conditions and environments!')
        )
