from django.db import models

class ParleProduct(models.Model):
    sku_id = models.IntegerField(primary_key=True)  # auto-increment ID
    brand = models.CharField(max_length=100)
    mrp = models.IntegerField()
    min_order = models.IntegerField()
    box_amount = models.IntegerField()
    image_url = models.URLField()  # better for URLs

    def __str__(self):
        return f"{self.brand} - {self.sku_id}"