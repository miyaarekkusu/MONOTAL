from django.db import models


class Product(models.Model):
    """商品テーブル"""
    name = models.CharField(max_length=200, verbose_name='商品名')
    image = models.ImageField(upload_to='products/', verbose_name='商品画像')
    description = models.TextField(verbose_name='商品詳細')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品価格')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


    aaa