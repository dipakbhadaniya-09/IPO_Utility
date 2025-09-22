
from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('Broker_id', models.CharField(default=None, max_length=1000, null=True)),
                ('Group_id', models.CharField(default=None, max_length=1000, null=True)),
                ('Order_limit', models.IntegerField(blank=True, max_length=100, null=True)),
                ('IPO_limit', models.IntegerField(blank=True, max_length=100, null=True)),
                ('Client_limit', models.IntegerField(blank=True, max_length=100, null=True)),
                ('Group_limit', models.IntegerField(blank=True, max_length=100, null=True)),
                ('Premium_Order_limit', models.IntegerField(blank=True, max_length=100, null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='ClientDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('PANNo', models.CharField(default=None, max_length=10)),
                ('Name', models.CharField(blank=True, max_length=100)),
                ('ClientIdDpId', models.CharField(blank=True, max_length=100)),
                ('Active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='CurrentIpoName',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('IPOType', models.CharField(default=None, max_length=100, null=True)),
                ('IPOName', models.CharField(default=None, max_length=100)),
                ('IPOPrice', models.FloatField(blank=True)),
                ('PreOpenPrice', models.FloatField(default=0)),
                ('LotSizeRetail', models.FloatField(default=None, null=True)),
                ('LotSizeSHNI', models.FloatField(default=None, null=True)),
                ('LotSizeBHNI', models.FloatField(default=None, null=True)),
                ('Remark', models.CharField(blank=True, max_length=500)),
                ('TotalIPOSzie', models.CharField(blank=True, max_length=100)),
                ('RetailPercentage', models.CharField(blank=True, max_length=100)),
                ('SHNIPercentage', models.CharField(blank=True, max_length=100)),
                ('BHNIPercentage', models.CharField(blank=True, max_length=100)),
                ('ExpecetdRetailApplication', models.CharField(blank=True, max_length=100)),
                ('ExpecetdSHNIApplication', models.CharField(blank=True, max_length=100, null=True)),
                ('ExpecetdBHNIApplication', models.CharField(blank=True, max_length=100, null=True)),
                ('ProfitMargin', models.CharField(blank=True, max_length=100)),
                ('Premium', models.CharField(blank=True, max_length=100)),
                ('Active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='IPO', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='GroupDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('GroupName', models.CharField(default=None, max_length=100)),
                ('MobileNo', models.CharField(blank=True, max_length=100)),
                ('Address', models.CharField(blank=True, max_length=500)),
                ('Collection', models.FloatField(default=0)),
                ('Remark', models.CharField(blank=True, max_length=500)),
                ('Active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='Group', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('OrderType', models.CharField(default=None, max_length=100)),
                ('Rate', models.FloatField(default=None)),
                ('Quantity', models.FloatField(default=None)),
                ('OrderCategory', models.CharField(default=None, max_length=100)),
                ('Amount', models.FloatField(default=0)),
                ('OrderDate', models.DateField()),
                ('Active', models.BooleanField(default=True)),
                ('OrderTime', models.TimeField(null=True)),
                ('InvestorType', models.CharField(default=None, max_length=100, null=True)),
                ('OrderGroup', models.ForeignKey(default=None, on_delete=django.db.models.deletion.SET_DEFAULT, to='home.groupdetail')),
                ('OrderIPOName', models.ForeignKey(default=None, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='IPOName1', to='home.currentiponame')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='Order', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='RateList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kostakBuyRate', models.FloatField(default=0)),
                ('KostakBuyQty', models.FloatField(default=0)),
                ('kostakSellRate', models.FloatField(default=0)),
                ('KostakSellQty', models.FloatField(default=0)),
                ('SubjecToBuyRate', models.FloatField(default=0)),
                ('SubjecToBuyQty', models.FloatField(default=0)),
                ('SubjecToSellRate', models.FloatField(default=0)),
                ('SubjecToSellQty', models.FloatField(default=0)),
                ('PremiumBuyRate', models.FloatField(default=0)),
                ('PremiumBuyQty', models.FloatField(default=0)),
                ('PremiumSellRate', models.FloatField(default=0)),
                ('PremiumSellQty', models.FloatField(default=0)),
                ('RateListIPOName', models.ForeignKey(default=None, on_delete=django.db.models.deletion.SET_DEFAULT, to='home.currentiponame')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='OrderDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('AllotedQty', models.FloatField(blank=True, null=True)),
                ('PreOpenPrice', models.FloatField(default=0)),
                ('ApplicationNumber', models.CharField(blank=True, max_length=100)),
                ('DematNumber', models.CharField(blank=True, max_length=100)),
                ('Amount', models.FloatField(default=0)),
                ('Active', models.BooleanField(default=True, max_length=100)),
                ('Order', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, to='home.order')),
                ('OrderDetailPANNo', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, to='home.clientdetail')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='OrderDetail', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='clientdetail',
            name='Group',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.SET_DEFAULT, to='home.groupdetail'),
        ),
        migrations.AddField(
            model_name='clientdetail',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='Client', to=settings.AUTH_USER_MODEL),
        ),
    ]
