#!/bin/bash
cd /home/site/wwwroot/appfew
pip install -r requirements.txt
python manage.py migrate
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'appfew.settings')
django.setup()
from monotal.models import ProductCategory
for i, n in [(1,'電子機器'),(2,'ファッション'),(3,'スポーツ・アウトドア'),(4,'エンタメ・ホビー'),(5,'生活・インテリア')]:
    ProductCategory.objects.get_or_create(product_category_id=i, defaults={'category_name': n})
print('カテゴリ5件登録完了')
"
python manage.py seed_quests
gunicorn appfew.wsgi:application --bind 0.0.0.0:8000
