from django.core.management.base import BaseCommand
from apps.branches.models import Branch
from apps.accounts.models import Staff
from apps.inventory.models import Category, Product
from apps.customers.models import Customer

class Command(BaseCommand):
    help = 'Seed database with mock POS data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding branches...')
        branches = {}
        for name, addr in [
            ('Makati', 'Ayala Ave, Makati City'),
            ('BGC',    'BGC High Street, Taguig'),
            ('Quezon', 'Timog Ave, Quezon City'),
        ]:
            b, _ = Branch.objects.get_or_create(name=name, defaults={'address': addr})
            branches[name] = b

        self.stdout.write('Seeding staff...')
        for s in [
            {'email':'ck@xantara.com',   'name':'Clouie Caagbay', 'role':'admin',       'branch':'Makati', 'password':'admin123'},
            {'email':'ana@xantara.com',  'name':'Ana Reyes',      'role':'cashier',     'branch':'Makati', 'password':'staff123'},
            {'email':'rico@xantara.com', 'name':'Rico Santos',    'role':'cashier',     'branch':'Makati', 'password':'staff123'},
            {'email':'maya@xantara.com', 'name':'Maya Cruz',      'role':'manager',     'branch':'BGC',    'password':'staff123'},
            {'email':'ben@xantara.com',  'name':'Ben Lim',        'role':'stock_clerk', 'branch':'Makati', 'password':'staff123'},
            {'email':'rose@xantara.com', 'name':'Rose Tan',       'role':'cashier',     'branch':'BGC',    'password':'staff123'},
            {'email':'jun@xantara.com',  'name':'Jun Dela Cruz',  'role':'cashier',     'branch':'Quezon', 'password':'staff123'},
            {'email':'cris@xantara.com', 'name':'Cris Bautista',  'role':'stock_clerk', 'branch':'Quezon', 'password':'staff123'},
        ]:
            branch = branches[s.pop('branch')]
            pwd    = s.pop('password')
            staff, created = Staff.objects.get_or_create(
                email=s['email'],
                defaults={**s, 'branch': branch, 'status': 'active'}
            )
            if created:
                staff.set_password(pwd)
                staff.avatar = ''.join(p[0].upper() for p in staff.name.split()[:2])
                staff.save()

        self.stdout.write('Seeding categories + products...')
        for name in ['FTWR', 'TOPS', 'BOTM', 'ACCS', 'BAGS']:
            Category.objects.get_or_create(name=name)

        for itemcode, descshort, cat, price, cost, stock in [
            ('AF1-WHT-42',  'Air Force 1',   'FTWR', 4250, 2100, 12),
            ('SFT-BLK-M',   'Slim Fit Tee',  'TOPS',  890,  380, 34),
            ('CGS-KHK-L',   'Cargo Shorts',  'BOTM', 1650,  720,  3),
            ('SBC-RED-OS',  'Snapback Cap',  'ACCS',  750,  280,  0),
            ('SLB-BLK-OS',  'Sling Bag',     'BAGS', 1290,  550,  5),
            ('SGL-BLK-OS',  'Sunglasses',    'ACCS', 2100,  900, 21),
            ('PS-WHT-L',    'Polo Shirt',    'TOPS', 1350,  580, 45),
            ('CS-BLK-41',   'Canvas Shoes',  'FTWR', 2800, 1200,  0),
            ('WW-SLV-OS',   'Wrist Watch',   'ACCS', 5500, 2400,  7),
            ('JP-BLK-M',    'Jogger Pants',  'BOTM', 1750,  760, 22),
        ]:
            Product.objects.get_or_create(itemcode=itemcode, defaults={
                'descshort':    descshort,
                'categorycode': cat,
                'sell_price_rp': price,
                'unitcost':     cost,
                'stock_sa':     stock,
                'active':       True,
                'trackinventory': True,
            })

        self.stdout.write('Seeding customers...')
        for name, email, phone in [
            ('Maria Santos',  'maria@email.com',   '09171234567'),
            ('Jose Reyes',    'jose@email.com',    '09281234567'),
            ('Ana Cruz',      'anacruz@email.com', '09391234567'),
            ('Carlo Mendoza', 'carlo@email.com',   '09451234567'),
        ]:
            Customer.objects.get_or_create(
                email=email, defaults={'name': name, 'phone': phone}
            )

        self.stdout.write(self.style.SUCCESS('Seed complete!'))
        self.stdout.write('Login: ck@xantara.com / admin123')
