import sqlite3
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
categories = [
    'カメラ・撮影機材',
    '家電・生活家電',
    'アウトドア・スポーツ用品',
    '楽器・音楽機材',
    'パソコン・周辺機器'
]
for cat in categories:
    cursor.execute('INSERT INTO M_ProductCategory (category_name, parent_product_category_id) VALUES (?, NULL)', (cat,))
conn.commit()
print(f'追加完了: {len(categories)}件')
cursor.execute('SELECT product_category_id, category_name FROM M_ProductCategory')
for row in cursor.fetchall():
    print(f'ID: {row[0]}, カテゴリ名: {row[1]}')
conn.close()
