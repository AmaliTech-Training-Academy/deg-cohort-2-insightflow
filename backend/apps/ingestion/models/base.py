from django.db import models
from apps.authentication.models import User

class Customer(models.Model):
    customerId = models.CharField(max_length=20, primary_key=True, db_column='customerId')
    userId = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId')

    class Meta:
        db_table = 'customer'

    def save(self, *args, **kwargs):
        if not self.customerId:
            last_customer = Customer.objects.all().order_by('customerId').last()
            if not last_customer:
                self.customerId = 'CUST-000001'
            else:
                last_number = int(last_customer.customerId.split('-')[1])
                next_number = last_number + 1
                self.customerId = f'CUST-{next_number:06d}'
        super().save(*args, **kwargs)

