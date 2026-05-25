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
        cats = {}
        for name in ['Footwear', 'Tops', 'Bottoms', 'Accessories', 'Bags']:
            c, _ = Category.objects.get_or_create(name=name)
            cats[name] = c

        for name, sku, cat, price, cost, stock, maxs in [
            ('Air Force 1',   'AF1-WHT-42',  'Footwear',    4250, 2100, 12, 50),
            ('Slim Fit Tee',  'SFT-BLK-M',   'Tops',         890,  380, 34,100),
            ('Cargo Shorts',  'CGS-KHK-L',   'Bottoms',     1650,  720,  3, 40),
            ('Snapback Cap',  'SBC-RED-OS',  'Accessories',  750,  280,  0, 30),
            ('Sling Bag',     'SLB-BLK-OS',  'Bags',        1290,  550,  5, 20),
            ('Sunglasses',    'SGL-BLK-OS',  'Accessories', 2100,  900, 21, 40),
            ('Polo Shirt',    'PS-WHT-L',    'Tops',        1350,  580, 45, 80),
            ('Canvas Shoes',  'CS-BLK-41',   'Footwear',    2800, 1200,  0, 30),
            ('Wrist Watch',   'WW-SLV-OS',   'Accessories', 5500, 2400,  7, 15),
            ('Jogger Pants',  'JP-BLK-M',    'Bottoms',     1750,  760, 22, 50),
        ]:
            Product.objects.get_or_create(sku=sku, defaults={
                'name': name, 'category': cats[cat],
                'price': price, 'cost': cost, 'stock': stock, 'max_stock': maxs,
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
