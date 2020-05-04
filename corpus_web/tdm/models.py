from django.db import models

# Create your models here.
class Article(models.Model):
	title = models.CharField(max_length=200)
	abstract = models.CharField(max_length=3000)
	body_text = models.CharField(max_length=30000)
	# ...
	def __str__(self):
		return self.title
