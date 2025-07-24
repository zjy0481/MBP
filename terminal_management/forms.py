# terminal_management/forms.py
from django import forms
from .models import ShipInfo
from .models import TerminalInfo
from .models import BaseStationInfo

class ShipInfoForm(forms.ModelForm):
    """
    基于 ShipInfo 模型创建的表单。
    ModelForm 会自动根据模型的字段生成对应的表单输入项。
    """
    class Meta:
        model = ShipInfo  # 指定表单基于哪个模型
        fields = '__all__' # '__all__' 表示包含模型中的所有字段
        # 你也可以手动指定字段，例如：fields = ['mmsi', 'ship_name', 'call_sign', 'ship_owner']

        # widgets 可以用来定制输入框的样式和属性
        widgets = {
            'mmsi': forms.TextInput(attrs={'class': 'form-control'}),
            'ship_name': forms.TextInput(attrs={'class': 'form-control'}),
            'call_sign': forms.TextInput(attrs={'class': 'form-control'}),
            'ship_owner': forms.TextInput(attrs={'class': 'form-control'}),
        }

class TerminalInfoForm(forms.ModelForm):
    """
    基于 TerminalInfo 模型创建的表单。
    """
    # 我们自定义一个字段来接收呼号，而不是一个下拉框
    ship_call_sign = forms.CharField(
        label='所属船舶呼号', 
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = TerminalInfo
        # 我们只包含需要用户填写的字段
        fields = ['sn', 'ship_call_sign', 'ip_address', 'port_number']
        widgets = {
            'sn': forms.TextInput(attrs={'class': 'form-control'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control'}),
            'port_number': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class BaseStationInfoForm(forms.ModelForm):
    """
    基于 BaseStationInfo 模型创建的表单。
    """
    class Meta:
        model = BaseStationInfo
        fields = '__all__' # 包含所有字段
        widgets = {
            'bts_id': forms.TextInput(attrs={'class': 'form-control'}),
            'bts_name': forms.TextInput(attrs={'class': 'form-control'}),
            'frequency_band': forms.TextInput(attrs={'class': 'form-control'}),
            'coverage_distance': forms.NumberInput(attrs={'class': 'form-control'}),
            'region_code': forms.TextInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
        }