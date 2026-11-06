from django.apps import AppConfig


class VoiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "talentplus_ai.voice"
    verbose_name = "Voice Screening"

    def ready(self):
        pass  # signal imports go here if needed later