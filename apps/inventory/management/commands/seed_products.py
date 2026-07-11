from django.core.management.base import BaseCommand
from apps.inventory.models import Product


PRODUCTS = [
    # itemcode         descshort                 dept  class cat   price   cost  stock  rop  uom   supplier
    # ── Footwear ──────────────────────────────────────────────────────────────────────────
    ('SNKR-WHT-42',  'White Sneakers Sz42',    'APRL','FTWU','FTWR', 3200, 1440, 18, 5, 'PCS', 'SUP001'),
    ('SNKR-BLK-42',  'Black Sneakers Sz42',    'APRL','FTWU','FTWR', 3200, 1440, 22, 5, 'PCS', 'SUP001'),
    ('SNKR-GRY-41',  'Grey Sneakers Sz41',     'APRL','FTWU','FTWR', 3200, 1440, 10, 5, 'PCS', 'SUP001'),
    ('BOOT-BRN-43',  'Brown Boots Sz43',       'APRL','FTWU','FTWR', 4800, 2160, 8,  3, 'PCS', 'SUP001'),
    ('BOOT-BLK-42',  'Black Boots Sz42',       'APRL','FTWU','FTWR', 4800, 2160, 6,  3, 'PCS', 'SUP001'),
    ('SNDL-TAN-38',  'Tan Sandals Sz38',       'APRL','FTWU','FTWR', 1500,  675, 14, 5, 'PCS', 'SUP002'),
    ('SNDL-BLK-39',  'Black Sandals Sz39',     'APRL','FTWU','FTWR', 1500,  675, 12, 5, 'PCS', 'SUP002'),
    ('LOAF-BRN-42',  'Brown Loafers Sz42',     'APRL','FTWU','FTWR', 3800, 1710, 9,  3, 'PCS', 'SUP001'),
    ('HITP-WHT-41',  'White Hi-Tops Sz41',     'APRL','FTWU','FTWR', 4200, 1890, 7,  3, 'PCS', 'SUP001'),
    ('FLIP-BLK-40',  'Black Flip Flops Sz40',  'APRL','FTWU','FTWR',  650,  260, 30, 8, 'PCS', 'SUP002'),
    # ── Tops ──────────────────────────────────────────────────────────────────────────────
    ('TEE-WHT-S',    'White Crew Tee S',       'APRL','TOPS','TOPS',  690,  280, 40, 10,'PCS', 'SUP003'),
    ('TEE-WHT-M',    'White Crew Tee M',       'APRL','TOPS','TOPS',  690,  280, 45, 10,'PCS', 'SUP003'),
    ('TEE-WHT-L',    'White Crew Tee L',       'APRL','TOPS','TOPS',  690,  280, 38, 10,'PCS', 'SUP003'),
    ('TEE-BLK-M',    'Black Crew Tee M',       'APRL','TOPS','TOPS',  690,  280, 50, 10,'PCS', 'SUP003'),
    ('TEE-GRY-M',    'Grey Crew Tee M',        'APRL','TOPS','TOPS',  690,  280, 35, 10,'PCS', 'SUP003'),
    ('PLO-WHT-M',    'White Polo Shirt M',     'APRL','TOPS','TOPS', 1350,  580, 28, 8, 'PCS', 'SUP003'),
    ('PLO-NVY-L',    'Navy Polo Shirt L',      'APRL','TOPS','TOPS', 1350,  580, 20, 8, 'PCS', 'SUP003'),
    ('PLO-GRN-M',    'Green Polo Shirt M',     'APRL','TOPS','TOPS', 1350,  580, 15, 8, 'PCS', 'SUP003'),
    ('HDY-GRY-M',    'Grey Hoodie M',          'APRL','TOPS','TOPS', 2100,  945, 22, 6, 'PCS', 'SUP004'),
    ('HDY-BLK-L',    'Black Hoodie L',         'APRL','TOPS','TOPS', 2100,  945, 18, 6, 'PCS', 'SUP004'),
    ('BTN-WHT-M',    'White Button-Down M',    'APRL','TOPS','TOPS', 1650,  743, 16, 5, 'PCS', 'SUP003'),
    ('BTN-BLK-L',    'Black Button-Down L',    'APRL','TOPS','TOPS', 1650,  743, 12, 5, 'PCS', 'SUP003'),
    ('LSV-WHT-M',    'White Long Sleeve M',    'APRL','TOPS','TOPS',  990,  446, 24, 6, 'PCS', 'SUP003'),
    # ── Bottoms ───────────────────────────────────────────────────────────────────────────
    ('JNS-BLK-30',   'Black Jeans Sz30',       'APRL','BOTM','BOTM', 1990,  896, 20, 6, 'PCS', 'SUP004'),
    ('JNS-BLK-32',   'Black Jeans Sz32',       'APRL','BOTM','BOTM', 1990,  896, 22, 6, 'PCS', 'SUP004'),
    ('JNS-BLU-32',   'Blue Jeans Sz32',        'APRL','BOTM','BOTM', 1990,  896, 18, 6, 'PCS', 'SUP004'),
    ('JNS-BLU-34',   'Blue Jeans Sz34',        'APRL','BOTM','BOTM', 1990,  896, 15, 6, 'PCS', 'SUP004'),
    ('SHT-KHK-M',    'Khaki Shorts M',         'APRL','BOTM','BOTM', 1200,  540, 25, 8, 'PCS', 'SUP004'),
    ('SHT-BLK-L',    'Black Shorts L',         'APRL','BOTM','BOTM', 1200,  540, 20, 8, 'PCS', 'SUP004'),
    ('TRK-GRY-M',    'Grey Track Pants M',     'APRL','BOTM','BOTM', 1450,  653, 18, 6, 'PCS', 'SUP004'),
    ('TRK-BLK-L',    'Black Track Pants L',    'APRL','BOTM','BOTM', 1450,  653, 14, 6, 'PCS', 'SUP004'),
    ('CGO-KHK-L',    'Khaki Cargo Pants L',    'APRL','BOTM','BOTM', 1750,  788, 12, 4, 'PCS', 'SUP004'),
    ('CHN-BLK-32',   'Black Chinos Sz32',      'APRL','BOTM','BOTM', 1800,  810, 16, 5, 'PCS', 'SUP004'),
    # ── Accessories ───────────────────────────────────────────────────────────────────────
    ('CAP-BLK-OS',   'Black Snapback Cap',     'APRL','ACCS','ACCS',  750,  300, 30, 8, 'PCS', 'SUP005'),
    ('CAP-WHT-OS',   'White Snapback Cap',     'APRL','ACCS','ACCS',  750,  300, 28, 8, 'PCS', 'SUP005'),
    ('CAP-NVY-OS',   'Navy Snapback Cap',      'APRL','ACCS','ACCS',  750,  300, 20, 8, 'PCS', 'SUP005'),
    ('BLT-BLK-OS',   'Black Leather Belt',     'APRL','ACCS','ACCS',  850,  340, 22, 6, 'PCS', 'SUP005'),
    ('BLT-BRN-OS',   'Brown Leather Belt',     'APRL','ACCS','ACCS',  850,  340, 18, 6, 'PCS', 'SUP005'),
    ('WLT-BLK-OS',   'Black Bifold Wallet',    'APRL','ACCS','ACCS', 1100,  495, 15, 4, 'PCS', 'SUP005'),
    ('WLT-BRN-OS',   'Brown Bifold Wallet',    'APRL','ACCS','ACCS', 1100,  495, 12, 4, 'PCS', 'SUP005'),
    ('SCF-GRY-OS',   'Grey Knit Scarf',        'APRL','ACCS','ACCS',  590,  236, 16, 4, 'PCS', 'SUP005'),
    ('SCK-WHT-OS',   'White Ankle Socks',      'APRL','ACCS','ACCS',  180,   72, 60,15, 'PCS', 'SUP005'),
    ('SCK-BLK-OS',   'Black Ankle Socks',      'APRL','ACCS','ACCS',  180,   72, 55,15, 'PCS', 'SUP005'),
    # ── Bags ──────────────────────────────────────────────────────────────────────────────
    ('BKP-BLK-OS',   'Black Backpack',         'APRL','BAGS','BAGS', 2800, 1260, 14, 4, 'PCS', 'SUP006'),
    ('BKP-GRY-OS',   'Grey Backpack',          'APRL','BAGS','BAGS', 2800, 1260, 10, 4, 'PCS', 'SUP006'),
    ('BKP-NVY-OS',   'Navy Backpack',          'APRL','BAGS','BAGS', 2800, 1260, 8,  4, 'PCS', 'SUP006'),
    ('TTE-TAN-OS',   'Tan Canvas Tote Bag',    'APRL','BAGS','BAGS', 1500,  675, 18, 5, 'PCS', 'SUP006'),
    ('TTE-BLK-OS',   'Black Canvas Tote Bag',  'APRL','BAGS','BAGS', 1500,  675, 15, 5, 'PCS', 'SUP006'),
    ('SLB-BRN-OS',   'Brown Sling Bag',        'APRL','BAGS','BAGS', 1800,  810, 12, 4, 'PCS', 'SUP006'),
    ('MSG-BLK-OS',   'Black Messenger Bag',    'APRL','BAGS','BAGS', 2400, 1080, 9,  3, 'PCS', 'SUP006'),
    ('DFL-BLK-OS',   'Black Duffel Bag',       'APRL','BAGS','BAGS', 3500, 1575, 6,  2, 'PCS', 'SUP006'),
    ('CLT-BLK-OS',   'Black Clutch Bag',       'APRL','BAGS','BAGS', 1200,  540, 11, 4, 'PCS', 'SUP006'),
    ('FNY-BLK-OS',   'Black Fanny Pack',       'APRL','BAGS','BAGS',  950,  428, 14, 4, 'PCS', 'SUP006'),
]


class Command(BaseCommand):
    help = 'Seed 50 product records into the inventory'

    def handle(self, *args, **kwargs):
        created_count = 0
        skipped_count = 0

        for row in PRODUCTS:
            (itemcode, descshort, deptcode, classcode, categorycode,
             price, cost, stock, rop, uom, supplier) = row

            _, created = Product.objects.get_or_create(
                itemcode=itemcode,
                defaults={
                    'descshort':      descshort,
                    'deptcode':       deptcode,
                    'classcode':      classcode,
                    'categorycode':   categorycode,
                    'sell_price_rp':  price,
                    'unitcost':       cost,
                    'stock_sa':       float(stock),
                    'stock_rop':      float(rop),
                    'sell_uom':       uom,
                    'suppliercode':   supplier,
                    'active':         True,
                    'trackinventory': True,
                },
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done — {created_count} created, {skipped_count} already existed.'
        ))
