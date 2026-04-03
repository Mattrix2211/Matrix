from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from org.models import Ship, Service, Sector, Section
from accounts.models import UserProfile, Roles
from assets.models import AssetType, Asset, Location, ChecklistTemplate, ChecklistItemTemplate
from maintenance.models import MaintenancePlan

class Command(BaseCommand):
    help = "Seed demo data for BordOps"

    def handle(self, *args, **options):
        ship, _ = Ship.objects.get_or_create(name="BordOps I", code="BO1")
        service, _ = Service.objects.get_or_create(ship=ship, name="Technique")
        sector_fire, _ = Sector.objects.get_or_create(service=service, name="Pompiers")
        sector_elec, _ = Sector.objects.get_or_create(service=service, name="Électricité")
        section_a, _ = Section.objects.get_or_create(sector=sector_fire, name="Section A")
        section_b, _ = Section.objects.get_or_create(sector=sector_elec, name="Section B")

        admin = User.objects.create_user("admin", password="admin")
        commandant = User.objects.create_user("commandant", password="pass")
        chef_service = User.objects.create_user("chefservice", password="pass")
        chef_secteur = User.objects.create_user("chefsecteur", password="pass")
        chef_section = User.objects.create_user("chefsection", password="pass")
        equipier = User.objects.create_user("equipier", password="pass")

        UserProfile.objects.create(user=commandant, role=Roles.COMMANDANT, ship=ship)
        UserProfile.objects.create(user=chef_service, role=Roles.CHEF_SERVICE, service=service)
        UserProfile.objects.create(user=chef_secteur, role=Roles.CHEF_SECTEUR, sector=sector_fire)
        UserProfile.objects.create(user=chef_section, role=Roles.CHEF_SECTION, section=section_a)
        UserProfile.objects.create(user=equipier, role=Roles.EQUIPIER, section=section_a)

        location, _ = Location.objects.get_or_create(ship=ship, name="Pont 1")
        at_fire, _ = AssetType.objects.get_or_create(name="Extincteur", category="Fire", sector=sector_fire)
        at_san, _ = AssetType.objects.get_or_create(name="Évacuation sanitaire", category="Sanitaire", sector=sector_elec)

        asset1 = Asset.objects.create(asset_type=at_fire, ship=ship, service=service, sector=sector_fire, section=section_a, location=location, internal_id="FX-001")
        asset2 = Asset.objects.create(asset_type=at_san, ship=ship, service=service, sector=sector_elec, section=section_b, location=location, internal_id="SAN-001")

        temp, _ = ChecklistTemplate.objects.get_or_create(name="Contrôle visuel extincteur", sector=sector_fire, asset_type=at_fire)
        ChecklistItemTemplate.objects.get_or_create(template=temp, label="Goupille présente", field_type="checkbox", required=True, order=1)
        ChecklistItemTemplate.objects.get_or_create(template=temp, label="Pression (bar)", field_type="number", unit="bar", order=2)

        MaintenancePlan.objects.get_or_create(scope="ASSET_TYPE", asset_type=at_fire, name="Contrôle trimestriel", every_n_days=90, checklist_template=temp)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
